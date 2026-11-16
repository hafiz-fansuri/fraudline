import argparse
import json
import os
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon

from fraudline.data import FEATURES, features, synthetic
from fraudline.model import Model
from fraudline.pipeline import ART, ROOT, records, registry, train, write_json
from fraudline.store import Store


def drift(reference, current, minimum=100):
    if len(current) < minimum:
        return {
            "status": "insufficient_samples",
            "samples": len(current),
            "minimum": minimum,
            "drifted": False,
            "features": [],
        }
    a, b = features(records(reference)), features(records(current))
    result = []
    for name in FEATURES:
        edges = np.unique(np.quantile(a[name], np.linspace(0, 1, 11)))
        if len(edges) < 3:
            edges = np.array([-np.inf, 0.5, np.inf])
        else:
            edges[0], edges[-1] = -np.inf, np.inf
        left, _ = np.histogram(a[name], bins=edges)
        right, _ = np.histogram(b[name], bins=edges)
        distance = float(jensenshannon(left + 1, right + 1))
        result.append({"feature": name, "distance": round(distance, 4), "drifted": distance > 0.2})
    return {
        "status": "ready",
        "samples": len(current),
        "minimum": minimum,
        "drifted": any(r["drifted"] for r in result),
        "features": result,
        "method": "Jensen-Shannon distance; threshold 0.20; reference quantile bins",
    }


def demo_reports():
    reference = pd.read_parquet(ART / "reference.parquet")
    normal = synthetic(1500, 123)
    shifted = normal.copy()
    shifted["amount"] *= 8
    shifted["distance"] = 1800.0
    model = Model(ART / "models" / registry()["champion"])
    output = {}
    for name, frame in [("reference", normal), ("shifted", shifted)]:
        report = drift(reference, frame)
        p = model.probabilities(records(frame))
        report.update(
            {
                "scenario": name,
                "provenance": "Injected synthetic scenario"
                if name == "shifted"
                else "Independent synthetic sample",
                "prediction_mean": float(p.mean()),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "retraining": "Not triggered: isolated demonstration",
            }
        )
        output[name] = report
    write_json(ART / "reports/demo-drift.json", output)
    return output


def monitor_once(retrain=False):
    store = Store(os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'runtime/events.db'}"))
    rows = store.recent()
    model = Model(ART / "models" / registry()["champion"])
    current = pd.DataFrame(
        [r["features"] for r in rows if r["prediction"]["model_version"] == model.meta["version"]]
    )
    reference = pd.read_parquet(ART / "reference.parquet")
    report = drift(reference, current)
    report["performance"] = store.performance()
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["retraining"] = "Not requested"
    report["alerts"] = []
    webhook = os.environ.get("ALERT_WEBHOOK_URL")
    if report["drifted"]:
        report["alerts"].append({"kind": "data_drift", "status": "local_alert"})
        if webhook:
            request = Request(
                webhook,
                data=json.dumps(
                    {"content": "Fraudline: data drift threshold exceeded; inspect the monitoring report."}
                ).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=10) as response:
                report["alerts"][-1]["status"] = f"webhook_{response.status}"
    stamp = ROOT / "runtime/last-retraining.json"
    last = json.loads(stamp.read_text())["time"] if stamp.exists() else 0
    if retrain and report["drifted"]:
        if time.time() - last < 86400:
            report["retraining"] = "Suppressed by 24-hour cooldown"
        else:
            # A frozen dataset cannot fix new drift; require a newly labeled, prepared dataset.
            lineage = json.loads((ROOT / "data/lineage.json").read_text())
            if lineage["data_sha256"] == model.meta["data_sha256"]:
                report["retraining"] = "Waiting for a new validated labeled dataset"
            else:
                result = train()
                write_json(stamp, {"time": time.time(), "version": result["version"]})
                report["retraining"] = {"version": result["version"], "promoted": result["promoted"]}
    if len(current) >= 100:
        from evidently import Report
        from evidently.presets import DataDriftPreset

        snapshot = Report([DataDriftPreset()]).run(
            reference_data=features(records(reference)), current_data=features(records(current))
        )
        path = ART / "reports/evidently.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        snapshot.save_html(str(path))
    write_json(ART / "reports/monitoring.json", report)
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--retrain", action="store_true")
    args = parser.parse_args()
    demo_reports() if args.demo else monitor_once(args.retrain)
