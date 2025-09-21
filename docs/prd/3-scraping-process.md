# 3. Scraping Process

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
