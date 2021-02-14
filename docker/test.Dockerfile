FROM python:3.9.1

WORKDIR /app

RUN pip install poetry

COPY . .
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi
