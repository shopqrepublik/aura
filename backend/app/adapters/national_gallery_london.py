"""National Gallery London CIIM/Elasticsearch snapshot adapter.

Official-source mechanics stay here; ELYIO reconciliation remains generic.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..source_adapter import AdapterMediaRecord, AdapterObjectRecord


def _first(rows: Any, key: str, value: str | None = None) -> Any:
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and (value is None or str(row.get(key, "")).lower() == value.lower()):
            return row
    return None


def _identifier(source: dict, kind: str) -> str | None:
    row = _first(source.get("identifier"), "type", kind)
    return str(row.get("value")) if row and row.get("value") else None


def _creator(source: dict) -> str | None:
    creation = source.get("creation") or []
    creation = creation[0] if isinstance(creation, list) and creation else {}
    attribution = _first(creation.get("attribution"), "type", "attribution")
    if attribution and attribution.get("value"):
        return str(attribution["value"])
    maker = creation.get("maker") or []
    maker = maker[0] if isinstance(maker, list) and maker else {}
    return (maker.get("summary") or {}).get("title")


def _date(source: dict) -> str | None:
    creation = source.get("creation") or []
    creation = creation[0] if isinstance(creation, list) and creation else {}
    dates = creation.get("date") or []
    row = dates[0] if isinstance(dates, list) and dates else {}
    return row.get("value") or row.get("from")


def _typed_value(rows: Any, kind: str) -> str | None:
    row = _first(rows, "type", kind)
    return str(row.get("value")) if row and row.get("value") else None


class NationalGalleryLondonAdapter:
    adapter_key = "national_gallery_ciim_v1"
    provider_id = "national_gallery_london"

    def __init__(self, path: str | Path, provider_id: str = "national_gallery_london", institution_id: str = "national-gallery-london", provider_record_ids: set[str] | None = None):
        if provider_id != self.provider_id:
            raise ValueError("National Gallery adapter requires provider national_gallery_london")
        self.path = Path(path)
        self.institution_id = institution_id
        self._bytes = self.path.read_bytes()
        self.snapshot = json.loads(self._bytes)
        self.provider_record_ids = provider_record_ids
        self._hits = self.snapshot.get("records")
        if not isinstance(self._hits, list):
            raise ValueError("National Gallery snapshot must contain records")

    def source_snapshot(self) -> str:
        return "sha256:" + hashlib.sha256(self._bytes).hexdigest()

    def records(self) -> Iterable[AdapterObjectRecord]:
        for hit in self._hits:
            source = hit.get("_source") or hit
            pid = (source.get("@admin") or {}).get("uid") or _identifier(source, "PID")
            if self.provider_record_ids is not None and str(pid or "") not in self.provider_record_ids:
                continue
            accession = _identifier(source, "object number")
            title = (source.get("summary") or {}).get("title") or _typed_value(source.get("title"), "full title")
            if not pid or not title:
                # Preserve malformed source rows for generic validation.
                pid = str(pid or "")
                title = str(title or "")
            legal = source.get("legal") or {}
            rights_rows = legal.get("rights") or []
            rights_details = "\n".join(str(row.get("details", "")) for row in rights_rows if isinstance(row, dict)).strip()
            media = []
            for position, item in enumerate(source.get("multimedia") or []):
                admin = item.get("@admin") or {}
                media_pid = admin.get("uid")
                if not media_pid:
                    continue
                # Official docs say IIIF URLs/media PIDs are not stable yet.
                # Store the dereferenceable media record as evidence only.
                media.append(AdapterMediaRecord(
                    provider_asset_id=str(media_pid),
                    original_url=f"https://data.ng.ac.uk/{media_pid}?profile=ciim-json",
                    purpose="REFERENCE", media_type=str(item.get("@type") or "OTHER").upper(),
                    rights_status="LICENSED" if rights_details else "UNKNOWN",
                    verification_state="DECLARED_BY_SOURCE" if rights_details else "UNKNOWN",
                    license_code="CC-BY-NC-ND-4.0" if "BY-NC-ND" in rights_details else None,
                    attribution="The National Gallery, London" if rights_details else None,
                    presentation_eligible=None, recognition_eligible=False,
                    source_rights_metadata={"source_declaration": rights_details or None, "iiif_status": "UNDER_DEVELOPMENT"},
                    association_scope="HOLDING", association_role="CONTEXTUAL" if item.get("@type") == "video" else "REFERENCE",
                    position=position, primary=position == 0,
                    source_relationship_key=f"{pid}:multimedia:{position}:{media_pid}",
                ))
            category = _typed_value(source.get("category"), "department")
            location = source.get("location") or {}
            current = location.get("current") or {}
            location_title = (current.get("summary") or {}).get("title")
            classifications = source.get("classification") or []
            object_type = _typed_value(classifications, "classification")
            processed = (source.get("@admin") or {}).get("processed")
            provider_modified = datetime.fromtimestamp(processed / 1000, tz=timezone.utc) if isinstance(processed, (int, float)) else None
            yield AdapterObjectRecord(
                provider_id=self.provider_id, provider_record_id=str(pid),
                institution_id=self.institution_id,
                institution_record_id=accession,
                source_url=f"https://data.ng.ac.uk/{pid}", source_language="en-GB",
                title_original=str(title), title_locale="en-GB",
                creator_display=_creator(source), date_display=_date(source),
                object_type=object_type, department=category,
                room=location_title if location_title and location_title.lower() != "not on display" else None,
                provider_modified_at=provider_modified, media=tuple(media), raw_payload=source,
            )
