"""
One-off voice comparison for the ELYIO audio-narration feature.
Generates short samples (one real script excerpt per language) across a
few candidate tts-1 voices, so a human can listen and pick the brand voice
before the full 60-file generation runs. Not part of the app; run once,
throw away.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

OUT_DIR = Path(__file__).resolve().parents[2] / "voice_samples"
OUT_DIR.mkdir(exist_ok=True)

VOICES = ["onyx", "nova", "shimmer", "fable"]

SAMPLES = {
    "en": "This woman is lying in the classic pose of a reclining goddess, except she isn't looking away demurely. She's staring straight back at you, calm and completely unbothered.",
    "fr": "Trois personnes partagent ce petit balcon, et pourtant aucune d'elles ne regarde les autres, ni vous. Cette absence de contact n'a rien d'accidentel.",
    "zh-Hans": "留意阳光并不是均匀洒落的——它被头顶的树叶打散成斑驳的光斑，洒落在人群之中。真正把整幅画凝聚在一起的，正是这些破碎的光斑。",
}

for voice in VOICES:
    for locale, text in SAMPLES.items():
        out_path = OUT_DIR / f"{voice}_{locale}.mp3"
        resp = client.audio.speech.create(model="tts-1", voice=voice, input=text)
        resp.write_to_file(out_path)
        print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")

print("Done.")
