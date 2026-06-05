# Backend image: install deps, then run migrations and serve with uvicorn.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8000

# Apply migrations, optionally seed an empty DB (SEED_ON_STARTUP), then start the API.
# The DATABASE_URL env selects the engine.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed.bootstrap && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
