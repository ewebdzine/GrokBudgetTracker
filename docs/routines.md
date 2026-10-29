# Routines

Sample routine prompts. Replace <placeholders>. Create them with the Grok Bot routines feature on your Finance bot.


**Daily Transaction Review (every morning at <time>)**
> Run my Daily Transaction Review from GrokBudgetTracker docs/workflows.md. Pull new transactions from every connected account in my budget tracker (new rows are needs_review). Review every transaction with review_status needs_review or skipped, including any backlog from earlier days. Tell me "I found N transactions to review" with a count and total for each account and how many are from earlier days; if there are 8 or fewer, list them all. Automatically match only obvious matches to my known recurring bills (mark them auto_applied) and tell me which ones you matched. Then ask me about the rest one transaction at a time, with your best guesses prefilled as options labeled "Recurring bill: <name>", "One-off bill: <category>" or "Budget bucket: <name>", plus "Split…", "Skip for now" and a typed answer. Save my answers to transaction_allocations, set review_status to categorized (or skipped) (and the matching bills, one-offs and bucket totals). Finish with a recap: updated balances for the buckets you touched, any bucket over budget, bills still unpaid this month, and anything I skipped. If nothing needs review, send nothing.

**Month rollover (1st of the month)**
> Roll my budget tracker into the new month: create bill instances and bucket rows, carry over unpaid one-offs, create the planned spending-account transfer, and build this month's Budget Plan PDF.

**Month-end report (last day of the month)**
> Build last month's dashboard and the Where the Money Went PDF from dashboard_snapshot and send me the PDF with a 3-line summary.
