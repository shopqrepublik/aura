# Museum Factory V1

The factory is a provider-neutral sequence over the existing institution,
ingestion, media, RecognitionAsset and descriptor contracts:

`institution config -> official snapshot -> DISCOVER/DRY_RUN/PLAN -> APPLY -> readiness -> controlled selection -> RecognitionAssets/descriptors -> short benchmark -> controlled preview -> phone smoke -> public activation`

The first profile is `backend/data/onboarding/rijksmuseum_amsterdam/config.json`.
It uses the official Rijksmuseum Search API for painting discovery, the Linked
Data resolver for metadata and official IIIF access points for reference media.
The normalized snapshot is consumed by `JsonFileAdapter`; no museum-specific
tables or recognition paths are introduced.

## New museum checklist

1. Add institution profile and official endpoints.
2. Add or configure a source adapter only when normalization differs.
3. Discover and reconcile official records.
4. Run generic ingestion in DISCOVER, DRY_RUN, PLAN, then audited APPLY.
5. Map media and apply readiness gates.
6. Select a deterministic representative image-backed tranche.
7. Generate RecognitionAssets and versioned visual descriptors.
8. Run the short known/confusion/hard-negative benchmark.
9. Activate controlled preview only when P0 safety gates pass.
10. Perform trusted phone smoke; public activation is a separate decision.

National Gallery remains unchanged at 2,000 controlled works.
