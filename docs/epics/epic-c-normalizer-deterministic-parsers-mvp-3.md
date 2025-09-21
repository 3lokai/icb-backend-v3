# Epic C — Normalizer & Deterministic Parsers (MVP-3)

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
