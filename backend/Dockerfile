FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY scripts/ scripts/

# Reference cache warming is an operational step, not required to build the
# app image. Keeping it out of Docker build avoids deployment-time network
# fetches; runtime verification still uses the same safe thumbnail-first
# cache path in app/main.py.

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
