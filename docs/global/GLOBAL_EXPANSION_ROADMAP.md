# Global Expansion Roadmap

Status: PROPOSED sequence.

## Phase 0 — documentation baseline

Outputs: canonical docs, current evidence, definitions, hardcode audit, National Gallery paper test. Exit: links/tests/paths validated; old audit historical; production source discrepancy explicitly owned.

## Phase 1 — remove P0 global blockers

Work: integrate production history into reviewed mainline; embed Git SHA; add migration framework; country/institution baseline; harden/version event ingestion and trusted QA/identity. Exit: clean deploy from main, reproducible schema, metrics cannot be trivially spoofed, institution has country/timezone/default locales.

## Phase 2 — second-country museum

Use National Gallery London as controlled pilot after source/rights agreement. Build generic source adapter contract, media provenance, DB-backed visitor catalog/recognition profile, English/UK policy content and benchmark. Exit: onboard/activate/deactivate without named backend branch; wrong-museum/confident-wrong gates pass; admin metrics trustworthy.

## Phase 3 — multi-country repeatability

Onboard a third institution with a different source and visitor language. Add collection/holding/location only where demonstrated. Exit: no new core code for ordinary onboarding; locale/currency/legal policy comes from configuration/content packages.

## Phase 4 — institution tooling

Add scoped roles, provenance/readiness workflow, imports/diffs, benchmark approval and catalog activation in admin. Exit: institution operator cannot access another institution; every activation is audited and reversible.

## Phase 5 — automation and scale

Introduce event batching/retention/rollups, indexed recognition retrieval, asset/object storage/CDN policy, cost attribution, SLOs/alerts and capacity tests. Exit: Scenario B load targets measured; Scenario C architecture decisions based on evidence, not speculative microservices.
