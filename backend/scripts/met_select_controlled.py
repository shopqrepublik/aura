"""Create deterministic Met controlled selection from audited shortlist."""
import argparse,json
from pathlib import Path
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--snapshot',required=True); ap.add_argument('--audit',required=True); ap.add_argument('--out',required=True); a=ap.parse_args(); s=json.loads(Path(a.snapshot).read_text()); audit=json.loads(Path(a.audit).read_text()); good={str(x['provider_record_id']) for x in audit['records'] if x.get('quality') in {'STRONG','LOW_RESOLUTION_BUT_USABLE'}}; rows=[{'provider_record_id':str(r['provider_record_id'])} for r in s['records'] if str(r['provider_record_id']) in good]; rows=sorted(rows,key=lambda x:int(x['provider_record_id'])); out={'catalog_version':f'met-controlled-{len(rows)}-v1','summary':{'institution_id':'metropolitan-museum-new-york','target':len(rows),'selection_policy':'official Met Open Access CSV shortlist, stable object ID order'},'records':rows}; Path(a.out).write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out['summary']))
if __name__=='__main__':main()
