"""Apply the prepared Met tranche through generic ingestion and activate controlled preview."""
import argparse,importlib,json,time
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from backend.app.adapters.json_file import JsonFileAdapter
from backend.app.ingestion import apply_plan,build_plan,stable_id
from backend.app.models import Country,Museum,InstitutionProfile,SourceProvider,Artwork,ArtworkCatalogMembership,RecognitionAsset,MediaAssetAssociation,MediaAsset
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/'backend/data/onboarding/metropolitan_museum_new_york'; INST='metropolitan-museum-new-york'; PROVIDER='metropolitan_museum_open_access'
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--operator',required=True); ap.add_argument('--batch-size',type=int,default=10); a=ap.parse_args(); load_dotenv(ROOT/'.env'); import backend.app.db as dbm; dbm=importlib.reload(dbm)
 snap=D/'met_tranche_snapshot_v1.json'; sel=json.loads((D/'met_controlled_selection_v1.json').read_text()); desc=json.loads((D/'met_visual_descriptors_v1.json').read_text()); descriptors={str(x['provider_record_id']):x for x in desc['records']}; payload=json.loads(snap.read_text())
 with dbm.SessionLocal() as db:
  db.execute(text("SET statement_timeout='120s'")); db.add(db.get(Country,'US') or Country(code='US',name='United States',default_locale='en',default_timezone='America/New_York',default_currency='USD')); db.flush(); inst=db.get(Museum,INST) or Museum(id=INST,name='The Metropolitan Museum of Art'); inst.name='The Metropolitan Museum of Art'; inst.common_name='The Met'; inst.city='New York'; inst.country_code='US'; inst.timezone='America/New_York'; inst.default_locale='en'; inst.supported_locales=['en']; inst.display_currency='USD'; inst.content_policy={'controlled_preview_only':True,'seo_enabled':False}; inst.active=True; db.add(inst); prof=db.get(InstitutionProfile,INST) or InstitutionProfile(institution_id=INST); prof.visitor_catalog_version=sel['catalog_version']; prof.candidate_universe='ACTIVE_CATALOG'; prof.recognition_policy='ASSET_VERIFY'; prof.confidence_auto=.92; prof.confidence_review=.82; prof.active=True; db.add(prof); provider=db.get(SourceProvider,PROVIDER) or SourceProvider(id=PROVIDER,name='The Metropolitan Museum of Art',provider_type='MUSEUM'); provider.base_url='https://collectionapi.metmuseum.org/public/collection/v1'; provider.adapter_key='normalized_json_v1'; provider.adapter_config={'institution_ids':[INST]}; provider.active=True; db.add(provider); db.flush()
  runs=[]
  for start in range(0,len(payload['records']),a.batch_size):
   part=D/'_met_batch.json'; part.write_text(json.dumps({'records':payload['records'][start:start+a.batch_size]})); adapter=JsonFileAdapter(part,PROVIDER,INST); plan=build_plan(db,adapter,INST,mode='PLAN'); rid=apply_plan(db,plan,operator_id=a.operator); runs.append(rid); print(json.dumps({'batch':start//a.batch_size+1,'batches':(len(payload['records'])+a.batch_size-1)//a.batch_size,'plan':plan.summary}),flush=True)
  # Generic activation: membership plus RecognitionAsset and descriptor, keyed by canonical stable artwork ID.
  for row in sel['records']:
   pid=str(row['provider_record_id']); aid=stable_id('artwork',PROVIDER,pid); art=db.get(Artwork,aid)
   if not art: raise RuntimeError('missing artwork '+aid)
   m=db.query(ArtworkCatalogMembership).filter_by(artwork_id=aid,catalog_version=sel['catalog_version']).first() or ArtworkCatalogMembership(artwork_id=aid,museum_id=INST,catalog_version=sel['catalog_version']); m.active=True; m.tier='CONTROLLED_PREVIEW'; m.visitor_priority=1; db.add(m)
   edge=db.query(MediaAssetAssociation).filter_by(institution_holding_id=art.institution_holding_id,active=True).first(); media=db.get(MediaAsset,edge.media_asset_id) if edge else None
   src=media.original_url if media else None; rec=db.query(RecognitionAsset).filter_by(artwork_id=aid,source_url=src).first() if src else None
   if rec is None and src: rec=RecognitionAsset(artwork_id=aid,source='met_controlled_preview',source_url=src); db.add(rec)
   if rec: rec.ai_tdm_eligible=True; rec.embedding_eligible=True; rec.local_storage_status='not_fetched'; rec.visual_descriptor=descriptors.get(pid)
  db.commit(); print(json.dumps({'controlled':len(sel['records']),'recognition_assets':len(sel['records']),'descriptors':len(descriptors)}))
if __name__=='__main__':main()
