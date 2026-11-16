"""Verify real Postgres permissions and a service-level rollback, then restore the champion."""

import json
import subprocess
import time

import httpx

from fraudline.pipeline import ART, write_json


def in_monitor(code):
    return subprocess.check_output(
        ["docker", "compose", "exec", "-T", "monitor", "python", "-c", code], text=True
    ).strip()


def wait_ready(expected):
    for _ in range(40):
        try:
            response = httpx.get("http://127.0.0.1:8013/ready", timeout=2)
            if response.status_code == 200 and response.json()["model_version"] == expected:
                return
        except httpx.RequestError:
            pass
        time.sleep(0.5)
    raise RuntimeError("API did not become ready with the expected model")


sql = "SELECT has_table_privilege('scoring_writer','scoring_events','INSERT'), has_table_privilege('scoring_writer','scoring_events','UPDATE'), has_table_privilege('scoring_writer','scoring_events','DELETE')"
privileges = in_monitor(
    "import os,json; from sqlalchemy import text; from fraudline.store import Store; s=Store(os.environ['DATABASE_URL']); c=s.engine.connect(); print(json.dumps(list(c.execute(text("
    + repr(sql)
    + ")).one()))); c.close()"
)
assert json.loads(privileges) == [True, False, False]
before = in_monitor("from fraudline.pipeline import registry; print(registry()['champion'])")
previous = in_monitor("from fraudline.pipeline import registry; print(registry()['previous'])")
assert previous != "None" and previous != before
try:
    rolled_back = in_monitor("from fraudline.pipeline import rollback; print(rollback()['champion'])")
    assert rolled_back == previous
    subprocess.run(["docker", "compose", "restart", "api"], check=True)
    wait_ready(previous)
finally:
    current = in_monitor("from fraudline.pipeline import registry; print(registry()['champion'])")
    if current != before:
        restored = in_monitor("from fraudline.pipeline import rollback; print(rollback()['champion'])")
        assert restored == before
        subprocess.run(["docker", "compose", "restart", "api"], check=True)
wait_ready(before)
result = {
    "audit_privileges": {"insert": True, "update": False, "delete": False},
    "original_champion": before,
    "verified_rollback_version": previous,
    "restored_champion": before,
    "service_readiness_verified_after_each_restart": True,
}
write_json(ART / "reports/rollback-demo.json", result)
print(json.dumps(result, indent=2))
