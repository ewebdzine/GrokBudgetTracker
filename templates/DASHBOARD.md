# Interactive dashboard Page (default monthly view)

`dashboard.canvas.tsx` is a Grok Bot Page (a React `.canvas.tsx` using `grok/canvas` components). It is the **default** monthly budget view; the PDFs from `build_reports.py` are the printable option. Which ones a user gets is stored in `settings.reports` (`{"page": true, "pdf": false}`), set in ONBOARDING step 7.

The file in this repo holds **fake sample data** in one `DATA` constant at the top. Each month Grok replaces only that constant.

## How Grok fills it each month
1. **Query Supabase** (read-only, through the Supabase connector) for the month, using the queries below.
2. **Embed the data**: rebuild the `DATA` object (month label, as-of date, and the arrays below). Keep the component code unchanged.
3. **Publish to the same Page**: the first time, `WriteCanvas` with a title like "Budget Dashboard" and save the returned `canvas_id` in `settings` (key `dashboard_canvas_id`). Every later month, update that Page with `EditCanvas` (replace the `DATA` block) or `WriteCanvas` with the saved `canvas_id`. Don't create a new Page each month. If you want a history, export the PDFs instead.
4. If `settings.reports.pdf` is true, also run `build_reports.py` and send the PDFs.

## What feeds each section
| Section | `DATA` field | Source |
|---|---|---|
| Headline: income received vs expected | `income[]` | `select source_name, frequency, expected, received from monthly_income where month = :m and source_id is not null` |
| Headline: bills paid/unpaid, Bills table + Segmented (All / Unpaid / Paid) | `bills[]` | `dashboard_snapshot(:m) -> 'bills'` (recurring instances with template name, category, due date, status) and `-> 'one_offs'` (kind `One-off`) |
| Headline: bucket spend vs budget, Budget buckets bars | `buckets[]` | `dashboard_snapshot(:m) -> 'budgets'` (budget_months planned/spent joined to spending_budgets) |
| Left over (planned) | computed | income received - all bills planned - bucket budgets |
| Income table (Segmented: Buckets / Income) | `income[]` | `monthly_income` as above |
| Needs review | `review[]` | `select nickname, items, total, skipped_before, oldest from needs_review_by_account` (label accounts by nickname and last 4 from `accounts`) |
| Debt snowball | `debts[]`, `snowball` | `dashboard_snapshot(:m) -> 'debts'` + `settings.snowball`; payoff months, clear dates and interest from the same simulation `build_reports.py` prints (`snowball` in its JSON output) |

Notes:
- Amounts are plain numbers; the Page formats them.
- Never put account numbers beyond the last 4, Plaid ids, or keys in `DATA`.
- The Page shows status as of the date in `asOf`; it is not live. Grok refreshes it after the Daily Transaction Review or at month end.
