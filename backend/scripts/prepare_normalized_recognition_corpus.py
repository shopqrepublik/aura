"""Prepare generic recognition fixtures from a normalized adapter snapshot."""
from __future__ import annotations
import argparse, hashlib, io, json, random
from pathlib import Path
from PIL import Image, ImageEnhance
from backend.app.ingestion import stable_id

def encode(im, width=1024):
    im=im.convert("RGB"); im.thumbnail((width,width*2),Image.Resampling.LANCZOS); b=io.BytesIO(); im.save(b,"JPEG",quality=90,optimize=True); return b.getvalue()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--snapshot",required=True); ap.add_argument("--selection",required=True); ap.add_argument("--audit",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    snap=json.loads(Path(a.snapshot).read_text(encoding="utf-8")); ids={str(x["provider_record_id"]) for x in json.loads(Path(a.selection).read_text(encoding="utf-8"))["records"]}; audit={str(x.get("provider_record_id")):x for x in json.loads(Path(a.audit).read_text(encoding="utf-8"))["records"]}; out=Path(a.out).resolve(); out.mkdir(parents=True,exist_ok=True); records=[]
    for row in snap["records"]:
        pid=str(row["provider_record_id"])
        if pid not in ids: continue
        source=Image.open(audit[pid]["path"]).convert("RGB"); aid=stable_id("artwork","rijksmuseum_amsterdam",pid); d=out/aid.replace(":","_"); d.mkdir(parents=True,exist_ok=True)
        visitor=ImageEnhance.Brightness(source).enhance(.88); files={}
        for name,im in (("reference",source),("pristine",source),("visitor_like",visitor),("partial",source.crop((0,0,max(1,int(source.width*.8)),max(1,int(source.height*.8)))))):
            data=encode(im); p=d/f"{name}.jpg"; p.write_bytes(data); files[name]={"path":p.relative_to(Path.cwd()).as_posix(),"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}
        records.append({"status":"READY","artwork_id":aid,"provider_record_id":pid,"title":row["title_original"],"artist":row.get("creator_display"),"date":row.get("date_display"),"source_url":row["source_url"],"source_media_id":row["media"][0].get("provider_asset_id"),"files":files})
    m={"schema_version":1,"records":sorted(records,key=lambda x:x["provider_record_id"]),"production_mutations":0}; (out/"manifest.json").write_text(json.dumps(m,indent=2)+"\n",encoding="utf-8"); print(json.dumps({"records":len(records),"ready":len(records)}))
if __name__=="__main__": main()
