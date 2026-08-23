# Internationalization

Status: CURRENT versus TARGET.

## Current

- UI type is closed union `en | fr | zh-Hans`; URLs use `en`, `fr`, `zh-hans`.
- UI strings are TypeScript/JSON localized records and many ternaries.
- Public SEO has separate pages, canonical/hreflang/x-default for three locales.
- Artwork localization table stores arbitrary locale strings, but frontend types/render paths accept only three.
- Stage 1 prompt is English; requested locale is logged/request context but prompt output schema/content is not localized.
- Generated enrichment has explicit three-locale templates and English fallback.
- Browser language is analytics metadata; it does not automatically add a supported locale.
- Selected locale persists in visit state; URL query can initialize organic visit attribution.
- Dates/numbers/value mostly use custom strings/EUR, not a comprehensive `Intl` policy.
- Homepage contains Paris/France copy; French public-collection legal copy is pattern-matched in `api.ts`.

## Blockers for a non-English/French primary-language museum

Closed TypeScript types, every localized object requiring all three current keys, inline ternaries, generated-content templates, audio asset convention, SEO static params/content, mode/game/value/share strings and editorial review workflow. AI prompts lack a configured institution/source language and controlled output language policy.

## Target global i18n

1. BCP-47 locale registry with institution supported/default locales and fallback graph.
2. Locale resource modules/CMS package validated for completeness, not ternary strings.
3. Source-language fields preserved; translations are separate rows with provenance/review status.
4. Institution/country timezone, numbering, currency and legal-context policy.
5. Prompt template accepts institution name, source language and response locale; identity facts remain source-grounded.
6. SEO locale generation only for approved useful content, with reciprocal hreflang.
7. Automated layout tests for long/RTL/CJK text; RTL is currently unsupported/not tested.
8. Locale persistence independent of museum and mode.
