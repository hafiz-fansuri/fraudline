"""Exercise the real serving path with authored synthetic inputs, not an accuracy benchmark."""

import math
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from fraudline.api import create_app
from fraudline.pipeline import ART, registry, write_json
from fraudline.scenarios import scenarios
from fraudline.signals import combine


def run():
    version = registry()["champion"]
    cases = scenarios()
    with tempfile.TemporaryDirectory(prefix="fraudline-scenarios-") as directory:
        with TestClient(create_app(database_url=f"sqlite:///{Path(directory) / 'events.db'}")) as client:
            response = client.post("/predict/batch", json={"transactions": [c["transaction"] for c in cases]})
            assert response.status_code == 200, response.text
            results = response.json()["predictions"]
            assert len(results) == len(cases)
            rows = []
            for case, result in zip(cases, results, strict=True):
                factors = {item["factor"] for item in result["signals"]}
                passed = case["expected_factor"] in factors if case["expected_factor"] else not factors
                assert passed, case["id"]
                assert math.isfinite(result["probability"]) and 0 <= result["probability"] <= 1
                assert result["decision"] == combine(result["model_decision"], result["signals"])
                assert result["model_version"] == version and result["prediction_id"]
                rows.append(
                    {
                        "scenario": case["id"],
                        "expected_factor": case["expected_factor"],
                        "activated_factors": sorted(factors),
                        "passed": passed,
                        "model_probability": result["probability"],
                        "model_decision": result["model_decision"],
                        "final_decision": result["decision"],
                    }
                )
            invalid = cases[0]["transaction"] | {"amount": -1}
            assert client.post("/predict", json=invalid).status_code == 422
            assert (
                client.post(
                    "/predict", json=cases[0]["transaction"] | {"benchmark_signals": {"isFraud": 1}}
                ).status_code
                == 422
            )
    report = {
        "model_version": version,
        "passed": len(rows),
        "total": len(cases),
        "results": rows,
        "interpretation": "Synthetic signal/serving checks only; not a real-world classifier accuracy estimate",
    }
    write_json(ART / "reports/synthetic-tests.json", report)
    print(f"Passed {len(rows)}/{len(cases)} synthetic end-to-end cases for {version}")
    return report


if __name__ == "__main__":
    run()
