# Acquisition V1 integration

The web app preserves GA4 and PostHog and additionally sends bounded,
failure-tolerant funnel envelopes to AGENT's acquisition endpoint. A random
first-party acquisition session is retained for seven days. Publication tokens
are read only from `utm_content` values beginning with `pub_`; no publication
is inferred from a social referrer. Existing product routes and event names
are unchanged, and acquisition delivery never delays navigation.

The backend recognition endpoint accepts an optional acquisition session ID.
At the existing successful recognition boundary it emits one signed,
authoritative `scan_success` envelope to AGENT using the recognition attempt
ID as the stable event identity. The envelope contains no image, provider
payload, location, or user identity. Missing or failed acquisition delivery
does not change recognition success.

AGENT is the canonical acquisition linkage store; GA4 and PostHog remain
corroborating analytics providers. Analytics 3B is unchanged and no automatic
experiment is created for recognition or static-image traffic.
