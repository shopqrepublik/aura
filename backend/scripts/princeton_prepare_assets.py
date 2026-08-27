"""Materialize Princeton references/descriptors and persist RecognitionAssets."""
import hashlib, importlib, json
from pathlib import Path
from urllib.request import urlopen
from dotenv import load_dotenv
from PIL import Image
from backend.app.visual_retrieval import descriptor_from_image, DESCRIPTOR_VERSION
from backend.app.ingestion import stable_id
from backend.app.models import Artwork, RecognitionAsset
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/'backend/data/onboarding/princeton_university_art_museum'; INST='princeton-art-museum-princeton'; PROVIDER='princeton_art_museum'
def main():
 load_dotenv(ROOT/'.env'); import backend.app.db as dbm; dbm=importlib.reload(dbm)
 snap=json.loads((D/'princeton-controlled-v1.json').read_text(encoding='utf-8')); cache=D/'reference_images'; cache.mkdir(exist_ok=True); desc=[]; manifest=[]
 for row in snap['records']:
  pid=str(row['provider_record_id']); path=cache/(pid+'.jpg');
  if not path.exists(): path.write_bytes(urlopen(row['media'][0]['original_url'],timeout=20).read())
  with Image.open(path) as im: im.verify()
  with Image.open(path) as im: vals=descriptor_from_image(im); w,h=im.size
  sha=hashlib.sha256(path.read_bytes()).hexdigest(); row['media'][0].update({'checksum_sha256':sha,'bytes':path.stat().st_size,'width':w,'height':h,'verification_state':'VERIFIED'})
  manifest.append({'status':'READY','provider_record_id':pid,'files':{'reference':{'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha,'bytes':path.stat().st_size}}}); desc.append({'provider_record_id':pid,'version':DESCRIPTOR_VERSION,'source_sha256':sha,'values':vals})
 (D/'princeton-controlled-v1.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8'); (D/'reference_manifest.json').write_text(json.dumps({'records':manifest},indent=2),encoding='utf-8'); (D/'visual_descriptors_v1.json').write_text(json.dumps({'schema_version':1,'descriptor_version':DESCRIPTOR_VERSION,'records':desc},separators=(',',':'))+'\n',encoding='utf-8')
 ids=[str(r['provider_record_id']) for r in snap['records']]; dv={str(x['provider_record_id']):x for x in desc}; aids=[stable_id('artwork',PROVIDER,p) for p in ids]
 with dbm.SessionLocal() as db:
  existing=db.query(RecognitionAsset).filter(RecognitionAsset.artwork_id.in_(aids)).all(); by={(x.artwork_id,x.source_url):x for x in existing}; created=0
  for pid,aid in zip(ids,aids):
   url=next(r for r in snap['records'] if str(r['provider_record_id'])==pid)['media'][0]['original_url']; rec=by.get((aid,url))
   if rec is None: rec=RecognitionAsset(artwork_id=aid,source='princeton_prepared',source_url=url); db.add(rec); created+=1
   rec.embedding_eligible=True; rec.ai_tdm_eligible=True; rec.local_storage_status='cached'; rec.visual_descriptor=dv[pid]['values']
  db.commit(); print(json.dumps({'references':len(ids),'descriptors':len(desc),'recognition_assets':db.query(RecognitionAsset).filter(RecognitionAsset.artwork_id.in_(aids)).count(),'created':created,'descriptor_version':DESCRIPTOR_VERSION}))
if __name__=='__main__': main()
