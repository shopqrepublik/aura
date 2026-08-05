"""
Latency test harness for the hybrid recognition pipeline (Stage 1 open
recognition -> fuzzy match -> Stage 2 single visual verify against ONE
resized reference image), against spec §18's p50<2.5s / p95<5s budget.

Runs the two real test sets this project has used for every prior ad-hoc
latency check (never previously saved as a script, hence this file):
  - all 101 catalog works, using their own cached reference image
    (backend/.reference_cache/*.jpg, already resized to 512px) as the
    simulated visitor photo. Ground truth is the source artwork itself, so
    this set also doubles as a confident-wrong safety check: any case where
    the pipeline confidently returns a DIFFERENT catalog id than the true
    source is flagged.
  - the 13 real museum photos in test_photos/*.jpeg, resized 512px-wide
    client-side-equivalent before sending (matching the on-device step in
    spec §8.2) -- these have no recorded ground truth, so only
    latency/path is measured for this set, no accuracy verdict.

Measures, separately, the fast path (recognize_open + fuzzy_match only,
no vision call on the reference image) and the slow path (adds ONE
visual_verify_single_candidate call) -- via a monkeypatch around
visual_verify_single_candidate, not by touching recognize_with_vision
itself, so this file never risks changing production behavior.

Usage (from repo root):
    venv/Scripts/python.exe backend/scripts/latency_test.py
"""
import base64
import io
import json
import os
import statistics
import sys
import time

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.normpath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)  # so REFERENCE_CACHE_DIR's relative ".." resolves the same way main.py expects

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO_ROOT, ".env"))

from PIL import Image  # noqa: E402
from app import main as backend  # noqa: E402

REFERENCE_DIR = os.path.join(BACKEND_DIR, ".reference_cache")
TEST_PHOTOS_DIR = os.path.join(REPO_ROOT, "test_photos")

# ---- Monkeypatch: detect slow-path usage + isolate its own latency, without
# modifying recognize_with_vision's real code path. -------------------------
_orig_verify = backend.visual_verify_single_candidate
_last = {"slow_path": False, "verify_latency": None}


def _wrapped_verify(image_base64, candidate):
    _last["slow_path"] = True
    t0 = time.perf_counter()
    result = _orig_verify(image_base64, candidate)
    _last["verify_latency"] = time.perf_counter() - t0
    return result


backend.visual_verify_single_candidate = _wrapped_verify


def resize_like_device(raw_bytes: bytes, target_w: int = 512) -> str:
    """Mimics spec §8.2 step 2 (on-device resize before upload) for the real
    test_photos, which are un-resized ~1290x1720 camera-roll originals."""
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    w, h = img.size
    if w > target_w:
        new_h = round(h * (target_w / w))
        img = img.resize((target_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def run_one(image_b64: str, museum_id: str = "orsay") -> dict:
    _last["slow_path"] = False
    _last["verify_latency"] = None
    t0 = time.perf_counter()
    try:
        result = backend.recognize_with_vision(image_b64, museum_id, None)
        err = None
    except Exception as e:  # rate limits, transient API errors -- recorded, not fatal to the run
        result = None
        err = repr(e)
    total = time.perf_counter() - t0
    return {
        "total": total,
        "slow_path": _last["slow_path"],
        "verify_latency": _last["verify_latency"],
        "result": result,
        "error": err,
    }


def pctl(values, p):
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[p - 1]


def summarize(label, records):
    ok = [r for r in records if r["error"] is None]
    errors = len(records) - len(ok)
    times = [r["total"] for r in ok]
    fast = [r["total"] for r in ok if not r["slow_path"]]
    slow = [r["total"] for r in ok if r["slow_path"]]
    print(f"\n=== {label} (n={len(records)}, errors={errors}) ===")
    if times:
        print(f"  all  n={len(times):3d}  p50={pctl(times,50):.2f}s  p95={pctl(times,95):.2f}s  max={max(times):.2f}s")
    if fast:
        print(f"  fast n={len(fast):3d}  p50={pctl(fast,50):.2f}s  p95={pctl(fast,95):.2f}s  max={max(fast):.2f}s")
    else:
        print("  fast n=0")
    if slow:
        print(f"  slow n={len(slow):3d}  p50={pctl(slow,50):.2f}s  p95={pctl(slow,95):.2f}s  max={max(slow):.2f}s")
    else:
        print("  slow n=0")
    return {"all": times, "fast": fast, "slow": slow, "errors": errors}


def main():
    print("=== Set A: 101-catalog reference images (ground truth = source artwork) ===")
    by_id = {a["id"]: a for a in backend.DEMO_ARTWORKS}
    files = sorted(f for f in os.listdir(REFERENCE_DIR) if f.endswith(".jpg"))
    ref_records = []
    confident_wrong = []
    no_match = 0
    for i, fname in enumerate(files, 1):
        artwork_id = fname[:-4]
        path = os.path.join(REFERENCE_DIR, fname)
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        rec = run_one(b64)
        rec["source_id"] = artwork_id
        ref_records.append(rec)
        if rec["error"] is None:
            returned_id = rec["result"].get("artwork_id")
            if returned_id is None:
                no_match += 1
            elif returned_id != artwork_id:
                confident_wrong.append((artwork_id, returned_id))
        if rec["error"]:
            line = "ERROR " + rec["error"]
        else:
            path_label = "slow" if rec["slow_path"] else "fast"
            line = f'{rec["total"]:.2f}s {path_label}'
        print(f"  [{i}/{len(files)}] {artwork_id}: {line}")

    print("\n=== Set B: 13 real museum photos (no ground truth, latency/path only) ===")
    photo_files = sorted(f for f in os.listdir(TEST_PHOTOS_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    photo_records = []
    for i, fname in enumerate(photo_files, 1):
        path = os.path.join(TEST_PHOTOS_DIR, fname)
        with open(path, "rb") as f:
            raw = f.read()
        b64 = resize_like_device(raw)
        rec = run_one(b64)
        photo_records.append(rec)
        outcome = rec["result"].get("artwork_id") if (rec["result"] and not rec["error"]) else None
        if rec["error"]:
            line = "ERROR " + rec["error"]
        else:
            path_label = "slow" if rec["slow_path"] else "fast"
            outcome_label = f" -> {outcome}" if outcome else " -> no_match"
            line = f'{rec["total"]:.2f}s {path_label}{outcome_label}'
        print(f"  [{i}/{len(photo_files)}] {fname}: {line}")

    ref_stats = summarize("Set A: 101-catalog reference images", ref_records)
    photo_stats = summarize("Set B: 13 real photos", photo_records)

    combined_all = ref_stats["all"] + photo_stats["all"]
    combined_fast = ref_stats["fast"] + photo_stats["fast"]
    combined_slow = ref_stats["slow"] + photo_stats["slow"]
    summarize("Combined (A+B)", ref_records + photo_records)

    print(f"\n=== Confident-wrong (Set A only, ground truth known): {len(confident_wrong)} ===")
    for src, wrong in confident_wrong:
        print(f"  {src} -> confidently returned {wrong}")
    print(f"\nSet A no-match count: {no_match}/{len(files)}")

    out = {
        "set_a_101_reference": ref_stats,
        "set_b_13_photos": photo_stats,
        "confident_wrong": confident_wrong,
        "set_a_no_match": no_match,
    }
    with open(os.path.join(REPO_ROOT, "latency_test_results.json"), "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("\nRaw results written to latency_test_results.json")


if __name__ == "__main__":
    main()
