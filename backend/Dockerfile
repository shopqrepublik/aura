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
# Frozen metadata-only inputs required by the explicit controlled-preview
# provisioner. Generated image/benchmark binaries remain outside the image.
COPY data/onboarding/national_gallery_london/config.json data/onboarding/national_gallery_london/config.json
COPY data/onboarding/national_gallery_london/pre_eminent_review_snapshot_2026-08-23.json data/onboarding/national_gallery_london/pre_eminent_review_snapshot_2026-08-23.json
COPY data/onboarding/national_gallery_london/source_snapshot_2026-08-23.json data/onboarding/national_gallery_london/source_snapshot_2026-08-23.json
COPY data/onboarding/national_gallery_london/controlled_catalog_500_v1.json data/onboarding/national_gallery_london/controlled_catalog_500_v1.json
COPY data/onboarding/national_gallery_london/controlled_catalog_500_recognition_readiness_v1.json data/onboarding/national_gallery_london/controlled_catalog_500_recognition_readiness_v1.json
COPY data/onboarding/national_gallery_london/controlled_catalog_500_visual_descriptors_v1.json data/onboarding/national_gallery_london/controlled_catalog_500_visual_descriptors_v1.json
COPY data/onboarding/national_gallery_london/controlled_catalog_1000_v1.json data/onboarding/national_gallery_london/controlled_catalog_1000_v1.json
COPY data/onboarding/national_gallery_london/controlled_catalog_1000_recognition_readiness_v1.json data/onboarding/national_gallery_london/controlled_catalog_1000_recognition_readiness_v1.json
COPY data/onboarding/national_gallery_london/controlled_catalog_1000_visual_descriptors_v1.json data/onboarding/national_gallery_london/controlled_catalog_1000_visual_descriptors_v1.json
COPY data/onboarding/national_gallery_london/controlled_catalog_2000_v1.json data/onboarding/national_gallery_london/controlled_catalog_2000_v1.json
COPY data/onboarding/national_gallery_london/controlled_catalog_2000_recognition_readiness_v1.json data/onboarding/national_gallery_london/controlled_catalog_2000_recognition_readiness_v1.json
COPY data/onboarding/national_gallery_london/controlled_catalog_2000_visual_descriptors_v1.json data/onboarding/national_gallery_london/controlled_catalog_2000_visual_descriptors_v1.json

# Reference cache warming is an operational step, not required to build the
# app image. Keeping it out of Docker build avoids deployment-time network
# fetches; runtime verification still uses the same safe thumbnail-first
# cache path in app/main.py.

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
