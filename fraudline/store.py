"""Append-only scoring events. Hash links are tamper evidence, not administrator-proof immutability."""

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    event,
    select,
    update,
)

metadata = MetaData()
head = Table("audit_head", metadata, Column("id", Integer, primary_key=True), Column("digest", String(64)))
events = Table(
    "scoring_events",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("at", String),
    Column("payload", Text),
    Column("digest", String(64)),
)
labels = Table(
    "labels",
    metadata,
    Column("prediction_id", String(36), primary_key=True),
    Column("is_fraud", Integer),
    Column("received_at", String),
)


class Store:
    def __init__(self, url):
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(url, pool_pre_ping=True)
        self.lock = threading.Lock()
        if self.engine.dialect.name == "sqlite":

            @event.listens_for(self.engine, "connect")
            def sqlite_config(conn, _):
                conn.execute("PRAGMA busy_timeout=10000")
                conn.isolation_level = None

            @event.listens_for(self.engine, "begin")
            def sqlite_begin(conn):
                conn.exec_driver_sql("BEGIN IMMEDIATE")

        metadata.create_all(self.engine)
        with self.engine.begin() as conn:
            if conn.execute(select(head)).first() is None:
                conn.execute(head.insert().values(id=1, digest="0" * 64))

    def append(self, request, prediction):
        event_id = str(uuid.uuid4())
        clean = {key: value for key, value in request.items() if key != "transaction_id"}
        payload = json.dumps(
            {
                "inputs_hash": hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest(),
                "features": clean,
                "prediction": prediction,
            },
            sort_keys=True,
            allow_nan=False,
        )
        at = datetime.now(timezone.utc).isoformat()
        with self.lock, self.engine.begin() as conn:
            previous = conn.execute(
                select(head.c.digest).where(head.c.id == 1).with_for_update()
            ).scalar_one()
            digest = hashlib.sha256((previous + event_id + at + payload).encode()).hexdigest()
            conn.execute(events.insert().values(id=event_id, at=at, payload=payload, digest=digest))
            conn.execute(update(head).where(head.c.id == 1).values(digest=digest))
        return event_id

    def recent(self, limit=1000):
        with self.engine.connect() as conn:
            rows = conn.execute(select(events).order_by(events.c.at.desc()).limit(limit)).mappings().all()
        return [{**dict(row), **json.loads(row["payload"])} for row in reversed(rows)]

    def add_label(self, prediction_id, is_fraud):
        if is_fraud not in [0, 1]:
            raise ValueError("Label must be 0 or 1")
        with self.engine.begin() as conn:
            if conn.execute(select(events.c.id).where(events.c.id == prediction_id)).first() is None:
                raise ValueError("Unknown prediction ID")
            conn.execute(
                labels.insert().values(
                    prediction_id=prediction_id,
                    is_fraud=is_fraud,
                    received_at=datetime.now(timezone.utc).isoformat(),
                )
            )

    def performance(self):
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(events.c.payload, labels.c.is_fraud).join(
                    labels, labels.c.prediction_id == events.c.id
                )
            ).all()
        if len(rows) < 30 or len({r.is_fraud for r in rows}) < 2:
            return {"status": "insufficient_labels", "labeled_rows": len(rows)}
        from sklearn.metrics import average_precision_score, brier_score_loss

        y = [r.is_fraud for r in rows]
        p = [json.loads(r.payload)["prediction"]["probability"] for r in rows]
        return {
            "status": "ready",
            "labeled_rows": len(rows),
            "pr_auc": float(average_precision_score(y, p)),
            "brier": float(brier_score_loss(y, p)),
        }
