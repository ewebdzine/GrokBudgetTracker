-- 0001_init_budget_schema.sql: core tables, indexes, deny-all RLS (no policies; access is server-side only).
-- Money convention: bills/budgets positive; in transactions, negative = money out.
create table public.accounts (id text primary key, name text not null, institution text, mask text, plaid_account_id text unique, kind text not null default 'checking', notes text);
create table public.income_sources (id text primary key, name text not null, expected_amount numeric(12,2) not null, due_day int, account_id text references public.accounts, active boolean not null default true);
create table public.income_events (id text primary key, source_id text references public.income_sources, month date not null, received_date date, amount numeric(12,2) not null,
  account_id text references public.accounts, plaid_id text, kind text not null default 'income' check (kind in ('income','one_off_income','refund','transfer_in')), inferred boolean not null default false, notes text);
create table public.bill_templates (id text primary key, name text not null, default_amount numeric(12,2) not null, due_day int, week int, category text, payee_hint text, unverified boolean not null default false, active boolean not null default true);
create table public.bill_instances (id bigint generated always as identity primary key, template_id text not null references public.bill_templates, month date not null, due_date date, amount numeric(12,2) not null,
  estimated boolean not null default false, status text not null default 'unpaid' check (status in ('unpaid','paid','cleared')), paid_amount numeric(12,2), paid_date date, paid_from text, cleared_plaid_id text, notes text, unique (template_id, month));
create table public.one_off_bills (id text primary key, payee text not null, amount numeric(12,2) not null, month date not null, received_date date, due_date date, receipt_path text, carried_over_from date,
  status text not null default 'unpaid' check (status in ('unpaid','paid','cleared')), paid_date date, paid_from text, cleared_plaid_id text, unverified boolean not null default false, notes text);
create table public.spending_budgets (id text primary key, name text not null, monthly_amount numeric(12,2) not null, funded_by text, sort int);
create table public.budget_months (id bigint generated always as identity primary key, budget_id text not null references public.spending_budgets, month date not null, planned numeric(12,2) not null, spent numeric(12,2) not null default 0, unique (budget_id, month));
create table public.transactions (id bigint generated always as identity primary key, plaid_id text not null unique, account_id text not null references public.accounts, date date not null, amount numeric(12,2) not null,
  description text, category text, pending boolean not null default false,
  matched_bill_instance bigint references public.bill_instances on delete set null, matched_one_off text references public.one_off_bills on delete set null);
create table public.transfers (id text primary key, month date not null, from_account text, to_account text, amount numeric(12,2) not null, planned_amount numeric(12,2), date date, plaid_id text, status text, notes text);
create table public.debts (id bigint generated always as identity primary key, snowball_order int not null, name text not null unique, apr numeric(6,3) not null default 0, min_payment numeric(12,2) not null default 0, starting_balance numeric(12,2) not null, as_of date not null, active boolean not null default true);
create table public.debt_payments (id bigint generated always as identity primary key, debt_id bigint not null references public.debts on delete cascade, date date not null, amount numeric(12,2) not null, plaid_id text, notes text);
create table public.settings (key text primary key, value jsonb not null);

create index on public.bill_instances (month); create index on public.transactions (account_id, date);
create index on public.transactions (matched_bill_instance); create index on public.transactions (matched_one_off);
create index on public.debt_payments (debt_id); create index on public.budget_months (budget_id);
create index on public.income_events (source_id); create index on public.income_events (account_id);
create index on public.income_sources (account_id); create index on public.bill_instances (template_id);

do $$ declare t text; begin
  foreach t in array array['accounts','income_sources','income_events','bill_templates','bill_instances','one_off_bills','spending_budgets','budget_months','transactions','transfers','debts','debt_payments','settings']
  loop execute format('alter table public.%I enable row level security', t);
       execute format('revoke all on public.%I from anon, authenticated', t); end loop; end $$;
