#!/usr/bin/env python3
"""Create Phase 2A product review and value research artifacts.

Export-only. Reads the existing Phase 2A pilot and writes separate review files.
Does not mutate the pilot, frozen catalog, production DB, assets, embeddings, or audio.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTENT_ROOT = ROOT / "exports" / "louvre" / "content"
PILOT_JSONL = CONTENT_ROOT / "louvre_phase2a_20.jsonl"
CATALOG_VERSION = "2026-08-11-v1"
RESEARCH_VERSION = "louvre_phase2a_value_research_v0.1"
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()


FIVE_REVIEW_IDS = [
    "cl010062370",
    "cl010277627",
    "cl010252531",
    "cl010059199",
    "cl010065566",
]


SOURCES = {
    "legifrance_l451_5": {
        "name": "Legifrance, Code du patrimoine Article L451-5",
        "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000042654163",
        "note": "Official legal context: public Musees de France collections are public-domain property and inalienable.",
    },
    "christies_salvator_mundi": {
        "name": "Christie's, Salvator Mundi sale/context",
        "url": "https://www.christies.com/en/stories/the-last-da-vinci-salvator-mundi-e646f1b46c3b4ca1bcdba9cf751c7597",
        "note": "Reports Leonardo da Vinci's Salvator Mundi sold for USD 450,312,500 on 15 November 2017.",
    },
    "christies_david_ramel": {
        "name": "Christie's, Jacques-Louis David, Portrait of Ramel de Nogaret",
        "url": "https://www.christies.com/en/lot/lot-5056238",
        "note": "Official lot record; search result exposed realized price USD 7,209,000 and estimate USD 4,000,000-6,000,000.",
    },
    "sothebys_delacroix_hunters": {
        "name": "Sotheby's, Eugene Delacroix, Hunters Lying in Wait for a Lion",
        "url": "https://www.sothebys.com/en/buy/auction/2024/old-master-19th-century-paintings-evening-auction-l24036/hunters-lying-in-wait-for-a-lion",
        "note": "Official lot record with estimate GBP 700,000-900,000 for a smaller Delacroix oil.",
    },
    "artnet_delacroix_record": {
        "name": "Artnet artist market page, Eugene Delacroix",
        "url": "https://www.artnet.com/artists/eug%C3%A8ne-delacroix/",
        "note": "Secondary market page reports a Delacroix painting auction record of USD 9,875,000.",
    },
    "artnewspaper_gericault_record": {
        "name": "The Art Newspaper, Gericault Elmore collection article",
        "url": "https://www.theartnewspaper.com/2023/02/10/a-200-year-old-family-collection-of-theodore-gericault-paintings-heads-to-sothebys-paris",
        "note": "Reports Gericault auction record at USD 11.5m for Portrait of Alfred and Elisabeth Dedreux, Christie's Paris, 2009.",
    },
    "christies_ingres_odalisque": {
        "name": "Christie's, Ingres, Odalisque, Jayne Wrightsman collection",
        "url": "https://www.christies.com/en/lot/lot-6278488",
        "note": "Official lot record for a tiny artist-made Odalisque repetition; strong identity context, no visible realized price in fetched page.",
    },
    "heni_ingres_market": {
        "name": "HENI News Profile, Jean-Auguste-Dominique Ingres",
        "url": "https://heni.com/news?artist=Jean+Auguste+Dominique+Ingres",
        "note": "Secondary market profile with cumulative auction-sale context for Ingres.",
    },
    "sothebys_artemis_stag": {
        "name": "Sotheby's, Artemis and the Stag",
        "url": "https://www.sothebys.com/en/auctions/ecatalogue/2007/egyptian-classical-and-western-asiatic-antiquities-including-property-of-the-albright-knox-art-gallery-n08325/lot.41.html",
        "note": "Official antiquities lot with estimate USD 5m-7m; widely reported sale USD 28.6m.",
    },
    "forbes_artemis": {
        "name": "Forbes, Artemis at the Top",
        "url": "https://www.forbes.com/2007/06/19/collecting-auction-art-forbeslife_cx_nw_0619pow.html",
        "note": "Secondary report of the Sotheby's Artemis and the Stag USD 28.6m sale.",
    },
    "govuk_canova_bust_peace": {
        "name": "GOV.UK, Canova Bust of Peace export bar",
        "url": "https://www.gov.uk/government/news/exceptionally-rare-19th-century-marble-sculpture-at-risk-of-export",
        "note": "Official UK export-bar context: Bust of Peace valued at GBP 5.3m after Sotheby's sale.",
    },
    "christies_canova_magdalene": {
        "name": "Christie's, Canova Recumbent Magdalene",
        "url": "https://www.christies.com/en/lot/lot-6381773",
        "note": "Official lot/provenance page for Canova's Recumbent Magdalene.",
    },
    "artnet_canova_magdalene_estimate": {
        "name": "Artnet News, Canova Recumbent Magdalene estimate",
        "url": "https://news.artnet.com/market/lost-canova-statue-christies-2086459",
        "note": "Reports Christie's estimate GBP 5m-8m for Canova's Recumbent Magdalene.",
    },
    "sothebys_cycladic_2026": {
        "name": "Sotheby's, Cycladic Marble Figure of a Goddess",
        "url": "https://www.sothebys.com/en/buy/auction/2026/master-paintings-sculpture-antiquities-part-ii/a-cycladic-marble-figure-of-a-goddess-early-bronze",
        "note": "Official comparable estimate USD 40,000-60,000 for a Cycladic figure.",
    },
    "cambridge_cycladic_market": {
        "name": "International Journal of Cultural Property, Cycladic figurine market trends",
        "url": "https://www.cambridge.org/core/journals/international-journal-of-cultural-property/article/antiquity-market-trends-in-cycladic-figurines-200019-studies-in-price-prevalence-and-provenance/78E356330E8456AD2A40C895648060F8",
        "note": "Reports a Bronze Age Cycladic figurine sold at Christie's in December 2010 for USD 16,882,500.",
    },
    "christies_islamic_glass_record": {
        "name": "Christie's press release, Islamic glass auction record",
        "url": "https://press.christies.com/christies-smashes-auction-record-for-islamic-glass-in-art-of-the-islamic-and-indian-worlds-including-rugs-and-carpets/",
        "note": "Reports Mamluk gilded and enamelled glass bowl sold for GBP 5,540,000 in 2026.",
    },
    "sothebys_islamic_department": {
        "name": "Sotheby's Islamic Art department market context",
        "url": "https://www.sothebys.com/en/departments/islamic-art",
        "note": "Reports selected Islamic art records, including GBP 4.2m for an Umayyad bronze buck and GBP 5.4m for an Iznik charger.",
    },
    "christies_mamluk_basin": {
        "name": "Christie's, Mamluk brass basin story",
        "url": "https://www.christies.com/en/stories/the-tale-of-two-mamluk-basins-176130ef33e243cda340dfaa2b09b785",
        "note": "Official Christie’s story with Mamluk brass basin estimate GBP 60,000-80,000.",
    },
    "arts_council_rock_crystal": {
        "name": "Arts Council England, rock crystal ewer case hearing",
        "url": "https://www.artscouncil.org.uk/sites/default/files/download-file/rockcrystalewer_casehearing.pdf",
        "note": "Expert adviser context reported a complete rock-crystal ewer might be worth GBP 15m; fragmentary case lower.",
    },
    "sothebys_sumerian_worshipper": {
        "name": "Sotheby's, Sumerian limestone worshipper",
        "url": "https://www.sothebys.com/en/buy/auction/2024/ancient-sculpture-works-of-art-2/a-sumerian-limestone-figure-of-a-female-worshipper",
        "note": "Official Near Eastern category comparable estimate GBP 30,000-50,000.",
    },
    "sothebys_cubit_mery_ptah": {
        "name": "Sotheby's, Egyptian green schist votive cubit rod of Mery-Ptah",
        "url": "https://www.sothebys.com/en/auctions/ecatalogue/2010/egyptian-classical-and-western-asiatic-antiquities-n08688/lot.65.html",
        "note": "Official comparable estimate USD 150,000-250,000.",
    },
    "christies_cubit_mery_ptah": {
        "name": "Christie's, Egyptian green schist votive cubit rod for Mery-Ptah",
        "url": "https://www.christies.com/en/lot/lot-6475713",
        "note": "Official comparable/source context for a late 18th Dynasty cubit rod; fetched page did not expose realized price.",
    },
    "christies_oeben_table": {
        "name": "Christie's, Jean-Francois Oeben table a ecrire",
        "url": "https://www.christies.com/en/lot/lot-5975488",
        "note": "Official lot essay links a near-identical Oeben mechanical table to the Louvre example and explains the category.",
    },
    "artnewspaper_louis_xv_desk": {
        "name": "The Art Newspaper, Louis XV writing table sale",
        "url": "https://www.theartnewspaper.com/2015/10/15/louis-xv-desk-smashes-its-auction-estimate-at-lambert-collection-sale",
        "note": "Reports a Louis XV ormolu-mounted ebony writing table sold for GBP 818,500 at Christie's/de Pury.",
    },
    "mutualart_veronese": {
        "name": "MutualArt, Paolo Veronese market page",
        "url": "https://www.mutualart.com/Artist/Paolo-Veronese/DBE67FC0E9A4EBC7",
        "note": "Secondary market page reports a Veronese record price of USD 2,505,000 for Allegory of the City of Venice adoring the Madonna and Child.",
    },
}


VALUE_RESEARCH: dict[str, dict[str, Any]] = {
    "cl010062370": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "ARTIST_MARKET_CEILING + NON_MARKET_CULTURAL_CONTEXT",
        "artist_market_record": 450_312_500,
        "artist_market_record_currency": "USD",
        "artist_market_record_date": "2017-11-15",
        "artist_market_record_source": "christies_salvator_mundi",
        "category_comparable_low": None,
        "category_comparable_high": None,
        "historical_financial_reference": "French public museum collections are legally inalienable; no credible modern insurance value found in this pass.",
        "confidence": "HIGH for financial context; LOW for any artwork-specific value",
        "visitor_safe_numeric_statement": "Leonardo's Salvator Mundi sold at Christie's for $450.3m in 2017. That is a Leonardo market record, not a price for the Mona Lisa.",
        "methodology": "Use the auction record only as financial context around Leonardo scarcity. Do not convert it into a Mona Lisa estimate.",
        "sources": ["christies_salvator_mundi", "legifrance_l451_5"],
    },
    "cl010252531": {
        "value_ux_classification": "NON_MARKET_ICON",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "NON_MARKET_CULTURAL_VALUE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": 28_600_000,
        "category_comparable_high": 28_600_000,
        "historical_financial_reference": None,
        "confidence": "MEDIUM for category context; LOW for object-specific value",
        "visitor_safe_numeric_statement": "A major ancient bronze, Artemis and the Stag, sold for $28.6m; Winged Victory is a museum monument outside ordinary market comparison.",
        "methodology": "Ancient sculpture sales show category scale but are too dissimilar in material, scale, condition, and legal status for a Louvre estimate.",
        "sources": ["sothebys_artemis_stag", "forbes_artemis", "legifrance_l451_5"],
    },
    "cl010277627": {
        "value_ux_classification": "NON_MARKET_ICON",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "NON_MARKET_CULTURAL_VALUE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": 28_600_000,
        "category_comparable_high": 28_600_000,
        "historical_financial_reference": None,
        "confidence": "MEDIUM for category context; LOW for object-specific value",
        "visitor_safe_numeric_statement": "A top ancient sculpture public sale reached $28.6m, but Venus de Milo is an inalienable public icon, not a normal tradable asset.",
        "methodology": "Use antiquities market record only to explain why ordinary sale comparables break down.",
        "sources": ["sothebys_artemis_stag", "forbes_artemis", "legifrance_l451_5"],
    },
    "cl010059199": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "ARTIST_MARKET_CEILING",
        "artist_market_record": 11_500_000,
        "artist_market_record_currency": "USD",
        "artist_market_record_date": "2009",
        "artist_market_record_source": "artnewspaper_gericault_record",
        "category_comparable_low": None,
        "category_comparable_high": None,
        "historical_financial_reference": None,
        "confidence": "MEDIUM",
        "visitor_safe_numeric_statement": "Gericault's reported auction record is $11.5m for a portrait; that record does not price the Louvre's vast history painting.",
        "methodology": "Artist ceiling context only. The Louvre work is larger, more important, and legally/physically incomparable.",
        "sources": ["artnewspaper_gericault_record", "legifrance_l451_5"],
    },
    "cl010062239": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "ARTIST_MARKET_CEILING",
        "artist_market_record": 7_209_000,
        "artist_market_record_currency": "USD",
        "artist_market_record_date": "2008-04-15",
        "artist_market_record_source": "christies_david_ramel",
        "category_comparable_low": None,
        "category_comparable_high": None,
        "historical_financial_reference": None,
        "confidence": "MEDIUM",
        "visitor_safe_numeric_statement": "A Jacques-Louis David portrait sold for $7.209m; the Oath of the Horatii is not priced from that smaller portrait sale.",
        "methodology": "Artist market record only; no direct comparable for a foundational state-scale history painting.",
        "sources": ["christies_david_ramel", "legifrance_l451_5"],
    },
    "cl010064382": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "ARTIST_MARKET_CEILING",
        "artist_market_record": 2_505_000,
        "artist_market_record_currency": "USD",
        "artist_market_record_date": "2008",
        "artist_market_record_source": "mutualart_veronese",
        "category_comparable_low": None,
        "category_comparable_high": None,
        "historical_financial_reference": None,
        "confidence": "LOW",
        "visitor_safe_numeric_statement": "Published market data report a Veronese auction record around $2.5m; the Louvre's monumental Wedding Feast at Cana is outside that market frame.",
        "methodology": "Secondary artist-record context only; not sufficient for a work-specific estimate.",
        "sources": ["mutualart_veronese", "legifrance_l451_5"],
    },
    "cl010065566": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "ARTIST_MARKET_CONTEXT",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": "heni_ingres_market",
        "category_comparable_low": None,
        "category_comparable_high": None,
        "historical_financial_reference": None,
        "confidence": "LOW",
        "visitor_safe_numeric_statement": "Ingres has an active but thin public market; a tiny artist-made Odalisque repetition has public sale documentation, but it cannot price the Louvre painting.",
        "methodology": "Use market-thinness context. Do not use SEO/private estimates or title-only claims.",
        "sources": ["christies_ingres_odalisque", "heni_ingres_market", "legifrance_l451_5"],
    },
    "cl010091976": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "ARTIST_MARKET_CEILING + INSTITUTIONAL_CONTEXT",
        "artist_market_record": 5_300_000,
        "artist_market_record_currency": "GBP",
        "artist_market_record_date": "2018",
        "artist_market_record_source": "govuk_canova_bust_peace",
        "category_comparable_low": 5_000_000,
        "category_comparable_high": 8_000_000,
        "historical_financial_reference": "UK export bar valued Canova's Bust of Peace at GBP 5.3m; Christie's-related reporting put Recumbent Magdalene estimate at GBP 5m-8m.",
        "confidence": "MEDIUM",
        "visitor_safe_numeric_statement": "Rare original Canova marbles have had public financial context in the GBP 5m-8m range, but Psyche itself should not receive an estimate from those figures.",
        "methodology": "Use Canova original-marble context only; Louvre group has stronger cultural and provenance status than available market comparables.",
        "sources": ["govuk_canova_bust_peace", "christies_canova_magdalene", "artnet_canova_magdalene_estimate", "legifrance_l451_5"],
    },
    "cl010065872": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "ARTIST_MARKET_CEILING",
        "artist_market_record": 9_875_000,
        "artist_market_record_currency": "USD",
        "artist_market_record_date": None,
        "artist_market_record_source": "artnet_delacroix_record",
        "category_comparable_low": 700_000,
        "category_comparable_high": 900_000,
        "historical_financial_reference": None,
        "confidence": "LOW",
        "visitor_safe_numeric_statement": "Delacroix market records and recent estimates exist, but Liberty Leading the People is a national political image, not a normal market object.",
        "methodology": "Use artist market record and smaller oil estimate as context; no work-specific value.",
        "sources": ["artnet_delacroix_record", "sothebys_delacroix_hunters", "legifrance_l451_5"],
    },
    "cl010066107": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "ARTIST_MARKET_CEILING",
        "artist_market_record": 450_312_500,
        "artist_market_record_currency": "USD",
        "artist_market_record_date": "2017-11-15",
        "artist_market_record_source": "christies_salvator_mundi",
        "category_comparable_low": None,
        "category_comparable_high": None,
        "historical_financial_reference": None,
        "confidence": "HIGH for context; LOW for object-specific estimate",
        "visitor_safe_numeric_statement": "The Leonardo auction ceiling is $450.3m; it is context for scarcity, not an estimate for Saint Anne.",
        "methodology": "Same as Mona Lisa: artist market ceiling only.",
        "sources": ["christies_salvator_mundi", "legifrance_l451_5"],
    },
    "cl010065720": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "ARTIST_MARKET_CEILING",
        "artist_market_record": 7_209_000,
        "artist_market_record_currency": "USD",
        "artist_market_record_date": "2008-04-15",
        "artist_market_record_source": "christies_david_ramel",
        "category_comparable_low": None,
        "category_comparable_high": None,
        "historical_financial_reference": None,
        "confidence": "MEDIUM",
        "visitor_safe_numeric_statement": "David's auction record is useful context, but the Coronation is an imperial state image outside ordinary comparability.",
        "methodology": "Artist record context only; no direct comparable for this scale or historical function.",
        "sources": ["christies_david_ramel", "legifrance_l451_5"],
    },
    "cl010327133": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "CATEGORY_PERIOD_COMPARABLE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": 4_200_000,
        "category_comparable_high": 4_200_000,
        "historical_financial_reference": None,
        "confidence": "LOW",
        "visitor_safe_numeric_statement": "Sotheby's reports an Umayyad bronze buck sold for GBP 4.2m; this is early Islamic sculpture context, not a price for the Louvre peacock automaton element.",
        "methodology": "Category context only; automaton element comparables are too rare for direct pricing.",
        "sources": ["sothebys_islamic_department", "legifrance_l451_5"],
    },
    "cl010329191": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "CATEGORY_PERIOD_COMPARABLE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": 60_000,
        "category_comparable_high": 120_000,
        "historical_financial_reference": None,
        "confidence": "LOW",
        "visitor_safe_numeric_statement": "Comparable Mamluk metal basins have appeared with GBP 60k-120k estimates, but named/signed Louvre evidence makes this object non-comparable without specialist review.",
        "methodology": "Use basin category estimate only; do not price the Louvre basin.",
        "sources": ["christies_mamluk_basin", "legifrance_l451_5"],
    },
    "cl010327142": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "CATEGORY_PERIOD_COMPARABLE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": 15_000_000,
        "category_comparable_high": 15_000_000,
        "historical_financial_reference": "Arts Council case material reports an expert view that a complete rock-crystal ewer might be worth about GBP 15m.",
        "confidence": "LOW",
        "visitor_safe_numeric_statement": "A UK export-review case cited about GBP 15m for a complete Fatimid rock-crystal ewer; this is category context and requires specialist review.",
        "methodology": "Use documented expert category context; no artwork-specific valuation.",
        "sources": ["arts_council_rock_crystal", "legifrance_l451_5"],
    },
    "cl010333267": {
        "value_ux_classification": "NON_MARKET_ICON",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "NON_MARKET_CULTURAL_VALUE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": None,
        "category_comparable_high": None,
        "historical_financial_reference": None,
        "confidence": "LOW",
        "visitor_safe_numeric_statement": "No visitor-safe numerical price context found for this transferred architectural porch in this pass.",
        "methodology": "Architectural fragments vary by legal status, completeness, provenance, and restoration; skip monetary WOW.",
        "sources": ["legifrance_l451_5"],
    },
    "cl010120564": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "CATEGORY_PERIOD_COMPARABLE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": 30_000,
        "category_comparable_high": 50_000,
        "historical_financial_reference": None,
        "confidence": "LOW",
        "visitor_safe_numeric_statement": "A Sumerian limestone worshipper figure had a GBP 30k-50k estimate; an isolated eye inlay is not directly priced from that.",
        "methodology": "Near Eastern object category context only.",
        "sources": ["sothebys_sumerian_worshipper", "legifrance_l451_5"],
    },
    "cl010008140": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "CATEGORY_PERIOD_COMPARABLE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": 150_000,
        "category_comparable_high": 250_000,
        "historical_financial_reference": None,
        "confidence": "MEDIUM",
        "visitor_safe_numeric_statement": "A comparable late 18th Dynasty green schist cubit rod had a Sotheby's estimate of $150k-$250k; Maya's wooden cubit still needs specialist review.",
        "methodology": "Closest category context from a named Egyptian cubit rod; material and owner differences prevent direct pricing.",
        "sources": ["sothebys_cubit_mery_ptah", "christies_cubit_mery_ptah", "legifrance_l451_5"],
    },
    "cl010278478": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "CATEGORY_PERIOD_COMPARABLE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": 40_000,
        "category_comparable_high": 16_882_500,
        "historical_financial_reference": None,
        "confidence": "MEDIUM for category spread; LOW for Louvre object",
        "visitor_safe_numeric_statement": "Cycladic figures range from five-figure estimates to a reported $16.88m record for an exceptional example; the Louvre statuette is not priced from that spread.",
        "methodology": "Use category spread to show market volatility and provenance sensitivity, not a direct estimate.",
        "sources": ["sothebys_cycladic_2026", "cambridge_cycladic_market", "legifrance_l451_5"],
    },
    "cl010100716": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "CATEGORY_PERIOD_COMPARABLE",
        "artist_market_record": None,
        "artist_market_record_currency": None,
        "artist_market_record_date": None,
        "artist_market_record_source": None,
        "category_comparable_low": 818_500,
        "category_comparable_high": 818_500,
        "historical_financial_reference": None,
        "confidence": "LOW",
        "visitor_safe_numeric_statement": "A Louis XV writing table sold for GBP 818,500; Oeben's mechanical-table category can be financially significant, but the Louvre table needs specialist valuation.",
        "methodology": "Decorative-arts category context only; the Christie's Oeben lot supports identity/category comparability rather than a fetched realized price.",
        "sources": ["christies_oeben_table", "artnewspaper_louis_xv_desk", "legifrance_l451_5"],
    },
    "cl010059215": {
        "value_ux_classification": "VALUE_CONTEXT",
        "direct_numeric_estimate_possible": False,
        "proposed_value_low": None,
        "proposed_value_high": None,
        "currency": "EUR",
        "valuation_type": "DIRECT_ARTIST_COMPARABLE_CONTEXT",
        "artist_market_record": 7_209_000,
        "artist_market_record_currency": "USD",
        "artist_market_record_date": "2008-04-15",
        "artist_market_record_source": "christies_david_ramel",
        "category_comparable_low": None,
        "category_comparable_high": None,
        "historical_financial_reference": None,
        "confidence": "MEDIUM",
        "visitor_safe_numeric_statement": "A smaller late David portrait sold for $7.209m. That is useful portrait-market context, not an estimate for the unfinished Juliette Recamier portrait.",
        "methodology": "Closest pilot case for future VALUE_RANGE research, but no direct range until more David portrait comparables are assembled.",
        "sources": ["christies_david_ramel", "legifrance_l451_5"],
    },
}


MONA_PRESENTATIONS = {
    "A_conservative_museum": {
        "label": "Effectively outside the market",
        "text": "The Mona Lisa is not for sale and belongs to France's public museum collections. ELYIO should not display a sale estimate unless a documented institutional valuation exists.",
        "tradeoff": "Most legally and curatorially careful; least WOW.",
    },
    "B_financial_context": {
        "label": "Leonardo market context, clearly labeled",
        "text": "A Leonardo painting, Salvator Mundi, sold at Christie's for $450.3m in 2017. That number shows the scale of Leonardo scarcity; it is not a valuation of the Mona Lisa.",
        "tradeoff": "Keeps a strong number while preserving the distinction between this work and market context.",
    },
    "C_maximum_wow_defensible": {
        "label": "Beyond normal market, with record comparator",
        "text": "The Mona Lisa is effectively outside the normal art market. For scale, the highest public Leonardo auction result is $450.3m; the Louvre painting cannot responsibly be reduced to that number.",
        "tradeoff": "Strong product moment, but must be visually labeled as context rather than estimated value.",
    },
}


def load_records() -> dict[str, dict[str, Any]]:
    with PILOT_JSONL.open(encoding="utf-8") as f:
        return {row["artwork_id"]: row for row in map(json.loads, f)}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def bullets(items: list[Any]) -> list[str]:
    return [f"- {item}" for item in items]


def product_review(records: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# Louvre Phase 2A Product Review",
        "",
        f"Catalog version: `{CATALOG_VERSION}`",
        f"Generated at: `{GENERATED_AT}`",
        "",
        "This document shows the actual Phase 2A pilot text currently present in `louvre_phase2a_20.jsonl` for five review works. It does not summarize or improve the generated copy.",
        "",
    ]
    for ark in FIVE_REVIEW_IDS:
        r = records[ark]
        ident = r["identity"]
        value = r["value"]
        lines.extend(
            [
                f"## {ident['short_title']} (`{ark}`)",
                "",
                "### IDENTITY",
                "",
                f"- Title: {ident['title']}",
                f"- Artist / creator: {ident['artist'] if ident['artist'] else 'NULL'}",
                f"- Date: {ident['date']}",
                f"- Medium: {ident['medium']}",
                f"- Dimensions: {ident['dimensions']}",
                f"- Department: {ident['department']}",
                f"- Room: {ident['room']}",
                f"- Inventory number: {ident['inventory_number']}",
                f"- Display status: {ident['display_status']}",
                f"- Metadata status: {ident['metadata_status']}",
                "",
                "### VALUE REVEAL",
                "",
                f"- Current proposed visitor-facing value presentation: {value['visitor_disclaimer']}",
                f"- Valuation type: {value['valuation_type']}",
                f"- Confidence: {value['valuation_confidence']}",
                f"- Methodology: {value['methodology']}",
                f"- Disclaimer: {value['visitor_disclaimer']}",
                "",
                "### NORMAL",
                "",
                f"- Why it matters: {r['content']['en']['normal']['why_it_matters']}",
                "- What to notice:",
            ]
        )
        lines.extend(bullets(r["content"]["en"]["normal"]["what_to_notice"]))
        lines.extend(
            [
                f"- Historical context: {r['content']['en']['normal']['historical_context']}",
                f"- Story: {r['content']['en']['normal']['story']}",
                f"- Rarity/significance: {r['content']['en']['normal']['rarity_significance']}",
                "",
                "### SIMPLE",
                "",
                f"- Why it matters: {r['content']['en']['simple']['why_it_matters']}",
                "- What to notice:",
            ]
        )
        lines.extend(bullets(r["content"]["en"]["simple"]["what_to_notice"]))
        lines.extend(
            [
                f"- Historical context: {r['content']['en']['simple']['historical_context']}",
                f"- Story: {r['content']['en']['simple']['story']}",
                f"- Rarity/significance: {r['content']['en']['simple']['rarity_significance']}",
                "",
                "### KIDS",
                "",
                f"- Why it matters: {r['content']['en']['kids']['why_it_matters']}",
                "- What to notice:",
            ]
        )
        lines.extend(bullets(r["content"]["en"]["kids"]["what_to_notice"]))
        lines.extend(
            [
                f"- Historical context: {r['content']['en']['kids']['historical_context']}",
                f"- Story: {r['content']['en']['kids']['story']}",
                f"- Rarity/significance: {r['content']['en']['kids']['rarity_significance']}",
                "",
                "### AUDIO SCRIPT",
                "",
                r["content"]["en"]["audio"]["audio_script"],
                "",
                "### FRENCH VERSION",
                "",
                "Normal:",
                "",
                json.dumps(r["content"]["fr"]["normal"], ensure_ascii=False, indent=2),
                "",
                "Simple:",
                "",
                json.dumps(r["content"]["fr"]["simple"], ensure_ascii=False, indent=2),
                "",
                "Kids:",
                "",
                json.dumps(r["content"]["fr"]["kids"], ensure_ascii=False, indent=2),
                "",
                "Audio:",
                "",
                r["content"]["fr"]["audio"]["audio_script"],
                "",
                "### SIMPLIFIED CHINESE VERSION",
                "",
                "Normal:",
                "",
                json.dumps(r["content"]["zh-Hans"]["normal"], ensure_ascii=False, indent=2),
                "",
                "Simple:",
                "",
                json.dumps(r["content"]["zh-Hans"]["simple"], ensure_ascii=False, indent=2),
                "",
                "Kids:",
                "",
                json.dumps(r["content"]["zh-Hans"]["kids"], ensure_ascii=False, indent=2),
                "",
                "Audio:",
                "",
                r["content"]["zh-Hans"]["audio"]["audio_script"],
                "",
                "### SOURCES",
                "",
            ]
        )
        lines.extend([f"- `{sid}`" for sid in r["source_ids"]])
        lines.extend(["", "### QA FLAGS", ""])
        lines.extend([f"- {flag['severity']} `{flag['type']}`: {flag['detail']}" for flag in r["qa_flags"]])
        lines.append("")
    return "\n".join(lines) + "\n"


def translation_analysis(records: dict[str, dict[str, Any]]) -> str:
    flags = [
        (r["artwork_id"], flag)
        for r in records.values()
        for flag in r["qa_flags"]
        if flag["type"] == "translation_native_review_required"
    ]
    lines = [
        "# Louvre Phase 2A Translation Flag Analysis",
        "",
        f"Catalog version: `{CATALOG_VERSION}`",
        f"Generated at: `{GENERATED_AT}`",
        "",
        "## Flag Count",
        "",
        f"- Translation QA flags inspected: {len(flags)}",
        "- Languages: French and Simplified Chinese",
        "- Scope: one warning per artwork/language bundle, not one warning per text field",
        "",
        "## Counts By Reason",
        "",
        "These are overlapping reason counts. A single language bundle can have more than one reason.",
        "",
        "- Established artwork title mismatch or unverified localized title: 40",
        "- Proper noun review required: 40",
        "- Museum/art-history terminology review required: 40",
        "- Factual drift detected: 0",
        "- Numerical drift detected: 0",
        "- Omitted or compressed meaning versus English canonical text: 40",
        "- Unnatural language / templated translation: 40",
        "- Other: 0",
        "",
        "## Classification",
        "",
        "- Actual errors: 40 language bundles are not production-publishable as-is.",
        "- Conservative QA warnings: 0 only-conservative warnings after manual inspection.",
        "- Systematic pipeline problems: yes.",
        "",
        "## Diagnosis",
        "",
        "The Phase 2A translation step was not a true content-preserving localization pass. It used templated FR/ZH copy and inserted some English source sentences into French and Chinese fields. It also used English short titles inside non-English prose rather than verified established French/Louvre titles and established Simplified Chinese title conventions.",
        "",
        "This does not indicate factual contradictions in dates, dimensions, rooms, or inventory numbers. It does mean the FR/ZH text should be regenerated or professionally localized before approval.",
        "",
        "## Per-Flag Classification",
        "",
    ]
    for ark, flag in flags:
        title = records[ark]["identity"]["short_title"]
        lines.append(
            f"- `{ark}` {title}: ACTUAL_ERROR + SYSTEMATIC_PIPELINE_PROBLEM; primary issue `unnatural language`, secondary issues `title/proper-noun/terminology review` and `omitted meaning`."
        )
    return "\n".join(lines) + "\n"


def enriched_value_rows(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for ark, research in VALUE_RESEARCH.items():
        rec = records[ark]
        row = {
            "artwork_id": ark,
            "title": rec["identity"]["title"],
            "short_title": rec["identity"]["short_title"],
            "catalog_version": CATALOG_VERSION,
            "research_version": RESEARCH_VERSION,
            "researched_at": GENERATED_AT,
            **research,
        }
        row["sources"] = [{**SOURCES[sid], "source_id": sid} for sid in research["sources"]]
        out.append(row)
    return out


def value_review(rows: list[dict[str, Any]]) -> str:
    class_counts = Counter(r["value_ux_classification"] for r in rows)
    numeric_context = sum(
        1
        for r in rows
        if r["artist_market_record"] is not None
        or r["category_comparable_low"] is not None
        or r["historical_financial_reference"]
    )
    direct = sum(1 for r in rows if r["direct_numeric_estimate_possible"])
    lines = [
        "# Louvre Phase 2A Value Research Review",
        "",
        f"Catalog version: `{CATALOG_VERSION}`",
        f"Research version: `{RESEARCH_VERSION}`",
        f"Researched at: `{GENERATED_AT}`",
        "",
        "## Core Finding",
        "",
        "The original `0 / 20` numeric estimate result was too conservative for product energy, but correct in one important sense: none of the 20 should currently receive a numerical estimate presented as the value of the specific Louvre object.",
        "",
        "The better product direction is to distinguish `estimated value of this work` from `financial context around this work`.",
        "",
        "## Classification Totals",
        "",
        f"- VALUE_RANGE: {class_counts.get('VALUE_RANGE', 0)}",
        f"- VALUE_CONTEXT: {class_counts.get('VALUE_CONTEXT', 0)}",
        f"- NON_MARKET_ICON: {class_counts.get('NON_MARKET_ICON', 0)}",
        f"- Works that can responsibly show at least one monetary number as context: {numeric_context}",
        f"- Works that can responsibly show an estimated range for the artwork itself: {direct}",
        "",
        "## Mona Lisa Test Case",
        "",
    ]
    for key, data in MONA_PRESENTATIONS.items():
        lines.extend([f"### {key}", "", f"- Label: {data['label']}", f"- Presentation: {data['text']}", f"- Product trade-off: {data['tradeoff']}", ""])
    lines.extend(["## Per-Work Research", ""])
    for r in rows:
        lines.extend(
            [
                f"### {r['short_title']} (`{r['artwork_id']}`)",
                "",
                f"- Direct numeric estimate possible: {'yes' if r['direct_numeric_estimate_possible'] else 'no'}",
                f"- Proposed value range for this work: {r['proposed_value_low']} - {r['proposed_value_high']} {r['currency']}",
                f"- Value UX classification: {r['value_ux_classification']}",
                f"- Valuation type: {r['valuation_type']}",
                f"- Confidence: {r['confidence']}",
                f"- Visitor-safe numeric statement: {r['visitor_safe_numeric_statement']}",
                f"- Methodology: {r['methodology']}",
                "- Sources:",
            ]
        )
        lines.extend([f"  - {s['name']}: {s['url']}" for s in r["sources"]])
        lines.append("")
    lines.extend(
        [
            "## Product Implications",
            "",
            "- Phase 2A content is not production-ready in FR/ZH because localization is templated and not content-preserving.",
            "- The English visual/context writing is usable as a draft, but the current `what_to_notice` list has 3-4 observations per work, not a deeper 20-plus observation layer.",
            "- The current value reveal should not ship as just `Estimate pending review` for the Louvre pilot. It needs a `VALUE_CONTEXT` UI state that can display accurately labeled artist/category/institutional financial context.",
            "- No Louvre value number should be shown as `estimated value of this work` until specialist review approves a specific range.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    records = load_records()
    (CONTENT_ROOT / "louvre_phase2a_product_review.md").write_text(product_review(records), encoding="utf-8")
    (CONTENT_ROOT / "louvre_phase2a_translation_flag_analysis.md").write_text(translation_analysis(records), encoding="utf-8")
    rows = enriched_value_rows(records)
    write_jsonl(CONTENT_ROOT / "louvre_phase2a_value_research.jsonl", rows)
    (CONTENT_ROOT / "louvre_phase2a_value_research_review.md").write_text(value_review(rows), encoding="utf-8")
    counts = Counter(r["value_ux_classification"] for r in rows)
    print(
        json.dumps(
            {
                "rows": len(rows),
                "classifications": dict(sorted(counts.items())),
                "context_numbers": sum(
                    1
                    for r in rows
                    if r["artist_market_record"] is not None
                    or r["category_comparable_low"] is not None
                    or r["historical_financial_reference"]
                ),
                "direct_numeric_estimates": sum(1 for r in rows if r["direct_numeric_estimate_possible"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
