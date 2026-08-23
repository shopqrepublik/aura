"""Fetch a reproducible metadata-only National Gallery CIIM snapshot.

No image binaries are downloaded. Output includes the exact query and source
response metadata. Run manually; deterministic tests use the checked snapshot.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENDPOINT = "https://data.ng.ac.uk/es/public/_search"
SOURCE_FIELDS = [
    "@admin.uid", "@admin.processed", "summary.title", "title", "identifier",
    "creation", "classification", "category", "location", "multimedia.@admin",
    "multimedia.@type", "legal.rights", "legal.status", "access.item", "access.media", "date",
]


def fetch(timeout: int = 120, pre_eminent_only: bool = False) -> dict:
    filters = [{"term": {"@datatype.base": "object"}}]
    must = [{"match": {"date.type": "Pre-eminent work flag"}}] if pre_eminent_only else []
    query = {
        "size": 5000,
        "_source": SOURCE_FIELDS,
        "query": {"bool": {"filter": filters, "must": must}},
    }
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(query).encode("utf-8"), method="GET",
        headers={"Content-Type": "application/json", "User-Agent": "ELYIO-onboarding/1.0"},
    )
    last_error = None
    for delay in (0, 2, 5):
        if delay: time.sleep(delay)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
                break
        except Exception as exc:
            last_error = exc
    else:
        raise RuntimeError(f"National Gallery source fetch failed: {last_error}")
    hits = payload.get("hits", {}).get("hits", [])
    hits.sort(key=lambda row: ((row.get("_source") or {}).get("@admin") or {}).get("uid", ""))
    return {
        "snapshot": {
            "provider": "National Gallery, London",
            "provider_id": "national_gallery_london",
            "endpoint": ENDPOINT,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "api_status": "beta",
            "query": query,
            "source_total": payload.get("hits", {}).get("total"),
            "record_count": len(hits),
            "images_downloaded": 0,
            "selection": "official_pre_eminent_work_flag" if pre_eminent_only else "all_objects",
        },
        "records": hits,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--pre-eminent-only", action="store_true")
    args = parser.parse_args()
    result = fetch(pre_eminent_only=args.pre_eminent_only)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(result["snapshot"], indent=2))


if __name__ == "__main__":
    main()
