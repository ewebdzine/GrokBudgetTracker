# Workflows

## Bot roles
- **One Finance bot owns the ledger.** It is the only bot that writes to the budget database. Other bots (email triage, chief of staff, etc.) send it facts: "log $X from <account> as a one-off for <payee>", "the user says this charge is Shopping".
- The Finance bot asks the user only when it can't decide, and never posts, pays or moves money.

## Daily sync (routine, e.g. 6 AM)
1. For each `accounts` row with `connected = true`: pull new transactions through the Finance connector since `last_synced_at` (with a few days of overlap for pending -> posted).
2. Upsert into `transactions` on `(account_id, source, external_id)`. New rows get `review_status = 'needs_review'`. When a pending item posts, update `bank_status` (`pending` -> `posted`), amount and date; that never changes `review_status`. Set `last_synced_at`.
3. If a connection fails, set `status = 'needs_reauth'` and tell the user.
4. Update `settings.balances` with the available balance.
5. Run matching (below), then queue anything left for categorizing.
6. Report only what needs the user: new uncategorized items, past-due bills, low balance. Say nothing if nothing changed.

## Daily huddle (routine, at the time you pick in ONBOARDING step 8)
Formerly "Daily Transaction Review" (same routine, renamed; the old name is an alias). Four parts, in order: transactions, bills, buckets, alerts.

### 1. Transactions
1. **Pull**: sync every `accounts` row with `connected = true` (see Daily sync). Non-connected accounts (cash, CSV-only) are skipped unless the user uploaded a file.
2. **Queue**: the review covers every row in `needs_review_transactions` (review_status `needs_review` or `skipped`), not just today's import, so missed days and earlier skips are included.
3. **Auto-apply obvious matches only**: a new outgoing transaction that matches exactly one unpaid `bill_instances` row by `payee_hint` and amount (within the bill's tolerance) is matched to that **recurring bill** automatically and set to `review_status = 'auto_applied'`. Nothing else is auto-applied: no guessing one-offs, buckets or splits.
4. **Headline**: "I found N transactions to review," then one line per account from `needs_review_by_account` with its count and total (and how many are left over from earlier days), for example
   `Bills checking (…1111): 4 transactions, -$1,382.50` / `Spending card (…2222): 3 transactions, -$61.20`.
   If there are only a few (about 8 or fewer), list them all (date, description, amount).
5. **Report auto-matches**: "Matched automatically: Electric $140.00 (due 1/12) -> cleared."
6. **Interview one transaction at a time** for everything else. Each question shows date, account, description, amount and offers prefilled options, best guess first:
   - for deposits: `Income: <source>` (creates or links an `income_events` row with `transaction_id` and `month`), `Income: one-off`, `Refund`, `Transfer`
   - `Recurring bill: <name>` (a near match: wrong amount or month)
   - `One-off bill: <category>`
   - `Budget bucket: <name>` (always include the bucket the charge most likely fits)
   - `Split…` (then ask the parts: target and amount for each, until the parts add up to the total)
   - `Skip for now` (sets `review_status = 'skipped'`; it comes back in the next review)
   - a typed answer (free text, e.g. "transfer to savings" or "refund").
7. **Write**: each answer sets `review_status = 'categorized'` and `reviewed_at`, and becomes `transaction_allocations` rows (one row for a single target, several for a split: `target_type` bill / one_off / bucket / debt with the matching id and amount; buckets get `budget_month`). Also set `transactions.expense_type`, `category_id` and the simple link column, mark bills `cleared`, create a `one_off_bills` row when needed, and add bucket amounts to `budget_months.spent`. Transfers and income don't create allocations; they set `matched_transfer` / `matched_income_event`.
8. **Income suggestions**: if `income_source_suggestions` has rows, ask "This deposit repeats about every N days at about $X. Add it as an income source?" (name, frequency, account) and link the past deposits.
9. **Recap**: updated balance for every bucket touched ("Groceries: $310 of $500, $190 left") and anything skipped.
10. `bank_status` (pending/posted) is shown for information only; pending items can be reviewed too.

### 2. Bills due
1. List unpaid `bill_instances` (fixed) and `one_off_bills` with `due_date` before today (overdue), today, or within the next 7 days: payee, amount, due date, overdue first.
2. **Pay-online links**: a bill's saved link is the `pay: <url>` line in its `notes` (saved from the bill photo, see Photo -> one-off bill). For each bill with a link, offer "Pay <payee> $<amount> now with your card on file?" Ask per bill. Pay only after the user says yes to that bill; never batch, never pay without a yes, never enter a new card. After paying, set `status = 'paid'`, `paid_date`, `paid_from`, and confirm "Paid with card on file •••• 1234".
3. Bills without a link: remind only.

### 3. Bucket chart
If any bucket's `spent` changed since the last huddle (new allocations), show the summary chart (`templates/bucket-chart.html`, summary view; see Showing buckets).

### 4. Over / near budget
Call out every bucket at 90% or more of plan ("Blow money: $10 left of $120") or over ("Gas is $12.40 over its $160"). If the user asks about one, show its single-bucket chart.

### Stay quiet
If there is nothing to review, nothing overdue or due within 7 days, and no bucket over budget, send nothing.

Sample routine prompt: [docs/routines.md](routines.md).

## Low balance watch (routine, every 4 hours during the day)
Checks each checking account so a bill doesn't bounce. Read only: it never moves money or pays anything.
1. **Balance**: current balance per checking account from the Finance connector (balances aren't stored in the ledger).
2. **Window**: today until the next expected deposit into that account (`income_sources.next_expected_date`, else its `due_day`; 35 days if no income is set up).
3. **Coming out before then**:
   - unpaid `bill_instances` and `one_off_bills` due in the window, paid from this account (or with no `paid_from` when it's the bills account), including ones up to 30 days overdue;
   - "usual" charges learned from transactions: the same payee in at least 2 of the last 3 months, $25 or more, not yet seen this month and not already a bill. Due date = its typical day of month; amount = its median. This catches the $500 insurance that always comes out around the 2nd even if it isn't set up as a bill.
4. **Threshold**: alert when the balance is negative (`negative`), less than the total coming out (`short`), or would end below the cushion after those bills (`below_cushion`, default $100, `settings.low_balance_watch.cushion`). `templates/low_balance_watch.sql` returns all of this as JSON (example: `templates/sample/low-balance-example.json`).
5. **Alert**: e.g. "Heads up: Checking has $420. Car Insurance $500 comes out Nov 2 and Water ~$48 around Nov 4, $548 total. You're $128 short until your paycheck ($1,850) on Nov 6." Offer to suggest a transfer, but don't make it.
6. **No repeats**: the last alert per account is saved in `settings` key `low_balance_watch` (`{"cushion": 100, "alerts": {"<account_id>": {"status": "short", "shortfall": 128, "bills": [...], "at": "..."}}}`). Same status, same or smaller shortfall and no new bill: stay quiet. When it's back to ok, clear the entry and say once that it's in the clear.

## Photo -> one-off bill (documents)
1. The user sends a photo or PDF of a bill or receipt in chat.
2. Grok reads it: payee, amount, due date, account/invoice number (kept to last 4), and what it's for. It never stores card numbers.
3. Grok **confirms** with one question: "Example Dental, $180.00, due 1/25 - save as `One-off bill: Medical`?" with options to fix any field, link it to an existing bill or transaction instead, or cancel.
4. On yes: upload the file to the `bill-documents` bucket at `<yyyy>/<mm>/<uuid>-<file>` and insert the `documents` row (`doc_type`, `sha256`, `ocr_text`). If the sha256 already exists, reuse that row and say so.
5. If the bill shows a pay-online link (a payment URL or "pay online at ..."), save it in the bill's `notes` as `pay: <url>` and tell the user it was saved.
6. Create the `one_off_bills` record (or link an existing one, a `bill_instances` row, or a transaction) and set the document's link column.
7. Later, to show it, Grok creates a signed URL (valid about 10 minutes) and opens or sends that. Never a public link.

How files get into Storage: the Supabase connector runs SQL but has no Storage upload tool. Use the optional Edge Function in `supabase/functions/bill-documents` (`/upload`, `/signed-url`, protected by a secret you set in Supabase and save in the Grok vault), or upload in the Supabase dashboard (Storage > bill-documents) and let Grok insert the row.

## Bill matching
For each new outgoing transaction:
1. **Fixed bills**: find an unpaid `bill_instances` row this month (or last month if overdue) whose template `payee_hint` matches the start of the description and whose amount is within tolerance (exact for most bills; utilities can vary). Set `matched_bill_instance`, `expense_type = 'recurring_fixed'`, instance `status = 'cleared'`, `paid_amount`, `paid_date`, `paid_from`.
2. **One-offs**: match an unpaid `one_off_bills` row by payee and amount; set `matched_one_off`, `expense_type = 'one_off'`, status `cleared`.
3. **Transfers**: description shows a move between two registered accounts (or a card payment) -> `expense_type = 'transfer'`, link or create a `transfers` row.
4. **Income**: a deposit matching an `income_sources` row (account, amount within tolerance, around the expected date) -> create or link an `income_events` row with `transaction_id`, set `matched_income_event`, `expense_type = 'income'`, and advance `next_expected_date`.
5. **Split payments**: one charge covering several bills or a bill plus bucket spending -> write `transaction_allocations` rows and check `allocation_check.unallocated = 0`.
Anything ambiguous stays uncategorized for the user.

## Categorizing (asking the user, outside the daily huddle)
- Show the full list first (date, amount, description, account), then **ask one item at a time** so the user can just tap or type an answer.
- Each option is labeled with what it is:
  - `One-off bill: <category>` (for example `One-off bill: Medical`)
  - `Budget bucket: <bucket name>` (for example `Budget bucket: Groceries`); include the matching bucket whenever the charge looks like it fits one
  - `Recurring bill: <bill name>` when it looks like a fixed bill
  - `Transfer` / `Income` / `Refund` when relevant
  - plus a free-text "Other" choice.
- Save the answer: set `expense_type`, `category_id`, the link column, and update `budget_months.spent` for buckets.
- If the user picks a bucket that doesn't exist, ask whether to create it (monthly amount and funding account).

## Month rollover (1st of the month)
1. Insert `bill_instances` for every active `bill_templates` row.
2. Insert `budget_months` for every bucket (`planned = monthly_amount`, `spent = 0`).
3. Unpaid one-offs stay visible (the snapshot includes unpaid older ones); set `carried_over_from` when moving one to the new month.
4. Create the planned `transfers` row for funding the spending account.
5. Generate the new month's Budget Plan PDF.

## Showing buckets (charts)
Whenever the user asks to see their buckets, their budget, how a bucket is doing, or "show me my groceries bucket", use the bucket chart template. Never draw a generic bar or pie chart.
1. Run `templates/bucket_chart.sql` through the Supabase connector for the month (`:month` = 'YYYY-MM-01'). It returns one JSON `chart` value: each bucket's `planned` and `spent` (`budget_months` + `spending_budgets`) and every bucket expense for the month (`transaction_allocations` with `target_type = 'bucket'`, joined to `transactions`).
2. Pick the view:
   - **All buckets / "my budget"**: `--view summary`. One card with each bucket's name, "$spent of $planned", a rounded bar and "$X left" or "$X over", plus the month total.
   - **One bucket**: `--view single --bucket "<name>"`. Big "$X left of $Y" (or "$X over the $Y plan"), the bar, then every expense from the 1st to the last day of the month under small grey date headings.
3. Render: save the JSON to a file and run `python3 templates/render_bucket_chart.py chart.json --view summary --out buckets.png`. Then send the PNG. It uses headless Chrome, and Pillow trims the margin if it's installed.
4. Colors: purple #8350f2 when on track, amber at 90% or more used, red when over budget, green for money left overall. White Grok theme with the purple blob.
5. In a Page, use the dashboard Page's bucket section (`templates/dashboard.canvas.tsx`), which shows the same spent / planned / left-or-over numbers.

## Dashboard and PDFs
1. `select public.dashboard_snapshot('YYYY-MM-01');` through the Supabase connector; save the JSON to a file and add `"pulled_at": "YYYY-MM-DD"`.
2. `python3 templates/build_reports.py snapshot.json --config templates/config.json --out ./output`
3. Output: `YYYY-MM.html`, `YYYY-MM-budget-plan.pdf`, `YYYY-MM-where-the-money-went.pdf`. Check the PDFs visually (`pdftoppm -r 60 -png file.pdf page`) before sending.
4. Blank pencil versions: `python3 templates/build_blank.py --config templates/config.json`.
