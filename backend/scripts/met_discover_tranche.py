"""Discover a deterministic Open Access Met painting tranche from the official API."""
from __future__ import annotations
import json, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"backend/data/onboarding/metropolitan_museum_new_york/met_tranche_snapshot_v1.json"
BASE="https://collectionapi.metmuseum.org/public/collection/v1"

def fetch(oid):
    req=urllib.request.Request(f"{BASE}/objects/{oid}",headers={"User-Agent":"ELYIO-MuseumFactory/2.0"})
    try:
        with urllib.request.urlopen(req,timeout=20) as r: x=json.load(r)
        if (x.get("objectName") or "").lower() != "painting": return None
        if not x.get("isPublicDomain") or not x.get("primaryImage"): return None
        if not x.get("title") or not x.get("artistDisplayName") or not x.get("objectDate"): return None
        return {"provider_record_id":str(x["objectID"]),"source_url":x.get("objectURL"),"source_language":"en","title_original":x["title"],"title_locale":"en","creator_display":x.get("artistDisplayName"),"date_display":x.get("objectDate"),"object_type":"Painting","institution_record_id":x.get("accessionNumber"),"department":x.get("department"),"description":"Open Access object from The Metropolitan Museum of Art.","media":[{"provider_asset_id":f"{x['objectID']}-primary","original_url":x["primaryImage"],"purpose":"REFERENCE","media_type":"IMAGE","rights_status":"VERIFIED_PUBLIC_DOMAIN","verification_state":"VERIFIED","presentation_eligible":True,"recognition_eligible":True,"association_role":"REFERENCE","primary":True}]}
    except Exception: return None

def main():
    params=urllib.parse.urlencode({"hasImages":"true","q":"painting"})
    req=urllib.request.Request(f"{BASE}/search?{params}",headers={"User-Agent":"Mozilla/5.0 ELYIO-MuseumFactory/2.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=60) as r: ids=json.load(r)["objectIDs"]
    ids=sorted(ids)[:5000]
    rows=[]
    # API ordering is captured only as an input; output is sorted by stable object ID.
    with ThreadPoolExecutor(max_workers=24) as pool:
        fs=[pool.submit(fetch,oid) for oid in ids]
        for i,f in enumerate(as_completed(fs),1):
            x=f.result()
            if x: rows.append(x)
            if i%1000==0: print(f"inspected {i}/{len(ids)} usable={len(rows)}",flush=True)
    rows=sorted(rows,key=lambda r:int(r["provider_record_id"]))[:500]
    payload={"snapshot":{"provider":"The Metropolitan Museum of Art","provider_id":"metropolitan_museum_open_access","endpoint":BASE,"selection":"official_open_access_paintings_sorted_object_id_first_500"},"records":rows}
    OUT.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"discovered":len(ids),"usable":len(rows),"output":str(OUT)},indent=2))
if __name__=="__main__": main()
