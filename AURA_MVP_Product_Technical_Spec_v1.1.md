# AURA — Product & Technical Specification

**MVP: Musée d’Orsay Edition**  
**Version 1.1 — 2 August 2026**  
**Implementation target: Codex-assisted development**

## 1. Executive summary

**Consumer promise:** Point. Discover. Understand.

AURA is a game-like AI museum guide. A visitor points the camera at an artwork and, within seconds, receives a compact, understandable card: what the object is, why it matters, what to look at, how rare it is, and an honest indicative market-value range. During the visit, AURA tracks works, artists, time, progress, missions, and total indicative value. At the end, it creates a vertical share card for Instagram Stories, TikTok, WhatsApp, and image export.

**Five-second explanation:**

> Point your camera at an artwork. Discover its story, significance and scale. After the museum, see how many masterpieces — and billions — you experienced.

AURA is not an encyclopedia, a long audio guide, or an art-history course. The first release is deliberately narrow: **one museum, a highly reliable recognition system, one excellent artwork card, and one viral visit recap.**

## 2. Product thesis

Museums usually present art through labels: artist, year, technique, dimensions. Most visitors cannot translate those facts into meaning. AURA turns a label into a story that feels native to the Instagram/TikTok era without reducing art to empty entertainment.

The product has four layers:

1. **Hook — scale:** “What might this be worth?”
2. **Utility — meaning:** “Why does this matter?”
3. **Emotion — attention:** “Where should I look to feel it myself?”
4. **Reward — recap:** “Today you experienced 37 masterpieces with an indicative value of €3.8B.”

Money is a translator of scale, not the meaning of the artwork. The primary product is understanding.

## 3. MVP goals and success criteria

The MVP must prove three behaviors:

1. Visitors use AURA’s camera instead of the default phone camera. Target: **more than 60% of a test group perform at least five scans**.
2. Visitors read the card and return their attention to the physical artwork. Target: **median card engagement above 15 seconds** and measurable increase in artwork dwell time.
3. Visitors share the recap. Target: **30% of completed visits trigger a share or image save**.

North-star metric for the pilot:

> **Increase in meaningful attention time in front of the original artwork.**

## 4. MVP scope

### 4.1 Included

- Musée d’Orsay only.
- Initial recognition set: Top 100 priority works, with Top 20 fully editorialized at launch.
- AI-assisted visual recognition using retrieval against a controlled reference set.
- Artwork card with identification, indicative value, analogy, significance, “where to look,” rarity and 30–60 second audio.
- Visit session, progress and missions.
- Favorite artwork selection.
- Visit recap and 9:16 share image.
- Interface and editorial content in:
  - English (`en`)
  - French (`fr`)
  - Simplified Chinese (`zh-Hans`)
- Normal, Simple and Kids explanation modes.
- Analytics required to validate the three MVP hypotheses.
- Monetization architecture prepared but activated only after product validation.

### 4.2 Explicitly excluded

- Global Cultural Score.
- User rankings or leaderboards.
- Cultural biography and AI personality profile.
- Social graph and public feed.
- AR historical reconstructions.
- Museum heatmaps, white label and B2B dashboards.
- Multiple museums in the launch build.
- Generic “recognize all art in the world” promise.
- Unverified AI-generated facts or live AI-generated valuations.

## 5. Target users

### Primary

International visitors aged 18–55 who use mobile photography and social media, are curious about art, but do not want a traditional academic guide.

### Secondary

- Parents visiting with children.
- Young adults looking for a more social and game-like museum experience.
- Visitors interested in markets, collecting, rarity and value.
- French, English-speaking and Chinese-speaking tourists in Paris.

## 6. Core user journey

1. User opens AURA.
2. App detects Musée d’Orsay by GPS/geofence or allows manual selection.
3. User selects interface language: English, French or Simplified Chinese. The app also suggests the device language.
4. User taps **Start Visit**.
5. A visit session starts and three missions are assigned.
6. User points the camera at an artwork and takes a photo.
7. AURA recognizes the work and returns an artwork card in under 2.5 seconds on 4G for known works.
8. User reads, listens, adds the work to the visit, favorites it, or shares it.
9. Progress updates automatically.
10. User ends the visit and receives a vertical recap card.

## 7. Screen specification

The MVP contains six user-facing states. They may be implemented as five main tabs/screens plus onboarding.

### 7.1 Onboarding

Purpose: explain the product in one screen.

Content:

- Point your camera at the whole artwork.
- Discover its story, significance and scale.
- Build your visit and share the recap.
- Language selector: EN / FR / 简体中文.
- Primary CTA: **Continue**.

### 7.2 Museum Home

Elements:

- Museum detection chip: `Musée d’Orsay · Detected`.
- Primary button: **Start Visit**.
- Three missions, for example:
  - See three works by Monet — 0/3.
  - Find a work estimated above €100M.
  - Discover an artist you did not know.
- “How it works” row with three icons.
- If a session is active, show **Continue Visit** and current metrics.

### 7.3 Camera

- Fullscreen camera.
- Thin 3:4 framing guide.
- Instruction: “Frame the entire artwork.”
- iPhone-style shutter button with haptic feedback.
- After capture: crop/resize and upload.
- Loading state: artwork-card skeleton, not a blocking spinner.
- Failure state: “We could not identify it. Move closer and photograph the entire artwork without people blocking it.”
- Retry button.

### 7.4 Artwork Card

Order is fixed:

1. Artwork image, 4:3, pinch-to-zoom.
2. Artist, title and year.
3. Indicative market estimate badge, e.g. `€80–120M EST.`
4. Estimate-information sheet explaining that the work is not for sale and the range is based on comparable sales and object characteristics.
5. Scale analogy, e.g. “Comparable to one modern wide-body aircraft.”
6. **Why it matters** — maximum two short lines.
7. Mode selector: Normal / Simple / Kids.
8. **Where to look** — one concrete action in a highlighted block.
9. Rarity note.
10. Audio playback, 30–60 seconds.
11. Actions: **Add to Visit**, favorite, share.

Example:

**Claude Monet — Vétheuil, soleil couchant — 1901**

- Indicative estimate: €80–120M.
- Why it matters: Monet stopped describing the city precisely and began showing how light changes it from moment to moment.
- Where to look: Step back three paces and watch how separate brushstrokes become a luminous reflection.
- Rarity: Works of this level almost never reach the open market.

### 7.5 Visit Progress

Metrics:

- Works viewed.
- Unique artists.
- Indicative total value.
- Visit duration.
- Route completion percentage.
- Completed missions.
- Horizontal gallery of viewed works.
- Sticky next action, e.g. “Next: discover one more artist.”

Missions must rotate across artists and categories. They must not over-focus on Monet.

### 7.6 Visit Recap

- Vertical 9:16 output, 1080 × 1920 PNG.
- Museum name and date.
- Works viewed.
- Artists discovered.
- Indicative total value.
- Visit duration.
- Most valuable viewed work.
- Favorite work.
- One achievement badge, e.g. `Billion Euro Visitor`.
- Share sheet: Instagram Stories, TikTok, WhatsApp, Save Image.

The recap is a digital souvenir and the primary organic acquisition loop.

## 8. AI and recognition architecture

### 8.1 Principle

For the MVP, recognition is primarily **retrieval**, not unconstrained generation. Reliability on a controlled museum set is more important than worldwide breadth.

> 98% accuracy on 100 works is better than 60% accuracy on 100,000 works.

### 8.2 Recognition pipeline

1. Capture image.
2. On device: orientation correction, crop, resize to 512 × 512, JPEG compression.
3. Send image with `museum_id` and optional `hall_hint`.
4. Generate image embedding using DINOv2 or CLIP ViT-L/14.
5. Search nearest reference embeddings in FAISS or Supabase Vector.
6. Re-rank top candidates using:
   - visual similarity;
   - current museum;
   - hall hint;
   - aspect ratio;
   - optional OCR of the wall label;
   - optional multimodal model verification for low-confidence cases.
7. Return `artwork_id`, confidence and candidate metadata.

### 8.3 Reference images

For each priority artwork store:

- one high-quality public-domain reference image;
- 3–5 museum-condition reference photos where legally and operationally possible:
  - frontal;
  - angled;
  - glare;
  - partial crowd obstruction;
  - wider wall context.

### 8.4 Confidence handling

Suggested thresholds, to be calibrated in testing:

- `>= 0.92`: auto-confirm.
- `0.82–0.92`: show top two candidates for user confirmation or run multimodal verification.
- `< 0.82`: ask user to retry.

The UI must never confidently present an uncertain match.

### 8.5 Role of generative AI

Generative AI is used for controlled assistance, not as the source of truth:

- draft and translate editorial text;
- adapt the same verified meaning into Normal, Simple and Kids modes;
- generate audio from approved localized scripts;
- summarize user visit patterns after sufficient data exists.

Core identity facts, value ranges, rarity claims and comparable sales must come from stored reviewed data.

## 9. Data architecture

### 9.1 Two-layer model

**Layer 1 — Factual database (approximately 80%, imported):**

- artist;
- original title;
- localized titles where available;
- year/date;
- technique;
- dimensions;
- museum;
- inventory number;
- hall/location;
- public-domain image URL;
- source URLs;
- tags.

Primary sources:

- Base Joconde / POP Open Data.
- Wikidata SPARQL.
- Wikimedia Commons.
- Museum open-data records where reuse is permitted.
- Curated public lists for Top 20 / Top 50 / Top 100 prioritization.

**Layer 2 — AURA editorial content (approximately 20%, reviewed):**

- indicative estimate low/high;
- estimate currency and date;
- estimate logic;
- comparable-sale references;
- scale analogy;
- why it matters;
- where to look;
- rarity note;
- audio script;
- missions;
- confidence and editorial status.

### 9.2 Canonical database entities

#### `museums`

- `id`
- `slug`
- `name_default`
- `latitude`
- `longitude`
- `geofence_radius_m`
- `timezone`
- `status`

#### `artworks`

- `id`
- `museum_id`
- `artist_name`
- `title_original`
- `year_display`
- `inventory_number`
- `hall`
- `technique`
- `dimensions`
- `image_url`
- `image_storage_key`
- `priority` (`top20`, `top50`, `top100`, `catalog`)
- `tags[]`
- `source_urls[]`
- `status`

#### `artwork_localizations`

One row per artwork, language and explanation mode.

- `artwork_id`
- `locale` (`en`, `fr`, `zh-Hans`)
- `mode` (`normal`, `simple`, `kids`)
- `title_localized`
- `hook`
- `why_important`
- `where_to_look`
- `rarity_note`
- `analogy_text`
- `audio_script`
- `review_status`
- `reviewed_by`
- `updated_at`

#### `artwork_estimates`

- `artwork_id`
- `currency`
- `low_value`
- `high_value`
- `as_of_date`
- `logic`
- `confidence_level` (`low`, `medium`, `high`)
- `comparable_sales_json`
- `disclaimer_key`
- `review_status`

#### `artwork_embeddings`

- `id`
- `artwork_id`
- `model`
- `embedding`
- `reference_image_type`
- `reference_image_url`

#### `visits`

- `id`
- `user_id` or anonymous installation ID
- `museum_id`
- `locale`
- `started_at`
- `ended_at`
- `status`

#### `visit_artworks`

- `visit_id`
- `artwork_id`
- `recognized_at`
- `confidence`
- `card_read_ms`
- `dwell_time_ms`
- `added_to_visit`
- `is_favorite`
- `shared`

#### `missions`

- `id`
- `museum_id`
- `type`
- `criteria_json`
- localized label keys
- `active`

## 10. Multilingual and localization requirements

### 10.1 Supported launch languages

- English — `en`
- French — `fr`
- Simplified Chinese — `zh-Hans`

The app architecture must allow adding other locales without schema changes.

### 10.2 Localization principles

- No user-facing string is hard-coded inside view code.
- UI strings use localization keys.
- Editorial artwork content is stored by locale in the database.
- Original artwork titles are preserved; localized titles are displayed as a secondary or primary title according to locale.
- Fallback chain: requested locale → English → original title/factual field.
- All monetary figures use locale-aware formatting, while estimates remain primarily in EUR for the Musée d’Orsay edition.
- Chinese copy must use Simplified Chinese and natural localization, not literal machine translation.
- French copy must preserve museum and art terminology while remaining conversational.
- English is the canonical fallback language.

### 10.3 Required localized UI keys

| Key | English | French | Simplified Chinese |
|---|---|---|---|
| `start_visit` | Start Visit | Commencer la visite | 开始参观 |
| `continue_visit` | Continue Visit | Reprendre la visite | 继续参观 |
| `frame_artwork` | Frame the entire artwork | Cadrez l’œuvre en entier | 请将整件作品置于画面中 |
| `add_to_visit` | Add to Visit | Ajouter à ma visite | 加入本次参观 |
| `listen` | Listen | Écouter | 收听 |
| `why_it_matters` | Why it matters | Pourquoi cette œuvre compte | 为什么它重要 |
| `where_to_look` | Where to look | Où regarder | 看哪里 |
| `indicative_estimate` | Indicative market estimate | Estimation indicative de marché | 市场参考估值 |
| `share_visit` | Share your visit | Partager votre visite | 分享本次参观 |
| `try_again` | Try again | Réessayer | 重试 |
| `not_recognized` | We could not identify this artwork | Nous n’avons pas pu identifier cette œuvre | 未能识别这件作品 |

### 10.4 Audio

- Audio script exists separately for each locale and mode where enabled.
- Launch requirement: Normal audio in EN, FR and zh-Hans for Top 20.
- Target length: 30–60 seconds, approximately 75–110 words in English; equivalent natural duration in French and Chinese.
- TTS output must be cached; do not synthesize on every playback.

## 11. Content rules

### Estimates

Always display a range, never a definitive price.

Correct:

> Indicative market estimate: €80–120M.

Incorrect:

> This painting is worth €100M.

Mandatory disclaimer:

> This museum work is not for sale. The range is an editorial estimate based on comparable public sales, artist, period, subject, size, provenance and museum significance. It is not an appraisal or insurance value.

### Analogies

- Use a controlled reference table with dates and source notes.
- Prefer approximate wording: “Comparable to…”
- Avoid false precision such as “exactly 347 Ferraris.”
- Kids analogies may use ice creams or other intuitive units, but must remain clearly playful.

### Why it matters

- One sentence.
- No academic jargon.
- Explain the change the work represents.

### Where to look

- One direct action.
- Begin with a verb: Step back, Find, Compare, Notice, Follow.
- Must send the user’s eyes back to the physical artwork.

### Audio

- Calm, intelligent and conversational — “a knowledgeable friend,” not a lecturer.
- Combine the key meaning with one observation action.

## 12. API contract

### `POST /v1/recognize`

Request:

```json
{
  "image_base64": "...",
  "museum_id": "orsay",
  "hall_hint": "34",
  "locale": "fr"
}
```

Response:

```json
{
  "status": "matched",
  "artwork_id": "orsay_rf_1990",
  "confidence": 0.96,
  "bbox": null,
  "alternatives": []
}
```

### `GET /v1/artworks/{id}?locale=en&mode=normal`

Returns the complete localized artwork card and estimate disclaimer.

### `POST /v1/visits`

```json
{
  "museum_id": "orsay",
  "locale": "zh-Hans"
}
```

### `POST /v1/visits/{visit_id}/artworks`

```json
{
  "artwork_id": "orsay_rf_1990",
  "recognition_confidence": 0.96,
  "card_read_ms": 18400,
  "dwell_time_ms": 61000,
  "is_favorite": false
}
```

### `GET /v1/visits/{visit_id}/progress`

Returns metrics, completed missions and the next recommended mission.

### `POST /v1/visits/{visit_id}/complete`

Returns recap data and a server-renderable share-card payload.

## 13. Technical stack

### Mobile

- iOS-first: SwiftUI.
- Camera: AVFoundation.
- Location: CoreLocation.
- Localized resources: String Catalog / `.xcstrings`.
- Image preprocessing on device.
- Anonymous mode supported; account not required for first visit.

### Backend

- Python FastAPI.
- Supabase: Postgres, Auth/anonymous IDs, Storage, optional pgvector.
- FAISS in memory is acceptable for the initial 100-work retrieval set.
- Object storage for normalized public-domain images and cached audio.
- Background jobs for data import, embeddings and share-card rendering.

### Analytics

PostHog or equivalent. Required events:

- `onboarding_completed`
- `language_selected`
- `visit_started`
- `scan_attempt`
- `scan_success`
- `scan_failed`
- `candidate_confirmed`
- `artwork_card_opened`
- `artwork_card_read_time`
- `audio_started`
- `audio_completed`
- `artwork_added`
- `artwork_favorited`
- `mission_completed`
- `visit_completed`
- `recap_generated`
- `share_started`
- `share_completed`
- `paywall_viewed`
- `purchase_completed`

Do not collect precise movement analytics beyond what is necessary for the pilot without explicit consent.

## 14. Monetization — prepared, activated later

### Free

- Five recognitions.
- Basic identification and short explanation.
- Visit recap without indicative-value total.

### Museum Pass — €4.99

- Unlimited recognition for 24 hours in Musée d’Orsay.
- Full cards, value ranges, audio, missions, Kids mode and full recap.

### Paris Pass — €12.99

- Musée d’Orsay plus future Paris museums.
- In the MVP it may appear as “Coming Soon”; do not sell unavailable content until it exists.

Paywall concept after the fifth successful scan:

> You discovered five masterpieces. Unlock the full Musée d’Orsay visit for €4.99.

Monetization is implemented after behavior validation, not before.

## 15. Design direction

- Apple-first, contemporary and calm.
- References: Apple Camera, Shazam’s single-action clarity, Linear typography, Airbnb card hierarchy.
- Light theme for MVP.
- Background: `#FAFAF9`.
- Main text: `#111111`.
- Primary button: black.
- Corner radius: approximately 20 px.
- SF Pro on iOS; Inter for web/admin tooling.
- Generous whitespace.
- No decorative “museum gold,” parchment, faux-classical frames or academic visual clichés.
- Price is prominent enough to hook attention but must not visually dominate “Why it matters” and “Where to look.”

## 16. Content/CMS workbook mapping

The existing workbook structures are consolidated into the following canonical import columns:

1. ID
2. Museum ID
3. Artist
4. Title Original
5. Title EN
6. Title FR
7. Title zh-Hans
8. Year
9. Inventory Number
10. Hall
11. Technique
12. Dimensions
13. Image URL
14. Priority
15. Estimate Low EUR M
16. Estimate High EUR M
17. Estimate Logic
18. Comparable Sales
19. Estimate Confidence
20. Analogy Type
21. Analogy EN
22. Analogy FR
23. Analogy zh-Hans
24. Analogy Kids EN
25. Analogy Kids FR
26. Analogy Kids zh-Hans
27. Why Important Normal EN
28. Why Important Normal FR
29. Why Important Normal zh-Hans
30. Why Important Simple EN
31. Why Important Simple FR
32. Why Important Simple zh-Hans
33. Why Important Kids EN
34. Why Important Kids FR
35. Why Important Kids zh-Hans
36. Where to Look EN
37. Where to Look FR
38. Where to Look zh-Hans
39. Rarity Note EN
40. Rarity Note FR
41. Rarity Note zh-Hans
42. Audio Script EN
43. Audio Script FR
44. Audio Script zh-Hans
45. Tags
46. Mission IDs
47. Source URLs
48. Editorial Status
49. Reviewed By
50. Updated At

For production, localized text should be normalized into the `artwork_localizations` table rather than kept as fifty wide columns. The spreadsheet is an editorial import/export interface only.

## 17. Delivery plan

### Week 1 — Data and recognition

- Import/finalize factual records for Top 100.
- Complete reference-image set and embeddings.
- Implement `/recognize` and confidence handling.
- Define localization keys and database schema.
- Import current workbook into staging tables.

### Week 2 — iOS product flow

- Onboarding and language selection.
- Museum Home.
- Camera and recognition states.
- Artwork Card.
- Visit Progress.
- Localized UI in EN, FR and zh-Hans.

### Week 3 — Content, recap and field test

- Fully review Top 20 content in three languages.
- Generate/cache audio in three languages.
- Implement Visit Recap and PNG export.
- Add analytics.
- TestFlight field test inside Musée d’Orsay.
- Measure recognition accuracy, card reading, dwell time and sharing.

This is an aggressive three-week plan. Scope must remain frozen.

## 18. Definition of done

The MVP is ready for a museum pilot when:

- Top 100 known works can be recognized under normal museum conditions.
- Top 20 have fully reviewed EN, FR and zh-Hans cards and audio.
- Recognition latency is below 2.5 seconds at p50 and below 5 seconds at p95 on 4G.
- Low-confidence matches do not produce confident false results.
- A visit can start, record works, update missions and complete without account creation.
- Recap exports correctly at 1080 × 1920.
- All user-facing strings are localized and no raw localization keys appear.
- Estimate ranges always include the disclaimer.
- Analytics events are visible end to end.
- The app passes a real one-day Musée d’Orsay test.

## 19. Codex implementation order

Codex should build in this order:

1. Repository structure and environment configuration.
2. Database migrations and seed format.
3. Localization framework with EN, FR and zh-Hans from day one.
4. Data-import script for the canonical workbook.
5. Recognition service with a local test dataset.
6. API contracts and automated tests.
7. iOS onboarding, home and session state.
8. Camera and recognition flow.
9. Artwork Card and localized content modes.
10. Visit Progress and missions.
11. Recap rendering and sharing.
12. Analytics.
13. Audio.
14. Monetization only after pilot metrics are reviewed.

Engineering rules:

- Do not silently fabricate artwork facts.
- Do not generate valuations at request time.
- Do not hard-code user-facing strings.
- Do not couple the UI directly to spreadsheet column names.
- Every endpoint must return typed errors.
- Every recognition response must include confidence.
- Prefer simple, observable systems over premature scale architecture.

## 20. Positioning

### Consumer

**Point. Discover. Understand.**

Alternative:

**Scan art. Discover its story and scale.**

French:

**Cadrez. Découvrez. Comprenez.**

Chinese:

**对准作品，发现故事，读懂艺术。**

### Internal/investor description

> AURA is an AI-powered, game-like museum guide that turns physical artworks into understandable stories, scale and shareable visit achievements.

## 21. Final product principle

Do not build a universal cultural operating system yet.

Build one moment exceptionally well:

> A visitor photographs a Monet in Musée d’Orsay, receives a trustworthy and beautiful explanation in their language, looks back at the original with new attention, says “wow,” and shares the visit with friends.

If that loop works, the larger AURA can be built on top of it.
