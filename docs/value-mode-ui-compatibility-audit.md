# Value Mode UI Compatibility Audit

Scope: current production artwork card UI/API only. No UI changes were implemented.

Required future value modes:

- `ESTIMATED_VALUE`: a defensible numerical range for the specific artwork.
- `MARKET_CONTEXT`: a financial reference around the work, not the work's estimated value.
- `BEYOND_MARKET`: a non-market/institutional value state where pricing the work would mislead.

Critical rule: `MARKET_CONTEXT` and `BEYOND_MARKET` numbers must never enter visit estimated-value totals.

## Current Data Model

`backend/app/models.py:152` defines `ArtworkEstimate` as the only value layer. Its numerical fields are mandatory floats:

- `estimate_low_eur_m`, `backend/app/models.py:157`
- `estimate_high_eur_m`, `backend/app/models.py:158`
- `estimate_logic`, `backend/app/models.py:159`
- `comparable_sales`, `backend/app/models.py:160`
- `estimate_confidence`, `backend/app/models.py:161`

Compatibility issue: the model can only express one kind of value: a numeric EUR-million estimate range. It cannot distinguish `ESTIMATED_VALUE` from `MARKET_CONTEXT` or `BEYOND_MARKET`.

Required future change: add an additive value-mode model or columns. Do not store context numbers, such as the Leonardo `$450.3m` record, in `estimate_low_eur_m` / `estimate_high_eur_m`.

## Backend Catalog/API

`backend/app/catalog.py:14` maps DB rows into the legacy catalog shape. It emits only:

- `estimate_low`, `backend/app/catalog.py:28`
- `estimate_high`, `backend/app/catalog.py:29`
- `needs_editorial_review`, `backend/app/catalog.py:30`

Compatibility issue: API clients receive no `value_mode`, no context label, no context explanation, and no explicit aggregate-eligibility flag.

Required future change: extend the catalog response with a structured `value_reveal` object while keeping `estimate_low` / `estimate_high` backward-compatible for existing Orsay/Orangerie `ESTIMATED_VALUE` records.

`backend/app/main.py:984-987` computes visit progress value totals by summing `estimate_low` and `estimate_high` from seen artworks. This is currently safe only because the fields mean estimated artwork value.

Required future change: sum only records where `value_reveal.mode == "ESTIMATED_VALUE"` or a backend-safe `aggregate_value_eligible == true`.

## Frontend Types

`web/lib/types.ts:16-28` defines `Estimate` as:

- `low: number | null`
- `high: number | null`
- optional review metadata

`web/lib/types.ts:44` makes `estimate` required on every `Artwork`.

Compatibility issue: there is no type-level way to represent `MARKET_CONTEXT` or `BEYOND_MARKET`. If a context number is squeezed into `estimate.low/high`, every downstream total/ranking path will treat it as artwork value.

Required future change: introduce a discriminated union, for example:

```ts
type ValueReveal =
  | { mode: "ESTIMATED_VALUE"; valueLow: number; valueHigh: number; currency: "EUR"; aggregateEligible: true; ... }
  | { mode: "MARKET_CONTEXT"; headlineNumber: number | string; currency?: string; aggregateEligible: false; ... }
  | { mode: "BEYOND_MARKET"; headline: string; optionalNumericContext?: ...; aggregateEligible: false; ... };
```

Keep legacy `estimate` only as a derived/backward-compatible field for old UI paths, and only when mode is `ESTIMATED_VALUE`.

## ProvenanceReveal

`web/components/ui/ProvenanceReveal.tsx:48-64` accepts only `low`, `high`, `accent`, sales count, inventory number, locale, and mode.

`web/components/ui/ProvenanceReveal.tsx:65` defines `hasEstimate = low != null && high != null`.

`web/components/ui/ProvenanceReveal.tsx:114-118` formats every present value as `€{low}` or `€{low}–{high}M`.

`web/components/ui/ProvenanceReveal.tsx:188-189` shows either `Estimated market range` or the generic pending-review note.

`web/components/ui/ProvenanceReveal.tsx:208-225` always shows the generic estimate disclaimer/methodology sheet.

Compatibility issue: the component already has the visual label “Market context” via `web/lib/i18n.ts:267`, but its behavior is still binary: numeric estimate or pending estimate. It cannot show:

- `BEYOND THE MARKET`
- `No ordinary market price`
- artist auction record as context
- category comparable as context
- a disclaimer saying “not the value of this work”

Required future change: make `ProvenanceReveal` consume `valueReveal`, branch by mode, and only call `resolveScaleComparisonSentence` for `ESTIMATED_VALUE`.

## CardScreen

`web/components/screens/CardScreen.tsx:145-153` passes only `artwork.estimate.low`, `artwork.estimate.high`, and comparable sales count into `ProvenanceReveal`.

Compatibility issue: even if API data includes a value mode, the card currently discards it.

Required future change: pass `artwork.valueReveal` to `ProvenanceReveal`. Keep `estimate` fallback for existing content during migration.

## Scale Comparisons

`web/lib/scaleComparison.ts:184-190` returns null only when low/high are null; otherwise it computes a midpoint from the numeric range.

`web/lib/scaleComparison.ts:210-213` does the same for Kids mode.

Compatibility issue: any MARKET_CONTEXT number stored as low/high would generate fake scale comparisons.

Required future change: scale comparisons are allowed only for `ESTIMATED_VALUE` and only when comparison inputs are sourced and approved. MARKET_CONTEXT may display its source-labeled number, but should not produce “equivalent to X” analogies unless a separate approved calculation exists.

## Progress Screen

`web/components/screens/ProgressScreen.tsx:68-71` sums `a.estimate.low/high` for every seen artwork and displays `€low–highM`.

`web/components/screens/ProgressScreen.tsx:134-136` labels the result as value seen.

Compatibility issue: a MARKET_CONTEXT number in `estimate` would immediately inflate the live visit total. Example: Mona Lisa's Leonardo context number must not produce `€450.3M` in visit progress.

Required future change: compute:

- estimated total from `ESTIMATED_VALUE` only;
- optional separate counts for `MARKET_CONTEXT` and `BEYOND_MARKET`.

Recommended progress copy:

- If only `ESTIMATED_VALUE`: `€X–YM estimated market value`.
- If mixed: `€X–YM estimated market value + N beyond-market/context works`.
- If only non-estimated modes: `N beyond-market/context works` or localized equivalent, not `Pending review`.

## Recap Screen

`web/components/screens/RecapScreen.tsx:73-75` sums estimate values and determines whether any estimate exists.

`web/components/screens/RecapScreen.tsx:91-94` chooses `mostValuable` from artworks with `estimate.high != null`.

`web/components/screens/RecapScreen.tsx:105-111` triggers the “billion” badge from summed estimate high.

`web/components/screens/RecapScreen.tsx:117-127` and `web/lib/i18n.ts:259-262` describe partial estimate coverage.

`web/components/screens/RecapScreen.tsx:431-433` displays the most valuable card as `€low–highM EST.`.

Compatibility issue: all of these paths assume any non-null estimate is an artwork-value estimate.

Required future change:

- totals: include only `ESTIMATED_VALUE`;
- most valuable: choose only `ESTIMATED_VALUE` for “Most valuable seen today”;
- if no estimated values but context/icon works exist, show “Featured today” or a new “Beyond-market highlight” label;
- billion badge: trigger only from `ESTIMATED_VALUE` aggregate, never from MARKET_CONTEXT;
- partial note: distinguish “reviewed estimate count” from “context/icon count”.

Recommended recap behavior:

- `ESTIMATED_VALUE` only: current recap remains valid.
- Mixed visit: `€X–YM estimated market value + N beyond-market icons`.
- Louvre-only Golden-style visit: `N beyond-market/context works` with no estimated total.
- Featured object selection: prioritize `BEYOND_MARKET` Tier A or first favorite when no `ESTIMATED_VALUE` exists.

## Recap Image Generation

`web/lib/recap-image.ts:164-166` renders `€low–highM` if `hasAnyEstimate`.

`web/lib/recap-image.ts:197-199` uses the subtitle `in estimated art market value`.

`web/lib/recap-image.ts:287-289` renders the most valuable work estimate as `€low–highM EST.`.

Compatibility issue: the share image has the same aggregate-value risk as RecapScreen. It must not print market-context numbers as if they were artwork estimates.

Required future change: pass separate recap aggregates:

- `estimatedValueLow`
- `estimatedValueHigh`
- `estimatedValueCount`
- `marketContextCount`
- `beyondMarketCount`
- `featuredValueMode`

## Visit Palette / Artwork Ranking

`web/lib/visitPalette.ts:13-18` ranks seen works by `estimate.high`, then appends unestimated works.

Compatibility issue: MARKET_CONTEXT values would incorrectly dominate the visual recap palette if stored in `estimate.high`.

Required future change: ranking should use a separate `significanceRank` or product-level highlight score. `estimate.high` should only rank within `ESTIMATED_VALUE` works.

## Missions

`web/lib/missions.ts:47-62` computes a “most valuable” mission target by choosing the catalog artwork with the highest `estimate.high`.

Compatibility issue: MARKET_CONTEXT numbers would change mission logic and could make a context-only Louvre work the “most valuable” target.

Required future change: this mission should use only `ESTIMATED_VALUE` records, or be museum-specific and disabled/renamed for Louvre until value-mode-aware missions exist.

## I18n Strings

Current strings assume a single estimate concept:

- `stat_value_seen`, `web/lib/i18n.ts:220`
- `estimate_disclaimer`, `web/lib/i18n.ts:233-236`
- `pending_review`, `web/lib/i18n.ts:244`
- `estimate_pending`, `web/lib/i18n.ts:250`
- `estimated_market_range`, `web/lib/i18n.ts:270-273`
- `methodology_body`, `web/lib/i18n.ts:301-303`
- `reveal_pending_review_note`, `web/lib/i18n.ts:305-308`
- `in_estimated_market_value`, `web/lib/i18n.ts:320-323`
- share text at `web/lib/i18n.ts:347-349`

Required future change: add localized strings for:

- `BEYOND THE MARKET`
- `No ordinary market price`
- `MARKET CONTEXT`
- `Artist auction record`
- `Category market context`
- `Not a valuation of this Louvre work`
- mixed recap labels

## API/UI Payload Requirement

The future API should expose a structured `value_reveal` object and an explicit `aggregate_value_eligible` boolean. The UI must never derive aggregate eligibility from “has a number”.

For the Louvre Golden 20, the sample payload in `exports/louvre/content/louvre_golden20_ui_payload_sample.json` sets `aggregate_value_eligible: false` for all `MARKET_CONTEXT` and `BEYOND_MARKET` rows.

## Summary Of Required Changes

Before Louvre value content can ship, the smallest safe UI/API work is:

1. Add a discriminated `ValueReveal` type.
2. Extend backend catalog/API serialization with `value_reveal`.
3. Update `ProvenanceReveal` to render three value modes.
4. Ensure only `ESTIMATED_VALUE` contributes to progress/recap/share totals.
5. Add separate recap counts for `MARKET_CONTEXT` and `BEYOND_MARKET`.
6. Make most-valuable ranking and missions ignore context-only numbers.
7. Add localized value-mode strings.
8. Keep legacy `estimate.low/high` behavior for Orsay/Orangerie until their content is migrated.

Do not place Louvre MARKET_CONTEXT numbers into `ArtworkEstimate.estimate_low_eur_m` or `estimate_high_eur_m`.
