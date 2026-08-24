# Value Experience

Status: CURRENT

Value Engine V4 remains EUR-grounded. Institution display currency is configuration, not an exchange-rate instruction: an EUR estimate is never relabelled GBP, and ELYIO does not invent an FX conversion.

## Rendering contract

| State | Visitor output | Scale comparison |
|---|---|---|
| `NUMERIC_ESTIMATE` | Responsible reviewed or valid aggregate-eligible V4 indicative range, supporting methodology and disclaimer | Required. `web/lib/scaleComparison.ts` deterministically supplies rounded comparisons. |
| `NO_RESPONSIBLE_ESTIMATE` | Truthful no-estimate/beyond-market explanation | No Ferrari, property, yacht or other monetary equivalent is generated. Source context may remain clearly labelled as context rather than the work's value. |
| `VALUE_UNAVAILABLE` / `UNSUPPORTED` | Value output omitted or explicitly unavailable | No monetary comparison and no currency relabelling. |

`web/components/ui/ProvenanceReveal.tsx` enforces this boundary. A numeric market record for another work (`MARKET_CONTEXT`) is not a viewed-work estimate and does not qualify for visitor-facing scale analogies.

## Deterministic comparison context

`web/lib/comparisonReferences.ts` is the reviewed, versioned reference library; `web/lib/scaleComparison.ts` owns deterministic selection, arithmetic and broad rounding. The language model never invents reference prices or calculates comparison counts. Version `scale-comparison-v2.0.0` records each reference range, currency, scope, methodology and review date.

For Normal mode, the engine targets three rows from distinct categories. The stable seed is artwork ID + engine version + Institution city/country, so an artwork does not change on refresh while similarly valued artworks can receive different combinations. Available global categories cover supercars, light/private and commercial aircraft, yachts, provider-neutral suborbital seats, holidays, hotel stays, private-island-class property, education and entertainment budgets. References are admitted only when their resulting quantities remain readable; output uses rounded quantities rather than false precision.

Local property references are selected from the current Institution city carried in visit state:

- Paris context uses central-Paris wording.
- London context uses central-London wording.
- An unconfigured city receives no fabricated local-property label; global comparisons still keep the required block available.

The contextual property benchmark's currency is used only for deterministic scale arithmetic. It does not change or relabel the displayed artwork range.

## Founder easter egg

About 3–5% of eligible numeric-estimate artworks deterministically replace one of the three comparison rows with `🤝 one meeting with ELYIO’s founder — apparently priceless`. The selection seed is artwork ID + comparison-engine version. This row is explicitly `monetary: false`, has no reference price, never participates in valuation arithmetic, never adds a fourth row, and cannot appear for no-estimate, unsupported or pending-review states. The ordinary non-appraisal methodology disclaimer remains unchanged.

## Controlled-preview cache behavior

The Paris wording observed after the earlier city-context fix came from an installed controlled-preview PWA still executing the previous content-hashed JavaScript bundle. `web/components/ServiceWorkerRegister.tsx` now activates a waiting worker automatically only for trusted controlled-preview sessions, and `web/sw-template.js` uses network-first navigation for `controlled-preview=1`. Public visitor update behavior remains unchanged.
