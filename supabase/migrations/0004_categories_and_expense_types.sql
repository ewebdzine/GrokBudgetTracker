-- 0004_categories_and_expense_types.sql
-- Replaces free-text categories with a lookup (`categories`), and records WHAT KIND of expense each
-- transaction is (`expense_types`), with the matching link: bill_instances, one_off_bills or spending_budgets.
-- Extends what 0001 already has: transactions.category (free text, kept as a display label),
-- transactions.matched_bill_instance and transactions.matched_one_off (kept, reused).

create table if not exists public.expense_types (
  id text primary key,            -- one_off | recurring_fixed | budget_bucket | transfer | income
  label text not null,
  description text);
insert into public.expense_types (id,label,description) values
 ('recurring_fixed','Recurring / fixed bill','Matched to a bill_instances row (from bill_templates)'),
 ('one_off','One-off bill','Matched to a one_off_bills row'),
 ('budget_bucket','Budget bucket','Counts against a spending_budgets bucket for the month'),
 ('transfer','Transfer','Money moving between your own registered accounts; not spending'),
 ('income','Income','Deposits, one-off income and refunds (see income_events)')
on conflict (id) do nothing;

create table if not exists public.categories (
  id text primary key,
  name text not null unique,
  parent_group text,              -- report grouping, e.g. 'Housing & Loan'
  default_expense_type text references public.expense_types(id),
  sort int,
  active boolean not null default true);

alter table public.bill_templates   add column if not exists category_id text references public.categories(id) on update cascade;
alter table public.spending_budgets add column if not exists category_id text references public.categories(id) on update cascade;
alter table public.one_off_bills    add column if not exists category_id text references public.categories(id) on update cascade;

alter table public.transactions
  add column if not exists category_id     text references public.categories(id) on update cascade,
  add column if not exists expense_type    text references public.expense_types(id),
  add column if not exists matched_budget  text references public.spending_budgets(id) on update cascade on delete set null,
  add column if not exists matched_transfer text references public.transfers(id) on update cascade on delete set null,
  add column if not exists matched_income_event text references public.income_events(id) on update cascade on delete set null;

-- exactly the right link for the type (null expense_type = not yet categorized)
alter table public.transactions add constraint transactions_expense_link_chk check (
  expense_type is null
  or (expense_type='recurring_fixed' and matched_bill_instance is not null)
  or (expense_type='one_off'         and matched_one_off is not null)
  or (expense_type='budget_bucket'   and matched_budget is not null)
  or (expense_type='transfer')
  or (expense_type='income'));

create index if not exists tx_expense_type_idx on public.transactions (expense_type);
create index if not exists tx_category_idx     on public.transactions (category_id);
create index if not exists tx_budget_idx       on public.transactions (matched_budget);
create index if not exists tx_transfer_idx     on public.transactions (matched_transfer);
create index if not exists tx_income_idx       on public.transactions (matched_income_event);

alter table public.expense_types enable row level security; revoke all on public.expense_types from anon, authenticated;
alter table public.categories    enable row level security; revoke all on public.categories    from anon, authenticated;

-- what still needs a decision from the user (feeds the one-at-a-time categorizing prompt)
create or replace view public.uncategorized_transactions with (security_invoker = true) as
  select t.id, t.date, t.amount, t.description, t.account_id, t.pending
  from public.transactions t where t.expense_type is null order by t.date;
revoke all on public.uncategorized_transactions from anon, authenticated;
