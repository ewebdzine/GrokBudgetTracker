-- 0003_bank_accounts_registry.sql
-- Makes bank-account registration required: every tracked account is a row in public.accounts,
-- and every money-moving table references accounts.id by foreign key.
-- Safe to run on a fresh install after 0001/0002. On an existing database, review the
-- backfill notes first (text values in paid_from / funded_by / transfers must already be valid account ids).

alter table public.accounts
  add column if not exists nickname        text,
  add column if not exists account_type    text,
  add column if not exists last4           text,
  add column if not exists owner_name      text,
  add column if not exists plaid_item_id   text,
  add column if not exists connected       boolean not null default false,
  add column if not exists connected_at    timestamptz,
  add column if not exists last_synced_at  timestamptz,
  add column if not exists status          text not null default 'active',
  add column if not exists active          boolean not null default true,
  add column if not exists funding_role    text not null default 'none',
  add column if not exists created_at      timestamptz not null default now();

-- backfill from the original columns (name/mask/kind)
update public.accounts set nickname = coalesce(nickname, name), last4 = coalesce(last4, mask),
  account_type = coalesce(account_type, case when kind in ('checking','savings','credit_card') then kind
                                              when kind in ('credit','card') then 'credit_card' when kind in ('venmo','paypal','cash') then kind else 'checking' end);

alter table public.accounts
  alter column nickname set not null,
  alter column account_type set not null,
  alter column institution set not null,
  add constraint accounts_type_chk   check (account_type in ('checking','savings','credit_card','venmo','paypal','cash','loan','other')),
  add constraint accounts_last4_chk  check (last4 is null or last4 ~ '^[0-9]{4}$'),
  add constraint accounts_status_chk check (status in ('active','needs_reauth','disconnected','closed')),
  add constraint accounts_role_chk   check (funding_role in ('bills','spending','savings','debt','income','none')),
  add constraint accounts_plaid_chk  check (not connected or (plaid_item_id is not null and plaid_account_id is not null));
-- `mask` and `kind` are kept for backward compatibility (dashboard_snapshot / older prompts); new code should use last4 / account_type.

-- foreign keys to accounts.id
alter table public.bill_instances   add constraint bill_instances_paid_from_fk  foreign key (paid_from)    references public.accounts(id) on update cascade;
alter table public.one_off_bills    add constraint one_off_bills_paid_from_fk   foreign key (paid_from)    references public.accounts(id) on update cascade;
alter table public.spending_budgets add constraint spending_budgets_funded_by_fk foreign key (funded_by)   references public.accounts(id) on update cascade;
alter table public.transfers        add constraint transfers_from_account_fk    foreign key (from_account) references public.accounts(id) on update cascade;
alter table public.transfers        add constraint transfers_to_account_fk      foreign key (to_account)   references public.accounts(id) on update cascade;
alter table public.debts            add column if not exists account_id text references public.accounts(id) on update cascade;
-- transactions.account_id and income_events/income_sources.account_id already reference accounts (0001).

create index if not exists on_bill_instances_paid_from on public.bill_instances (paid_from);
create index if not exists on_one_off_paid_from        on public.one_off_bills (paid_from);
create index if not exists on_budgets_funded_by        on public.spending_budgets (funded_by);
create index if not exists on_transfers_from           on public.transfers (from_account);
create index if not exists on_transfers_to             on public.transfers (to_account);
create index if not exists on_debts_account            on public.debts (account_id);

-- the setup gate: the bot refuses to sync/categorize until this returns at least one row
create or replace view public.registered_accounts with (security_invoker = true) as
  select id, nickname, institution, account_type, last4, owner_name, funding_role, connected, status, last_synced_at
  from public.accounts where active;
revoke all on public.registered_accounts from anon, authenticated;
