import argparse,json,importlib
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from backend.app.adapters.json_file import JsonFileAdapter
from backend.app.ingestion import build_plan,apply_plan
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--operator',required=True);p.add_argument('--batch-size',type=int,default=5);a=p.parse_args();load_dotenv(ROOT/'.env');import backend.app.db as dbm;dbm=importlib.reload(dbm);d=ROOT/'backend/data/onboarding/nordiska_museet_stockholm';rows=json.loads((d/'nordiska-controlled-v1.json').read_text(encoding='utf-8'))['records']
 with dbm.SessionLocal() as db:
  db.execute(text("SET statement_timeout='120s'"))
  for s in range(0,len(rows),a.batch_size):
   part=d/'_batch.json';part.write_text(json.dumps({'records':rows[s:s+a.batch_size]}));plan=build_plan(db,JsonFileAdapter(part,'digitaltmuseum_s_nm','nordiska-museet-stockholm'),'nordiska-museet-stockholm',mode='PLAN');apply_plan(db,plan,operator_id=a.operator);print(json.dumps({'batch':s//a.batch_size+1,'summary':plan.summary}),flush=True)
if __name__=='__main__':main()
