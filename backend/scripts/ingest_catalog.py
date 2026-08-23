"""Safe generic catalog ingestion runner. APPLY is never the default."""
from __future__ import annotations

import argparse
import json

from backend.app.adapters import ADAPTERS
from backend.app.db import SessionLocal
from backend.app.ingestion import apply_plan, build_plan, readiness_report, validate_record, validate_target
from backend.app.models import IngestionRun, SourceRecord


def main() -> int:
    parser = argparse.ArgumentParser(description="Provider-neutral ELYIO catalog ingestion")
    parser.add_argument("mode", choices=["DISCOVER", "DRY_RUN", "PLAN", "APPLY", "RECONCILE", "STATUS"])
    parser.add_argument("--adapter", default="normalized_json_v1", choices=sorted(ADAPTERS))
    parser.add_argument("--provider", required=True)
    parser.add_argument("--institution", required=True)
    parser.add_argument("--input", help="Provider snapshot; required except STATUS")
    parser.add_argument("--operator", help="Audited operator identity; required for APPLY")
    args = parser.parse_args()
    if args.mode != "STATUS" and not args.input:
        parser.error("--input is required for this mode")
    if args.mode == "APPLY" and not args.operator:
        parser.error("--operator is required for APPLY")

    db = SessionLocal()
    try:
        if args.mode == "STATUS":
            runs = db.query(IngestionRun).filter(IngestionRun.provider_id == args.provider, IngestionRun.institution_id == args.institution).order_by(IngestionRun.started_at.desc()).limit(10).all()
            result = {
                "source_records": db.query(SourceRecord).filter(SourceRecord.provider_id == args.provider, SourceRecord.institution_id == args.institution).count(),
                "recent_runs": [{"id": row.id, "status": row.status, "started_at": row.started_at.isoformat(), "summary": row.summary} for row in runs],
                "readiness": readiness_report(db, args.institution),
            }
        else:
            adapter = ADAPTERS[args.adapter](args.input, args.provider, args.institution)
            validate_target(db, adapter, args.institution)
            if args.mode == "DISCOVER":
                rows = tuple(adapter.records())
                result = {"source_snapshot": adapter.source_snapshot(), "records_inspected": len(rows), "invalid_records": sum(bool(validate_record(r, adapter, args.institution)) for r in rows)}
            else:
                plan = build_plan(db, adapter, args.institution, mode=args.mode, include_missing=args.mode == "RECONCILE")
                if args.mode == "APPLY":
                    result = {"ingestion_run_id": apply_plan(db, plan, operator_id=args.operator), "summary": plan.summary}
                else:
                    result = plan.public_dict()
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
