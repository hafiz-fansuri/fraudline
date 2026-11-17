"""Seeded demo data and the one feature contract used in training and serving."""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from fraudline.history import HISTORY_FEATURES, history_features

PRODUCTS = ["W", "C", "R", "H", "S"]
NETWORKS = ["visa", "mastercard", "american express", "discover", "unknown"]
CARD_TYPES = ["debit", "credit", "unknown"]
BASE_INPUTS = ["amount", "time_offset", "product", "network", "card_type", "distance", "identity_present"]
ANON_NUMERIC = [f"C{i}" for i in range(1, 15)] + ["D1", "D2", "D3", "D4", "D10", "D15"]
MATCH_FIELDS = ["M1", "M2", "M3", "M5", "M6", "M7", "M8", "M9"]
INPUTS = (
    BASE_INPUTS
    + [
        "account_id",
        "device_type",
        "payer_email_domain",
        "receiver_email_domain",
        "address_region",
        "issuer_region",
    ]
    + HISTORY_FEATURES
    + ANON_NUMERIC
    + MATCH_FIELDS
)
LEGACY_FEATURES = [
    "log_amount",
    "hour_sin",
    "hour_cos",
    "product",
    "network",
    "card_type",
    "log_distance",
    "distance_missing",
    "identity_present",
]
FEATURES = (
    LEGACY_FEATURES
    + HISTORY_FEATURES
    + [
        "device_type",
        "payer_domain_bucket",
        "receiver_domain_bucket",
        "email_domain_mismatch",
        "address_region",
        "issuer_region",
    ]
    + ANON_NUMERIC
    + MATCH_FIELDS
)


def validate(frame):
    import pandera.pandas as pa
    from pandera import Check

    pa.DataFrameSchema(
        {
            "transaction_id": pa.Column(str, unique=True),
            "amount": pa.Column(float, Check.in_range(0.01, 1_000_000), coerce=True),
            "time_offset": pa.Column(int, Check.ge(0), coerce=True),
            "product": pa.Column(str, Check.isin(PRODUCTS)),
            "network": pa.Column(str, Check.isin(NETWORKS)),
            "card_type": pa.Column(str, Check.isin(CARD_TYPES)),
            "distance": pa.Column(float, Check.in_range(0, 100_000), nullable=True, coerce=True),
            "identity_present": pa.Column(bool),
            "is_fraud": pa.Column(int, Check.isin([0, 1]), coerce=True),
        },
        strict=False,
    ).validate(frame, lazy=True)
    if len(frame) < 200 or frame.is_fraud.nunique() != 2:
        raise ValueError("Training needs at least 200 rows and both label classes")
    return frame.sort_values(["time_offset", "transaction_id"]).reset_index(drop=True)


def synthetic(rows=12000, seed=42):
    rng = np.random.default_rng(seed)
    amount = np.round(np.clip(rng.lognormal(4.0, 1.05, rows), 0.01, 10000), 2)
    distance = np.minimum(rng.exponential(90, rows), 5000)
    identity = rng.random(rows) > 0.35
    product = rng.choice(PRODUCTS, rows, p=[0.65, 0.15, 0.09, 0.06, 0.05])
    time = np.arange(rows) * 900
    hour = (time // 3600) % 24
    logits = -5.6 + 1.25 * (amount > 180) + 2.1 * (distance > 180)
    logits += 1.2 * (product == "C") + 0.8 * (~identity) + 0.9 * (hour < 5)
    labels = rng.binomial(1, 1 / (1 + np.exp(-logits)))
    distance[rng.random(rows) < 0.2] = np.nan
    return pd.DataFrame(
        {
            "transaction_id": [f"SYN-{i:06}" for i in range(rows)],
            "amount": amount,
            "time_offset": time,
            "product": product,
            "network": rng.choice(NETWORKS[:4], rows, p=[0.5, 0.35, 0.1, 0.05]),
            "card_type": rng.choice(CARD_TYPES[:2], rows, p=[0.65, 0.35]),
            "distance": distance,
            "identity_present": identity,
            "is_fraud": labels,
            "account_id": [f"SYN-A-{i % 200:04}" for i in range(rows)],
            "device_type": rng.choice(["desktop", "mobile", "unknown"], rows, p=[0.45, 0.3, 0.25]),
            "payer_email_domain": rng.choice(["gmail.com", "yahoo.com", "outlook.com", None], rows),
            "receiver_email_domain": rng.choice(["gmail.com", "yahoo.com", None], rows),
        }
    )


def import_ieee(folder):
    folder = Path(folder)
    columns = (
        [
            "TransactionID",
            "TransactionDT",
            "TransactionAmt",
            "ProductCD",
            "card4",
            "card6",
            "dist1",
            "isFraud",
            "card1",
            "card2",
            "card3",
            "card5",
            "addr1",
            "addr2",
            "P_emaildomain",
            "R_emaildomain",
        ]
        + ANON_NUMERIC
        + MATCH_FIELDS
    )
    tx = pd.read_csv(folder / "train_transaction.csv", usecols=columns)
    identity = pd.read_csv(folder / "train_identity.csv", usecols=["TransactionID", "DeviceType"])
    joined = tx.merge(
        identity.assign(identity_present=True), on="TransactionID", how="left", validate="one_to_one"
    )
    frame = joined.rename(
        columns=dict(
            zip(
                columns[:8],
                [
                    "transaction_id",
                    "time_offset",
                    "amount",
                    "product",
                    "network",
                    "card_type",
                    "distance",
                    "is_fraud",
                ],
                strict=True,
            )
        )
    )
    frame["transaction_id"] = frame.transaction_id.astype(str)
    frame["network"] = frame.network.where(frame.network.isin(NETWORKS), "unknown")
    frame["card_type"] = frame.card_type.where(frame.card_type.isin(CARD_TYPES), "unknown")
    frame["identity_present"] = frame.identity_present.eq(True)
    keys = (
        frame[["card1", "card2", "card3", "card5", "addr1"]]
        .fillna(-1)
        .astype(int)
        .astype(str)
        .agg("_".join, axis=1)
    )
    frame["account_id"] = keys.map(lambda value: hashlib.blake2b(value.encode(), digest_size=12).hexdigest())
    frame["device_type"] = frame.DeviceType.fillna("unknown")
    frame["payer_email_domain"] = frame.P_emaildomain
    frame["receiver_email_domain"] = frame.R_emaildomain
    frame["address_region"] = frame.addr2
    frame["issuer_region"] = frame.card3
    frame = frame.drop(
        columns=[
            "card1",
            "card2",
            "card3",
            "card5",
            "addr1",
            "addr2",
            "P_emaildomain",
            "R_emaildomain",
            "DeviceType",
        ]
    )
    return validate(frame)


def features(records, names=None):
    frame = pd.DataFrame(records).copy()
    hour = (frame.time_offset % 86400) / 3600
    result = pd.DataFrame(
        {
            "log_amount": np.log1p(frame.amount),
            "hour_sin": np.sin(hour * np.pi / 12),
            "hour_cos": np.cos(hour * np.pi / 12),
            "product": frame["product"].map({v: i for i, v in enumerate(PRODUCTS)}),
            "network": frame.network.map({v: i for i, v in enumerate(NETWORKS)}),
            "card_type": frame.card_type.map({v: i for i, v in enumerate(CARD_TYPES)}),
            "log_distance": np.log1p(frame.distance.astype(float).fillna(0)),
            "distance_missing": frame.distance.isna().astype(int),
            "identity_present": frame.identity_present.astype(int),
        }
    )
    for name in HISTORY_FEATURES:
        default = 1 if name == "amount_ratio_7d" else -1 if name == "seconds_since_previous" else 0
        result[name] = pd.to_numeric(
            frame.get(name, pd.Series(default, index=frame.index)), errors="coerce"
        ).fillna(default)
    result["device_type"] = (
        frame.get("device_type", pd.Series("unknown", index=frame.index))
        .map({"desktop": 0, "mobile": 1, "unknown": 2})
        .fillna(2)
    )
    domains = []
    for field, output in [
        ("payer_email_domain", "payer_domain_bucket"),
        ("receiver_email_domain", "receiver_domain_bucket"),
    ]:
        series = frame.get(field, pd.Series("", index=frame.index)).fillna("").astype(str).str.lower()
        domains.append(series)
        result[output] = series.map(
            lambda value: (
                1 + int.from_bytes(hashlib.blake2b(value.encode(), digest_size=2).digest(), "little") % 63
                if value
                else 0
            )
        )
    result["email_domain_mismatch"] = np.where(
        (domains[0] != "") & (domains[1] != ""), (domains[0] != domains[1]).astype(int), -1
    )
    for name in ["address_region", "issuer_region", *ANON_NUMERIC]:
        result[name] = pd.to_numeric(
            frame.get(name, pd.Series(-1, index=frame.index)), errors="coerce"
        ).fillna(-1)
    for name in MATCH_FIELDS:
        values = frame.get(name, pd.Series(None, index=frame.index))
        result[name] = values.map({"T": 1, "F": 0, 1: 1, 0: 0}).fillna(-1)
    if result.isna().any().any() or not np.isfinite(result.to_numpy()).all():
        raise ValueError("Invalid or unknown feature values")
    return result[names or FEATURES].astype("float32")


def add_history(frame):
    return pd.concat([frame, history_features(frame)], axis=1)


def split_time(frame):
    # Split by distinct timestamps so equal-time transactions never cross a boundary.
    times = np.sort(frame.time_offset.unique())
    if len(times) < 20:
        raise ValueError("Need at least 20 distinct timestamps")
    edges = [times[int(len(times) * p)] for p in [0.55, 0.7, 0.85]]
    groups = [
        frame[frame.time_offset < edges[0]],
        frame[(frame.time_offset >= edges[0]) & (frame.time_offset < edges[1])],
        frame[(frame.time_offset >= edges[1]) & (frame.time_offset < edges[2])],
        frame[frame.time_offset >= edges[2]],
    ]
    if any(g.is_fraud.nunique() < 2 for g in groups):
        raise ValueError("Every chronological interval must contain both classes; use more data")
    return groups


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
