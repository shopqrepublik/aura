"""Acquire and audit the prepared Rijksmuseum reference tranche."""
from __future__ import annotations
import argparse, hashlib, json, mimetypes, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--snapshot",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    payload=json.loads(Path(a.snapshot).read_text(encoding="utf-8")); root=Path(a.out); root.mkdir(parents=True,exist_ok=True)
    def one(row):
        media=row["media"][0]; dest=root/f"{row['provider_record_id']}.jpg"
        if not dest.exists():
            # Request a bounded IIIF derivative: sufficient for recognition,
            # reproducible, and avoids multi-megabyte full-resolution tails.
            image_url = media["original_url"].replace("/full/max/", "/full/1200,/")
            req=urllib.request.Request(image_url,headers={"User-Agent":"ELYIO-MuseumFactory/1.0"})
            with urllib.request.urlopen(req,timeout=120) as response: dest.write_bytes(response.read())
        data=dest.read_bytes(); status="UNAVAILABLE"; width=height=0
        try:
            with Image.open(dest) as im:
                im.verify()
            with Image.open(dest) as im: width,height=im.size
            status="STRONG" if min(width,height)>=600 else "LOW_RESOLUTION_BUT_USABLE" if min(width,height)>=300 else "UNSUITABLE"
        except Exception: status="UNSUITABLE"
        return {"provider_record_id":row["provider_record_id"],"source_url":media["original_url"],"path":str(dest),"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),"width":width,"height":height,"quality":status}
    out=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures=[pool.submit(one,row) for row in payload["records"]]
        for i,f in enumerate(as_completed(futures),1):
            try: out.append(f.result())
            except Exception as exc: out.append({"quality":"UNAVAILABLE","error":f"{type(exc).__name__}: {exc}"})
            if i%25==0: print(f"audited {i}/{len(futures)}",flush=True)
    out.sort(key=lambda x:x.get("provider_record_id", "")); Path(a.out).with_name("reference_audit_v1.json").write_text(json.dumps({"records":out,"summary":{"audited":len(out),"strong":sum(x.get("quality")=="STRONG" for x in out),"low_resolution_usable":sum(x.get("quality")=="LOW_RESOLUTION_BUT_USABLE" for x in out),"unsuitable":sum(x.get("quality")=="UNSUITABLE" for x in out),"unavailable":sum(x.get("quality")=="UNAVAILABLE" for x in out)}},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"audited":len(out),"strong":sum(x.get("quality")=="STRONG" for x in out),"usable":sum(x.get("quality") in {"STRONG","LOW_RESOLUTION_BUT_USABLE"} for x in out)},indent=2))
if __name__ == "__main__": main()
