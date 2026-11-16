"""Exercise the actual local stack with explicitly synthetic traffic and delayed labels."""

import json
import os
from urllib.request import Request, urlopen

from fraudline.data import synthetic
from fraudline.monitor import monitor_once
from fraudline.pipeline import ART, records, write_json
from fraudline.store import Store

base = os.environ.get("FRAUDLINE_API_URL", "http://api:8000")
store = Store(os.environ["DATABASE_URL"])
normal = synthetic(200, seed=918)
assert normal.is_fraud.nunique() == 2
shifted = synthetic(400, seed=919)
shifted["amount"] *= 8
shifted["distance"] = 1800.0
count = 0
for frame, labeled in [(normal, True), (shifted, False)]:
    inputs = records(frame)
    for offset in range(0, len(inputs), 100):
        request = Request(
            base + "/predict/batch",
            data=json.dumps({"transactions": inputs[offset : offset + 100]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            results = json.load(response)["predictions"]
        count += len(results)
        if labeled:
            for index, result in enumerate(results):
                store.add_label(result["prediction_id"], int(frame.iloc[offset + index].is_fraud))
report = monitor_once(retrain=True)
assert report["status"] == "ready" and report["drifted"]
assert report["performance"]["status"] == "ready"
evidence = {
    "provenance": "Synthetic traffic; injected covariate shift, no real payments",
    "predictions": count,
    "delayed_labels": len(normal),
    "drift_alert": report["drifted"],
    "retraining": report["retraining"],
    "performance": report["performance"],
    "evidently_html": (ART / "reports/evidently.html").exists(),
}
write_json(ART / "reports/lifecycle-demo.json", evidence)
print(json.dumps(evidence, indent=2))
