-- 0006_review_status_and_bank_status.sql
-- Two separate statuses on transactions:
--   bank_status   = what the bank/source says: 'pending' or 'posted'
--   review_status = where the user's review stands: needs_review | categorized | auto_applied | skipped
-- Every imported row starts as review_status = 'needs_review'.

alter table public.transactions
  add column if not exists bank_status text not null default 'posted',
  add column if not exists review_status text not null default 'needs_review',
  add column if not exists reviewed_at timestamptz;
update public.transactions set bank_status = case when pending then 'pending' else 'posted' end;
update public.transactions set review_status = case when expense_type is not null then 'categorized' else 'needs_review' end;
alter table public.transactions
  add constraint transactions_bank_status_chk   check (bank_status in ('pending','posted')),
  add constraint transactions_review_status_chk check (review_status in ('needs_review','categorized','auto_applied','skipped'));
create index if not exists tx_review_status_idx on public.transactions (review_status, account_id);

-- Legacy boolean `pending` (used by dashboard_snapshot) is kept in sync from bank_status; write bank_status, not pending.
create or replace function public.tx_sync_pending() returns trigger language plpgsql set search_path = '' as $$
begin new.pending := (new.bank_status = 'pending'); return new; end $$;
revoke all on function public.tx_sync_pending() from public, anon, authenticated;
drop trigger if exists tx_sync_pending on public.transactions;
create trigger tx_sync_pending before insert or update of bank_status on public.transactions
  for each row execute function public.tx_sync_pending();

-- Review queue: everything not yet decided, including backlog from days the review didn't run
-- and items the user skipped earlier. Oldest first.
drop view if exists public.uncategorized_transactions;
create view public.needs_review_transactions with (security_invoker = true) as
  select t.id, t.account_id, a.nickname, t.date, t.amount, t.description, t.bank_status, t.review_status, t.source
  from public.transactions t join public.accounts a on a.id = t.account_id
  where t.review_status in ('needs_review','skipped')
  order by t.date, t.id;
revoke all on public.needs_review_transactions from anon, authenticated;

create view public.needs_review_by_account with (security_invoker = true) as
  select account_id, nickname, count(*) as items, sum(amount) as total,
         count(*) filter (where review_status = 'skipped') as skipped_before,
         min(date) as oldest
  from public.needs_review_transactions group by account_id, nickname;
revoke all on public.needs_review_by_account from anon, authenticated;
