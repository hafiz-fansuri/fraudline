import json
from pathlib import Path

import lightgbm as lgb
import numpy as np

from fraudline.data import FEATURES, features, sha256

LABELS = {
    "log_amount": "Transaction amount",
    "hour_sin": "Time-of-day pattern",
    "hour_cos": "Time-of-day pattern",
    "product": "Product category",
    "network": "Card network",
    "card_type": "Card type",
    "log_distance": "Transaction distance",
    "distance_missing": "Distance unavailable",
    "identity_present": "Identity availability",
}


class Model:
    def __init__(self, folder):
        folder = Path(folder)
        self.meta = json.loads((folder / "metadata.json").read_text())
        if (
            not set(self.meta["features"]).issubset(FEATURES)
            or sha256(folder / "model.txt") != self.meta["model_sha256"]
        ):
            raise ValueError("Model bundle integrity or feature contract mismatch")
        self.booster = lgb.Booster(model_file=str(folder / "model.txt"))
        if self.booster.feature_name() != self.meta["features"]:
            raise ValueError("Model feature order mismatch")

    def probabilities(self, records):
        raw = self.booster.predict(features(records, self.meta["features"]), raw_score=True, num_threads=1)
        return self.calibrate(raw)

    def calibrate(self, raw):
        calibrated = raw * self.meta["calibration"]["slope"] + self.meta["calibration"]["intercept"]
        return 1 / (1 + np.exp(-np.clip(calibrated, -40, 40)))

    def predict(self, records):
        x = features(records, self.meta["features"])
        explanation = self.booster.predict(x, pred_contrib=True, num_threads=1)
        # TreeSHAP contributions plus the bias sum to the raw model score.
        probability = self.calibrate(explanation.sum(axis=1))
        contributions = explanation[:, :-1]
        review, block = self.meta["thresholds"]["review"], self.meta["thresholds"]["block"]
        results = []
        for p, row in zip(probability, contributions, strict=True):
            reasons = [
                {
                    "feature": self.meta["features"][i],
                    "label": LABELS.get(
                        self.meta["features"][i], self.meta["features"][i].replace("_", " ").capitalize()
                    ),
                    "contribution": round(float(row[i]), 5),
                    "direction": "increases" if row[i] > 0 else "decreases",
                }
                for i in np.argsort(-np.abs(row))[:3]
            ]
            results.append(
                {
                    "model_version": self.meta["version"],
                    "probability": round(float(p), 6),
                    "decision": "block" if p >= block else "review" if p >= review else "approve",
                    "thresholds": {"review": review, "block": block},
                    "reasons": reasons,
                    "reason_scale": "uncalibrated log-odds; associations, not causes",
                    "data_source": self.meta["data_source"],
                }
            )
        return results
