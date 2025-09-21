# Epic E — Firecrawl Fallback Integration (MVP-4)

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
