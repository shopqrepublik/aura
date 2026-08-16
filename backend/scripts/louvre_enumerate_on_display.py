# -*- coding: utf-8 -*-
"""Enumerates the exact set of ARK ids currently located anywhere in the
Louvre's physical Palais building, via the site's own advanced-search
"Current location" filter (internal location id 141082 = "Palais", the root
of the wing/room tree -- confirmed live via the site's own location picker:
Palais > {Cour carree, Denon, Flore, Hall Charles V, Napoleon, Richelieu,
Sully}).

This is NOT a fetch of individual records -- it reads only the search
RESULTS LIST pages (HTML text, `page=N` param, confirmed curl-safe and
returns different results per page -- unlike the free-text search's client-
side pagination from Phase 0, this route's pagination works over plain GET).
No image bytes are touched: this script fetches list-view HTML only, never
renders it, never follows <img> tags.

IMPORTANT CAVEAT: "located in Palais" is the Louvre's own grouping, used
here as a CANDIDATE list -- not a perfect proxy for our own is_on_display
classifier. Some Palais-located objects may still turn out NOT_ON_DISPLAY
per our own currentLocation-text classification (e.g. objects in a
workshop/reserve area physically inside the building). The authoritative
display_status for each record is still computed by louvre_import.py's own
classify_display_status() once the record's .json is actually fetched --
this script only produces the candidate id list to feed the importer.

Usage:
    venv/Scripts/python.exe backend/scripts/louvre_enumerate_on_display.py
Writes backend/data/louvre/checkpoints/on_display_candidates.json (ordered
list of ARK ids, in search-relevance order as returned by the site).
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "backend", "data", "louvre")
OUT_PATH = os.path.join(DATA_DIR, "checkpoints", "on_display_candidates.json")
PROGRESS_PATH = os.path.join(DATA_DIR, "checkpoints", "on_display_enum_progress.json")

UA = "AURA-MVP-backend/1.0 (contact: repo owner; research/museum-app project)"
BASE_URL = "https://collections.louvre.fr/en/recherche?advanced=1&location%5B0%5D=141082&lt=list&page={page}"
COURTESY_DELAY_S = 1.5
MAX_ATTEMPTS = 4
ARK_PATTERN = re.compile(r"ark:/53355/(cl\d+)")


def fetch_with_retry(url):
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise PermissionError(f"403 from {url} -- explicit access-control signal, stopping")
            last_err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = f"{type(e).__name__}: {e}"
        wait = 5 * attempt
        print(f"    retry {attempt}/{MAX_ATTEMPTS} after {last_err}, waiting {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"failed after {MAX_ATTEMPTS} attempts: {last_err}")


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"last_page_done": 0, "ark_ids": []}


def save_progress(progress):
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f)


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    progress = load_progress()
    seen = set(progress["ark_ids"])
    ordered = list(progress["ark_ids"])
    start_page = progress["last_page_done"] + 1

    page = start_page
    empty_streak = 0
    while True:
        url = BASE_URL.format(page=page)
        body = fetch_with_retry(url)
        ids_on_page = list(dict.fromkeys(ARK_PATTERN.findall(body)))
        if not ids_on_page:
            empty_streak += 1
            print(f"[page {page}] 0 results (empty streak {empty_streak})")
            if empty_streak >= 2:
                print("Two consecutive empty pages -- assuming end of results.")
                break
        else:
            empty_streak = 0
            new_ids = [i for i in ids_on_page if i not in seen]
            for i in new_ids:
                seen.add(i)
                ordered.append(i)
            print(f"[page {page}] {len(ids_on_page)} results, {len(new_ids)} new (total so far: {len(ordered)})")

        progress = {"last_page_done": page, "ark_ids": ordered}
        if page % 5 == 0:
            save_progress(progress)
        page += 1
        time.sleep(COURTESY_DELAY_S)

    save_progress(progress)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ordered, f)
    print(f"\nDone. {len(ordered)} unique ARK ids written to {OUT_PATH}")


if __name__ == "__main__":
    main()
