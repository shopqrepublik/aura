"""Small, repeatable orchestration wrapper for institution onboarding.

This intentionally delegates persistence and readiness to the existing generic
ingestion commands. It provides a uniform DISCOVER/DRY_RUN/PLAN/APPLY/STATUS
surface for the next museum without introducing a second catalog system.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=("DISCOVER","DRY_RUN","PLAN","APPLY","STATUS","PREPARE_RECOGNITION","BENCHMARK","ACTIVATE_CONTROLLED")); ap.add_argument("--config", required=True); ap.add_argument("--input"); ap.add_argument("--operator"); ap.add_argument("--adapter", default="normalized_json_v1"); ap.add_argument("--provider"); ap.add_argument("--institution")
    args = ap.parse_args(); cfg = json.loads(Path(args.config).read_text(encoding="utf-8")); inst = args.institution or cfg["institution_id"]; provider = args.provider or cfg["provider_id"]
    if args.mode in {"PREPARE_RECOGNITION","BENCHMARK","ACTIVATE_CONTROLLED"}:
        raise SystemExit(f"{args.mode} requires the existing institution-specific preparation/benchmark command; no second recognition pipeline is created")
    cmd=[sys.executable, str(ROOT/"backend/scripts/ingest_catalog.py"), args.mode, "--adapter", args.adapter, "--provider", provider, "--institution", inst]
    if args.input: cmd += ["--input", args.input]
    if args.operator: cmd += ["--operator", args.operator]
    return subprocess.call(cmd)
if __name__ == "__main__": raise SystemExit(main())
