# Updates (for Grok Bot)

How the Finance bot checks for a newer GrokBudgetTracker and helps the user update. The user decides; you never apply anything on your own.

## Where versions live
- **Installed version**: recorded at install in your memory/setup notes as `GrokBudgetTracker installed version: X.Y.Z` (ONBOARDING step 9). Also kept in the `settings` row `grokbudgettracker` (`{"version": "X.Y.Z"}`) if the user has it. If neither exists, ask the user once which version they installed (or treat it as `0.0.0` and say so).
- **Latest version**: `https://raw.githubusercontent.com/ewebdzine/GrokBudgetTracker/main/VERSION` (one semver line, e.g. `0.7.0`).
- **What changed**: `https://raw.githubusercontent.com/ewebdzine/GrokBudgetTracker/main/CHANGELOG.md`, one `## X.Y.Z - date` heading per release.

## Check
1. Read the installed version and fetch the latest `VERSION`.
2. Compare as semver (major.minor.patch, numerically). If latest is not newer, stop. **Say nothing to the user.**
3. If newer, read every CHANGELOG section above your installed version up to and including the latest.
4. If you can't reach GitHub, try once more later; don't message the user about a failed check unless it fails three months in a row.

## Tell the user
Send one short message in plain words:
- "GrokBudgetTracker X.Y.Z is out (you have A.B.C)."
- 3-6 bullets on what's new that matters to them (skip internal details).
- What updating involves: new database migrations (list each file and what it does in one line), new or changed templates/prompts.
- Ask: "Want me to update?" Then wait. No reply means no update.

## Apply (only after the user's explicit OK)
1. **Migrations**: list the new `supabase/migrations/NNNN_*.sql` files above the last one applied (check the migration history in Supabase). For each, explain it in plain language, show it, and apply it only after the user says OK to that migration. Apply in order, one at a time; stop on any error and report it.
   - Migrations change schema only. Never delete, truncate, overwrite or rewrite the user's rows. If a migration would drop or alter a column that holds data, stop and ask, explaining the impact.
   - Never run `seed_example.sql` or any seed on a real project.
2. **Templates, prompts and docs**: re-pull them from `raw.githubusercontent.com/ewebdzine/GrokBudgetTracker/main/...`. Keep the user's own files: never overwrite `templates/config.json`, their routine times, or anything they customized; if a template they edited changed upstream, show the difference and ask.
3. **Routines and setup prompt**: if the release changes a routine prompt or the setup rules, show the new text and update only after OK.
4. **Record**: update the installed version in memory (and the `settings` row if used) to the new version, then confirm in one line what changed.

## Never
- Apply anything without the user's OK, or batch-approve migrations they haven't seen.
- Touch, export or send the user's financial data as part of an update.
- Store keys or passwords.
