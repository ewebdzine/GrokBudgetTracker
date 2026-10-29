-- 0008_documents_storage.sql
-- All bill photos, receipts and statements live in the user's own Supabase project:
-- files in the private Storage bucket 'bill-documents', metadata in public.documents.
-- Path convention (object name inside the bucket): <yyyy>/<mm>/<uuid>-<file>
--   shown in docs as bill-documents/<yyyy>/<mm>/<uuid>-<file>
-- one_off_bills.receipt_path (0001) is kept for compatibility; new code links documents instead.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('bill-documents', 'bill-documents', false, 20971520,
        array['image/jpeg','image/png','image/heic','image/heif','image/webp','application/pdf'])
on conflict (id) do update set public = false;
-- No storage.objects policies are created: with RLS on storage.objects (Supabase default) and no policy for
-- this bucket, anon/authenticated can't read or write it. The bot uploads and creates signed URLs server-side.

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  storage_bucket text not null default 'bill-documents',
  storage_path text not null,                 -- object name in the bucket, e.g. 2026/01/<uuid>-dentist.jpg
  file_name text not null,
  mime_type text,
  size_bytes bigint check (size_bytes is null or size_bytes >= 0),
  sha256 text check (sha256 is null or sha256 ~ '^[0-9a-f]{64}$'),
  doc_type text not null default 'other' check (doc_type in ('bill_photo','receipt','statement','other')),
  uploaded_at timestamptz not null default now(),
  one_off_bill_id text references public.one_off_bills(id) on update cascade on delete set null,
  bill_instance_id bigint references public.bill_instances(id) on delete set null,
  transaction_id bigint references public.transactions(id) on delete set null,
  income_event_id text references public.income_events(id) on update cascade on delete set null,
  notes text,
  ocr_text text,                              -- optional: the text Grok read from the image
  constraint documents_path_uniq unique (storage_bucket, storage_path),
  constraint documents_path_format_chk check (storage_path ~ '^[0-9]{4}/[0-9]{2}/[0-9a-f-]{36}-.+$'),
  constraint documents_one_link_chk check (num_nonnulls(one_off_bill_id, bill_instance_id, transaction_id, income_event_id) <= 1));
create unique index if not exists documents_sha256_uniq on public.documents (sha256) where sha256 is not null;  -- dedupe
create index if not exists documents_one_off_idx  on public.documents (one_off_bill_id);
create index if not exists documents_bill_idx     on public.documents (bill_instance_id);
create index if not exists documents_tx_idx       on public.documents (transaction_id);
create index if not exists documents_income_idx   on public.documents (income_event_id);
create index if not exists documents_type_idx     on public.documents (doc_type, uploaded_at);

alter table public.documents enable row level security;
revoke all on public.documents from anon, authenticated;
