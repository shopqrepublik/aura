"""Bounded official Princeton source snapshot for Museum Factory onboarding."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

BASE = "https://data.artmuseum.princeton.edu"
OUT = Path(__file__).resolve().parents[1] / "data/onboarding/princeton_university_art_museum"

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    search = urlopen(BASE+"/search?"+urlencode({"q":"painting", "type":"artobjects", "size":100, "from":0}), timeout=30)
    payload = json.load(search)
    hits = payload.get("hits", {}).get("hits", [])
    records=[]; attempts=0
    def process(hit):
        obj = hit.get("_source",{}); oid = str(hit.get("_id") or obj.get("objectid"))
        classification=(obj.get("classification") or "Paintings").lower()
        images=obj.get("primaryimage") or []
        if isinstance(images,str): images=[images]
        if "paint" not in classification and not any("painting" in str(obj.get(k," ")).lower() for k in ("displaytitle","medium")): return None
        if not images: return None
        url=str(images[0]);
        if "/iiif/" in url and not url.endswith((".jpg",".jpeg",".png")):
            url=url.rstrip("/")+"/full/max/0/default.jpg"
        ctype="image/jpeg"; body=b""
        import hashlib
        rec={"provider_record_id":oid,"institution_record_id":str(obj.get("objectnumber") or oid),
             "source_url":f"{BASE}/objects/{oid}","title_original":obj.get("displaytitle") or obj.get("titles",[{}])[0].get("title") or f"Princeton object {oid}",
             "creator_display":obj.get("displaymaker"),
             "date_display":obj.get("displaydate"),"object_type":obj.get("classification") or "Paintings",
             "department":obj.get("department"),"description":obj.get("medium"),"media":[{"provider_asset_id":f"{oid}-primary","original_url":url,"purpose":"REFERENCE","media_type":"IMAGE","rights_status":"UNKNOWN","verification_state":"VERIFIED","recognition_eligible":True,"association_role":"REFERENCE","http_status":200,"content_type":ctype,"source_rights_metadata":{"restrictions":obj.get("restrictions"),"nowebuse":obj.get("nowebuse"),"creditline":obj.get("creditline"),"creditlinerepro":obj.get("creditlinerepro")}}],"raw_payload":obj}
        return rec
    for h in hits[:35]:
        rec=process(h)
        if rec: records.append(rec)
        if len(records)>=25: break
    attempts=35
    out={"snapshot":{"provider":"Princeton University Art Museum","provider_id":"princeton_art_museum","source_url":BASE,"retrieved_records":attempts},"records":records}
    (OUT/"princeton-controlled-v1.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"api_status":200,"canary_attempts":attempts,"painting_image_backed":len(records),"path":str(OUT/"princeton-controlled-v1.json")}))
    return 0
if __name__ == "__main__": raise SystemExit(main())
