import base64
import csv
import hashlib
import hmac
import json
import math
import os
import secrets
import threading
import time
import uuid
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, and_, case, desc, distinct, func, inspect, or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import SessionLocal, get_db
from .auth import get_optional_current_user
from .models import (
    AdminLoginAttempt,
    AdminSession,
    AnalyticsIdentityLink,
    AnalyticsSession,
    Artwork,
    ArtworkCatalogMembership,
    ArtworkLocalization,
    ArtworkValueReveal,
    Country,
    InstitutionHolding,
    InstitutionProfile,
    LouvreImageReference,
    MediaAsset,
    MediaAssetAssociation,
    MediaProvenanceReview,
    Museum,
    ProductEvent,
    RecognitionAsset,
    RecognitionAttempt,
    UncatalogedSighting,
    User,
    Visit,
    VisitArtwork,
)

router = APIRouter()

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "alexsen33@gmail.com").strip().lower()
DEFAULT_ADMIN_PASSWORD_HASH = (
    "pbkdf2_sha256$260000$OuaLQdcniDseZVsAq3dBoA$BkRoanD8tyigNeU3vhSePRsiXDUhvghHVSwFpKYfhuk"
)
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", DEFAULT_ADMIN_PASSWORD_HASH)
ADMIN_COOKIE_NAME = os.environ.get("ADMIN_COOKIE_NAME", "elyio_admin_session")
ADMIN_SESSION_DAYS = int(os.environ.get("ADMIN_SESSION_DAYS", "7"))
ADMIN_LOGIN_WINDOW_MINUTES = int(os.environ.get("ADMIN_LOGIN_WINDOW_MINUTES", "15"))
ADMIN_LOGIN_MAX_FAILURES = int(os.environ.get("ADMIN_LOGIN_MAX_FAILURES", "8"))
TRACKING_AVAILABLE_SINCE = "2026-08-20"
TRUSTED_ANALYTICS_AVAILABLE_SINCE = "2026-08-23"
EVENT_SCHEMA_VERSION = 2
EVENT_BODY_MAX_BYTES = int(os.environ.get("EVENT_BODY_MAX_BYTES", "32768"))
EVENT_RATE_LIMIT_PER_MINUTE = int(os.environ.get("EVENT_RATE_LIMIT_PER_MINUTE", "120"))
EVENT_PROPERTIES_MAX_BYTES = int(os.environ.get("EVENT_PROPERTIES_MAX_BYTES", "8192"))
ANALYTICS_QA_TOKEN = os.environ.get("ANALYTICS_QA_TOKEN")

PUBLIC_EVENT_ALLOWLIST = {
    "achievement_unlocked", "app_opened", "artwork_added", "artwork_card_opened",
    "artwork_card_read_time", "artwork_favorited", "artwork_viewed", "audio_completed",
    "audio_started", "candidate_confirmed", "catalog_match", "catalog_no_match",
    "favorite_added", "finish_visit_clicked", "image_captured", "language_selected",
    "mission_completed", "museum_selected", "onboarding_completed", "progress_viewed",
    "pwa_install_cta_clicked", "pwa_install_cta_shown", "pwa_install_prompt_shown",
    "pwa_install_started", "pwa_install_prompt_accepted", "pwa_install_prompt_dismissed",
    "pwa_installed", "pwa_standalone_open", "pwa_ios_instructions_shown",
    "comparison_set_viewed", "comparison_surprise_clicked",
    "recap_generated", "recap_viewed", "recognition_completed", "recognition_failed",
    "recognition_started", "result_viewed", "scan_attempt", "scan_failed", "scan_opened",
    "scan_success", "second_scan_started", "seo_begin_visit", "session_started",
    "share_card_viewed", "share_clicked", "share_completed", "share_saved", "share_started",
    "visit_completed", "visit_started",
}
ARTWORK_DIMENSION_EVENTS = {
    "artwork_added", "artwork_card_opened", "artwork_card_read_time", "artwork_favorited",
    "artwork_viewed", "audio_completed", "audio_started", "candidate_confirmed",
    "catalog_match", "favorite_added", "result_viewed", "scan_success",
}
MEANINGFUL_CLIENT_EVENTS = {
    "museum_selected", "visit_started", "scan_attempt", "result_viewed", "artwork_viewed",
    "artwork_added", "favorite_added", "progress_viewed", "recap_viewed", "share_completed",
}
SUCCESSFUL_RECOGNITION_OUTCOMES = {"success", "uncataloged_result", "ai_result"}
FAILED_RECOGNITION_OUTCOMES = {"no_match", "invalid_image", "timeout", "failed"}
_event_rate_buckets: Dict[str, deque[float]] = defaultdict(deque)
_event_rate_lock = threading.Lock()

MEANINGFUL_EVENTS = {
    "visit_started",
    "museum_selected",
    "scan_opened",
    "image_captured",
    "recognition_started",
    "recognition_completed",
    "recognition_succeeded",
    "recognition_failed",
    "scan_success",
    "scan_failed",
    "result_viewed",
    "artwork_viewed",
    "artwork_added",
    "favorite_added",
    "progress_viewed",
    "recap_viewed",
    "share_clicked",
    "share_completed",
}
SUCCESS_EVENTS = {"recognition_succeeded", "scan_success"}
FAILURE_EVENTS = {"recognition_failed", "scan_failed"}
FUNNEL_STAGES = [
    ("app_opened", "App opened"),
    ("museum_selected", "Museum selected"),
    ("visit_started", "Visit started"),
    ("scan_attempt", "Image captured/uploaded"),
    ("recognition_started", "Recognition submitted"),
    ("scan_success", "Successful recognition"),
    ("result_viewed", "Artwork result viewed"),
    ("second_scan_started", "Second artwork scanned"),
    ("recap_viewed", "Recap viewed"),
]


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class ProductEventIn(BaseModel):
    schema_version: int = Field(default=1, ge=1, le=EVENT_SCHEMA_VERSION)
    event_id: str
    event_name: str = Field(min_length=1, max_length=64)
    client_occurred_at: Optional[datetime] = None
    # Accepted only for v1 compatibility and stored as an untrusted client time.
    occurred_at: Optional[datetime] = None
    user_id: Optional[str] = None
    anonymous_id: Optional[str] = Field(default=None, max_length=36)
    session_id: Optional[str] = Field(default=None, max_length=36)
    museum_id: Optional[str] = Field(default=None, max_length=120)
    artwork_id: Optional[str] = Field(default=None, max_length=200)
    recognition_attempt_id: Optional[str] = Field(default=None, max_length=36)
    properties: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = Field(default=None, max_length=120)
    referrer: Optional[str] = Field(default=None, max_length=2048)
    utm_source: Optional[str] = Field(default=None, max_length=200)
    utm_medium: Optional[str] = Field(default=None, max_length=200)
    utm_campaign: Optional[str] = Field(default=None, max_length=200)
    utm_content: Optional[str] = Field(default=None, max_length=200)
    language: Optional[str] = Field(default=None, max_length=80)
    device_type: Optional[str] = Field(default=None, max_length=40)
    os: Optional[str] = Field(default=None, max_length=80)
    browser: Optional[str] = Field(default=None, max_length=80)
    path: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("event_id", "anonymous_id", "session_id", "recognition_attempt_id")
    @classmethod
    def identifiers_are_uuids(cls, value: Optional[str]):
        if value is None:
            return value
        try:
            return str(uuid.UUID(value))
        except ValueError as exc:
            raise ValueError("identifier must be a UUID") from exc

    @field_validator("event_name")
    @classmethod
    def event_is_supported(cls, value: str):
        if value not in PUBLIC_EVENT_ALLOWLIST:
            raise ValueError("unsupported public event")
        return value

    @field_validator("properties")
    @classmethod
    def properties_are_bounded(cls, value: Dict[str, Any]):
        def depth(node: Any, level: int = 0) -> int:
            if level > 5:
                raise ValueError("properties exceed maximum nesting depth")
            if isinstance(node, dict):
                for key, child in node.items():
                    if not isinstance(key, str) or len(key) > 120:
                        raise ValueError("properties contain an invalid key")
                    depth(child, level + 1)
            elif isinstance(node, list):
                if len(node) > 50:
                    raise ValueError("properties array is too large")
                for child in node:
                    depth(child, level + 1)
            elif isinstance(node, str) and len(node) > 2000:
                raise ValueError("property string is too large")
            return level
        depth(value)
        if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > EVENT_PROPERTIES_MAX_BYTES:
            raise ValueError("properties payload is too large")
        return value


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "")
    if not ip:
        return None
    pepper = os.environ.get("ADMIN_IP_HASH_PEPPER", "elyio-admin-ip-v1")
    return hashlib.sha256(f"{pepper}:{ip}".encode("utf-8")).hexdigest()


def _trusted_internal_request(request: Request) -> bool:
    supplied = request.headers.get("x-elyio-qa-token", "")
    return bool(ANALYTICS_QA_TOKEN and supplied and hmac.compare_digest(supplied, ANALYTICS_QA_TOKEN))


def _enforce_event_rate_limit(request: Request, anonymous_id: Optional[str]) -> None:
    now_monotonic = time.monotonic()
    ip_key = _hash_ip(request) or "unknown"
    keys = [f"ip:{ip_key}"]
    if anonymous_id:
        keys.append(f"anon:{anonymous_id}")
    with _event_rate_lock:
        for key in keys:
            bucket = _event_rate_buckets[key]
            while bucket and bucket[0] <= now_monotonic - 60:
                bucket.popleft()
            if len(bucket) >= EVENT_RATE_LIMIT_PER_MINUTE:
                raise HTTPException(status_code=429, detail="event ingestion rate limit exceeded")
        for key in keys:
            _event_rate_buckets[key].append(now_monotonic)


def _link_analytics_identity(db: Session, anonymous_id: Optional[str], user: Optional[User]) -> None:
    if not anonymous_id or user is None or not _table_exists(db, "analytics_identity_links"):
        return
    user_id = str(user.id)
    row = db.get(AnalyticsIdentityLink, anonymous_id)
    if row is None:
        db.add(AnalyticsIdentityLink(anonymous_id=anonymous_id, user_id=user_id))
    elif row.user_id != user_id:
        # A browser identifier cannot be silently reassigned between accounts.
        raise HTTPException(status_code=409, detail="anonymous identity is already linked to another user")
    else:
        row.last_seen_at = _utcnow()


def _validate_analytics_session(
    db: Session,
    session_id: Optional[str],
    anonymous_id: Optional[str],
    user: Optional[User],
) -> None:
    if not session_id or not _table_exists(db, "analytics_sessions"):
        return
    user_id = str(user.id) if user else None
    row = db.get(AnalyticsSession, session_id)
    if row is None:
        db.add(AnalyticsSession(session_id=session_id, anonymous_id=anonymous_id, user_id=user_id))
        return
    if row.anonymous_id and anonymous_id and row.anonymous_id != anonymous_id:
        raise HTTPException(status_code=409, detail="session belongs to another anonymous identity")
    if row.user_id and user_id and row.user_id != user_id:
        raise HTTPException(status_code=409, detail="session belongs to another authenticated user")
    row.anonymous_id = row.anonymous_id or anonymous_id
    row.user_id = row.user_id or user_id
    row.last_seen_at = _utcnow()


def _b64decode_padded(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_password(password: str, encoded_hash: Optional[str] = None) -> bool:
    try:
        encoded_hash = encoded_hash or ADMIN_PASSWORD_HASH
        algorithm, iterations_raw, salt_raw, digest_raw = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = _b64decode_padded(salt_raw)
        expected = _b64decode_padded(digest_raw)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _cookie_secure(request: Request) -> bool:
    if os.environ.get("ADMIN_COOKIE_SECURE", "").lower() in {"0", "false", "no"}:
        return False
    return request.url.scheme == "https" or os.environ.get("FLY_APP_NAME") is not None


def _table_exists(db: Session, table_name: str) -> bool:
    try:
        return inspect(db.bind).has_table(table_name) if db.bind is not None else False
    except Exception:
        return False


def _identity_expr():
    linked_user = (
        select(AnalyticsIdentityLink.user_id)
        .where(AnalyticsIdentityLink.anonymous_id == ProductEvent.anonymous_id)
        .limit(1)
        .scalar_subquery()
    )
    return func.coalesce(ProductEvent.user_id, linked_user, ProductEvent.anonymous_id)


def _attempt_identity_expr():
    linked_user = (
        select(AnalyticsIdentityLink.user_id)
        .where(AnalyticsIdentityLink.anonymous_id == RecognitionAttempt.anonymous_id)
        .limit(1)
        .scalar_subquery()
    )
    return func.coalesce(RecognitionAttempt.user_id, linked_user, RecognitionAttempt.anonymous_id)


def _attempt_base_query(db: Session, start: Optional[datetime], end: datetime, include_internal: bool = False):
    query = db.query(RecognitionAttempt).filter(RecognitionAttempt.completed_at.isnot(None))
    if start:
        query = query.filter(RecognitionAttempt.completed_at >= start)
    query = query.filter(RecognitionAttempt.completed_at < end)
    if not include_internal:
        query = query.filter(RecognitionAttempt.internal_test.is_(False))
    return query


def _safe_datetime(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _period_bounds(period: str) -> Tuple[Optional[datetime], datetime, Optional[datetime], Optional[datetime], str]:
    now = _utcnow()
    key = period or "30d"
    if key == "today":
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    elif key == "7d":
        start = now - timedelta(days=7)
    elif key == "90d":
        start = now - timedelta(days=90)
    elif key == "all":
        return None, now, None, None, "All time"
    else:
        start = now - timedelta(days=30)
        key = "30d"
    span = now - start
    return start, now, start - span, start, key


def _non_internal_event_filter():
    return ProductEvent.internal_test.isnot(True)


def _event_base_query(
    db: Session,
    start: Optional[datetime],
    end: datetime,
    include_internal: bool = False,
    trusted_only: bool = True,
):
    query = db.query(ProductEvent)
    if start:
        query = query.filter(ProductEvent.occurred_at >= start)
    query = query.filter(ProductEvent.occurred_at < end)
    if not include_internal:
        query = query.filter(_non_internal_event_filter())
    if trusted_only:
        query = query.filter(
            ProductEvent.schema_version == EVENT_SCHEMA_VERSION,
            ProductEvent.business_eligible.is_(True),
        )
    return query


def _identity_count(db: Session, start: Optional[datetime], end: datetime, event_names: Optional[Iterable[str]] = None) -> int:
    if not _table_exists(db, "product_events"):
        return 0
    query = _event_base_query(db, start, end).filter(_identity_expr().isnot(None))
    if event_names:
        query = query.filter(ProductEvent.event_name.in_(list(event_names)))
    return int(query.with_entities(func.count(distinct(_identity_expr()))).scalar() or 0)


def _event_count(db: Session, start: Optional[datetime], end: datetime, event_names: Optional[Iterable[str]] = None) -> int:
    if not _table_exists(db, "product_events"):
        return 0
    query = _event_base_query(db, start, end)
    if event_names:
        query = query.filter(ProductEvent.event_name.in_(list(event_names)))
    return int(query.count())


def _identified_event_query(db: Session, start: Optional[datetime], end: datetime):
    return _event_base_query(db, start, end).filter(_identity_expr().isnot(None))


def _pct(current: int | float, previous: int | float) -> Optional[float]:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _with_delta(current: int | float, previous: int | float) -> Dict[str, Any]:
    return {"value": current, "previous": previous, "delta": current - previous, "pct_change": _pct(current, previous)}


def _extract_prop(properties: Optional[dict], *keys: str) -> Any:
    if not isinstance(properties, dict):
        return None
    for key in keys:
        if key in properties:
            return properties.get(key)
    return None


def _event_to_row(event: ProductEvent) -> Dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_name": event.event_name,
        "occurred_at": _safe_datetime(event.occurred_at),
        "user_id": event.user_id,
        "anonymous_id": event.anonymous_id,
        "session_id": event.session_id,
        "museum_id": event.museum_id,
        "artwork_id": event.artwork_id,
        "recognition_attempt_id": event.recognition_attempt_id,
        "properties": event.properties or {},
        "source": event.source,
        "referrer": event.referrer,
        "utm_source": event.utm_source,
        "utm_medium": event.utm_medium,
        "utm_campaign": event.utm_campaign,
        "utm_content": event.utm_content,
        "language": event.language,
        "device_type": event.device_type,
        "os": event.os,
        "browser": event.browser,
        "path": event.path,
        "schema_version": event.schema_version,
        "client_occurred_at": _safe_datetime(event.client_occurred_at),
        "server_received_at": _safe_datetime(event.server_received_at),
        "internal_test": event.internal_test,
        "trust_level": event.trust_level,
        "business_eligible": event.business_eligible,
    }


def _record_login_attempt(db: Session, email: str, ip_hash: Optional[str], success: bool, user_agent: Optional[str]) -> None:
    db.add(AdminLoginAttempt(email=email[:255], ip_hash=ip_hash, success=success, user_agent=(user_agent or "")[:2000]))
    db.commit()


def _failed_attempts(db: Session, email: str, ip_hash: Optional[str]) -> int:
    since = _utcnow() - timedelta(minutes=ADMIN_LOGIN_WINDOW_MINUTES)
    query = db.query(AdminLoginAttempt).filter(
        AdminLoginAttempt.success.is_(False),
        AdminLoginAttempt.attempted_at >= since,
        or_(AdminLoginAttempt.email == email, AdminLoginAttempt.ip_hash == ip_hash),
    )
    return int(query.count())


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
    admin_cookie: Optional[str] = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
) -> AdminSession:
    if not admin_cookie:
        raise HTTPException(status_code=401, detail="admin authentication required")
    session = (
        db.query(AdminSession)
        .filter(AdminSession.token_hash == _hash_token(admin_cookie), AdminSession.revoked_at.is_(None))
        .first()
    )
    if not session or _as_aware(session.expires_at) <= _utcnow():
        raise HTTPException(status_code=401, detail="admin authentication required")
    session.last_seen_at = _utcnow()
    db.commit()
    return session


@router.post("/v1/admin/login")
def admin_login(payload: AdminLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    if not _table_exists(db, "admin_sessions"):
        raise HTTPException(status_code=503, detail="admin schema is not installed")
    email = payload.email.strip().lower()
    ip_hash = _hash_ip(request)
    if _failed_attempts(db, email, ip_hash) >= ADMIN_LOGIN_MAX_FAILURES:
        raise HTTPException(status_code=429, detail="too many login attempts")
    ok = email == ADMIN_EMAIL and verify_password(payload.password)
    _record_login_attempt(db, email, ip_hash, ok, request.headers.get("user-agent"))
    if not ok:
        raise HTTPException(status_code=401, detail="invalid admin credentials")

    token = secrets.token_urlsafe(32)
    expires = _utcnow() + timedelta(days=ADMIN_SESSION_DAYS)
    session = AdminSession(
        id=str(uuid.uuid4()),
        email=ADMIN_EMAIL,
        token_hash=_hash_token(token),
        expires_at=expires,
        ip_hash=ip_hash,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session)
    db.commit()
    response.set_cookie(
        ADMIN_COOKIE_NAME,
        token,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        max_age=ADMIN_SESSION_DAYS * 24 * 60 * 60,
        path="/",
    )
    return {"ok": True, "email": ADMIN_EMAIL, "expires_at": expires.isoformat()}


@router.post("/v1/admin/logout")
def admin_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    admin_cookie: Optional[str] = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
):
    if admin_cookie and _table_exists(db, "admin_sessions"):
        session = db.query(AdminSession).filter(AdminSession.token_hash == _hash_token(admin_cookie)).first()
        if session:
            session.revoked_at = _utcnow()
            db.commit()
    response.delete_cookie(ADMIN_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/v1/admin/me")
def admin_me(session: AdminSession = Depends(require_admin)):
    return {"email": session.email, "expires_at": _safe_datetime(session.expires_at)}


class ProvenanceReviewUpdate(BaseModel):
    verification_state: Optional[str] = None
    rights_status: Optional[str] = None
    presentation_eligible: Optional[bool] = None
    recognition_eligible: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("verification_state")
    @classmethod
    def valid_verification(cls, value):
        if value is not None and value not in {"UNKNOWN", "DECLARED_BY_SOURCE", "VERIFIED", "RESTRICTED"}:
            raise ValueError("invalid verification state")
        return value

    @field_validator("rights_status")
    @classmethod
    def valid_rights(cls, value):
        if value is not None and value not in {"UNKNOWN", "LICENSED", "VERIFIED_PUBLIC_DOMAIN", "RESTRICTED"}:
            raise ValueError("invalid rights status")
        return value


def _media_review_dict(row: MediaAsset, db: Session | None = None) -> dict:
    result = {key: getattr(row, key) for key in (
        "id", "provider_id", "artwork_id", "institution_holding_id", "source_record_id",
        "purpose", "original_url", "rights_status", "verification_state", "license_code",
        "attribution", "presentation_eligible", "recognition_eligible", "reviewed_by",
    )}
    if db is not None:
        edges = db.query(MediaAssetAssociation).filter(MediaAssetAssociation.media_asset_id == row.id, MediaAssetAssociation.active.is_(True)).all()
        result["linked_objects_count"] = len({edge.cultural_object_id for edge in edges if edge.cultural_object_id})
        result["linked_holdings_count"] = len({edge.institution_holding_id for edge in edges if edge.institution_holding_id})
        result["relationship_roles"] = sorted({edge.relationship_role for edge in edges})
        result["associations"] = [{"id": edge.id, "target_scope": edge.target_scope, "cultural_object_id": edge.cultural_object_id, "institution_holding_id": edge.institution_holding_id, "source_record_id": edge.source_record_id, "relationship_role": edge.relationship_role, "presentation_eligible": edge.presentation_eligible, "recognition_eligible": edge.recognition_eligible} for edge in edges]
    return result


@router.get("/v1/admin/provenance")
def admin_provenance_queue(
    institution_id: Optional[str] = None, provider_id: Optional[str] = None,
    verification_state: Optional[str] = None, rights_status: Optional[str] = None,
    presentation_eligible: Optional[bool] = None, recognition_eligible: Optional[bool] = None,
    no_usable_media: bool = False, limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db), _: AdminSession = Depends(require_admin),
):
    query = db.query(MediaAsset)
    if institution_id:
        associated_ids = db.query(MediaAssetAssociation.media_asset_id).outerjoin(
            InstitutionHolding, InstitutionHolding.id == MediaAssetAssociation.institution_holding_id
        ).filter(MediaAssetAssociation.active.is_(True), or_(
            InstitutionHolding.institution_id == institution_id,
            MediaAssetAssociation.cultural_object_id.in_(db.query(Artwork.cultural_object_id).filter(Artwork.museum_id == institution_id)),
        ))
        query = query.filter(or_(MediaAsset.id.in_(associated_ids), MediaAsset.artwork_id.in_(db.query(Artwork.id).filter(Artwork.museum_id == institution_id))))
    if provider_id: query = query.filter(MediaAsset.provider_id == provider_id)
    if verification_state: query = query.filter(MediaAsset.verification_state == verification_state)
    if rights_status: query = query.filter(MediaAsset.rights_status == rights_status)
    if presentation_eligible is not None: query = query.filter(MediaAsset.presentation_eligible.is_(presentation_eligible))
    if recognition_eligible is not None: query = query.filter(MediaAsset.recognition_eligible.is_(recognition_eligible))
    if no_usable_media: query = query.filter(MediaAsset.presentation_eligible.isnot(True), MediaAsset.recognition_eligible.isnot(True))
    rows = query.order_by(MediaAsset.created_at.asc()).limit(limit).all()
    return {"items": [_media_review_dict(row, db) for row in rows], "returned": len(rows)}


@router.patch("/v1/admin/provenance/{media_asset_id}")
def admin_review_provenance(
    media_asset_id: str, payload: ProvenanceReviewUpdate,
    db: Session = Depends(get_db), admin: AdminSession = Depends(require_admin),
):
    row = db.get(MediaAsset, media_asset_id)
    if row is None: raise HTTPException(status_code=404, detail="media asset not found")
    before = _media_review_dict(row)
    for field in ("verification_state", "rights_status"):
        value = getattr(payload, field)
        if value is not None: setattr(row, field, value)
    if row.rights_status == "RESTRICTED" or row.verification_state == "RESTRICTED":
        row.presentation_eligible = False
        row.recognition_eligible = False
    else:
        for field in ("presentation_eligible", "recognition_eligible"):
            value = getattr(payload, field)
            if value is not None: setattr(row, field, value)
        if (row.presentation_eligible is True or row.recognition_eligible is True) and row.verification_state != "VERIFIED":
            raise HTTPException(status_code=409, detail="eligibility requires explicit VERIFIED provenance")
        if (row.presentation_eligible is True or row.recognition_eligible is True) and row.rights_status not in {"LICENSED", "VERIFIED_PUBLIC_DOMAIN"}:
            raise HTTPException(status_code=409, detail="eligibility requires reviewed usable rights")
    row.reviewed_by, row.reviewed_at, row.review_notes = admin.email, _utcnow(), payload.notes
    after = _media_review_dict(row)
    db.add(MediaProvenanceReview(media_asset_id=row.id, actor=admin.email, action="REVIEW", before_state=before, after_state=after, notes=payload.notes))
    db.commit()
    return {"ok": True, "asset": after}


@router.post("/v1/events")
def ingest_product_event(
    payload: ProductEventIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    if not _table_exists(db, "product_events"):
        return {"ok": False, "stored": False, "reason": "schema_missing"}
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > EVENT_BODY_MAX_BYTES:
        raise HTTPException(status_code=413, detail="event payload too large")
    if payload.user_id is not None:
        raise HTTPException(status_code=400, detail="user_id is server-derived and must not be supplied")
    _enforce_event_rate_limit(request, payload.anonymous_id)
    if db.query(ProductEvent).filter(ProductEvent.event_id == payload.event_id).first():
        return {"ok": True, "stored": False, "duplicate": True}
    now = _utcnow()
    client_time = payload.client_occurred_at or payload.occurred_at
    if client_time is not None:
        client_time = _as_aware(client_time)
        if abs((client_time - now).total_seconds()) > 86400:
            client_time = None
    institution = db.get(Museum, payload.museum_id) if payload.museum_id else None
    if payload.museum_id and (institution is None or not institution.active):
        raise HTTPException(status_code=422, detail="unknown or inactive institution")
    properties = dict(payload.properties or {})
    # These fields are never trusted from a public payload.
    properties.pop("internal_test", None)
    properties.pop("user_id", None)
    result_type = properties.get("result_type")
    artwork = db.get(Artwork, payload.artwork_id) if payload.artwork_id else None
    if payload.artwork_id and artwork is None and payload.event_name in ARTWORK_DIMENSION_EVENTS and result_type != "uncataloged":
        raise HTTPException(status_code=422, detail="unknown artwork")
    artwork_id = artwork.id if artwork is not None else None
    if artwork is not None and institution is not None and artwork.museum_id != institution.id:
        raise HTTPException(status_code=422, detail="artwork does not belong to institution")
    internal_test = _trusted_internal_request(request)
    _link_analytics_identity(db, payload.anonymous_id, current_user)
    _validate_analytics_session(db, payload.session_id, payload.anonymous_id, current_user)
    schema_v2 = payload.schema_version == EVENT_SCHEMA_VERSION
    db.add(
        ProductEvent(
            event_id=payload.event_id,
            event_name=payload.event_name,
            occurred_at=now,
            client_occurred_at=client_time,
            server_received_at=now,
            schema_version=payload.schema_version,
            user_id=str(current_user.id) if current_user else None,
            anonymous_id=(payload.anonymous_id or None),
            session_id=(payload.session_id or None),
            museum_id=institution.id if institution else None,
            artwork_id=artwork_id,
            recognition_attempt_id=payload.recognition_attempt_id,
            properties=properties,
            source=payload.source or _extract_prop(properties, "source"),
            referrer=payload.referrer,
            utm_source=payload.utm_source,
            utm_medium=payload.utm_medium,
            utm_campaign=payload.utm_campaign,
            utm_content=payload.utm_content,
            language=payload.language or request.headers.get("accept-language", "")[:80],
            device_type=payload.device_type,
            os=payload.os,
            browser=payload.browser,
            user_agent=request.headers.get("user-agent"),
            path=payload.path,
            internal_test=internal_test,
            trust_level="CLIENT_VALIDATED_V2" if schema_v2 else "CLIENT_VALIDATED_LEGACY",
            business_eligible=bool(schema_v2 and payload.anonymous_id),
        )
    )
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        return {"ok": False, "stored": False}
    return {"ok": True, "stored": True, "schema_version": payload.schema_version, "internal_test": internal_test}


def record_product_event_from_server(event_name: str, properties: Optional[dict] = None) -> None:
    if SessionLocal is None:
        return
    db = SessionLocal()
    try:
        if not _table_exists(db, "product_events"):
            return
        props = properties or {}
        db.add(
            ProductEvent(
                event_id=str(uuid.uuid4()),
                event_name=event_name[:120],
                occurred_at=_utcnow(),
                museum_id=props.get("museum_id"),
                artwork_id=props.get("resolved_artwork_id") or props.get("artwork_id"),
                recognition_attempt_id=props.get("recognition_attempt_id"),
                properties=props,
                schema_version=EVENT_SCHEMA_VERSION,
                server_received_at=_utcnow(),
                internal_test=bool(props.get("internal_test", False)),
                trust_level="SERVER_OPERATIONAL",
                business_eligible=False,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _meaningful_activity_by_identity(
    db: Session,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> Dict[str, List[datetime]]:
    end = end or _utcnow()
    rows: Dict[str, List[datetime]] = defaultdict(list)
    if _table_exists(db, "product_events"):
        for identity, occurred_at in (
            _event_base_query(db, start, end)
            .filter(_identity_expr().isnot(None), ProductEvent.event_name.in_(list(MEANINGFUL_CLIENT_EVENTS)))
            .with_entities(_identity_expr(), ProductEvent.occurred_at)
            .all()
        ):
            rows[str(identity)].append(_as_aware(occurred_at))
    if _table_exists(db, "recognition_attempts"):
        for identity, completed_at in (
            _attempt_base_query(db, start, end)
            .filter(_attempt_identity_expr().isnot(None))
            .with_entities(_attempt_identity_expr(), RecognitionAttempt.completed_at)
            .all()
        ):
            rows[str(identity)].append(_as_aware(completed_at))
    return rows


def _basic_user_metrics(db: Session, start: Optional[datetime], end: datetime, prev_start: Optional[datetime], prev_end: Optional[datetime]) -> Dict[str, Any]:
    registered_total = int(db.query(User).count())
    current_activity = _meaningful_activity_by_identity(db, start, end)
    previous_activity = _meaningful_activity_by_identity(db, prev_start, prev_end) if prev_start and prev_end else {}
    all_activity = _meaningful_activity_by_identity(db)
    active = len(current_activity)
    previous_active = len(previous_activity)
    linked_anonymous = {row.anonymous_id for row in db.query(AnalyticsIdentityLink).all()} if _table_exists(db, "analytics_identity_links") else set()
    anonymous_ids = set()
    if _table_exists(db, "product_events"):
        anonymous_ids.update(value for (value,) in _event_base_query(db, start, end).filter(ProductEvent.anonymous_id.isnot(None)).with_entities(ProductEvent.anonymous_id).distinct().all())
    anonymous = len(anonymous_ids - linked_anonymous)
    activated = _activated_identity_count(db, start, end)
    session_ids = set()
    if _table_exists(db, "product_events"):
        session_ids.update(value for (value,) in _event_base_query(db, start, end).filter(ProductEvent.session_id.isnot(None)).with_entities(ProductEvent.session_id).distinct().all())
    if _table_exists(db, "recognition_attempts"):
        session_ids.update(value for (value,) in _attempt_base_query(db, start, end).filter(RecognitionAttempt.session_id.isnot(None), _attempt_identity_expr().isnot(None)).with_entities(RecognitionAttempt.session_id).distinct().all())
    sessions = len(session_ids)
    returning = _returning_user_count(db, start, end)
    first_seen = {identity: min(times) for identity, times in all_activity.items() if times}
    new_users = sum(1 for seen in first_seen.values() if (start is None or seen >= start) and seen < end)
    total_users = len(set(all_activity) | {str(user_id) for (user_id,) in db.query(User.id).all()})
    return {
        "total_users": total_users,
        "registered_users": registered_total,
        "anonymous_visitors": anonymous,
        "new_users": new_users,
        "active_users": _with_delta(active, previous_active),
        "activated_users": activated,
        "activation_rate": round((activated / new_users) * 100, 1) if new_users else None,
        "returning_users": returning,
        "returning_user_pct": round((returning / active) * 100, 1) if active else None,
        "sessions": sessions,
        "sessions_per_active_user": round(sessions / active, 2) if active else None,
        "dau": _active_since(db, timedelta(days=1)),
        "wau": _active_since(db, timedelta(days=7)),
        "mau": _active_since(db, timedelta(days=30)),
        "dau_mau": round(_active_since(db, timedelta(days=1)) / _active_since(db, timedelta(days=30)), 3) if _active_since(db, timedelta(days=30)) else None,
    }


def _active_since(db: Session, delta: timedelta) -> int:
    return len(_meaningful_activity_by_identity(db, _utcnow() - delta, _utcnow()))


def _returning_user_count(db: Session, start: Optional[datetime], end: datetime) -> int:
    current = set(_meaningful_activity_by_identity(db, start, end))
    all_activity = _meaningful_activity_by_identity(db)
    return sum(1 for identity in current if len({moment.date() for moment in all_activity.get(identity, [])}) > 1)


def _activated_identity_count(db: Session, start: Optional[datetime], end: datetime) -> int:
    if not _table_exists(db, "recognition_attempts"):
        return 0
    rows = (
        db.query(RecognitionAttempt)
        .filter(
            RecognitionAttempt.completed_at.isnot(None),
            RecognitionAttempt.internal_test.is_(False),
            RecognitionAttempt.terminal_outcome.in_(list(SUCCESSFUL_RECOGNITION_OUTCOMES)),
            _attempt_identity_expr().isnot(None),
        )
        .with_entities(_attempt_identity_expr(), func.min(RecognitionAttempt.completed_at))
        .group_by(_attempt_identity_expr())
        .all()
    )
    first_seen = {
        identity: min(times)
        for identity, times in _meaningful_activity_by_identity(db).items()
        if times
    }
    return sum(
        1
        for identity_raw, first_activation in rows
        if str(identity_raw) in first_seen
        and (start is None or first_seen[str(identity_raw)] >= start)
        and first_seen[str(identity_raw)] < end
        and (start is None or _as_aware(first_activation) >= start)
        and _as_aware(first_activation) < end
    )


def _successful_identity_count(db: Session, start: Optional[datetime], end: datetime) -> int:
    if not _table_exists(db, "recognition_attempts"):
        return 0
    return int(
        _attempt_base_query(db, start, end)
        .filter(_attempt_identity_expr().isnot(None), RecognitionAttempt.terminal_outcome.in_(list(SUCCESSFUL_RECOGNITION_OUTCOMES)))
        .with_entities(func.count(distinct(_attempt_identity_expr())))
        .scalar()
        or 0
    )


def _recognition_metrics(db: Session, start: Optional[datetime], end: datetime) -> Dict[str, Any]:
    if not _table_exists(db, "recognition_attempts"):
        return {"attempts": None, "successful": None, "failed": None, "success_rate": None, "data_available_since": TRUSTED_ANALYTICS_AVAILABLE_SINCE}
    kpi_outcomes = SUCCESSFUL_RECOGNITION_OUTCOMES | FAILED_RECOGNITION_OUTCOMES
    rows = _attempt_base_query(db, start, end).filter(
        _attempt_identity_expr().isnot(None),
        RecognitionAttempt.terminal_outcome.in_(list(kpi_outcomes)),
    ).all()
    attempts = len(rows)
    successes = sum(1 for row in rows if row.terminal_outcome in SUCCESSFUL_RECOGNITION_OUTCOMES)
    auto_accepted = sum(1 for row in rows if row.visitor_resolution == "AUTO_ACCEPTED")
    confirmation_required = sum(1 for row in rows if row.visitor_resolution == "CONFIRMATION_REQUIRED")
    generated_results = sum(1 for row in rows if row.visitor_resolution == "GENERATED_RESULT")
    failures = sum(1 for row in rows if row.terminal_outcome in FAILED_RECOGNITION_OUTCOMES)
    no_match = sum(1 for row in rows if row.terminal_outcome == "no_match")
    latencies = [float(row.latency_ms) for row in rows if row.latency_ms is not None]
    failure_reasons = Counter(row.terminal_outcome for row in rows if row.terminal_outcome in FAILED_RECOGNITION_OUTCOMES)
    confidence_buckets = Counter(_confidence_bucket(float(row.confidence)) for row in rows if row.confidence is not None)
    identityless_operational_events = int(_attempt_base_query(db, start, end).filter(_attempt_identity_expr().is_(None)).count())
    return {
        "attempts": attempts,
        "successful": successes,
        "auto_accepted": auto_accepted,
        "confirmation_required": confirmation_required,
        "generated_results": generated_results,
        "failed": failures,
        "unknown_no_match": no_match,
        "success_rate": round((successes / attempts) * 100, 1) if attempts else None,
        "latency_avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
        "confidence_buckets": dict(confidence_buckets),
        "failure_reasons": [{"reason": reason, "count": count} for reason, count in failure_reasons.most_common()],
        "historical_success_records": int(db.query(VisitArtwork).count()),
        "identityless_operational_events": identityless_operational_events,
        "visitor_metric_definition": "One non-internal, visitor-linked recognition_attempt row is one attempt. Engine success includes an auto-accepted catalog match, a catalog candidate requiring confirmation, or an uncataloged generated result; visitor_resolution reports those states separately. Companion raw events never add KPI attempts or successes.",
        "data_available_since": TRUSTED_ANALYTICS_AVAILABLE_SINCE,
    }


def _confidence_bucket(value: float) -> str:
    if value < 0.25:
        return "0-0.25"
    if value < 0.5:
        return "0.25-0.50"
    if value < 0.7:
        return "0.50-0.70"
    if value < 0.85:
        return "0.70-0.85"
    return "0.85+"


def _percentile(values: List[float], pct: int) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil((pct / 100) * len(ordered)) - 1))
    return round(ordered[idx], 1)


def _funnel(db: Session, start: Optional[datetime], end: datetime) -> Dict[str, Any]:
    rows = []
    first_count = None
    previous = None
    for event, label in FUNNEL_STAGES:
        if event == "recognition_started" and _table_exists(db, "recognition_attempts"):
            count = int(_attempt_base_query(db, start, end).filter(_attempt_identity_expr().isnot(None)).with_entities(func.count(distinct(_attempt_identity_expr()))).scalar() or 0)
        elif event == "scan_success":
            count = _successful_identity_count(db, start, end)
        else:
            count = _identity_count(db, start, end, {event})
        if first_count is None:
            first_count = count
        rows.append(
            {
                "event": event,
                "label": label,
                "users": count,
                "from_previous_pct": round((count / previous) * 100, 1) if previous else None,
                "from_start_pct": round((count / first_count) * 100, 1) if first_count else None,
            }
        )
        previous = count
    dropoffs = [
        {"from": rows[i - 1]["label"], "to": rows[i]["label"], "lost": rows[i - 1]["users"] - rows[i]["users"]}
        for i in range(1, len(rows))
    ]
    biggest = max(dropoffs, key=lambda x: x["lost"], default=None)
    return {"stages": rows, "biggest_dropoff": biggest, "trust": {"recognition_started": "SERVER_CONFIRMED", "scan_success": "SERVER_CONFIRMED", "other_stages": "CLIENT_VALIDATED"}}


def _retention(db: Session) -> Dict[str, Any]:
    activity = _meaningful_activity_by_identity(db)
    by_identity: Dict[str, List[date]] = {
        identity: sorted({moment.date() for moment in moments})
        for identity, moments in activity.items()
    }
    if not by_identity:
        return {"d1": None, "d7": None, "d30": None, "cohorts": [], "available_since": TRUSTED_ANALYTICS_AVAILABLE_SINCE}
    d1 = d7 = d30 = 0
    d1_eligible = d7_eligible = d30_eligible = 0
    today = _utcnow().date()
    cohorts: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"users": 0, "d1": 0, "d7": 0, "d30": 0, "d1e": 0, "d7e": 0, "d30e": 0})
    for days in by_identity.values():
        first = min(days)
        day_set = set(days)
        key = f"{first.isocalendar().year}-W{first.isocalendar().week:02d}"
        cohorts[key]["users"] += 1
        if first + timedelta(days=1) <= today:
            d1_eligible += 1
            cohorts[key]["d1e"] += 1
            if first + timedelta(days=1) in day_set:
                d1 += 1
                cohorts[key]["d1"] += 1
        if first + timedelta(days=7) <= today:
            d7_eligible += 1
            cohorts[key]["d7e"] += 1
            if first + timedelta(days=7) in day_set:
                d7 += 1
                cohorts[key]["d7"] += 1
        if first + timedelta(days=30) <= today:
            d30_eligible += 1
            cohorts[key]["d30e"] += 1
            if first + timedelta(days=30) in day_set:
                d30 += 1
                cohorts[key]["d30"] += 1
    total = len(by_identity)
    cohort_rows = []
    for cohort, data in sorted(cohorts.items(), reverse=True)[:12]:
        users = data["users"]
        cohort_rows.append({
            "cohort": cohort,
            "users": users,
            "d1": round(data["d1"] / data["d1e"] * 100, 1) if data["d1e"] else None,
            "d7": round(data["d7"] / data["d7e"] * 100, 1) if data["d7e"] else None,
            "d30": round(data["d30"] / data["d30e"] * 100, 1) if data["d30e"] else None,
        })
    return {
        "d1": round(d1 / d1_eligible * 100, 1) if d1_eligible else None,
        "d7": round(d7 / d7_eligible * 100, 1) if d7_eligible else None,
        "d30": round(d30 / d30_eligible * 100, 1) if d30_eligible else None,
        "eligible": {"d1": d1_eligible, "d7": d7_eligible, "d30": d30_eligible},
        "cohorts": cohort_rows,
        "available_since": TRUSTED_ANALYTICS_AVAILABLE_SINCE,
    }


def _catalog_health(db: Session) -> Dict[str, Any]:
    active_select = select(ArtworkCatalogMembership.artwork_id).where(ArtworkCatalogMembership.active.is_(True))
    active_total = int(db.query(ArtworkCatalogMembership).filter(ArtworkCatalogMembership.active.is_(True)).count())
    active_artworks = db.query(Artwork).filter(Artwork.id.in_(active_select))
    active_ids = {artwork_id for (artwork_id,) in db.query(ArtworkCatalogMembership.artwork_id).filter(ArtworkCatalogMembership.active.is_(True)).all()}
    presentation_ids = {
        artwork_id
        for (artwork_id,) in db.query(Artwork.id).filter(Artwork.id.in_(active_select), Artwork.image_url.isnot(None), Artwork.image_url != "").all()
    }
    ra_rows = (
        db.query(RecognitionAsset.artwork_id, RecognitionAsset.source_url, RecognitionAsset.local_storage_status)
        .join(ArtworkCatalogMembership, ArtworkCatalogMembership.artwork_id == RecognitionAsset.artwork_id)
        .filter(ArtworkCatalogMembership.active.is_(True))
        .all()
    )
    recognition_asset_ids = {artwork_id for artwork_id, _source_url, _storage in ra_rows}
    recognition_asset_source_ids = {artwork_id for artwork_id, source_url, _storage in ra_rows if source_url}
    local_cache_ids = {
        artwork_id
        for artwork_id, _source_url, storage in ra_rows
        if (storage or "").lower() in {"cached", "downloaded", "local"}
    }
    louvre_rows = (
        db.query(LouvreImageReference.artwork_id, LouvreImageReference.url_image, LouvreImageReference.url_thumbnail, LouvreImageReference.fetched)
        .join(ArtworkCatalogMembership, ArtworkCatalogMembership.artwork_id == LouvreImageReference.artwork_id)
        .filter(ArtworkCatalogMembership.active.is_(True))
        .all()
    )
    louvre_reference_ids = {artwork_id for artwork_id, url_image, url_thumbnail, _fetched in louvre_rows if url_image or url_thumbnail}
    louvre_fetched_ids = {artwork_id for artwork_id, _url_image, _url_thumbnail, fetched in louvre_rows if fetched}
    with_assets = len(recognition_asset_ids)
    status_counts = {
        (status or "UNKNOWN"): int(count)
        for status, count in (
            db.query(Artwork.recognition_status, func.count(distinct(Artwork.id)))
            .filter(Artwork.id.in_(active_select))
            .group_by(Artwork.recognition_status)
            .all()
        )
    }
    vision_plus_asset = int(status_counts.get("VISION_PLUS_ASSET", with_assets))
    vision_ready = int(status_counts.get("VISION_READY", max(0, active_total - with_assets)))
    not_ready_statuses = {"INSUFFICIENT", "NOT_READY", "NO_USABLE_ASSET", "RIGHTS_RESTRICTED"}
    not_ready = int(
        active_artworks.filter(or_(Artwork.metadata_status.in_(["INSUFFICIENT", "NOT_READY"]), Artwork.recognition_status.in_(list(not_ready_statuses)))).count()
    )
    missing_images = int(active_artworks.filter(or_(Artwork.image_url.is_(None), Artwork.image_url == "")).count())
    missing_metadata = int(active_artworks.filter(or_(Artwork.title_original.is_(None), Artwork.title_original == "")).count())
    any_reference_ids = presentation_ids | recognition_asset_source_ids | louvre_reference_ids
    local_image_ids = local_cache_ids | louvre_fetched_ids
    louvre_active = int(db.query(ArtworkCatalogMembership).filter(ArtworkCatalogMembership.active.is_(True), ArtworkCatalogMembership.museum_id == "louvre").count())
    louvre_total = int(db.query(Artwork).filter(Artwork.museum_id == "louvre").count())
    active_artwork_rows = db.query(Artwork.id, Artwork.cultural_object_id, Artwork.institution_holding_id).filter(Artwork.id.in_(active_ids)).all() if active_ids else []
    object_to_artwork = {object_id: artwork_id for artwork_id, object_id, _holding_id in active_artwork_rows if object_id}
    holding_to_artwork = {holding_id: artwork_id for artwork_id, _object_id, holding_id in active_artwork_rows if holding_id}
    associated_media = db.query(MediaAssetAssociation, MediaAsset).join(
        MediaAsset, MediaAsset.id == MediaAssetAssociation.media_asset_id
    ).filter(MediaAssetAssociation.active.is_(True), or_(
        MediaAssetAssociation.cultural_object_id.in_(list(object_to_artwork)),
        MediaAssetAssociation.institution_holding_id.in_(list(holding_to_artwork)),
    )).all() if active_ids else []
    def associated_artwork_id(edge):
        return holding_to_artwork.get(edge.institution_holding_id) or object_to_artwork.get(edge.cultural_object_id)
    legacy_media = db.query(MediaAsset).filter(MediaAsset.artwork_id.in_(active_ids)).all() if active_ids else []
    media_facts = [(associated_artwork_id(edge), asset, edge) for edge, asset in associated_media]
    media_facts.extend((asset.artwork_id, asset, None) for asset in legacy_media if not any(edge.media_asset_id == asset.id for edge, _linked in associated_media))
    provenance_verified_ids = {artwork_id for artwork_id, asset, _edge in media_facts if artwork_id and asset.verification_state == "VERIFIED"}
    provenance_partial_ids = {artwork_id for artwork_id, asset, _edge in media_facts if artwork_id and asset.verification_state == "DECLARED_BY_SOURCE"} - provenance_verified_ids
    provenance_unknown_ids = active_ids - provenance_verified_ids - provenance_partial_ids
    rights_restricted_ids = {artwork_id for artwork_id, asset, _edge in media_facts if artwork_id and asset.rights_status == "RESTRICTED"}
    usable_reference_ids = {artwork_id for artwork_id, asset, edge in media_facts if artwork_id and (edge.relationship_role if edge else asset.purpose) in {"REFERENCE", "RECOGNITION_ASSET", "SOURCE_ORIGINAL"} and (asset.original_url or asset.asset_url) and asset.rights_status != "RESTRICTED"}
    return {
        "knowledge_catalog_total": int(db.query(Artwork).count()),
        "active_visitor_catalog_total": active_total,
        "vision_plus_asset": vision_plus_asset,
        "vision_ready": vision_ready,
        "not_ready": not_ready,
        "recognition_status_counts": status_counts,
        "active_works": active_total,
        "inactive_works": max(0, int(db.query(Artwork).count()) - active_total),
        "works_missing_images": missing_images,
        "works_missing_presentation_images": missing_images,
        "works_missing_metadata": missing_metadata,
        "works_with_recognition_assets": with_assets,
        "works_missing_recognition_assets": max(0, active_total - with_assets),
        "works_with_presentation_images": len(presentation_ids),
        "works_with_source_or_reference_images": len(any_reference_ids),
        "works_missing_any_image_reference": len(active_ids - any_reference_ids),
        "works_with_louvre_image_references": len(louvre_reference_ids),
        "works_with_local_cached_source_images": len(local_image_ids),
        "works_missing_local_cached_source_images": len(active_ids - local_image_ids),
        "works_with_remote_or_reference_images_but_no_local_cache": len(any_reference_ids - local_image_ids),
        "recognition_asset_exists_presentation_missing": len(recognition_asset_ids - presentation_ids),
        "presentation_exists_recognition_asset_missing": len(presentation_ids - recognition_asset_ids),
        "both_presentation_and_recognition_asset_missing": len(active_ids - (presentation_ids | recognition_asset_ids)),
        "provenance_verified": len(provenance_verified_ids),
        "provenance_partial": len(provenance_partial_ids),
        "provenance_unknown": len(provenance_unknown_ids),
        "rights_restricted": len(rights_restricted_ids),
        "no_usable_source_media": len(active_ids - usable_reference_ids),
        "louvre": {
            "knowledge_catalog": louvre_total,
            "active_visitor_catalog": louvre_active,
        },
    }


def _museum_rows(db: Session, start: Optional[datetime], end: datetime, limit: int = 50) -> List[Dict[str, Any]]:
    catalog_counts = dict(
        db.query(ArtworkCatalogMembership.museum_id, func.count(ArtworkCatalogMembership.id))
        .filter(ArtworkCatalogMembership.active.is_(True))
        .group_by(ArtworkCatalogMembership.museum_id)
        .all()
    )
    museums = db.query(Museum).order_by(Museum.experience_level.desc(), Museum.name.asc()).limit(limit).all()
    rows = []
    for museum in museums:
        attempts_query = _attempt_base_query(db, start, end).filter(RecognitionAttempt.institution_id == museum.id, _attempt_identity_expr().isnot(None)) if _table_exists(db, "recognition_attempts") else None
        scans = int(attempts_query.count()) if attempts_query is not None else 0
        success = int(attempts_query.filter(RecognitionAttempt.terminal_outcome.in_(list(SUCCESSFUL_RECOGNITION_OUTCOMES))).count()) if attempts_query is not None else 0
        visitors = _identity_count_for_museum(db, start, end, museum.id)
        rows.append({
            "id": museum.id,
            "name": museum.name,
            "city": museum.city,
            "experience_level": museum.experience_level,
            "catalog_size": int(catalog_counts.get(museum.id, 0)),
            "unique_visitors": visitors,
            "sessions": _session_count_for_museum(db, start, end, museum.id),
            "scans": scans,
            "successful_recognitions": success,
            "success_rate": round(success / scans * 100, 1) if scans else None,
            "scans_per_user": round(scans / visitors, 2) if visitors else None,
        })
    return rows


def _event_count_for_museum(db: Session, start: Optional[datetime], end: datetime, museum_id: str, events: Iterable[str]) -> int:
    if not _table_exists(db, "product_events"):
        return 0
    return int(_identified_event_query(db, start, end).filter(ProductEvent.event_name.in_(list(events)), ProductEvent.museum_id == museum_id).count())


def _identity_count_for_museum(db: Session, start: Optional[datetime], end: datetime, museum_id: str) -> int:
    identities = set()
    if _table_exists(db, "product_events"):
        identities.update(str(value) for (value,) in _event_base_query(db, start, end).filter(ProductEvent.museum_id == museum_id, _identity_expr().isnot(None)).with_entities(_identity_expr()).distinct().all())
    if _table_exists(db, "recognition_attempts"):
        identities.update(str(value) for (value,) in _attempt_base_query(db, start, end).filter(RecognitionAttempt.institution_id == museum_id, _attempt_identity_expr().isnot(None)).with_entities(_attempt_identity_expr()).distinct().all())
    return len(identities)


def _session_count_for_museum(db: Session, start: Optional[datetime], end: datetime, museum_id: str) -> int:
    sessions = set()
    if _table_exists(db, "product_events"):
        sessions.update(value for (value,) in _event_base_query(db, start, end).filter(ProductEvent.museum_id == museum_id, ProductEvent.session_id.isnot(None)).with_entities(ProductEvent.session_id).distinct().all())
    if _table_exists(db, "recognition_attempts"):
        sessions.update(value for (value,) in _attempt_base_query(db, start, end).filter(RecognitionAttempt.institution_id == museum_id, RecognitionAttempt.session_id.isnot(None), _attempt_identity_expr().isnot(None)).with_entities(RecognitionAttempt.session_id).distinct().all())
    return len(sessions)


def _top_artworks(db: Session, start: Optional[datetime], end: datetime, limit: int = 20) -> List[Dict[str, Any]]:
    event_counts = Counter()
    if _table_exists(db, "recognition_attempts"):
        rows = (
            _attempt_base_query(db, start, end)
            .filter(RecognitionAttempt.artwork_id.isnot(None), RecognitionAttempt.terminal_outcome == "success", _attempt_identity_expr().isnot(None))
            .with_entities(RecognitionAttempt.artwork_id, func.count(RecognitionAttempt.recognition_attempt_id))
            .group_by(RecognitionAttempt.artwork_id)
            .order_by(desc(func.count(RecognitionAttempt.recognition_attempt_id)))
            .limit(limit)
            .all()
        )
        event_counts.update({artwork_id: int(count) for artwork_id, count in rows})
    artworks = {a.id: a for a in db.query(Artwork).filter(Artwork.id.in_(list(event_counts.keys()))).all()} if event_counts else {}
    return [
        {
            "artwork_id": artwork_id,
            "title": artworks.get(artwork_id).title_original if artworks.get(artwork_id) else artwork_id,
            "artist": artworks.get(artwork_id).artist if artworks.get(artwork_id) else None,
            "museum_id": artworks.get(artwork_id).museum_id if artworks.get(artwork_id) else None,
            "events": count,
        }
        for artwork_id, count in event_counts.most_common(limit)
    ]


def _acquisition(db: Session, start: Optional[datetime], end: datetime) -> Dict[str, Any]:
    if not _table_exists(db, "product_events"):
        return {"sources": [], "utm": []}
    source_expr = func.coalesce(ProductEvent.utm_source, ProductEvent.source, "direct")
    sources = (
        _event_base_query(db, start, end)
        .filter(_identity_expr().isnot(None))
        .with_entities(source_expr.label("source"), func.count(distinct(_identity_expr())).label("users"))
        .group_by(source_expr)
        .order_by(desc("users"))
        .limit(25)
        .all()
    )
    return {"sources": [{"source": source, "users": int(users)} for source, users in sources]}


def _segments(db: Session, start: Optional[datetime], end: datetime) -> Dict[str, Any]:
    if not _table_exists(db, "product_events"):
        return {"devices": [], "os": [], "browsers": [], "languages": [], "countries": []}
    def grouped(column):
        return [
            {"label": label or "unknown", "events": int(count)}
            for label, count in _identified_event_query(db, start, end).with_entities(column, func.count(ProductEvent.event_id)).group_by(column).order_by(desc(func.count(ProductEvent.event_id))).limit(15).all()
        ]
    return {
        "devices": grouped(ProductEvent.device_type),
        "os": grouped(ProductEvent.os),
        "browsers": grouped(ProductEvent.browser),
        "languages": grouped(ProductEvent.language),
        "countries": grouped(ProductEvent.country),
    }


def _system(db: Session) -> Dict[str, Any]:
    latest_recognition = None
    if _table_exists(db, "recognition_attempts"):
        row = db.query(RecognitionAttempt).filter(RecognitionAttempt.terminal_outcome.in_(list(SUCCESSFUL_RECOGNITION_OUTCOMES))).order_by(RecognitionAttempt.completed_at.desc()).first()
        latest_recognition = _safe_datetime(row.completed_at) if row else None
    configured_institutions = int(db.query(InstitutionProfile).filter(InstitutionProfile.active.is_(True)).count()) if _table_exists(db, "institution_profiles") else 0
    unconfigured_institutions = int(
        db.query(Museum).filter(Museum.active.is_(True), ~Museum.id.in_(select(InstitutionProfile.institution_id))).count()
    ) if _table_exists(db, "institution_profiles") else int(db.query(Museum).count())
    return {
        "api_status": "ok",
        "db_status": "ok",
        "frontend_release": os.environ.get("FRONTEND_GIT_SHA"),
        "backend_release": os.environ.get("GIT_COMMIT_SHA") or os.environ.get("FLY_IMAGE_REF") or os.environ.get("RENDER_GIT_COMMIT"),
        "build_timestamp": os.environ.get("BUILD_TIMESTAMP"),
        "deployment_environment": os.environ.get("DEPLOYMENT_ENV", "unknown"),
        "migration_head": _migration_head(db),
        "countries": int(db.query(Country).count()) if _table_exists(db, "countries") else 0,
        "institutions": int(db.query(Museum).filter(Museum.active.is_(True)).count()),
        "configured_institutions": configured_institutions,
        "unconfigured_institutions": unconfigured_institutions,
        "latest_successful_recognition": latest_recognition,
        "tracking_available_since": TRACKING_AVAILABLE_SINCE,
        "trusted_analytics_available_since": TRUSTED_ANALYTICS_AVAILABLE_SINCE,
    }


def _migration_head(db: Session) -> Optional[str]:
    if not _table_exists(db, "schema_migrations"):
        return None
    return db.execute(text("SELECT migration_id FROM schema_migrations ORDER BY migration_id DESC LIMIT 1")).scalar()


def _data_gaps(db: Session) -> List[str]:
    gaps = []
    if not _table_exists(db, "product_events"):
        gaps.append("First-party product_events table is not installed; anonymous funnel, retention and recognition attempt history cannot be calculated.")
    elif int(db.query(ProductEvent).count()) == 0:
        gaps.append("First-party product event history begins with this admin deployment; older anonymous funnel and retention metrics are unavailable.")
    gaps.append(f"Trusted business metrics begin at schema v2 rollout ({TRUSTED_ANALYTICS_AVAILABLE_SINCE}); legacy product_events remain raw/unverified and are not reinterpreted.")
    gaps.append("City/country analytics are only shown when privacy-safe request metadata or client properties exist; no GPS collection is used.")
    return gaps


@router.get("/v1/admin/dashboard")
def admin_dashboard(period: str = Query("30d"), db: Session = Depends(get_db), _: AdminSession = Depends(require_admin)):
    start, end, prev_start, prev_end, period_key = _period_bounds(period)
    return {
        "period": {"key": period_key, "start": _safe_datetime(start), "end": _safe_datetime(end), "previous_start": _safe_datetime(prev_start), "previous_end": _safe_datetime(prev_end)},
        "users": _basic_user_metrics(db, start, end, prev_start, prev_end),
        "activation": _activation(db, start, end),
        "funnel": _funnel(db, start, end),
        "retention": _retention(db),
        "recognition": _recognition_metrics(db, start, end),
        "catalog": _catalog_health(db),
        "museums": _museum_rows(db, start, end, limit=30),
        "top_artworks": _top_artworks(db, start, end),
        "acquisition": _acquisition(db, start, end),
        "segments": _segments(db, start, end),
        "system": _system(db),
        "data_gaps": _data_gaps(db),
        "updated_at": _utcnow().isoformat(),
    }


def _activation(db: Session, start: Optional[datetime], end: datetime) -> Dict[str, Any]:
    all_activity = _meaningful_activity_by_identity(db)
    first_seen = {identity: min(times) for identity, times in all_activity.items() if times}
    new_users = sum(1 for seen in first_seen.values() if (start is None or seen >= start) and seen < end)
    activated = _activated_identity_count(db, start, end)
    median_time = None
    scans_before_first = None
    if _table_exists(db, "recognition_attempts"):
        rows = (
            _attempt_base_query(db, start, end)
            .filter(_attempt_identity_expr().isnot(None))
            .with_entities(_attempt_identity_expr(), RecognitionAttempt.completed_at, RecognitionAttempt.terminal_outcome)
            .order_by(RecognitionAttempt.completed_at.asc())
            .all()
        )
        first_success: Dict[str, datetime] = {}
        scans: Dict[str, int] = defaultdict(int)
        for identity_raw, completed_at, outcome in rows:
            identity = str(identity_raw)
            if identity not in first_seen or (start is not None and first_seen[identity] < start):
                continue
            if identity in first_success:
                continue
            scans[identity] += 1
            if outcome in SUCCESSFUL_RECOGNITION_OUTCOMES:
                first_success[identity] = _as_aware(completed_at)
        deltas = [(first_success[i] - first_seen[i]).total_seconds() for i in first_success if i in first_seen]
        median_time = _percentile(deltas, 50) if deltas else None
        scan_counts = [scans[i] for i in first_success]
        scans_before_first = _percentile([float(x) for x in scan_counts], 50) if scan_counts else None
    return {
        "new_users": new_users,
        "activated_users": activated,
        "activation_rate": round(activated / new_users * 100, 1) if new_users else None,
        "median_time_to_activation_seconds": median_time,
        "median_scans_before_first_success": scans_before_first,
    }


@router.get("/v1/admin/recognition/failures")
def admin_recognition_failures(
    period: str = Query("30d"),
    museum: Optional[str] = None,
    reason: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: AdminSession = Depends(require_admin),
):
    start, end, *_ = _period_bounds(period)
    if not _table_exists(db, "recognition_attempts"):
        return {"rows": [], "total": 0, "data_gap": "trusted recognition attempts are not installed"}
    query = _attempt_base_query(db, start, end).filter(RecognitionAttempt.terminal_outcome.in_(list(FAILED_RECOGNITION_OUTCOMES)))
    if museum:
        query = query.filter(RecognitionAttempt.institution_id == museum)
    if reason:
        query = query.filter(RecognitionAttempt.terminal_outcome == reason)
    rows = []
    for event in query.order_by(RecognitionAttempt.completed_at.desc()).offset(offset).limit(limit).all():
        rows.append({
            "timestamp": _safe_datetime(event.completed_at),
            "user": event.user_id or event.anonymous_id,
            "session_id": event.session_id,
            "museum_id": event.institution_id,
            "top_candidate": event.artwork_id,
            "confidence": event.confidence,
            "failure_reason": event.terminal_outcome,
            "latency_ms": event.latency_ms,
            "pipeline": event.recognition_mode,
            "status": event.response_status or event.terminal_outcome,
            "recognition_attempt_id": event.recognition_attempt_id,
        })
    return {"rows": rows, "total": query.count(), "images_available": False}


@router.get("/v1/admin/users")
def admin_users(
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: AdminSession = Depends(require_admin),
):
    rows = []
    registered = db.query(User)
    if q:
        registered = registered.filter(or_(User.email.ilike(f"%{q}%"), func.cast(User.id, String).ilike(f"%{q}%")))
    for user in registered.order_by(User.created_at.desc()).offset(offset).limit(limit).all():
        rows.append({
            "id": str(user.id),
            "email": user.email,
            "type": "registered",
            "first_seen": _safe_datetime(user.created_at),
            "last_seen": _safe_datetime(_latest_user_event(db, str(user.id))),
            "sessions": int(db.query(Visit).filter(Visit.user_id == user.id).count()),
            "scans": int(db.query(VisitArtwork).join(Visit, Visit.id == VisitArtwork.visit_id).filter(Visit.user_id == user.id).count()),
        })
    if _table_exists(db, "product_events") and len(rows) < limit:
        anon_rows = (
            db.query(ProductEvent.anonymous_id, func.min(ProductEvent.occurred_at), func.max(ProductEvent.occurred_at), func.count(distinct(ProductEvent.session_id)))
            .filter(ProductEvent.anonymous_id.isnot(None), ProductEvent.user_id.is_(None))
            .group_by(ProductEvent.anonymous_id)
            .order_by(desc(func.max(ProductEvent.occurred_at)))
            .limit(limit - len(rows))
            .all()
        )
        for anon_id, first_seen, last_seen, sessions in anon_rows:
            rows.append({"id": anon_id, "email": None, "type": "anonymous", "first_seen": _safe_datetime(first_seen), "last_seen": _safe_datetime(last_seen), "sessions": int(sessions or 0)})
    return {"rows": rows, "limit": limit, "offset": offset}


def _latest_user_event(db: Session, user_id: str) -> Optional[datetime]:
    if not _table_exists(db, "product_events"):
        return None
    row = db.query(ProductEvent).filter(ProductEvent.user_id == user_id).order_by(ProductEvent.occurred_at.desc()).first()
    return row.occurred_at if row else None


@router.get("/v1/admin/users/{identity}")
def admin_user_detail(identity: str, db: Session = Depends(get_db), _: AdminSession = Depends(require_admin)):
    timeline = []
    if _table_exists(db, "product_events"):
        query = db.query(ProductEvent).filter(or_(ProductEvent.user_id == identity, ProductEvent.anonymous_id == identity)).order_by(ProductEvent.occurred_at.desc()).limit(200)
        timeline = [_event_to_row(row) for row in query.all()]
    return {"identity": identity, "timeline": timeline}


@router.get("/v1/admin/artworks")
def admin_artworks(
    q: Optional[str] = None,
    museum: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: AdminSession = Depends(require_admin),
):
    query = db.query(Artwork)
    if q:
        query = query.filter(or_(Artwork.title_original.ilike(f"%{q}%"), Artwork.artist.ilike(f"%{q}%"), Artwork.id.ilike(f"%{q}%")))
    if museum:
        query = query.filter(Artwork.museum_id == museum)
    if status:
        query = query.filter(Artwork.recognition_status == status)
    total = query.count()
    rows = []
    for artwork in query.order_by(Artwork.museum_id.asc(), Artwork.priority.asc(), Artwork.title_original.asc()).offset(offset).limit(limit).all():
        recognition_count = _artwork_event_count(db, artwork.id)
        rows.append({
            "artwork_id": artwork.id,
            "title": artwork.title_original,
            "artist": artwork.artist,
            "museum_id": artwork.museum_id,
            "catalog_status": "active" if db.query(ArtworkCatalogMembership).filter(ArtworkCatalogMembership.artwork_id == artwork.id, ArtworkCatalogMembership.active.is_(True)).first() else "inactive",
            "recognition_readiness": artwork.recognition_status,
            "recognitions": recognition_count,
            "success_rate": None,
            "average_confidence": None,
            "last_recognized": _safe_datetime(_last_artwork_event(db, artwork.id)),
            "content_views": _artwork_event_count(db, artwork.id, {"result_viewed", "artwork_viewed"}),
        })
    return {"rows": rows, "total": total, "limit": limit, "offset": offset}


def _artwork_event_count(db: Session, artwork_id: str, events: Optional[Iterable[str]] = None) -> int:
    if not _table_exists(db, "product_events"):
        return int(db.query(VisitArtwork).filter(VisitArtwork.artwork_id == artwork_id).count())
    query = db.query(ProductEvent).filter(ProductEvent.artwork_id == artwork_id)
    if events:
        query = query.filter(ProductEvent.event_name.in_(list(events)))
    return int(query.count())


def _last_artwork_event(db: Session, artwork_id: str) -> Optional[datetime]:
    if not _table_exists(db, "product_events"):
        row = db.query(VisitArtwork).filter(VisitArtwork.artwork_id == artwork_id).order_by(VisitArtwork.scanned_at.desc()).first()
        return row.scanned_at if row else None
    row = db.query(ProductEvent).filter(ProductEvent.artwork_id == artwork_id).order_by(ProductEvent.occurred_at.desc()).first()
    return row.occurred_at if row else None


@router.get("/v1/admin/museums")
def admin_museums(period: str = "30d", db: Session = Depends(get_db), _: AdminSession = Depends(require_admin)):
    start, end, *_ = _period_bounds(period)
    return {"rows": _museum_rows(db, start, end, limit=2000)}


@router.get("/v1/admin/catalog")
def admin_catalog(db: Session = Depends(get_db), _: AdminSession = Depends(require_admin)):
    return _catalog_health(db)


@router.get("/v1/admin/acquisition")
def admin_acquisition(period: str = "30d", db: Session = Depends(get_db), _: AdminSession = Depends(require_admin)):
    start, end, *_ = _period_bounds(period)
    return _acquisition(db, start, end)


@router.get("/v1/admin/system")
def admin_system(db: Session = Depends(get_db), _: AdminSession = Depends(require_admin)):
    return _system(db)


@router.get("/v1/admin/export/{kind}")
def admin_export(kind: str, period: str = "30d", db: Session = Depends(get_db), _: AdminSession = Depends(require_admin)):
    start, end, *_ = _period_bounds(period)
    if kind == "failures":
        if not _table_exists(db, "product_events"):
            payload = []
        else:
            events = (
                _event_base_query(db, start, end)
                .filter(ProductEvent.event_name.in_(list(FAILURE_EVENTS) + ["recognition_completed"]))
                .order_by(ProductEvent.occurred_at.desc())
                .limit(1000)
                .all()
            )
            payload = []
            for event in events:
                props = event.properties or {}
                if event.event_name == "recognition_completed" and props.get("status") not in {"no_match", "failed"}:
                    continue
                payload.append({
                    "timestamp": _safe_datetime(event.occurred_at),
                    "user": event.user_id or event.anonymous_id,
                    "session_id": event.session_id,
                    "museum_id": event.museum_id,
                    "confidence": props.get("confidence"),
                    "failure_reason": props.get("reason") or props.get("failure_reason") or props.get("status"),
                    "latency_ms": props.get("latency_ms") or props.get("recognition_latency_ms"),
                    "status": props.get("status") or event.event_name,
                })
    elif kind == "museums":
        payload = _museum_rows(db, start, end, limit=2000)
    else:
        payload = _top_artworks(db, start, end, limit=1000)
    output = StringIO()
    keys = sorted({key for row in payload for key in row.keys()}) if payload else ["empty"]
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    writer.writerows(payload)
    return Response(content=output.getvalue(), media_type="text/csv")
