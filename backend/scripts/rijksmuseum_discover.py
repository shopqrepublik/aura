"""Discover a deterministic, image-backed Rijksmuseum painting snapshot.

Uses only the official Search and Linked Data resolver services.  The output
is the normalized snapshot consumed by the generic JsonFileAdapter/ingestion
pipeline; no Rijksmuseum-specific persistence is introduced.
"""
from __future__ import annotations
import argparse, json, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEARCH = "https://data.rijksmuseum.nl/search/collection"
RESOLVER = "https://id.rijksmuseum.nl/"

def get_json(url: str) -> dict:
    req = Request(url, headers={"Accept": "application/ld+json", "User-Agent": "ELYIO-MuseumFactory/1.0"})
    with urlopen(req, timeout=30) as response:
        return json.load(response)

def content(items, language=None):
    for item in items or []:
        if isinstance(item, dict) and item.get("content") and (language is None or any(str(x.get("id", "")).endswith(language) for x in item.get("language", []))):
            return str(item["content"])
    return None

def resolve(pid: str) -> dict:
    obj = get_json(RESOLVER + pid.rsplit("/", 1)[-1] + "?_profile=la-framed")
    title = content(obj.get("identified_by")) or pid.rsplit("/", 1)[-1]
    accession = next((str(x.get("content")) for x in obj.get("identified_by", []) if x.get("type") == "Identifier" and x.get("content")), None)
    artist = None
    production = obj.get("produced_by") or {}
    for ref in production.get("referred_to_by", []):
        if ref.get("content"):
            artist = str(ref["content"]); break
    date = None
    for name in (production.get("timespan") or {}).get("identified_by", []):
        if name.get("content"):
            date = str(name["content"]); break
    image_url = None
    visual = obj.get("shows") or {}
    if isinstance(visual, list): visual = visual[0] if visual else {}
    visual_id = visual.get("id") if isinstance(visual, dict) else None
    if visual_id:
        v = get_json(visual_id.replace("id.rijksmuseum.nl", "id.rijksmuseum.nl") + "?_profile=la-framed")
        digital = (v.get("digitally_shown_by") or [{}])[0].get("id")
        if digital:
            d = get_json(digital + "?_profile=la-framed")
            image_url = (d.get("access_point") or [{}])[0].get("id")
    if not image_url:
        return {}
    return {"provider_record_id": pid.rsplit("/", 1)[-1], "source_url": pid,
            "source_language": "en", "title_original": title, "title_locale": "en",
            "creator_display": artist, "date_display": date, "object_type": "painting",
            "institution_record_id": accession, "media": [{"provider_asset_id": visual_id,
            "original_url": image_url, "purpose": "REFERENCE", "media_type": "IMAGE",
            "rights_status": "PUBLIC_DOMAIN", "verification_state": "DECLARED_BY_SOURCE",
            "presentation_eligible": True, "recognition_eligible": True,
            "association_role": "REFERENCE", "primary": True}]}

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--output", required=True); ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args(); ids=[]; next_url=SEARCH+"?"+urlencode({"type":"painting"})
    while next_url and len(ids) < args.limit:
        page=get_json(next_url); ids.extend(str(x["id"]) for x in page.get("orderedItems", []) if x.get("id")); next_url=(page.get("next") or {}).get("id")
    rows=[]; skipped=0
    for i,pid in enumerate(ids[:args.limit],1):
        try:
            row=resolve(pid)
            if row: rows.append(row)
            else: skipped += 1
        except Exception:
            skipped += 1
        if i % 25 == 0: print(f"resolved {i}/{min(len(ids),args.limit)}", flush=True)
        time.sleep(0.05)
    payload={"snapshot":{"provider":"Rijksmuseum","provider_id":"rijksmuseum_amsterdam","endpoint":SEARCH,"retrieved_at":datetime.now(timezone.utc).isoformat(),"record_count":len(rows),"discovered":len(ids[:args.limit]),"skipped_without_image":skipped,"selection":"official_search_type_painting"},"records":rows}
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload["snapshot"], indent=2))
if __name__ == "__main__": main()
