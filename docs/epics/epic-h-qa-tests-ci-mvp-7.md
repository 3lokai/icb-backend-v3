# Epic H — QA, Tests & CI (MVP-7)

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
