"""CSV-first, resumable official Met shortlist/detail acquisition."""
from __future__ import annotations
import argparse,csv,json,os,time,urllib.request
from pathlib import Path

BASE='https://collectionapi.metmuseum.org/public/collection/v1/objects/'
ROOT=Path(__file__).resolve().parents[2]
def norm(x):
    return {"provider_record_id":str(x['Object ID']),"source_url":x.get('Link Resource') or f"https://www.metmuseum.org/art/collection/search/{x['Object ID']}","source_language":"en","title_original":x['Title'].strip(),"title_locale":"en","creator_display":x.get('Artist Display Name','').strip() or None,"date_display":x.get('Object Date','').strip() or None,"object_type":"Painting","institution_record_id":x.get('\ufeffObject Number') or x.get('Object Number'),"department":x.get('Department'),"description":"Open Access object from The Metropolitan Museum of Art.","media":[]}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--csv',required=True); ap.add_argument('--target',type=int,default=800); ap.add_argument('--min-usable',type=int,default=100); ap.add_argument('--cache',default=str(ROOT/'backend/data/onboarding/metropolitan_museum_new_york/met_detail_cache_v1.json')); a=ap.parse_args(); cache=Path(a.cache); cache.parent.mkdir(parents=True,exist_ok=True)
 rows=[]
 with open(a.csv,encoding='utf-8-sig',newline='') as f:
  for x in csv.DictReader(f):
   obj=(x.get('Object Name') or '').lower(); cls=(x.get('Classification') or '').lower();
   if ('painting' not in obj and 'painting' not in cls) or x.get('Is Public Domain')!='True': continue
   if not all((x.get(k) or '').strip() for k in ['Object ID','Title','Artist Display Name','Object Date']): continue
   rows.append(x)
 rows=sorted(rows,key=lambda x:int(x['Object ID']))[:a.target]
 data=json.loads(cache.read_text()) if cache.exists() else {}
 for i,x in enumerate(rows,1):
  oid=str(x['Object ID'])
  if oid in data: continue
  for attempt in range(3):
   try:
    req=urllib.request.Request(BASE+oid,headers={'User-Agent':'ELYIO-MuseumFactory/2.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r: d=json.load(r)
    if d.get('isPublicDomain') and d.get('primaryImage') and (d.get('objectName') or '').lower()=='painting':
     row=norm(x); row['media']=[{"provider_asset_id":f"{oid}-primary","original_url":d['primaryImage'],"purpose":"REFERENCE","media_type":"IMAGE","rights_status":"VERIFIED_PUBLIC_DOMAIN","verification_state":"VERIFIED","presentation_eligible":True,"recognition_eligible":True,"association_role":"REFERENCE","primary":True}]; data[oid]=row
    break
   except Exception:
    if attempt<2: time.sleep(2**attempt)
  if i%25==0: cache.write_text(json.dumps(data,indent=2)+'\n'); print(f'processed {i}/{len(rows)} usable={len(data)}',flush=True)
  if len(data)>=a.min_usable: break
 cache.write_text(json.dumps(data,indent=2)+'\n')
 out=ROOT/'backend/data/onboarding/metropolitan_museum_new_york/met_tranche_snapshot_v1.json'; selected=[data[k] for k in sorted(data,key=lambda z:int(z))]; out.write_text(json.dumps({'snapshot':{'provider':'The Metropolitan Museum of Art','provider_id':'metropolitan_museum_open_access','selection':f'official CSV shortlist {a.target}, sorted object ID'},'records':selected},indent=2)+'\n')
 print(json.dumps({'csv_candidates':sum(1 for _ in rows),'shortlist':len(rows),'usable_details':len(selected),'output':str(out)},indent=2))
if __name__=='__main__': main()
