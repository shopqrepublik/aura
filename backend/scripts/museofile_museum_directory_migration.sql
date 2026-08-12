-- Additive museum-directory fields for the France-wide Muséofile import.
-- No artwork/content tables are modified by this migration.

alter table museums add column if not exists external_source text;
alter table museums add column if not exists external_id text;
alter table museums add column if not exists slug text;
alter table museums add column if not exists common_name text;
alter table museums add column if not exists city text;
alter table museums add column if not exists department text;
alter table museums add column if not exists region text;
alter table museums add column if not exists address text;
alter table museums add column if not exists postal_code text;
alter table museums add column if not exists website_url text;
alter table museums add column if not exists collection_categories jsonb;
alter table museums add column if not exists notable_terms jsonb;
alter table museums add column if not exists source_url text;
alter table museums add column if not exists source_updated_at timestamptz;
alter table museums add column if not exists raw_json jsonb;
alter table museums add column if not exists experience_level text not null default 'AI_GUIDE';

create unique index if not exists idx_museums_external_source_id
  on museums (external_source, external_id)
  where external_source is not null and external_id is not null;

create index if not exists idx_museums_city on museums (city);
create index if not exists idx_museums_region on museums (region);
create index if not exists idx_museums_experience_level on museums (experience_level);
