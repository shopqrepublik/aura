# Security Architecture

Status: CURRENT code audit; not a penetration test.

## Controls

- Visitor account APIs verify Supabase ES256 JWTs via JWKS and require `sub`.
- Admin APIs use server-side DB sessions, random bearer cookie, hashed token, expiry/revocation and login throttling.
- Admin cookie is HttpOnly/Secure production/SameSite=Lax; `www` and `api` are same-site subdomains.
- CORS credentials are restricted to production/apex/Vercel/local origins.
- CSP, HSTS, frame denial, no-sniff, referrer policy and preview/admin noindex are configured.
- Recognition validates base64 size; image proxy validates allowed host/width.
- Secrets are environment variables; values are excluded from docs.

## Findings

| Severity | Finding/evidence | Consequence | Action |
|---|---|---|---|
| CRITICAL | No confirmed critical vulnerability in this source audit | — | Continue independent security testing. |
| HIGH | Public `/v1/events` accepts arbitrary event names, identities, client timestamps/properties and client-controlled `internal_test`; no auth/signature/rate limit | Metric poisoning, identity spoofing, DB/storage abuse | Event allowlist/schema/version, size/time bounds, trusted identity/QA, rate control |
| HIGH | Admin code has fallback email/password hash and default IP pepper | Misconfigured production can activate source-known defaults; weak pseudonymization | Fail startup/login closed unless strong env values exist; rotate and remove defaults |
| MEDIUM | Admin is single credential, no MFA/RBAC/audit-action log | Credential compromise gives global read/export access | IdP/MFA and scoped roles/audit log |
| MEDIUM | Login throttle is DB count only; successful attempts do not clear old failures and no global edge control | Distributed abuse/DoS remains possible | Edge/IP/account backoff, cleanup and alerts |
| MEDIUM | Recognition/value public AI endpoints have no app limiter | Cost/availability abuse | Measured quotas, body limits, abuse monitoring |
| MEDIUM | Visitor capture resides in localStorage and transits OpenAI | XSS/quota/retention exposure | IndexedDB/TTL/clear UI, provider retention review |
| MEDIUM | CSP requires `unsafe-inline`; visitor state is origin-readable | XSS impact remains high | Nonce/hash CSP and dependency review |
| LOW | Admin cookie lacks explicit Domain (host-only API cookie) and CSRF token | SameSite=Lax plus JSON/CORS reduces risk; state-changing logout/login still depend on browser rules | Document/test CSRF; add Origin validation/CSRF defense for future admin mutations |
| LOW | Expired/revoked admin sessions and login attempts have no cleanup job | Table growth/operational exposure | Retention job and indices/monitoring |
| INFO | Admin route is public HTML but data is server-protected and noindex | Expected architecture | Preserve server authorization. |

## Public APIs

Recognition, value, directory, artwork and image proxy are anonymous. Visit persistence requires Supabase bearer. Event ingestion is anonymous. Admin login/logout are public entry actions; all dashboard/read/export paths require `require_admin`.

## Unknowns

Provider WAF/rate limits, database RLS/network controls, secret rotation cadence, dependency scanning, backups, OpenAI/PostHog/Supabase/Vercel/Fly log retention and incident response were not verified.
