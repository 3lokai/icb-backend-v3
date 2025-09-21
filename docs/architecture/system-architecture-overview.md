# System Architecture Overview

```mermaid
flowchart TD
  A[Scheduler: GitHub Actions / Cloud Scheduler] --> B[Orchestrator / Job Queue]
  B --> C[Fetcher Pool]
  C --> C1[Shopify Fetcher (HTTP JSON)]
  C --> C2[Woo Fetcher (WC JSON)]
  C --> C3[Firecrawl Fallback (map/extract)]
  C1 & C2 & C3 --> D[Validator (Pydantic v2) ---> Persist raw artifact (S3/Blob / supabase_scrape_artifacts)]
  D --> E[Normalizer Service]
  E --> E1[Deterministic parsers (regex, unit conversion)]
  E --> E2[LLM Enrichment (fallback) — low qps]
  E --> F[Transformer (Pydantic -> RPC payload)]
  F --> G[Supabase RPCs (rpc_upsert_coffee, rpc_upsert_variant, rpc_insert_price, rpc_upsert_image)]
  F --> H[ImageKit uploader / Image cache]
  G & H --> I[Materialized Views / Dashboard (supabase views)]
  G --> J[Metrics & Logs -> Prometheus / Grafana & Sentry]
  J --> K[Alerting (Slack)]
  subgraph infra
    B
    C
    D
    E
    F
    G
  end
```
