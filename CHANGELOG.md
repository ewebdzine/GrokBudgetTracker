# Changelog
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
