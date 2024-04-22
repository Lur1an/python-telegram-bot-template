FROM ghcr.io/pyo3/maturin as maturinbuilder
COPY rustlib rustlib
RUN mv rustlib/* .
# FROM python:3.11-buster as builder
FROM rust:latest as builder
RUN apt-get update && apt-get install -y musl-tools

RUN pip install poetry==1.8.2

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./
COPY rustlib ./rustlib
RUN touch README.md

RUN poetry install --only main --no-root && rm -rf $POETRY_CACHE_DIR
COPY --from=maturinbuilder /io/dist/wheels/* .
RUN wheel=$(find . -name "*.whl" | head -n 1)
RUN pip install "$wheel"

# The runtime image, used to just run the code provided its virtual environment
FROM python:3.11-slim-buster as runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY src ./src
COPY entrypoint.sh ./
COPY alembic.ini ./
COPY migrations ./migrations
RUN mkdir /data # Directory to mount volume for database

RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
