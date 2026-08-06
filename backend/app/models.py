"""
Canonical entities per spec §9.2:
museums, artworks, artwork_localizations, artwork_estimates,
artwork_embeddings, visits, visit_artworks, missions.

Layer 1 (factual, imported) vs Layer 2 (editorial, reviewed) is kept
explicit via separate tables rather than flattened columns, so imports
never silently overwrite reviewed editorial content.
"""
from sqlalchemy import (
    Column, String, Integer, Float, ForeignKey, DateTime, Boolean, JSON, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


def now():
    return datetime.now(timezone.utc)


class Museum(Base):
    __tablename__ = "museums"
    id = Column(String, primary_key=True)          # e.g. "orsay"
    name = Column(String, nullable=False)
    lat = Column(Float)
    lng = Column(Float)
    geofence_radius_m = Column(Integer, default=150)


class Artwork(Base):
    """Layer 1 — factual, imported from CMS workbook (§16)."""
    __tablename__ = "artworks"
    id = Column(String, primary_key=True)           # e.g. "orsay_rf_1990"
    museum_id = Column(String, ForeignKey("museums.id"), nullable=False)
    artist = Column(String, nullable=False)
    title_original = Column(String, nullable=False)
    year = Column(String)
    inventory_number = Column(String)
    hall = Column(String)
    technique = Column(String)
    dimensions = Column(String)
    image_url = Column(String)
    priority = Column(Integer, default=100)          # lower = higher priority (Top 100/Top 20)
    tags = Column(JSON, default=list)
    source_urls = Column(JSON, default=list)

    localizations = relationship("ArtworkLocalization", back_populates="artwork")
    estimates = relationship("ArtworkEstimate", back_populates="artwork")
    embeddings = relationship("ArtworkEmbedding", back_populates="artwork")


class ArtworkLocalization(Base):
    """Layer 2 — editorial, reviewed. One row per (artwork, locale, mode)."""
    __tablename__ = "artwork_localizations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    locale = Column(String, nullable=False)          # "en" | "fr" | "zh-Hans"
    mode = Column(String, default="normal")           # "normal" | "simple" | "kids"
    title = Column(String)
    analogy = Column(Text)
    why_it_matters = Column(Text)
    where_to_look = Column(Text)
    rarity_note = Column(Text)
    audio_script = Column(Text)
    audio_url = Column(String)
    editorial_status = Column(String, default="draft")  # draft|reviewed|published
    reviewed_by = Column(String)
    updated_at = Column(DateTime, default=now, onupdate=now)

    artwork = relationship("Artwork", back_populates="localizations")


class ArtworkEstimate(Base):
    """Layer 2 — never generated live; stored and reviewed only (§8.4, §11)."""
    __tablename__ = "artwork_estimates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    estimate_low_eur_m = Column(Float, nullable=False)
    estimate_high_eur_m = Column(Float, nullable=False)
    estimate_logic = Column(Text)
    comparable_sales = Column(Text)
    estimate_confidence = Column(String)              # low|medium|high
    reviewed_by = Column(String)
    updated_at = Column(DateTime, default=now, onupdate=now)

    artwork = relationship("Artwork", back_populates="estimates")


class ArtworkEmbedding(Base):
    """DINOv2/CLIP embeddings for retrieval (§8.2). Store vector out-of-band
    (FAISS index / pgvector) in production; this row tracks provenance."""
    __tablename__ = "artwork_embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    source_image_url = Column(String, nullable=False)
    augmentation_type = Column(String)                 # "canonical" | "synthetic_rotation" | "field_photo" ...
    model_name = Column(String, default="dinov2-vitl14")
    vector_ref = Column(String)                        # id/key in FAISS or pgvector, not the raw vector
    created_at = Column(DateTime, default=now)

    artwork = relationship("Artwork", back_populates="embeddings")


class User(Base):
    """Mirrors Supabase Auth's auth.users (email + Sign in with Apple/Google,
    Apple deferred until an Apple Developer account exists) -- id is the SAME
    uuid as auth.users.id, kept in sync by an app-level upsert on first
    verified request (see app/auth.py's get_current_user) rather than a
    Postgres trigger, so the sync logic lives in one place (Python) instead
    of being split across a trigger function only visible in the DB. A real
    FK constraint against auth.users(id) is added separately in
    scripts/init_db.py (SQLAlchemy can't easily declare a FK into another
    schema without a shadow table for it)."""
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String)
    auth_provider = Column(String)  # "email" | "google" | "apple"
    created_at = Column(DateTime, default=now)

    visits = relationship("Visit", back_populates="user")


class Mission(Base):
    __tablename__ = "missions"
    id = Column(String, primary_key=True)
    museum_id = Column(String, ForeignKey("museums.id"))
    locale = Column(String, default="en")
    text = Column(String, nullable=False)


class Visit(Base):
    __tablename__ = "visits"
    id = Column(String, primary_key=True)              # uuid
    # Real registration (email magic link + Google, §17 Continue-visit state
    # reads this) replaces the old anonymous=True default -- a Visit can no
    # longer exist without a signed-in user, so this is NOT NULL rather than
    # the optional field it would be if anonymous visits were still allowed.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    museum_id = Column(String, ForeignKey("museums.id"))
    locale = Column(String, default="en")
    started_at = Column(DateTime, default=now)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="visits")
    artworks = relationship("VisitArtwork", back_populates="visit")


class VisitArtwork(Base):
    __tablename__ = "visit_artworks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(String, ForeignKey("visits.id"), nullable=False)
    # No FK into artworks(id): the catalog is still served from main.py's
    # in-memory DEMO_ARTWORKS (unchanged by this task -- migrating it to
    # real rows is separate, larger scope), so the artworks table stays
    # empty and a real FK here would reject every insert.
    artwork_id = Column(String, nullable=False)
    confidence = Column(Float)
    added = Column(Boolean, default=False)
    favorited = Column(Boolean, default=False)
    card_read_seconds = Column(Float, nullable=True)
    scanned_at = Column(DateTime, default=now)

    visit = relationship("Visit", back_populates="artworks")
