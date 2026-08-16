#!/usr/bin/env python3
"""Generate Louvre Phase 2B content candidates for the 480 non-Golden works.

Export-only. This script reads the frozen Louvre Visitor 500 catalog, excludes
the Golden 20, enriches the remaining 480 from local normalized Louvre metadata
and the final Commons manifest, then writes review artifacts under
exports/louvre/content/phase2b.

It does not fetch network resources, write production rows, create recognition
assets, create embeddings, download images, or generate audio bytes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LOUVRE = ROOT / "exports" / "louvre"
CONTENT = LOUVRE / "content"
OUT = CONTENT / "phase2b"
NORMALIZED = ROOT / "backend" / "data" / "louvre" / "normalized"

CATALOG_VERSION = "2026-08-11-v1"
PIPELINE_VERSION = "louvre_phase2b_v0.1"
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

FINAL_500 = LOUVRE / "louvre_visitor_500_final.jsonl"
COMMONS_FINAL = LOUVRE / "louvre_wikimedia_asset_manifest_final.jsonl"
GOLDEN_20 = CONTENT / "louvre_golden20_final.jsonl"
FREEZE_MANIFEST = LOUVRE / "louvre_visitor_500_freeze_manifest.json"

BANNED = [
    "more than just",
    "testament to",
    "stands as",
    "captivates",
    "invites viewers",
    "timeless",
    "rich tapestry",
    "delve into",
    "masterful use of",
    "iconic masterpiece",
]

SOURCE_LIBRARY = {
    "legifrance_l451_5": {
        "source_id": "legifrance_l451_5",
        "source_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000042654163",
        "source_type": "official_legal_reference",
        "retrieved_at": "2026-08-11T18:44:47+00:00",
        "supported_fields": ["value_reveal", "institutional_legal_context"],
        "notes": "French public Musees de France collections are public-domain property and inalienable.",
    }
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def short_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, list):
        value = "; ".join(str(v) for v in value if v)
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text or fallback


def strip_louvre_prefix(value: str) -> str:
    value = short_text(value)
    value = re.sub(r"^Date de création/fabrication\s*:\s*", "", value, flags=re.I)
    value = re.sub(r"^Matériau\s*:\s*", "", value, flags=re.I)
    value = re.sub(r"^Technique\s*:\s*", "", value, flags=re.I)
    return value


def department_family(department: str, object_type: str, title: str) -> str:
    d = department.lower()
    ot = object_type.lower()
    t = title.lower()
    if "peintures" in d:
        return "painting"
    if "sculptures" in d:
        return "sculpture"
    if "egypt" in d:
        return "egyptian"
    if "orientales" in d:
        return "near_eastern"
    if "islam" in d:
        return "islamic"
    if "objets d'art" in d:
        return "decorative"
    if "grecques" in d or "étrusques" in d or "romaines" in d:
        return "greek_roman"
    if "byzance" in d or "chrétientés" in d:
        return "byzantine"
    if "histoire du louvre" in d:
        return "history"
    if any(word in ot or word in t for word in ["tableau", "portrait", "vierge", "paysage"]):
        return "painting"
    return "object"


def display_title(row: dict[str, Any], norm: dict[str, Any]) -> str:
    return short_text(row.get("title") or norm.get("title"), "Untitled Louvre work")


def creator_text(row: dict[str, Any], norm: dict[str, Any]) -> str | None:
    artist = short_text(row.get("artist") or norm.get("artist_name"))
    return artist or None


def title_seed(title: str) -> str:
    if len(title) <= 80:
        return title
    for sep in [" dit ", " ou ", " : ", ";"]:
        if sep in title:
            return title.split(sep)[0].strip()
    return title[:77].rstrip() + "..."


def period_label(norm: dict[str, Any]) -> str:
    date = strip_louvre_prefix(norm.get("date_display") or norm.get("display_date_created") or "")
    return date or "its documented period"


def material_label(norm: dict[str, Any]) -> str:
    material = short_text(norm.get("materials_and_techniques"))
    if not material:
        return "its material surface"
    material = material.replace("Matériau :", "").replace("Technique :", "").strip()
    return material[:130].rstrip()


def object_label(norm: dict[str, Any], row: dict[str, Any]) -> str:
    return short_text(norm.get("object_type") or row.get("title"), "museum object")


def source_support(norm: dict[str, Any], row: dict[str, Any]) -> str:
    score = 0
    for field in ["date_display", "materials_and_techniques", "dimensions_raw", "inventory_number", "room"]:
        if short_text(norm.get(field) or row.get(field)):
            score += 1
    if short_text(norm.get("description")):
        score += 1
    if score >= 5:
        return "STRONG"
    if score >= 3:
        return "ADEQUATE"
    return "LIMITED"


def english_content(row: dict[str, Any], norm: dict[str, Any]) -> dict[str, Any]:
    title = display_title(row, norm)
    short = title_seed(title)
    creator = creator_text(row, norm)
    family = department_family(row.get("department", ""), object_label(norm, row), title)
    material = material_label(norm)
    date = period_label(norm)
    room = short_text(row.get("room") or norm.get("room"), "the Louvre room listed for this work")
    obj = object_label(norm, row)
    dimensions = short_text(norm.get("dimensions_raw") or norm.get("dimensions_display"))
    description = short_text(norm.get("description"))
    place = short_text(norm.get("place_of_discovery"))
    provenance = short_text(norm.get("provenance") or norm.get("object_history"))
    tier = row.get("visitor_tier", "C")

    family_hooks = {
        "painting": f"{short} asks you to read a painted surface one decision at a time.",
        "sculpture": f"{short} changes as soon as you move around it.",
        "egyptian": f"{short} carries ancient Egyptian belief into a room full of living visitors.",
        "near_eastern": f"{short} brings power, writing, and image into the same object.",
        "islamic": f"{short} rewards close looking at pattern, script, and surface.",
        "decorative": f"{short} shows how luxury can be built from material, skill, and use.",
        "greek_roman": f"{short} turns an ancient body or object into a lesson in presence.",
        "byzantine": f"{short} belongs to a world where image, ritual, and material met.",
        "history": f"{short} makes the Louvre itself part of what you are looking at.",
        "object": f"{short} is worth slowing down for its surface, scale, and purpose.",
    }

    why = [
        f"The work matters because it is not only an item in {row.get('department')}; it is a visible example of how that collection teaches through objects.",
        f"Its Louvre record anchors it to {date}, so the object can be read against a specific historical world rather than as a generic display piece.",
    ]
    if creator:
        why.insert(1, f"The named creator or attribution, {creator}, gives the visitor a concrete authorship trail without making the label do all the work.")
    elif family in {"egyptian", "near_eastern", "greek_roman", "islamic", "decorative"}:
        why.insert(1, "The absence of a single modern artist name is part of the lesson: workshop, ritual, court, or archaeological context matters as much as individual authorship.")
    if tier == "B":
        why.append(f"Its room evidence places it at {room}, making it a practical visitor-facing stop rather than an abstract catalog record.")

    notice = [
        f"Start with the title: ask which part of the object actually explains the words \"{short}\".",
        f"Look for the material evidence: {material}.",
        "Check the edges, base, frame, or missing parts; they often explain how the object survived and how it was handled.",
    ]
    if dimensions:
        notice.append(f"Use the scale listed by the Louvre, {dimensions}, to judge whether the work was made for intimacy, ceremony, or public display.")
    if family == "painting":
        notice.append("Find the strongest light-dark contrast, then see how it directs the first few seconds of looking.")
    elif family == "sculpture":
        notice.append("Move a little if the room allows; the outline and shadows will change before the label does.")
    elif family in {"egyptian", "near_eastern", "islamic"}:
        notice.append("Look for marks of writing, repeated pattern, or symbolic order before you read the full label.")
    elif family == "decorative":
        notice.append("Separate decoration from construction: one tells you how it dazzles, the other how it was made.")

    if tier == "C":
        notice = notice[:3]

    context = f"Layer 1 Louvre metadata places this work in {date}. In front of it, that date is most useful as a way to imagine the skills, beliefs, and patrons that made this object necessary."
    if place:
        context += f" The recorded place evidence also points to {place}."

    story_source = description or provenance or place
    if story_source:
        story = f"The memorable detail here is already in the source record: {story_source[:260].rstrip()}."
    else:
        story = "The most useful story is a looking story: the object asks you to connect title, material, scale, and room placement before turning it into a single explanation."

    rarity = f"Its significance for ELYIO is visitor usefulness: an on-display Louvre work with documented room evidence, {row.get('metadata_status')} metadata, and a clear place inside the frozen Visitor 500."
    if row.get("commons_asset_status") == "APPROVED":
        rarity += " It also has a high-confidence Commons candidate for future recognition review."

    simple = (
        f"You are looking at {short}. "
        f"The Louvre lists it in {row.get('department')} and places it in {room}. "
        f"First look at the material and scale, then ask what the title helps you notice."
    )
    kids = (
        f"Mission: find one detail on {short} that you can point to without reading the label. "
        "Then ask what it is made from. That clue can tell you whether the object was made to be used, shown, remembered, or believed in."
    )
    audio = (
        f"Pause in front of {short}. Do not start with the whole story. Start with one visible clue: the surface, the scale, or the shape. "
        f"The Louvre record connects this work to {date}, but the date only matters if it changes what you see. "
        f"Now look for how {material} behaves in the room light. "
        "Before you move on, choose one detail that would disappear in a quick photograph. That detail is the reason to stand here."
    )

    return {
        "title": title,
        "creator": creator,
        "hook": family_hooks.get(family, family_hooks["object"]),
        "why_it_matters": why[:4],
        "what_to_notice": notice[:4 if tier == "B" else 3],
        "time_context": context,
        "story": story,
        "rarity_significance": rarity,
        "simple_mode": simple,
        "kids_mode": kids,
        "audio_script": audio,
    }


def localized_content(row: dict[str, Any], norm: dict[str, Any], en: dict[str, Any]) -> dict[str, Any]:
    title = display_title(row, norm)
    short = title_seed(title)
    department = row.get("department", "département du Louvre")
    room = short_text(row.get("room") or norm.get("room"), "la salle indiquée par le Louvre")
    material = material_label(norm)
    date = period_label(norm)

    fr = {
        "title": title,
        "creator": creator_text(row, norm),
        "hook": f"{short} demande de commencer par un détail visible, puis de revenir à l'ensemble.",
        "why_it_matters": [
            f"L'oeuvre compte parce qu'elle donne une entrée concrète dans {department}.",
            f"La notice du Louvre la rattache à {date}, ce qui aide à regarder l'objet dans son monde historique.",
            "Elle garde aussi la différence entre fait de source et interprétation de visite.",
        ],
        "what_to_notice": [
            f"Commencez par vérifier quel détail explique le titre: {short}.",
            f"Regardez la matière ou la technique indiquée par la source: {material}.",
            "Cherchez les bords, le socle, le cadre ou les parties manquantes.",
            "Mesurez l'effet de l'échelle avec votre propre distance devant l'objet.",
        ][:4 if row.get("visitor_tier") == "B" else 3],
        "time_context": f"La source Louvre place cette oeuvre dans {date}; cette information sert ici à mieux lire les gestes, usages et croyances visibles.",
        "story": "Le récit reste volontairement attaché aux indices de la notice: titre, matière, lieu, usage et état de conservation.",
        "rarity_significance": "Son intérêt vient de sa présence vérifiée en salle et de son rôle dans le parcours visiteur du Louvre.",
        "simple_mode": f"Vous regardez {short}. Le Louvre la situe dans {room}. Regardez d'abord la matière, puis le détail qui explique le titre.",
        "kids_mode": f"À trouver: un détail de {short} que vous pouvez montrer du doigt. Demandez ensuite de quoi l'objet est fait.",
        "audio_script": f"Restez devant {short}. Choisissez d'abord un détail visible: la surface, l'échelle ou la forme. La notice du Louvre la relie à {date}, mais cette date doit vous aider à regarder. Observez maintenant la matière: {material}. Avant de partir, gardez un détail que la photographie ne remplacerait pas.",
    }

    zh = {
        "title": title,
        "creator": creator_text(row, norm),
        "hook": f"先从{short}的一个可见细节开始，再回到整体。",
        "why_it_matters": [
            f"这件作品重要，因为它让观众具体进入{department}。",
            f"卢浮宫资料把它和{date}联系起来，这能帮助你把作品放回它的历史世界。",
            "这里区分来源事实和 ELYIO 的参观解读。",
        ],
        "what_to_notice": [
            f"先找一个能解释题名的细节：{short}。",
            f"再看来源记录中的材料或技法：{material}。",
            "注意边缘、底座、框架，或缺失的部分。",
            "用你和作品之间的距离感受它的尺度。",
        ][:4 if row.get("visitor_tier") == "B" else 3],
        "time_context": f"卢浮宫资料把这件作品放在{date}；这个年代信息应当帮助你看见手法、用途和信仰。",
        "story": "这里的故事只依靠来源记录中的线索：题名、材料、地点、用途和保存状态。",
        "rarity_significance": "它的意义来自已核实的展出状态，以及它在卢浮宫参观路线中的作用。",
        "simple_mode": f"你正在看{short}。卢浮宫把它列在{room}。先看材料，再找出能说明题名的细节。",
        "kids_mode": f"任务：在{short}上找一个能指给别人看的细节。然后问问自己：它是用什么做的？",
        "audio_script": f"在{short}前停一下。先选一个可见线索：表面、尺度，或形状。卢浮宫资料把它和{date}联系起来，但年代应该帮助你观看。现在看它的材料：{material}。离开前，记住一个照片无法替代的细节。",
    }
    return {"en": en, "fr": fr, "zh-Hans": zh}


def value_reveal() -> dict[str, Any]:
    return {
        "mode": "BEYOND_MARKET",
        "aggregate_value_eligible": False,
        "headline": "No responsible market estimate.",
        "label_en": "BEYOND THE MARKET",
        "label_fr": "AU-DELÀ DU MARCHÉ",
        "label_zh_hans": "超出市场价格",
        "explanation_en": "This Louvre work belongs to France's public museum collections and is not treated as an ordinary private-market asset.",
        "explanation_fr": "Cette oeuvre appartient aux collections publiques françaises et ne se traite pas comme un actif privé ordinaire.",
        "explanation_zh_hans": "这件卢浮宫藏品属于法国公共博物馆收藏，不能当作普通私人市场资产处理。",
        "institutional_legal_context": "French public Musees de France collections are inalienable public property.",
        "optional_numeric_context": None,
        "confidence": "MEDIUM",
        "sources": ["legifrance_l451_5"],
        "disclaimer": "Not an appraisal, insurance value, or sale estimate.",
    }


def source_bundle(row: dict[str, Any], norm: dict[str, Any], commons: dict[str, Any] | None) -> list[dict[str, Any]]:
    ark = row["ark_id"]
    sources = [
        {
            "source_id": f"src:{ark}:louvre_normalized_local",
            "source_url": row.get("source_url"),
            "source_type": "local_louvre_normalized_metadata",
            "retrieved_at": norm.get("last_source_sync"),
            "supported_fields": [
                "title",
                "artist",
                "date",
                "medium",
                "dimensions",
                "inventory_number",
                "department",
                "room",
                "display_status",
                "source_url",
            ],
            "notes": "Local normalized Louvre metadata file; no network fetch in Phase 2B.",
        },
        {
            "source_id": f"src:{ark}:frozen_visitor_catalog",
            "source_url": row.get("source_url"),
            "source_type": "elyio_frozen_catalog",
            "retrieved_at": "2026-08-11",
            "supported_fields": ["visitor_tier", "visitor_priority_score", "selection_reason", "catalog_membership"],
            "notes": f"Frozen catalog version {CATALOG_VERSION}; membership not changed in Phase 2B.",
        },
    ]
    if commons:
        sources.append(
            {
                "source_id": f"src:{ark}:commons_manifest_final",
                "source_url": commons.get("wikimedia_page_url"),
                "source_type": "wikimedia_asset_discovery_manifest",
                "retrieved_at": "2026-08-11",
                "supported_fields": ["commons_asset_status", "rights_status", "match_confidence", "wikimedia_file"],
                "notes": "Metadata-only Commons discovery output; no image bytes fetched or stored.",
            }
        )
    sources.append(SOURCE_LIBRARY["legifrance_l451_5"])
    return sources


def qa_translation(lang: str, translated: dict[str, Any]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    text = json.dumps(translated, ensure_ascii=False)
    english_leak_terms = [
        "Look at",
        "Mission:",
        "This is",
        "market context",
        "not a valuation",
        "Start with",
    ]
    body = " ".join(
        short_text(item)
        for key, value in translated.items()
        if key not in {"title", "creator"}
        for item in (value if isinstance(value, list) else [value])
    )
    if any(term in body for term in english_leak_terms):
        flags.append({"severity": "BLOCKING", "type": "english_leakage", "detail": lang})
    if lang == "fr" and not re.search(r"[éèàùçÉÈÀÙÇ]", text):
        flags.append({"severity": "REVIEW", "type": "french_diacritic_signal_low", "detail": "French text has few diacritics"})
    if lang == "zh-Hans" and not re.search(r"[\u4e00-\u9fff]", text):
        flags.append({"severity": "BLOCKING", "type": "missing_chinese", "detail": "No Han characters detected"})
    return flags


def qa_editorial(record: dict[str, Any], support: str) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    text = json.dumps(record["content"]["en"], ensure_ascii=False).lower()
    for phrase in BANNED:
        if phrase in text:
            flags.append({"severity": "BLOCKING", "type": "banned_phrase", "detail": phrase})
    if len(record["content"]["en"]["what_to_notice"]) < (4 if record["visitor_tier"] == "B" else 3):
        flags.append({"severity": "BLOCKING", "type": "too_few_visual_observations", "detail": record["artwork_id"]})
    if support == "LIMITED":
        flags.append({"severity": "REVIEW", "type": "limited_source_support", "detail": "Local metadata has limited Layer 1 detail"})
    return flags


def qa_value(record: dict[str, Any]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    v = record["value_reveal"]
    if v["mode"] != "ESTIMATED_VALUE" and v.get("aggregate_value_eligible"):
        flags.append({"severity": "BLOCKING", "type": "aggregate_eligibility_error", "detail": record["artwork_id"]})
    if v["mode"] == "BEYOND_MARKET" and v.get("optional_numeric_context") is None:
        flags.append({"severity": "INFO", "type": "no_numeric_value_context", "detail": "Conservative non-market mode used"})
    return flags


def qa_kids_audio(record: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    kids_flags: list[dict[str, str]] = []
    audio_flags: list[dict[str, str]] = []
    kids = record["content"]["en"]["kids_mode"]
    audio = record["content"]["en"]["audio_script"]
    if len(kids.split()) < 18:
        kids_flags.append({"severity": "REVIEW", "type": "kids_too_short", "detail": record["artwork_id"]})
    words = len(audio.split())
    if words < 55 or words > 145:
        audio_flags.append({"severity": "REVIEW", "type": "audio_length_outside_target", "detail": f"{words} words"})
    return kids_flags, audio_flags


def build_exception_queue(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exceptions: list[dict[str, Any]] = []
    groups = {
        "editorial_qa_flags": "editorial",
        "value_qa_flags": "value",
        "kids_qa_flags": "kids",
        "audio_qa_flags": "audio",
    }
    for record in records:
        ark = record["artwork_id"]
        for field, label in groups.items():
            for flag in record.get(field, []):
                suggested = "Human review before production import."
                if flag["severity"] == "INFO":
                    suggested = "No regeneration required; keep as traceable QA note unless value research is reopened."
                exceptions.append(
                    {
                        "ark_id": ark,
                        "field": label,
                        "language": "en",
                        "severity": flag["severity"],
                        "reason": f"{flag['type']}: {flag.get('detail', '')}",
                        "suggested_action": suggested,
                    }
                )
        for item in record.get("translation_qa", []):
            for flag in item["qa_flags"]:
                if flag["severity"] in {"BLOCKING", "REVIEW"}:
                    exceptions.append(
                        {
                            "ark_id": ark,
                            "field": "localization",
                            "language": item["language"],
                            "severity": flag["severity"],
                            "reason": f"{flag['type']}: {flag.get('detail', '')}",
                            "suggested_action": "Regenerate or native-review localized field.",
                        }
                    )
    return exceptions


def review_sample(records: list[dict[str, Any]]) -> str:
    tier_b = [r for r in records if r["visitor_tier"] == "B"][:10]
    by_dept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        if r["visitor_tier"] == "C":
            by_dept[r["identity"]["department"]].append(r)
    tier_c: list[dict[str, Any]] = []
    while len(tier_c) < 10 and by_dept:
        for dept in list(by_dept):
            if by_dept[dept] and len(tier_c) < 10:
                tier_c.append(by_dept[dept].pop(0))
            if not by_dept[dept]:
                by_dept.pop(dept, None)
    sample = tier_b + tier_c
    lines = [
        "# Louvre Phase 2B Review Sample: 20 Non-Golden Works",
        "",
        "This sample shows actual generated visitor-facing candidate content. It is not production-approved content.",
    ]
    for r in sample:
        en = r["content"]["en"]
        fr = r["content"]["fr"]
        zh = r["content"]["zh-Hans"]
        v = r["value_reveal"]
        lines.extend(
            [
                "",
                f"## {en['title']}",
                "",
                f"- ARK: `{r['artwork_id']}`",
                f"- Tier: {r['visitor_tier']}",
                f"- Department: {r['identity']['department']}",
                f"- Room: {r['identity']['room']}",
                "",
                "### VALUE REVEAL",
                f"- {v['label_en']}: {v['headline']}",
                f"- {v['explanation_en']}",
                f"- Disclaimer: {v['disclaimer']}",
                "",
                "### EN",
                f"**Hook:** {en['hook']}",
                "",
                "**Why It Matters**",
            ]
        )
        lines.extend(f"- {x}" for x in en["why_it_matters"])
        lines.append("")
        lines.append("**What To Notice**")
        lines.extend(f"- {x}" for x in en["what_to_notice"])
        lines.extend(
            [
                "",
                f"**Time Context:** {en['time_context']}",
                "",
                f"**Story:** {en['story']}",
                "",
                f"**Rarity / Significance:** {en['rarity_significance']}",
                "",
                f"**Simple:** {en['simple_mode']}",
                "",
                f"**Kids:** {en['kids_mode']}",
                "",
                f"**Audio Script:** {en['audio_script']}",
                "",
                "### FR",
                f"**Accroche:** {fr['hook']}",
                "",
                f"**Simple:** {fr['simple_mode']}",
                "",
                f"**Audio:** {fr['audio_script']}",
                "",
                "### ZH-Hans",
                f"**钩子:** {zh['hook']}",
                "",
                f"**简明模式:** {zh['simple_mode']}",
                "",
                f"**音频脚本:** {zh['audio_script']}",
                "",
                "### INTERNAL QA",
                f"- Review status: {r['review_status']}",
                f"- Editorial flags: {len(r['editorial_qa_flags'])}",
                f"- FR QA: {r['translation_qa'][0]['qa_status']}",
                f"- ZH QA: {r['translation_qa'][1]['qa_status']}",
            ]
        )
    return "\n".join(lines) + "\n"


def write_markdown_reports(records: list[dict[str, Any]], exceptions: list[dict[str, Any]]) -> None:
    fr_block = sum(1 for r in records for q in r["translation_qa"] if q["language"] == "fr" for f in q["qa_flags"] if f["severity"] == "BLOCKING")
    zh_block = sum(1 for r in records for q in r["translation_qa"] if q["language"] == "zh-Hans" for f in q["qa_flags"] if f["severity"] == "BLOCKING")
    trans = [
        "# Louvre Phase 2B Localization QA",
        "",
        f"Pipeline version: `{PIPELINE_VERSION}`",
        f"Records checked: {len(records)}",
        "",
        f"- FR blocking flags: {fr_block}",
        f"- ZH-Hans blocking flags: {zh_block}",
        f"- FR review flags: {sum(1 for e in exceptions if e['field'] == 'localization' and e['language'] == 'fr' and e['severity'] == 'REVIEW')}",
        f"- ZH-Hans review flags: {sum(1 for e in exceptions if e['field'] == 'localization' and e['language'] == 'zh-Hans' and e['severity'] == 'REVIEW')}",
        "",
        "Deterministic checks covered English leakage, basic language signal, and field completeness. Human native review is still required before production approval.",
    ]
    (OUT / "louvre_phase2b_localization_qa.md").write_text("\n".join(trans) + "\n", encoding="utf-8")

    ed_counter = Counter()
    for r in records:
        for field in ["editorial_qa_flags", "value_qa_flags", "kids_qa_flags", "audio_qa_flags"]:
            for flag in r.get(field, []):
                ed_counter[(field, flag["severity"], flag["type"])] += 1
    ed = [
        "# Louvre Phase 2B Editorial QA",
        "",
        f"Pipeline version: `{PIPELINE_VERSION}`",
        f"Records checked: {len(records)}",
        "",
        "## Flag Counts",
    ]
    for (field, severity, typ), count in sorted(ed_counter.items()):
        ed.append(f"- {field} / {severity} / {typ}: {count}")
    ed.extend(
        [
            "",
            "## Policy",
            "",
            "- Tier B rows are marked NEEDS_HUMAN_REVIEW.",
            "- Tier C rows are AUTO_QA_PASSED only when no BLOCKING/REVIEW flags are present.",
            "- No row is marked APPROVED.",
            "- Value mode is conservative BEYOND_MARKET unless specific financial evidence exists; no context number is used as an artwork estimate.",
        ]
    )
    (OUT / "louvre_phase2b_editorial_qa.md").write_text("\n".join(ed) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    final = read_jsonl(FINAL_500)
    commons_rows = {r["ark_id"]: r for r in read_jsonl(COMMONS_FINAL)}
    golden_ids = {r["artwork_id"] for r in read_jsonl(GOLDEN_20)}
    freeze = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))

    if freeze.get("louvre_visitor_catalog_version") != CATALOG_VERSION:
        raise SystemExit("Frozen catalog version mismatch")
    if len(final) != 500 or len({r["ark_id"] for r in final}) != 500:
        raise SystemExit("Final 500 membership validation failed")

    remaining = [r for r in final if r["ark_id"] not in golden_ids]
    if len(remaining) != 480 or len({r["ark_id"] for r in remaining}) != 480:
        raise SystemExit("Expected exactly 480 non-Golden artworks")
    if any(r.get("display_status") != "ON_DISPLAY" for r in remaining):
        raise SystemExit("All Phase 2B records must be ON_DISPLAY")

    records: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    value_rows: list[dict[str, Any]] = []
    audio_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for row in remaining:
        ark = row["ark_id"]
        norm_path = NORMALIZED / f"{ark}.json"
        if not norm_path.exists():
            raise SystemExit(f"Missing local normalized metadata for {ark}")
        norm = json.loads(norm_path.read_text(encoding="utf-8"))
        commons = commons_rows.get(ark)
        en = english_content(row, norm)
        content = localized_content(row, norm, en)
        sources = source_bundle(row, norm, commons)
        source_ids = [s["source_id"] for s in sources]
        support = source_support(norm, row)
        review_status = "NEEDS_HUMAN_REVIEW" if row.get("visitor_tier") == "B" else "AUTO_QA_PASSED"

        record = {
            "artwork_id": ark,
            "catalog_version": CATALOG_VERSION,
            "phase2b_version": PIPELINE_VERSION,
            "generated_at": GENERATED_AT,
            "visitor_tier": row.get("visitor_tier"),
            "identity": {
                "ark_id": ark,
                "source_url": row.get("source_url"),
                "title": display_title(row, norm),
                "artist": creator_text(row, norm),
                "date": norm.get("date_display") or norm.get("display_date_created"),
                "medium": norm.get("materials_and_techniques"),
                "dimensions": norm.get("dimensions_raw") or norm.get("dimensions_display"),
                "department": row.get("department") or norm.get("department"),
                "room": row.get("room") or norm.get("room"),
                "current_location": row.get("current_location") or norm.get("current_location_raw"),
                "inventory_number": row.get("inventory_number") or norm.get("inventory_number"),
                "object_type": norm.get("object_type"),
                "display_status": row.get("display_status"),
                "metadata_status": row.get("metadata_status") or norm.get("metadata_status"),
                "source_support": support,
            },
            "value_reveal": value_reveal(),
            "content": content,
            "sources": source_ids,
            "source_bundle": sources,
            "review_status": review_status,
            "commons": {
                "commons_asset_status": row.get("commons_asset_status"),
                "rights_status": row.get("rights_status"),
                "match_confidence": row.get("commons_match_confidence"),
                "wikimedia_page_url": row.get("commons_file_page") or (commons or {}).get("wikimedia_page_url"),
            },
            "safety": {
                "production_writes": 0,
                "recognition_assets_created": 0,
                "embeddings_created": 0,
                "tts_audio_bytes_generated": 0,
                "louvre_image_bytes_fetched": 0,
                "catalog_membership_changed": False,
            },
        }

        translation_qa = []
        for lang in ("fr", "zh-Hans"):
            flags = qa_translation(lang, content[lang])
            translation_qa.append(
                {
                    "artwork_id": ark,
                    "language": lang,
                    "translation_version": PIPELINE_VERSION,
                    "qa_status": "BLOCKING_FLAGS" if any(f["severity"] == "BLOCKING" for f in flags) else "PASSED",
                    "qa_flags": flags,
                    "fields_checked": [
                        "title",
                        "hook",
                        "why_it_matters",
                        "what_to_notice",
                        "time_context",
                        "story",
                        "rarity_significance",
                        "simple_mode",
                        "kids_mode",
                        "audio_script",
                    ],
                }
            )
        record["translation_qa"] = translation_qa
        record["editorial_qa_flags"] = qa_editorial(record, support)
        record["value_qa_flags"] = qa_value(record)
        record["kids_qa_flags"], record["audio_qa_flags"] = qa_kids_audio(record)

        has_review_or_blocking = any(
            f["severity"] in {"BLOCKING", "REVIEW"}
            for field in ["editorial_qa_flags", "kids_qa_flags", "audio_qa_flags"]
            for f in record[field]
        ) or any(
            f["severity"] in {"BLOCKING", "REVIEW"}
            for item in translation_qa
            for f in item["qa_flags"]
        )
        if row.get("visitor_tier") == "C" and has_review_or_blocking:
            record["review_status"] = "NEEDS_HUMAN_REVIEW"

        records.append(record)
        for s in sources:
            source_rows.append({"artwork_id": ark, **s})
        value_rows.append({"artwork_id": ark, "catalog_version": CATALOG_VERSION, **record["value_reveal"]})
        audio_rows.append(
            {
                "artwork_id": ark,
                "catalog_version": CATALOG_VERSION,
                "en": content["en"]["audio_script"],
                "fr": content["fr"]["audio_script"],
                "zh-Hans": content["zh-Hans"]["audio_script"],
                "tts_audio_bytes_generated": 0,
                "review_status": record["review_status"],
            }
        )
        summary_rows.append(
            {
                "ark_id": ark,
                "title": record["identity"]["title"],
                "visitor_tier": row.get("visitor_tier"),
                "department": record["identity"]["department"],
                "metadata_status": record["identity"]["metadata_status"],
                "source_support": support,
                "value_mode": record["value_reveal"]["mode"],
                "aggregate_value_eligible": record["value_reveal"]["aggregate_value_eligible"],
                "commons_asset_status": row.get("commons_asset_status"),
                "review_status": record["review_status"],
                "editorial_flags": len(record["editorial_qa_flags"]),
                "translation_flags": sum(len(q["qa_flags"]) for q in translation_qa),
                "value_flags": len(record["value_qa_flags"]),
                "kids_flags": len(record["kids_qa_flags"]),
                "audio_flags": len(record["audio_qa_flags"]),
            }
        )

    exceptions = build_exception_queue(records)

    write_jsonl(OUT / "louvre_phase2b_480.jsonl", records)
    write_jsonl(OUT / "louvre_phase2b_sources.jsonl", source_rows)
    write_jsonl(OUT / "louvre_phase2b_value_model.jsonl", value_rows)
    write_jsonl(OUT / "louvre_phase2b_audio_scripts.jsonl", audio_rows)
    write_jsonl(OUT / "louvre_phase2b_exception_queue.jsonl", exceptions)

    with (OUT / "louvre_phase2b_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    write_markdown_reports(records, exceptions)
    (OUT / "louvre_phase2b_review_sample_20.md").write_text(review_sample(records), encoding="utf-8")

    mode_counts = Counter(r["value_reveal"]["mode"] for r in records)
    tier_counts = Counter(r["visitor_tier"] for r in records)
    status_counts = Counter(r["review_status"] for r in records)
    exc_counts = Counter(e["severity"] for e in exceptions)
    dept_counts = Counter(r["identity"]["department"] for r in records)
    manifest = {
        "catalog_version": CATALOG_VERSION,
        "phase2b_version": PIPELINE_VERSION,
        "generated_at": GENERATED_AT,
        "inputs": {
            "final_500": str(FINAL_500.relative_to(ROOT)),
            "golden_20": str(GOLDEN_20.relative_to(ROOT)),
            "commons_manifest": str(COMMONS_FINAL.relative_to(ROOT)),
            "local_normalized_dir": str(NORMALIZED.relative_to(ROOT)),
        },
        "validation": {
            "final_catalog_rows": len(final),
            "final_catalog_unique_arks": len({r["ark_id"] for r in final}),
            "golden_excluded": len(golden_ids),
            "processed": len(records),
            "processed_unique_arks": len({r["artwork_id"] for r in records}),
            "all_on_display": all(r["identity"]["display_status"] == "ON_DISPLAY" for r in records),
            "catalog_membership_changes": 0,
            "overlap_with_golden": len({r["artwork_id"] for r in records} & golden_ids),
        },
        "counts": {
            "tiers": dict(tier_counts),
            "departments": dict(dept_counts),
            "value_modes": dict(mode_counts),
            "aggregate_value_eligible": sum(1 for r in records if r["value_reveal"].get("aggregate_value_eligible")),
            "review_status": dict(status_counts),
            "exceptions": dict(exc_counts),
            "fr_blocking_flags": sum(1 for r in records for q in r["translation_qa"] if q["language"] == "fr" for f in q["qa_flags"] if f["severity"] == "BLOCKING"),
            "zh_hans_blocking_flags": sum(1 for r in records for q in r["translation_qa"] if q["language"] == "zh-Hans" for f in q["qa_flags"] if f["severity"] == "BLOCKING"),
            "editorial_blocking_flags": sum(1 for r in records for f in r["editorial_qa_flags"] if f["severity"] == "BLOCKING"),
            "kids_blocking_flags": sum(1 for r in records for f in r["kids_qa_flags"] if f["severity"] == "BLOCKING"),
            "audio_blocking_flags": sum(1 for r in records for f in r["audio_qa_flags"] if f["severity"] == "BLOCKING"),
        },
        "safety": {
            "production_writes": 0,
            "recognition_assets_created": 0,
            "embeddings_created": 0,
            "tts_audio_bytes_generated": 0,
            "louvre_image_bytes_fetched": 0,
            "network_requests": 0,
        },
        "outputs": {},
    }

    manifest_path = OUT / "louvre_phase2b_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for path in sorted(OUT.iterdir()):
        if path.is_file():
            if path == manifest_path:
                continue
            manifest["outputs"][path.name] = {
                "size_bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["validation"] | manifest["counts"] | manifest["safety"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
