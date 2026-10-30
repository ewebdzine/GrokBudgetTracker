# Routines

Sample routine prompts. Replace <placeholders>. Create them with the Grok Bot routines feature on your Finance bot.


**Daily Transaction Review (every morning at <time>)**
> Run my Daily Transaction Review from GrokBudgetTracker docs/workflows.md. Pull new transactions from every connected account in my budget tracker (new rows are needs_review). Review every transaction with review_status needs_review or skipped, including any backlog from earlier days. Tell me "I found N transactions to review" with a count and total for each account and how many are from earlier days; if there are 8 or fewer, list them all. Automatically match only obvious matches to my known recurring bills (mark them auto_applied) and tell me which ones you matched. Then ask me about the rest one transaction at a time, with your best guesses prefilled as options labeled "Recurring bill: <name>", "One-off bill: <category>" or "Budget bucket: <name>", plus "Split…", "Skip for now" and a typed answer. For deposits offer "Income: <source>" and suggest new income sources for deposits that repeat. Save my answers to transaction_allocations, set review_status to categorized (or skipped) (and the matching bills, one-offs and bucket totals). Finish with a recap: updated balances for the buckets you touched, any bucket over budget, bills still unpaid this month, and anything I skipped. If nothing needs review, send nothing.

**Month rollover (1st of the month)**
> Roll my budget tracker into the new month: create bill instances and bucket rows, carry over unpaid one-offs, create the planned spending-account transfer, and build this month's Budget Plan PDF.

**Month-end report (last day of the month)**
> Read settings.reports. If page is true, refresh my Budget Dashboard Page for this month (same Page every month, per GrokBudgetTracker templates/DASHBOARD.md) and send me the link. If pdf is true, also build the Monthly Budget Plan and Where the Money Went PDFs from dashboard_snapshot and send them. Add a 3-line summary: income received vs expected, bills left, and any bucket over budget.

## GrokBudgetTracker update check
Name: **GrokBudgetTracker update check**. Schedule: monthly, 1st of the month at 9:00 AM (any day/time is fine). Prompt:

```
GrokBudgetTracker update check. Follow docs/updates.md from https://raw.githubusercontent.com/ewebdzine/GrokBudgetTracker/main/docs/updates.md. Compare my installed GrokBudgetTracker version (in your memory/setup notes) with https://raw.githubusercontent.com/ewebdzine/GrokBudgetTracker/main/VERSION. If it isn't newer, stop and send me nothing. If it is newer, read CHANGELOG.md for every release since my version and send me one short plain-words message: the new version, what's new that matters to me, and which migrations, templates or prompts would change. Then ask if I want to update and wait. Do not apply anything, run any migration or change any template, routine or data until I say OK, and then follow docs/updates.md step by step, asking before each migration.
```
