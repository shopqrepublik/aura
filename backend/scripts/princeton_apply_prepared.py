"""Apply the frozen Princeton package through the proven bounded Factory path."""
import argparse, json, importlib
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from backend.app.adapters.json_file import JsonFileAdapter
from backend.app.ingestion import apply_plan, build_plan
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser(); p.add_argument('--operator',required=True); p.add_argument('--batch-size',type=int,default=5); a=p.parse_args(); load_dotenv(ROOT/'.env'); import backend.app.db as dbm; dbm=importlib.reload(dbm)
 d=ROOT/'backend/data/onboarding/princeton_university_art_museum'; cfg=json.loads((d/'princeton-controlled-v1.json').read_text(encoding='utf-8')); rows=cfg['records']; inst='princeton-art-museum-princeton'; provider='princeton_art_museum'
 with dbm.SessionLocal() as db:
  db.execute(text("SET statement_timeout='120s'"))
  for start in range(0,len(rows),a.batch_size):
   part=d/'_princeton_batch.json'; part.write_text(json.dumps({'records':rows[start:start+a.batch_size]}))
   plan=build_plan(db,JsonFileAdapter(part,provider,inst),inst,mode='PLAN'); apply_plan(db,plan,operator_id=a.operator)
   print(json.dumps({'batch':start//a.batch_size+1,'batches':(len(rows)+a.batch_size-1)//a.batch_size,'summary':plan.summary}),flush=True)
if __name__=='__main__': main()
