# ELYIO — COMPARISON ENGINE V2.2
## VIRAL SCALE COMPARISONS — Architecture + Migration Plan

**Status:** Ready for Codex implementation
**Input:** comparisons_v2.json (67 items) + table as direction, NOT as production truth
**Output:** Deterministic, local, shareable entertainment engine

---

### 0. GOAL

Turn comparisons from `valuation explanation` into `content mechanic`.

User must see comparison and want to show neighbor / send to friend.
Engine remains numerically truthful. NO AI-generated concepts/prices.

### 1. POOL ARCHITECTURE (Fixed)

**Canonical categories:** luxury, food, everyday, tech, pop, city, kids, easter_egg

Migration decision: legacy authoring categories `travel` and `life` are normalized
to `everyday`. They are not production category extensions. This maps
`family_holiday_exceptional` and `university_scholarship` into a reachable
canonical pool.

**NORMAL — Exactly 3 rows:**
A. 1 scale/luxury/major-tech (ferrari, jets, yacht, iphone, rolex, tesla, etc.)
B. 1 food/everyday (big_mac, croissant, coffee, pizza, nutella, etc.)
C. 1 city-specific. If none exists → fallback pop/tech/universal

Avoid duplicate semantics (e.g. not 2x apartments).

**SIMPLE — Exactly 2 rows:**
A. 1 food/everyday (universally understandable)
B. 1 universal OR local-city

Forbidden in Simple unless explicitly approved:
- light_private_jet, large_business_jet, commercial_aircraft, yacht_50m, private_island, luxury_hotel_suite_year, film_budget

**KIDS — Isolated pool:**
Eligible ONLY if `category == "kids"`
Exception: explicit Kids Easter eggs (founder_meeting kids variant)

Forbidden leak: jets, yachts, apartments, scholarships, film_budgets, hotels, private_islands, adult luxury

Display 3 kids comparisons + optional punchline.

### 2. CITY PACKS (Fixed leak)

Rule: City references appear ONLY in their city.

Fixed in v2.2 migration:
- croissant_paris, baguette, paris_bouquet_buci, paris_moulin_rouge, paris_studio_year, paris_apt_prime → ["paris"] only (was ["paris","global"])
- kebab_berlin → ["berlin"]
- avocado_toast_london, london_black_cab, london_pint, london_travelcard, london_apt_prime → ["london"]
- gelato, rome_vespa → ["rome"]
- madrid_jamon, madrid_apt_prime → ["madrid"]
- nyc_hotdog, nyc_apt_month, broadway_ticket → ["newyork"]
- tokyo_ramen, tokyo_capsule → ["tokyo"]
- dubai_burj_night → ["dubai"]

Museum/institution city is authoritative, not visitor GPS.
Architecture allows adding new city packs without code change.

### 3. ROTATION — Deterministic

**OLD:** random on every render → product feels random, numbers lie
**NEW:** stable per `artwork_id + mode + city + session_id`

Algorithm:
```
hash = fnv1a(artwork_id + "|" + mode + "|" + city + "|" + session_id) % pool_size
pick = (hash + offset) deterministic
```

Same card reopened in same visit = same comparisons.

**Surprise Me:**
- Button 🎲 Surprise me
- Picks different valid combination
- Avoid immediate repeats (track comparison_ids history in session)
- Preserve artwork value, mode, city constraints
- No LLM call
- Analytics: comparison_surprise_clicked

### 4. PUNCHLINES

Curated, magnitude-aware, never AI-generated.

Schema per comparison:
```json
"punchlines": [
  {"min_count": 1000000, "max_count": null, "text_en": "They would probably take over the museum.", "text_ru": "Они захватят музей."}
]
```

Rules:
- At most ONE punchline per set by default
- Kids = higher punchline probability (80%)
- Normal = witty, not childish (30%)

Examples implemented:
- hamster: <10k "That's a lot of cages." / 10k-1M "Pet shop needs help" / >1M "Take over museum"
- croissant: >1M "Breakfast sorted" / >20M "Paris needs more butter"
- lego: >100k "Need another room" / >1M "Another city"

### 5. EASTER EGGS

**Founder meeting MUST NOT be treated as €460M commodity.**

OLD: division → "~0.2 meetings"
NEW: explicit Easter egg, 1% chance, separate line:

☕ One meeting with ELYIO's founder — Apparently priceless.

Implementation:
- category=easter_egg, allow_math=false, calculation_price_eur=null
- Roll 1% after normal set built
- If triggered, append as 4th line OR replace least important row, but never leave <2 useful scale rows
- Track separately

### 6. NUMBER FORMAT / APPROXIMATION

All outputs use "~"

Humanize:
1.04 → ~1
8.7 → ~9
347 → ~350
1,183 → ~1,200
18,181,818 → ~18 million
83,333 → ~83,000

Locale:
EN: ~18 million
FR: ~18 millions (or same)
Implement function humanizeCount(count, locale)

No fake precision, no raw float division in UI.

### 7. PRICE GOVERNANCE

Extended schema v2.2:

- source_url
- source_name
- verified_at (ISO date)
- valid_until
- review_interval_days
- original_currency
- original_price
- calculation_price_eur
- status: REVIEW_REQUIRED | STALE | UNSOURCED | EASTER_EGG | VERIFIED
- allow_remote_override

All v2.1 values flagged REVIEW_REQUIRED. Must be audited before production truth.
Landing and app share same prices.

### 8. REMOTE MEME PACK

Monthly/pop references separable from core.

File: remote_meme_pack_v1.json
- versioned, schema validated, cached, fallback to last-known-good
- allowlist, no executable, source+expiry required, can be disabled immediately
- Deterministic once loaded

Core app ships with 60 comparisons (luxury/food/everyday/tech/city/kids/easter_egg),
including `chatgpt_pro_year` and `private_chef_year`.
Remote adds exactly these 7 pop items: `super_bowl_ad`, `film_budget`,
`eras_tour_ticket`, `labubu_doll`, `champions_final_ticket`, `bored_ape`, and
`lebron_james_rookie_card`.

No deploy needed to refresh memes.

### 9. LANDING = SAME ENGINE

Remove hardcoded arithmetic from landing.

Landing uses same canonical engine + prices + rounding + labels.

BUT fixed demo seed: elyio_landing_fixed_2026_09_04

File: landing_demo_seed.json with 3 demos:
- orsay_monet_100m_normal → [ferrari, croissant, moulin_rouge]
- orsay_monet_100m_simple → [big_mac, paris_apt]
- orsay_monet_100m_kids → [ice_cream, ps5, hamster]

SSR/hydration always same result.

### 10. ANALYTICS

Events:
- comparison_set_viewed
- comparison_surprise_clicked

Params: artwork_id, mode, museum_id, city, comparison_ids, categories, engine_version, has_easter_egg, has_punchline

Do NOT send estimated artwork value unless approved.

### 11. REGRESSION SAFETY

Preserve:
- value provenance
- ESTIMATED_VALUE / AI_INDICATIVE_ESTIMATE / MARKET_CONTEXT / BEYOND_MARKET
- recognition, story modes, localization

Comparison Engine transforms eligible monetary scale, does not create valuation.

### 12. MIGRATION PLAN v2.1 → v2.2

1. Audit catalog: add source governance fields (DONE in catalog)
2. Fix city leaks (DONE)
3. Fix Kids isolation: remove kids from iphone_16_pro_max, pizza_napoletana, nutella_ton, gelato, labubu_doll (DONE)
4. Move pop category to remote pack (DONE)
5. Founder meeting → allow_math=false, status EASTER_EGG (DONE)
6. Add punchlines structure (DONE for 6 key items, extend later)
7. Implement engine JS with deterministic hash + humanize + punchline selector
8. Implement remote pack loader with cache+fallback
9. Replace landing hardcoded examples with engine + fixed seed
10. Add analytics hooks
11. Run test matrix

### 13. TEST MATRIX

- Normal/Paris, Normal/London, Normal/no city, Simple/Paris, Simple/NY, Kids/Paris, Kids/non-Paris
- Surprise me repeat prevention
- Same-session deterministic, new-session variation
- Very small/large estimate, singular, million, billion scale
- Missing city, missing source, expired reference, remote pack unavailable
- Verify Kids never leaks adult luxury
- City never leaks wrong city
- Same card not mutating without Surprise me
- No fake precision, no division by zero
- Landing == app calculation

### 14. FILES

- comparison_engine_v2_2_catalog.json (60 core)
- remote_meme_pack_v1.json (7 remote)
- landing_demo_seed.json
- comparison_engine_v2_2_implementation.js (engine)
- ARCHITECTURE.md (this file)
