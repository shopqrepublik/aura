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

Wave 1 representative-price verification now has 15 production-eligible
records, including the three Kids launch references and Paris/London/New York
city rows required by the launch matrix. Remaining records are either
`NEEDS_DECISION` or `REVIEW_REQUIRED` pending an acceptable source/basis and
localized labels. Production-eligible monetary references: **15** of 59.

The supplied remote pack contains seven `REVIEW_REQUIRED` records with blank
required sources. It is invalid for production and is rejected by the loader.

The Normal, Simple, Kids, Paris, London, New York, and no-city launch gates
are now satisfied. V2.2 is enabled behind the production feature flag; the
remote meme pack remains disabled and independently fail-closed.
