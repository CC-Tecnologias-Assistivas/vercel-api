-- LGPD hardening for the RehabEasy Transfer API.
--
-- The API is the only data-plane client. It uses SUPABASE_SECRET_KEY (or the
-- legacy SUPABASE_SERVICE_ROLE_KEY) on the backend, so no anon/authenticated
-- policy is required for these tables.

create table if not exists public.organizations (
  id text primary key,
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.api_credentials (
  id text primary key,
  organization_id text not null references public.organizations(id),
  key_id text not null unique,
  label text not null,
  role text not null check (role in ('publisher', 'consumer')),
  secret_hash text not null,
  created_at timestamptz not null default now(),
  last_used_at timestamptz null,
  expires_at timestamptz null,
  revoked_at timestamptz null
);

alter table public.payloads
  add column if not exists organization_id text references public.organizations(id),
  add column if not exists ingest_credential_id text references public.api_credentials(id),
  add column if not exists report_type text null,
  add column if not exists pdf_path text null;

create table if not exists public.audit_events (
  id bigint generated always as identity primary key,
  organization_id text null references public.organizations(id),
  credential_id text null references public.api_credentials(id),
  payload_id text null,
  action text not null,
  outcome text not null check (outcome in ('success', 'failure')),
  request_id text null,
  occurred_at timestamptz not null default now()
);

create index if not exists idx_payloads_expires_at on public.payloads (expires_at);
create index if not exists idx_payloads_consumed_at on public.payloads (consumed_at);
create index if not exists idx_payloads_organization_pending
  on public.payloads (organization_id, consumed_at, expires_at, created_at);
create index if not exists idx_payloads_ingest_credential
  on public.payloads (ingest_credential_id);
create index if not exists idx_credentials_org_role
  on public.api_credentials (organization_id, role, revoked_at, expires_at);
create index if not exists idx_audit_events_org_time
  on public.audit_events (organization_id, occurred_at desc);
create index if not exists idx_audit_events_credential
  on public.audit_events (credential_id);

-- Before making these columns NOT NULL, map all legacy rows to a real
-- organization and a revoked migration credential. Do not delete old data.
--
-- Example for a single-organization migration:
--   insert into public.organizations (id, name)
--   values ('org-rehabeasy', 'Organizacao RehabEasy')
--   on conflict (id) do nothing;
--   update public.payloads
--      set organization_id = 'org-rehabeasy'
--    where organization_id is null;
--   update public.payloads
--      set ingest_credential_id = '<revoked-migration-credential-id>'
--    where ingest_credential_id is null;

alter table public.organizations enable row level security;
alter table public.api_credentials enable row level security;
alter table public.payloads enable row level security;
alter table public.audit_events enable row level security;

revoke all on table public.organizations from anon, authenticated;
revoke all on table public.api_credentials from anon, authenticated;
revoke all on table public.payloads from anon, authenticated;
revoke all on table public.audit_events from anon, authenticated;

insert into storage.buckets (id, name, public)
values ('payload-pdfs', 'payload-pdfs', false)
on conflict (id) do update set public = false;

-- Cleanup is performed by the protected API maintenance endpoint. Keep
-- SECURITY DEFINER functions out of the exposed public schema.
