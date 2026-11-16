"""Run with python -m fraudline.pipeline; no network or credentials needed for demo training."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from fraudline.data import FEATURES, INPUTS, features, import_ieee, sha256, split_time, synthetic, validate
from fraudline.model import Model

ROOT = Path(os.environ.get("FRAUDLINE_HOME", ".")).resolve()
ART = ROOT / "artifacts"


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


@contextmanager
def lifecycle_lock():
    lock = ART / ".lifecycle-lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        raise RuntimeError(
            "Another lifecycle operation is running; check for a stale lock after a crash"
        ) from None
    try:
        yield
    finally:
        lock.rmdir()


def registry():
    path = ART / "registry.json"
    return (
        json.loads(path.read_text()) if path.exists() else {"champion": None, "previous": None, "history": []}
    )


def records(frame):
    return frame[INPUTS].replace({np.nan: None}).to_dict("records")


def costs(y, p, amount, review, block):
    # Hypothetical costs: review $3 and 20% missed fraud; false block $15.
    approve = p < review
    blocked = p >= block
    loss = np.where(approve, y * amount, np.where(blocked, (1 - y) * 15.0, 3.0 + y * amount * 0.2))
    return float(np.mean(loss))


def evaluate(frame, p, thresholds):
    y = frame.is_fraud.to_numpy()
    alert = p >= thresholds["review"]
    metrics = {
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "recall": float(np.sum(alert & (y == 1)) / np.sum(y == 1)),
        "false_positive_rate": float(np.sum(alert & (y == 0)) / np.sum(y == 0)),
        "cost_per_transaction": costs(y, p, frame.amount.to_numpy(), **thresholds),
        "rows": len(frame),
    }
    return metrics


def can_promote(candidate, incumbent):
    if incumbent is None:
        return True
    return (
        candidate["pr_auc"] > incumbent["pr_auc"] + 0.001
        and candidate["cost_per_transaction"] <= incumbent["cost_per_transaction"]
        and candidate["recall"] >= incumbent["recall"] - 0.03
    )


def prepare(ieee=None, rows=12000, seed=42):
    data = ROOT / "data"
    data.mkdir(parents=True, exist_ok=True)
    frame = import_ieee(ieee) if ieee else validate(synthetic(rows, seed))
    frame.to_parquet(data / "transactions.parquet", index=False)
    lineage = {
        "data_source": "ieee-cis" if ieee else "synthetic",
        "rows": len(frame),
        "seed": seed,
        "data_sha256": sha256(data / "transactions.parquet"),
    }
    if ieee:
        lineage["raw_sha256"] = {
            name: sha256(Path(ieee) / name) for name in ["train_transaction.csv", "train_identity.csv"]
        }
    write_json(data / "lineage.json", lineage)
    return lineage


def train(tune=False):
    with lifecycle_lock():
        return _train(tune)


def _train(tune=False):
    frame = validate(pd.read_parquet(ROOT / "data/transactions.parquet"))
    lineage = json.loads((ROOT / "data/lineage.json").read_text())
    if sha256(ROOT / "data/transactions.parquet") != lineage["data_sha256"]:
        raise ValueError("Dataset hash changed; run prepare again")
    training, calibration, promotion, final = split_time(frame)
    x, y = features(records(training)), training.is_fraud
    baseline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=42))
    baseline.fit(x, y)
    params = {
        "objective": "binary",
        "n_estimators": 100,
        "learning_rate": 0.05,
        "num_leaves": 15,
        "min_child_samples": 40,
        "reg_lambda": 2.0,
        "verbosity": -1,
        "n_jobs": 1,
        "random_state": 42,
        "deterministic": True,
        "force_col_wise": True,
    }
    if tune:
        import optuna

        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))

        def objective(trial):
            choices = {
                "num_leaves": trial.suggest_categorical("num_leaves", [7, 15, 31]),
                "reg_lambda": trial.suggest_float("reg_lambda", 1.0, 10.0),
            }
            m = lgb.LGBMClassifier(**(params | choices)).fit(x, y)
            return average_precision_score(
                calibration.is_fraud, m.predict_proba(features(records(calibration)))[:, 1]
            )

        study.optimize(objective, n_trials=6)
        params.update(study.best_params)
    classifier = lgb.LGBMClassifier(**params).fit(x, y)
    raw = classifier.booster_.predict(features(records(calibration)), raw_score=True, num_threads=1)
    calibrator = LogisticRegression(C=10, random_state=42).fit(
        np.asarray(raw).reshape(-1, 1), calibration.is_fraud
    )
    probabilities = calibrator.predict_proba(np.asarray(raw).reshape(-1, 1))[:, 1]
    options = np.linspace(0.01, 0.8, 35)
    _, review, block = min(
        (
            costs(calibration.is_fraud.to_numpy(), probabilities, calibration.amount.to_numpy(), a, b),
            float(a),
            float(b),
        )
        for a in options
        for b in options
        if a < b
    )
    version = f"fl-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"
    folder = ART / "models" / version
    folder.mkdir(parents=True)
    training[INPUTS].to_parquet(folder / "reference.parquet", index=False)
    classifier.booster_.save_model(str(folder / "model.txt"))
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = "uncommitted"
    metadata = {
        **lineage,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "features": FEATURES,
        "model_sha256": sha256(folder / "model.txt"),
        "thresholds": {"review": review, "block": block},
        "calibration": {"slope": float(calibrator.coef_[0, 0]), "intercept": float(calibrator.intercept_[0])},
        "cost_assumptions": {"review": 3, "review_missed_fraction": 0.2, "false_block": 15},
        "splits": {
            name: {"rows": len(g), "start": int(g.time_offset.min()), "end": int(g.time_offset.max())}
            for name, g in zip(
                ["train", "calibration", "promotion", "final_test"],
                [training, calibration, promotion, final],
                strict=True,
            )
        },
    }
    write_json(folder / "metadata.json", metadata)
    model = Model(folder)
    candidate = evaluate(promotion, model.probabilities(records(promotion)), metadata["thresholds"])
    state = registry()
    incumbent = None
    if state["champion"]:
        old = Model(ART / "models" / state["champion"])
        if old.meta["data_source"] != lineage["data_source"]:
            raise ValueError("Do not compare synthetic and IEEE champions; use a separate FRAUDLINE_HOME")
        incumbent = evaluate(promotion, old.probabilities(records(promotion)), old.meta["thresholds"])
    promoted = can_promote(candidate, incumbent)
    final_metrics = evaluate(final, model.probabilities(records(final)), metadata["thresholds"])
    slices = {
        str(key): evaluate(group, model.probabilities(records(group)), metadata["thresholds"])
        for key, group in final.groupby("product")
        if len(group) >= 50 and group.is_fraud.nunique() == 2
    }
    report = {
        "version": version,
        "data_source": lineage["data_source"],
        "promotion": candidate,
        "incumbent": incumbent,
        "promoted": promoted,
        "final_test": final_metrics,
        "slices": slices,
        "baseline": evaluate(
            final, baseline.predict_proba(features(records(final)))[:, 1], metadata["thresholds"]
        ),
        "warning": "Synthetic scores do not estimate real fraud performance"
        if lineage["data_source"] == "synthetic"
        else "Anonymized IEEE features are not verified authorization-time inputs",
    }
    write_json(folder / "evaluation.json", report)
    mlflow_version = track(folder, params, report, metadata)
    if promoted:
        state["previous"], state["champion"] = state["champion"], version
    state["history"].append(
        {
            "version": version,
            "promoted": promoted,
            "at": metadata["created_at"],
            "metrics": candidate,
            "data_source": lineage["data_source"],
            "mlflow_version": mlflow_version,
        }
    )
    sync_mlflow_aliases(state)
    write_json(ART / "registry.json", state)
    write_json(ART / "reports/latest-training.json", report)
    if promoted or not (ART / "reference.parquet").exists():
        shutil.copy2(folder / "reference.parquet", ART / "reference.parquet")
    return report


def track(folder, params, report, metadata):
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        return None
    import mlflow
    import mlflow.lightgbm

    mlflow.set_experiment("fraudline")
    with mlflow.start_run():
        mlflow.log_params(
            params
            | {
                "data_sha256": metadata["data_sha256"],
                "git_commit": metadata["git_commit"],
                "data_source": metadata["data_source"],
            }
        )
        mlflow.log_metrics(report["promotion"])
        mlflow.log_artifacts(str(folder), artifact_path="bundle")
        info = mlflow.lightgbm.log_model(
            lgb.Booster(model_file=str(folder / "model.txt")), name="model", registered_model_name="fraudline"
        )
        version = info.registered_model_version
        mlflow.MlflowClient().set_model_version_tag(
            "fraudline", version, "bundle_version", metadata["version"]
        )
        mlflow.MlflowClient().set_registered_model_alias("fraudline", "challenger", version)
        return str(version)


def sync_mlflow_aliases(state):
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        return
    from mlflow import MlflowClient

    client = MlflowClient()
    for alias in ["previous", "champion"]:
        bundle_version = state[alias]
        if not bundle_version:
            continue
        folder = ART / "models" / bundle_version
        metadata = Model(folder).meta
        known = client.search_model_versions("name='fraudline'")
        match = next((v for v in known if v.tags.get("bundle_version") == bundle_version), None)
        version = (
            match.version
            if match
            else track(folder, {}, json.loads((folder / "evaluation.json").read_text()), metadata)
        )
        client.set_registered_model_alias("fraudline", alias, version)


def rollback():
    with lifecycle_lock():
        state = registry()
        if not state["previous"]:
            raise ValueError("No previous champion exists")
        previous_folder = ART / "models" / state["previous"]
        previous_model = Model(previous_folder)
        current_model = Model(ART / "models" / state["champion"])
        reference = previous_folder / "reference.parquet"
        if not reference.exists() and previous_model.meta["data_sha256"] != current_model.meta["data_sha256"]:
            raise ValueError("Previous model has no compatible drift reference; rollback aborted")
        state["champion"], state["previous"] = state["previous"], state["champion"]
        state["history"].append(
            {"action": "rollback", "version": state["champion"], "at": datetime.now(timezone.utc).isoformat()}
        )
        sync_mlflow_aliases(state)
        if reference.exists():
            shutil.copy2(reference, ART / "reference.parquet")
        write_json(ART / "registry.json", state)
    return state


def main():
    # MLflow prints emoji URLs; legacy Windows pipe encodings must not abort a completed run.
    sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "train", "demo", "rollback"])
    parser.add_argument("--ieee")
    parser.add_argument("--rows", type=int, default=12000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tune", action="store_true")
    args = parser.parse_args()
    if args.command in ["prepare", "demo"]:
        print(json.dumps(prepare(args.ieee, args.rows, args.seed)))
    if args.command in ["train", "demo"]:
        print(json.dumps(train(args.tune), indent=2))
    if args.command == "rollback":
        print(json.dumps(rollback(), indent=2))


if __name__ == "__main__":
    main()
