# economic-data-api.
#
# Long-running FastAPI service. Reads the canonical parquets from the
# shared volume and serves them. The four *_PATH environment variables
# set by compose select online mode over the bundled fixtures.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_FORMAT=json

# curl backs the compose healthcheck against /health.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The app package. uvicorn imports app.main:app from the working
# directory, and GROCERY_FIXTURES_DIR resolves relative to it.
COPY app ./app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
