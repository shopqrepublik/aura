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

`web/lib/scaleComparison.ts` owns arithmetic and broad rounding; the language model never calculates comparison counts. Globally understandable references can be used everywhere. Local property references are selected from the current Institution city carried in visit state:

- Paris context uses central-Paris wording.
- London context uses central-London wording.
- An unconfigured city receives no fabricated local-property label; global comparisons still keep the required block available.

The contextual property benchmark's currency is used only for deterministic scale arithmetic. It does not change or relabel the displayed artwork range.
