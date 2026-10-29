# Onboarding

Go step by step. The bot should explain each step in plain language and wait for your OK before it changes anything.

## 1. Supabase account and project
1. Create a free Supabase account at [supabase.com/dashboard/sign-up](https://supabase.com/dashboard/sign-up). Most people will need to create a new account. If you already have **GitHub** or **ChatGPT**, you can use **Continue with GitHub** / **Continue with ChatGPT** and skip making a password; otherwise use the email and password form (any email, including Gmail, works). Supabase does not offer Google sign-in. Skip **Continue with SSO** unless your employer's IT has set up single sign-on with Supabase.
2. Create one project. Pick a region near you and save the database password in your password manager (the bot does not need it).
3. Free-plan caveats: no automatic backups, projects pause after about a week with no activity, two active free projects per account. Consider Pro if you rely on it daily (check Supabase's current pricing).

## 2. Connect the Supabase connector
In Grok Bot, add the Supabase connector and sign in **with the same Supabase account you just created** (same GitHub, ChatGPT or email login), otherwise Grok won't see your project. Ask the bot: *"List my Supabase projects."* Confirm it shows the project you just made. Tell the bot that project is the budget ledger.

## 3. Apply migrations in order
Ask: *"Apply GrokBudgetTracker migration 0001 to my budget project. Explain it first."* Repeat for 0002 through 0006. Each file is applied as its own migration with the same name. Afterwards ask the bot to run Supabase's security advisor; the only expected notice is "RLS enabled, no policy" (intentional: deny-all).

## 4. Categories (Grok-led interview)
`supabase/seed_categories.sql` preloads a standard category list: the core set (housing, utilities, insurance, groceries, fuel, dining out, medical, transfers, income ...) plus **common optional categories** taken from widely used budget templates (YNAB, Ramsey, 50/30/20 lists): childcare, kids activities, pets and vet, personal care, clothing, health/pharmacy, fitness, phone, car payment, parking/transit, household supplies, lawn and garden, HOA, home improvement, charitable giving, holidays, travel, hobbies, fun money, emergency fund, retirement, education savings, annual fees, work expenses, miscellaneous.

The bot runs this as an interview; you don't edit SQL:
1. **Show the full list first**, grouped by `parent_group` (Housing & Loan, Utilities, Insurance, Spending, One-off, Kids, Savings / Investing, Transfers, Income, ...), each with its type (recurring bill, budget bucket, one-off).
2. **Ask one category at a time**, as a question with options `Keep`, `Drop`, `Rename…` and a typed answer. It can go a group at a time ("Keep all of Utilities?") when you'd rather move fast. The optional categories are shown as suggestions.
3. **Ask whether you want to add your own**: for each one, name, group, and type (`Recurring bill`, `Budget bucket` or `One-off bill`). Repeat until you say done.
4. **Confirm**: it shows the final kept/added list, then loads the seed and saves your choices (dropped ones are set `active = false`, so they can come back later).

## 5. Register and connect your bank accounts (required)
The bot will not sync or categorize until at least one account is registered (`select * from registered_accounts`).

**5a. Register each account.** For every checking, savings or credit-card account you want tracked, tell the bot:
- a short id (for example `chk-bills`, `card-spend`, `cc-payoff`),
- nickname, institution, type (`checking`, `savings`, `credit_card`, `venmo`, `paypal`, `cash`, `loan`, `other`), last 4 digits, owner name,
- funding role: `bills` (pays fixed bills), `spending` (funds budget buckets), `savings`, `debt` (a card or loan you are paying off), `income` (where deposits land), or `none`.

The bot inserts one `accounts` row per account with `connected = false`.

**5b. Connect each bank through the Finance connector.** Grok Bot's Finance connector uses Plaid for bank links. Use the Finance connector's connect prompt in Grok Bot to link each institution. You sign in to your bank in Plaid's own window; never give the bot your bank password.

**5c. Verify the connection.** Ask: *"List my connected finance accounts."* The bot calls the Finance connector's list-connections and list-accounts tools and shows each account's name, type and last 4 (mask). For each one, it proposes the matching `accounts` row by **last 4 and nickname** and asks you to confirm. Anything it can't match, it asks you about rather than guessing.

**5d. Record the Plaid ids.** For each confirmed match the bot updates the row: `plaid_item_id` (the connection), `plaid_account_id`, `connected = true`, `connected_at = now()`, `status = 'active'`. The table enforces that a connected account has both Plaid ids.

**5e. Run a test sync.** Ask: *"Do a test sync of <nickname> for the last 7 days, but don't save anything yet."* The bot pulls transactions through the Finance connector and shows a few rows with dates and amounts so you can compare them to your bank's app. When they match, say "save it": rows go into `transactions` with `account_id`, `source = 'plaid'` and `external_id` (the Plaid transaction id, also kept in `plaid_id`) as the dedupe key, and the bot sets `last_synced_at`. Every imported row starts as `review_status = 'needs_review'`; the bank's pending/posted state is stored separately in `bank_status`.

**5f. Banks that won't connect.** If an institution isn't available or keeps failing:
- keep the account with `connected = false` and `status = 'disconnected'`;
- **manual entry**: tell the bot each transaction ("$42.10 at the hardware store on the 3rd from card-spend"); it saves it with `source = 'manual'` and an `external_id` like `manual-<date>-<n>`;
- **CSV**: download a CSV from your bank's website and send it to the bot; it maps the columns (date, description, amount), shows you a preview, and imports with `source = 'csv'` and `external_id` = a hash of the row, so re-imports don't duplicate.
- **Venmo / PayPal / cash**: register them as accounts of type `venmo`, `paypal` or `cash`. Import their activity by CSV export or manual entry with `source = 'venmo'` / `'paypal'` (use their transaction id as `external_id`) or `'manual'` for cash.
If a connection later needs re-login, the bot sets `status = 'needs_reauth'` and tells you.

## 6. Income, bills, buckets and debts (Grok-led interview)
The bot asks **one question at a time** (a choice widget with a typed answer). Options are labeled `Recurring bill: <category>` or `Budget bucket: <name>` so it's clear what each entry becomes.
1. **Settings**: your snowball extra per month (can be $0). Balances fill in from the first sync.
2. **Income sources** (fills `income_sources`), one at a time: name, amount per payment, frequency (`weekly`, `biweekly`, `semimonthly`, `monthly`, `irregular`), next expected date (or day of month), and which account it lands in. "Any more income?" until you say no.
3. **Fixed / recurring bills**, one at a time: name, amount, due day (or week of the month if it varies), category (`Recurring bill: Utilities`, `Recurring bill: Insurance`, ...), and which registered account pays it. It also asks for a word from the bank description so it can match it later, or offers to learn it from the first payment it sees.
4. **Budget buckets**, one at a time: which bucket (`Budget bucket: Groceries`, `Budget bucket: Fuel`, ... from the categories you kept), monthly amount, and the funding account.
5. **Debts**, one at a time: name, current balance, APR, minimum payment, the linked account if it's a card or loan, then the snowball order (smallest balance first by default).
6. **Summary and confirm**: before saving anything, it shows a summary (income total, each bill with due day and paying account, buckets with totals, debts in snowball order, and what's left over each month). You can fix any line, then say "save". It writes `income_sources`, `bill_templates`, `spending_budgets`, `debts` and `settings`, and creates this month's `bill_instances` and `budget_months` rows.

## 7. Reports
Copy `templates/config.example.json` to `templates/config.json`, set labels and the bills/spending account ids, then ask: *"Build this month's dashboard and PDFs."*

## 8. Daily Transaction Review and other routines
Pick the time you want your **Daily Transaction Review** each morning (for example 7:00 AM). The bot creates a routine from the sample prompt in [docs/routines.md](docs/routines.md). How it works: [docs/workflows.md#daily-transaction-review](docs/workflows.md). The review covers every `needs_review` (and previously skipped) transaction, including backlog from days it didn't run, with a count per account. Optionally add the month-rollover and month-end report routines from the same file.
