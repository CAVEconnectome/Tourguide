FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.6.1 /uv /uvx /bin/

RUN apt-get update && apt-get install -y gcc

ENV GIT_SSL_NO_VERIFY=1

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_DOWNLOADS=0

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

RUN mkdir -p /root/.cloudvolume/secrets

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-default-groups

ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []

CMD ["uv", "run", "--with", "gunicorn==23.0.0", "--no-default-groups", "gunicorn", "--workers=2", "run:app"]