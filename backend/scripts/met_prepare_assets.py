"""Acquire and audit official Met primary-image references for the shortlist."""
from __future__ import annotations
import argparse,hashlib,json,urllib.request
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from PIL import Image
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--snapshot',required=True); ap.add_argument('--out',required=True); a=ap.parse_args(); p=json.loads(Path(a.snapshot).read_text()); root=Path(a.out); root.mkdir(parents=True,exist_ok=True)
 def one(row):
  dest=root/f"{row['provider_record_id']}.jpg"
  if not dest.exists():
   req=urllib.request.Request(row['media'][0]['original_url'],headers={'User-Agent':'ELYIO-MuseumFactory/2.0'})
   with urllib.request.urlopen(req,timeout=60) as r: dest.write_bytes(r.read())
  b=dest.read_bytes(); w=h=0; q='UNAVAILABLE'
  try:
   with Image.open(dest) as im: im.verify()
   with Image.open(dest) as im:w,h=im.size
   q='STRONG' if min(w,h)>=600 else 'LOW_RESOLUTION_BUT_USABLE' if min(w,h)>=300 else 'UNSUITABLE'
  except Exception:q='UNSUITABLE'
  return {'provider_record_id':row['provider_record_id'],'source_url':row['media'][0]['original_url'],'path':str(dest),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'width':w,'height':h,'quality':q}
 out=[]
 with ThreadPoolExecutor(max_workers=8) as pool:
  fs=[pool.submit(one,r) for r in p['records']]
  for i,f in enumerate(as_completed(fs),1):
   try:out.append(f.result())
   except Exception as e:out.append({'provider_record_id':'unknown','quality':'UNAVAILABLE','error':type(e).__name__})
 out.sort(key=lambda x:x.get('provider_record_id','')); audit={'records':out,'summary':{'audited':len(out),'strong':sum(x.get('quality')=='STRONG' for x in out),'low_resolution_usable':sum(x.get('quality')=='LOW_RESOLUTION_BUT_USABLE' for x in out),'unsuitable':sum(x.get('quality')=='UNSUITABLE' for x in out),'unavailable':sum(x.get('quality')=='UNAVAILABLE' for x in out)}}; Path(a.out).with_name('reference_audit_v1.json').write_text(json.dumps(audit,indent=2)+'\n'); print(json.dumps(audit['summary']))
if __name__=='__main__':main()
