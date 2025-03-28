FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
RUN apt-get update && apt-get install -y gcc

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

# Install the project's dependencies using the lockfile and settings
WORKDIR /app

# Copy only the necessary files for dependency installation
COPY uv.lock pyproject.toml ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-default-groups

COPY . ./
RUN --mount=type=cache,target=/root/.cache/uv \
uv sync --frozen --no-default-groups

FROM python:3.12-slim-bookworm
COPY --from=builder --chown=root:root /app/.venv /app/.venv
COPY --from=builder --chown=root:root /app/*.py /app/
COPY --from=builder --chown=root:root /app/tourguide /app/tourguide

# Install the project into `/app`
RUN mkdir -p /root/.cloudvolume/secrets

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

CMD ["gunicorn", "--workers=2", "run:app"]