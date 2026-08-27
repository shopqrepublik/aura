"""Minimal non-mutating Rijksmuseum recognition smoke."""
import argparse,base64,json,statistics,time
from pathlib import Path
from dotenv import load_dotenv
from backend.app.catalog import InstitutionRuntimeConfig
from backend.app.ingestion import stable_id
from backend.app.main import recognize_with_vision
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/'backend/data/onboarding/rijksmuseum_amsterdam'; INST='rijksmuseum-amsterdam'; PROVIDER='rijksmuseum_amsterdam'
def run(paths,expected):
 snap=json.loads((D/'source_snapshot_v1.json').read_text(encoding='utf-8')); rows={str(r['provider_record_id']):r for r in snap['records']}; desc=json.loads((D/'controlled_catalog_443_visual_descriptors_v1.json').read_text(encoding='utf-8')); dv={str(x['provider_record_id']):x for x in desc['records']}; candidates=[]
 for pid,row in rows.items(): candidates.append({'id':stable_id('artwork',PROVIDER,pid),'museum_id':INST,'artist':row.get('creator_display'),'title':row['title_original'],'year':row.get('date_display'),'inventory_number':row.get('institution_record_id'),'department':row.get('department'),'object_type':row.get('object_type'),'description':row.get('description'),'source_record_id':pid,'image_url':row['media'][0]['original_url'],'recognition_asset_id':'prepared:'+row['media'][0].get('provider_asset_id',''),'priority':50,'tags':[],'source_urls':[row.get('source_url')],'visual_descriptor':dv.get(pid)})
 cfg=InstitutionRuntimeConfig(institution_id=INST,display_name='Rijksmuseum',visitor_catalog_version='rijksmuseum-controlled-443-v1',candidate_universe='ACTIVE_CATALOG',recognition_policy='ASSET_VERIFY',supported_modes=('normal',),max_candidates=5,confidence_auto=.92,confidence_review=.82,fuzzy_candidate_threshold=.55,prompt_context='Rijksmuseum Amsterdam. Resolve only against supplied institution-scoped candidates.',allow_recognition_asset_substitution=True); out=[]
 for i,(path,exp) in enumerate(zip(paths,expected),1):
  b=Path(path).read_bytes(); t=time.perf_counter(); z=recognize_with_vision(base64.b64encode(b).decode(),INST,None,candidates,institution_config=cfg); out.append((z.get('artwork_id'),exp,time.perf_counter()-t)); print(f'{i}/{len(paths)}',flush=True)
 return out
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=10); ap.add_argument('--external-manifest'); a=ap.parse_args(); load_dotenv(ROOT/'.env'); man=json.loads((D/'../rijksmuseum_amsterdam/corpus/manifest.json').read_text()) if False else json.loads((ROOT/'exports/rijksmuseum_amsterdam/corpus/manifest.json').read_text()); rows=man['records'][:a.limit]; paths=[ROOT/r['files']['visitor_like']['path'] for r in rows]; exp=[stable_id('artwork',PROVIDER,str(r['provider_record_id'])) for r in rows]
 if a.external_manifest:
  em=json.loads(Path(a.external_manifest).read_text())['records'][:a.limit]; paths=[ROOT/r['files']['visitor_like']['path'] for r in em]; exp=[None]*len(paths)
 out=run(paths,exp); ts=[x[2] for x in out]; print(json.dumps({'cases':len(out),'top1':sum(a==b and b is not None for a,b,_ in out),'fallback':sum(a is None for a,b,_ in out),'incorrect':sum(a is not None and b is not None and a!=b for a,b,_ in out),'false_confident':sum(a is not None and b is None for a,b,_ in out),'p50':statistics.median(ts),'p95':sorted(ts)[max(0,round(.95*(len(ts)-1)))]},indent=2))
if __name__=='__main__':main()
