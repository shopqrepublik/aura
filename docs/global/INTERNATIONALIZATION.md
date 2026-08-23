# Internationalization

Status: CURRENT foundation versus remaining target work.

## Current configuration

- Country and Institution accept validated arbitrary BCP-47 default/supported locales, IANA timezone and three-letter display currency. Institution overrides Country defaults.
- `Artwork.source_language` and `SourceRecord.source_language` preserve provider language. `ArtworkLocalization.locale` remains an arbitrary string; translation/editorial rows do not overwrite provider truth.
- `web/lib/types.ts` distinguishes open `LocaleCode` from the shipped UI-bundle union. `resolveUiLocale` honestly falls back to a bundle that exists.
- `web/lib/i18n.ts` centralizes reusable UI copy and institution names/location are interpolated. Featured/directory behavior no longer assumes Paris/France IDs.
- `web/lib/international.ts` supplies `Intl` date/currency presentation helpers. It performs no FX conversion.
- Analytics canonical/server times and retention cohorts stay UTC. Institution timezone is display/local-business context only.
- Current public SEO and complete visitor content ship `en`, `fr`, `zh-Hans`; URL spelling remains `zh-hans` and HTML language/hreflang map to `zh-Hans`.
- Recognition prompt context is institution/profile-driven and not branched by country. Recognition structured facts are not visitor translation.
- Generated enrichment currently produces only the three shipped content locales with English fallback.

## Currency and content policy

Institution/Country configuration may select EUR/GBP/USD/JPY-style ISO codes, but this is not conversion. Value Engine V4 remains an explicit EUR valuation ladder and must not be relabeled as GBP. Structured `content_policy_code` plus localized policy fields replace France-string matching for legal/public-collection copy. New jurisdiction-specific claims must be explicitly reviewed/configured or omitted; ELYIO is not a legal rules engine.

## Remaining work for a new language

Create/review a UI message bundle, remove remaining inline locale ternaries, add generated-content templates/prompt output locale, editorial workflow, audio convention, SEO content/routes/hreflang and layout tests. RTL is not implemented/tested. This is a content/UI-language blocker when the institution cannot use an existing shipped language; it is no longer a Country/Institution/catalog schema blocker.

## National Gallery paper configuration

`GB`, London, `Europe/London`, default/supported `en-GB`, and `GBP` validate through the generic backend with no Louvre/France core branch. The current English UI can deliberately fall back to `en`; claiming a distinct fully localized `en-GB` bundle requires reviewed copy but no schema change.

## Target

Move messages into validated locale resource packages; add localized Institution/Collection/Object metadata; make generated content accept explicit response locale and institution/country context; generate SEO only for approved useful locale content; add CJK/long/RTL tests; keep locale persistence independent from visit mode/institution.
