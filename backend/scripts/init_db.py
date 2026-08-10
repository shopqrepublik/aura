"""
One-time (and safe to re-run) setup against the real Supabase Postgres
database: creates every table declared in app/models.py (§9.2's canonical
schema -- most of it, e.g. artworks/museums, stays unused for now since the
catalog is still served from DEMO_ARTWORKS in main.py; only users/visits/
visit_artworks are actually read/written yet), then adds the one constraint
SQLAlchemy can't express on its own: users.id -> auth.users(id), a
cross-schema FK into Supabase Auth's own table.

Usage (from repo root):
    venv/Scripts/python.exe backend/scripts/init_db.py
"""
import os
import sys

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.normpath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO_ROOT, ".env"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from app.models import Base, Museum  # noqa: E402

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL not set (check .env)")

engine = create_engine(DATABASE_URL)

print("Creating tables (idempotent -- skips ones that already exist)...")
Base.metadata.create_all(engine)

# visits.museum_id has a real FK into museums(id) -- needs at least this one
# row to exist, or Visit creation fails with a ForeignKeyViolation the
# instant real (non-mock) visits start getting written. Coordinates match
# web/lib/geolocation.ts's MUSEUM_COORDS/GEOFENCE_RADIUS_M exactly (same
# museum, don't want the two to silently drift apart).
print("Seeding the museum rows (idempotent)...")
with Session(engine) as session:
    if session.get(Museum, "orsay") is None:
        session.add(Museum(id="orsay", name="Musée d'Orsay", lat=48.86, lng=2.3266, geofence_radius_m=150))
        session.commit()
    # Phase 3 pilot (Étape 1) — coordinates from Wikidata Q726781 (P625),
    # not eyeballed off a map, same rigor as the Orsay row above.
    if session.get(Museum, "orangerie") is None:
        session.add(Museum(id="orangerie", name="Musée de l'Orangerie", lat=48.86384535145145, lng=2.322538337460585, geofence_radius_m=150))
        session.commit()

print("Adding users.id -> auth.users(id) FK (idempotent)...")
with engine.begin() as conn:
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'users_id_fkey'
            ) THEN
                ALTER TABLE users
                    ADD CONSTRAINT users_id_fkey
                    FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """))

print("Dropping visit_artworks.artwork_id -> artworks(id) FK, if it exists (idempotent)...")
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE visit_artworks DROP CONSTRAINT IF EXISTS visit_artworks_artwork_id_fkey;"))

print("Done. Tables:", list(Base.metadata.tables.keys()))
