# National Gallery London — image-backed coverage audit (2026-08-25)

Status: controlled-preview preparation; not public activation.

The frozen official snapshot contains 3,785 object records. Reconciliation against `controlled_catalog_2000_v1.json` finds:

| Cohort | Count |
| --- | ---: |
| Existing controlled image-backed works | 2,000 |
| Remaining records declaring image relationships | 566 |
| Remaining technically excluded media records | 6 |
| Remaining image-backed candidates after exclusions | 560 |
| Remaining metadata-only records | 1,219 |

The six exclusions remain explicit in `media_technical_exclusions_v1.json` (three HTTP 403 and three HTTP 404 provider derivative failures). A deterministic 2,560-work selection and benchmark manifest are prepared in:

- `controlled_catalog_2560_v1.json`
- `controlled_catalog_2560_benchmark_samples_v1.json`

The canonical backend environment is Python 3.11 from `backend/Dockerfile` with the pinned `requirements.txt`. The local default Python 3.14 installation was malformed (`logging` resolved as an incomplete namespace package); it was not modified. An isolated Python 3.11 environment restored Pillow 12.3.0, standard-library logging, derivative generation, checksums and 456-value descriptors.

The acquisition produced 559 READY references and one additional HTTP 403 (`0IAJ-0001-0000-0000`, media `0VEC-000B-0000-0000`). The valid package is therefore 2,559 works, not 2,560. The generated package is:

- `controlled_catalog_2559_v1.json`
- `controlled_catalog_2559_recognition_readiness_v1.json`
- `controlled_catalog_2559_visual_descriptors_v1.json`
- `controlled_catalog_2559_reference_audit_v1.json`

The 559-reference audit found 507 strong and 52 low-resolution-but-usable references, with zero contextual/wrong references and zero duplicate checksums. Production controlled membership and runtime activation remain at 2,000 until the OpenAI-backed recognition benchmark and all safety gates are run.

Metadata-only holdings remain inactive and are not converted into `VISION_PLUS_ASSET`.
