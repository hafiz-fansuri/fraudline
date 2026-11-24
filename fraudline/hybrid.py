"""Portable adaptation of the supplied Kaggle LGB -> XGB residual notebook.

Uses the shared, past-only serving contract rather than transductive train+test
aggregates. No competition test rows are needed and all fitted artifacts persist.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit

from fraudline.data import FEATURES, features, sha256, split_time, validate
from fraudline.pipeline import choose_thresholds, evaluate, write_json


def train(data, output, rounds=300, threads=2):
    data = Path(data)
    lineage = json.loads((data.parent / "lineage.json").read_text())
    if sha256(data) != lineage["data_sha256"]:
        raise ValueError("Prepared data hash mismatch; prepare the dataset again")
    frame = validate(pd.read_parquet(data))
    groups = split_time(frame)
    training, calibration, promotion, final = groups
    x, y = features(training), training.is_fraud.to_numpy()
    params = dict(
        objective="binary",
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=100,
        feature_fraction=0.7,
        bagging_fraction=0.8,
        bagging_freq=1,
        lambda_l2=2,
        seed=42,
        verbosity=-1,
        num_threads=threads,
        deterministic=True,
        force_col_wise=True,
    )
    oof = np.full(len(x), np.nan)
    boundaries = []
    # Split unique timestamps so equal-time records never cross fold boundaries.
    times = np.sort(training.time_offset.unique())
    for past, future in TimeSeriesSplit(n_splits=3).split(times):
        tr = np.flatnonzero(training.time_offset.to_numpy() <= times[past[-1]])
        va = np.flatnonzero(np.isin(training.time_offset, times[future]))
        model = lgb.train(params, lgb.Dataset(x.iloc[tr], label=y[tr]), num_boost_round=rounds)
        oof[va] = model.predict(x.iloc[va], raw_score=True)
        boundaries.append(dict(train_end=int(times[past[-1]]), valid_start=int(times[future[0]])))
        print(f"Past-only fold: {len(tr):,} -> {len(va):,}", flush=True)
    base = lgb.train(params, lgb.Dataset(x, label=y), num_boost_round=rounds)
    usable = np.isfinite(oof)
    residual = xgb.train(
        dict(
            objective="binary:logistic",
            tree_method="hist",
            learning_rate=0.03,
            max_depth=4,
            min_child_weight=5,
            subsample=0.8,
            colsample_bytree=0.7,
            reg_lambda=2,
            seed=42,
            nthread=threads,
        ),
        xgb.DMatrix(x.loc[usable], label=y[usable], base_margin=oof[usable]),
        num_boost_round=rounds,
    )

    def raw(rows):
        matrix = features(rows)
        margin = base.predict(matrix, raw_score=True)
        return residual.predict(xgb.DMatrix(matrix, base_margin=margin), output_margin=True)

    cal_raw = raw(calibration)
    calibrator = LogisticRegression(C=10, random_state=42).fit(cal_raw.reshape(-1, 1), calibration.is_fraud)

    def probabilities(rows):
        return calibrator.predict_proba(raw(rows).reshape(-1, 1))[:, 1]

    thresholds = choose_thresholds(calibration, probabilities(calibration))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    base.save_model(str(output / "model.txt"))
    residual.save_model(output / "residual.ubj")
    meta = dict(
        **lineage,
        version=output.name,
        model_kind="lgb-xgb-residual",
        created_at=datetime.now(timezone.utc).isoformat(),
        features=FEATURES,
        model_sha256=sha256(output / "model.txt"),
        residual_sha256=sha256(output / "residual.ubj"),
        feature_importance_gain=dict(
            zip(FEATURES, base.feature_importance(importance_type="gain").tolist(), strict=True)
        ),
        calibration=dict(slope=float(calibrator.coef_[0, 0]), intercept=float(calibrator.intercept_[0])),
        thresholds=thresholds,
        parameters=dict(rounds=rounds, threads=threads),
        oof_boundaries=boundaries,
        splits={
            name: dict(rows=len(g), start=int(g.time_offset.min()), end=int(g.time_offset.max()))
            for name, g in zip(["train", "calibration", "promotion", "final_test"], groups, strict=True)
        },
        warning="Research rerun on previously inspected IEEE intervals; not a new untouched benchmark. 54 serving features, not notebook's 488 transductive features.",
    )
    write_json(output / "metadata.json", meta)
    report = dict(
        version=output.name,
        data_source=lineage["data_source"],
        promoted=False,
        promotion=evaluate(promotion, probabilities(promotion), thresholds),
        final_test=evaluate(final, probabilities(final), thresholds),
        warning=meta["warning"],
    )
    write_json(output / "evaluation.json", report)
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Prepared IEEE transactions.parquet")
    parser.add_argument("--output", type=Path, required=True, help="New bundle directory; never overwrites")
    parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 3000 or not 1 <= args.threads <= 16:
        parser.error("Use 1–3000 rounds and 1–16 threads")
    train(args.data, args.output, args.rounds, args.threads)
