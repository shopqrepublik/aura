"""Bounded official DigitaltMuseum S-NM painting snapshot."""
import json, hashlib
from pathlib import Path
from urllib.request import urlopen
BASE='https://api.dimu.org/api/solr/select'; OUT=Path(__file__).resolve().parents[1]/'data/onboarding/nordiska_museet_stockholm'
def main():
 OUT.mkdir(parents=True,exist_ok=True); rows=[]
 for start in (0,10,20):
  url=BASE+'?q=*:*&fq=identifier.owner:S-NM&fq=artifact.hasPictures:true&fq=artifact.ingress.names:M%C3%A5lning&wt=json&rows=10&start='+str(start)+'&api.key=demo'
  data=json.load(urlopen(url,timeout=20)); rows.extend(data.get('response',{}).get('docs',[]))
  if len(rows)>=25: break
 out=[]
 for d in rows[:25]:
  oid=str(d.get('artifact.uniqueId') or d.get('identifier.id')); mid=d.get('artifact.defaultMediaIdentifier')
  if not mid: continue
  img=f'https://ems.dimu.org/image/{mid}?dimension=1200x1200'
  try:
   r=urlopen(img,timeout=15); c=r.headers.get('content-type','').split(';')[0]; body=r.read()
   if not c.startswith('image/'): continue
  except Exception: continue
  out.append({'provider_record_id':oid,'institution_record_id':d.get('identifier.id'),'source_url':f'https://digitaltmuseum.org/{d.get("identifier.id")}', 'title_original':d.get('artifact.ingress.title') or 'Målning','creator_display':d.get('artifact.ingress.producer'),'date_display':str(d.get('artifact.ingress.production.fromYear') or ''),'object_type':'Fineart','department':'Nordiska museet','description':None,'media':[{'provider_asset_id':mid,'original_url':img,'purpose':'REFERENCE','media_type':'IMAGE','rights_status':'UNKNOWN','verification_state':'VERIFIED','recognition_eligible':True,'association_role':'REFERENCE','http_status':200,'content_type':c,'checksum_sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'source_rights_metadata':{'owner':'S-NM','license':d.get('artifact.ingress.license')}}],'raw_payload':d})
 payload={'snapshot':{'provider':'DigitaltMuseum / KulturIT','provider_id':'digitaltmuseum_s_nm','owner':'S-NM','source_url':'https://api.dimu.org'},'records':out}
 (OUT/'nordiska-controlled-v1.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({'query_total':107,'painting_image_backed':len(out),'path':str(OUT/'nordiska-controlled-v1.json')}))
if __name__=='__main__': main()
