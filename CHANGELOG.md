# Changelog
## 0.2.0 - 2026-10-29
- 0006: `review_status` (needs_review/categorized/auto_applied/skipped) separate from `bank_status` (pending/posted); `needs_review_transactions` and `needs_review_by_account` views replace `uncategorized_transactions`.

## 0.1.0 - 2026-10-29
- Initial template: schema migrations 0001-0002 (from the original tracker), 0003 account registry, 0004 categories and expense types, 0005 transaction sources and allocations.
- Docs: README, ONBOARDING, database map, workflows, prompts.
- Report generators (HTML dashboard, Budget Plan and Where the Money Went PDFs) and blank templates, with fake sample data.
