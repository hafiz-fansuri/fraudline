import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pandera.errors import SchemaErrors

from fraudline import pipeline
from fraudline.data import FEATURES, features, import_ieee, split_time, synthetic, validate
from fraudline.model import Model
from fraudline.monitor import drift
from fraudline.store import Store


@pytest.fixture(scope="session")
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("trained")
    old_root, old_art = pipeline.ROOT, pipeline.ART
    pipeline.ROOT, pipeline.ART = root, root / "artifacts"
    try:
        pipeline.prepare(rows=6000)
        report = pipeline.train()
        yield pipeline.ART / "models" / report["version"]
    finally:
        pipeline.ROOT, pipeline.ART = old_root, old_art


def test_seed_and_time_boundaries():
    frame = validate(synthetic(6000))
    pd.testing.assert_frame_equal(frame, validate(synthetic(6000)))
    # Equal timestamps at the split boundary must travel together.
    frame.loc[1, "time_offset"] = frame.loc[0, "time_offset"]
    groups = split_time(frame)
    assert sum(map(len, groups)) == len(frame)
    for a, b in zip(groups, groups[1:], strict=False):
        assert a.time_offset.max() < b.time_offset.min()


def test_shared_feature_contract():
    rows = pipeline.records(synthetic(200))
    batch = features(rows)
    single = features([rows[0]])
    assert list(batch.columns) == FEATURES
    np.testing.assert_array_equal(batch.iloc[0].to_numpy(), single.iloc[0].to_numpy())
    assert np.isfinite(batch.to_numpy()).all()
    altered = synthetic(200)
    altered["is_fraud"] = 1 - altered.is_fraud
    pd.testing.assert_frame_equal(features(pipeline.records(altered)), batch)
    with pytest.raises(ValueError):
        features([rows[0] | {"network": "invalid"}])


def test_validation_rejects_bad_data():
    frame = synthetic(1000)
    frame.loc[0, "amount"] = -10
    with pytest.raises(SchemaErrors):
        validate(frame)


def test_ieee_join_fanout_rejected(tmp_path):
    pd.DataFrame(
        {
            "TransactionID": [1],
            "TransactionDT": [100],
            "TransactionAmt": [10],
            "ProductCD": ["W"],
            "card4": ["visa"],
            "card6": ["debit"],
            "dist1": [2],
            "isFraud": [0],
        }
    ).to_csv(tmp_path / "train_transaction.csv", index=False)
    pd.DataFrame({"TransactionID": [1, 1]}).to_csv(tmp_path / "train_identity.csv", index=False)
    with pytest.raises(pd.errors.MergeError):
        import_ieee(tmp_path)


def test_model_integrity_and_reasons(bundle, tmp_path):
    model = Model(bundle)
    rows = pipeline.records(synthetic(200))[:2]
    predicted = model.predict(rows)
    np.testing.assert_allclose([p["probability"] for p in predicted], model.probabilities(rows), atol=1e-6)
    assert all(0 <= p["probability"] <= 1 and len(p["reasons"]) == 3 for p in predicted)
    assert model.predict([rows[0]])[0] == predicted[0]
    corrupted = tmp_path / "bad"
    corrupted.mkdir()
    (corrupted / "metadata.json").write_text((bundle / "metadata.json").read_text())
    (corrupted / "model.txt").write_text("tampered")
    with pytest.raises(ValueError, match="integrity"):
        Model(corrupted)


def test_promotion_gate():
    champion = {"pr_auc": 0.3, "cost_per_transaction": 2.0, "recall": 0.7}
    assert pipeline.can_promote(champion, None)
    assert not pipeline.can_promote(champion, champion)
    assert not pipeline.can_promote(champion | {"pr_auc": 0.5, "cost_per_transaction": 3}, champion)
    assert not pipeline.can_promote(champion | {"pr_auc": 0.5, "recall": 0.4}, champion)
    assert pipeline.can_promote(champion | {"pr_auc": 0.4}, champion)


def test_drift_and_minimum_samples():
    reference = synthetic(1000)
    assert drift(reference, reference)["drifted"] is False
    assert drift(reference, reference.head(10))["status"] == "insufficient_samples"
    shifted = reference.copy()
    shifted["amount"] *= 10
    assert drift(reference, shifted)["drifted"] is True


def test_api_contract(bundle, tmp_path):
    from fraudline.api import create_app

    db = f"sqlite:///{tmp_path / 'events.db'}"
    with TestClient(create_app(bundle, db)) as client:
        assert client.get("/ready").status_code == 200
        assert client.get("/").status_code == 200
        sample = client.get("/api/samples").json()["transactions"][0]
        response = client.post("/predict", json=sample)
        assert response.status_code == 200
        result = response.json()
        assert result["decision"] in ["approve", "review", "block"]
        assert result["model_version"] and result["prediction_id"]
        assert client.post("/predict/batch", json={"transactions": [sample, sample]}).status_code == 200
        assert client.post("/predict/batch", json={"transactions": []}).status_code == 422
        assert client.post("/predict/batch", json={"transactions": [sample] * 101}).status_code == 422
        for bad in [
            {"amount": -1},
            {"amount": True},
            {"amount": "12"},
            {"identity_present": "false"},
            {"network": "no"},
            {"time_offset": 1.2},
            {"card_number": "123"},
        ]:
            assert client.post("/predict", json=sample | bad).status_code == 422
        assert client.post("/predict", content=b"x" * 66000).status_code == 413
        assert "fraudline_request_seconds" in client.get("/metrics").text
        assert client.post("/admin/retrain").status_code == 404
    store = Store(db)
    rows = store.recent()
    assert len(rows) == 3
    previous = "0" * 64
    for row in rows:
        expected = hashlib.sha256((previous + row["id"] + row["at"] + row["payload"]).encode()).hexdigest()
        assert expected == row["digest"]
        previous = expected
    store.add_label(result["prediction_id"], 1)
    assert store.performance(result["model_version"])["status"] == "insufficient_labels"
    assert store.performance("different-model")["labeled_rows"] == 0
    with pytest.raises(ValueError):
        store.add_label("unknown", 1)
    store.engine.dispose()


def test_readiness_without_model(tmp_path):
    from fraudline.api import create_app

    with TestClient(create_app(tmp_path / "missing", f"sqlite:///{tmp_path / 'events.db'}")) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503


def test_failed_audit_is_counted_as_server_error(bundle, tmp_path, monkeypatch):
    from fraudline.api import create_app

    app = create_app(bundle, f"sqlite:///{tmp_path / 'failed-audit.db'}")
    with TestClient(app, raise_server_exceptions=False) as client:
        sample = client.get("/api/samples").json()["transactions"][0]

        def fail(*args):
            raise RuntimeError("Simulated audit storage failure")

        monkeypatch.setattr(app.state.store, "append", fail)
        assert client.post("/predict", json=sample).status_code == 500
        assert 'status="500"} 1.0' in client.get("/metrics").text


def test_rollback(tmp_path, bundle, monkeypatch):
    import shutil

    monkeypatch.setattr(pipeline, "ART", tmp_path)
    metadata = json.loads((bundle / "metadata.json").read_text())
    version = metadata["version"]
    shutil.copytree(bundle, tmp_path / "models" / version)
    shutil.copytree(bundle, tmp_path / "models" / "newer")
    pipeline.write_json(tmp_path / "registry.json", {"champion": "newer", "previous": version, "history": []})
    state = pipeline.rollback()
    assert state["champion"] == version and state["previous"] == "newer"
