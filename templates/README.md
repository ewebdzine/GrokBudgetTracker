# Report templates

| File | Output |
|---|---|
| `build_reports.py` | From a `dashboard_snapshot` JSON: `YYYY-MM.html` dashboard, `YYYY-MM-budget-plan.pdf`, `YYYY-MM-where-the-money-went.pdf`; prints a JSON summary (bills left, snowball months, etc.) |
| `build_blank.py` | Blank fill-in versions: `monthly-budget-plan-blank.pdf`, `where-the-money-went-blank.pdf` |
| `config.example.json` | Labels, account ids, colors, bill grouping, keyword rules, blank-template rows |
| `sample/snapshot-2026-01.json` | Fake snapshot |
| `sample/output/` | Rendered from the fake snapshot |

Requirements: Python 3 and `reportlab` (`pip install reportlab`). Uses DejaVu Sans for checkbox glyphs if installed.

```
cp config.example.json config.json   # edit
python3 build_reports.py sample/snapshot-2026-01.json --out sample/output
python3 build_blank.py --out sample/output
```

## Customizing
- **Names and accounts**: `owner_label`, `account_note`, `bills_account_id` (key in `settings.balances`), `spending_account_id` (the transfer target), and their labels.
- **Colors**: `colors.accent` (dashboard and chart).
- **Bill grouping**: `bill_groups` maps a bill's category to a report group; `bill_group_order` sets group order.
- **Exclusions**: `own_transfer_keywords`, `card_payment_keywords`, `fee_keywords` are matched against bank descriptions (upper case) to exclude own transfers and card payments from spending and count fees.
- **Blank templates**: `blank_template.fixed_bills`, `one_off_groups`, `budgets`, `income`.
- The HTML styling is the `CSS` string in `build_reports.py`; PDF styles are the `ParagraphStyle`/`TableStyle` definitions.
- `config.json` is git-ignored because it usually holds your real labels.
