import hashlib,importlib,json
from pathlib import Path
from urllib.request import urlopen
from dotenv import load_dotenv
from PIL import Image
from backend.app.visual_retrieval import descriptor_from_image,DESCRIPTOR_VERSION
from backend.app.ingestion import stable_id
from backend.app.models import RecognitionAsset
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'backend/data/onboarding/nordiska_museet_stockholm';INST='nordiska-museet-stockholm';PROVIDER='digitaltmuseum_s_nm'
def main():
 load_dotenv(ROOT/'.env');import backend.app.db as dbm;dbm=importlib.reload(dbm);s=json.loads((D/'nordiska-controlled-v1.json').read_text(encoding='utf-8'));cache=D/'reference_images';cache.mkdir(exist_ok=True);ds=[];ids=[]
 for row in s['records']:
  pid=str(row['provider_record_id']);ids.append(pid);p=cache/(pid+'.jpg')
  if not p.exists():p.write_bytes(urlopen(row['media'][0]['original_url'],timeout=15).read())
  with Image.open(p) as im: im.verify()
  with Image.open(p) as im: vals=descriptor_from_image(im);w,h=im.size
  sha=hashlib.sha256(p.read_bytes()).hexdigest();row['media'][0].update({'checksum_sha256':sha,'bytes':p.stat().st_size,'width':w,'height':h,'verification_state':'VERIFIED'});ds.append({'provider_record_id':pid,'version':DESCRIPTOR_VERSION,'source_sha256':sha,'values':vals})
 (D/'nordiska-controlled-v1.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8');(D/'visual_descriptors_v1.json').write_text(json.dumps({'schema_version':1,'descriptor_version':DESCRIPTOR_VERSION,'records':ds},separators=(',',':'))+'\n',encoding='utf-8')
 aids=[stable_id('artwork',PROVIDER,p) for p in ids]
 with dbm.SessionLocal() as db:
  for pid,aid in zip(ids,aids):
   url=next(r for r in s['records'] if str(r['provider_record_id'])==pid)['media'][0]['original_url'];r=db.query(RecognitionAsset).filter_by(artwork_id=aid,source_url=url).first() or RecognitionAsset(artwork_id=aid,source='nordiska_prepared',source_url=url);r.embedding_eligible=True;r.ai_tdm_eligible=True;r.local_storage_status='cached';r.visual_descriptor=next(x['values'] for x in ds if x['provider_record_id']==pid);db.add(r)
  db.commit();print(json.dumps({'recognition_assets':db.query(RecognitionAsset).filter(RecognitionAsset.artwork_id.in_(aids)).count(),'descriptors':len(ds),'version':DESCRIPTOR_VERSION}))
if __name__=='__main__':main()
