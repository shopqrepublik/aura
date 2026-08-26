"""Single-record production-adjacent Museum Factory canary."""
from __future__ import annotations
import argparse, importlib, json, time
from pathlib import Path
from dotenv import load_dotenv
from backend.app.adapters.json_file import JsonFileAdapter
from backend.app.ingestion import apply_plan, build_plan
from backend.app.models import Country, Institution, InstitutionProfile, SourceProvider

ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/"backend/data/onboarding/metropolitan_museum_new_york"; SNAPSHOT=DATA/"canary_snapshot_v1.json"; INST="metropolitan-museum-new-york"; PROVIDER="metropolitan_museum_open_access"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--operator",required=True); a=ap.parse_args(); load_dotenv(ROOT/".env"); import backend.app.db as dbm; dbm=importlib.reload(dbm)
    timings={}; started=time.perf_counter()
    with dbm.SessionLocal() as db:
        db.execute(__import__("sqlalchemy").text("SET statement_timeout = '120s'")); timings["connect_and_timeout_s"]=time.perf_counter()-started
        t=time.perf_counter(); country=db.get(Country,"US") or Country(code="US",name="United States",default_locale="en",default_timezone="America/New_York",default_currency="USD"); db.add(country); db.flush(); timings["institution_upsert_s"]=time.perf_counter()-t
        inst=db.get(Institution,INST) or Institution(id=INST,slug=INST,name="The Metropolitan Museum of Art"); inst.common_name="The Met"; inst.city="New York"; inst.country_code="US"; inst.timezone="America/New_York"; inst.default_locale="en"; inst.supported_locales=["en"]; inst.display_currency="USD"; inst.content_policy={"controlled_preview_only":True,"seo_enabled":False}; inst.active=True; db.add(inst); db.flush()
        prof=db.get(InstitutionProfile,INST) or InstitutionProfile(institution_id=INST); prof.visitor_catalog_version="met-controlled-1-v1"; prof.candidate_universe="ACTIVE_CATALOG"; prof.recognition_policy="ASSET_VERIFY"; prof.confidence_auto=.92; prof.confidence_review=.82; prof.active=True; db.add(prof)
        provider=db.get(SourceProvider,PROVIDER) or SourceProvider(id=PROVIDER,name="The Metropolitan Museum of Art",provider_type="MUSEUM"); provider.base_url="https://collectionapi.metmuseum.org/public/collection/v1"; provider.adapter_key="normalized_json_v1"; provider.adapter_config={"institution_ids":[INST]}; provider.active=True; db.add(provider); db.flush()
        adapter=JsonFileAdapter(SNAPSHOT,PROVIDER,INST); t=time.perf_counter(); plan=build_plan(db,adapter,INST,mode="PLAN"); timings["plan_s"]=time.perf_counter()-t; t=time.perf_counter(); run_id=apply_plan(db,plan,operator_id=a.operator); timings["commit_s"]=time.perf_counter()-t
        print(json.dumps({"status":"PASS","run_id":run_id,"records":plan.summary["records_inspected"],"plan":plan.summary,"timings":timings},indent=2,default=str))
if __name__=="__main__": main()
