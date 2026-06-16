FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EIDOLON_PROJECT_ROOT=/app

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY configs/ ./configs/

RUN python -m pip install --upgrade pip && \
    python -m pip install ".[ml,api,osint]" && \
    mkdir -p artifacts artifacts/models

EXPOSE 8000

CMD ["python", "-m", "eidolon", "serve", "--host", "0.0.0.0"]
