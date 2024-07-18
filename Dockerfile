FROM python:3.9 AS backend

ARG APP_ENVIRONMENT=development

ENV APP_ENVIRONMENT=${APP_ENVIRONMENT} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    PYTHONPATH=/app/src \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR='/pypoetry' \
    PATH="${PATH}:/root/.local/bin"

WORKDIR /app

COPY poetry.lock ./
COPY pyproject.toml ./

RUN curl -sSL https://install.python-poetry.org | python3 - && \
  poetry config virtualenvs.create false && \
  poetry install $([ "$APP_ENVIRONMENT" = 'production' ] && echo "--no-dev") --no-interaction --no-ansi

COPY . ./
