#!/usr/bin/env python3
"""Create Phase 2B.1 quality-gate artifacts for the existing 20-work sample.

This audit reads existing Phase 2B outputs and writes only under
exports/louvre/content/phase2b/quality_gate. It does not regenerate the 480,
change catalog membership, write production data, fetch images, create assets,
create embeddings, or generate audio bytes.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PHASE2B = ROOT / "exports" / "louvre" / "content" / "phase2b"
OUT = PHASE2B / "quality_gate"
SAMPLE = PHASE2B / "louvre_phase2b_review_sample_20.md"
RECORDS = PHASE2B / "louvre_phase2b_480.jsonl"
GOLDEN = ROOT / "exports" / "louvre" / "content" / "louvre_golden20_final.jsonl"
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()


VALUE_RESEARCH: dict[str, dict[str, Any]] = {
    "cl010063515": {
        "classification": "BEYOND_MARKET",
        "headline": None,
        "currency": None,
        "confidence": "LOW",
        "safe_statement": "No public, reputable numeric market context was found for François-Édouard Picot in this targeted pass; Artnet/Artprice indicate market records exist but do not expose a usable public number.",
        "relationship": "no_defensible_public_number_found",
        "sources": [
            {"label": "Artnet, exact Picot L'Amour et Psyché lot page", "url": "https://www.artnet.com/artists/fran%C3%A7ois-edouard-picot/lamour-et-psyche-dY3hHSd0RO0bbi86ESW0-Q2"},
            {"label": "Artprice Picot artist market page", "url": "https://www.artprice.com/artist/22824/francois-edouard-picot"},
        ],
    },
    "cl010315397": {
        "classification": "MARKET_CONTEXT",
        "headline": 457250,
        "currency": "GBP",
        "confidence": "MEDIUM",
        "safe_statement": "A 10th-century Samanid pottery bowl sold at Christie's for £457,250; this is Samarkand/Samanid ceramics context, not a valuation of the Louvre plate.",
        "relationship": "category_comparable_samanid_pottery",
        "sources": [{"label": "Christie's, Samanid pottery bowl, price realised £457,250", "url": "https://www.christies.com/en/lot/lot-5236065"}],
    },
    "cl010321121": {
        "classification": "MARKET_CONTEXT",
        "headline": 40320,
        "currency": "GBP",
        "confidence": "MEDIUM",
        "safe_statement": "A Kashan lustre pottery bowl sold at Christie's for £40,320; this is Persian lustre ceramic context, not a price for the Louvre edicule.",
        "relationship": "category_comparable_kashan_lustre_ceramic",
        "sources": [{"label": "Christie's, Kashan lustre pottery bowl, price realised £40,320", "url": "https://www.christies.com/en/lot/lot-6445621"}],
    },
    "cl010329343": {
        "classification": "MARKET_CONTEXT",
        "headline": 6600000,
        "currency": "GBP",
        "confidence": "MEDIUM",
        "safe_statement": "A 13th-century Islamic silver-inlaid brass candlestick sold at Sotheby's for £6.6m / about $9.1m; this is metalwork-market context only.",
        "relationship": "category_record_islamic_metalwork_candlestick",
        "sources": [
            {"label": "The National, Sotheby's candlestick sale £6.6m", "url": "https://www.thenationalnews.com/world/uk-news/2021/10/28/sothebys-islamic-art-auction-13th-century-candlestick-fetches-66m/"},
            {"label": "Louvre Collections, Chandelier aux canards identity", "url": "https://collections.louvre.fr/en/ark%3A/53355/cl010329343"},
        ],
    },
    "cl010059373": {
        "classification": "MARKET_CONTEXT",
        "headline": 9800000,
        "currency": "USD",
        "confidence": "MEDIUM",
        "safe_statement": "Delacroix's Tiger Playing with a Tortoise sold for $9.8m in the Rockefeller sale; this is artist-market context, not a valuation of Médée furieuse.",
        "relationship": "artist_auction_record_context",
        "sources": [{"label": "Artnet News, Rockefeller sale Delacroix $9.8m", "url": "https://news.artnet.com/market/christies-rockefeller-sale-648m-1281551"}],
    },
    "cl010104474": {
        "classification": "MARKET_CONTEXT",
        "headline": 406702,
        "currency": "USD",
        "confidence": "MEDIUM",
        "safe_statement": "A set of ten Léonard Limosin plaques is reported as the artist's auction record at $406,702; this is enamel-plaque market context, not a price for the Louvre plaque.",
        "relationship": "artist_category_market_record",
        "sources": [
            {"label": "MutualArt, Léonard Limosin artist record", "url": "https://www.mutualart.com/Artist/Leonard-Limosin/F6A8B593E1810D3A"},
            {"label": "Christie's, Limosin set of ten plaques lot context", "url": "https://www.christies.com/en/lot/lot-6217625"},
        ],
    },
    "cl010062290": {
        "classification": "MARKET_CONTEXT",
        "headline": 17560000,
        "currency": "GBP",
        "confidence": "MEDIUM",
        "safe_statement": "Titian's Rest on the Flight into Egypt sold at Christie's for £17.56m in 2024; this is Titian market context, not a value for L'Homme au gant.",
        "relationship": "artist_auction_record_context",
        "sources": [{"label": "Alain.R.Truong reposting Christie sale result, Titian £17.56m", "url": "https://www.alaintruong.com/tag/titian/"}],
    },
    "cl010062308": {
        "classification": "BEYOND_MARKET",
        "headline": None,
        "currency": None,
        "confidence": "LOW",
        "safe_statement": "No reputable public numeric market context for Jan Stephan van Calcar was found in this targeted pass; one visible MutualArt entry is gated and for an after/copy work.",
        "relationship": "no_defensible_public_number_found",
        "sources": [
            {"label": "Louvre Collections, Melchior von Brauweiler identity", "url": "https://collections.louvre.fr/en/ark%3A/53355/cl010062308"},
            {"label": "MutualArt, after Jan Stephan von Calcar lot page", "url": "https://www.mutualart.com/Artwork/Portrait-Of-Melchior-von-Brauweiler/95378BB32D7623CE"},
        ],
    },
    "cl010066647": {
        "classification": "MARKET_CONTEXT",
        "headline": 17560000,
        "currency": "GBP",
        "confidence": "MEDIUM",
        "safe_statement": "Titian's Rest on the Flight into Egypt sold at Christie's for £17.56m in 2024; this is artist-market context, not a value for the Louvre Ecce Homo.",
        "relationship": "artist_auction_record_context",
        "sources": [{"label": "Alain.R.Truong reposting Christie sale result, Titian £17.56m", "url": "https://www.alaintruong.com/tag/titian/"}],
    },
    "cl010091989": {
        "classification": "MARKET_CONTEXT",
        "headline": 105052,
        "currency": "USD",
        "confidence": "LOW",
        "safe_statement": "Nicolas Coustou works have public market records up to about $105k; this is weak artist-market context for sculpture and should not price the Louvre marble.",
        "relationship": "artist_market_context_low_confidence",
        "sources": [{"label": "MutualArt, Nicolas Coustou market overview", "url": "https://www.mutualart.com/Artist/Nicolas-Coustou/EBD8B71B855EA5F0"}],
    },
    "cl010059589": {
        "classification": "MARKET_CONTEXT",
        "headline": 1648326,
        "currency": "USD",
        "confidence": "MEDIUM",
        "safe_statement": "Luca Giordano's reported auction record is $1.648m; this is artist-market context, not a valuation of the Louvre philosopher.",
        "relationship": "artist_auction_record_context",
        "sources": [{"label": "MutualArt, Luca Giordano artist record", "url": "https://www.mutualart.com/Artist/Luca-Giordano/F94F91EAE4AE18B8"}],
    },
    "cl010090779": {
        "classification": "BEYOND_MARKET",
        "headline": None,
        "currency": None,
        "confidence": "LOW",
        "safe_statement": "The targeted pass found auction database traces for Michel-Ange Slodtz but no reliable public numeric result suitable for visitor display.",
        "relationship": "no_defensible_public_number_found",
        "sources": [{"label": "MutualArt, Michel-Ange Slodtz auction results page", "url": "https://www.mutualart.com/Artist/Michel-Ange-Slodtz/091FDE58A64C22A1/AuctionResults"}],
    },
    "cl010099607": {
        "classification": "MARKET_CONTEXT",
        "headline": 406702,
        "currency": "USD",
        "confidence": "LOW",
        "safe_statement": "Limosin/Limoges enamel plaque sales provide category context around painted enamel plaques; it is not a value for this Master of the Aeneid plaque.",
        "relationship": "category_comparable_limoges_enamel_plaque",
        "sources": [
            {"label": "MutualArt, Léonard Limosin artist record", "url": "https://www.mutualart.com/Artist/Leonard-Limosin/F6A8B593E1810D3A"},
            {"label": "Christie's, Limosin set of ten plaques lot context", "url": "https://www.christies.com/en/lot/lot-6217625"},
        ],
    },
    "cl010111542": {
        "classification": "MARKET_CONTEXT",
        "headline": {"low": 40000, "high": 60000},
        "currency": "USD",
        "confidence": "LOW",
        "safe_statement": "A Byzantine bronze incense burner carried a Sotheby's estimate of $40k-$60k; this is only low-confidence Byzantine-object context, not a price for the Stoclet paten.",
        "relationship": "category_estimate_byzantine_object_low_confidence",
        "sources": [{"label": "Sotheby's, Byzantine incense burner estimate $40k-$60k", "url": "https://www.sothebys.com/buy/d3f2cb64-0eaa-4021-9508-11e01df05b65/lots/309e4ee3-6984-44fe-80a5-431d7968e49c"}],
    },
    "cl010009267": {
        "classification": "MARKET_CONTEXT",
        "headline": {"low": 5000, "high": 8000},
        "currency": "GBP",
        "confidence": "LOW",
        "safe_statement": "A fragmentary Egyptian stone naophorous statue carried a Sotheby's estimate of £5k-£8k; this is narrow category context only and does not value the Louvre naophore/cube statue.",
        "relationship": "category_estimate_egyptian_naophorous_statue",
        "sources": [{"label": "Sotheby's, Egyptian stone naophorous statue estimate £5k-£8k", "url": "https://www.sothebys.com/buy/3bd9c423-d710-4efc-9b17-35ff50757350"}],
    },
    "cl010123045": {
        "classification": "BEYOND_MARKET",
        "headline": None,
        "currency": None,
        "confidence": "MEDIUM",
        "safe_statement": "Cuneiform tablet prices exist, but the strong public examples found are legally/problematically different; for a royal Hittite-Ugarit letter, a numeric visitor context would be misleading without specialist review.",
        "relationship": "market_context_rejected_due_to_legal_and_identity_risk",
        "sources": [
            {"label": "Archaeology Magazine, Ugarit archives context", "url": "https://archaeology.org/issues/july-august-2021/features/ugarit-bronze-age-archive/"},
            {"label": "The Art Newspaper, Gilgamesh tablet $1.7m and restitution context", "url": "https://www.theartnewspaper.com/2021/09/23/looted-gilgamesh-tablet-returned-to-iraq"},
        ],
    },
    "cl010258916": {
        "classification": "MARKET_CONTEXT",
        "headline": {"low": 3000, "high": 5000},
        "currency": "GBP",
        "confidence": "LOW",
        "safe_statement": "A Sotheby's Etruscan bucchero chalice carried a £3k-£5k estimate; this is category estimate context only.",
        "relationship": "category_estimate_etruscan_bucchero_chalice",
        "sources": [{"label": "Sotheby's, Etruscan bucchero chalice estimate £3k-£5k", "url": "https://www.sothebys.com/en/buy/auction/2021/ancient-sculpture-and-works-of-art/an-etruscan-bucchero-chalice-circa-mid-6th-century"}],
    },
    "cl010472062": {
        "classification": "MARKET_CONTEXT",
        "headline": 152400,
        "currency": "USD",
        "confidence": "MEDIUM",
        "safe_statement": "Jean-Michel Othoniel's Untitled (blue-knot) sold at Phillips for $152,400; this is contemporary artist-market context, not a value for La Rose du Louvre.",
        "relationship": "artist_auction_record_context",
        "sources": [
            {"label": "Phillips, Othoniel Untitled (blue-knot) sold for $152,400", "url": "https://phillips.com/detail/jeanmichel-othoniel/219470"},
            {"label": "Louvre boutique, La Rose du Louvre joined collections in 2020", "url": "https://boutique.louvre.fr/en/products/400578-jean-michel-othoniel/"},
        ],
    },
    "cl010060786": {
        "classification": "MARKET_CONTEXT",
        "headline": 3442500,
        "currency": "USD",
        "confidence": "MEDIUM",
        "safe_statement": "A Giovanni Paolo Panini architectural capriccio sold for $3.4425m; this is artist/category market context, not a valuation of the Louvre painting.",
        "relationship": "artist_category_market_context",
        "sources": [
            {"label": "Invaluable, Panini sold for $3,442,500 via Christie's", "url": "https://www.invaluable.com/artist/panini-giovannipaolo-tdpvp1ezd8/sold-at-auction-prices/"},
            {"label": "Christie's, Panini auction results/history page", "url": "https://www.christies.com/en/artists/giovanni-paolo-pannini"},
        ],
    },
    "cl010091138": {
        "classification": "BEYOND_MARKET",
        "headline": None,
        "currency": None,
        "confidence": "LOW",
        "safe_statement": "No defensible public numeric context was found for this French 1500-1525 polychromed stone funerary/sculptural object in the targeted pass.",
        "relationship": "no_defensible_public_number_found",
        "sources": [{"label": "Local Louvre normalized metadata only", "url": "https://collections.louvre.fr/ark:/53355/cl010091138"}],
    },
}

SPECIFICITY = {
    "cl010063515": ("SPECIFICITY_MEDIUM", "Uses artist, 1817, Salon de 1819, oil-on-canvas and scale, but does not explain the Cupid/Psyche scene visually."),
    "cl010315397": ("SPECIFICITY_MEDIUM", "Uses Samarkand, 975-1000, ceramic technique and title, but misses the actual Arabic inscription/adage."),
    "cl010321121": ("SPECIFICITY_LOW", "Uses date/material/room but gives no object-specific account of the festive scene or lustre imagery."),
    "cl010329343": ("SPECIFICITY_MEDIUM", "Uses Herat/date/metal and title, but barely uses the ducks, lions, inscription, and repoussé construction."),
    "cl010059373": ("SPECIFICITY_LOW", "Names Delacroix and date, but does not describe Medea, the children, gesture, or drama."),
    "cl010104474": ("SPECIFICITY_LOW", "Names Limosin and enamel/copper, but does not explain Ceres, Psyche, or painted enamel detail."),
    "cl010062290": ("SPECIFICITY_LOW", "Names Titian and scale/date, but misses the glove, hand, dark costume, and portrait psychology."),
    "cl010062308": ("SPECIFICITY_LOW", "Uses sitter name and artist, but not costume, pose, office, inscription, or Cologne identity."),
    "cl010066647": ("SPECIFICITY_LOW", "Names Titian and medium but does not describe Christ, gaze, wounds, or devotional framing."),
    "cl010091989": ("SPECIFICITY_LOW", "Names sculpture/material/date but not the hunting nymph pose, movement, or marble details."),
    "cl010059589": ("SPECIFICITY_LOW", "Generic philosopher prompt; does not use glasses, facial type, or Giordano's handling."),
    "cl010090779": ("SPECIFICITY_LOW", "Mentions terracotta and date but not Chryses, gesture, or maquette character."),
    "cl010099607": ("SPECIFICITY_LOW", "Does not exploit Trojan horse subject or serial plaque context beyond title."),
    "cl010111542": ("SPECIFICITY_MEDIUM", "Uses complex materials and Byzantine/Gothic dates, but not the paten's liturgical function clearly."),
    "cl010009267": ("SPECIFICITY_MEDIUM", "Uses reign/place/material and statue type, but could point more directly to naos/cube features."),
    "cl010123045": ("SPECIFICITY_MEDIUM", "Uses Ugarit/Hittite letter identity but does not explain cuneiform or diplomatic stakes in the card."),
    "cl010258916": ("SPECIFICITY_LOW", "Uses bucchero and dimensions but no specific visual guidance for calyx shape or surface."),
    "cl010472062": ("SPECIFICITY_MEDIUM", "Uses artist/date/material, but not the Rubens rose/Louvre commission in visitor copy."),
    "cl010060786": ("SPECIFICITY_LOW", "Names Panini and ruins, but does not direct attention to architecture, figures, or preaching scene."),
    "cl010091138": ("SPECIFICITY_LOW", "Names sitter and material, but does not explain effigy, polychromy traces, or funerary context."),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sample_arks() -> list[str]:
    text = SAMPLE.read_text(encoding="utf-8")
    arks = re.findall(r"ARK: `([^`]+)`", text)
    if len(arks) != 20:
        raise SystemExit(f"Expected 20 sample ARKs, found {len(arks)}")
    return arks


def bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def product_review(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Louvre Phase 2B.1 Product Review: Existing 20-Work Sample",
        "",
        "This document shows the exact generated Phase 2B visitor-facing strings. It does not summarize or rewrite them.",
    ]
    for r in records:
        i = r["identity"]
        en = r["content"]["en"]
        fr = r["content"]["fr"]
        zh = r["content"]["zh-Hans"]
        lines.extend(
            [
                "",
                f"## {i['title']}",
                "",
                f"- ARK: `{r['artwork_id']}`",
                f"- Title: {i['title']}",
                f"- Artist: {i.get('artist') or 'NULL'}",
                f"- Department: {i.get('department')}",
                f"- Room: {i.get('room')}",
                f"- Tier: {r.get('visitor_tier')}",
                "",
                "### NORMAL / EN",
                f"**Hook:** {en['hook']}",
                "",
                "**Why it matters**",
            ]
        )
        lines.extend(bullet_list(en["why_it_matters"]))
        lines.extend(["", "**What to notice**"])
        lines.extend(bullet_list(en["what_to_notice"]))
        lines.extend(
            [
                "",
                f"**Context / story:** {en['time_context']} {en['story']}",
                "",
                f"**Rarity / significance:** {en['rarity_significance']}",
                "",
                "### SIMPLE / EN",
                en["simple_mode"],
                "",
                "### KIDS / EN",
                en["kids_mode"],
                "",
                "### AUDIO / EN",
                en["audio_script"],
                "",
                "### FR",
                f"**Accroche:** {fr['hook']}",
                "",
                "**Pourquoi c'est important**",
            ]
        )
        lines.extend(bullet_list(fr["why_it_matters"]))
        lines.extend(["", "**À regarder**"])
        lines.extend(bullet_list(fr["what_to_notice"]))
        lines.extend(
            [
                "",
                f"**Contexte:** {fr['time_context']}",
                "",
                f"**Récit:** {fr['story']}",
                "",
                f"**Importance:** {fr['rarity_significance']}",
                "",
                f"**Simple:** {fr['simple_mode']}",
                "",
                f"**Kids:** {fr['kids_mode']}",
                "",
                f"**Audio:** {fr['audio_script']}",
                "",
                "### ZH-Hans",
                f"**钩子:** {zh['hook']}",
                "",
                "**为什么重要**",
            ]
        )
        lines.extend(bullet_list(zh["why_it_matters"]))
        lines.extend(["", "**看什么**"])
        lines.extend(bullet_list(zh["what_to_notice"]))
        lines.extend(
            [
                "",
                f"**背景:** {zh['time_context']}",
                "",
                f"**故事:** {zh['story']}",
                "",
                f"**意义:** {zh['rarity_significance']}",
                "",
                f"**简明模式:** {zh['simple_mode']}",
                "",
                f"**儿童模式:** {zh['kids_mode']}",
                "",
                f"**音频脚本:** {zh['audio_script']}",
            ]
        )
    return "\n".join(lines) + "\n"


def repetition_audit(records: list[dict[str, Any]]) -> str:
    phrases = Counter()
    examples: defaultdict[str, list[str]] = defaultdict(list)
    checks = {
        "why_work_matters": "The work matters because it is not only an item in",
        "louvre_record_anchors": "Its Louvre record anchors it to",
        "room_evidence": "Its room evidence places it at",
        "start_title": "Start with the title: ask which part of the object actually explains",
        "material_evidence": "Look for the material evidence:",
        "edges_base_frame": "Check the edges, base, frame, or missing parts",
        "simple_you_are_looking": "You are looking at",
        "kids_mission": "Mission: find one detail on",
        "audio_pause": "Pause in front of",
        "audio_photo_close": "choose one detail that would disappear in a quick photograph",
    }
    for r in records:
        text = json.dumps(r["content"]["en"], ensure_ascii=False)
        for key, phrase in checks.items():
            if phrase in text:
                phrases[key] += 1
                examples[key].append(f"{r['artwork_id']} - {r['identity']['title']}")

    lines = [
        "# Louvre Phase 2B.1 Sample Repetition Audit",
        "",
        "Verdict: the sample reads as one scalable template with nouns swapped, not as 20 individually written museum cards.",
        "",
        "## Measured Repetition",
    ]
    for key, count in phrases.most_common():
        lines.append(f"- `{key}`: {count}/20")
        lines.append(f"  Example phrase: {checks[key]}")
        lines.append(f"  Seen in: {', '.join(examples[key][:5])}{'...' if len(examples[key]) > 5 else ''}")
    lines.extend(
        [
            "",
            "## Actual Repeated Structures",
            "",
            "- Nearly every card opens the interpretive core with `The work matters because it is not only an item in [department]`.",
            "- Nearly every `WHAT_TO_NOTICE` begins with title decoding, then material evidence, then edges/base/frame/missing parts.",
            "- Kids mode repeats the same mission skeleton for all 20: find one detail, ask what it is made from.",
            "- Audio repeats `Pause in front of [title]`, `Do not start with the whole story`, and the quick-photograph closing.",
            "- FR/ZH repeat a localization scaffold and do not preserve the full English specificity.",
            "",
            "## Product Impact",
            "",
            "The content is structurally valid but editorially generic. It would make ELYIO feel like a catalog templating system rather than a authored museum guide.",
        ]
    )
    return "\n".join(lines) + "\n"


def factual_depth_audit(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Louvre Phase 2B.1 Factual Depth Audit",
        "",
        "| ARK | Title | Tier | Specific facts used | Category-only facts | Generic statements | Specificity | Notes |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for r in records:
        i = r["identity"]
        score, note = SPECIFICITY[r["artwork_id"]]
        specific = []
        for key in ["artist", "date", "medium", "dimensions", "room", "inventory_number"]:
            if i.get(key):
                specific.append(key)
        category = ["department", "period/material category"]
        generic = ["collection teaches through objects", "look at material and scale", "choose one detail"]
        lines.append(
            f"| `{r['artwork_id']}` | {i['title']} | {r['visitor_tier']} | {', '.join(specific)} | {', '.join(category)} | {', '.join(generic)} | {score} | {note} |"
        )
    lines.extend(
        [
            "",
            "Tier B failure condition: several Tier B rows are SPECIFICITY_LOW. They should not pass without rewrite.",
        ]
    )
    return "\n".join(lines) + "\n"


def quality_audit(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Louvre Phase 2B.1 Visual, Kids, Audio, Localization Audit",
        "",
        "| ARK | Title | Visual Guidance | Kids | Audio | Localization | Verdict |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in records:
        title = r["identity"]["title"]
        visual = "WEAK - prompts are mostly title/material/edges/scale, not object-specific observable details"
        kids = "WEAK - repeated mission, no memorable artwork-specific fact"
        audio = "WEAK - repeated intro/structure/closing, sounds templated"
        loc = "FAIL - FR/ZH are scaffold localizations; ZH leaks French titles, room strings, materials and dates"
        verdict = "REGENERATE" if r["visitor_tier"] == "B" or SPECIFICITY[r["artwork_id"]][0] == "SPECIFICITY_LOW" else "MINOR_EDIT"
        lines.append(f"| `{r['artwork_id']}` | {title} | {visual} | {kids} | {audio} | {loc} | {verdict} |")
    lines.extend(
        [
            "",
            "## Localization Spot Check",
            "",
            "- English leakage: not many raw English sentences, but ZH-Hans contains untranslated French titles, French room labels, French date strings, and source material strings such as `huile sur toile` and `Céramique`.",
            "- Literal translation: FR/ZH use the same sentence architecture across all works.",
            "- Lost visual instructions: FR/ZH do not translate the English `why_it_matters` and `what_to_notice` content faithfully; they use a generic replacement scaffold.",
            "- Title localization: Chinese titles are not established localized titles for the sample; most are French source titles inserted into Chinese prose.",
            "- Automated QA result of zero blocking flags is therefore not product-valid.",
        ]
    )
    return "\n".join(lines) + "\n"


def value_research(records: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    rows = []
    lines = [
        "# Louvre Phase 2B.1 Value Research: 20-Work Sample",
        "",
        "This pass used targeted textual/source research only. No Louvre image bytes, RecognitionAssets, embeddings, production writes, or TTS were created.",
        "",
        "| ARK | Title | Proposed mode | Headline/context | Confidence | Visitor-safe statement | Sources |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in records:
        ark = r["artwork_id"]
        research = VALUE_RESEARCH[ark]
        headline = research["headline"]
        if isinstance(headline, dict):
            headline_text = f"{headline.get('low')} - {headline.get('high')} {research['currency']}"
        elif headline is None:
            headline_text = "None"
        else:
            headline_text = f"{headline:,} {research['currency']}"
        sources = "; ".join(f"[{s['label']}]({s['url']})" for s in research["sources"])
        lines.append(f"| `{ark}` | {r['identity']['title']} | {research['classification']} | {headline_text} | {research['confidence']} | {research['safe_statement']} | {sources} |")
        rows.append(
            {
                "artwork_id": ark,
                "title": r["identity"]["title"],
                "current_phase2b_mode": r["value_reveal"]["mode"],
                "researched_mode": research["classification"],
                "headline": research["headline"],
                "currency": research["currency"],
                "confidence": research["confidence"],
                "relationship_to_artwork": research["relationship"],
                "visitor_safe_statement": research["safe_statement"],
                "sources": research["sources"],
            }
        )
    counts = Counter(row["researched_mode"] for row in rows)
    lines.extend(
        [
            "",
            "## Result",
            "",
            f"- ESTIMATED_VALUE: {counts.get('ESTIMATED_VALUE', 0)}",
            f"- MARKET_CONTEXT: {counts.get('MARKET_CONTEXT', 0)}",
            f"- BEYOND_MARKET: {counts.get('BEYOND_MARKET', 0)}",
            "",
            "Conclusion: the existing Phase 2B value output is not research-complete. The sample supports many MARKET_CONTEXT reveals, not 20/20 BEYOND_MARKET.",
        ]
    )
    return "\n".join(lines) + "\n", rows


def golden_comparison(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Louvre Phase 2B.1 Golden 20 Comparison",
        "",
        "| Dimension | Golden 20 score | Phase 2B sample score | Assessment |",
        "|---|---:|---:|---|",
        "| Factual specificity | 8 | 3 | Golden cards use artwork-specific looking claims; sample mostly uses metadata slots. |",
        "| Editorial quality | 8 | 3 | Sample has repeated scaffolds and generic museum-guide language. |",
        "| Visual usefulness | 8 | 3 | Golden sends eyes to concrete details; sample says title/material/scale repeatedly. |",
        "| Kids quality | 7 | 2 | Sample repeats one mission and lacks memorable artwork facts. |",
        "| Audio quality | 8 | 3 | Sample scripts are structurally identical and not natural authored narration. |",
        "| Localization quality | 5 | 2 | Golden was deterministic but cleaner; sample ZH/FR visibly leak source-language fragments and scaffold text. |",
        "| Source traceability | 8 | 7 | Phase 2B source bundles exist, but content does not use enough of them. |",
        "| Value WOW | 7 | 1 | Sample defaulted to BEYOND_MARKET without research. |",
        "| Value honesty | 9 | 7 | The fallback is safe, but under-researched and product-poor. |",
        "",
        "## Did Quality Degrade When We Scaled?",
        "",
        "YES.",
        "",
        "The scale run preserved schema and safety, but degraded product quality. The output is traceable and non-destructive, yet it reads like templated metadata prose. Value research did not run for the sample until this quality gate.",
    ]
    return "\n".join(lines) + "\n"


def final_report(records: list[dict[str, Any]], value_rows: list[dict[str, Any]]) -> str:
    value_counts = Counter(r["researched_mode"] for r in value_rows)
    classifications = {}
    for r in records:
        spec = SPECIFICITY[r["artwork_id"]][0]
        if r["visitor_tier"] == "B":
            classifications[r["artwork_id"]] = "REGENERATE"
        elif spec == "SPECIFICITY_LOW":
            classifications[r["artwork_id"]] = "REGENERATE"
        elif spec == "SPECIFICITY_MEDIUM":
            classifications[r["artwork_id"]] = "MINOR_EDIT"
        else:
            classifications[r["artwork_id"]] = "PRODUCTION_READY"
    class_counts = Counter(classifications.values())
    lines = [
        "# Louvre Phase 2B.1 Quality Gate Final Report",
        "",
        f"Generated at: `{GENERATED_AT}`",
        "",
        "## Scope",
        "",
        "- Reviewed the existing `louvre_phase2b_review_sample_20.md` membership.",
        "- Did not modify the existing 480 Phase 2B files.",
        "- Wrote audit artifacts only under `exports/louvre/content/phase2b/quality_gate/`.",
        "- No production writes, catalog changes, RecognitionAssets, embeddings, TTS, or Louvre image-byte fetching.",
        "",
        "## Value Research Result",
        "",
        f"- ESTIMATED_VALUE: {value_counts.get('ESTIMATED_VALUE', 0)}",
        f"- MARKET_CONTEXT: {value_counts.get('MARKET_CONTEXT', 0)}",
        f"- BEYOND_MARKET: {value_counts.get('BEYOND_MARKET', 0)}",
        "",
        f"Meaningful monetary context found: {value_counts.get('MARKET_CONTEXT', 0)} / 20.",
        "Defensible artwork-specific estimated values found: 0 / 20.",
        "",
        "## Production Classification",
        "",
        f"- PRODUCTION_READY: {class_counts.get('PRODUCTION_READY', 0)}",
        f"- MINOR_EDIT: {class_counts.get('MINOR_EDIT', 0)}",
        f"- REGENERATE: {class_counts.get('REGENERATE', 0)}",
        f"- INSUFFICIENT_SOURCE: {class_counts.get('INSUFFICIENT_SOURCE', 0)}",
        "",
        "| ARK | Title | Tier | Classification | Reason |",
        "|---|---|---:|---|---|",
    ]
    for r in records:
        lines.append(f"| `{r['artwork_id']}` | {r['identity']['title']} | {r['visitor_tier']} | {classifications[r['artwork_id']]} | {SPECIFICITY[r['artwork_id']][1]} |")
    lines.extend(
        [
            "",
            "## Overall Recommendation",
            "",
            "C - scaled generation quality is unacceptable and must be rebuilt before production.",
            "",
            "The schema/export run succeeded, but the content pipeline did not meet the Golden 20 standard. The main failures are templated prose, low object-specific visual guidance, weak kids/audio variation, localization scaffolding, and missing value research.",
            "",
            "## Safety Confirmation",
            "",
            "- Existing 480 files modified: 0",
            "- Production writes: 0",
            "- Catalog membership changes: 0",
            "- RecognitionAssets created: 0",
            "- Embeddings created: 0",
            "- TTS/audio bytes generated: 0",
            "- Louvre image bytes fetched: 0",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    arks = sample_arks()
    all_records = {r["artwork_id"]: r for r in read_jsonl(RECORDS)}
    records = [all_records[ark] for ark in arks]

    (OUT / "louvre_phase2b_sample_product_review.md").write_text(product_review(records), encoding="utf-8")
    (OUT / "louvre_phase2b_sample_repetition_audit.md").write_text(repetition_audit(records), encoding="utf-8")
    (OUT / "louvre_phase2b_sample_factual_depth_audit.md").write_text(factual_depth_audit(records), encoding="utf-8")
    (OUT / "louvre_phase2b_sample_visual_kids_audio_localization_audit.md").write_text(quality_audit(records), encoding="utf-8")
    value_md, value_rows = value_research(records)
    (OUT / "louvre_phase2b_sample_value_research.md").write_text(value_md, encoding="utf-8")
    with (OUT / "louvre_phase2b_sample_value_research.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for row in value_rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    (OUT / "louvre_phase2b_sample_golden20_comparison.md").write_text(golden_comparison(records), encoding="utf-8")
    (OUT / "louvre_phase2b_quality_gate_final_report.md").write_text(final_report(records, value_rows), encoding="utf-8")
    manifest = {
        "generated_at": GENERATED_AT,
        "sample_source": str(SAMPLE.relative_to(ROOT)),
        "sample_arks": arks,
        "outputs": sorted(p.name for p in OUT.iterdir() if p.is_file()),
        "safety": {
            "existing_480_files_modified": 0,
            "production_writes": 0,
            "catalog_membership_changes": 0,
            "recognition_assets_created": 0,
            "embeddings_created": 0,
            "tts_audio_bytes_generated": 0,
            "louvre_image_bytes_fetched": 0,
        },
    }
    (OUT / "louvre_phase2b_quality_gate_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records_reviewed": len(records), "value_modes": Counter(r["researched_mode"] for r in value_rows), "outputs": manifest["outputs"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
