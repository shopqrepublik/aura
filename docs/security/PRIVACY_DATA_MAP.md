# Privacy Data Map

Status: CURRENT technical behavior; not legal advice.

| Data | Source | Storage/transit | Retention known? | Notes |
|---|---|---|---|---|
| Visitor scan image | Camera/file input | Browser base64; HTTPS to FastAPI; sent to OpenAI | Browser: until visit overwritten/cleared where retained; provider: UNKNOWN | Not stored in product DB by recognition code; failed network image is persisted for retry. |
| Presentation/reference derivative | Public providers | Browser/CDN/backend filesystem cache | Cache TTL/code known; provider lifecycle unknown | Public catalog media, separate from visitor image. |
| Anonymous ID | Browser | localStorage; product_events, attempts, identity links, PostHog | No deletion/TTL policy in code | Validated random UUID, persistent per origin; pseudonymous, not authentication. |
| Session ID | Browser | sessionStorage; product_events, attempts, analytics_sessions | Browser tab lifetime; DB retention undefined | UUID fixed server-side to identity context; not inactivity-based. |
| Supabase user | Auth | Supabase + local `users`; verified ID in analytics/attempts and identity link | Provider/app retention undefined | Browser cannot submit arbitrary user ID; historical anonymous rows remain immutable. |
| Product events | Explicit client/backend | PostgreSQL `product_events`, PostHog client copy | No DB TTL/partition/purge; PostHog UNKNOWN | Bounded acquisition/device/path fields; server time/trust/QA classification. |
| IP | HTTP infrastructure; admin login | Only peppered SHA-256 hash stored for admin login by app | No cleanup policy | Product events do not store IP; provider logs unknown. |
| Geo | Browser geolocation | Used client-side for museum choice | No coordinates intentionally put in events | Selected museum is stored; country/city event columns usually empty. |
| Admin session | Login | Hashed token, email, hashed IP, user-agent, times | Expiry seven days; rows not automatically purged | Cookie contains raw random token, HttpOnly/Secure. |
| Recognition telemetry | Client/server | `recognition_attempts`, product_events and logs | No DB/log policy | One pseudonymous/user/session-linked attempt; response metadata retained, raw image not inserted. |

## Successful versus failed images

On successful catalog recognition, a trusted presentation image remains primary; if absent, the capture may become private visitor hero and be persisted in local visit JSON. Uncataloged results use capture as hero. On network failure, pending capture is persisted for retry. Pure no-match clears pending capture. Backend code processes image in memory and forwards it to OpenAI; it does not insert raw bytes into DB/event rows.

## Internal/QA

QA marker is assigned only when the server validates the secret QA header. Controlled tooling may hold the token in sessionStorage for that browser session; it is not bundled or accepted from query/properties. Admin retains QA rows operationally and excludes them from founder KPIs. QA images follow the same provider path as visitor images.

## Required policy decisions

Define browser capture TTL/clear action, PostgreSQL raw-event retention/deletion/export, admin-log retention, provider data processing/regions, authenticated identity merge/deletion, backups and DSAR operational ownership. Do not infer legal compliance from absence of a DB image column.
