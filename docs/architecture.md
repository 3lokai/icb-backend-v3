# Coffee Scraper Pipeline — Final Architecture Document

## Executive Summary

This document defines the comprehensive architecture for a production-ready coffee product scraping pipeline that fetches, normalizes, and stores coffee product data from various e-commerce platforms. The system is designed for deployment on Fly.io with robust error handling, observability, and scalability.

**Key Goals:**
- Monthly full product refresh (metadata + normalization + images + optional LLM enrichment)
- Weekly price-only refresh (prices + availability) that is fast, cheap, and idempotent
- Minimal schema changes to existing database
- Production-ready deployment on Fly.io with comprehensive monitoring

## System Architecture Overview

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

## 1. Core Data Flow

### 1.1 Full Pipeline (Monthly)
1. **Fetch** → Store JSON endpoints (Shopify/Woo) as primary source
2. **Validate** → Pydantic v2 validation against canonical artifact schema
3. **Persist** → Raw artifact pointer/hashes to S3/Supabase Storage
4. **Normalize** → Deterministic parsing (weights, roast levels, etc.)
5. **Enrich** → Optional LLM enrichment for ambiguous fields
6. **Upload** → ImageKit upload for new/changed images
7. **Upsert** → `rpc_upsert_coffee` + `rpc_upsert_variant` + `rpc_insert_price` (product + variants + latest prices)
8. **Mark** → Processed status and audit trail

### 1.2 Price-Only Pipeline (Weekly)
1. **Fetch** → Minimal product/variants JSON from list endpoints
2. **Compare** → `price_decimal` vs `variants.price_current`
3. **Update** → `rpc_insert_price` for changes
4. **Sync** → Update `variants.price_current`, `variants.price_last_checked_at`, `variants.in_stock`

## 2. Component Architecture

### 2.1 Scheduler
- **Primary**: GitHub Actions scheduled workflows
- **Fallback**: Small Fly machine with cron
- **Configuration**: Per-roaster cadence overrides in database
- **Default Schedules**:
  - Full refresh: `0 3 1 * *` (monthly at 03:00 UTC on 1st)
  - Price-only: `0 4 * * 0` (weekly Sunday at 04:00 UTC)

### 2.2 Orchestrator & Job Queue
- **Technology**: Redis/Bull or Cloud Tasks
- **Features**: Job state, retries, backoff, per-roaster concurrency
- **Concurrency**: Default 3 workers per roaster (configurable)
- **Backoff**: Exponential retry (1s, 2s, 4s, 8s, 16s) with jitter

### 2.3 Fetcher Pool
- **Technology**: Async `httpx` workers with semaphores
- **Primary Sources**: Shopify JSON, WooCommerce REST API
- **Fallback**: Firecrawl map/extract for JS-heavy sites
- **Politeness**: 250ms ± 100ms jitter, respect robots.txt
- **Caching**: ETag/Last-Modified support for bandwidth efficiency
- **Source Configuration**: Read from `product_sources` table for endpoint configuration

### 2.4 Validator
- **Technology**: Pydantic v2 models from canonical JSON schema
- **Validation**: Strict schema compliance with detailed error reporting
- **Persistence**: Raw artifacts to S3/Supabase Storage for replay
- **Error Handling**: Invalid artifacts marked for manual review
- **Artifact Storage**: Store in `scrape_artifacts` table with run tracking

### 2.5 Normalizer Service
- **Deterministic Parsing**: Weight conversion, currency normalization, roast level mapping
- **LLM Fallback**: Rate-limited enrichment for ambiguous fields only
- **Confidence Scoring**: Auto-apply only if `llm_confidence >= 0.70`
- **Change Detection**: Content hash comparison for efficient processing

### 2.6 Transformer & RPCs
- **Atomic Operations**: All writes through server-side RPCs
- **Idempotency**: Composite keys for safe retries
- **Data Storage Strategy**: 
  - Raw scraping data → `coffees.source_raw` (JSON)
  - LLM enrichment → `coffees.notes_raw` (JSON)
  - Sensory analysis → `sensory_params` table (existing)
- **RPC Functions** (using existing schema):
  - `rpc_upsert_coffee`: Product metadata with parameters: `p_bean_species`, `p_name`, `p_slug`, `p_roaster_id`, `p_process`, `p_roast_level`, `p_description_md`, `p_platform_product_id`, `p_source_raw`, `p_notes_raw`
  - `rpc_upsert_variant`: Single variant upsert with parameters: `p_coffee_id`, `p_platform_variant_id`, `p_sku`, `p_weight_g`, `p_grind`, `p_currency`, `p_in_stock`, `p_source_raw`
  - `rpc_insert_price`: Price time-series insert with parameters: `p_variant_id`, `p_price`, `p_currency`, `p_is_sale`, `p_scraped_at`, `p_source_url`, `p_source_raw`
  - `rpc_upsert_coffee_image`: Image record with parameters: `p_coffee_id`, `p_url`, `p_alt`, `p_width`, `p_height`, `p_sort_order`, `p_source_raw`

### 2.7 ImageKit Integration
- **Upload Strategy**: New/changed images only (hash-based deduplication)
- **CDN**: ImageKit CDN URLs for performance
- **Fallback**: Remote fetch for problematic image hosts
- **Storage**: Both source URL and ImageKit URL stored in `coffee_images` table

## 3. Data Models & Schema

### 3.1 Canonical Artifact Schema
The system uses a comprehensive JSON schema for all scraped data:

**Required Fields:**
- `source`: Origin (shopify, woocommerce, firecrawl, manual, other)
- `roaster_domain`: Store domain (hostname format)
- `scraped_at`: ISO 8601 timestamp
- `product`: Product object with platform identifiers and variants

**Key Product Fields:**
- `platform_product_id`: Unique identifier from source platform
- `title`, `handle`, `description_html/md`: Product information
- `source_url`: Original product URL
- `variants`: Array of product variants with pricing and inventory
- `images`: Array with url, alt_text, order, source_id

**Normalization Fields:**
- `is_coffee`: Boolean coffee classification
- `content_hash`: Hash of normalized content for change detection (stored in `source_raw`)
- `name_clean`, `description_md_clean`: Cleaned text fields
- `roast_level_enum`, `process_enum`: Standardized enums
- `varieties`, `region`, `country`, `altitude_m`: Geographic data
- `llm_enrichment`: LLM-generated data with confidence score (stored in `notes_raw`)
- `sensory_params`: Sensory analysis data (stored in `sensory_params` table)

### 3.2 Database Schema Changes
Minimal additions to existing tables with repurposed fields strategy:

```sql
-- Roaster configuration (roasters table)
ALTER TABLE roasters
  ADD COLUMN full_cadence text,               -- cron: '0 3 1 * *'
  ADD COLUMN price_cadence text,              -- cron: '0 4 * * 0'
  ADD COLUMN default_concurrency int DEFAULT 3,
  ADD COLUMN use_firecrawl_fallback boolean DEFAULT false,
  ADD COLUMN firecrawl_budget_limit int DEFAULT 0,
  -- Essential caching and LLM support
  ADD COLUMN last_etag text,                 -- ETag for 304 handling
  ADD COLUMN last_modified timestamptz,       -- Last-Modified for caching
  ADD COLUMN use_llm boolean DEFAULT false,  -- Per-roaster LLM opt-in
  ADD COLUMN alert_price_delta_pct numeric DEFAULT 0.10; -- Price spike threshold

-- Variant price tracking
ALTER TABLE variants
  ADD COLUMN price_last_checked_at timestamptz,
  ADD COLUMN price_current numeric,
  ADD COLUMN last_seen_at timestamptz,
  ADD COLUMN status text DEFAULT 'active';

-- Coffee minimal new fields (repurpose existing fields for scraping data)
ALTER TABLE coffees
  ADD COLUMN is_coffee boolean DEFAULT true,  -- Coffee classification
  ADD COLUMN tags text[],                     -- Product tags array
  ADD COLUMN varieties text[],                -- Coffee varieties array
  ADD COLUMN region text,                     -- Geographic region
  ADD COLUMN country text,                    -- Country
  ADD COLUMN altitude_m integer,              -- Altitude in meters
  ADD COLUMN default_pack_weight_g integer,   -- Standard pack weight
  ADD COLUMN default_grind grind_enum,        -- Default grind preference
  ADD COLUMN bean_species species_enum,       -- Coffee species (arabica, robusta, etc.)
  ADD COLUMN first_seen_at timestamptz;       -- First discovery timestamp
```

**Repurposed Fields Strategy:**
- **`coffees.source_raw`** → Store complete raw scraping payload (content_hash, raw_payload_hash, artifact_id, collector_signals)
- **`coffees.notes_raw`** → Store LLM enrichment and processing data (llm_enrichment, llm_confidence, processing_warnings)
- **`sensory_params` table** → Already exists for sensory analysis (no changes needed)
- **Existing scraping infrastructure** → `scrape_runs`, `scrape_artifacts`, `product_sources` tables already exist

## 4. Deployment Architecture (Fly.io)

### 4.1 Fly App Structure
Split into multiple Fly apps for isolation and scaling:

1. **api-web**: Web UI, health endpoints, status pages (publicly exposed)
2. **worker-ingest**: Long-running workers for fetch → validate → normalize → transform → RPC upsert
3. **worker-image**: Dedicated image download + ImageKit uploader (optional)
4. **scheduler**: Tiny machine or GitHub Actions for job scheduling
5. **dev/staging**: Mirrors with smaller machines and separate secrets/DB

### 4.2 Filesystem & Persistence
- **Ephemeral Rootfs**: Machine restarts replace root filesystem
- **External Storage**: S3/Supabase Storage for raw artifacts and image backups
- **Fly Volumes**: Only for low-latency, high-I/O needs where persistent local disk is required
- **Worker Design**: Idempotent workers that push results to external storage immediately

### 4.3 Secrets & Configuration
- **Runtime Secrets**: `fly secrets set` per environment
- **Service Role**: RPC-only service accounts in Supabase
- **Per-Roaster Config**: Rate limits, auth tokens in secure config table
- **Environment Separation**: Staging and prod with separate secrets/DB

## 5. Operational Policies

### 5.1 Concurrency & Rate Limiting
- **Per-Roaster Concurrency**: Default 3 workers (configurable)
- **Domain Delays**: 250ms ± 100ms jitter, respect robots.txt crawl-delay
- **Retry Policy**: 5 retries with exponential backoff
- **Permanent Failures**: 4xx errors logged to manual review queue

### 5.2 Data Retention & Cleanup
- **Raw Artifacts**: 90 days retention (configurable)
- **Price Time-Series**: Retained forever or per policy
- **Image Backups**: S3 with lifecycle rules and versioning
- **Database Backups**: Periodic snapshots from Supabase

### 5.3 Error Handling & Monitoring
- **Alert Thresholds**: >5% failures per run OR per-roaster repeat failures
- **Manual Review**: Artifacts with parsing warnings or confidence issues
- **Metrics**: Requests/sec, errors, queue length, per-roaster failure rate
- **Logging**: Structured logs to external provider (Papertrail, Datadog)

## 6. Security & Compliance

### 6.1 Data Protection
- **HTTPS Only**: All communications encrypted
- **API Key Rotation**: Regular rotation of service keys
- **Least Privilege**: RPC-only service accounts
- **Audit Trail**: Complete collector metadata and audit fields

### 6.2 Scraping Ethics
- **Robots.txt Compliance**: Check and respect robots.txt
- **Polite Scraping**: Low request frequency, clear User-Agent
- **Rate Limiting**: Respect roaster API quotas and terms
- **Firecrawl Fallback**: Reduce direct scraping impact

## 7. Performance & Scalability

### 7.1 Non-Functional Requirements
- **Throughput**: 500 products/minute across pool
- **Latency**: Per-artifact pipeline < 5s (excluding image upload & LLM)
- **Availability**: 99.5% for pipeline scheduler and worker execution
- **Error Budget**: <1% failed artifacts/week (excluding malformed roasters)

### 7.2 Scaling Strategy
- **Horizontal Scaling**: Increase worker machine count
- **Per-Roaster Concurrency**: Configure via worker settings, not machine count
- **Auto-scaling**: Fly autoscaling features for autostop/autostart
- **Backpressure**: Pause queue on Supabase RPC rate limits

## 8. Development & Testing

### 8.1 Local Development
- **Docker Compose**: Worker + local Supabase emulator + mock Firecrawl
- **Environment Variables**: Same as Fly to minimize surprises
- **Testing**: Unit tests for parsers, integration tests with staging DB

### 8.2 CI/CD Pipeline
- **GitHub Actions**: Tests, linting, Docker builds, deployment
- **Staging First**: Deploy to staging before production
- **Feature Flags**: Toggle LLM enrichment and Firecrawl fallback
- **Security Scanning**: Docker image vulnerability checks

### 8.3 Quality Assurance
- **Golden Fixtures**: Full example artifacts for testing
- **Integration Tests**: End-to-end pipeline against staging
- **Monitoring**: Dashboards and Slack alerts configured
- **Manual Review**: UI for triaging flagged artifacts

## 9. Failure Modes & Mitigations

### 9.1 Common Failure Scenarios
- **Malformed JSON**: Persist raw blob, mark for review
- **DB Rate Limits**: Pause queue, exponential backoff, alert
- **Image Host Issues**: Use ImageKit remote fetch, flag failing domains
- **LLM Hallucination**: Store raw enrichment + confidence, don't auto-trust

### 9.2 Recovery Procedures
- **Queue Pause**: On DB rate limits, scale down workers
- **Worker OOMs**: Increase machine size or lower concurrency
- **Volume Failures**: Move to API-based persistence, restore from S3
- **Data Corruption**: Replay from raw artifacts in S3

## 10. Monitoring & Observability

### 10.1 Metrics Collection
- **Fetch Metrics**: Requests/sec, latency, success rate per roaster
- **Processing Metrics**: Artifacts processed, parsing warnings count
- **Business Metrics**: Price changes, new products, review queue depth
- **Infrastructure Metrics**: Queue depth, worker health, DB connection pool

### 10.2 Alerting Strategy
- **Critical Alerts**: >5% artifacts flagged for review, DB RPC errors
- **Warning Alerts**: High error volume, queue backup, LLM budget exhausted
- **Info Alerts**: Successful runs, significant price changes
- **Escalation**: Slack notifications, optional PagerDuty integration

### 10.3 Dashboards
- **Operational Dashboard**: Real-time pipeline health, queue status
- **Business Dashboard**: Product counts, price trends, review queue
- **Technical Dashboard**: Error rates, latency, resource utilization
- **Roaster Dashboard**: Per-roaster performance, failure patterns

## 11. Launch Checklist

### 11.1 Pre-Production
- [ ] Local development environment working
- [ ] Unit tests and parser golden tests passing
- [ ] Integration tests against staging Supabase + S3
- [ ] Fly staging apps deployed and smoke-tested
- [ ] Secrets configured for all environments
- [ ] Docker image scanning completed
- [ ] Alerting and dashboards configured

### 11.2 Production Readiness
- [ ] Monitoring dashboards operational
- [ ] Slack alerting configured
- [ ] Runbook procedures documented
- [ ] Backup and recovery procedures tested
- [ ] Performance benchmarks established
- [ ] Security review completed
- [ ] Documentation updated

## 12. Future Considerations

### 12.1 Scalability Enhancements
- **Multi-Region Deployment**: Geographic distribution for global roasters
- **Advanced Caching**: Redis for frequently accessed data
- **Stream Processing**: Real-time price updates for high-value products
- **Machine Learning**: Automated quality scoring and anomaly detection

### 12.2 Feature Extensions
- **Additional Platforms**: Support for more e-commerce platforms
- **Enhanced LLM**: More sophisticated product categorization
- **Real-time Alerts**: Instant notifications for significant price changes
- **API Access**: External API for third-party integrations

---

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Next Review**: Quarterly or after major system changes

This architecture document serves as the definitive reference for the coffee scraper pipeline development and deployment process.
