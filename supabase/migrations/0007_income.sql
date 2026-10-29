-- 0007_income.sql
-- Income already exists since 0001: income_sources (expected) and income_events (actual money in).
-- This migration EXTENDS them instead of adding duplicate tables:
--   * income_sources: frequency, next_expected_date, notes
--   * income_events:  transaction_id link to the matching deposit in transactions
--   * view `income`: the simple "what came in, when, how much" table
--   * view monthly_income: expected vs received per source per month
--   * view income_source_suggestions: recurring deposits that aren't a source yet

alter table public.income_sources
  add column if not exists frequency text not null default 'monthly',
  add column if not exists next_expected_date date,
  add column if not exists notes text;
alter table public.income_sources
  add constraint income_sources_frequency_chk check (frequency in ('weekly','biweekly','semimonthly','monthly','irregular'));
-- expected_amount = amount per payment; due_day stays for monthly sources (day of month).

alter table public.income_events
  add column if not exists transaction_id bigint references public.transactions(id) on delete set null;
create unique index if not exists income_events_transaction_uniq on public.income_events (transaction_id) where transaction_id is not null;
create index if not exists income_events_month_idx on public.income_events (month);
-- backfill the link from the Plaid id where one exists
update public.income_events e set transaction_id = t.id
  from public.transactions t where e.transaction_id is null and e.plaid_id is not null and t.plaid_id = e.plaid_id;

-- The income table, as a readable view (write to income_events).
create or replace view public.income with (security_invoker = true) as
  select e.id, e.received_date as date_received, e.amount, e.source_id, s.name as source_name, e.kind,
         e.account_id, e.transaction_id, e.month, e.inferred, e.notes
  from public.income_events e left join public.income_sources s on s.id = e.source_id
  where e.kind <> 'refund';
revoke all on public.income from anon, authenticated;

-- Number of expected payments of a source in a month.
create or replace function public.income_expected_count(p_freq text, p_anchor date, p_due_day int, p_month date)
returns int language sql immutable set search_path = '' as $$
  select case p_freq
    when 'monthly' then 1
    when 'semimonthly' then 2
    when 'irregular' then 0
    else (select count(*)::int from generate_series(
            coalesce(p_anchor, p_month) - (case p_freq when 'weekly' then 7 else 14 end) * 400,
            coalesce(p_anchor, p_month) + (case p_freq when 'weekly' then 7 else 14 end) * 400,
            make_interval(days => case p_freq when 'weekly' then 7 else 14 end)) d
          where d >= p_month and d < p_month + interval '1 month')
  end $$;
revoke all on function public.income_expected_count(text,date,int,date) from public, anon, authenticated;

create or replace view public.monthly_income with (security_invoker = true) as
  with months as (select distinct month from public.income_events
                  union select date_trunc('month', current_date)::date)
  select m.month, s.id as source_id, s.name as source_name, s.frequency,
         s.expected_amount * public.income_expected_count(s.frequency, s.next_expected_date, s.due_day, m.month) as expected,
         coalesce((select sum(e.amount) from public.income_events e
                   where e.source_id = s.id and e.month = m.month and e.kind = 'income'), 0) as received
  from months m cross join public.income_sources s where s.active
  union all
  select m.month, null, 'Other income (one-off, transfers in)', null, 0,
         coalesce((select sum(e.amount) from public.income_events e
                   where e.month = m.month and e.kind in ('one_off_income','transfer_in')), 0)
  from months m;
revoke all on public.monthly_income from anon, authenticated;

-- Deposits that repeat (same description start, 2+ times in 120 days) and aren't linked to income yet.
create or replace view public.income_source_suggestions with (security_invoker = true) as
  select t.account_id, upper(left(regexp_replace(t.description, '[0-9#*]+', '', 'g'), 24)) as description_key,
         count(*) as deposits, round(avg(t.amount), 2) as avg_amount, min(t.date) as first_seen, max(t.date) as last_seen,
         case when count(*) > 1 then (max(t.date) - min(t.date)) / (count(*) - 1) end as avg_days_between
  from public.transactions t
  where t.amount > 0 and t.date >= current_date - 120
    and not exists (select 1 from public.income_events e where e.transaction_id = t.id)
    and t.matched_income_event is null and coalesce(t.expense_type, '') <> 'transfer'
  group by 1, 2 having count(*) >= 2;
revoke all on public.income_source_suggestions from anon, authenticated;
