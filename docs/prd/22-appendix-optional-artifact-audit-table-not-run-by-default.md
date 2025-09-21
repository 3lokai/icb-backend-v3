# 22. Appendix — Optional artifact audit table (not run by default)

If you want full auditability later, create `scrape_artifacts`. This is **optional** and not required for initial launch.

```sql
CREATE TABLE IF NOT EXISTS scrape_artifacts (
  artifact_id text PRIMARY KEY,
  roaster_id uuid REFERENCES roasters(id),
  scraped_at timestamptz,
  raw_payload jsonb,
  raw_payload_hash text,
  content_hash text,
  processed boolean DEFAULT false,
  processing_warnings jsonb,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX ON scrape_artifacts(raw_payload_hash);
```

---

**Note:** This is the final, comprehensive PRD that merges both the database/processing logic and the scraping implementation details into a single, deployable specification.
