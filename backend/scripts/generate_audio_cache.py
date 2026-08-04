"""
One-time generation of Top-20 audio narration (Normal mode, en/fr/zh-Hans).

Reads audioScript from web/lib/data/artworks.json, calls OpenAI TTS once per
(work, locale), writes the resulting mp3 to web/public/audio/ as a static
asset, and writes the resulting relative URL back into audioUrl in the same
JSON file. Deliberately NOT a runtime/on-demand endpoint -- §10.4 requires
cached audio, never synthesized on playback. Safe to re-run: skips any file
that already exists on disk (idempotent, so a partial run can be resumed
without re-paying for already-generated files).
"""
import json
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

VOICE = "nova"
MODEL = "tts-1-hd"

JSON_PATH = ROOT / "web" / "lib" / "data" / "artworks.json"
AUDIO_DIR = ROOT / "web" / "public" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

LOCALES = ["en", "fr", "zh-Hans"]

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

works = [a for a in data if a.get("priority") == "top20" and "audioScript" in a]
print(f"{len(works)} top20 works with audioScript found")

generated = 0
skipped = 0
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
        resp = client.audio.speech.create(model=MODEL, voice=VOICE, input=text)
        resp.write_to_file(out_path)
        size_kb = out_path.stat().st_size / 1024
        print(f"  {filename}: {size_kb:.0f} KB")
        art["audioUrl"][locale] = url
        generated += 1

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"\nDone. Generated {generated} new files, skipped {skipped} already-cached files.")
print(f"Audio files in: {AUDIO_DIR}")
