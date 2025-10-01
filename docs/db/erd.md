# Entity Relationship Diagram (ERD)

This document provides a visual and textual representation of the database relationships.

## Core Entity Relationships

### Primary Entities

```
ROASTERS (1) ──────── (N) COFFEES
    │                      │
    │                      │
    └─── (N) PRODUCT_SOURCES │
                            │
                            │
                    (N) ────┴──── (1) SENSORY_PARAMS
```

### Coffee Relationships

```
COFFEES (1) ──────── (N) VARIANTS
    │                      │
    │                      │
    ├─── (N) COFFEE_IMAGES  │
    │                      │
    ├─── (N) COFFEE_BREW_METHODS ──── (N) BREW_METHODS
    │
    ├─── (N) COFFEE_FLAVOR_NOTES ──── (N) FLAVOR_NOTES
    │
    ├─── (N) COFFEE_ESTATES ──── (N) ESTATES ──── (1) REGIONS
    │
    └─── (N) COFFEE_REGIONS ──── (1) REGIONS
```

### Variant and Pricing Relationships

```
VARIANTS (1) ──────── (N) PRICES
    │
    └─── (1) VARIANT_COMPUTED (View)
    │
    └─── (1) VARIANT_LATEST_PRICE (View)
```

### Scraping System Relationships

```
PRODUCT_SOURCES (1) ──────── (N) SCRAPE_RUNS
    │                           │
    └─── (1) ROASTERS           └─── (N) SCRAPE_ARTIFACTS
```

## Detailed Relationship Descriptions

### 1. Roasters to Coffees (One-to-Many)
- **Relationship:** One roaster can have many coffees
- **Foreign Key:** `coffees.roaster_id` → `roasters.id`
- **Cardinality:** 1:N
- **Referenced Relations:** `roasters` (primary), `coffee_summary` (view)

### 2. Coffees to Variants (One-to-Many)
- **Relationship:** One coffee can have many variants (different sizes, grinds)
- **Foreign Key:** `variants.coffee_id` → `coffees.id`
- **Cardinality:** 1:N
- **Referenced Relations:** `coffees` (primary), `coffee_summary` (view)

### 3. Coffees to Images (One-to-Many)
- **Relationship:** One coffee can have many images
- **Foreign Key:** `coffee_images.coffee_id` → `coffees.id`
- **Cardinality:** 1:N
- **Referenced Relations:** `coffees` (primary), `coffee_summary` (view)

### 4. Coffees to Sensory Parameters (One-to-One)
- **Relationship:** One coffee has one set of sensory parameters
- **Foreign Key:** `sensory_params.coffee_id` → `coffees.id`
- **Cardinality:** 1:1
- **Referenced Relations:** `coffees` (primary), `coffee_summary` (view)

### 5. Coffees to Brew Methods (Many-to-Many)
- **Junction Table:** `coffee_brew_methods`
- **Foreign Keys:** 
  - `coffee_brew_methods.coffee_id` → `coffees.id`
  - `coffee_brew_methods.brew_method_id` → `brew_methods.id`
- **Cardinality:** M:N
- **Referenced Relations:** `coffees` (primary), `coffee_summary` (view), `brew_methods`

### 6. Coffees to Flavor Notes (Many-to-Many)
- **Junction Table:** `coffee_flavor_notes`
- **Foreign Keys:**
  - `coffee_flavor_notes.coffee_id` → `coffees.id`
  - `coffee_flavor_notes.flavor_note_id` → `flavor_notes.id`
- **Cardinality:** M:N
- **Referenced Relations:** `coffees` (primary), `coffee_summary` (view), `flavor_notes`

### 7. Coffees to Estates (Many-to-Many with Percentage)
- **Junction Table:** `coffee_estates`
- **Foreign Keys:**
  - `coffee_estates.coffee_id` → `coffees.id`
  - `coffee_estates.estate_id` → `estates.id`
- **Additional Field:** `pct` (percentage of coffee from estate)
- **Cardinality:** M:N
- **Referenced Relations:** `coffees` (primary), `coffee_summary` (view), `estates`

### 8. Coffees to Regions (Many-to-Many with Percentage)
- **Junction Table:** `coffee_regions`
- **Foreign Keys:**
  - `coffee_regions.coffee_id` → `coffees.id`
  - `coffee_regions.region_id` → `regions.id`
- **Additional Field:** `pct` (percentage of coffee from region)
- **Cardinality:** M:N
- **Referenced Relations:** `coffees` (primary), `coffee_summary` (view), `regions`

### 9. Estates to Regions (Many-to-One)
- **Relationship:** Many estates belong to one region
- **Foreign Key:** `estates.region_id` → `regions.id`
- **Cardinality:** N:1

### 10. Variants to Prices (One-to-Many)
- **Relationship:** One variant can have many price records (price history)
- **Foreign Key:** `prices.variant_id` → `variants.id`
- **Cardinality:** 1:N
- **Referenced Relations:** `variants` (primary), `variant_computed` (view), `variant_latest_price` (view)

### 11. Roasters to Product Sources (One-to-Many)
- **Relationship:** One roaster can have many product sources
- **Foreign Key:** `product_sources.roaster_id` → `roasters.id`
- **Cardinality:** 1:N
- **Referenced Relations:** `roasters`

### 12. Product Sources to Scrape Runs (One-to-Many)
- **Relationship:** One product source can have many scrape runs
- **Foreign Key:** `scrape_runs.source_id` → `product_sources.id`
- **Cardinality:** 1:N
- **Referenced Relations:** `product_sources`

### 13. Scrape Runs to Artifacts (One-to-Many)
- **Relationship:** One scrape run can produce many artifacts
- **Foreign Key:** `scrape_artifacts.run_id` → `scrape_runs.id`
- **Cardinality:** 1:N
- **Referenced Relations:** `scrape_runs`

## Database Views and Their Relationships

### Coffee Summary View
- **Base Tables:** `coffees`, `roasters`
- **Purpose:** Provides computed fields and summary data for coffees
- **Key Computed Fields:**
  - `has_250g_bool`: Whether 250g variant exists
  - `has_sensory`: Whether sensory data exists
  - `in_stock_count`: Number of in-stock variants
  - `min_price_in_stock`: Minimum in-stock price
  - `best_normalized_250g`: Best normalized 250g price

### Variant Computed View
- **Base Tables:** `variants`, `prices`
- **Purpose:** Provides computed pricing and availability data
- **Key Computed Fields:**
  - `normalized_250g`: Price normalized to 250g
  - `valid_for_best_value`: Whether variant qualifies for best value
  - `price_one_time`: Current one-time price

### Variant Latest Price View
- **Base Tables:** `variants`, `prices`
- **Purpose:** Shows latest price information for each variant
- **Key Fields:**
  - `scraped_at_latest`: Latest scraping timestamp
  - `is_sale`: Whether current price is a sale price

## Relationship Constraints and Business Rules

### 1. Coffee Status Rules
- Only `active` and `seasonal` coffees should appear in public listings
- `draft` coffees are for internal use only
- `discontinued` coffees should not be available for purchase

### 2. Variant Availability Rules
- Variants must have `in_stock = true` to be available for purchase
- Stock quantity should be updated when orders are placed

### 3. Price History Rules
- Price records should be immutable once created
- Latest price is determined by `scraped_at` timestamp
- Sale prices should have `is_sale = true`

### 4. Scraping Rules
- Scrape runs should be linked to product sources
- Artifacts should be linked to scrape runs
- Failed runs should have `status = 'fail'`

### 5. Geographic Rules
- Estates must belong to regions
- Coffee regions percentages should sum to 100% for each coffee
- Coffee estates percentages should sum to 100% for each coffee

## Indexing Strategy

### Primary Keys
- All tables have UUID primary keys
- Primary keys are automatically indexed

### Foreign Key Indexes
- `coffees.roaster_id`
- `variants.coffee_id`
- `coffee_images.coffee_id`
- `sensory_params.coffee_id`
- `prices.variant_id`
- `estates.region_id`
- `product_sources.roaster_id`
- `scrape_runs.source_id`
- `scrape_artifacts.run_id`

### Composite Indexes
- `coffees(status, roaster_id)` - For filtering active coffees by roaster
- `variants(coffee_id, in_stock)` - For finding in-stock variants
- `prices(variant_id, scraped_at)` - For price history queries
- `coffee_estates(coffee_id, pct)` - For estate percentage queries

### Unique Constraints
- `coffees(slug)` - Unique coffee slugs
- `roasters(slug)` - Unique roaster slugs
- `variants(coffee_id, grind, weight_g)` - Unique variant combinations
- `flavor_notes(key)` - Unique flavor note keys
- `brew_methods(key)` - Unique brew method keys

## Data Integrity Rules

### 1. Referential Integrity
- All foreign keys must reference existing records
- Cascade deletes are not implemented (soft deletes preferred)
- Orphaned records should be cleaned up periodically

### 2. Business Logic Constraints
- Coffee status transitions should follow business rules
- Price values must be positive
- Percentages should be between 0 and 100
- Stock quantities should be non-negative

### 3. Data Validation
- Enum values must be from predefined lists
- URLs should be valid format
- Email addresses should be valid format
- Timestamps should be in ISO format

## Performance Considerations

### 1. Query Optimization
- Use views for complex computed fields
- Implement proper indexing for common queries
- Consider materialized views for expensive computations

### 2. Data Archiving
- Old price records can be archived
- Completed scrape runs can be archived
- Inactive coffees can be archived

### 3. Caching Strategy
- Coffee summary data can be cached
- Price calculations can be cached
- Geographic data rarely changes and can be cached