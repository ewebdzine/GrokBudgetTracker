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
| Headline: income received vs expected, Income table | `income[]` (`source`, `frequency`, `expected`, `received`) | `select source_name as source, frequency, expected, received from monthly_income where month = :m and source_id is not null`. The `source_id is not null` filter drops the "Other income (one-off, transfers in)" row, so one-off income and transfers in are not counted in the headline. Refunds are never income. |
| Headline: bills paid/unpaid, Bills table + Segmented (All / Unpaid / Paid) and a List / By week toggle | `bills[]` (`name`, `kind`, `category`, `due`, `amount`, `status`) | `dashboard_snapshot(:m) -> 'bills'`: `name`, `category`, `due_date`, `amount`, `status`, with `kind` = `Recurring`. Plus `-> 'one_offs'` (raw `one_off_bills` rows, including unpaid ones carried over from earlier months): `name` = `payee`, `kind` = `One-off`, `due` from `due_date`. One-offs have no text `category`; look up `categories.name` by `category_id`, or leave `category` as `""` (the Page then shows just the kind). Format `due` as `M/D`. |
| Headline: bucket spend vs budget, Budget buckets bars | `buckets[]` (`name`, `budget`, `spent`) | `dashboard_snapshot(:m) -> 'budgets'`: `budget` = `planned`, `spent` = `spent` (from `budget_months`). |
| Left over (planned) | computed | income received - all bills planned - bucket budgets |
| Needs review | `review[]` (`account`, `items`, `total`, `skipped`, `oldest`) | `select r.nickname, a.last4, r.items, r.total, r.skipped_before as skipped, r.oldest from needs_review_by_account r join accounts a on a.id = r.account_id`. `account` = `nickname (…last4)`. The view has no `last4`, so the join is required. `skipped` is items the user skipped in an earlier review. Backlog from days the review didn't run shows up in `items` and in an older `oldest`. |
| Debt snowball | `debts[]` (`order`, `name`, `apr`, `min`, `balance`, `clears`), `snowball` (`extra`, `months`, `debtFree`, `interest`) | `dashboard_snapshot(:m) -> 'debts'`: `balance` = `start - paid` (the snapshot has no `balance` field). `snowball.extra` = `settings.snowball.extra_per_month`. `clears`, `months`, `debtFree` and `interest` come from the payoff simulation that `build_reports.py` prints (`snowball` in its JSON output). |

Notes:
- Amounts are plain numbers; the Page formats them.
- Never put account numbers beyond the last 4, Plaid ids, or keys in `DATA`.
- The Page shows status as of the date in `asOf`; it is not live. Grok refreshes it after the Daily Transaction Review or at month end.

## Bills by week (timeline)

The Bills section has a **List | By week** toggle next to the All / Unpaid / Paid filter. By week is a timeline: one heading per week of the month, with that week's total and unpaid amount, then every bill in due-date order, each led by its date (e.g. "Mon 1/5"), with a Fixed or One-off marker, the amount and paid status.

- Week 1: days 1-7
- Week 2: days 8-14
- Week 3: days 15-21
- Week 4: day 22 to month end (29-31 fold into week 4)

The week and weekday are computed from `due` (`M/D`) and the year in `month`, so no extra DATA fields are needed. The status filter still applies inside By week; week totals always cover all of that week's bills.

The Monthly Budget Plan PDF and the HTML dashboard from `build_reports.py` use the same structure: the PDF's whole bills section is a **Bills timeline** (week headings with subtotals, a dotted rail of bills by date, a FIXED / ONE-OFF label, amount, status, and an overall total), replacing the old Fixed bills and One-off bills tables. Carried-over unpaid one-offs go under the week of their due date when it falls in this month; otherwise under Week 1, marked "carried over". The PDF timeline is compact (small grey WEEK labels with hairline rules and inline subtotals, single-line 8-8.5pt rows) and is kept on one page: if it doesn't fit after the income plan it moves whole to the next page, and above ~44 bills it switches to two columns (weeks 1-2 | 3-4). Stress test: `python3 build_reports.py sample/test/snapshot-stress-35-bills.json --out /tmp/stress` (fake data, 36 bills, fits one page). The Where the Money Went PDF keeps its by-category tables.
