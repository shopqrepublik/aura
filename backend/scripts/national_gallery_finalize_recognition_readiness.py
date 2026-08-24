"""Create a compact, reviewable recognition-readiness manifest from corpora."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2] if (SCRIPT.parents[2] / "backend").exists() else SCRIPT.parents[1]
DATA = (ROOT / "backend" if (ROOT / "backend").exists() else ROOT) / "data/onboarding/national_gallery_london"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", default=str(DATA / "controlled_catalog_500_v1.json"))
    parser.add_argument("--corpus-manifest", action="append", required=True)
    parser.add_argument("--out", default=str(DATA / "controlled_catalog_500_recognition_readiness_v1.json"))
    args = parser.parse_args()
    selection = json.loads(Path(args.selection).read_text(encoding="utf-8"))
    corpus = {}
    corpus_hashes = []
    for value in args.corpus_manifest:
        path = Path(value); payload = json.loads(path.read_text(encoding="utf-8"))
        corpus_hashes.append({"manifest": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        corpus.update({str(row["provider_record_id"]): row for row in payload["records"]})
    records = []
    for selected in selection["records"]:
        provider_id = str(selected["provider_record_id"]); prepared = corpus.get(provider_id)
        if prepared and prepared.get("status") == "READY":
            readiness, reason = "VISION_PLUS_ASSET", "technical reference derivative prepared"
        elif prepared:
            readiness, reason = "VISION_READY", f'media preparation status: {prepared.get("status")}'
        else:
            readiness, reason = "VISION_READY", "metadata-qualified; no prepared recognition derivative"
        records.append({"provider_record_id": provider_id, "readiness": readiness, "reason": reason})
    summary = {
        "total": len(records),
        "vision_plus_asset": sum(row["readiness"] == "VISION_PLUS_ASSET" for row in records),
        "vision_ready": sum(row["readiness"] == "VISION_READY" for row in records),
        "not_ready": sum(row["readiness"] == "NOT_READY" for row in records),
    }
    payload = {"schema_version": 1, "catalog_version": selection["catalog_version"], "corpus_manifests": corpus_hashes, "summary": summary, "records": records}
    out = Path(args.out); out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
