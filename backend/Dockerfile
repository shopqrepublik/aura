FROM python:3.11-slim

ARG GIT_COMMIT_SHA=unknown
ARG BUILD_TIMESTAMP=unknown
ARG DEPLOYMENT_ENV=production
ENV GIT_COMMIT_SHA=${GIT_COMMIT_SHA} \
    BUILD_TIMESTAMP=${BUILD_TIMESTAMP} \
    DEPLOYMENT_ENV=${DEPLOYMENT_ENV}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY scripts/ scripts/
COPY migrations/ migrations/

# Reference cache warming is an operational step, not required to build the
# app image. Keeping it out of Docker build avoids deployment-time network
# fetches; runtime verification still uses the same safe thumbnail-first
# cache path in app/main.py.

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
