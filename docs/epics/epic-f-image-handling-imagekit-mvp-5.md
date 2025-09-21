# Epic F — Image Handling & ImageKit (MVP-5)

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
