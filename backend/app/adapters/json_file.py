"""Deterministic normalized-JSON adapter used for approved snapshots and tests."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from ..source_adapter import AdapterMediaRecord, AdapterObjectRecord


def _dt(value: Any) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class JsonFileAdapter:
    adapter_key = "normalized_json_v1"

    def __init__(self, path: str | Path, provider_id: str, institution_id: str):
        self.path = Path(path)
        self.provider_id = provider_id
        self.institution_id = institution_id
        self._bytes = self.path.read_bytes()
        payload = json.loads(self._bytes)
        self._rows = payload["records"] if isinstance(payload, dict) else payload
        if not isinstance(self._rows, list):
            raise ValueError("normalized JSON must be an array or contain a records array")

    def source_snapshot(self) -> str:
        return "sha256:" + hashlib.sha256(self._bytes).hexdigest()

    def records(self) -> Iterable[AdapterObjectRecord]:
        for row in self._rows:
            media = tuple(AdapterMediaRecord(
                provider_asset_id=item.get("provider_asset_id"),
                original_url=item["original_url"], purpose=item["purpose"],
                media_type=item.get("media_type", "IMAGE"),
                rights_status=item.get("rights_status", "UNKNOWN"),
                verification_state=item.get("verification_state", "UNKNOWN"),
                license_code=item.get("license_code"), license_text=item.get("license_text"),
                attribution=item.get("attribution"),
                presentation_eligible=item.get("presentation_eligible"),
                recognition_eligible=item.get("recognition_eligible"),
                retrieved_at=_dt(item.get("retrieved_at")),
                checksum_sha256=item.get("checksum_sha256"),
                source_rights_metadata=item.get("source_rights_metadata") or {},
            ) for item in row.get("media", []))
            yield AdapterObjectRecord(
                provider_id=self.provider_id,
                provider_record_id=str(row["provider_record_id"]),
                institution_id=self.institution_id,
                source_url=row.get("source_url"), source_language=row.get("source_language"),
                title_original=row["title_original"], title_locale=row.get("title_locale"),
                creator_display=row.get("creator_display"), date_display=row.get("date_display"),
                object_type=row.get("object_type"), description=row.get("description"),
                institution_record_id=row.get("institution_record_id"),
                collection_source_id=row.get("collection_source_id"),
                department=row.get("department"), room=row.get("room"), gallery=row.get("gallery"),
                retrieved_at=_dt(row.get("retrieved_at")),
                provider_modified_at=_dt(row.get("provider_modified_at")),
                media=media, raw_payload=row,
            )
