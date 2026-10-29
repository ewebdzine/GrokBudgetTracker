# Dashboard Page (sample)
A wide Grok Bot Page built from `templates/dashboard.canvas.tsx` with the fake January 2026 data:
- **Headline metrics**: income received $3,620 of $6,360 expected; bills 3 paid, 3 unpaid ($360 still due); bucket spending $565 of $1,000; left over (planned) $904.
- **Bills** table with type (`Recurring: <category>` / `One-off: <category>`), due date and status, with a Segmented control for All / Unpaid / Paid.
- **Budget buckets** as bars of spent vs budget, switchable (Segmented) to the **Income** expected vs received table.
- **Needs review**: transactions waiting per account, with how many are left from earlier days.
- **Debt snowball**: debt-free date, interest, and each debt with APR, minimum, balance and clear date.
- A pointer to the printable PDFs.
