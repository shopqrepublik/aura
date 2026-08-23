import base64
import csv
import hashlib
import hmac
import json
import math
import os
import secrets
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import String, and_, case, desc, distinct, func, inspect, or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import SessionLocal, get_db
from .models import (
    AdminLoginAttempt,
    AdminSession,
    Artwork,
    ArtworkCatalogMembership,
    ArtworkLocalization,
    ArtworkValueReveal,
    Country,
    InstitutionProfile,
    LouvreImageReference,
    Museum,
    ProductEvent,
    RecognitionAsset,
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
    event_id: Optional[str] = None
    event_name: str = Field(min_length=1, max_length=120)
    occurred_at: Optional[datetime] = None
    user_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    session_id: Optional[str] = None
    museum_id: Optional[str] = None
    artwork_id: Optional[str] = None
    recognition_attempt_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    language: Optional[str] = None
    device_type: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    path: Optional[str] = None


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
    return func.coalesce(ProductEvent.user_id, ProductEvent.anonymous_id)


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
    return or_(ProductEvent.properties.is_(None), ProductEvent.properties["internal_test"].as_boolean().isnot(True))


def _event_base_query(db: Session, start: Optional[datetime], end: datetime, include_internal: bool = False):
    query = db.query(ProductEvent)
    if start:
        query = query.filter(ProductEvent.occurred_at >= start)
    query = query.filter(ProductEvent.occurred_at < end)
    if not include_internal:
        query = query.filter(_non_internal_event_filter())
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


@router.post("/v1/events")
def ingest_product_event(payload: ProductEventIn, request: Request, db: Session = Depends(get_db)):
    if not _table_exists(db, "product_events"):
        return {"ok": False, "stored": False, "reason": "schema_missing"}
    event_id = payload.event_id or str(uuid.uuid4())
    if db.query(ProductEvent).filter(ProductEvent.event_id == event_id).first():
        return {"ok": True, "stored": False, "duplicate": True}
    db.add(
        ProductEvent(
            event_id=event_id,
            event_name=payload.event_name[:120],
            occurred_at=payload.occurred_at or _utcnow(),
            user_id=(payload.user_id or None),
            anonymous_id=(payload.anonymous_id or None),
            session_id=(payload.session_id or None),
            museum_id=(payload.museum_id or _extract_prop(payload.properties, "museum_id")),
            artwork_id=(payload.artwork_id or _extract_prop(payload.properties, "artwork_id")),
            recognition_attempt_id=(payload.recognition_attempt_id or _extract_prop(payload.properties, "recognition_attempt_id")),
            properties=payload.properties,
            source=payload.source or _extract_prop(payload.properties, "source"),
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
        )
    )
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        return {"ok": False, "stored": False}
    return {"ok": True, "stored": True}


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
                properties=props,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _basic_user_metrics(db: Session, start: Optional[datetime], end: datetime, prev_start: Optional[datetime], prev_end: Optional[datetime]) -> Dict[str, Any]:
    registered_total = int(db.query(User).count())
    registered_new = int(db.query(User).filter(User.created_at >= start, User.created_at < end).count()) if start else registered_total
    active = _identity_count(db, start, end, MEANINGFUL_EVENTS)
    previous_active = _identity_count(db, prev_start, prev_end, MEANINGFUL_EVENTS) if prev_start and prev_end else 0
    anonymous = int(
        _event_base_query(db, start, end)
        .filter(ProductEvent.anonymous_id.isnot(None), ProductEvent.user_id.is_(None))
        .with_entities(func.count(distinct(ProductEvent.anonymous_id)))
        .scalar()
        or 0
    ) if _table_exists(db, "product_events") else 0
    activated = _identity_count(db, start, end, SUCCESS_EVENTS)
    sessions = int(
        _event_base_query(db, start, end)
        .filter(ProductEvent.session_id.isnot(None))
        .with_entities(func.count(distinct(ProductEvent.session_id)))
        .scalar()
        or 0
    ) if _table_exists(db, "product_events") else 0
    visit_sessions = int(db.query(Visit).filter((Visit.started_at >= start) if start else text("true"), Visit.started_at < end).count())
    sessions = max(sessions, visit_sessions)
    returning = _returning_user_count(db, start, end)
    return {
        "total_users": registered_total + anonymous,
        "registered_users": registered_total,
        "anonymous_visitors": anonymous,
        "new_users": registered_new,
        "active_users": _with_delta(active, previous_active),
        "activated_users": activated,
        "activation_rate": round((activated / registered_new) * 100, 1) if registered_new else None,
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
    return _identity_count(db, _utcnow() - delta, _utcnow(), MEANINGFUL_EVENTS)


def _returning_user_count(db: Session, start: Optional[datetime], end: datetime) -> int:
    if not _table_exists(db, "product_events"):
        return 0
    rows = (
        _event_base_query(db, start, end)
        .filter(ProductEvent.event_name.in_(list(MEANINGFUL_EVENTS)), _identity_expr().isnot(None))
        .with_entities(_identity_expr().label("identity"), func.count(distinct(func.date(ProductEvent.occurred_at))).label("days"))
        .group_by("identity")
        .all()
    )
    return sum(1 for row in rows if int(row.days or 0) > 1)


def _recognition_metrics(db: Session, start: Optional[datetime], end: datetime) -> Dict[str, Any]:
    visitor_events = _identified_event_query(db, start, end) if _table_exists(db, "product_events") else None
    attempts = int(visitor_events.filter(ProductEvent.event_name == "recognition_started").count()) if visitor_events else 0
    successes = int(visitor_events.filter(ProductEvent.event_name.in_(list(SUCCESS_EVENTS))).count()) if visitor_events else 0
    failures = int(visitor_events.filter(ProductEvent.event_name.in_(list(FAILURE_EVENTS))).count()) if visitor_events else 0
    no_match = 0
    latencies: List[float] = []
    failure_reasons = Counter()
    confidence_buckets = Counter()
    identityless_operational_events = 0
    if _table_exists(db, "product_events"):
        identityless_operational_events = int(
            _event_base_query(db, start, end)
            .filter(ProductEvent.event_name.in_(["recognition_started", "recognition_completed", "recognition_failed"]), _identity_expr().is_(None))
            .count()
        )
        rows = _identified_event_query(db, start, end).filter(
            ProductEvent.event_name.in_(["recognition_completed", "recognition_failed", "scan_failed", "scan_success", "recognition_succeeded"])
        ).all()
        for row in rows:
            props = row.properties or {}
            status = props.get("status")
            if row.event_name == "recognition_completed" and status in {"matched", "needs_confirmation"}:
                successes += 1
            if status == "no_match" or props.get("reason") in {"no_match", "uncataloged"}:
                no_match += 1
                if row.event_name == "recognition_completed":
                    failures += 1
            reason = props.get("reason") or props.get("failure_reason") or status
            if row.event_name in FAILURE_EVENTS and reason:
                failure_reasons[str(reason)] += 1
            latency = props.get("latency_ms") or props.get("recognition_latency_ms")
            if isinstance(latency, (int, float)):
                latencies.append(float(latency))
            conf = props.get("confidence")
            if isinstance(conf, (int, float)):
                confidence_buckets[_confidence_bucket(float(conf))] += 1
    historical_successes = int(db.query(VisitArtwork).count())
    if attempts == 0 and historical_successes:
        successes = historical_successes
    return {
        "attempts": attempts,
        "successful": successes,
        "failed": failures,
        "unknown_no_match": no_match,
        "success_rate": round((successes / attempts) * 100, 1) if attempts else None,
        "latency_avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
        "confidence_buckets": dict(confidence_buckets),
        "failure_reasons": [{"reason": reason, "count": count} for reason, count in failure_reasons.most_common()],
        "historical_success_records": historical_successes,
        "identityless_operational_events": identityless_operational_events,
        "visitor_metric_definition": "Recognition metrics count first-party product events with a persistent user_id or anonymous_id. Identityless server smoke/API events are retained but excluded from visitor KPIs.",
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
    return {"stages": rows, "biggest_dropoff": biggest}


def _retention(db: Session) -> Dict[str, Any]:
    if not _table_exists(db, "product_events"):
        return {"d1": None, "d7": None, "d30": None, "cohorts": []}
    rows = (
        db.query(ProductEvent)
        .filter(ProductEvent.event_name.in_(list(MEANINGFUL_EVENTS)), _identity_expr().isnot(None))
        .with_entities(_identity_expr().label("identity"), func.date(ProductEvent.occurred_at).label("day"))
        .distinct()
        .all()
    )
    by_identity: Dict[str, List[date]] = defaultdict(list)
    for identity, day in rows:
        if identity and day:
            by_identity[str(identity)].append(day)
    if not by_identity:
        return {"d1": None, "d7": None, "d30": None, "cohorts": []}
    d1 = d7 = d30 = 0
    cohorts: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"users": 0, "d1": 0, "d7": 0, "d30": 0})
    for days in by_identity.values():
        first = min(days)
        day_set = set(days)
        key = f"{first.isocalendar().year}-W{first.isocalendar().week:02d}"
        cohorts[key]["users"] += 1
        if first + timedelta(days=1) in day_set:
            d1 += 1
            cohorts[key]["d1"] += 1
        if any(day >= first + timedelta(days=7) for day in day_set):
            d7 += 1
            cohorts[key]["d7"] += 1
        if any(day >= first + timedelta(days=30) for day in day_set):
            d30 += 1
            cohorts[key]["d30"] += 1
    total = len(by_identity)
    cohort_rows = []
    for cohort, data in sorted(cohorts.items(), reverse=True)[:12]:
        users = data["users"]
        cohort_rows.append({
            "cohort": cohort,
            "users": users,
            "d1": round(data["d1"] / users * 100, 1) if users else 0,
            "d7": round(data["d7"] / users * 100, 1) if users else 0,
            "d30": round(data["d30"] / users * 100, 1) if users else 0,
        })
    return {
        "d1": round(d1 / total * 100, 1),
        "d7": round(d7 / total * 100, 1),
        "d30": round(d30 / total * 100, 1),
        "cohorts": cohort_rows,
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
        scans = _event_count_for_museum(db, start, end, museum.id, {"recognition_started", "scan_attempt"})
        success = _event_count_for_museum(db, start, end, museum.id, SUCCESS_EVENTS)
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
    if not _table_exists(db, "product_events"):
        return 0
    return int(
        _event_base_query(db, start, end)
        .filter(ProductEvent.museum_id == museum_id, _identity_expr().isnot(None))
        .with_entities(func.count(distinct(_identity_expr())))
        .scalar()
        or 0
    )


def _session_count_for_museum(db: Session, start: Optional[datetime], end: datetime, museum_id: str) -> int:
    if not _table_exists(db, "product_events"):
        return 0
    return int(
        _event_base_query(db, start, end)
        .filter(ProductEvent.museum_id == museum_id, ProductEvent.session_id.isnot(None))
        .with_entities(func.count(distinct(ProductEvent.session_id)))
        .scalar()
        or 0
    )


def _top_artworks(db: Session, start: Optional[datetime], end: datetime, limit: int = 20) -> List[Dict[str, Any]]:
    event_counts = Counter()
    if _table_exists(db, "product_events"):
        rows = (
            _identified_event_query(db, start, end)
            .filter(ProductEvent.artwork_id.isnot(None), ProductEvent.event_name.in_(["result_viewed", "artwork_viewed", "scan_success", "recognition_succeeded"]))
            .with_entities(ProductEvent.artwork_id, func.count(ProductEvent.event_id))
            .group_by(ProductEvent.artwork_id)
            .order_by(desc(func.count(ProductEvent.event_id)))
            .limit(limit)
            .all()
        )
        event_counts.update({artwork_id: int(count) for artwork_id, count in rows})
    if not event_counts:
        rows = db.query(VisitArtwork.artwork_id, func.count(VisitArtwork.id)).group_by(VisitArtwork.artwork_id).order_by(desc(func.count(VisitArtwork.id))).limit(limit).all()
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
    if _table_exists(db, "product_events"):
        row = db.query(ProductEvent).filter(ProductEvent.event_name.in_(["recognition_succeeded", "scan_success", "recognition_completed"])).order_by(ProductEvent.occurred_at.desc()).first()
        latest_recognition = _safe_datetime(row.occurred_at) if row else None
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
    gaps.append("Historical backend recognition attempts were previously stdout logs only; precise historical failure/latency metrics are available only after first-party event ingestion.")
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
    new_users = _identity_count(db, start, end, {"app_opened", "visit_started", "museum_selected"})
    activated = _identity_count(db, start, end, SUCCESS_EVENTS)
    median_time = None
    scans_before_first = None
    if _table_exists(db, "product_events"):
        rows = (
            _event_base_query(db, start, end)
            .filter(_identity_expr().isnot(None), ProductEvent.event_name.in_(["app_opened", "visit_started", "recognition_started", "recognition_succeeded", "scan_success"]))
            .order_by(ProductEvent.occurred_at.asc())
            .all()
        )
        first_seen: Dict[str, datetime] = {}
        first_success: Dict[str, datetime] = {}
        scans: Dict[str, int] = defaultdict(int)
        for row in rows:
            identity = row.user_id or row.anonymous_id
            if not identity:
                continue
            first_seen.setdefault(identity, row.occurred_at)
            if row.event_name == "recognition_started" and identity not in first_success:
                scans[identity] += 1
            if row.event_name in SUCCESS_EVENTS and identity not in first_success:
                first_success[identity] = row.occurred_at
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
    if not _table_exists(db, "product_events"):
        return {"rows": [], "total": 0, "data_gap": "recognition failures were not durably stored before product_events"}
    query = _event_base_query(db, start, end).filter(ProductEvent.event_name.in_(list(FAILURE_EVENTS) + ["recognition_completed"]))
    if museum:
        query = query.filter(ProductEvent.museum_id == museum)
    rows = []
    for event in query.order_by(ProductEvent.occurred_at.desc()).offset(offset).limit(limit).all():
        props = event.properties or {}
        event_reason = props.get("reason") or props.get("failure_reason") or props.get("status")
        if reason and event_reason != reason:
            continue
        if event.event_name == "recognition_completed" and props.get("status") not in {"no_match", "failed"}:
            continue
        rows.append({
            "timestamp": _safe_datetime(event.occurred_at),
            "user": event.user_id or event.anonymous_id,
            "session_id": event.session_id,
            "museum_id": event.museum_id,
            "top_candidate": props.get("top_candidate") or props.get("candidate") or props.get("ai_candidate"),
            "confidence": props.get("confidence"),
            "failure_reason": event_reason,
            "latency_ms": props.get("latency_ms") or props.get("recognition_latency_ms"),
            "pipeline": props.get("pipeline") or props.get("recognition_mode") or props.get("model"),
            "status": props.get("status") or event.event_name,
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
