# Changelog
## 0.3.0 - 2026-10-29
- seed_categories: 26 common optional categories from widely used budget templates (YNAB, Ramsey, 50/30/20 lists), no amounts.
- ONBOARDING step 4 (categories) and step 6 (income, bills, buckets, debts) rewritten as Grok-led one-question-at-a-time interviews with a confirm-before-save summary.

## 0.2.0 - 2026-10-29
- 0006: `review_status` (needs_review/categorized/auto_applied/skipped) separate from `bank_status` (pending/posted); `needs_review_transactions` and `needs_review_by_account` views replace `uncategorized_transactions`.

## 0.1.0 - 2026-10-29
- Initial template: schema migrations 0001-0002 (from the original tracker), 0003 account registry, 0004 categories and expense types, 0005 transaction sources and allocations.
- Docs: README, ONBOARDING, database map, workflows, prompts.
- Report generators (HTML dashboard, Budget Plan and Where the Money Went PDFs) and blank templates, with fake sample data.
