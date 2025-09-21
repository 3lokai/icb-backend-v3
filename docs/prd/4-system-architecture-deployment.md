# 4. System Architecture & Deployment

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
