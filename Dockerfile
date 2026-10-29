# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder
RUN pip install --no-cache-dir uv==0.8.15
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies first, so this layer is cached until uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim
RUN useradd --create-home --uid 1000 app && mkdir /work && chown app:app /work
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONUNBUFFERED=1
USER app
WORKDIR /work
ENTRYPOINT ["polar-hrv-viz"]
CMD ["--help"]
