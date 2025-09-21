# PRD — Coffee Scraper Pipeline (Final)

## 1. Goal

* Monthly **full product refresh** (metadata + normalization + images + optional LLM enrichment).
* Weekly **price-only refresh** (prices + availability) that is fast, cheap, idempotent.
* Minimal schema changes to your existing DB; no extra tables unless explicitly opted-in.

## 2. High-level flows

1. **Full pipeline (monthly)**
   * Fetch product artifact → Validate (Pydantic) → Persist raw artifact pointer/hashes → Normalize deterministic → (LLM enrichment if needed and enabled) → ImageKit upload (if new) → `rpc_upsert_coffee` (product + variants + latest prices) → mark processed.

2. **Price-only pipeline (weekly)**
   * Fetch minimal product/variants JSON → Compare `price_decimal` vs `variants.price_current` → `rpc_insert_price` for changes and update `variants.price_current`, `price_last_checked_at`, `in_stock`.

## 3. Scraping Process

### 3.1 Goals

* Use store JSON endpoints (Shopify/Woo) as primary source.
* Use Firecrawl (map → extract) only as fallback for JS-heavy or missing JSON endpoints.
* Support two run types: **full** (monthly) and **price-only** (weekly).
* Save raw responses (artifact) for replay & debugging.
* Be polite: respect robots, rate-limits, and store-specific config.

### 3.2 Canonical Artifact Schema

All scraped data must conform to the canonical artifact JSON schema for validation and processing:

**Required Fields:**
- `source`: Origin of artifact (shopify, woocommerce, firecrawl, manual, other)
- `roaster_domain`: Store domain (hostname format)
- `scraped_at`: ISO 8601 timestamp
- `product`: Product object with platform_product_id, title, source_url, variants

**Key Product Fields:**
- `platform_product_id`: Unique identifier from source platform
- `title`: Product name
- `handle`: URL-friendly identifier
- `description_html` / `description_md`: Product descriptions
- `source_url`: Original product URL
- `product_type`: Type classification
- `tags`: Array of product tags
- `images`: Array with url, alt_text, order, source_id
- `variants`: Array of product variants with pricing and inventory

**Normalization Fields:**
- `is_coffee`: Boolean coffee classification
- `content_hash`: Hash of normalized content for change detection
- `raw_payload_hash`: Hash of raw scraped data
- `parsing_warnings`: Array of parsing issues
- `name_clean`: Cleaned product name
- `description_md_clean`: Cleaned markdown description
- `tags_normalized`: Normalized tag array
- `roast_level_enum`: Standardized roast level (light, medium, dark, etc.)
- `process_enum`: Processing method (washed, natural, honey, etc.)
- `varieties`: Coffee variety array
- `region`, `country`, `altitude_m`: Geographic data
- `default_pack_weight_g`: Standard pack weight
- `default_grind`: Grind preference
- `llm_enrichment`: LLM-generated data (JSON)
- `llm_confidence`: LLM confidence score (0-1)

**Audit Fields:**
- `artifact_id`: Unique artifact identifier
- `created_at`: Creation timestamp
- `collected_by`: Collection method
- `collector_meta`: Collector metadata (version, job_id, etc.)
- `collector_signals`: Response metadata (status, headers, timing, size)

### 3.3 Endpoints & concrete requests

#### Shopify (storefront JSON)
* Primary endpoint (list): `https://<store>/products.json?limit=<N>&page=<M>`
  * Shopify supports `limit` up to 250; prefer `limit=250` for fewer pages.
  * For single product detail (if needed): `https://<store>/products/<handle>.json`
* Response contains product objects with `variants[]`, `images[]`.
* Some Shopify stores restrict storefront JSON — expect 403/429 or truncated responses.

#### WooCommerce (Storefront REST)
* Primary endpoint (storefront): `https://<store>/wp-json/wc/store/products?per_page=<N>&page=<M>`
  * Typical `per_page` up to 100 depending on host.
* Product object includes `variations` / `prices` / `images`.
* Some WooCommerce installs disable the REST endpoint or require auth.

#### Price-only optimizations
* For price-only job, fetch the list endpoint (products.json / wc store products) and only parse `variants[]` price fields. Avoid fetching per-product HTML or images.
* If listing endpoint not available, fallback to per-product endpoint for minimal fields.

#### Firecrawl fallback (map → extract)
* Use Firecrawl `map` to discover product pages for a domain (cheap discovery).
* Use Firecrawl `extract` on a product URL to get structured product JSON.
* Firecrawl is used only if primary JSON endpoints fail or return incomplete data (missing `variants`, missing `price`, or blocked).

### 3.4 Store config & per-store behavior

Each roaster (row in `roasters`) must include:
* `platform` (shopify|woocommerce|other)
* `full_cadence`, `price_cadence` (cron strings)
* `default_concurrency` (workers), `use_firecrawl_fallback`, `firecrawl_budget_limit`
* `last_etag`, `last_modified` (optional) for caching via `If-None-Match` / `If-Modified-Since`
* `robots_checked_at` timestamp and `robots_allow` flag (pre-check at onboarding)

Before any fetch run, the scheduler checks:
1. If `use_firecrawl_fallback` false → only JSON endpoints.
2. If robots.txt disallows scraping → skip and mark roaster incident.

### 3.5 Fetcher behavior (detailed)

#### Concurrency & politeness
* Per-roaster concurrency: default `3` (configurable). Implement with `asyncio.Semaphore(per_roaster_concurrency)`.
* Per-domain delay: base `delay_ms` = 250ms ± jitter (±100ms). Respect `Crawl-Delay` if present in robots.txt.
* Set a custom `User-Agent` header: e.g. `MyScraper/1.0 (+https://your.domain; contact@you)` — store this in config.
* On 429/503: exponential backoff with `Retry-After` if provided.

#### Retries & backoff
* Retry policy for transient errors: up to `5` retries. Backoff: `1s, 2s, 4s, 8s, 16s` + jitter.
* Treat 4xx (except 429) as permanent for that request; log, persist raw response, and mark artifact with parsing warning.
* If a roaster returns repeated permanent failures, escalate: mark roaster `active=false` or `incident` and notify ops.

#### Caching (ETag / Last-Modified)
* Use `If-None-Match` with stored `last_etag` and `If-Modified-Since` with `last_modified` to cut bandwidth.
* On `304 Not Modified`: skip heavy normalization; only update `price_last_checked_at` if running price-only and prices are unchanged.

#### Payload size & timeouts
* Set timeout: connect=5s, read=15s (tuneable). If response > 5MB (configurable), save raw and send to manual review or stream to S3 for later parsing; avoid keeping large responses in memory.

#### Response validation
* Immediately validate raw JSON against **Canonical Artifact JSON Schema**:
  * If valid -> persist raw artifact (raw\_payload + raw\_payload\_hash), continue normalization.
  * If invalid -> persist raw payload, set `processing_status='review'`, include parse errors in `processing_warnings`.

### 3.6 Product discovery & pagination

* For list endpoints use pagination parameters as documented above. Stop when:
  * No more pages, or returned length < `limit`, or response contains `next` pagination link.
* If store exposes only product pages (no list JSON), use Firecrawl map to get product URLs (fallback).

### 3.7 Firecrawl integration (budgeted fallback)

* Trigger Firecrawl only when:
  * JSON endpoints return 4xx/5xx or malformed JSON, OR
  * Required fields missing (`variants` or `price`).
* Firecrawl sequence:
  1. `map` domain to discover product URLs (cheap).
  2. For each product URL, call `extract` to get structured product JSON.
  3. Merge `extract` output into canonical artifact shape (map fields deterministically; store missing fields into `raw_meta`).
* Respect `firecrawl_budget_limit` per-store: decrement budget counter on each `extract`. Stop using Firecrawl when budget exhausted, mark store for manual handling.

### 3.8 Price-only job specifics

* For each store, perform lightweight fetch:
  * Prefer list endpoints (products.json / wc store products) — parse `variants[].price` and `in_stock`.
  * If list endpoint missing, fetch product endpoints *only for known product handles/ids* (from DB) — do not crawl entire site.
* Compare with `variants.price_current` and call `rpc_insert_price` for each changed variant. Update `variants.price_last_checked_at` and `variants.in_stock`.
* Price-only jobs must finish within the operational window (configurable). Backoff if DB starts rate-limiting.

### 3.9 Security, polite scraping, legal

* Check `robots.txt` once per store and store result. If disallowed, escalate and do not scrape.
* Show a clear contact `User-Agent`. Keep request frequency low and configurable.
* Respect store API quotas and terms — Firecrawl is used to reduce direct scraping impact.

### 3.10 Edge cases & defensive rules

* If list endpoint returns partial data (e.g., variants empty) -> treat as incomplete and trigger Firecrawl fallback for those products only.
* For huge catalog roasters (>5000 products) — split full refresh into paginated, staged runs to avoid DB spikes.
* If a roaster blocks our IP range repeatedly, rotate outbound IPs using Fly regions or contact the roaster.

## 4. System Architecture & Deployment

### 4.1 High-Level Architecture

The system follows a microservices architecture with clear separation of concerns:

```mermaid
flowchart TD
  A[Scheduler: GitHub Actions / Cloud Scheduler] --> B[Orchestrator / Job Queue]
  B --> C[Fetcher Pool]
  C --> C1[Shopify Fetcher (HTTP JSON)]
  C --> C2[Woo Fetcher (WC JSON)]
  C --> C3[Firecrawl Fallback (map/extract)]
  C1 & C2 & C3 --> D[Validator (Pydantic v2) ---> Persist raw artifact (S3/Blob / supabase_scrape_artifacts)]
  D --> E[Normalizer Service]
  E --> E1[Deterministic parsers (regex, unit conversion)]
  E --> E2[LLM Enrichment (fallback) — low qps]
  E --> F[Transformer (Pydantic -> RPC payload)]
  F --> G[Supabase RPCs (rpc_upsert_coffee, rpc_upsert_variant, rpc_insert_price, rpc_upsert_image)]
  F --> H[ImageKit uploader / Image cache]
  G & H --> I[Materialized Views / Dashboard (supabase views)]
  G --> J[Metrics & Logs -> Prometheus / Grafana & Sentry]
  J --> K[Alerting (Slack)]
```

### 4.2 Component Responsibilities

* **Scheduler**: Kicks jobs (hourly/daily or per-roaster cadence). Use GitHub Actions for MVP + Cloud Scheduler/Cloud Run for prod.
* **Orchestrator / Job Queue**: Lightweight queue (Redis / Bull / Cloud Tasks). Maintains job state, retries, backoff, per-roaster concurrency.
* **Fetcher Pool**: Async `httpx` workers with per-domain semaphores + jittered delays + Tenacity backoff. Primary: Shopify/Woo JSON endpoints. Fallback: Firecrawl map/extract.
* **Validator**: Strict Pydantic v2 models generated from canonical JSON Schema. Immediately persist raw artifact (blob store or supabase `scrape_artifacts`) for replay.
* **Normalizer Service**: Deterministic extraction (weights, grams, roast enums, tags) + LLM-only-on-fallback routine. Exposes small library used in pipeline.
* **Transformer → RPCs**: Artifact → normalized payload → call Supabase RPCs. All DB writes go through server-side RPCs for atomicity.
* **ImageKit integration**: Upload new images (or use remote fetch) and return CDN URL; dedupe via hash.
* **Observability**: Metrics (requests/sec, errors, queue length, per-roaster failure rate), traces optional. Errors -> Sentry. Alerts -> Slack.

### 4.3 Data Flow & Guarantees

* **Idempotency**: Use composite key `(source, roaster_domain, platform_product_id, platform_variant_id)` as RPC upsert key. Persist `raw_payload_hash` and `content_hash` to detect no-op.
* **Atomic writes**: All writes for product + variants + prices for one artifact should be encapsulated in one RPC call or transaction (server-side).
* **Replayability**: Raw artifact + artifact\_id persisted for reprocessing.
* **Order**: Fetch → validate → normalize → transform → upsert → image upload (images can be async but must update db).
* **Backpressure**: If Supabase RPCs rate-limit, pause queue; metric exposes API error rate and queue depth.

### 4.4 Deployment Architecture (Fly.io)

**Recommended Fly App Structure:**
1. **api-web** — Web UI, health endpoints, status pages. Publicly exposed service.
2. **worker-ingest** — Long-running worker(s) that process fetch → validate → normalize → transform → RPC upsert. Scales horizontally.
3. **worker-image** — Optional: dedicated image download + ImageKit uploader to isolate heavy IO.
4. **scheduler** — Tiny machine or rely on **GitHub Actions** scheduled workflows to enqueue jobs. Prefer GitHub Actions for simplicity and reproducible CI-driven schedule.
5. **dev/staging** — Mirrors of the above with smaller machine sizes and separate secrets/DB.

**Key Fly.io Considerations:**
* **Ephemeral rootfs**: Machine restarts replace root filesystem. Never rely on container filesystem for persistent artifacts or local DBs.
* **Use S3 / Supabase Storage** as canonical storage for raw artifacts, large file blobs, and image backups.
* **Fly Volumes**: Use only for low-latency, high-I/O needs where persistent local disk is strictly required.
* **Worker design**: Make workers idempotent and push results out to S3/Supabase immediately so ephemeral restart does not lose data.

### 4.5 Non-Functional Requirements

* **Throughput**: 500 products / minute across pool (tune later).
* **Latency**: Per-artifact pipeline < 5s (excluding image upload & LLM).
* **Availability**: 99.5% for pipeline scheduler and worker execution.
* **Error budget**: <1% failed artifacts/week (excluding malformed stores).

### 4.6 Failure Modes & Mitigations

* **Malformed JSON** → Persist raw blob, mark artifact `parsing_warnings`, route to manual review UI.
* **DB RPC failure (rate-limit)** → Pause job queue, exponential backoff + alert.
* **Image host punishes scraping** → Use ImageKit remote fetch + CDN. Flag repeatedly failing domains.
* **LLM hallucination** → Store `llm_enrichment` raw + `llm_confidence`. Don't auto-trust without threshold.

## 5. DB design (finalized — minimal additions)

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

## 6. RPC contracts (finalized)

All writes to canonical tables should go through server-side RPCs for atomicity and access control.

### 6.1 `rpc_upsert_coffee` — product metadata + variants + optional images

* **Purpose:** Upsert coffee + variants + optionally prices and images in a single transaction.
* **Signature (Postgres function stub):**

```sql
-- Using existing rpc_upsert_coffee function with actual parameters:
CREATE OR REPLACE FUNCTION rpc_upsert_coffee(
  p_bean_species species_enum,
  p_name text,
  p_slug text,
  p_roaster_id uuid,
  p_process process_enum,
  p_process_raw text,
  p_roast_level roast_level_enum,
  p_roast_level_raw text,
  p_roast_style_raw text,
  p_description_md text,
  p_direct_buy_url text,
  p_platform_product_id text,
  p_status coffee_status_enum DEFAULT 'active',
  p_decaf boolean DEFAULT false,
  p_notes_raw jsonb DEFAULT NULL,
  p_source_raw jsonb DEFAULT NULL
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER AS $$
  -- Implementation handles coffee upsert with existing schema
$$;
```

* **Notes:** This function handles coffee metadata upsert. For variants and prices, use separate `rpc_upsert_variant` and `rpc_insert_price` functions.

### 6.2 `rpc_upsert_variant` — single variant upsert

* **Signature:** Uses existing `rpc_upsert_variant` function with parameters: `p_coffee_id`, `p_platform_variant_id`, `p_sku`, `p_weight_g`, `p_grind`, `p_currency`, `p_in_stock`, `p_source_raw`. Returns variant id.

### 6.3 `rpc_insert_price` — price time-series insert

* **Signature:**

```sql
-- Using existing rpc_insert_price function with actual parameters:
CREATE OR REPLACE FUNCTION rpc_insert_price(
  p_variant_id uuid,
  p_price numeric,
  p_currency text DEFAULT 'USD',
  p_is_sale boolean DEFAULT false,
  p_scraped_at timestamptz DEFAULT now(),
  p_source_url text DEFAULT NULL,
  p_source_raw jsonb DEFAULT NULL
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER AS $$ ... $$;
```

* **Behavior:** Insert price row, update `variants.price_current` and `variants.price_last_checked_at` atomically.

### 6.4 `rpc_upsert_image` — image record (called after ImageKit upload)

* **Signature:** Uses existing `rpc_upsert_coffee_image` function with parameters: `p_coffee_id`, `p_url`, `p_alt`, `p_width`, `p_height`, `p_sort_order`, `p_source_raw`. Returns image id.

## 7. Job scheduling (final)

* **Defaults:**
  * Full refresh: `0 3 1 * *` — run at 03:00 UTC on the 1st of every month.
  * Price-only: `0 4 * * 0` — run at 04:00 UTC every Sunday.
* **Per-roaster overrides:** use `roasters.full_cadence`, `roasters.price_cadence`. Worker must respect per-roaster schedule and concurrency.
* **Backoff & retries:** transient HTTP errors → exponential backoff up to 5 retries; permanent 4xx → mark roaster incident and skip.

## 8. Heuristics & thresholds (final)

* `price_delta_alert_threshold = 0.10` (10%) — configurable per roaster via a `roasters.alert_price_delta_pct` optional column (suggested).
* `max_parse_warnings_before_review = 1` — if `processing_warnings` array length > 1, set `processing_status='review'`.
* `max_variant_count_change = 3` — if number of variants added/removed > 3 in full run → `processing_status='review'`.
* `llm_confidence_threshold = 0.70` — only auto-commit llm\_enrichment if confidence >= 0.7; otherwise store enrichment JSON and mark for review if critical.

## 9. Short-circuit logic (final, pseudocode)

```python
# input: artifact (validated)
if artifact.normalization.content_hash == db.coffees.content_hash:
    # content unchanged
    if only prices differ (compare variant prices):
        run price-only path -> rpc_insert_price updates
    else:
        skip heavy work (no image uploads or LLM)
else:
    # content changed -> do full pipeline
    run full normalization -> imagekit -> rpc_upsert_coffee(metadata_only=False)
```

## 10. Normalization & LLM fallback (brief)

* Run deterministic parsers first: weight parsing, currency normalization, roast level mapping, variety extraction. If deterministics pass and `llm_enrichment` not required → continue.
* If ambiguous fields remain (e.g., weight parsing fails or roast parsing ambiguous), **queue a limited LLM enrichment** call (rate-limited per minute and per-store). Cache result and only auto-apply if `llm_confidence >= 0.70`.

## 11. Manual review workflow (final)

* `processing_status='review'` flags coffee for triage. UI/QA queries `coffees WHERE processing_status='review'`.
* `processing_warnings` contains detail: e.g., `["price missing", "weight ambiguous: '12oz'"]`.
* If human resolves, call `rpc_upsert_coffee` with corrected payload and set `processing_status='ok'` and populate `processing_warnings` with resolution notes.

## 12. Image handling (final)

* Image detection: compare remote image URL hash vs stored image hash. Upload to ImageKit only on new/changed hash.
* Price-only job must **never** re-upload or transform images.
* Store both `images.source_url` (original) and `images.imagekit_url` (cdn). RPC `rpc_upsert_image` writes both.

## 13. LLM usage policy (final)

* LLM is **fallback-only**. Toggleable globally and per-roaster (`use_llm boolean` per roaster optional).
* Cache LLM outputs in `coffees.notes_raw` (JSON) and confidence scores.
* Auto-apply LLM outputs only if `llm_confidence >= 0.70`. Otherwise store result and mark `processing_status='review'` if the field is core (e.g., `roast_level_enum`).

## 14. Error handling & manual review

* Rules to push to manual review:
  * `parsing_warnings.length > 1`
  * `variant_count_change > 3`
  * `missing price` for all variants
  * LLM output below confidence threshold for core fields
  * > 10% price\_delta across roaster (suspicious)
* Manual review stores the raw payload in `coffees.source_raw` and sets `coffees.processing_status='review'` with reasons in `processing_warnings`.

## 15. Observability & alerts (final)

* Metrics: per-run artifacts processed, parse\_warnings\_count, percent\_reviewed, average\_time\_per\_artifact, RPC error rate.
* Alerts:
  * > 5% artifacts flagged review per run → Slack alert.
  * DB RPC errors > threshold → pause queue + alert.
  * Price-change spike: if > X% of variants changed > `price_delta_alert_threshold`, notify ops.

### 15.1 Observability & metrics (per fetch)

Emit metrics:
* `fetch_requests_total{store,platform,result=success|fail|not_modified}`
* `fetch_latency_ms{store}`
* `fetch_size_bytes{store}`
* `artifacts_validated_total{valid|invalid}`
* `firecrawl_extracts_total{store}`
* `llm_calls_total{store}`
* Alert when:
  * `fetch_fail_rate > 5%` per run
  * `artifacts_invalid_ratio > 3%` per run
  * `firecrawl_budget_exhausted` event

Log at two levels:
* **Info**: roaster-level run start/end, number of artifacts processed, variant price updates count.
* **Error**: persistent 4xx/5xx, parser exceptions, LLM failures, DB RPC failures.

Persist raw responses to S3/Supabase storage with path: `s3://<bucket>/artifacts/<roaster>/<YYYY>/<MM>/<artifact_id>.json` and save link to `coffees.source_raw` (or to `scrape_artifacts` if you choose that later).

## 16. Backfill scripts (final)

* **Backfill `price_current`** from `prices`:

```sql
-- backfill_price_current.sql
WITH latest_price AS (
  SELECT DISTINCT ON (variant_id) variant_id, price
  FROM prices
  ORDER BY variant_id, scraped_at DESC
)
UPDATE variants v
SET price_current = lp.price
FROM latest_price lp
WHERE v.id = lp.variant_id
  AND (v.price_current IS NULL OR v.price_current <> lp.price);
```

## 17. Indexes & performance (final)

Add these indexes to keep queries fast:

```sql
CREATE INDEX IF NOT EXISTS idx_prices_variant_scraped_at ON prices(variant_id, scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_variants_status ON variants(status);
CREATE INDEX IF NOT EXISTS idx_coffees_content_hash ON coffees(content_hash);
```

## 18. Security & secrets (final)

* Supabase RPC credentials: use a **server-side** service role for RPC execution stored in Fly secrets. Do **not** embed in client code.
* ImageKit keys stored in Fly secrets / CI secrets.
* LLM keys stored and rotated; usage metered and capped.

## 19. QA checklist (final)

* [ ] Migrations applied to staging.
* [ ] Golden fixtures: `full_example.json` + `price_delta_example.json`.
* [ ] Unit tests for parser (weight, currency, price detection).
* [ ] Integration test: run monthly full pipeline against staging stores; verify `coffees.processing_status` behavior.
* [ ] Integration test: run weekly price-only pipeline; verify `rpc_insert_price` calls and `variants.price_current`.
* [ ] Feature flag tests: LLM off/on, Firecrawl fallback off/on.
* [ ] Monitor dashboards + Slack alerts configured before prod run.

## 20. Acceptance criteria (final)

* **Monthly full run (sample 100 products)**: ≥95% products have `name_clean`, `description_md_clean`, and `default_pack_weight_g` populated; images uploaded to ImageKit; ≤3% artifacts `processing_status='review'`.
* **Weekly price run (sample 100 products)**: ≥99% reachable variants updated `price_last_checked_at`; price deltas recorded in `prices` table; job completes within operational window without DB rate-limit.

## 21. Pseudocode: orchestrator & worker

Scheduler (high level):

```
for each roaster in active_roasters:
  if now matches roaster.full_cadence and last_full_run older than cadence:
      enqueue Job(roaster.id, job_type='full')
  if now matches roaster.price_cadence:
      enqueue Job(roaster.id, job_type='price_only')
```

Worker (per job):

```
job = queue.get()
with roaster_semaphore(job.roaster_id):
  if job.type == 'price_only':
     run price_only_for_roaster(job.roaster_id)
  else:
     run full_refresh_for_roaster(job.roaster_id)
```

Full refresh flow:

```
pages = discover_list_pages(roaster)
for page in pages:
   resp = fetch_json(page.url)
   save_raw(resp)
   for product in resp.products:
      artifact = build_artifact(product, collector_meta)
      validate(artifact) -> pydantic
      if valid:
         normalize(artifact)
         if content_hash == db.content_hash:
            handle_price_deltas_only_if_price_changed()
         else:
            maybe_call_llm_if_needed()
            upload_images_if_changed()
            call rpc_upsert_coffee() + rpc_upsert_variant() + rpc_insert_price()
      else:
         mark_review(artifact)
```

Price-only flow:

```
pages = discover_list_pages(roaster)
for page in pages:
   resp = fetch_json(page.url)
   for product in resp.products:
      for variant in product.variants:
         if variant.price != db.variant.price_current:
            rpc_insert_price(...)
         update variant.price_last_checked_at
```

## 22. Appendix — Optional artifact audit table (not run by default)

If you want full auditability later, create `scrape_artifacts`. This is **optional** and not required for initial launch.

```sql
CREATE TABLE IF NOT EXISTS scrape_artifacts (
  artifact_id text PRIMARY KEY,
  roaster_id uuid REFERENCES roasters(id),
  scraped_at timestamptz,
  raw_payload jsonb,
  raw_payload_hash text,
  content_hash text,
  processed boolean DEFAULT false,
  processing_warnings jsonb,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX ON scrape_artifacts(raw_payload_hash);
```

---

**Note:** This is the final, comprehensive PRD that merges both the database/processing logic and the scraping implementation details into a single, deployable specification.
