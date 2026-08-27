"""Persist prepared RecognitionAssets without activating memberships."""
import argparse,importlib,json
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from backend.app.ingestion import stable_id
from backend.app.models import Artwork,RecognitionAsset
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/'backend/data/onboarding/rijksmuseum_amsterdam'; INST='rijksmuseum-amsterdam'; PROVIDER='rijksmuseum_amsterdam'
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--operator',required=True); ap.add_argument('--batch-size',type=int,default=50); a=ap.parse_args(); load_dotenv(ROOT/'.env'); import backend.app.db as dbm; dbm=importlib.reload(dbm)
 sel=json.loads((D/'controlled_catalog_443_v1.json').read_text(encoding='utf-8')); snap=json.loads((D/'source_snapshot_v1.json').read_text(encoding='utf-8')); desc=json.loads((D/'controlled_catalog_443_visual_descriptors_v1.json').read_text(encoding='utf-8')); ids=[str(x['provider_record_id']) for x in sel['records']]; source={str(x['provider_record_id']):x for x in snap['records']}; dv={str(x['provider_record_id']):x for x in desc['records']}; aids=[stable_id('artwork',PROVIDER,p) for p in ids]
 with dbm.SessionLocal() as db:
  db.execute(text("SET statement_timeout='120s'")); existing=db.query(RecognitionAsset).filter(RecognitionAsset.artwork_id.in_(aids)).all(); by={(x.artwork_id,x.source_url):x for x in existing}; created=0; updated=0
  for start in range(0,len(ids),a.batch_size):
   batch=[]
   for pid,aid in zip(ids[start:start+a.batch_size],aids[start:start+a.batch_size]):
    url=source[pid]['media'][0]['original_url']; rec=by.get((aid,url))
    if rec is None: rec=RecognitionAsset(artwork_id=aid,source='rijksmuseum_prepared',source_url=url); batch.append(rec); by[(aid,url)]=rec; created+=1
    rec.rights_status='public_domain'; rec.ai_tdm_eligible=True; rec.embedding_eligible=True; rec.local_storage_status='not_fetched'; rec.visual_descriptor=dv.get(pid); updated+=1
   db.add_all(batch); db.commit(); print(json.dumps({'batch':start//a.batch_size+1,'requested':len(batch),'created':len(batch)}),flush=True)
  print(json.dumps({'recognition_assets':db.query(RecognitionAsset).filter(RecognitionAsset.artwork_id.in_(aids)).count(),'created':created,'updated':updated,'duplicates':0}))
if __name__=='__main__':main()
