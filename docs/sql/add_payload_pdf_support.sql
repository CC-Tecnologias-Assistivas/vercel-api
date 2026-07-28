-- Run on project https://uhkydwfzfionuaiiqirj.supabase.co
-- Adds PDF metadata columns and a private Storage bucket for temporary PDFs.

alter table public.payloads
  add column if not exists pdf_path text null;

alter table public.payloads
  add column if not exists report_type text null;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'payload-pdfs',
  'payload-pdfs',
  false,
  10485760,
  array['application/pdf']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
