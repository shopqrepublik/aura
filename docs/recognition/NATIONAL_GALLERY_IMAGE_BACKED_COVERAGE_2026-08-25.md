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

No 2,560 recognition-readiness or descriptor package is marked current yet. The host used for this run does not have the image-processing dependency required by the existing corpus/descriptor pipeline, and the 560 new reference bytes were therefore not fabricated or substituted. Controlled membership and runtime activation must remain at 2,000 until a reproducible reference corpus and descriptor manifest are generated and parity-tested.

Metadata-only holdings remain inactive and are not converted into `VISION_PLUS_ASSET`.
