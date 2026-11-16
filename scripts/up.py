import secrets
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = root / ".env"
if not env.exists():
    env.write_text(
        "\n".join(
            f"{key}={secrets.token_hex(24)}"
            for key in ["POSTGRES_PASSWORD", "AUDIT_PASSWORD", "GRAFANA_PASSWORD"]
        )
        + "\n"
    )
subprocess.run(["docker", "compose", "up", "--build", "-d"], cwd=root, check=True)
print("Fraudline: http://localhost:8013 | MLflow: http://localhost:5013 | Grafana: http://localhost:3013")
print("Local-only passwords are in the ignored .env file. Startup training can take a few minutes.")
