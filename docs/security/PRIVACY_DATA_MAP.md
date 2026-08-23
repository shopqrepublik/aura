# Privacy Data Map

Status: CURRENT technical behavior; not legal advice.

| Data | Source | Storage/transit | Retention known? | Notes |
|---|---|---|---|---|
| Visitor scan image | Camera/file input | Browser base64; HTTPS to FastAPI; sent to OpenAI | Browser: until visit overwritten/cleared where retained; provider: UNKNOWN | Not stored in product DB by recognition code; failed network image is persisted for retry. |
| Presentation/reference derivative | Public providers | Browser/CDN/backend filesystem cache | Cache TTL/code known; provider lifecycle unknown | Public catalog media, separate from visitor image. |
| Anonymous ID | Browser | localStorage; product_events/PostHog | No deletion/TTL policy in code | Random, persistent per origin; still pseudonymous. |
| Session ID | Browser | sessionStorage; product_events | Browser tab lifetime; DB raw-event retention undefined | Not inactivity-based. |
| Supabase user | Auth | Supabase + local `users` email/provider | Provider/app retention undefined | First-party events do not currently link user_id. |
| Product events | Explicit client/backend | PostgreSQL `product_events`, PostHog client copy | No DB TTL/partition/purge; PostHog UNKNOWN | Includes path/referrer/UTM/language/device/OS/browser/user-agent and product IDs. |
| IP | HTTP infrastructure; admin login | Only peppered SHA-256 hash stored for admin login by app | No cleanup policy | Product events do not store IP; provider logs unknown. |
| Geo | Browser geolocation | Used client-side for museum choice | No coordinates intentionally put in events | Selected museum is stored; country/city event columns usually empty. |
| Admin session | Login | Hashed token, email, hashed IP, user-agent, times | Expiry seven days; rows not automatically purged | Cookie contains raw random token, HttpOnly/Secure. |
| Recognition telemetry | Client/server | product_events and operational logs | No DB/log policy | Client has identity/correlation; server is identityless. Raw image not intentionally logged. |

## Successful versus failed images

On successful catalog recognition, a trusted presentation image remains primary; if absent, the capture may become private visitor hero and be persisted in local visit JSON. Uncataloged results use capture as hero. On network failure, pending capture is persisted for retry. Pure no-match clears pending capture. Backend code processes image in memory and forwards it to OpenAI; it does not insert raw bytes into DB/event rows.

## Internal/QA

QA marker is session-local and client-asserted. Admin excludes marked events, but the rows remain stored. QA images follow the same recognition/provider path as visitor images.

## Required policy decisions

Define browser capture TTL/clear action, PostgreSQL raw-event retention/deletion/export, admin-log retention, provider data processing/regions, authenticated identity merge/deletion, backups and DSAR operational ownership. Do not infer legal compliance from absence of a DB image column.
