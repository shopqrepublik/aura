"""Small, repeatable orchestration wrapper for institution onboarding.

This intentionally delegates persistence and readiness to the existing generic
ingestion commands. It provides a uniform DISCOVER/DRY_RUN/PLAN/APPLY/STATUS
surface for the next museum without introducing a second catalog system.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=("DISCOVER","DRY_RUN","PLAN","APPLY","STATUS","PREPARE_RECOGNITION","BENCHMARK","ACTIVATE_CONTROLLED")); ap.add_argument("--config", required=True); ap.add_argument("--input"); ap.add_argument("--operator"); ap.add_argument("--adapter", default="normalized_json_v1"); ap.add_argument("--provider"); ap.add_argument("--institution")
    args = ap.parse_args(); cfg = json.loads(Path(args.config).read_text(encoding="utf-8")); inst = args.institution or cfg["institution_id"]; provider = args.provider or cfg["provider_id"]
    if args.mode == "ACTIVATE_CONTROLLED":
        from dotenv import load_dotenv
        from sqlalchemy import text
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from backend.app.ingestion import stable_id
        from backend.app.models import ArtworkCatalogMembership, RecognitionAsset, Artwork
        load_dotenv(ROOT/".env"); import backend.app.db as dbm; dbm=importlib.reload(dbm)
        if not args.input: raise SystemExit("ACTIVATE_CONTROLLED requires --input normalized package")
        payload=json.loads(Path(args.input).read_text(encoding="utf-8")); ids=[stable_id("artwork",provider,str(r["provider_record_id"])) for r in payload["records"]]
        with dbm.SessionLocal() as db:
            db.execute(text("SET statement_timeout='120s'")); ready=db.query(RecognitionAsset).filter(RecognitionAsset.artwork_id.in_(ids),RecognitionAsset.visual_descriptor.isnot(None),RecognitionAsset.embedding_eligible.is_(True)).count()
            if ready != len(ids): raise SystemExit(f"activation blocked: recognition-ready assets {ready}/{len(ids)}")
            version=cfg.get("catalog_version",f"{inst}-controlled-{len(ids)}-v1")
            for start in range(0,len(ids),50):
                batch=ids[start:start+50]; values=[{"artwork_id":x,"museum_id":inst,"catalog_version":version,"active":True,"tier":"CONTROLLED_PREVIEW","visitor_priority":1} for x in batch]
                db.execute(pg_insert(ArtworkCatalogMembership).values(values).on_conflict_do_update(index_elements=["artwork_id","catalog_version"],set_={"active":True,"tier":"CONTROLLED_PREVIEW","visitor_priority":1})); db.commit()
            print(json.dumps({"active":db.query(ArtworkCatalogMembership).filter_by(museum_id=inst,catalog_version=version,active=True).count(),"recognition_assets":ready,"catalog_version":version}))
        return 0
    if args.mode in {"PREPARE_RECOGNITION","BENCHMARK"}:
        raise SystemExit(f"{args.mode} requires the existing institution-specific preparation/benchmark command; no second recognition pipeline is created")
    cmd=[sys.executable, str(ROOT/"backend/scripts/ingest_catalog.py"), args.mode, "--adapter", args.adapter, "--provider", provider, "--institution", inst]
    if args.input: cmd += ["--input", args.input]
    if args.operator: cmd += ["--operator", args.operator]
    return subprocess.call(cmd)
if __name__ == "__main__": raise SystemExit(main())
