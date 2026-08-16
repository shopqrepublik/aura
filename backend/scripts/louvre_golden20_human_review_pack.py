#!/usr/bin/env python3
"""Build the Golden 20 human-review pack for the requested 10 works.

This is a pure formatter over louvre_golden20_final.jsonl. It does not
regenerate, rewrite, research, import, or mutate the Golden 20 source fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "exports" / "louvre" / "content"
SOURCE = CONTENT / "louvre_golden20_final.jsonl"

REQUESTED = [
    "cl010062370",  # Mona Lisa
    "cl010277627",  # Venus de Milo
    "cl010252531",  # Winged Victory of Samothrace
    "cl010065872",  # Liberty Leading the People
    "cl010059199",  # The Raft of the Medusa
    "cl010064382",  # The Wedding Feast at Cana
    "cl010091976",  # Psyche Revived by Cupid's Kiss
    "cl010065720",  # The Coronation of Napoleon
    "cl010065566",  # Grande Odalisque
    "cl010062239",  # Oath of the Horatii
]


def read_records() -> dict[str, dict[str, Any]]:
    with SOURCE.open(encoding="utf-8") as f:
        return {row["artwork_id"]: row for row in map(json.loads, f)}


def headline(v: dict[str, Any]) -> str:
    if v["mode"] == "BEYOND_MARKET":
        return v["headline"]
    number = v.get("headline_number")
    if isinstance(number, dict):
        return f"{number.get('low')}-{number.get('high')} {v.get('currency')}"
    return f"{number} {v.get('currency')}".strip()


def label(v: dict[str, Any], lang: str = "en") -> str:
    if v["mode"] == "BEYOND_MARKET":
        if lang == "fr":
            return v["label_fr"]
        if lang == "zh-Hans":
            return v["label_zh_hans"]
        return v["label_en"]
    if lang == "fr":
        return f"CONTEXTE DE MARCHÉ - {v['context_label_fr']}"
    if lang == "zh-Hans":
        return f"市场背景 - {v['context_label_zh_hans']}"
    return f"MARKET CONTEXT - {v['context_label_en']}"


def supporting(v: dict[str, Any], lang: str = "en") -> str:
    if v["mode"] == "BEYOND_MARKET":
        text = v[f"explanation_{'zh_hans' if lang == 'zh-Hans' else lang}"]
        optional = v.get("optional_numeric_context")
        if optional and lang == "en":
            return f"{text} For scale: {optional['explanation']}"
        return text
    key = "context_explanation_zh_hans" if lang == "zh-Hans" else f"context_explanation_{lang}"
    return v[key]


def qa_status(record: dict[str, Any], lang: str) -> str:
    items = [q for q in record["translation_qa"] if q["language"] == lang]
    return items[0]["qa_status"] if items else "MISSING"


def render_localized_card(record: dict[str, Any], lang: str) -> list[str]:
    c = record["content"][lang]
    v = record["value_reveal"]
    return [
        f"TITLE: {c['title']}",
        f"VALUE REVEAL: {label(v, lang)} | {headline(v)} | {supporting(v, lang)} | {v['disclaimer']}",
        "",
        f"HOOK: {c['hook']}",
        "",
        f"WHY IT MATTERS: {c['why_it_matters']}",
        "",
        "WHAT TO NOTICE:",
        *[f"- {item}" for item in c["what_to_notice"]],
        "",
        f"TIME CONTEXT: {c['time_context']}",
        "",
        f"STORY: {c['story']}",
        "",
        f"RARITY / SIGNIFICANCE: {c['rarity_significance']}",
        "",
        f"SIMPLE MODE: {c['simple']}",
        "",
        f"KIDS MODE: {c['kids']}",
        "",
        f"AUDIO SCRIPT: {c['audio']}",
    ]


def build_review(records: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# Louvre Golden 20 Human Review Pack",
        "",
        "Source: `exports/louvre/content/louvre_golden20_final.jsonl`",
        "Scope: the 10 requested works only. Visitor copy is shown without interleaved citations.",
        "",
    ]
    for ark in REQUESTED:
        r = records[ark]
        ident = r["identity"]
        en = r["content"]["en"]
        v = r["value_reveal"]
        lines.extend(
            [
                f"## {en['title']} (`{ark}`)",
                "",
                f"TITLE: {en['title']}",
                f"ARTIST / CREATOR: {en['creator'] if en['creator'] else 'NULL'}",
                f"DATE: {ident['date']}",
                f"ROOM: {ident['room']}",
                "",
                "### VALUE REVEAL",
                "",
                f"- exact UI label: {label(v, 'en')}",
                f"- headline number/text: {headline(v)}",
                f"- supporting sentence: {supporting(v, 'en')}",
                f"- disclaimer: {v['disclaimer']}",
                "",
                "### HOOK",
                "",
                en["hook"],
                "",
                "### WHY IT MATTERS",
                "",
            ]
        )
        lines.extend([f"- {item}" for item in en["why_it_matters"]])
        lines.extend(["", "### WHAT TO NOTICE", ""])
        lines.extend([f"- {item}" for item in en["what_to_notice"]])
        lines.extend(
            [
                "",
                "### TIME CONTEXT",
                "",
                en["time_context"],
                "",
                "### STORY",
                "",
                en["story"],
                "",
                "### RARITY / SIGNIFICANCE",
                "",
                en["rarity_significance"],
                "",
                "### SIMPLE MODE",
                "",
                en["simple_mode"],
                "",
                "### KIDS MODE",
                "",
                en["kids_mode"],
                "",
                "### EN AUDIO SCRIPT",
                "",
                en["audio_script"],
                "",
                "### FR FINALIZED VISITOR CARD",
                "",
            ]
        )
        lines.extend(render_localized_card(r, "fr"))
        lines.extend(["", "### ZH-Hans FINALIZED VISITOR CARD", ""])
        lines.extend(render_localized_card(r, "zh-Hans"))
        lines.extend(
            [
                "",
                "### INTERNAL REVIEW",
                "",
                f"- value_mode: {v['mode']}",
                f"- valuation confidence: {v['confidence']}",
                f"- source count: {len(set(r['sources']))}",
                f"- editorial QA: {'PASSED' if not r['editorial_qa_flags'] else r['editorial_qa_flags']}",
                f"- FR QA: {qa_status(r, 'fr')}",
                f"- ZH QA: {qa_status(r, 'zh-Hans')}",
                f"- review_status: {r['review_status']}",
                "",
            ]
        )
    return "\n".join(lines)


def ui_payload(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "source_file": "exports/louvre/content/louvre_golden20_final.jsonl",
        "catalog_version": records[REQUESTED[0]]["catalog_version"],
        "golden_version": records[REQUESTED[0]]["golden_version"],
        "artworks": [],
    }
    for ark in REQUESTED:
        r = records[ark]
        v = r["value_reveal"]
        payload["artworks"].append(
            {
                "id": ark,
                "museum_id": "louvre",
                "title": {
                    "en": r["content"]["en"]["title"],
                    "fr": r["content"]["fr"]["title"],
                    "zh-Hans": r["content"]["zh-Hans"]["title"],
                },
                "artist": r["content"]["en"]["creator"],
                "date": r["identity"]["date"],
                "room": r["identity"]["room"],
                "inventory_number": r["identity"]["inventory_number"],
                "value_reveal": {
                    "mode": v["mode"],
                    "label": {
                        "en": label(v, "en"),
                        "fr": label(v, "fr"),
                        "zh-Hans": label(v, "zh-Hans"),
                    },
                    "headline": headline(v),
                    "supporting_sentence": {
                        "en": supporting(v, "en"),
                        "fr": supporting(v, "fr"),
                        "zh-Hans": supporting(v, "zh-Hans"),
                    },
                    "disclaimer": v["disclaimer"],
                    "aggregate_value_eligible": v["mode"] == "ESTIMATED_VALUE",
                    "raw_value_reveal": v,
                },
                "content": r["content"],
                "internal_review": {
                    "source_count": len(set(r["sources"])),
                    "editorial_qa": "PASSED" if not r["editorial_qa_flags"] else r["editorial_qa_flags"],
                    "fr_qa": qa_status(r, "fr"),
                    "zh_qa": qa_status(r, "zh-Hans"),
                    "review_status": r["review_status"],
                },
            }
        )
    return payload


def main() -> None:
    records = read_records()
    missing = [ark for ark in REQUESTED if ark not in records]
    if missing:
        raise SystemExit(f"Missing Golden 20 records: {missing}")
    (CONTENT / "louvre_golden20_human_review.md").write_text(build_review(records), encoding="utf-8")
    (CONTENT / "louvre_golden20_ui_payload_sample.json").write_text(
        json.dumps(ui_payload(records), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"review_records": len(REQUESTED), "production_writes": 0}, indent=2))


if __name__ == "__main__":
    main()
