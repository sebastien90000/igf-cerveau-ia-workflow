FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY *.py ./

ARG DEPLOYMENT_NAME
ENV DEPLOYMENT_NAME=${DEPLOYMENT_NAME}

CMD ["uv", "run", "--no-sync", "python", "worker.py"]
