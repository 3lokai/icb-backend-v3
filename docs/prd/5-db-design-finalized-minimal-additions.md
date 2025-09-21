# 5. DB design (finalized — minimal additions)

We will **add a few columns** to existing `roasters`, `coffees`, and `variants`. No new core tables required.

### 5.1 Final migration SQL (run on staging → prod)

```sql
-- 01_add_roaster_fields.sql
ALTER TABLE roasters
  ADD COLUMN IF NOT EXISTS full_cadence text,               -- example: '0 3 1 * *' (monthly 03:00 UTC on day 1)
  ADD COLUMN IF NOT EXISTS price_cadence text,              -- example: '0 4 * * 0' (weekly Sun 04:00 UTC)
  ADD COLUMN IF NOT EXISTS default_concurrency int DEFAULT 3,
  ADD COLUMN IF NOT EXISTS use_firecrawl_fallback boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS firecrawl_budget_limit int DEFAULT 0; -- optional monthly units

-- 02_variants_price_meta.sql
ALTER TABLE variants
  ADD COLUMN IF NOT EXISTS price_last_checked_at timestamptz,
  ADD COLUMN IF NOT EXISTS price_current numeric,
  ADD COLUMN IF NOT EXISTS last_seen_at timestamptz,
  ADD COLUMN IF NOT EXISTS status text DEFAULT 'active'; -- values: active, archived, missing, review

-- 03_coffees_artifact_meta.sql
ALTER TABLE coffees
  ADD COLUMN IF NOT EXISTS raw_payload_hash text,
  ADD COLUMN IF NOT EXISTS content_hash text,
  ADD COLUMN IF NOT EXISTS raw_payload jsonb,
  ADD COLUMN IF NOT EXISTS processing_status text DEFAULT 'ok', -- ok, review, error
  ADD COLUMN IF NOT EXISTS processing_warnings jsonb;

-- 04_indexes.sql
CREATE INDEX IF NOT EXISTS idx_coffees_raw_payload_hash ON coffees(raw_payload_hash);
CREATE INDEX IF NOT EXISTS idx_variants_price_last_checked_at ON variants(price_last_checked_at);
CREATE INDEX IF NOT EXISTS idx_coffees_processing_status ON coffees(processing_status);
```

> Note: If you prefer a separate `scrape_artifacts` table for full audit/replay, that is **optional** and included later as an appendix — but final DB here is intentionally *minimal*.

### 5.2 Column meaning & usage

* `roasters.full_cadence` / `price_cadence`: cron expressions per-roaster (overrides global defaults).
* `variants.price_current`: current/latest price numeric (same currency as variant). Maintained by price job and RPCs.
* `variants.price_last_checked_at`: when price was last updated/checked.
* `coffees.raw_payload` / `raw_payload_hash` / `content_hash`: raw artifact, raw hash, normalized content hash for change detection.
* `coffees.processing_status`: `ok | review | error` used for manual triage.
* `coffees.processing_warnings`: JSON array with parser warnings, LLM low confidence notes, or other anomalies.
