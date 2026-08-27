"""Set-based activation of an already-prepared Rijksmuseum catalog."""
import argparse,importlib,json
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.app.ingestion import stable_id
from backend.app.models import ArtworkCatalogMembership,RecognitionAsset,Artwork
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/'backend/data/onboarding/rijksmuseum_amsterdam'; INST='rijksmuseum-amsterdam'
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--operator',required=True); ap.add_argument('--batch-size',type=int,default=50); a=ap.parse_args(); load_dotenv(ROOT/'.env'); import backend.app.db as dbm; dbm=importlib.reload(dbm); sel=json.loads((D/'controlled_catalog_443_v1.json').read_text(encoding='utf-8')); ids=[stable_id('artwork','rijksmuseum_amsterdam',str(x['provider_record_id'])) for x in sel['records']]
 with dbm.SessionLocal() as db:
  db.execute(text("SET statement_timeout='120s'"))
  for start in range(0,len(ids),a.batch_size):
   batch=ids[start:start+a.batch_size]; values=[{'artwork_id':x,'museum_id':INST,'catalog_version':'rijksmuseum-controlled-443-v1','active':True,'tier':'CONTROLLED_PREVIEW','visitor_priority':1} for x in batch]; stmt=pg_insert(ArtworkCatalogMembership).values(values).on_conflict_do_update(index_elements=['artwork_id','catalog_version'],set_={'active':True,'tier':'CONTROLLED_PREVIEW','visitor_priority':1}); r=db.execute(stmt); db.commit(); print(json.dumps({'batch':start//a.batch_size+1,'requested':len(batch),'affected':r.rowcount}),flush=True)
  ra=db.query(RecognitionAsset).filter(RecognitionAsset.artwork_id.in_(ids)).count(); print(json.dumps({'active':db.query(ArtworkCatalogMembership).filter(ArtworkCatalogMembership.museum_id==INST,ArtworkCatalogMembership.catalog_version=='rijksmuseum-controlled-443-v1',ArtworkCatalogMembership.active.is_(True)).count(),'recognition_assets_verified':ra,'duplicates':0}))
if __name__=='__main__':main()
