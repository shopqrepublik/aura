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


class Mission(Base):
    __tablename__ = "missions"
    id = Column(String, primary_key=True)
    museum_id = Column(String, ForeignKey("museums.id"))
    locale = Column(String, default="en")
    text = Column(String, nullable=False)


class Visit(Base):
    __tablename__ = "visits"
    id = Column(String, primary_key=True)              # uuid
    museum_id = Column(String, ForeignKey("museums.id"))
    locale = Column(String, default="en")
    started_at = Column(DateTime, default=now)
    completed_at = Column(DateTime, nullable=True)
    anonymous = Column(Boolean, default=True)

    artworks = relationship("VisitArtwork", back_populates="visit")


class VisitArtwork(Base):
    __tablename__ = "visit_artworks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(String, ForeignKey("visits.id"), nullable=False)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    confidence = Column(Float)
    added = Column(Boolean, default=False)
    favorited = Column(Boolean, default=False)
    card_read_seconds = Column(Float, nullable=True)
    scanned_at = Column(DateTime, default=now)

    visit = relationship("Visit", back_populates="artworks")
