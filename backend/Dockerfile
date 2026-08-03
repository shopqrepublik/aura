FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY scripts/ scripts/

# Bakes .reference_cache/ (already-resized, ~50-100KB per work) into the
# image at build time, so the deployed container never does a live
# Wikimedia fetch on the request hot path. Needs the thumbnail-first fetch
# fix in app/main.py (_fetch_reference_image_b64) to already be in place —
# without it, this would bake in whatever a slow/huge original download
# produces, bloating the image instead of shrinking the runtime risk.
RUN python scripts/warm_reference_cache.py

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
