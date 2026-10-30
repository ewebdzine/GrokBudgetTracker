-- Low balance watch (read-only). Run through the Supabase connector once per checking account.
-- Replace :account_id ('chk-main'), :balance (current balance from the Finance connector, e.g. 420.00),
-- :today ('YYYY-MM-DD', local date) and :cushion (default 100; settings.low_balance_watch.cushion if set).
-- Balances are not stored in the ledger; they come live from the Finance connector. No schema change.
-- Window = today .. day before the next expected income deposit into this account (max 35 days).
-- Upcoming outflows = (a) unpaid bill_instances / one_off_bills due in the window, paid from this account
-- (or with no paid_from when this is the bills account), plus (b) "usual" charges learned from past
-- transactions: the same description seen in at least 2 of the last 3 months, typical day of month in the
-- window, not yet seen this month and not already covered by a bill in (a). Amount = median of past charges.
with p as (
  select :account_id::text as account_id, (:balance)::numeric as balance, (:today)::date as today, (:cushion)::numeric as cushion
),
acct as (select a.id, a.funding_role from public.accounts a, p where a.id = p.account_id),
next_income as (
  select s.name, s.expected_amount,
         coalesce(s.next_expected_date,
                  case when s.due_day is not null then
                    case when make_date(extract(year from p.today)::int, extract(month from p.today)::int, least(s.due_day, 28)) >= p.today
                         then make_date(extract(year from p.today)::int, extract(month from p.today)::int, least(s.due_day, 28))
                         else (make_date(extract(year from p.today)::int, extract(month from p.today)::int, least(s.due_day, 28)) + interval '1 month')::date end
                  end) as expected_date
  from public.income_sources s, p
  where s.active and (s.account_id = p.account_id or s.account_id is null)
),
win as (
  select p.*, coalesce((select min(expected_date) from next_income where expected_date >= p.today), p.today + 35) as income_date
  from p
),
bills as (
  select t.name as bill, i.amount, i.due_date, 'recurring_bill' as source
  from public.bill_instances i join public.bill_templates t on t.id = i.template_id, win w
  where i.status = 'unpaid' and i.due_date < w.income_date and i.due_date >= w.today - 30
    and (i.paid_from = w.account_id or (i.paid_from is null and exists (select 1 from acct where funding_role = 'bills')))
  union all
  select o.payee, o.amount, o.due_date, 'one_off_bill'
  from public.one_off_bills o, win w
  where o.status = 'unpaid' and o.due_date is not null and o.due_date < w.income_date and o.due_date >= w.today - 30
    and (o.paid_from = w.account_id or (o.paid_from is null and exists (select 1 from acct where funding_role = 'bills')))
),
hist as (
  select lower(regexp_replace(coalesce(t.description, ''), '[0-9#*]+', '', 'g')) as key,
         min(t.description) as label, t.date, -t.amount as amount
  from public.transactions t, win w
  where t.account_id = w.account_id and t.amount < 0 and not t.pending
    and t.date >= (date_trunc('month', w.today) - interval '3 months') and t.date < date_trunc('month', w.today)
  group by 1, t.date, t.amount
),
usual as (
  select key, min(label) as label,
         percentile_cont(0.5) within group (order by amount)::numeric(12,2) as amount,
         round(percentile_cont(0.5) within group (order by extract(day from date)))::int as typical_day,
         count(distinct date_trunc('month', date)) as months_seen
  from hist where key <> '' group by key
  having count(distinct date_trunc('month', date)) >= 2
),
learned as (
  select u.label as bill, u.amount,
         case when make_date(extract(year from w.today)::int, extract(month from w.today)::int, least(u.typical_day, 28)) >= w.today
              then make_date(extract(year from w.today)::int, extract(month from w.today)::int, least(u.typical_day, 28))
              else (make_date(extract(year from w.today)::int, extract(month from w.today)::int, least(u.typical_day, 28)) + interval '1 month')::date end as due_date,
         'usual_charge' as source
  from usual u, win w
  where u.amount >= 25
    and not exists (select 1 from public.transactions t where t.account_id = w.account_id and t.amount < 0
                    and t.date >= date_trunc('month', w.today)
                    and lower(regexp_replace(coalesce(t.description, ''), '[0-9#*]+', '', 'g')) = u.key)
    and not exists (select 1 from bills b where u.key like '%' || lower(split_part(b.bill, ' ', 1)) || '%')
),
upcoming as (
  select * from bills
  union all
  select l.* from learned l, win w where l.due_date < w.income_date
)
select jsonb_build_object(
  'account_id', w.account_id,
  'balance', w.balance,
  'cushion', w.cushion,
  'next_income', (select jsonb_build_object('name', n.name, 'amount', n.expected_amount, 'date', n.expected_date)
                  from next_income n where n.expected_date >= w.today order by n.expected_date limit 1),
  'upcoming', coalesce((select jsonb_agg(jsonb_build_object('bill', u.bill, 'amount', u.amount, 'due_date', u.due_date, 'source', u.source) order by u.due_date) from upcoming u), '[]'::jsonb),
  'upcoming_total', coalesce((select sum(amount) from upcoming), 0),
  'projected_after_bills', w.balance - coalesce((select sum(amount) from upcoming), 0),
  'shortfall', greatest(0, coalesce((select sum(amount) from upcoming), 0) - w.balance),
  'status', case when w.balance < 0 then 'negative'
                 when w.balance < coalesce((select sum(amount) from upcoming), 0) then 'short'
                 when w.balance - coalesce((select sum(amount) from upcoming), 0) < w.cushion then 'below_cushion'
                 else 'ok' end
) as watch
from win w;
