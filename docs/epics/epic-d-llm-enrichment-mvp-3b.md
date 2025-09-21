# Epic D — LLM Enrichment (MVP-3b)

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
