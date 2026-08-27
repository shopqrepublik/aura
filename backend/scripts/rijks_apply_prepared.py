"""Apply prepared Rijksmuseum records using generic Factory phases."""
import argparse, importlib, json
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.app.adapters.json_file import JsonFileAdapter
from backend.app.ingestion import apply_plan, build_plan, stable_id
from backend.app.models import Country, Museum, InstitutionProfile, SourceProvider, Artwork, ArtworkCatalogMembership, RecognitionAsset, MediaAssetAssociation, MediaAsset
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/'backend/data/onboarding/rijksmuseum_amsterdam'; INST='rijksmuseum-amsterdam'; PROVIDER='rijksmuseum_amsterdam'
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--operator',required=True); ap.add_argument('--batch-size',type=int,default=25); ap.add_argument('--activate',action='store_true'); ap.add_argument('--activation-batch-size',type=int,default=50); a=ap.parse_args(); load_dotenv(ROOT/'.env'); import backend.app.db as dbm; dbm=importlib.reload(dbm)
 sel=json.loads((D/'controlled_catalog_443_v1.json').read_text(encoding='utf-8')); desc=json.loads((D/'controlled_catalog_443_visual_descriptors_v1.json').read_text(encoding='utf-8')); descriptors={str(x['provider_record_id']):x for x in desc['records']}; ids={str(x['provider_record_id']) for x in sel['records']}; payload=json.loads((D/'source_snapshot_v1.json').read_text(encoding='utf-8')); records=[r for r in payload['records'] if str(r['provider_record_id']) in ids]
 with dbm.SessionLocal() as db:
  db.execute(text("SET statement_timeout='120s'")); db.add(db.get(Country,'NL') or Country(code='NL',name='Netherlands',default_locale='en',default_timezone='Europe/Amsterdam',default_currency='EUR')); db.flush()
  inst=db.get(Museum,INST) or Museum(id=INST,name='Rijksmuseum'); inst.name='Rijksmuseum'; inst.city='Amsterdam'; inst.country_code='NL'; inst.timezone='Europe/Amsterdam'; inst.default_locale='en'; inst.supported_locales=['en']; inst.display_currency='EUR'; inst.content_policy={'controlled_preview_only':True,'seo_enabled':False}; inst.active=True; db.add(inst); db.flush()
  prof=db.get(InstitutionProfile,INST) or InstitutionProfile(institution_id=INST); prof.visitor_catalog_version=sel['catalog_version']; prof.candidate_universe='ACTIVE_CATALOG'; prof.recognition_policy='ASSET_VERIFY'; prof.confidence_auto=.92; prof.confidence_review=.82; prof.active=True; db.add(prof)
  provider=db.get(SourceProvider,PROVIDER) or SourceProvider(id=PROVIDER,name='Rijksmuseum',provider_type='MUSEUM'); provider.base_url='https://data.rijksmuseum.nl'; provider.adapter_key='normalized_json_v1'; provider.adapter_config={'institution_ids':[INST]}; provider.active=True; db.add(provider); db.flush()
  for start in range(0,len(records),a.batch_size):
   part=D/'_rijks_batch.json'; part.write_text(json.dumps({'records':records[start:start+a.batch_size]})); plan=build_plan(db,JsonFileAdapter(part,PROVIDER,INST),INST,mode='PLAN'); apply_plan(db,plan,operator_id=a.operator); print(json.dumps({'batch':start//a.batch_size+1,'batches':(len(records)+a.batch_size-1)//a.batch_size,'plan':plan.summary}),flush=True)
  if not a.activate: print(json.dumps({'prepared':len(records),'activated':0})); return
  # Activation is deliberately set-based: no per-artwork remote reads/writes.
  ids=[stable_id('artwork',PROVIDER,str(row['provider_record_id'])) for row in sel['records']]
  for start in range(0,len(ids),a.activation_batch_size):
   batch=ids[start:start+a.activation_batch_size]
   values=[{'artwork_id':aid,'museum_id':INST,'catalog_version':sel['catalog_version'],'active':True,'tier':'CONTROLLED_PREVIEW','visitor_priority':1} for aid in batch]
   stmt=pg_insert(ArtworkCatalogMembership).values(values).on_conflict_do_update(index_elements=['artwork_id','catalog_version'],set_={'active':True,'tier':'CONTROLLED_PREVIEW','visitor_priority':1})
   result=db.execute(stmt); db.commit(); print(json.dumps({'activation_batch':start//a.activation_batch_size+1,'batches':(len(ids)+a.activation_batch_size-1)//a.activation_batch_size,'requested':len(batch),'affected':result.rowcount}),flush=True)
  ra_count=db.query(RecognitionAsset).join(Artwork,RecognitionAsset.artwork_id==Artwork.id).filter(Artwork.id.in_(ids)).count(); db.execute(text('SET statement_timeout=\'120s\'')); print(json.dumps({'prepared':len(records),'activated':len(ids),'recognition_assets_verified':ra_count,'descriptors':len(descriptors)}))
if __name__=='__main__': main()
