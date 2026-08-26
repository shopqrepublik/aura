"""Small non-mutating Met controlled-preview recognition smoke."""
import argparse,base64,json,os,time,statistics
from pathlib import Path
from dotenv import load_dotenv
from backend.app.adapters.json_file import JsonFileAdapter
from backend.app.catalog import InstitutionRuntimeConfig
from backend.app.ingestion import stable_id
from backend.app.main import recognize_with_vision
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/'backend/data/onboarding/metropolitan_museum_new_york'; INST='metropolitan-museum-new-york'; PROVIDER='metropolitan_museum_open_access'
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=20); a=ap.parse_args(); load_dotenv(ROOT/'.env'); snap=json.loads((D/'met_tranche_snapshot_v1.json').read_text()); man=json.loads((D/'corpus_100_v1/manifest.json').read_text()); rows={str(r['provider_record_id']):r for r in snap['records']}; ready=[r for r in man['records'] if r['status']=='READY'][:a.limit]; candidates=[]
 for pid,row in rows.items():
  candidates.append({'id':stable_id('artwork',PROVIDER,pid),'museum_id':INST,'artist':row.get('creator_display'),'title':row['title_original'],'year':row.get('date_display'),'inventory_number':row.get('institution_record_id'),'department':row.get('department'),'hall':None,'object_type':'Painting','description':row.get('description'),'source_record_id':pid,'image_url':row['media'][0]['original_url'],'recognition_asset_id':'benchmark:'+row['media'][0]['provider_asset_id'],'priority':50,'tags':[],'source_urls':[row.get('source_url')],'visual_descriptor':None})
 cfg=InstitutionRuntimeConfig(institution_id=INST,display_name='The Metropolitan Museum of Art',visitor_catalog_version='met-controlled-100-v1',candidate_universe='ACTIVE_CATALOG',recognition_policy='ASSET_VERIFY',supported_modes=('normal',),max_candidates=5,confidence_auto=.92,confidence_review=.82,fuzzy_candidate_threshold=.55,prompt_context='The Metropolitan Museum of Art, New York. Resolve only against supplied institution-scoped candidates.',allow_recognition_asset_substitution=True)
 out=[]
 for i,r in enumerate(ready,1):
  b=(ROOT/r['files']['visitor_like']['path']).read_bytes(); t=time.perf_counter(); result=recognize_with_vision(base64.b64encode(b).decode(),INST,None,candidates,institution_config=cfg); out.append({'provider_record_id':r['provider_record_id'],'expected':stable_id('artwork',PROVIDER,r['provider_record_id']),'selected':result.get('artwork_id'),'confidence':result.get('confidence',0),'elapsed_s':time.perf_counter()-t,'outcome':result.get('resolution') or result.get('status')}); print(f'{i}/{len(ready)} {out[-1]["outcome"]}',flush=True)
 print(json.dumps({'cases':len(out),'top1':sum(x['selected']==x['expected'] for x in out),'fallback':sum(x['selected'] is None for x in out),'incorrect':sum(x['selected'] not in (None,x['expected']) for x in out),'p50':statistics.median([x['elapsed_s'] for x in out]) if out else None,'p95':sorted(x['elapsed_s'] for x in out)[max(0,round(.95*(len(out)-1)))] if out else None},indent=2))
if __name__=='__main__':main()
