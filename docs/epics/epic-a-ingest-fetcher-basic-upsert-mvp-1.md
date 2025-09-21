# Epic A — Ingest: Fetcher + Basic Upsert (MVP-1)

**Goal:** Implement the core fetch → validate → upsert path using Shopify/Woo JSON endpoints and Supabase RPCs. This is the minimum pipeline to start ingesting product data.

### A.1 Story — Worker scaffolding & orchestrator

* **Description:** Create worker process, orchestrator, queue consumer, config for per-roaster cadence and concurrency. Use GitHub Actions for scheduled enqueues for MVP.
* **Acceptance Criteria:** Worker can dequeue a job for a roaster and execute a placeholder task. Scheduler enqueues jobs using roaster.full\_cadence and price\_cadence. Logs show job start/end.
* **Tasks:** repo scaffold, worker entrypoint, queue integration (local/mock), scheduler GH action, config schema for roaster.
* **Priority:** P0
* **Complexity:** M

### A.2 Story — Shopify/Woo list fetcher (paginated)

* **Description:** Implement async paginated fetcher for Shopify `products.json` and Woo `/wp-json/wc/store/products`. Respect per-roaster concurrency and jitter.
* **Acceptance Criteria:** For sample roasters, the fetcher returns product JSON lists and stores raw responses to temp storage. Pagination handled correctly.
* **Tasks:** httpx client, pagination logic, per-roaster semaphores, timeouts, sample mapping.
* **Priority:** P0
* **Complexity:** M

### A.3 Story — Artifact validation (Pydantic models)

* **Description:** Generate Pydantic v2 models from canonical JSON Schema and validate fetched product artifacts.
* **Acceptance Criteria:** Example fixture validates against model; invalid artifacts produce validation errors and are persisted for review.
* **Tasks:** generate models, write unit tests with provided `full_example.json` fixture, implement validation pipeline.
* **Priority:** P0
* **Complexity:** S

### A.4 Story — RPC upsert integration (rpc\_upsert\_coffee + rpc\_upsert\_variant)

* **Description:** Transform validated artifact → RPC payload and call `rpc_upsert_coffee` and `rpc_upsert_variant` per mapping table. Implement metadata\_only flag support.
* **Acceptance Criteria:** For sample artifact, RPCs are invoked with correct payloads; database rows created/updated in staging supabase.
* **Tasks:** mapping code, supabase client wrapper, test with staging DB, idempotency tests.
* **Priority:** P0
* **Complexity:** M

### A.5 Story — Persist raw artifact metadata in coffees (raw\_payload & hashes)

* **Description:** Persist artifact raw JSON, raw\_payload\_hash, content\_hash, and audit fields into `coffees.raw_payload` and columns added by migration.
* **Acceptance Criteria:** After upsert, `coffees.raw_payload_hash` and `coffees.content_hash` are set and `first_seen_at` is populated.
* **Tasks:** hashing utilities, storage integration, DB update via RPC or separate RPC call.
* **Priority:** P0
* **Complexity:** S

---
