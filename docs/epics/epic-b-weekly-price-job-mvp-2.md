# Epic B — Weekly Price Job (MVP-2)

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
