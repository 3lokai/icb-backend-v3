# Epic G — Observability, Alerts & Ops (MVP-6)

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
