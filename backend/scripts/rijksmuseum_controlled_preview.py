"""Idempotent Rijksmuseum controlled-preview activation for Factory V1."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from dotenv import load_dotenv
from backend.app.adapters.json_file import JsonFileAdapter
from backend.app.ingestion import apply_plan, build_plan, stable_id
from backend.app.models import Artwork, ArtworkCatalogMembership, Country, Institution, InstitutionProfile, MediaAsset, MediaAssetAssociation, RecognitionAsset, SourceProvider

ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/"backend/data/onboarding/rijksmuseum_amsterdam"; SNAPSHOT=DATA/"source_snapshot_v1.json"; SELECTION=DATA/"controlled_catalog_443_v1.json"; READINESS=DATA/"controlled_catalog_443_recognition_readiness_v1.json"; DESCRIPTORS=DATA/"controlled_catalog_443_visual_descriptors_v1.json"; INST="rijksmuseum-amsterdam"; PROVIDER="rijksmuseum_amsterdam"; VERSION="rijksmuseum-controlled-443-v1"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--operator",required=True); ap.add_argument("--activate",action="store_true"); a=ap.parse_args()
    load_dotenv(ROOT/".env")
    import importlib, backend.app.db as db_module
    db_module = importlib.reload(db_module)
    with db_module.SessionLocal() as db:
        try:
            db.execute(__import__("sqlalchemy").text("SET statement_timeout = '120s'"))
        except Exception:
            pass
        if db.get(Country,"NL") is None: db.add(Country(code="NL",name="Netherlands",default_locale="en",default_timezone="Europe/Amsterdam",default_currency="EUR"))
        inst=db.get(Institution,INST) or Institution(id=INST,slug=INST,name="Rijksmuseum"); inst.common_name="Rijksmuseum"; inst.city="Amsterdam"; inst.country_code="NL"; inst.timezone="Europe/Amsterdam"; inst.default_locale="en"; inst.supported_locales=["en","nl"]; inst.display_currency="EUR"; inst.experience_level="CURATED"; inst.active=True; inst.content_policy={"controlled_preview_only":True,"seo_enabled":False}; db.add(inst); db.flush()
        prof=db.get(InstitutionProfile,INST) or InstitutionProfile(institution_id=INST); prof.visitor_catalog_version=VERSION; prof.candidate_universe="ACTIVE_CATALOG"; prof.recognition_policy="ASSET_VERIFY"; prof.supported_modes=["normal","simple","kids"]; prof.max_candidates=5; prof.confidence_auto=.92; prof.confidence_review=.82; prof.fuzzy_candidate_threshold=.55; prof.allow_recognition_asset_substitution=True; prof.active=True; db.add(prof)
        provider=db.get(SourceProvider,PROVIDER) or SourceProvider(id=PROVIDER,name="Rijksmuseum",provider_type="MUSEUM"); provider.base_url="https://data.rijksmuseum.nl"; provider.adapter_key="normalized_json_v1"; provider.adapter_config={"institution_ids":[INST]}; provider.active=True; db.add(provider); db.flush()
        adapter=JsonFileAdapter(SNAPSHOT,PROVIDER,INST)
        selected_ids=[str(x["provider_record_id"]) for x in json.loads(SELECTION.read_text())["records"]]
        class BatchAdapter:
            adapter_key=adapter.adapter_key; provider_id=adapter.provider_id
            def __init__(self, rows): self._rows=tuple(rows)
            def records(self): return iter(self._rows)
            def source_snapshot(self): return adapter.source_snapshot()
        rows=list(adapter.records()); by_id={r.provider_record_id:r for r in rows}; run_ids=[]
        for offset in range(0,len(selected_ids),50):
            batch=BatchAdapter([by_id[x] for x in selected_ids[offset:offset+50]])
            plan=build_plan(db,batch,INST,mode="PLAN")
            try:
                db.execute(__import__("sqlalchemy").text("SET statement_timeout = '120s'"))
            except Exception:
                pass
            run_ids.append(apply_plan(db,plan,operator_id=a.operator)); print(f"batch {offset//50+1}/{(len(selected_ids)+49)//50} committed",flush=True)
        run_id=run_ids[-1] if run_ids else None
        if a.activate:
            selected=[str(x["provider_record_id"]) for x in json.loads(SELECTION.read_text())["records"]]; ready={str(x["provider_record_id"]) for x in json.loads(READINESS.read_text())["records"] if x["readiness"]=="VISION_PLUS_ASSET"}; desc={str(x["provider_record_id"]):x for x in json.loads(DESCRIPTORS.read_text())["records"]}; arts={x.id:x for x in db.query(Artwork).filter(Artwork.museum_id==INST).all()}; created=0
            for pid in selected:
                aid=stable_id("artwork",PROVIDER,pid); art=arts.get(aid)
                if not art: continue
                m=db.query(ArtworkCatalogMembership).filter_by(artwork_id=aid,museum_id=INST,catalog_version=VERSION).one_or_none() or ArtworkCatalogMembership(artwork_id=aid,museum_id=INST,catalog_version=VERSION)
                m.active=True; m.tier="CONTROLLED_PREVIEW"; db.add(m)
                if pid in ready:
                    edge=db.query(MediaAssetAssociation).filter_by(institution_holding_id=art.institution_holding_id,active=True).join(MediaAsset,MediaAsset.id==MediaAssetAssociation.media_asset_id).filter(MediaAsset.media_type=="IMAGE").first()
                    if edge:
                        media=db.get(MediaAsset,edge.media_asset_id); media.recognition_eligible=True; edge.recognition_eligible=True; db.add(media); db.add(edge)
                        url=media.original_url; rec=db.query(RecognitionAsset).filter_by(artwork_id=aid,source_url=url).one_or_none() or RecognitionAsset(artwork_id=aid,source="rijksmuseum_controlled_preview",source_url=url); rec.ai_tdm_eligible=True; rec.embedding_eligible=True; rec.rights_status="public_domain"; rec.local_storage_status="not_fetched"; rec.visual_descriptor=desc.get(pid); db.add(rec); created+=1
            db.commit(); print(json.dumps({"ingestion_run_id":run_id,"controlled":len(selected),"recognition_assets_created_or_present":created,"catalog_version":VERSION,"public":False},indent=2))
        else: db.rollback(); print(json.dumps({"ingestion_run_id":run_id,"plan":plan.summary,"activation":False},indent=2))
if __name__=="__main__": main()
