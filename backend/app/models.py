"""
Canonical entities per spec §9.2:
museums, artworks, artwork_localizations, artwork_estimates,
artwork_embeddings, visits, visit_artworks, missions.

Layer 1 (factual, imported) vs Layer 2 (editorial, reviewed) is kept
explicit via separate tables rather than flattened columns, so imports
never silently overwrite reviewed editorial content.
"""
from sqlalchemy import (
    Column, String, Integer, Float, ForeignKey, DateTime, Boolean, JSON, Text,
    Index, UniqueConstraint
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
    external_source = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    slug = Column(String, nullable=True)
    common_name = Column(String, nullable=True)
    city = Column(String, nullable=True)
    department = Column(String, nullable=True)
    region = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    postal_code = Column(String, nullable=True)
    website_url = Column(String, nullable=True)
    collection_categories = Column(JSON, nullable=True)
    notable_terms = Column(JSON, nullable=True)
    source_url = Column(String, nullable=True)
    source_updated_at = Column(DateTime, nullable=True)
    raw_json = Column(JSON, nullable=True)
    experience_level = Column(String, nullable=False, default="AI_GUIDE")


class Artwork(Base):
    """Layer 1 — factual, imported from CMS workbook (§16) or, since the
    Louvre pilot, directly from a museum's own source-of-record API. See
    docs/louvre-schema.md for the full design rationale behind the columns
    added for that pilot (source/display-status/recognition-readiness)."""
    __tablename__ = "artworks"
    __table_args__ = (
        UniqueConstraint("source", "source_record_id", name="uq_artworks_source_record"),
        Index("idx_artworks_museum_id", "museum_id"),
        Index("idx_artworks_department", "department"),
        Index("idx_artworks_display_status", "display_status"),
        Index("idx_artworks_artist", "artist"),
        Index("idx_artworks_creator_wikidata_qid", "creator_wikidata_qid"),
        Index("idx_artworks_hall", "hall"),
        Index("idx_artworks_object_type", "object_type"),
    )

    id = Column(String, primary_key=True)           # e.g. "orsay_rf_1990"
    museum_id = Column(String, ForeignKey("museums.id"), nullable=False)
    artist = Column(String, nullable=True)
    title_original = Column(String, nullable=False)
    title_complement = Column(String, nullable=True)
    year = Column(String)
    inventory_number = Column(String)
    hall = Column(String)
    technique = Column(String)
    dimensions = Column(String)
    image_url = Column(String)
    priority = Column(Integer, default=100)          # lower = higher priority (Top 100/Top 20)
    tags = Column(JSON, default=list)
    source_urls = Column(JSON, default=list)

    # --- Source provenance (Louvre pilot onward) ------------------------
    # Every fact must be traceable back to where it came from -- never
    # inferred or silently fabricated. Null for museums imported before
    # this existed (Orsay/Orangerie's original Wikidata-based build).
    source = Column(String, nullable=True)            # e.g. "louvre", "demo_artworks", "wikidata_cirrus"
    source_record_id = Column(String, nullable=True)  # e.g. Louvre ARK id "cl010066107"
    source_url = Column(String, nullable=True)
    last_source_sync = Column(DateTime, nullable=True)
    raw_json = Column(JSON, nullable=True)             # unmodified source payload, never partially overwritten

    # --- Louvre-specific facts (nullable for other museums) ------------
    department = Column(String, nullable=True)         # Louvre's curatorial-department field
    collection = Column(String, nullable=True)
    object_type = Column(String, nullable=True)
    materials_and_techniques = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    provenance = Column(Text, nullable=True)
    object_history = Column(Text, nullable=True)
    historical_context = Column(Text, nullable=True)
    current_location_raw = Column(Text, nullable=True)  # verbatim currentLocation, kept even after classification
    room = Column(String, nullable=True)
    creator_wikidata_qid = Column(String, nullable=True)
    creator_raw = Column(JSON, nullable=True)
    creator_labels = Column(JSON, nullable=True)

    # --- Three INDEPENDENT classification dimensions, evidence-based
    # (never guessed from "has an image" or "belongs to this museum") --
    # see docs/louvre-schema.md. Deliberately kept as three separate
    # columns, never collapsed into one enum: an object must be able to be
    # ON_DISPLAY + READY metadata + NEEDS_ASSET all at once.
    display_status = Column(String, nullable=True)               # ON_DISPLAY | NOT_ON_DISPLAY | UNKNOWN
    display_status_confidence = Column(String, nullable=True)    # HIGH | MEDIUM | LOW | UNKNOWN
    display_status_reason = Column(Text, nullable=True)
    metadata_status = Column(String, nullable=True)               # READY | PARTIAL | INSUFFICIENT
    recognition_status = Column(String, nullable=True)            # READY | NEEDS_ASSET | NO_USABLE_ASSET | RIGHTS_REVIEW | RIGHTS_RESTRICTED
    rights_status = Column(String, nullable=True)                 # evidence-only status for artwork-level rights metadata
    rights_review_required = Column(Boolean, nullable=True)

    localizations = relationship("ArtworkLocalization", back_populates="artwork")
    estimates = relationship("ArtworkEstimate", back_populates="artwork")
    value_reveals = relationship("ArtworkValueReveal", back_populates="artwork")
    embeddings = relationship("ArtworkEmbedding", back_populates="artwork")
    louvre_image_references = relationship("LouvreImageReference", back_populates="artwork")
    recognition_assets = relationship("RecognitionAsset", back_populates="artwork")
    catalog_memberships = relationship("ArtworkCatalogMembership", back_populates="artwork")


class ArtworkCatalogMembership(Base):
    """Versioned visitor-catalog membership.

    `artworks` is museum knowledge. This table defines which subset is active
    for a specific visitor-facing catalog version, e.g. Louvre Visitor 500 v1.
    """
    __tablename__ = "artwork_catalog_memberships"
    __table_args__ = (
        UniqueConstraint("artwork_id", "catalog_version", name="uq_artwork_catalog_membership_version"),
        Index("idx_artwork_catalog_memberships_museum_version_active", "museum_id", "catalog_version", "active"),
        Index("idx_artwork_catalog_memberships_artwork_id", "artwork_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    museum_id = Column(String, ForeignKey("museums.id"), nullable=False)
    catalog_version = Column(String, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    tier = Column(String, nullable=True)
    visitor_priority = Column(Float, nullable=True)
    created_at = Column(DateTime, default=now)

    artwork = relationship("Artwork", back_populates="catalog_memberships")


class SourceRecordIndex(Base):
    """Enumeration layer only: known source records that may or may not have
    fetched metadata. This is not an artwork catalog table."""
    __tablename__ = "source_record_index"
    __table_args__ = (
        Index("idx_source_record_index_source", "source"),
        Index("idx_source_record_index_ingestion_status", "ingestion_status"),
    )

    source = Column(String, primary_key=True)            # e.g. "louvre"
    source_record_id = Column(String, primary_key=True)  # e.g. Louvre ARK id
    source_url = Column(String, nullable=False)
    sitemap_id = Column(String, nullable=True)
    position_in_sitemap = Column(Integer, nullable=True)
    prefix = Column(String, nullable=True)
    discovered_at = Column(DateTime, nullable=True)
    metadata_ingested_at = Column(DateTime, nullable=True)
    ingestion_status = Column(String, nullable=True)


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


class ArtworkValueReveal(Base):
    """Canonical visitor-facing value model.

    Supersedes the old binary "estimate or pending" UI contract without
    deleting artwork_estimates. Existing reviewed Orsay/Orangerie estimates
    continue to map into ESTIMATED_VALUE until explicit rows are backfilled.
    """
    __tablename__ = "artwork_value_reveals"
    __table_args__ = (
        UniqueConstraint("artwork_id", "catalog_version", name="uq_artwork_value_reveal_version"),
        Index("idx_artwork_value_reveals_artwork_id", "artwork_id"),
        Index("idx_artwork_value_reveals_mode", "mode"),
        Index("idx_artwork_value_reveals_review_status", "review_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    catalog_version = Column(String, nullable=True)
    mode = Column(String, nullable=False)  # ESTIMATED_VALUE | MARKET_CONTEXT | BEYOND_MARKET
    aggregate_value_eligible = Column(Boolean, nullable=False, default=False)

    estimated_value_low = Column(Float, nullable=True)
    estimated_value_high = Column(Float, nullable=True)
    estimated_value_currency = Column(String, nullable=True)

    market_context_headline_number = Column(JSON, nullable=True)
    market_context_currency = Column(String, nullable=True)
    market_context_label = Column(String, nullable=True)
    market_context_explanation = Column(Text, nullable=True)
    relationship_to_artwork = Column(Text, nullable=True)
    context_type = Column(String, nullable=True)
    source_reference = Column(String, nullable=True)
    context_date = Column(String, nullable=True)

    beyond_market_headline = Column(String, nullable=True)
    beyond_market_explanation = Column(Text, nullable=True)
    institutional_legal_context = Column(Text, nullable=True)
    optional_context = Column(Text, nullable=True)

    confidence = Column(String, nullable=True)
    methodology = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)
    disclaimer = Column(Text, nullable=True)
    review_status = Column(String, nullable=False, default="DRAFT")
    generated_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=now, onupdate=now)

    artwork = relationship("Artwork", back_populates="value_reveals")


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


class LouvreImageReference(Base):
    """Louvre's own published image URLs + per-image copyright strings --
    METADATA ONLY. `fetched` is always False for every row this project's
    Louvre importer creates: no image byte is ever downloaded, cached, or
    proxied through our infrastructure in this phase (see
    docs/louvre-source-audit.md §12-13 for why -- ADAGP's explicit AI/TDM
    prohibition and robots.txt's named block on Anthropic/Claude bots on
    image files). Deliberately a SEPARATE table from RecognitionAsset below
    -- an artwork's Louvre-sourced metadata must never be conflated with
    where its (future, independently-sourced) recognition image comes from.
    """
    __tablename__ = "louvre_image_references"
    id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    url_image = Column(String, nullable=False)
    url_thumbnail = Column(String)
    image_copyright = Column(String)          # verbatim Louvre copyright/credit string
    image_credit = Column(String, nullable=True)
    # Conservative, evidence-only classification -- NOT a creator-name/ADAGP
    # heuristic (removed; that was a guess, not evidence). rights_status
    # reflects only what the source record literally states;
    # rights_review_required is True for every Louvre-sourced row in this
    # phase (none have been cleared by an actual rights pipeline yet).
    rights_status = Column(String)             # "museum_asserted_copyright" | "unknown"
    rights_review_required = Column(Boolean, default=True)
    rights_reason = Column(Text, nullable=True)
    image_source = Column(String, default="louvre_collections")
    image_type = Column(String)                # Louvre's own "type" field (angle/detail description)
    position = Column(Integer)
    fetched = Column(Boolean, default=False)   # ALWAYS False here -- documents intent, not just absent data

    artwork = relationship("Artwork", back_populates="louvre_image_references")


class RecognitionAsset(Base):
    """Independent image layer for actual visual recognition -- deliberately
    decoupled from wherever an artwork's factual metadata came from. The
    Louvre importer NEVER writes to this table; it exists as the seam a
    later, separately-vetted pipeline (Wikimedia Commons, Wikidata media,
    our own photography, a future Rmn-GP license) attaches to once the
    image-rights question has an actual answer. ai_tdm_eligible and
    embedding_eligible are separate explicit booleans, never derived from
    rights_status or from the underlying artwork's public-domain status --
    "public domain artwork" says nothing about a specific photograph's
    license."""
    __tablename__ = "recognition_assets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    source = Column(String, nullable=False)     # e.g. "wikimedia_commons", "wikidata", "own_photograph", "rmn_gp_licensed"
    source_url = Column(String, nullable=False)
    license = Column(String)                     # e.g. "CC0", "CC-BY-SA-4.0", "PD-old-100", "proprietary_licensed"
    attribution = Column(Text)
    rights_status = Column(String)                # "public_domain" | "cc_licensed" | "proprietary_licensed" | "unknown"
    ai_tdm_eligible = Column(Boolean, default=False)
    embedding_eligible = Column(Boolean, default=False)
    local_storage_status = Column(String, default="not_fetched")  # "not_fetched" | "cached" | "cache_expired"
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    artwork = relationship("Artwork", back_populates="recognition_assets")


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


class UncatalogedSighting(Base):
    """Tier 2 recognition log (Phase 2 multi-museum §2) -- every time Stage 1
    open recognition names a real artist/title that fuzzy_match_catalog
    can't place in DEMO_ARTWORKS, this records it. One row per distinct
    (artist, title) pair (upserted, not one row per scan) -- this is a
    prioritization signal for which uncataloged works are actually being
    photographed often enough to be worth reviewing into the real catalog,
    not a per-visit analytics log (that's visit_artworks' job, and only
    covers works that ARE in the catalog)."""
    __tablename__ = "uncataloged_sightings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    artist = Column(String, nullable=False)
    title = Column(String, nullable=False)
    # Nullable: recognize() has no auth/visit context, so museum_id is only
    # ever what the caller's own RecognizeRequest.museum_id claims -- honest
    # best-effort provenance, not a verified location.
    museum_id = Column(String, ForeignKey("museums.id"), nullable=True)
    count = Column(Integer, default=1, nullable=False)
    first_seen_at = Column(DateTime, default=now)
    last_seen_at = Column(DateTime, default=now, onupdate=now)


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
    # No DB-level FK into artworks(id) yet, to avoid invalidating any
    # historic visit rows written before the catalog lived in Postgres. The
    # API validates current writes against the DB-backed, museum-scoped
    # catalog before inserting.
    artwork_id = Column(String, nullable=False)
    confidence = Column(Float)
    added = Column(Boolean, default=False)
    favorited = Column(Boolean, default=False)
    card_read_seconds = Column(Float, nullable=True)
    scanned_at = Column(DateTime, default=now)

    visit = relationship("Visit", back_populates="artworks")
