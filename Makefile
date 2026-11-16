.PHONY: up down demo test train rollback monitor
up:
	python scripts/up.py
down:
	docker compose down
demo:
	uv run python -m fraudline.pipeline demo
	uv run python -m fraudline.monitor --demo
	uv run uvicorn fraudline.api:app --host 127.0.0.1 --port 8012
test:
	uv run --extra dev pytest --cov=fraudline --cov-report=term-missing
train:
	uv run --extra ops python -m fraudline.pipeline train --tune
rollback:
	uv run python -m fraudline.pipeline rollback
	docker compose restart api
monitor:
	uv run --extra ops python -m fraudline.monitor --retrain
