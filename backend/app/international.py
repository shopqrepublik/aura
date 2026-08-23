"""Institution international configuration without currency conversion."""
from __future__ import annotations

import re
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from .models import Country, Institution

_LOCALE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class InstitutionInternationalConfig:
    country_code: str
    timezone: str
    default_locale: str
    supported_locales: tuple[str, ...]
    display_currency: str | None
    content_policy: dict


@dataclass(frozen=True)
class ValueOutputPolicy:
    enabled: bool
    engine_currency: str
    display_currency: str | None
    reason: str


def normalize_locale(value: str) -> str:
    value = (value or "").strip()
    if not _LOCALE.fullmatch(value):
        raise ValueError("locale must be a BCP-47 language tag")
    parts = value.split("-")
    normalized = [parts[0].lower()]
    for part in parts[1:]:
        normalized.append(part.title() if len(part) == 4 else part.upper() if len(part) in {2, 3} else part)
    return "-".join(normalized)


def validate_currency(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    if not _CURRENCY.fullmatch(value):
        raise ValueError("currency must be a three-letter ISO 4217-style code")
    return value


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone must be an IANA timezone") from exc
    return value


def get_institution_international_config(db: Session, institution_id: str) -> InstitutionInternationalConfig:
    institution = db.get(Institution, institution_id)
    if institution is None or not institution.active or not institution.country_code:
        raise ValueError("active institution with country is required")
    country = db.get(Country, institution.country_code)
    if country is None or not country.active:
        raise ValueError("active country configuration is required")
    default_locale = normalize_locale(institution.default_locale or country.default_locale or "")
    supported = tuple(dict.fromkeys(normalize_locale(v) for v in (institution.supported_locales or [default_locale])))
    if default_locale not in supported:
        raise ValueError("default locale must be included in supported locales")
    timezone = validate_timezone(institution.timezone or country.default_timezone or "UTC")
    currency = validate_currency(institution.display_currency or country.default_currency)
    policy = dict(country.content_policy or {})
    policy.update(institution.content_policy or {})
    return InstitutionInternationalConfig(
        country_code=country.code,
        timezone=timezone,
        default_locale=default_locale,
        supported_locales=supported,
        display_currency=currency,
        content_policy=policy,
    )


def get_value_output_policy(config: InstitutionInternationalConfig, engine_currency: str = "EUR") -> ValueOutputPolicy:
    """Never relabel a currency-grounded model as an institution currency."""
    engine_currency = validate_currency(engine_currency) or "EUR"
    explicitly_enabled = config.content_policy.get("value_engine_v4_enabled")
    compatible = config.display_currency == engine_currency
    enabled = compatible if explicitly_enabled is None else bool(explicitly_enabled) and compatible
    return ValueOutputPolicy(
        enabled=enabled, engine_currency=engine_currency,
        display_currency=config.display_currency,
        reason="currency_compatible" if enabled else "unsupported_currency_or_disabled_policy",
    )
