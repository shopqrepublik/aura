"""Controlled National Gallery recognition benchmark; no DB/public mutation."""
from __future__ import annotations

import argparse, base64, json, os, shutil, statistics, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
from backend.app.catalog import InstitutionRuntimeConfig
from backend.app.ingestion import stable_id
from backend.app.main import REFERENCE_CACHE_DIR, recognize_with_vision

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = ROOT / "backend/data/onboarding/national_gallery_london/pre_eminent_review_snapshot_2026-08-23.json"
DEFAULT_CORPUS = ROOT / "exports/national_gallery/recognition_corpus_170_v1/manifest.json"
DEFAULT_OUT = ROOT / "exports/national_gallery/recognition_benchmark"


def candidate(row, manifest_row, plus_asset: bool) -> dict:
    artwork_id = stable_id("artwork", row.provider_id, row.provider_record_id)
    return {
        "id": artwork_id, "museum_id": "national-gallery-london", "artist": row.creator_display,
        "title": row.title_original, "year": row.date_display, "inventory_number": row.institution_record_id,
        "department": row.department, "hall": row.room, "object_type": row.object_type,
        "description": row.description, "source_record_id": row.provider_record_id,
        "image_url": manifest_row.get("source_url") if plus_asset else None,
        "recognition_asset_id": f"benchmark:{manifest_row.get('source_media_id')}" if plus_asset else None,
        "priority": 50, "tags": [], "source_urls": [row.source_url] if row.source_url else [],
    }


def config(mode: str) -> InstitutionRuntimeConfig:
    return InstitutionRuntimeConfig(
        institution_id="national-gallery-london", display_name="The National Gallery",
        visitor_catalog_version="ng-controlled-170-v1", candidate_universe="ACTIVE_CATALOG",
        recognition_policy="TOP_N_METADATA" if mode == "vision_ready" else "ASSET_VERIFY",
        supported_modes=("normal",), max_candidates=5, confidence_auto=.92,
        confidence_review=.82, fuzzy_candidate_threshold=.55,
        prompt_context="The National Gallery, London. Resolve only against the supplied institution-scoped candidates.",
        allow_recognition_asset_substitution=mode == "vision_plus_asset",
    )


def percentile(values, p):
    if not values: return None
    values=sorted(values); return values[max(0, min(len(values)-1, round((len(values)-1)*p)))]


def main():
    load_dotenv(ROOT / ".env")
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=("vision_ready","vision_plus_asset"),required=True)
    ap.add_argument("--variant",choices=("pristine","visitor_like","partial"),default="pristine")
    ap.add_argument("--limit",type=int); ap.add_argument("--workers",type=int,default=2)
    ap.add_argument("--snapshot",default=str(DEFAULT_SNAPSHOT),help="Snapshot containing benchmark inputs")
    ap.add_argument("--manifest",default=str(DEFAULT_CORPUS),help="Corpus manifest containing benchmark inputs")
    ap.add_argument("--catalog-snapshot",default=str(DEFAULT_SNAPSHOT),help="Snapshot defining the controlled candidate universe")
    ap.add_argument("--catalog-manifest",default=str(DEFAULT_CORPUS),help="Manifest defining candidate reference assets")
    ap.add_argument("--expect-out-of-catalog",action="store_true")
    ap.add_argument("--out",default=str(DEFAULT_OUT),help="Ignored output directory")
    args=ap.parse_args()
    if not os.getenv("OPENAI_API_KEY"): raise SystemExit("OPENAI_API_KEY required")
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8")); by_provider={r["provider_record_id"]:r for r in manifest["records"] if r["status"]=="READY"}
    catalog_manifest=json.loads(Path(args.catalog_manifest).read_text(encoding="utf-8")); catalog_media={r["provider_record_id"]:r for r in catalog_manifest["records"] if r["status"]=="READY"}
    rows=[r for r in NationalGalleryLondonAdapter(args.snapshot).records() if r.provider_record_id in by_provider]
    if args.limit: rows=rows[:args.limit]
    catalog_rows=[r for r in NationalGalleryLondonAdapter(args.catalog_snapshot).records() if r.provider_record_id in catalog_media]
    candidates=[candidate(r,catalog_media[r.provider_record_id],args.mode=="vision_plus_asset") for r in catalog_rows]
    if args.mode=="vision_plus_asset":
        Path(REFERENCE_CACHE_DIR).mkdir(parents=True,exist_ok=True)
        for c,r in zip(candidates,catalog_rows): shutil.copyfile(ROOT/catalog_media[r.provider_record_id]["files"]["reference"]["path"],Path(REFERENCE_CACHE_DIR)/f'{c["id"]}.jpg')
    cfg=config(args.mode)
    def run(row):
        expected=stable_id("artwork",row.provider_id,row.provider_record_id); m=by_provider[row.provider_record_id]
        image=base64.b64encode((ROOT/m["files"][args.variant]["path"]).read_bytes()).decode(); start=time.perf_counter()
        try:
            result=recognize_with_vision(image,"national-gallery-london",None,candidates,institution_config=cfg); error=None
        except Exception as exc: result={}; error=f"{type(exc).__name__}: {exc}"
        latency=time.perf_counter()-start; chosen=result.get("artwork_id"); confidence=float(result.get("confidence",0) or 0)
        resolution="AUTO_ACCEPTED" if chosen and confidence>=cfg.confidence_auto else "CONFIRMATION_REQUIRED" if chosen and confidence>=cfg.confidence_review else "AI_UNCATALOGED" if result.get("recognized_but_not_cataloged") else "UNRESOLVED"
        top=[x.get("artwork_id") for x in result.get("top_candidates",[])]
        return {"expected_artwork_id":expected,"expected_in_catalog":not args.expect_out_of_catalog,"provider_record_id":row.provider_record_id,"title":row.title_original,"artist":row.creator_display,"variant":args.variant,"mode":args.mode,"chosen_artwork_id":chosen,"confidence":confidence,"correct_top1":chosen==expected,"correct_topk":expected in top,"top_candidates":result.get("top_candidates",[]),"engine_outcome":"CATALOG_CANDIDATE_MATCHED" if chosen else "UNCATALOGED_IDENTIFIED" if result.get("recognized_but_not_cataloged") else "NO_MATCH","visitor_resolution":resolution,"recognition_mode":result.get("recognition_mode"),"latency_s":latency,"failure_reason":error or (result.get("stage2_verifier") or {}).get("reason"),"stage2":result.get("stage2_verifier"),"ai_candidate":result.get("recognized_but_not_cataloged")}
    results=[]
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as pool:
        futures=[pool.submit(run,r) for r in rows]
        for i,f in enumerate(as_completed(futures),1):
            results.append(f.result()); print(f"{i}/{len(futures)}",flush=True)
    results.sort(key=lambda r:r["provider_record_id"]); lat=[r["latency_s"] for r in results]
    summary={"generated_at":datetime.now(timezone.utc).isoformat(),"code_sha":os.getenv("GIT_COMMIT_SHA") or "working-tree","catalog_version":cfg.visitor_catalog_version,"mode":args.mode,"variant":args.variant,"expected_out_of_catalog":args.expect_out_of_catalog,"cases":len(results),"correct_top1":sum(r["correct_top1"] for r in results),"correct_topk":sum(r["correct_topk"] for r in results),"confirmation_required":sum(r["visitor_resolution"]=="CONFIRMATION_REQUIRED" for r in results),"auto_accepted":sum(r["visitor_resolution"]=="AUTO_ACCEPTED" for r in results),"ai_fallback":sum(r["visitor_resolution"]=="AI_UNCATALOGED" for r in results),"unresolved":sum(r["visitor_resolution"]=="UNRESOLVED" for r in results),"incorrect_catalog_match":sum(bool(r["chosen_artwork_id"]) and not r["correct_top1"] for r in results),"confident_incorrect":sum(bool(r["chosen_artwork_id"]) and not r["correct_top1"] and r["confidence"]>=cfg.confidence_auto for r in results),"latency_average_s":statistics.mean(lat) if lat else None,"latency_p50_s":percentile(lat,.5),"latency_p95_s":percentile(lat,.95)}
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True); slug=f'{args.mode}_{args.variant}_{len(results)}'; (out/f'{slug}.jsonl').write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in results),encoding="utf-8"); (out/f'{slug}_summary.json').write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8"); print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
