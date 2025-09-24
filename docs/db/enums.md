# Database Enums

This document describes all enumerated types (enums) used in the database schema.

## Coffee Status Enum

**Type:** `coffee_status_enum`

**Values:**
- `active` - Coffee is currently available
- `seasonal` - Coffee is available seasonally
- `discontinued` - Coffee is no longer available
- `draft` - Coffee is in draft/preview state
- `hidden` - Coffee is hidden from public view
- `coming_soon` - Coffee will be available soon
- `archived` - Coffee is archived

**Usage:** Used in the `coffees` table to indicate the current status of a coffee product.

## Grind Enum

**Type:** `grind_enum`

**Values:**
- `whole` - Whole bean coffee
- `filter` - Filter grind
- `espresso` - Espresso grind
- `omni` - Omni grind (suitable for multiple brewing methods)
- `other` - Other grind types
- `turkish` - Turkish grind
- `moka` - Moka pot grind
- `cold_brew` - Cold brew grind
- `aeropress` - Aeropress grind
- `channi` - Channi grind
- `coffee filter` - Coffee filter grind
- `cold brew` - Cold brew grind
- `french press` - French press grind
- `home espresso` - Home espresso grind
- `commercial espresso` - Commercial espresso grind
- `inverted aeropress` - Inverted Aeropress grind
- `south indian filter` - South Indian filter grind
- `moka pot` - Moka pot grind
- `pour over` - Pour over grind
- `syphon` - Syphon/vacuum brewing grind

**Usage:** Used in the `variants` table to specify the grind type for coffee variants.

## Platform Enum

**Type:** `platform_enum`

**Values:**
- `shopify` - Shopify e-commerce platform
- `woocommerce` - WooCommerce platform
- `custom` - Custom platform
- `other` - Other platform types

**Usage:** Used in the `roasters` and `product_sources` tables to indicate the e-commerce platform used by roasters.

## Process Enum

**Type:** `process_enum`

**Values:**
- `washed` - Washed process
- `natural` - Natural/dry process
- `honey` - Honey process
- `pulped_natural` - Pulped natural process
- `monsooned` - Monsooned process
- `wet_hulled` - Wet hulled process
- `anaerobic` - Anaerobic process
- `carbonic_maceration` - Carbonic maceration
- `double_fermented` - Double fermented process
- `experimental` - Experimental process
- `other` - Other processing methods

**Usage:** Used in the `coffees` table to specify the coffee processing method.

## Roast Level Enum

**Type:** `roast_level_enum`

**Values:**
- `light` - Light roast
- `light_medium` - Light medium roast
- `medium` - Medium roast
- `medium_dark` - Medium dark roast
- `dark` - Dark roast

**Usage:** Used in the `coffees` table to specify the roast level of the coffee.

## Run Status Enum

**Type:** `run_status_enum`

**Values:**
- `ok` - Run completed successfully
- `partial` - Run completed with some issues
- `fail` - Run failed

**Usage:** Used in the `scrape_runs` table to indicate the status of a scraping run.

## Sensory Confidence Enum

**Type:** `sensory_confidence_enum`

**Values:**
- `high` - High confidence in sensory data
- `medium` - Medium confidence in sensory data
- `low` - Low confidence in sensory data

**Usage:** Used in the `sensory_params` table to indicate the confidence level of sensory analysis data.

## Sensory Source Enum

**Type:** `sensory_source_enum`

**Values:**
- `roaster` - Data provided by the roaster
- `icb_inferred` - Data inferred by ICB system
- `icb_manual` - Data manually entered by ICB

**Usage:** Used in the `sensory_params` table to indicate the source of sensory analysis data.

## Species Enum

**Type:** `species_enum`

**Values:**
- `arabica` - Arabica coffee species
- `robusta` - Robusta coffee species
- `liberica` - Liberica coffee species
- `blend` - Blend of multiple species
- `arabica_80_robusta_20` - 80% Arabica, 20% Robusta blend
- `arabica_70_robusta_30` - 70% Arabica, 30% Robusta blend
- `arabica_60_robusta_40` - 60% Arabica, 40% Robusta blend
- `arabica_50_robusta_50` - 50% Arabica, 50% Robusta blend
- `robusta_80_arabica_20` - 80% Robusta, 20% Arabica blend
- `arabica_chicory` - Arabica coffee with chicory
- `robusta_chicory` - Robusta coffee with chicory
- `blend_chicory` - Mixed blend with chicory
- `filter_coffee_mix` - Traditional South Indian filter coffee mix

**Usage:** Used in the `coffees` table to specify the coffee species.

## Enum Usage in Database Schema

### Tables Using Enums

| Table | Column | Enum Type |
|-------|--------|-----------|
| coffees | bean_species | species_enum |
| coffees | process | process_enum |
| coffees | roast_level | roast_level_enum |
| coffees | status | coffee_status_enum |
| roasters | platform | platform_enum |
| variants | grind | grind_enum |
| product_sources | platform | platform_enum |
| scrape_runs | status | run_status_enum |
| sensory_params | confidence | sensory_confidence_enum |
| sensory_params | source | sensory_source_enum |

### Enum Constants

The database also provides constants for each enum type:

```typescript
export const Constants = {
  public: {
    Enums: {
      coffee_status_enum: [
        "active", "seasonal", "discontinued", "draft", 
        "hidden", "coming_soon", "archived"
      ],
      grind_enum: [
        "whole", "filter", "espresso", "omni", "other",
        "turkish", "moka", "cold_brew", "aeropress", "channi",
        "coffee filter", "cold brew", "french press", 
        "home espresso", "commercial espresso", "inverted aeropress",
        "south indian filter", "moka pot", "pour over", "syphon"
      ],
      platform_enum: ["shopify", "woocommerce", "custom", "other"],
      process_enum: [
        "washed", "natural", "honey", "pulped_natural",
        "monsooned", "wet_hulled", "anaerobic", "carbonic_maceration",
        "double_fermented", "experimental", "other"
      ],
      roast_level_enum: [
        "light", "light_medium", "medium", "medium_dark", "dark"
      ],
      run_status_enum: ["ok", "partial", "fail"],
      sensory_confidence_enum: ["high", "medium", "low"],
      sensory_source_enum: ["roaster", "icb_inferred", "icb_manual"],
      species_enum: [
        "arabica", "robusta", "liberica", "blend",
        "arabica_80_robusta_20", "arabica_70_robusta_30", 
        "arabica_60_robusta_40", "arabica_50_robusta_50", 
        "robusta_80_arabica_20",
        "arabica_chicory", "robusta_chicory", "blend_chicory", 
        "filter_coffee_mix"
      ]
    }
  }
}
```

## Best Practices

1. **Enum Validation**: Always validate enum values before inserting into the database
2. **Default Values**: Consider using appropriate default values for optional enum fields
3. **Extensibility**: When adding new enum values, ensure backward compatibility
4. **Documentation**: Keep enum documentation updated when values change
5. **Type Safety**: Use TypeScript enum types for compile-time type checking

## Example Usage

```typescript
// Creating a coffee with enum values
const coffee = {
  name: "Ethiopian Yirgacheffe",
  bean_species: "arabica" as const,
  process: "washed" as const,
  roast_level: "light" as const,
  status: "active" as const,
  // ... other fields
};

// Creating a variant with grind enum
const variant = {
  coffee_id: "coffee-123",
  grind: "filter" as const,
  weight_g: 250,
  // ... other fields
};

// Sensory parameters with confidence and source
const sensoryParams = {
  coffee_id: "coffee-123",
  acidity: 8.5,
  sweetness: 7.2,
  confidence: "high" as const,
  source: "roaster" as const,
  // ... other fields
};
```
