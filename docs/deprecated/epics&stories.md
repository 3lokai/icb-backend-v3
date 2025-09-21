# Epics & Stories Backlog — Coffee Scraper Pipeline

This is the prioritized, developer-ready epics and stories backlog for the Coffee Scraper Pipeline. Use this to create tickets in your tracker (Jira/GitHub) and assign to squads. Each story includes a short description, acceptance criteria, implementation tasks, priority, and complexity (T-shirt).

---

## Epic A — Ingest: Fetcher + Basic Upsert (MVP-1)

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

## Epic B — Weekly Price Job (MVP-2)

**Goal:** Implement the fast, cheap weekly price-only pipeline that updates prices and availability only.

### B.1 Story — Price-only fetcher path

* **Description:** Implement minimal fetch path that avoids images/LLM and reads only price fields from list endpoints. If list endpoint missing, fetch per-known handles.
* **Acceptance Criteria:** Price-only runs complete for sample roasters and detect price deltas.
* **Tasks:** add job\_type flag, lightweight parser, handle missing endpoints.
* **Priority:** P0
* **Complexity:** S

### B.2 Story — rpc\_insert\_price integration and variant price updates

* **Description:** For each variant price change, call `rpc_insert_price` and update `variants.price_current` and `price_last_checked_at` atomically.
* **Acceptance Criteria:** Price rows inserted and `variants.price_current` updated for changed variants. Unit tests for atomic update.
* **Tasks:** supabase price wrapper, unit tests mocking DB, integration test on staging.
* **Priority:** P0
* **Complexity:** M

### B.3 Story — Price job monitoring & backoff

* **Description:** Add metrics for price job duration, price changes count, and backoff on DB rate-limit. Implement alerts for price spike > threshold.
* **Acceptance Criteria:** Metrics emitted; Slack alert triggered in test when threshold breached.
* **Tasks:** Prometheus exporter or push metrics, integrate with Sentry/Slack, threshold test harness.
* **Priority:** P1
* **Complexity:** M

---

## Epic C — Normalizer & Deterministic Parsers (MVP-3)

**Goal:** Implement deterministic normalization: weight parsing, roast enums, grind extraction, tags normalization, sensory mapping.

### C.1 Story — Weight & unit parser library

* **Description:** Implement robust weight parser to convert strings like "250g", "0.25 kg", "8.8 oz" into grams integer.
* **Acceptance Criteria:** Unit test coverage across 40 variants; accuracy >= 99% on test fixtures.
* **Tasks:** parser implementation, edge-case tests, fallback heuristics.
* **Priority:** P0
* **Complexity:** S

### C.2 Story — Roast & process mapping

* **Description:** Map free-form roast/process strings into enums per PRD (`roast_level_enum`, `process_enum`).
* **Acceptance Criteria:** Unit tests mapping common roast strings to canonical enums; ambiguous strings flagged in `parsing_warnings`.
* **Tasks:** mapping table, regex/lookup and tests.
* **Priority:** P0
* **Complexity:** S

### C.3 Story — Tags normalization & notes extraction

* **Description:** Normalize tags and extract tasting notes to `normalization.notes_raw`.
* **Acceptance Criteria:** Sample product tags normalized; tasting notes extracted into array.
* **Tasks:** normalizer functions, tests.
* **Priority:** P1
* **Complexity:** S

### C.4 Story — Integration: Normalizer in pipeline

* **Description:** Integrate deterministics into pipeline; only call LLM if ambiguous fields remain.
* **Acceptance Criteria:** Full pipeline uses deterministic parsers and only falls back to LLM when heuristics fail; flags stored in `processing_warnings`.
* **Tasks:** normalizer service endpoint/library, integration tests.
* **Priority:** P0
* **Complexity:** M

---

## Epic D — LLM Enrichment (MVP-3b)

**Goal:** Implement rate-limited LLM fallback with caching and confidence logic.

### D.1 Story — LLM call wrapper & cache

* **Description:** Build an adapter for chosen LLM provider; cache results keyed by `raw_payload_hash` and `field`.
* **Acceptance Criteria:** LLM results cached; repeated calls for same artifact use cache; calls rate-limited per roaster.
* **Tasks:** wrapper, cache layer (Redis or DB), tests, per-roaster rate limiter.
* **Priority:** P1
* **Complexity:** M

### D.2 Story — Apply LLM only if confidence >= threshold

* **Description:** Implement logic to accept LLM fields only when `llm_confidence >= 0.7`; otherwise persist enrichment and mark review.
* **Acceptance Criteria:** LLM fields auto-applied only above threshold; below threshold `processing_status='review'` and enrichment persisted.
* **Tasks:** confidence evaluation, DB write path, tests.
* **Priority:** P1
* **Complexity:** S

---

## Epic E — Firecrawl Fallback Integration (MVP-4)

**Goal:** Integrate Firecrawl `map` & `extract` for stores missing JSON endpoints or with JS-heavy pages.

### E.1 Story — Firecrawl map discovery

* **Description:** Implement `map` call to discover product URLs for a domain and store candidate URLs.
* **Acceptance Criteria:** For defined roasters, `map` returns URLs, and they get queued for extract.
* **Tasks:** Firecrawl client, budget handling, queueing product URLs.
* **Priority:** P1
* **Complexity:** M

### E.2 Story — Firecrawl extract → artifact normalizer

* **Description:** Call `extract` per URL and convert output into canonical artifact format for validation/normalization.
* **Acceptance Criteria:** Extracted artifacts validate against schema and can be processed through normal pipeline.
* **Tasks:** converter, tests with sample Firecrawl output.
* **Priority:** P1
* **Complexity:** M

### E.3 Story — Firecrawl budget & fallback policy

* **Description:** Enforce per-roaster `firecrawl_budget_limit`. Stop fallback if exhausted and flag roaster.
* **Acceptance Criteria:** Budget decremented; when zero, no more extracts; ops alerted.
* **Tasks:** budget accounting, alerts, state persistence.
* **Priority:** P2
* **Complexity:** S

---

## Epic F — Image Handling & ImageKit (MVP-5)

**Goal:** Implement image dedupe, upload to ImageKit, and store CDN URLs without reuploading on price-only runs.

### F.1 Story — Image hash & dedupe

* **Description:** Compute image hash (sha256) from remote fetch headers or content; dedupe uploads.
* **Acceptance Criteria:** New images uploaded; reruns detect duplicates and skip upload.
* **Tasks:** image fetcher, hashing, dedupe DB table or column usage, tests.
* **Priority:** P1
* **Complexity:** M

### F.2 Story — ImageKit upload integration

* **Description:** Upload images to ImageKit and store `imagekit_url` via `rpc_upsert_image`.
* **Acceptance Criteria:** ImageKit URLs returned and written to DB; image fallback if upload fails.
* **Tasks:** ImageKit client, retry/backoff, DB wrapper.
* **Priority:** P1
* **Complexity:** M

### F.3 Story — Price-only must not touch images

* **Description:** Enforce that price-only path never triggers image uploads or transforms.
* **Acceptance Criteria:** Code path test asserts image upload not called during price-only run.
* **Tasks:** code guards and tests.
* **Priority:** P0
* **Complexity:** S

---

## Epic G — Observability, Alerts & Ops (MVP-6)

**Goal:** Provide monitoring, logs, and alerting to keep pipeline healthy and debuggable.

### G.1 Story — Metrics exporter & dashboards

* **Description:** Expose metrics (fetch latency, artifact counts, review rate, price deltas) and build Grafana dashboards.
* **Acceptance Criteria:** Dashboards populated from staging runs and cover core run KPIs.
* **Tasks:** Prometheus exporter, Grafana dashboards config, CI smoke tests.
* **Priority:** P0
* **Complexity:** M

### G.2 Story — Error reporting (Sentry) + Slack alerts

* **Description:** Integrate Sentry for exceptions and implement Slack alerts for thresholds (review spike, RPC errors).
* **Acceptance Criteria:** Sentry receives errors; test Slack alerts fire on simulated threshold breaches.
* **Tasks:** Sentry SDK config, alert rules, Slack webhook setup.
* **Priority:** P0
* **Complexity:** S

### G.3 Story — Runbook & playbooks

* **Description:** Document runbook: DB rate-limit handling, backfill procedure, LLM budget exhaustion, Firecrawl budget exhaustion.
* **Acceptance Criteria:** Runbook stored in repo and validated by ops runthrough.
* **Tasks:** write runbook, tabletop drill.
* **Priority:** P1
* **Complexity:** S

---

## Epic H — QA, Tests & CI (MVP-7)

**Goal:** Ship a robust test suite and CI that validates parsing, normalization, and integration with Supabase.

### H.1 Story — Unit tests: parsers & normalizer

* **Description:** Implement unit tests for weight parser, roast mapper, tags normalizer, and fixture-based golden tests.
* **Acceptance Criteria:** Tests pass in CI with 90%+ coverage for parser modules.
* **Tasks:** write tests, fixtures, CI integration.
* **Priority:** P0
* **Complexity:** M

### H.2 Story — Integration tests: staging pipeline

* **Description:** End-to-end test on staging: run full pipeline for a small set of roasters and verify DB states.
* **Acceptance Criteria:** Staging run completes; `coffees`, `variants`, `prices` updated as per AC; `processing_status` flags set appropriately.
* **Tasks:** test harness, sample roaster data, rollback strategy for tests.
* **Priority:** P0
* **Complexity:** L

### H.3 Story — Contract tests for RPCs

* **Description:** Test that RPC contracts (`rpc_upsert_coffee`, `rpc_insert_price`, `rpc_upsert_image`) accept expected payloads.
* **Acceptance Criteria:** Contract tests validate schema and DB constraints; contract failures fail CI.
* **Tasks:** write contract test suite, mock DB errors, CI hooks.
* **Priority:** P0
* **Complexity:** M

---

## Cross-Epic Tasks & Dependencies

* **DB migrations** (final migration SQL) must be applied on staging before RPC & pipeline integration stories run. (Dependency for A.4, A.5, B.2, F.1)
* **Secrets & Fly configuration**: create staging/prod Fly secrets for Supabase, ImageKit, LLM provider before deployments. (Dependency for D, F)
* **Feature flags**: implement global and per-roaster flags for `use_llm` and `use_firecrawl_fallback`. (Dependency for D & E)
* **Golden fixtures**: use `canonical_artifact.json` and `full_example.json` for unit & integration tests. (Dependency for C, H)

---

## Roadmap & Sprint Planning Suggestion

1. **Sprint 1 (2 weeks)**: Epic A (A.1, A.2, A.3, A.4) + DB migration applied to staging. (Dev focus)
2. **Sprint 2 (2 weeks)**: Epic B (B.1, B.2) + basic metrics (G.1). (Dev + Ops)
3. **Sprint 3 (2 weeks)**: Epic C (C.1, C.2, C.4) + H.1 tests. (Dev + QA)
4. **Sprint 4 (2 weeks)**: Epic F (F.1, F.2, F.3) + E.1 Firecrawl map. (Dev)
5. **Sprint 5 (2 weeks)**: Epic D (LLM) + G.2 alerts + full integration tests (H.2). (Full stack)

---

## Ticket naming conventions & templates (copy/paste)

**Title:** `[EpicKey] - Short description` e.g. `[A] - Implement Shopify paginated fetcher`.

**Description template:**

* **What:** One-sentence summary.
* **Why:** Link to PRD section(s) and acceptance criteria.
* **How:** Implementation notes and RPC/migration dependencies.

**Acceptance Criteria:** List (AC1, AC2...).

**Dev tasks:** bullet list of implementation subtasks.

**Labels:** `epic:<key>`, `area:ingest|normalizer|db|ops|qa`, `priority:P0|P1|P2`, `estimate:S|M|L`.

---

*File references used: canonical artifact schema, architecture, and final PRD for mapping & acceptance criteria.*
