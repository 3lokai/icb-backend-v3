# 7. Job scheduling (final)

* **Defaults:**
  * Full refresh: `0 3 1 * *` — run at 03:00 UTC on the 1st of every month.
  * Price-only: `0 4 * * 0` — run at 04:00 UTC every Sunday.
* **Per-roaster overrides:** use `roasters.full_cadence`, `roasters.price_cadence`. Worker must respect per-roaster schedule and concurrency.
* **Backoff & retries:** transient HTTP errors → exponential backoff up to 5 retries; permanent 4xx → mark roaster incident and skip.
