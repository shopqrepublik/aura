"""
Verifies Supabase Auth JWTs sent by the frontend as `Authorization: Bearer
<token>` and resolves them to a local `users` row -- registration is real
now (email magic link + Google; Apple deferred until an Apple Developer
account exists), so every /v1/visits* endpoint requires one of these.

This project's Supabase keys are the newer sb_publishable_/sb_secret_
format, which correlates with asymmetric (ES256) JWT signing -- confirmed
live against this project's own JWKS endpoint before writing this, rather
than assumed. That means verification only needs the PUBLIC signing key
(fetched from SUPABASE_URL's well-known JWKS endpoint, cached by
PyJWT's PyJWKClient), never a shared secret -- nothing here can forge a
token, only verify one Supabase itself issued.
"""
import os
import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

SUPABASE_URL = os.environ.get("SUPABASE_URL")

_bearer_scheme = HTTPBearer(auto_error=True)
_optional_bearer_scheme = HTTPBearer(auto_error=False)
# Lazy -- constructing PyJWKClient makes no network call itself (only the
# first .get_signing_key_from_jwt() does, and that result is cached), but
# building it at import time would still hard-fail module import when
# SUPABASE_URL is unset (e.g. local UI-only dev), same reasoning as db.py's
# engine being None until actually used.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not SUPABASE_URL:
            raise HTTPException(status_code=503, detail="auth not configured (SUPABASE_URL missing)")
        _jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    return _jwks_client


def _verify_supabase_jwt(token: str) -> dict:
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=["ES256"], audience="authenticated")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"invalid or expired token: {e}")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = _verify_supabase_jwt(credentials.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="token missing a valid sub claim")
    email = payload.get("email")
    provider = (payload.get("app_metadata") or {}).get("provider", "email")

    # Upsert rather than trusting a Postgres trigger to have already run --
    # keeps the sync logic in one place (here) instead of split between
    # Python and a DB-side trigger function only visible in Supabase itself.
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, email=email, auth_provider=provider)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif email and user.email != email:
        user.email = email
        db.commit()
    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve a supplied bearer token server-side; remain anonymous if absent."""
    if credentials is None:
        return None
    payload = _verify_supabase_jwt(credentials.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="token missing a valid sub claim")
    email = payload.get("email")
    provider = (payload.get("app_metadata") or {}).get("provider", "email")
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, email=email, auth_provider=provider)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif email and user.email != email:
        user.email = email
        db.commit()
    return user
