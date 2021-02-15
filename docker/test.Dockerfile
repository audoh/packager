FROM python:3.9.1

RUN pip install poetry

WORKDIR /app
ENV PYTHONPATH=/app

# Install packages
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi

# Copy code
COPY . .
