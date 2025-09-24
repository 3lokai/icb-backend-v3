# Epic C — Normalizer & Deterministic Parsers (MVP-3)

**Goal:** Implement comprehensive deterministic normalization for all canonical artifact fields: weight parsing, roast enums, grind extraction, tags normalization, geographic parsing, sensory mapping, content hashing, and name cleaning.

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

### C.4 Story — Grind & bean species parser

* **Description:** Parse grind types and bean species from product titles/descriptions into canonical enums (`default_grind`, `bean_species`).
* **Acceptance Criteria:** Unit tests for grind/species detection; ambiguous cases flagged in `parsing_warnings`.
* **Tasks:** grind/species detection logic, enum mapping, tests.
* **Priority:** P0
* **Complexity:** S

### C.5 Story — Varieties & geographic parser

* **Description:** Extract coffee varieties, region, country, and altitude from product descriptions into structured fields.
* **Acceptance Criteria:** Varieties array populated; geographic data extracted; ambiguous cases flagged.
* **Tasks:** variety extraction, geographic parsing, region/country mapping, tests.
* **Priority:** P1
* **Complexity:** M

### C.6 Story — Sensory params & content hash parser

* **Description:** Parse sensory parameters from descriptions and generate content/raw payload hashes for change detection.
* **Acceptance Criteria:** Sensory params extracted; content hashes generated; confidence scoring implemented.
* **Tasks:** sensory parsing, hash generation, confidence scoring, tests.
* **Priority:** P1
* **Complexity:** M

### C.7 Story — Name & description cleaner

* **Description:** Clean and normalize product names and descriptions, removing HTML and standardizing format.
* **Acceptance Criteria:** Clean names/descriptions generated; HTML stripped; formatting standardized.
* **Tasks:** text cleaning, HTML removal, format standardization, tests.
* **Priority:** P1
* **Complexity:** S

### C.8 Story — Integration: Complete normalizer pipeline

* **Description:** Integrate all deterministic normalizers into pipeline; only call LLM if ambiguous fields remain.
* **Acceptance Criteria:** Full pipeline uses all deterministic parsers; LLM fallback for ambiguous cases; all warnings stored in `processing_warnings`.
* **Tasks:** normalizer service orchestration, LLM fallback logic, integration tests.
* **Priority:** P0
* **Complexity:** L

---

