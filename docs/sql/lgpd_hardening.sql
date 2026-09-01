-- Apply after the original payloads table and before accepting production data.
-- The service-role key remains backend-only; RLS is enabled for defense in depth.

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

-- Do not allow an unscoped payload to survive the migration. If this fails,
-- map each legacy row to its organization before enabling real traffic.
do $$
begin
  if exists (
    select 1 from public.payloads
    where organization_id is null or ingest_credential_id is null
  ) then
    raise exception 'payloads possui linhas sem escopo; migre-as antes da producao';
  end if;
  alter table public.payloads alter column organization_id set not null;
  alter table public.payloads alter column ingest_credential_id set not null;
end $$;

create index if not exists idx_payloads_organization_pending
  on public.payloads (organization_id, consumed_at, expires_at, created_at);
create index if not exists idx_credentials_org_role
  on public.api_credentials (organization_id, role, revoked_at, expires_at);

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

create index if not exists idx_audit_events_org_time
  on public.audit_events (organization_id, occurred_at desc);

alter table public.organizations enable row level security;
alter table public.api_credentials enable row level security;
alter table public.payloads enable row level security;
alter table public.audit_events enable row level security;

-- No anon/authenticated policy is granted. Backend access uses service_role only.

-- Cleanup function removes transient queue rows. PDF objects are removed by the
-- protected maintenance endpoint before the corresponding row is deleted.
create or replace function public.rehabeasy_cleanup_payload_rows(p_cutoff timestamptz)
returns table (id text, pdf_path text)
language sql
security definer
set search_path = public
as $$
  delete from public.payloads
   where expires_at < now()
      or consumed_at < p_cutoff
  returning payloads.id, payloads.pdf_path;
$$;
