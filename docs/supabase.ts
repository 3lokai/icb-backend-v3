export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "13.0.5"
  }
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      brew_methods: {
        Row: {
          id: string
          key: string
          label: string
        }
        Insert: {
          id?: string
          key: string
          label: string
        }
        Update: {
          id?: string
          key?: string
          label?: string
        }
        Relationships: []
      }
      coffee_brew_methods: {
        Row: {
          brew_method_id: string
          coffee_id: string
        }
        Insert: {
          brew_method_id: string
          coffee_id: string
        }
        Update: {
          brew_method_id?: string
          coffee_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "coffee_brew_methods_brew_method_id_fkey"
            columns: ["brew_method_id"]
            isOneToOne: false
            referencedRelation: "brew_methods"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "coffee_brew_methods_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffee_summary"
            referencedColumns: ["coffee_id"]
          },
          {
            foreignKeyName: "coffee_brew_methods_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffees"
            referencedColumns: ["id"]
          },
        ]
      }
      coffee_estates: {
        Row: {
          coffee_id: string
          estate_id: string
          pct: number | null
        }
        Insert: {
          coffee_id: string
          estate_id: string
          pct?: number | null
        }
        Update: {
          coffee_id?: string
          estate_id?: string
          pct?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "coffee_estates_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffee_summary"
            referencedColumns: ["coffee_id"]
          },
          {
            foreignKeyName: "coffee_estates_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffees"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "coffee_estates_estate_id_fkey"
            columns: ["estate_id"]
            isOneToOne: false
            referencedRelation: "estates"
            referencedColumns: ["id"]
          },
        ]
      }
      coffee_flavor_notes: {
        Row: {
          coffee_id: string
          flavor_note_id: string
        }
        Insert: {
          coffee_id: string
          flavor_note_id: string
        }
        Update: {
          coffee_id?: string
          flavor_note_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "coffee_flavor_notes_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffee_summary"
            referencedColumns: ["coffee_id"]
          },
          {
            foreignKeyName: "coffee_flavor_notes_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffees"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "coffee_flavor_notes_flavor_note_id_fkey"
            columns: ["flavor_note_id"]
            isOneToOne: false
            referencedRelation: "flavor_notes"
            referencedColumns: ["id"]
          },
        ]
      }
      coffee_images: {
        Row: {
          alt: string | null
          coffee_id: string
          content_hash: string | null
          height: number | null
          id: string
          imagekit_url: string | null
          sort_order: number
          source_raw: Json
          url: string
          width: number | null
        }
        Insert: {
          alt?: string | null
          coffee_id: string
          content_hash?: string | null
          height?: number | null
          id?: string
          imagekit_url?: string | null
          sort_order?: number
          source_raw?: Json
          url: string
          width?: number | null
        }
        Update: {
          alt?: string | null
          coffee_id?: string
          content_hash?: string | null
          height?: number | null
          id?: string
          imagekit_url?: string | null
          sort_order?: number
          source_raw?: Json
          url?: string
          width?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "coffee_images_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffee_summary"
            referencedColumns: ["coffee_id"]
          },
          {
            foreignKeyName: "coffee_images_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffees"
            referencedColumns: ["id"]
          },
        ]
      }
      coffee_regions: {
        Row: {
          coffee_id: string
          pct: number | null
          region_id: string
        }
        Insert: {
          coffee_id: string
          pct?: number | null
          region_id: string
        }
        Update: {
          coffee_id?: string
          pct?: number | null
          region_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "coffee_regions_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffee_summary"
            referencedColumns: ["coffee_id"]
          },
          {
            foreignKeyName: "coffee_regions_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffees"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "coffee_regions_region_id_fkey"
            columns: ["region_id"]
            isOneToOne: false
            referencedRelation: "regions"
            referencedColumns: ["id"]
          },
        ]
      }
      coffees: {
        Row: {
          bean_species: Database["public"]["Enums"]["species_enum"] | null
          created_at: string
          crop_year: number | null
          decaf: boolean
          description_md: string | null
          direct_buy_url: string | null
          first_seen_at: string | null
          harvest_window: string | null
          id: string
          is_coffee: boolean | null
          is_limited: boolean
          name: string
          notes_lang: string | null
          notes_raw: Json
          platform_product_id: string | null
          process: Database["public"]["Enums"]["process_enum"] | null
          process_raw: string | null
          rating_avg: number | null
          rating_count: number
          roast_level: Database["public"]["Enums"]["roast_level_enum"] | null
          roast_level_raw: string | null
          roast_style_raw: string | null
          roaster_id: string
          seo_desc: string | null
          seo_title: string | null
          slug: string
          source_raw: Json
          status: Database["public"]["Enums"]["coffee_status_enum"]
          tags: string[] | null
          updated_at: string
          varieties: string[] | null
          vendor_sku: string | null
        }
        Insert: {
          bean_species?: Database["public"]["Enums"]["species_enum"] | null
          created_at?: string
          crop_year?: number | null
          decaf?: boolean
          description_md?: string | null
          direct_buy_url?: string | null
          first_seen_at?: string | null
          harvest_window?: string | null
          id?: string
          is_coffee?: boolean | null
          is_limited?: boolean
          name: string
          notes_lang?: string | null
          notes_raw?: Json
          platform_product_id?: string | null
          process?: Database["public"]["Enums"]["process_enum"] | null
          process_raw?: string | null
          rating_avg?: number | null
          rating_count?: number
          roast_level?: Database["public"]["Enums"]["roast_level_enum"] | null
          roast_level_raw?: string | null
          roast_style_raw?: string | null
          roaster_id: string
          seo_desc?: string | null
          seo_title?: string | null
          slug: string
          source_raw?: Json
          status?: Database["public"]["Enums"]["coffee_status_enum"]
          tags?: string[] | null
          updated_at?: string
          varieties?: string[] | null
          vendor_sku?: string | null
        }
        Update: {
          bean_species?: Database["public"]["Enums"]["species_enum"] | null
          created_at?: string
          crop_year?: number | null
          decaf?: boolean
          description_md?: string | null
          direct_buy_url?: string | null
          first_seen_at?: string | null
          harvest_window?: string | null
          id?: string
          is_coffee?: boolean | null
          is_limited?: boolean
          name?: string
          notes_lang?: string | null
          notes_raw?: Json
          platform_product_id?: string | null
          process?: Database["public"]["Enums"]["process_enum"] | null
          process_raw?: string | null
          rating_avg?: number | null
          rating_count?: number
          roast_level?: Database["public"]["Enums"]["roast_level_enum"] | null
          roast_level_raw?: string | null
          roast_style_raw?: string | null
          roaster_id?: string
          seo_desc?: string | null
          seo_title?: string | null
          slug?: string
          source_raw?: Json
          status?: Database["public"]["Enums"]["coffee_status_enum"]
          tags?: string[] | null
          updated_at?: string
          varieties?: string[] | null
          vendor_sku?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "coffees_roaster_id_fkey"
            columns: ["roaster_id"]
            isOneToOne: false
            referencedRelation: "roasters"
            referencedColumns: ["id"]
          },
        ]
      }
      estates: {
        Row: {
          altitude_max_m: number | null
          altitude_min_m: number | null
          id: string
          name: string
          notes: string | null
          region_id: string | null
        }
        Insert: {
          altitude_max_m?: number | null
          altitude_min_m?: number | null
          id?: string
          name: string
          notes?: string | null
          region_id?: string | null
        }
        Update: {
          altitude_max_m?: number | null
          altitude_min_m?: number | null
          id?: string
          name?: string
          notes?: string | null
          region_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "estates_region_id_fkey"
            columns: ["region_id"]
            isOneToOne: false
            referencedRelation: "regions"
            referencedColumns: ["id"]
          },
        ]
      }
      flavor_notes: {
        Row: {
          group_key: string | null
          id: string
          key: string
          label: string
        }
        Insert: {
          group_key?: string | null
          id?: string
          key: string
          label: string
        }
        Update: {
          group_key?: string | null
          id?: string
          key?: string
          label?: string
        }
        Relationships: []
      }
      prices: {
        Row: {
          currency: string
          id: string
          is_sale: boolean
          price: number
          scraped_at: string
          source_raw: Json
          source_url: string | null
          variant_id: string
        }
        Insert: {
          currency?: string
          id?: string
          is_sale?: boolean
          price: number
          scraped_at?: string
          source_raw?: Json
          source_url?: string | null
          variant_id: string
        }
        Update: {
          currency?: string
          id?: string
          is_sale?: boolean
          price?: number
          scraped_at?: string
          source_raw?: Json
          source_url?: string | null
          variant_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "prices_variant_id_fkey"
            columns: ["variant_id"]
            isOneToOne: false
            referencedRelation: "variant_computed"
            referencedColumns: ["variant_id"]
          },
          {
            foreignKeyName: "prices_variant_id_fkey"
            columns: ["variant_id"]
            isOneToOne: false
            referencedRelation: "variant_latest_price"
            referencedColumns: ["variant_id"]
          },
          {
            foreignKeyName: "prices_variant_id_fkey"
            columns: ["variant_id"]
            isOneToOne: false
            referencedRelation: "variants"
            referencedColumns: ["id"]
          },
        ]
      }
      product_sources: {
        Row: {
          base_url: string
          id: string
          last_ok_ping: string | null
          platform: Database["public"]["Enums"]["platform_enum"] | null
          products_endpoint: string | null
          roaster_id: string
          robots_ok: boolean | null
          sitemap_url: string | null
        }
        Insert: {
          base_url: string
          id?: string
          last_ok_ping?: string | null
          platform?: Database["public"]["Enums"]["platform_enum"] | null
          products_endpoint?: string | null
          roaster_id: string
          robots_ok?: boolean | null
          sitemap_url?: string | null
        }
        Update: {
          base_url?: string
          id?: string
          last_ok_ping?: string | null
          platform?: Database["public"]["Enums"]["platform_enum"] | null
          products_endpoint?: string | null
          roaster_id?: string
          robots_ok?: boolean | null
          sitemap_url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "product_sources_roaster_id_fkey"
            columns: ["roaster_id"]
            isOneToOne: false
            referencedRelation: "roasters"
            referencedColumns: ["id"]
          },
        ]
      }
      regions: {
        Row: {
          country: string
          display_name: string
          id: string
          state: string | null
          subregion: string | null
        }
        Insert: {
          country: string
          display_name: string
          id?: string
          state?: string | null
          subregion?: string | null
        }
        Update: {
          country?: string
          display_name?: string
          id?: string
          state?: string | null
          subregion?: string | null
        }
        Relationships: []
      }
      roasters: {
        Row: {
          alert_price_delta_pct: number | null
          created_at: string
          default_concurrency: number | null
          firecrawl_budget_limit: number | null
          full_cadence: string | null
          hq_city: string | null
          hq_country: string | null
          hq_state: string | null
          id: string
          instagram_handle: string | null
          is_active: boolean
          last_etag: string | null
          last_modified: string | null
          lat: number | null
          lon: number | null
          name: string
          phone: string | null
          platform: Database["public"]["Enums"]["platform_enum"] | null
          price_cadence: string | null
          robots_allow: boolean | null
          robots_checked_at: string | null
          slug: string
          social_json: Json
          support_email: string | null
          updated_at: string
          use_firecrawl_fallback: boolean | null
          use_llm: boolean | null
          website: string | null
        }
        Insert: {
          alert_price_delta_pct?: number | null
          created_at?: string
          default_concurrency?: number | null
          firecrawl_budget_limit?: number | null
          full_cadence?: string | null
          hq_city?: string | null
          hq_country?: string | null
          hq_state?: string | null
          id?: string
          instagram_handle?: string | null
          is_active?: boolean
          last_etag?: string | null
          last_modified?: string | null
          lat?: number | null
          lon?: number | null
          name: string
          phone?: string | null
          platform?: Database["public"]["Enums"]["platform_enum"] | null
          price_cadence?: string | null
          robots_allow?: boolean | null
          robots_checked_at?: string | null
          slug: string
          social_json?: Json
          support_email?: string | null
          updated_at?: string
          use_firecrawl_fallback?: boolean | null
          use_llm?: boolean | null
          website?: string | null
        }
        Update: {
          alert_price_delta_pct?: number | null
          created_at?: string
          default_concurrency?: number | null
          firecrawl_budget_limit?: number | null
          full_cadence?: string | null
          hq_city?: string | null
          hq_country?: string | null
          hq_state?: string | null
          id?: string
          instagram_handle?: string | null
          is_active?: boolean
          last_etag?: string | null
          last_modified?: string | null
          lat?: number | null
          lon?: number | null
          name?: string
          phone?: string | null
          platform?: Database["public"]["Enums"]["platform_enum"] | null
          price_cadence?: string | null
          robots_allow?: boolean | null
          robots_checked_at?: string | null
          slug?: string
          social_json?: Json
          support_email?: string | null
          updated_at?: string
          use_firecrawl_fallback?: boolean | null
          use_llm?: boolean | null
          website?: string | null
        }
        Relationships: []
      }
      scrape_artifacts: {
        Row: {
          body_len: number | null
          http_status: number | null
          id: string
          run_id: string | null
          saved_html_path: string | null
          saved_json: Json | null
          url: string | null
        }
        Insert: {
          body_len?: number | null
          http_status?: number | null
          id?: string
          run_id?: string | null
          saved_html_path?: string | null
          saved_json?: Json | null
          url?: string | null
        }
        Update: {
          body_len?: number | null
          http_status?: number | null
          id?: string
          run_id?: string | null
          saved_html_path?: string | null
          saved_json?: Json | null
          url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "scrape_artifacts_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: false
            referencedRelation: "scrape_runs"
            referencedColumns: ["id"]
          },
        ]
      }
      scrape_runs: {
        Row: {
          finished_at: string | null
          id: string
          source_id: string | null
          started_at: string
          stats_json: Json
          status: Database["public"]["Enums"]["run_status_enum"] | null
        }
        Insert: {
          finished_at?: string | null
          id?: string
          source_id?: string | null
          started_at?: string
          stats_json?: Json
          status?: Database["public"]["Enums"]["run_status_enum"] | null
        }
        Update: {
          finished_at?: string | null
          id?: string
          source_id?: string | null
          started_at?: string
          stats_json?: Json
          status?: Database["public"]["Enums"]["run_status_enum"] | null
        }
        Relationships: [
          {
            foreignKeyName: "scrape_runs_source_id_fkey"
            columns: ["source_id"]
            isOneToOne: false
            referencedRelation: "product_sources"
            referencedColumns: ["id"]
          },
        ]
      }
      sensory_params: {
        Row: {
          acidity: number | null
          aftertaste: number | null
          bitterness: number | null
          body: number | null
          clarity: number | null
          coffee_id: string
          confidence:
            | Database["public"]["Enums"]["sensory_confidence_enum"]
            | null
          created_at: string
          notes: string | null
          source: Database["public"]["Enums"]["sensory_source_enum"] | null
          sweetness: number | null
          updated_at: string
        }
        Insert: {
          acidity?: number | null
          aftertaste?: number | null
          bitterness?: number | null
          body?: number | null
          clarity?: number | null
          coffee_id: string
          confidence?:
            | Database["public"]["Enums"]["sensory_confidence_enum"]
            | null
          created_at?: string
          notes?: string | null
          source?: Database["public"]["Enums"]["sensory_source_enum"] | null
          sweetness?: number | null
          updated_at?: string
        }
        Update: {
          acidity?: number | null
          aftertaste?: number | null
          bitterness?: number | null
          body?: number | null
          clarity?: number | null
          coffee_id?: string
          confidence?:
            | Database["public"]["Enums"]["sensory_confidence_enum"]
            | null
          created_at?: string
          notes?: string | null
          source?: Database["public"]["Enums"]["sensory_source_enum"] | null
          sweetness?: number | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "sensory_params_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: true
            referencedRelation: "coffee_summary"
            referencedColumns: ["coffee_id"]
          },
          {
            foreignKeyName: "sensory_params_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: true
            referencedRelation: "coffees"
            referencedColumns: ["id"]
          },
        ]
      }
      variants: {
        Row: {
          barcode: string | null
          coffee_id: string
          compare_at_price: number | null
          created_at: string
          currency: string
          grind: Database["public"]["Enums"]["grind_enum"]
          id: string
          in_stock: boolean
          last_seen_at: string | null
          pack_count: number
          platform_variant_id: string | null
          price_current: number | null
          price_last_checked_at: string | null
          sku: string | null
          source_raw: Json
          status: string | null
          stock_qty: number | null
          subscription_available: boolean
          updated_at: string
          weight_g: number
        }
        Insert: {
          barcode?: string | null
          coffee_id: string
          compare_at_price?: number | null
          created_at?: string
          currency?: string
          grind?: Database["public"]["Enums"]["grind_enum"]
          id?: string
          in_stock?: boolean
          last_seen_at?: string | null
          pack_count?: number
          platform_variant_id?: string | null
          price_current?: number | null
          price_last_checked_at?: string | null
          sku?: string | null
          source_raw?: Json
          status?: string | null
          stock_qty?: number | null
          subscription_available?: boolean
          updated_at?: string
          weight_g: number
        }
        Update: {
          barcode?: string | null
          coffee_id?: string
          compare_at_price?: number | null
          created_at?: string
          currency?: string
          grind?: Database["public"]["Enums"]["grind_enum"]
          id?: string
          in_stock?: boolean
          last_seen_at?: string | null
          pack_count?: number
          platform_variant_id?: string | null
          price_current?: number | null
          price_last_checked_at?: string | null
          sku?: string | null
          source_raw?: Json
          status?: string | null
          stock_qty?: number | null
          subscription_available?: boolean
          updated_at?: string
          weight_g?: number
        }
        Relationships: [
          {
            foreignKeyName: "variants_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffee_summary"
            referencedColumns: ["coffee_id"]
          },
          {
            foreignKeyName: "variants_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffees"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      coffee_summary: {
        Row: {
          best_normalized_250g: number | null
          best_variant_id: string | null
          coffee_id: string | null
          direct_buy_url: string | null
          has_250g_bool: boolean | null
          has_sensory: boolean | null
          in_stock_count: number | null
          min_price_in_stock: number | null
          name: string | null
          process: Database["public"]["Enums"]["process_enum"] | null
          process_raw: string | null
          roast_level: Database["public"]["Enums"]["roast_level_enum"] | null
          roast_level_raw: string | null
          roast_style_raw: string | null
          roaster_id: string | null
          sensory_public: Json | null
          sensory_updated_at: string | null
          slug: string | null
          status: Database["public"]["Enums"]["coffee_status_enum"] | null
          weights_available: number[] | null
        }
        Relationships: [
          {
            foreignKeyName: "coffees_roaster_id_fkey"
            columns: ["roaster_id"]
            isOneToOne: false
            referencedRelation: "roasters"
            referencedColumns: ["id"]
          },
        ]
      }
      variant_computed: {
        Row: {
          coffee_id: string | null
          compare_at_price: number | null
          currency: string | null
          grind: Database["public"]["Enums"]["grind_enum"] | null
          in_stock: boolean | null
          normalized_250g: number | null
          pack_count: number | null
          price_one_time: number | null
          scraped_at_latest: string | null
          valid_for_best_value: boolean | null
          variant_id: string | null
          weight_g: number | null
        }
        Relationships: [
          {
            foreignKeyName: "variants_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffee_summary"
            referencedColumns: ["coffee_id"]
          },
          {
            foreignKeyName: "variants_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffees"
            referencedColumns: ["id"]
          },
        ]
      }
      variant_latest_price: {
        Row: {
          coffee_id: string | null
          compare_at_price: number | null
          currency: string | null
          grind: Database["public"]["Enums"]["grind_enum"] | null
          in_stock: boolean | null
          is_sale: boolean | null
          pack_count: number | null
          price_one_time: number | null
          scraped_at_latest: string | null
          variant_id: string | null
          weight_g: number | null
        }
        Relationships: [
          {
            foreignKeyName: "variants_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffee_summary"
            referencedColumns: ["coffee_id"]
          },
          {
            foreignKeyName: "variants_coffee_id_fkey"
            columns: ["coffee_id"]
            isOneToOne: false
            referencedRelation: "coffees"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Functions: {
      citext: {
        Args: { "": boolean } | { "": string } | { "": unknown }
        Returns: string
      }
      citext_hash: {
        Args: { "": string }
        Returns: number
      }
      citextin: {
        Args: { "": unknown }
        Returns: string
      }
      citextout: {
        Args: { "": string }
        Returns: unknown
      }
      citextrecv: {
        Args: { "": unknown }
        Returns: string
      }
      citextsend: {
        Args: { "": string }
        Returns: string
      }
      get_epic_c_parameters: {
        Args: { p_coffee_id: string }
        Returns: Json
      }
      map_roast_legacy: {
        Args: { raw: string }
        Returns: Database["public"]["Enums"]["roast_level_enum"]
      }
      rpc_check_content_hash: {
        Args: { p_content_hash: string }
        Returns: string
      }
      rpc_check_duplicate_image_hash: {
        Args: { p_content_hash: string }
        Returns: string
      }
      rpc_insert_price: {
        Args: {
          p_currency?: string
          p_is_sale?: boolean
          p_price: number
          p_scraped_at?: string
          p_source_raw?: Json
          p_source_url?: string
          p_variant_id: string
        }
        Returns: string
      }
      rpc_record_artifact: {
        Args: {
          p_body_len: number
          p_http_status: number
          p_run_id: string
          p_saved_html_path?: string
          p_saved_json?: Json
          p_url: string
        }
        Returns: string
      }
      rpc_scrape_run_finish: {
        Args: {
          p_run_id: string
          p_stats: Json
          p_status: Database["public"]["Enums"]["run_status_enum"]
        }
        Returns: undefined
      }
      rpc_scrape_run_start: {
        Args: { p_source_id: string }
        Returns: string
      }
      rpc_upsert_coffee: {
        Args: {
          p_acidity?: number
          p_altitude?: number
          p_bean_species: Database["public"]["Enums"]["species_enum"]
          p_body?: number
          p_content_hash?: string
          p_country?: string
          p_decaf?: boolean
          p_default_grind?: Database["public"]["Enums"]["grind_enum"]
          p_description_cleaned?: string
          p_description_md: string
          p_direct_buy_url: string
          p_flavors?: string[]
          p_name: string
          p_notes_raw?: Json
          p_platform_product_id: string
          p_process: Database["public"]["Enums"]["process_enum"]
          p_process_raw: string
          p_raw_hash?: string
          p_region?: string
          p_roast_level: Database["public"]["Enums"]["roast_level_enum"]
          p_roast_level_raw: string
          p_roast_style_raw: string
          p_roaster_id: string
          p_slug: string
          p_source_raw?: Json
          p_status?: Database["public"]["Enums"]["coffee_status_enum"]
          p_tags?: string[]
          p_title_cleaned?: string
          p_varieties?: string[]
        }
        Returns: string
      }
      rpc_upsert_coffee_flavor_note: {
        Args: { p_coffee_id: string; p_flavor_note_id: string }
        Returns: boolean
      }
      rpc_upsert_coffee_image: {
        Args: {
          p_alt?: string
          p_coffee_id: string
          p_content_hash?: string
          p_height?: number
          p_imagekit_url?: string
          p_sort_order?: number
          p_source_raw?: Json
          p_url: string
          p_width?: number
        }
        Returns: string
      }
      rpc_upsert_flavor_note: {
        Args: { p_group_key?: string; p_key: string; p_label: string }
        Returns: string
      }
      rpc_upsert_roaster: {
        Args: {
          p_instagram_handle?: string
          p_name: string
          p_platform: Database["public"]["Enums"]["platform_enum"]
          p_slug: string
          p_social_json?: Json
          p_support_email?: string
          p_website: string
        }
        Returns: string
      }
      rpc_upsert_variant: {
        Args:
          | {
              p_coffee_id: string
              p_compare_at_price?: number
              p_currency?: string
              p_grind?: Database["public"]["Enums"]["grind_enum"]
              p_in_stock?: boolean
              p_pack_count?: number
              p_platform_variant_id: string
              p_sku: string
              p_source_raw?: Json
              p_stock_qty?: number
              p_subscription_available?: boolean
              p_weight_g: number
            }
          | {
              p_coffee_id: string
              p_compare_at_price?: number
              p_currency?: string
              p_grind?: Database["public"]["Enums"]["grind_enum"]
              p_in_stock?: boolean
              p_pack_count?: number
              p_platform_variant_id: string
              p_sku: string
              p_source_raw?: Json
              p_weight_g: number
            }
        Returns: string
      }
    }
    Enums: {
      coffee_status_enum:
        | "active"
        | "seasonal"
        | "discontinued"
        | "draft"
        | "hidden"
        | "coming_soon"
        | "archived"
      grind_enum:
        | "whole"
        | "filter"
        | "espresso"
        | "omni"
        | "other"
        | "turkish"
        | "moka"
        | "cold_brew"
        | "aeropress"
        | "channi"
        | "coffee filter"
        | "cold brew"
        | "french press"
        | "home espresso"
        | "commercial espresso"
        | "inverted aeropress"
        | "south indian filter"
        | "moka pot"
        | "pour over"
        | "syphon"
      platform_enum: "shopify" | "woocommerce" | "custom" | "other"
      process_enum:
        | "washed"
        | "natural"
        | "honey"
        | "pulped_natural"
        | "monsooned"
        | "wet_hulled"
        | "anaerobic"
        | "carbonic_maceration"
        | "double_fermented"
        | "experimental"
        | "other"
      roast_level_enum:
        | "light"
        | "light_medium"
        | "medium"
        | "medium_dark"
        | "dark"
      run_status_enum: "ok" | "partial" | "fail"
      sensory_confidence_enum: "high" | "medium" | "low"
      sensory_source_enum: "roaster" | "icb_inferred" | "icb_manual"
      species_enum:
        | "arabica"
        | "robusta"
        | "liberica"
        | "blend"
        | "arabica_80_robusta_20"
        | "arabica_70_robusta_30"
        | "arabica_60_robusta_40"
        | "arabica_50_robusta_50"
        | "robusta_80_arabica_20"
        | "arabica_chicory"
        | "robusta_chicory"
        | "blend_chicory"
        | "filter_coffee_mix"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {
      coffee_status_enum: [
        "active",
        "seasonal",
        "discontinued",
        "draft",
        "hidden",
        "coming_soon",
        "archived",
      ],
      grind_enum: [
        "whole",
        "filter",
        "espresso",
        "omni",
        "other",
        "turkish",
        "moka",
        "cold_brew",
        "aeropress",
        "channi",
        "coffee filter",
        "cold brew",
        "french press",
        "home espresso",
        "commercial espresso",
        "inverted aeropress",
        "south indian filter",
        "moka pot",
        "pour over",
        "syphon",
      ],
      platform_enum: ["shopify", "woocommerce", "custom", "other"],
      process_enum: [
        "washed",
        "natural",
        "honey",
        "pulped_natural",
        "monsooned",
        "wet_hulled",
        "anaerobic",
        "carbonic_maceration",
        "double_fermented",
        "experimental",
        "other",
      ],
      roast_level_enum: [
        "light",
        "light_medium",
        "medium",
        "medium_dark",
        "dark",
      ],
      run_status_enum: ["ok", "partial", "fail"],
      sensory_confidence_enum: ["high", "medium", "low"],
      sensory_source_enum: ["roaster", "icb_inferred", "icb_manual"],
      species_enum: [
        "arabica",
        "robusta",
        "liberica",
        "blend",
        "arabica_80_robusta_20",
        "arabica_70_robusta_30",
        "arabica_60_robusta_40",
        "arabica_50_robusta_50",
        "robusta_80_arabica_20",
        "arabica_chicory",
        "robusta_chicory",
        "blend_chicory",
        "filter_coffee_mix",
      ],
    },
  },
} as const
