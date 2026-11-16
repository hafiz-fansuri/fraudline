import os

from sqlalchemy import text

from fraudline.monitor import demo_reports
from fraudline.pipeline import ART, prepare, registry, sync_mlflow_aliases, train
from fraudline.store import Store

store = Store(os.environ["DATABASE_URL"])
password = os.environ["AUDIT_PASSWORD"]
if not password.isalnum():
    raise ValueError("Use a generated alphanumeric local audit password")
with store.engine.begin() as conn:
    exists = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname='scoring_writer'")).first()
    if not exists:
        conn.execute(text(f"CREATE ROLE scoring_writer LOGIN PASSWORD '{password}'"))
    conn.execute(text("GRANT USAGE ON SCHEMA public TO scoring_writer"))
    conn.execute(text("GRANT SELECT, INSERT ON scoring_events TO scoring_writer"))
    conn.execute(text("GRANT SELECT, UPDATE ON audit_head TO scoring_writer"))
    conn.execute(text("GRANT SELECT ON labels TO scoring_writer"))
if not (ART / "registry.json").exists():
    prepare()
    train()
sync_mlflow_aliases(registry())
demo_reports()
