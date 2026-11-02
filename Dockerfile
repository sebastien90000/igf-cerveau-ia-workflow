FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy application code
COPY src ./src

# DEPLOYMENT_NAME may be passed as a build arg by the platform
ARG DEPLOYMENT_NAME
ENV DEPLOYMENT_NAME=${DEPLOYMENT_NAME}

CMD ["uv", "run", "--no-sync", "python", "src/entrypoints/worker.py"]
