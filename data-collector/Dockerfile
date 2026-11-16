# syntax=docker/dockerfile:1

# ---- build: resolve and install into /app/.venv with uv ----
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first, so this layer is cached until pyproject.toml changes.
# uv.lock is not kept in the repository: uv resolves and writes it here, at build time.
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-editable

# ---- runtime: same Python, no uv, non-root ----
FROM python:3.13-slim-bookworm

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --no-create-home app \
    && mkdir /data \
    && chown app:app /data

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

USER app
VOLUME ["/data"]

CMD ["air-quality-collector"]
