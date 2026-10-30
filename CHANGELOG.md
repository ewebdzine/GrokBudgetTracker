# Changelog
## 0.7.0 - 2026-10-30
- Update check: `VERSION` file, [docs/updates.md](docs/updates.md) (compare installed vs latest, summarize, ask before applying; migrations only after OK, data never touched). Setup records the installed version and adds a monthly "GrokBudgetTracker update check" routine that stays quiet when nothing is new.
- Bucket charts: `templates/bucket-chart.html`, `bucket_chart.sql` and `render_bucket_chart.py`.
  - Summary card for all buckets: spent of planned, rounded bar, left or over, month total.
  - Single-bucket card: big left/over figure plus a dated timeline of every expense in the bucket that month.
  - Purple when on track, amber at 90% or more, red when over.
  - Over budget: the bar rescales so the limit sits at 75% with a dark limit marker, the overflow past it is red-striped, and an "Over" tag sits at the end. Near the limit, the marker shows at the end of the bar.
  - The bot shows these whenever you ask to see your buckets or budget, never a generic chart (finance-bot-setup prompt and docs/workflows.md "Showing buckets").
  - Example data in `templates/sample/buckets-example.json`; previews in `docs/images/buckets/`.
- PDF bills timeline made compact: small grey WEEK labels, inline subtotals, 8-8.5pt single-line rows, slim rail; kept on one page (moves whole, two columns above ~44 bills); stress fixture `templates/sample/test/snapshot-stress-35-bills.json`.
- Bills timeline by week of the month (Week 1 = 1-7, 2 = 8-14, 3 = 15-21, 4 = 22-end). Monthly Budget Plan PDF: the Fixed bills and One-off bills tables are replaced by week headings with subtotals and a dated rail of all bills (FIXED / ONE-OFF label, amount, status) plus an overall total. HTML dashboard weeks match (29-31 fold into week 4, date lead, type tag). Dashboard Page: List / By week toggle; By week shows dated bills with a Fixed / One-off marker.

## 0.6.0 - 2026-10-29
- 0008 documents: private Storage bucket `bill-documents` and `documents` table (sha256 dedupe, doc_type, one link to a one-off, bill, transaction or income row, ocr_text), deny-all RLS.
- Optional Edge Function `supabase/functions/bill-documents` for uploads and signed URLs (the Supabase connector has no Storage upload tool).
- Photo -> one-off bill workflow; README Portability section; onboarding and sample document rows.

## 0.5.0 - 2026-10-29
- Interactive Grok Bot Page is the default monthly view: `templates/dashboard.canvas.tsx` (sample data) and `templates/DASHBOARD.md` (monthly fill and same-Page update process, query map).
- PDFs become the printable option; `settings.reports` (`{"page": true, "pdf": false}`) chosen in ONBOARDING step 7; month-end routine updated.
- README "What you get" with PDF previews in docs/images/.

## 0.4.0 - 2026-10-29
- 0007 income: extends income_sources (frequency, next_expected_date) and income_events (transaction_id link); new views `income`, `monthly_income` (expected vs received) and `income_source_suggestions`; function income_expected_count.
- Daily review offers "Income: <source>" for deposits and suggests recurring deposits as sources; onboarding income interview asks frequency and next date.
- Report generator uses monthly_income expected totals when present in the snapshot.

## 0.3.0 - 2026-10-29
- seed_categories: 26 common optional categories from widely used budget templates (YNAB, Ramsey, 50/30/20 lists), no amounts.
- ONBOARDING step 4 (categories) and step 6 (income, bills, buckets, debts) rewritten as Grok-led one-question-at-a-time interviews with a confirm-before-save summary.

## 0.2.0 - 2026-10-29
- 0006: `review_status` (needs_review/categorized/auto_applied/skipped) separate from `bank_status` (pending/posted); `needs_review_transactions` and `needs_review_by_account` views replace `uncategorized_transactions`.

## 0.1.0 - 2026-10-29
- Initial template: schema migrations 0001-0002 (from the original tracker), 0003 account registry, 0004 categories and expense types, 0005 transaction sources and allocations.
- Docs: README, ONBOARDING, database map, workflows, prompts.
- Report generators (HTML dashboard, Budget Plan and Where the Money Went PDFs) and blank templates, with fake sample data.
