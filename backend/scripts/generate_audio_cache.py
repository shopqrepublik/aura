"""
Generation of audio narration (Normal mode, en/fr/zh-Hans) for every catalog
work that has an audioScript -- originally Top-20 only (Phase 1), now all
101 works (Phase 3 §1: the remaining 81 got their own audioScript, written
non-verbatim from the Normal-mode why/where/rarity text, same "calm,
knowledgeable friend" tone and 30-60s target length as the original 20).

Reads audioScript from web/lib/data/artworks.json, calls OpenAI TTS once per
(work, locale), writes the resulting mp3 to web/public/audio/ as a static
asset, measures its real duration with mutagen (not estimated), and writes
the resulting relative URL back into audioUrl in the same JSON file.
Deliberately NOT a runtime/on-demand endpoint -- §10.4 requires cached
audio, never synthesized on playback. Safe to re-run: skips any file that
already exists on disk (idempotent, so a partial run can be resumed without
re-paying for already-generated files, and re-running after this file's
filter changed never re-generates or overwrites the original 60 Top-20
files -- their audioUrl is already set, this script only fills in what's
missing).
"""
import json
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

import os
import openai
from openai import OpenAI
from mutagen.mp3 import MP3

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

VOICE = "nova"
MODEL = "tts-1-hd"

JSON_PATH = ROOT / "web" / "lib" / "data" / "artworks.json"
AUDIO_DIR = ROOT / "web" / "public" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

LOCALES = ["en", "fr", "zh-Hans"]


def _save_json(data):
    """Written after EVERY file, not once at the end -- a run interrupted by
    a network error (observed live: repeated transient DNS/TLS timeouts)
    used to lose every audioUrl written during that run, even though the
    mp3s themselves were already safely on disk, because the old version
    only serialized once after the full loop finished."""
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _create_speech_with_retry(text, max_attempts=5):
    """This machine saw repeated transient DNS/TLS failures generating the
    81-work batch (APIConnectionError, APITimeoutError) -- none were an
    actual OpenAI-side error, all resolved on a bare retry. Same backoff
    shape as backend/app/main.py's _urlopen_with_retry for Wikimedia."""
    for attempt in range(1, max_attempts + 1):
        try:
            return client.audio.speech.create(model=MODEL, voice=VOICE, input=text)
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            if attempt == max_attempts:
                raise
            wait = 2 ** attempt
            print(f"    [retry] {type(e).__name__}, retrying in {wait}s (attempt {attempt}/{max_attempts})")
            time.sleep(wait)


with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

# Any work with an audioScript, not just priority=="top20" -- generalized
# for Phase 3 §1. Whether a work NEEDS audio at all (still Top-20-only
# for now) is decided by which works have audioScript authored, not by
# a priority check baked into this script.
works = [a for a in data if "audioScript" in a]
print(f"{len(works)} works with audioScript found")

generated = 0
skipped = 0
out_of_range = []
for art in works:
    art.setdefault("audioUrl", {})
    for locale in LOCALES:
        text = art["audioScript"][locale]
        filename = f"{art['id']}_{locale}.mp3"
        out_path = AUDIO_DIR / filename
        url = f"/audio/{filename}"
        if out_path.exists():
            skipped += 1
            art["audioUrl"][locale] = url
            continue
        resp = _create_speech_with_retry(text)
        resp.write_to_file(out_path)
        duration = MP3(out_path).info.length
        if not (30 <= duration <= 60):
            out_of_range.append((filename, duration))
        size_kb = out_path.stat().st_size / 1024
        print(f"  {filename}: {size_kb:.0f} KB, {duration:.1f}s" + (" -- OUT OF RANGE" if not (30 <= duration <= 60) else ""))
        art["audioUrl"][locale] = url
        generated += 1
        _save_json(data)

# Also covers the case where every remaining file this run was already on
# disk (skipped) -- those still backfill audioUrl in memory above, but
# without this, that backfill would only reach disk if at least one NEW
# file was also generated in the same run to trigger the per-file save.
_save_json(data)

print(f"\nDone. Generated {generated} new files, skipped {skipped} already-cached files.")
print(f"Audio files in: {AUDIO_DIR}")
if out_of_range:
    print(f"\n{len(out_of_range)} file(s) OUTSIDE the 30-60s range:")
    for fname, dur in out_of_range:
        print(f"  {fname}: {dur:.1f}s")
else:
    print("\nAll newly-generated files measured within the 30-60s range.")
