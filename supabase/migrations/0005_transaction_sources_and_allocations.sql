-- 0005_transaction_sources_and_bill_payments.sql
-- `transactions` is generic: any source (bank/card via Plaid, Venmo, PayPal, CSV import, manual entry).
-- Every row belongs to a registered account (accounts.id; account types include venmo, paypal, cash).
-- Adds transaction_allocations: split one transaction across bills, one-offs, budget buckets and debts.

alter table public.transactions
  add column if not exists source text not null default 'plaid',
  add column if not exists external_id text,
  add column if not exists imported_at timestamptz not null default now();
update public.transactions set external_id = plaid_id where external_id is null;
alter table public.transactions
  alter column external_id set not null,
  alter column plaid_id drop not null,
  add constraint transactions_source_chk check (source in ('plaid','venmo','paypal','csv','manual')),
  add constraint transactions_plaid_id_chk check (source <> 'plaid' or plaid_id is not null),
  add constraint transactions_source_ext_uniq unique (account_id, source, external_id);
-- external_id = Plaid transaction id, Venmo/PayPal transaction id, a hash of the CSV row, or manual-<date>-<n>.

create table if not exists public.transaction_allocations (
  id bigint generated always as identity primary key,
  transaction_id bigint not null references public.transactions(id) on delete cascade,
  target_type text not null check (target_type in ('bill','one_off','bucket','debt')),
  bill_instance_id bigint references public.bill_instances(id) on delete cascade,      -- target_type = 'bill'
  one_off_bill_id text references public.one_off_bills(id) on update cascade on delete cascade, -- 'one_off'
  spending_budget_id text references public.spending_budgets(id) on update cascade on delete cascade, -- 'bucket'
  budget_month date,                                                                   -- month the bucket spend counts in
  debt_id bigint references public.debts(id) on delete cascade,                        -- 'debt'
  amount numeric(12,2) not null check (amount > 0),
  notes text,
  created_at timestamptz not null default now(),
  constraint ta_exactly_one_target_chk check (num_nonnulls(bill_instance_id, one_off_bill_id, spending_budget_id, debt_id) = 1),
  constraint ta_target_matches_type_chk check (
       (target_type='bill'    and bill_instance_id   is not null)
    or (target_type='one_off' and one_off_bill_id    is not null)
    or (target_type='bucket'  and spending_budget_id is not null and budget_month is not null)
    or (target_type='debt'    and debt_id            is not null)));
create index if not exists ta_tx_idx     on public.transaction_allocations (transaction_id);
create index if not exists ta_bill_idx   on public.transaction_allocations (bill_instance_id);
create index if not exists ta_oo_idx     on public.transaction_allocations (one_off_bill_id);
create index if not exists ta_bucket_idx on public.transaction_allocations (spending_budget_id, budget_month);
create index if not exists ta_debt_idx   on public.transaction_allocations (debt_id);
alter table public.transaction_allocations enable row level security;
revoke all on public.transaction_allocations from anon, authenticated;

-- Rule: a transaction is split when it has allocation rows; the rows should sum to abs(transactions.amount)
-- (the bot checks this with the view below). Unsplit transactions keep using matched_bill_instance /
-- matched_one_off / matched_budget from 0001/0004. Then transactions.expense_type = 'split' is not used;
-- instead expense_type holds the type of the largest allocation and the view shows the full split.
create or replace view public.allocation_check with (security_invoker = true) as
  select t.id as transaction_id, t.date, t.amount, sum(a.amount) as allocated,
         abs(t.amount) - sum(a.amount) as unallocated, count(*) as parts
  from public.transactions t join public.transaction_allocations a on a.transaction_id = t.id
  group by t.id, t.date, t.amount;
revoke all on public.allocation_check from anon, authenticated;
