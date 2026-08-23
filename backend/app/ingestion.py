"""Provider-neutral, fail-closed catalog ingestion and reconciliation core."""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import (
    Artwork,
    ArtworkCatalogMembership,
    Collection,
    CulturalObject,
    CulturalObjectDuplicateReview,
    IngestionChange,
    IngestionRun,
    Institution,
    InstitutionHolding,
    InstitutionProfile,
    MediaAsset,
    MediaProvenanceReview,
    SourceProvider,
    SourceRecord,
)
from .source_adapter import AdapterMediaRecord, AdapterObjectRecord, CatalogSourceAdapter

Risk = Literal["SAFE_AUTOMATIC", "REVIEW_RECOMMENDED", "HIGH_RISK"]
Action = Literal[
    "NEW", "MATCHED", "UNCHANGED", "UPDATE", "POSSIBLE_DUPLICATE",
    "CONFLICT", "INVALID", "SOURCE_MISSING",
]

PROVIDER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
PURPOSES = {"PRESENTATION", "REFERENCE", "RECOGNITION_ASSET", "SOURCE_ORIGINAL", "DERIVATIVE"}
RIGHTS = {"VERIFIED_PUBLIC_DOMAIN", "LICENSED", "UNKNOWN", "RESTRICTED"}
VERIFICATION = {"VERIFIED", "DECLARED_BY_SOURCE", "UNKNOWN", "RESTRICTED"}


class IngestionConfigurationError(ValueError):
    pass


class IngestionConflictError(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"{prefix}:{digest}"


def normalized_payload(record: AdapterObjectRecord) -> dict[str, Any]:
    payload = asdict(record)
    for key in ("retrieved_at", "provider_modified_at"):
        value = payload.get(key)
        payload[key] = value.isoformat() if isinstance(value, datetime) else value
    for media in payload.get("media", []):
        value = media.get("retrieved_at")
        media["retrieved_at"] = value.isoformat() if isinstance(value, datetime) else value
    return payload


def record_checksum(record: AdapterObjectRecord) -> str:
    # Retrieval time is transport state, not provider content.
    payload = normalized_payload(record)
    payload.pop("retrieved_at", None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PlannedRecord:
    provider_record_id: str
    action: Action
    risk: Risk
    reason: str
    checksum: str | None = None
    cultural_object_id: str | None = None
    institution_holding_id: str | None = None
    source_record_id: str | None = None
    artwork_id: str | None = None
    possible_duplicate_ids: tuple[str, ...] = ()
    changed_fields: tuple[str, ...] = ()
    media_additions: int = 0
    provenance_issues: tuple[str, ...] = ()
    record: AdapterObjectRecord | None = field(default=None, repr=False, compare=False)

    def public_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("record", None)
        return value


@dataclass(frozen=True)
class IngestionPlan:
    mode: str
    adapter_key: str
    provider_id: str
    institution_id: str
    source_snapshot: str | None
    generated_at: datetime
    records: tuple[PlannedRecord, ...]

    @property
    def summary(self) -> dict[str, int]:
        counts = {key: 0 for key in (
            "records_inspected", "new_objects", "new_holdings", "known_source_records",
            "possible_duplicates", "metadata_changes", "media_additions", "provenance_issues",
            "conflicts", "invalid_records", "records_requiring_review", "source_missing",
        )}
        counts["records_inspected"] = sum(1 for row in self.records if row.action != "SOURCE_MISSING")
        for row in self.records:
            if row.action in {"NEW", "POSSIBLE_DUPLICATE"}:
                counts["new_objects"] += 1
                counts["new_holdings"] += 1
            if row.action in {"MATCHED", "UNCHANGED", "UPDATE"}:
                counts["known_source_records"] += 1
            if row.action == "POSSIBLE_DUPLICATE": counts["possible_duplicates"] += 1
            if row.action == "UPDATE": counts["metadata_changes"] += 1
            if row.action == "CONFLICT": counts["conflicts"] += 1
            if row.action == "INVALID": counts["invalid_records"] += 1
            if row.action == "SOURCE_MISSING": counts["source_missing"] += 1
            if row.risk != "SAFE_AUTOMATIC": counts["records_requiring_review"] += 1
            counts["media_additions"] += row.media_additions
            counts["provenance_issues"] += len(row.provenance_issues)
        return counts

    def public_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode, "adapter_key": self.adapter_key,
            "provider_id": self.provider_id, "institution_id": self.institution_id,
            "source_snapshot": self.source_snapshot,
            "generated_at": self.generated_at.isoformat(), "summary": self.summary,
            "records": [row.public_dict() for row in self.records],
        }


def validate_target(db: Session, adapter: CatalogSourceAdapter, institution_id: str) -> tuple[SourceProvider, Institution]:
    institution = db.get(Institution, institution_id)
    if institution is None or not institution.active:
        raise IngestionConfigurationError("unknown or inactive institution")
    profile = db.get(InstitutionProfile, institution_id)
    if profile is None:
        raise IngestionConfigurationError("institution profile is required before ingestion")
    if not PROVIDER_ID_RE.fullmatch(adapter.provider_id):
        raise IngestionConfigurationError("invalid provider id")
    provider = db.get(SourceProvider, adapter.provider_id)
    if provider is None or not provider.active:
        raise IngestionConfigurationError("provider must be registered and active")
    if not provider.adapter_key or provider.adapter_key != adapter.adapter_key:
        raise IngestionConfigurationError("provider adapter mapping is missing or does not match")
    allowed = (provider.adapter_config or {}).get("institution_ids")
    if allowed is not None and institution_id not in allowed:
        raise IngestionConfigurationError("provider is not configured for this institution")
    return provider, institution


def validate_record(record: AdapterObjectRecord, adapter: CatalogSourceAdapter, institution_id: str) -> list[str]:
    errors = []
    if record.provider_id != adapter.provider_id: errors.append("provider mismatch")
    if record.institution_id != institution_id: errors.append("institution mismatch")
    if not record.provider_record_id or len(record.provider_record_id) > 500: errors.append("invalid provider_record_id")
    if not record.title_original or len(record.title_original) > 2000: errors.append("invalid title")
    for media in record.media:
        if media.purpose not in PURPOSES: errors.append(f"invalid media purpose:{media.purpose}")
        if media.rights_status not in RIGHTS: errors.append(f"invalid media rights:{media.rights_status}")
        if media.verification_state not in VERIFICATION: errors.append(f"invalid media verification:{media.verification_state}")
        if not media.original_url.startswith(("https://", "http://")): errors.append("invalid media URL")
    return errors


def _material_changes(existing: SourceRecord, record: AdapterObjectRecord) -> tuple[tuple[str, ...], Risk]:
    old = existing.raw_payload or {}
    new = normalized_payload(record)
    changed = tuple(key for key in (
        "title_original", "creator_display", "date_display", "institution_record_id",
        "source_url", "description", "media",
    ) if old.get(key) != new.get(key))
    if not changed:
        return (), "SAFE_AUTOMATIC"
    if "institution_record_id" in changed:
        return changed, "HIGH_RISK"
    if any(key in changed for key in ("title_original", "creator_display", "media")):
        return changed, "REVIEW_RECOMMENDED"
    return changed, "SAFE_AUTOMATIC"


def _provenance_issues(media: Iterable[AdapterMediaRecord]) -> tuple[str, ...]:
    issues = []
    for index, asset in enumerate(media):
        if asset.rights_status == "UNKNOWN": issues.append(f"media[{index}]:rights_unknown")
        if asset.verification_state != "VERIFIED": issues.append(f"media[{index}]:not_verified")
        if not asset.attribution and asset.rights_status != "UNKNOWN": issues.append(f"media[{index}]:attribution_missing")
        if asset.rights_status == "RESTRICTED": issues.append(f"media[{index}]:restricted")
    return tuple(issues)


def _media_addition_count(db: Session, provider_id: str, media: Iterable[AdapterMediaRecord]) -> int:
    count = 0
    for asset in media:
        exists = db.query(MediaAsset.id).filter(
            MediaAsset.provider_id == provider_id,
            MediaAsset.original_url == asset.original_url,
            MediaAsset.purpose == asset.purpose,
        ).first()
        if not exists: count += 1
    return count


def build_plan(
    db: Session,
    adapter: CatalogSourceAdapter,
    institution_id: str,
    *,
    mode: str = "PLAN",
    include_missing: bool = False,
) -> IngestionPlan:
    """Read-only planning. This function never adds, flushes or commits."""
    validate_target(db, adapter, institution_id)
    records = tuple(adapter.records())
    seen_batch: set[str] = set()
    planned: list[PlannedRecord] = []
    for record in records:
        errors = validate_record(record, adapter, institution_id)
        if record.provider_record_id in seen_batch:
            errors.append("duplicate provider_record_id in adapter batch")
        seen_batch.add(record.provider_record_id)
        if errors:
            planned.append(PlannedRecord(record.provider_record_id, "INVALID", "HIGH_RISK", "; ".join(errors), record=record))
            continue
        checksum = record_checksum(record)
        source = db.query(SourceRecord).filter(
            SourceRecord.provider_id == adapter.provider_id,
            SourceRecord.provider_record_id == record.provider_record_id,
        ).first()
        issues = _provenance_issues(record.media)
        media_count = _media_addition_count(db, adapter.provider_id, record.media)
        if source:
            if source.institution_id and source.institution_id != institution_id:
                planned.append(PlannedRecord(record.provider_record_id, "CONFLICT", "HIGH_RISK", "source record belongs to another institution", checksum, source_record_id=source.id, record=record))
                continue
            if source.content_checksum == checksum:
                planned.append(PlannedRecord(record.provider_record_id, "UNCHANGED", "SAFE_AUTOMATIC", "source checksum unchanged", checksum, source.cultural_object_id, source.institution_holding_id, source.id, media_additions=media_count, provenance_issues=issues, record=record))
            else:
                changed, risk = _material_changes(source, record)
                planned.append(PlannedRecord(record.provider_record_id, "UPDATE", risk, "provider record changed" if source.content_checksum else "legacy source record requires synchronization baseline", checksum, source.cultural_object_id, source.institution_holding_id, source.id, changed_fields=changed, media_additions=media_count, provenance_issues=issues, record=record))
            continue

        holding = None
        if record.institution_record_id:
            holding = db.query(InstitutionHolding).filter(
                InstitutionHolding.institution_id == institution_id,
                InstitutionHolding.institution_record_id == record.institution_record_id,
            ).first()
        if holding:
            artwork = db.query(Artwork).filter(Artwork.institution_holding_id == holding.id).first()
            planned.append(PlannedRecord(record.provider_record_id, "MATCHED", "REVIEW_RECOMMENDED", "strong institution record matched; new provider link requires review", checksum, holding.cultural_object_id, holding.id, stable_id("source-record", adapter.provider_id, record.provider_record_id), artwork.id if artwork else None, media_additions=media_count, provenance_issues=issues, record=record))
            continue

        duplicate_ids: tuple[str, ...] = ()
        if record.creator_display:
            matches = db.query(Artwork.cultural_object_id).filter(
                Artwork.museum_id == institution_id,
                func.lower(Artwork.title_original) == record.title_original.lower(),
                func.lower(Artwork.artist) == record.creator_display.lower(),
            ).limit(5).all()
            duplicate_ids = tuple(sorted({row[0] for row in matches if row[0]}))
        action: Action = "POSSIBLE_DUPLICATE" if duplicate_ids else "NEW"
        risk: Risk = "REVIEW_RECOMMENDED" if duplicate_ids else "SAFE_AUTOMATIC"
        planned.append(PlannedRecord(
            record.provider_record_id, action, risk,
            "weak metadata suggests an existing object; no automatic merge" if duplicate_ids else "new provider record",
            checksum,
            stable_id("object", adapter.provider_id, record.provider_record_id),
            stable_id("holding", adapter.provider_id, record.provider_record_id),
            stable_id("source-record", adapter.provider_id, record.provider_record_id),
            stable_id("artwork", adapter.provider_id, record.provider_record_id),
            duplicate_ids, (), media_count, issues, record,
        ))

    if include_missing:
        existing = db.query(SourceRecord).filter(SourceRecord.provider_id == adapter.provider_id, SourceRecord.institution_id == institution_id, SourceRecord.active.is_(True)).all()
        for source in existing:
            if source.provider_record_id not in seen_batch:
                planned.append(PlannedRecord(source.provider_record_id, "SOURCE_MISSING", "HIGH_RISK", "active provider record absent from current snapshot; no automatic deactivation", source.content_checksum, source.cultural_object_id, source.institution_holding_id, source.id))

    return IngestionPlan(mode, adapter.adapter_key, adapter.provider_id, institution_id, adapter.source_snapshot(), utcnow(), tuple(planned))


def _collection_id(db: Session, institution_id: str, source_id: str | None) -> str | None:
    if not source_id: return None
    row = db.query(Collection).filter(Collection.institution_id == institution_id, Collection.source_record_id == source_id).first()
    return row.id if row else None


def _eligibility(asset: AdapterMediaRecord) -> tuple[bool | None, bool | None]:
    if asset.rights_status == "RESTRICTED" or asset.verification_state == "RESTRICTED":
        return False, False
    # Adapter hints are recorded, but only an explicit ELYIO VERIFIED state
    # may activate use. SOURCE_DECLARED/UNKNOWN never self-promote.
    if asset.verification_state != "VERIFIED":
        return None, False
    return bool(asset.presentation_eligible), bool(asset.recognition_eligible)


def _upsert_media(db: Session, plan: PlannedRecord, run_id: str, artwork_id: str | None) -> int:
    created = 0
    assert plan.record is not None and plan.cultural_object_id
    for asset in plan.record.media:
        existing = db.query(MediaAsset).filter(
            MediaAsset.provider_id == plan.record.provider_id,
            MediaAsset.original_url == asset.original_url,
            MediaAsset.purpose == asset.purpose,
        ).first()
        if existing: continue
        presentation, recognition = _eligibility(asset)
        source_metadata = dict(asset.source_rights_metadata or {})
        source_metadata["adapter_presentation_hint"] = asset.presentation_eligible
        source_metadata["adapter_recognition_hint"] = asset.recognition_eligible
        db.add(MediaAsset(
            id=stable_id("media", plan.record.provider_id, asset.provider_asset_id or asset.original_url, asset.purpose),
            cultural_object_id=plan.cultural_object_id,
            artwork_id=artwork_id,
            institution_holding_id=plan.institution_holding_id,
            source_record_id=plan.source_record_id,
            provider_id=plan.record.provider_id,
            provider_asset_id=asset.provider_asset_id,
            purpose=asset.purpose, media_type=asset.media_type,
            original_url=asset.original_url, asset_url=None,
            rights_status=asset.rights_status,
            verification_state=asset.verification_state,
            license_code=asset.license_code, license_text=asset.license_text,
            attribution=asset.attribution,
            public_domain=True if asset.rights_status == "VERIFIED_PUBLIC_DOMAIN" and asset.verification_state == "VERIFIED" else None,
            presentation_eligible=presentation, recognition_eligible=recognition,
            retrieved_at=asset.retrieved_at, checksum_sha256=asset.checksum_sha256,
            source_rights_metadata=source_metadata, ingestion_run_id=run_id,
        ))
        created += 1
    return created


def apply_plan(db: Session, plan: IngestionPlan, *, operator_id: str | None = None, code_version: str | None = None) -> str:
    if plan.mode not in {"PLAN", "DRY_RUN", "RECONCILE", "APPLY"}:
        raise ValueError("unsupported plan mode")
    blockers = [row for row in plan.records if row.action in {"CONFLICT", "INVALID", "SOURCE_MISSING"}]
    if blockers:
        raise IngestionConflictError(f"apply refused: {len(blockers)} blocking reconciliation item(s)")
    run_id = str(uuid.uuid4())
    run = IngestionRun(
        id=run_id, mode="APPLY", adapter_key=plan.adapter_key,
        provider_id=plan.provider_id, institution_id=plan.institution_id,
        code_version=code_version or os.environ.get("GIT_COMMIT_SHA"),
        source_snapshot=plan.source_snapshot, operator_id=operator_id,
        records_inspected=plan.summary["records_inspected"],
    )
    db.add(run)
    created = updated = unchanged = conflicts = failed = 0
    try:
        for item in plan.records:
            record = item.record
            assert record is not None
            artwork_id = item.artwork_id
            if item.action in {"NEW", "POSSIBLE_DUPLICATE"}:
                db.add(CulturalObject(id=item.cultural_object_id, canonical_title=record.title_original, canonical_creator=record.creator_display, identity_status="SOURCE_SINGLETON"))
                db.add(InstitutionHolding(
                    id=item.institution_holding_id, cultural_object_id=item.cultural_object_id,
                    institution_id=plan.institution_id,
                    institution_record_id=record.institution_record_id or item.artwork_id,
                    collection_id=_collection_id(db, plan.institution_id, record.collection_source_id),
                    relationship_type="HOLDING", status="CURRENT",
                    location_text=record.room or record.gallery,
                ))
                db.add(Artwork(
                    id=artwork_id, museum_id=plan.institution_id,
                    cultural_object_id=item.cultural_object_id,
                    institution_holding_id=item.institution_holding_id,
                    title_original=record.title_original, artist=record.creator_display,
                    year=record.date_display, inventory_number=record.institution_record_id,
                    object_type=record.object_type, description=record.description,
                    department=record.department, room=record.room,
                    source=plan.provider_id, source_record_id=record.provider_record_id,
                    source_url=record.source_url, source_language=record.source_language or record.title_locale,
                    last_source_sync=record.retrieved_at or utcnow(), raw_json=record.raw_payload,
                ))
                if item.action == "POSSIBLE_DUPLICATE":
                    for duplicate_id in item.possible_duplicate_ids:
                        a, b = sorted((item.cultural_object_id, duplicate_id))
                        if not db.query(CulturalObjectDuplicateReview.id).filter(CulturalObjectDuplicateReview.object_a_id == a, CulturalObjectDuplicateReview.object_b_id == b).first():
                            db.add(CulturalObjectDuplicateReview(object_a_id=a, object_b_id=b, decision="POSSIBLE_DUPLICATE", evidence={"ingestion_run_id": run_id, "reason": item.reason}))
                created += 1
            elif item.action == "MATCHED":
                existing_artwork = db.query(Artwork).filter(Artwork.institution_holding_id == item.institution_holding_id).first()
                artwork_id = existing_artwork.id if existing_artwork else None
                created += 1
            elif item.action == "UNCHANGED":
                unchanged += 1
            elif item.action == "UPDATE":
                updated += 1

            source = db.get(SourceRecord, item.source_record_id) if item.source_record_id else None
            if source is None:
                source = SourceRecord(
                    id=item.source_record_id, provider_id=plan.provider_id,
                    provider_record_id=record.provider_record_id,
                    cultural_object_id=item.cultural_object_id,
                    institution_holding_id=item.institution_holding_id,
                    institution_id=plan.institution_id,
                    first_seen_at=utcnow(), ingestion_status="INGESTED",
                    review_status="REVIEW_REQUIRED" if item.risk != "SAFE_AUTOMATIC" else "UNREVIEWED",
                )
                db.add(source)
            source.last_seen_at = utcnow()
            source.retrieved_at = record.retrieved_at
            source.provider_modified_at = record.provider_modified_at
            source.last_ingestion_run_id = run_id
            source.active = True
            if item.risk == "SAFE_AUTOMATIC" or source.content_checksum is None:
                source.source_url = record.source_url
                source.source_language = record.source_language or record.title_locale
                source.raw_payload = normalized_payload(record)
                source.content_checksum = item.checksum
            else:
                source.review_status = "REVIEW_REQUIRED"

            media_created = _upsert_media(db, item, run_id, artwork_id)
            db.add(IngestionChange(
                ingestion_run_id=run_id, provider_id=plan.provider_id,
                provider_record_id=item.provider_record_id, action=item.action,
                risk=item.risk, status="APPLIED" if item.risk == "SAFE_AUTOMATIC" else "REVIEW_REQUIRED",
                cultural_object_id=item.cultural_object_id,
                institution_holding_id=item.institution_holding_id,
                source_record_id=item.source_record_id,
                details={"reason": item.reason, "changed_fields": list(item.changed_fields), "media_created": media_created, "possible_duplicate_ids": list(item.possible_duplicate_ids)},
            ))

        run.created_count, run.updated_count, run.unchanged_count = created, updated, unchanged
        run.conflict_count, run.failed_count = conflicts, failed
        run.summary = plan.summary
        run.status = "APPLIED"
        run.finished_at = utcnow()
        db.commit()
        return run_id
    except Exception as exc:
        db.rollback()
        failed_run = IngestionRun(
            id=run_id, mode="APPLY", adapter_key=plan.adapter_key,
            provider_id=plan.provider_id, institution_id=plan.institution_id,
            status="FAILED", code_version=code_version or os.environ.get("GIT_COMMIT_SHA"),
            source_snapshot=plan.source_snapshot, operator_id=operator_id,
            records_inspected=plan.summary["records_inspected"], failed_count=1,
            error=str(exc)[:4000], started_at=run.started_at, finished_at=utcnow(),
        )
        db.add(failed_run)
        db.commit()
        raise


def safe_deactivate_source_record(db: Session, source_record_id: str, *, operator_id: str) -> dict[str, int]:
    source = db.get(SourceRecord, source_record_id)
    if source is None: raise ValueError("source record not found")
    source.active = False
    source.ingestion_status = "DEACTIVATED"
    media = db.query(MediaAsset).filter(MediaAsset.source_record_id == source.id).all()
    for asset in media:
        before = {"presentation_eligible": asset.presentation_eligible, "recognition_eligible": asset.recognition_eligible}
        asset.presentation_eligible = False
        asset.recognition_eligible = False
        asset.review_notes = f"Deactivated by {operator_id}"
        asset.reviewed_by = operator_id
        asset.reviewed_at = utcnow()
        db.add(MediaProvenanceReview(
            media_asset_id=asset.id, actor=operator_id, action="SAFE_DEACTIVATION",
            before_state=before,
            after_state={"presentation_eligible": False, "recognition_eligible": False},
            notes="Source record deactivated; asset retained and made ineligible",
        ))
    memberships = []
    if source.institution_holding_id:
        artwork = db.query(Artwork).filter(Artwork.institution_holding_id == source.institution_holding_id).first()
        if artwork:
            memberships = db.query(ArtworkCatalogMembership).filter(ArtworkCatalogMembership.artwork_id == artwork.id, ArtworkCatalogMembership.active.is_(True)).all()
            for membership in memberships: membership.active = False
    db.commit()
    return {"media_disabled": len(media), "memberships_deactivated": len(memberships)}


def readiness_report(db: Session, institution_id: str) -> dict[str, Any]:
    holding_ids = [row[0] for row in db.query(InstitutionHolding.id).filter(InstitutionHolding.institution_id == institution_id, InstitutionHolding.status == "CURRENT").all()]
    artwork_rows = db.query(Artwork).filter(Artwork.institution_holding_id.in_(holding_ids)).all() if holding_ids else []
    artwork_ids = {row.id for row in artwork_rows}
    media = db.query(MediaAsset).filter(MediaAsset.artwork_id.in_(artwork_ids)).all() if artwork_ids else []
    presentation_ids = {row.artwork_id for row in media if row.presentation_eligible is True}
    recognition_ids = {row.artwork_id for row in media if row.recognition_eligible is True}
    reference_ids = {row.artwork_id for row in media if row.purpose in {"REFERENCE", "RECOGNITION_ASSET", "SOURCE_ORIGINAL"} and row.original_url and row.rights_status != "RESTRICTED"}
    missing_metadata = {row.id for row in artwork_rows if not row.title_original}
    provenance_blocked = {row.artwork_id for row in media if row.verification_state != "VERIFIED" or row.rights_status in {"UNKNOWN", "RESTRICTED"}}
    return {
        "institution_id": institution_id,
        "total_holdings": len(holding_ids),
        "media_reference_coverage": len(reference_ids),
        "presentation_eligible": len(presentation_ids),
        "recognition_eligible": len(recognition_ids),
        "vision_plus_asset": len(recognition_ids),
        "vision_ready": len(artwork_ids - recognition_ids - missing_metadata),
        "not_ready": len(missing_metadata),
        "missing_metadata": len(missing_metadata),
        "provenance_blockers": len({value for value in provenance_blocked if value}),
        "ready_for_benchmark": bool(artwork_ids) and not missing_metadata and not provenance_blocked,
    }
