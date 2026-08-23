# Production Smoke Test

Status: CURRENT checklist. Controlled tooling must supply the secret `X-ELYIO-QA-Token` context; query parameters or event properties cannot mark traffic internal.

## Read-only baseline

- [ ] Record Git source, Vercel deployment ID and Fly release/image.
- [ ] `GET /health` 200.
- [ ] OpenAPI includes public, visit, event and admin paths.
- [ ] `/admin` 200/noindex; unauthenticated `/v1/admin/me` 401.
- [ ] Production DB expected migrations exist; do not print secrets/data rows.

## Visitor

- [ ] Open `/visit` in a controlled browser with `elyio-trusted-qa-token` set in sessionStorage by authorized tooling (never print or bundle the token).
- [ ] Anonymous/session IDs are created; no credentials required.
- [ ] Select museum/start visit/camera capture.
- [ ] Known catalog result resolves with correct museum/artwork and stable image role.
- [ ] No-match and network failure do not count.
- [ ] Repeat stable work counts once.
- [ ] Favorite, mission, achievement, Progress and Recap agree.
- [ ] Trophy renders 1080×1920; save/share works.

## Recognition

- [ ] Match fixture, decoy, wrong museum, uncataloged and non-art image.
- [ ] No cross-museum candidate IDs.
- [ ] Response mode/status/confidence reviewed.
- [ ] Browser events share `recognition_attempt_id`.
- [ ] The recognition request/response and `recognition_attempts` row share that ID and one terminal outcome.

## Analytics/admin

- [ ] QA rows carry server-owned `internal_test=true`; a public `properties.internal_test=true` spoof remains false.
- [ ] Duplicate same `event_id` is not stored twice (use non-production test where possible).
- [ ] Unsupported names, user/timestamp spoof, invalid dimensions and oversized payloads are rejected/neutralized; do not load-test production.
- [ ] Authorized dashboard loads; data gaps remain visible.
- [ ] QA user does not change Active/Activation/Funnel.
- [ ] Attempt/success/failure counts derive from unique attempt rows, not companion events.
- [ ] Failure export does not expose images.

## SEO/PWA

- [ ] Locale home/museum/artwork 200 with canonical/hreflang.
- [ ] sitemap/robots counts valid; `/admin`, `/visit`, previews excluded.
- [ ] manifest/SW/icons 200; update/offline boundaries understood.
- [ ] Physical iOS/Android install/share test remains required before launch sign-off.
