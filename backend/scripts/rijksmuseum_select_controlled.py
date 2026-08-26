"""Deterministically select the image-backed Rijksmuseum tranche."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--snapshot",required=True); ap.add_argument("--output",required=True); ap.add_argument("--target",type=int,default=500); a=ap.parse_args()
    payload=json.loads(Path(a.snapshot).read_text(encoding="utf-8")); rows=sorted(payload["records"], key=lambda r:(r.get("creator_display") or "", r.get("provider_record_id") or ""))
    rows=rows[:a.target]
    out={"catalog_version":"rijksmuseum-controlled-443-v1","summary":{"institution_id":"rijksmuseum-amsterdam","provider_id":"rijksmuseum_amsterdam","target":len(rows),"selection_policy":"all official painting records with usable IIIF image, deterministic creator/id order","source_snapshot":str(Path(a.snapshot))},"records":[{"provider_record_id":r["provider_record_id"]} for r in rows]}
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8"); print(json.dumps(out["summary"],indent=2))
if __name__ == "__main__": main()
