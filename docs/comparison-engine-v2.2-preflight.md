# Comparison Engine V2.2 production preflight

Date: 2026-09-04

## Decisions

- Canonical categories remain `luxury`, `food`, `everyday`, `tech`, `pop`,
  `city`, `kids`, and `easter_egg`.
- Migration-only `travel` and `life` values normalize to `everyday`.
- The seven remote IDs are exactly `super_bowl_ad`, `film_budget`,
  `eras_tour_ticket`, `labubu_doll`, `champions_final_ticket`, `bored_ape`,
  and `lebron_james_rookie_card`. `chatgpt_pro_year` and
  `private_chef_year` remain core.
- Production monetary eligibility requires `VERIFIED`, a valid HTTPS source,
  an unexpired `valid_until`, a positive EUR calculation price, a valid ISO
  currency code, and complete EN/FR/zh-Hans labels.
- `REVIEW_REQUIRED`, `STALE`, `UNSOURCED`, expired, invalid, or incompletely
  localized references fail closed.
- Review records can be enabled only in explicit development/test contexts.
- V2.2 cannot create or alter a valuation. It receives only an already eligible
  monetary scale from the existing value-provenance path.

## Current gate result

The supplied core contains 59 `REVIEW_REQUIRED` monetary records with blank
source URLs and incomplete production localization, plus one isolated Easter
egg. Production-eligible monetary references: **0**.

The supplied remote pack contains seven `REVIEW_REQUIRED` records with blank
required sources. It is invalid for production and is rejected by the loader.

Consequently V2.2 is not production-ready. The feature flag defaults to V2.0,
and a V2.2 request automatically falls back to V2.0 until the complete catalog
readiness gate passes.
