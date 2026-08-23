"""Contract for provider-specific catalog adapters.

Adapters fetch/normalize provider truth. Core ingestion consumes this shape;
it must not branch on Louvre, a country, currency, or language.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Protocol


@dataclass(frozen=True)
class AdapterMediaRecord:
    provider_asset_id: str | None
    original_url: str
    purpose: str
    media_type: str = "IMAGE"
    rights_status: str = "UNKNOWN"
    verification_state: str = "UNKNOWN"
    license_code: str | None = None
    attribution: str | None = None
    presentation_eligible: bool | None = None
    recognition_eligible: bool | None = None
    retrieved_at: datetime | None = None
    checksum_sha256: str | None = None
    license_text: str | None = None
    source_rights_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterObjectRecord:
    provider_id: str
    provider_record_id: str
    institution_id: str
    source_url: str | None
    source_language: str | None
    title_original: str
    title_locale: str | None = None
    creator_display: str | None = None
    date_display: str | None = None
    object_type: str | None = None
    description: str | None = None
    institution_record_id: str | None = None
    collection_source_id: str | None = None
    department: str | None = None
    room: str | None = None
    gallery: str | None = None
    retrieved_at: datetime | None = None
    provider_modified_at: datetime | None = None
    media: tuple[AdapterMediaRecord, ...] = ()
    raw_payload: dict[str, Any] = field(default_factory=dict)


class CatalogSourceAdapter(Protocol):
    provider_id: str
    adapter_key: str

    def records(self) -> Iterable[AdapterObjectRecord]: ...

    def source_snapshot(self) -> str | None: ...
