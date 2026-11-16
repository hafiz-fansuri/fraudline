FROM python:3.13-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
ENV PATH="/app/.venv/bin:$PATH" FRAUDLINE_HOME=/app PYTHONUNBUFFERED=1

FROM base AS operations
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --extra ops --no-dev --no-install-project
COPY fraudline ./fraudline
COPY scripts ./scripts
CMD ["python", "-m", "fraudline.pipeline", "demo"]

FROM base AS runtime
RUN useradd --create-home --uid 10001 app && mkdir -p /app/artifacts /app/runtime && chown app:app /app/artifacts /app/runtime
COPY fraudline ./fraudline
COPY scripts ./scripts
COPY --chown=app:app demo-bundle/ /app/artifacts/
USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn fraudline.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
