FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

LABEL authors="Muhammed"

WORKDIR /app
RUN pip install poetry --no-cache-dir &&  \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root

COPY . .

EXPOSE 8500
EXPOSE 3005

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8500"]