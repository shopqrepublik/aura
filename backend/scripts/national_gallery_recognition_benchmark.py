"""Controlled National Gallery recognition benchmark; no DB/public mutation."""
from __future__ import annotations

import argparse, base64, hashlib, json, os, shutil, statistics, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

try:
    import backend.app.main as recognition_module
    from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
    from backend.app.catalog import InstitutionRuntimeConfig
    from backend.app.ingestion import stable_id
    from backend.app.main import REFERENCE_CACHE_DIR, recognize_with_vision
    from backend.app.visual_retrieval import descriptor_distance, descriptor_from_base64
except ModuleNotFoundError:
    import app.main as recognition_module
    from app.adapters.national_gallery_london import NationalGalleryLondonAdapter
    from app.catalog import InstitutionRuntimeConfig
    from app.ingestion import stable_id
    from app.main import REFERENCE_CACHE_DIR, recognize_with_vision
    from app.visual_retrieval import descriptor_distance, descriptor_from_base64

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2] if (SCRIPT.parents[2] / "backend").exists() else SCRIPT.parents[1]
BACKEND_ROOT = ROOT / "backend" if (ROOT / "backend").exists() else ROOT
DEFAULT_SNAPSHOT = BACKEND_ROOT / "data/onboarding/national_gallery_london/pre_eminent_review_snapshot_2026-08-23.json"
DEFAULT_CORPUS = ROOT / "exports/national_gallery/recognition_corpus_170_v1/manifest.json"
DEFAULT_OUT = ROOT / "exports/national_gallery/recognition_benchmark"


_profile = threading.local()


def install_stage_profiler() -> None:
    targets = {
        "recognize_open": "stage1_visual_analysis",
        "rank_catalog_candidates": "metadata_ranking",
        "rank_visual_candidates": "visual_retrieval",
        "verify_top_candidates_with_openai": "metadata_verification",
        "visual_verify_single_candidate": "asset_verification",
        "visual_verify_reference_candidates": "asset_verification",
    }
    for function_name, stage_name in targets.items():
        original = getattr(recognition_module, function_name)
        def wrapped(*args, __original=original, __stage=stage_name, **kwargs):
            started = time.perf_counter()
            try:
                return __original(*args, **kwargs)
            finally:
                timings = getattr(_profile, "timings", None)
                if timings is not None:
                    timings[__stage] = timings.get(__stage, 0.0) + time.perf_counter() - started
                    if __stage in {"stage1_visual_analysis", "metadata_verification", "asset_verification"}:
                        timings["model_calls"] = timings.get("model_calls", 0) + 1
        setattr(recognition_module, function_name, wrapped)


def candidate(row, manifest_row, plus_asset: bool, visual_descriptor: dict | None = None) -> dict:
    artwork_id = stable_id("artwork", row.provider_id, row.provider_record_id)
    return {
        "id": artwork_id, "museum_id": "national-gallery-london", "artist": row.creator_display,
        "title": row.title_original, "year": row.date_display, "inventory_number": row.institution_record_id,
        "department": row.department, "hall": row.room, "object_type": row.object_type,
        "description": row.description, "source_record_id": row.provider_record_id,
        "image_url": manifest_row.get("source_url") if plus_asset and manifest_row else None,
        "recognition_asset_id": f"benchmark:{manifest_row.get('source_media_id')}" if plus_asset and manifest_row else None,
        "priority": 50, "tags": [], "source_urls": [row.source_url] if row.source_url else [],
        "visual_descriptor": visual_descriptor,
    }


def config(mode: str, catalog_version: str) -> InstitutionRuntimeConfig:
    return InstitutionRuntimeConfig(
        institution_id="national-gallery-london", display_name="The National Gallery",
        visitor_catalog_version=catalog_version, candidate_universe="ACTIVE_CATALOG",
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
    ap.add_argument("--manifest",action="append",help="Repeatable corpus manifest containing benchmark inputs")
    ap.add_argument("--catalog-snapshot",default=str(DEFAULT_SNAPSHOT),help="Snapshot defining the controlled candidate universe")
    ap.add_argument("--catalog-manifest",action="append",help="Repeatable corpus manifest defining candidate reference assets")
    ap.add_argument("--catalog-selection",help="Controlled selection manifest defining the complete candidate universe")
    ap.add_argument("--catalog-version",default="ng-controlled-170-v1")
    ap.add_argument("--visual-descriptors",help="Versioned visual descriptor manifest")
    ap.add_argument("--expect-out-of-catalog",action="store_true")
    ap.add_argument("--input-selection",help="JSON manifest containing named provider-ID benchmark samples")
    ap.add_argument("--sample-name",help="Sample name under input-selection.samples")
    ap.add_argument("--out",default=str(DEFAULT_OUT),help="Ignored output directory")
    ap.add_argument("--profile-stages",action="store_true")
    ap.add_argument("--diagnose-retrieval",action="store_true")
    args=ap.parse_args()
    if not os.getenv("OPENAI_API_KEY"): raise SystemExit("OPENAI_API_KEY required")
    by_provider={}
    for manifest_path in args.manifest or [str(DEFAULT_CORPUS)]:
        manifest=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        by_provider.update({r["provider_record_id"]:r for r in manifest["records"] if r["status"]=="READY"})
    catalog_media={}
    for manifest_path in args.catalog_manifest or [str(DEFAULT_CORPUS)]:
        catalog_manifest=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        catalog_media.update({r["provider_record_id"]:r for r in catalog_manifest["records"] if r["status"]=="READY"})
    rows=[r for r in NationalGalleryLondonAdapter(args.snapshot).records() if r.provider_record_id in by_provider]
    if args.input_selection:
        if not args.sample_name: ap.error("--sample-name is required with --input-selection")
        sample_payload=json.loads(Path(args.input_selection).read_text(encoding="utf-8"))
        sample_ids=set(sample_payload["samples"][args.sample_name])
        rows=[r for r in rows if r.provider_record_id in sample_ids]
    if args.limit: rows=rows[:args.limit]
    catalog_selected = set(catalog_media)
    if args.catalog_selection:
        selected_payload=json.loads(Path(args.catalog_selection).read_text(encoding="utf-8"))
        catalog_selected={str(r["provider_record_id"]) for r in selected_payload["records"]}
    catalog_rows=[r for r in NationalGalleryLondonAdapter(args.catalog_snapshot).records() if r.provider_record_id in catalog_selected]
    catalog_row_ids = {row.provider_record_id for row in catalog_rows}
    missing_catalog_rows = catalog_selected - catalog_row_ids
    if missing_catalog_rows:
        raise SystemExit(
            "catalog snapshot/selection parity failed: "
            f"selected={len(catalog_selected)} rows={len(catalog_rows)} "
            f"missing={len(missing_catalog_rows)}"
        )
    visual_descriptors = {}
    if args.visual_descriptors:
        payload = json.loads(Path(args.visual_descriptors).read_text(encoding="utf-8"))
        visual_descriptors = {
            str(row["provider_record_id"]): {
                "version": row["version"], "values": row["values"],
                "source_sha256": row["source_sha256"],
            }
            for row in payload["records"]
        }
    candidates=[candidate(r,catalog_media.get(r.provider_record_id),args.mode=="vision_plus_asset",visual_descriptors.get(r.provider_record_id)) for r in catalog_rows]
    if args.mode=="vision_plus_asset":
        Path(REFERENCE_CACHE_DIR).mkdir(parents=True,exist_ok=True)
        for c,r in zip(candidates,catalog_rows):
            if r.provider_record_id in catalog_media:
                shutil.copyfile(ROOT/catalog_media[r.provider_record_id]["files"]["reference"]["path"],Path(REFERENCE_CACHE_DIR)/f'{c["id"]}.jpg')
    cfg=config(args.mode,args.catalog_version)
    if args.profile_stages: install_stage_profiler()
    def run(row):
        expected=stable_id("artwork",row.provider_id,row.provider_record_id); m=by_provider[row.provider_record_id]
        image=base64.b64encode((ROOT/m["files"][args.variant]["path"]).read_bytes()).decode(); start=time.perf_counter()
        # Keep concurrent benchmark cases isolated from any candidate-row
        # annotations made by the recognition path. Production loads a fresh
        # scoped candidate payload per request; the harness must model that
        # instead of sharing mutable dictionaries between worker threads.
        case_candidates = [{**item, "visual_descriptor": dict(item["visual_descriptor"]) if item.get("visual_descriptor") else None} for item in candidates]
        pre_visual = recognition_module.rank_visual_candidates(image, case_candidates, limit=len(case_candidates)) if args.diagnose_retrieval else []
        pre_visual_ids = [item["candidate"]["id"] for item in pre_visual]
        pre_visual_rank = pre_visual_ids.index(expected) + 1 if expected in pre_visual_ids else None
        expected_candidate = next((item for item in case_candidates if item["id"] == expected), None)
        expected_visual_distance = descriptor_distance(
            descriptor_from_base64(image),
            (expected_candidate or {}).get("visual_descriptor", {}).get("values", []),
        ) if args.diagnose_retrieval and expected_candidate else None
        _profile.timings = {}
        try:
            result=recognize_with_vision(image,"national-gallery-london",None,case_candidates,institution_config=cfg); error=None
        except Exception as exc: result={}; error=f"{type(exc).__name__}: {exc}"
        latency=time.perf_counter()-start; chosen=result.get("artwork_id"); confidence=float(result.get("confidence",0) or 0)
        resolution="AUTO_ACCEPTED" if chosen and confidence>=cfg.confidence_auto else "CONFIRMATION_REQUIRED" if chosen and confidence>=cfg.confidence_review else "AI_UNCATALOGED" if result.get("recognized_but_not_cataloged") else "UNRESOLVED"
        top=[x.get("artwork_id") for x in result.get("top_candidates",[])]
        measured=sum(value for key,value in _profile.timings.items() if key!="model_calls")
        stage_timings={**_profile.timings,"finalization_and_unmeasured":max(0.0,latency-measured)}
        metadata_rank = visual_rank = None
        if args.diagnose_retrieval and result.get("vision"):
            diagnostic_metadata = recognition_module.rank_catalog_candidates(result["vision"], candidates, hall_hint=None, limit=len(candidates))
            metadata_ids = [item["candidate"]["id"] for item in diagnostic_metadata]
            metadata_rank = metadata_ids.index(expected) + 1 if expected in metadata_ids else None
            diagnostic_visual = recognition_module.rank_visual_candidates(image, case_candidates, limit=len(case_candidates))
            visual_ids = [item["candidate"]["id"] for item in diagnostic_visual]
            visual_rank = visual_ids.index(expected) + 1 if expected in visual_ids else pre_visual_rank
        elif args.diagnose_retrieval:
            visual_rank = pre_visual_rank
        return {"expected_artwork_id":expected,"expected_in_catalog":not args.expect_out_of_catalog,"provider_record_id":row.provider_record_id,"title":row.title_original,"artist":row.creator_display,"variant":args.variant,"mode":args.mode,"chosen_artwork_id":chosen,"confidence":confidence,"correct_top1":chosen==expected,"correct_topk":expected in top,"metadata_candidate_rank":metadata_rank,"visual_candidate_rank":visual_rank,"expected_visual_distance":expected_visual_distance,"input_sha256":hashlib.sha256(base64.b64decode(image)).hexdigest(),"pre_visual_top_ids":[item["candidate"]["id"] for item in pre_visual[:5]],"top_candidates":result.get("top_candidates",[]),"engine_outcome":"CATALOG_CANDIDATE_MATCHED" if chosen else "UNCATALOGED_IDENTIFIED" if result.get("recognized_but_not_cataloged") else "NO_MATCH","visitor_resolution":resolution,"recognition_mode":result.get("recognition_mode"),"latency_s":latency,"stage_timings_s":stage_timings,"failure_reason":error or (result.get("stage2_verifier") or {}).get("reason"),"stage1":result.get("vision"),"stage2":result.get("stage2_verifier"),"ai_candidate":result.get("recognized_but_not_cataloged")}
    results=[]
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as pool:
        futures=[pool.submit(run,r) for r in rows]
        for i,f in enumerate(as_completed(futures),1):
            results.append(f.result()); print(f"{i}/{len(futures)}",flush=True)
    results.sort(key=lambda r:r["provider_record_id"]); lat=[r["latency_s"] for r in results]
    stage_names=sorted({key for row in results for key in row.get("stage_timings_s",{})})
    stage_summary={name:{"average_s":statistics.mean([row["stage_timings_s"].get(name,0) for row in results]),"p50_s":percentile([row["stage_timings_s"].get(name,0) for row in results],.5),"p95_s":percentile([row["stage_timings_s"].get(name,0) for row in results],.95)} for name in stage_names if name!="model_calls"}
    recall = {f"recall_at_{cutoff}": sum((row.get("visual_candidate_rank") or 10**9) <= cutoff for row in results) for cutoff in (1,3,5,10,20)} if args.diagnose_retrieval else {}
    summary={"generated_at":datetime.now(timezone.utc).isoformat(),"code_sha":os.getenv("GIT_COMMIT_SHA") or "working-tree","catalog_version":cfg.visitor_catalog_version,"mode":args.mode,"variant":args.variant,"expected_out_of_catalog":args.expect_out_of_catalog,"cases":len(results),"correct_top1":sum(r["correct_top1"] for r in results),"correct_topk":sum(r["correct_topk"] for r in results),"confirmation_required":sum(r["visitor_resolution"]=="CONFIRMATION_REQUIRED" for r in results),"auto_accepted":sum(r["visitor_resolution"]=="AUTO_ACCEPTED" for r in results),"ai_fallback":sum(r["visitor_resolution"]=="AI_UNCATALOGED" for r in results),"unresolved":sum(r["visitor_resolution"]=="UNRESOLVED" for r in results),"incorrect_catalog_match":sum(bool(r["chosen_artwork_id"]) and not r["correct_top1"] for r in results),"confident_incorrect":sum(bool(r["chosen_artwork_id"]) and not r["correct_top1"] and r["confidence"]>=cfg.confidence_auto for r in results),"latency_average_s":statistics.mean(lat) if lat else None,"latency_p50_s":percentile(lat,.5),"latency_p95_s":percentile(lat,.95),"model_calls_average":statistics.mean([row.get("stage_timings_s",{}).get("model_calls",0) for row in results]),"visual_candidate_recall":recall,"stage_timings":stage_summary}
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True); slug=f'{args.mode}_{args.variant}_{len(results)}'; (out/f'{slug}.jsonl').write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in results),encoding="utf-8"); (out/f'{slug}_summary.json').write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8"); print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
