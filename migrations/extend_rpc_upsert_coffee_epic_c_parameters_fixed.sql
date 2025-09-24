-- Migration: Extend rpc_upsert_coffee for Epic C normalization parameters (FIXED)
-- Purpose: Add all missing parameters needed for C.3-C.8 stories
-- Date: 2025-01-12
-- Author: Architect

-- Add missing parameters to rpc_upsert_coffee function for Epic C stories
-- This migration adds all the parameters needed for C.3-C.8 stories in one go

-- First, let's check if the function exists and get its current signature
DO $$
BEGIN
    -- Check if rpc_upsert_coffee exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p 
        JOIN pg_namespace n ON p.pronamespace = n.oid 
        WHERE n.nspname = 'public' AND p.proname = 'rpc_upsert_coffee'
    ) THEN
        RAISE EXCEPTION 'rpc_upsert_coffee function does not exist. Please create it first.';
    END IF;
END $$;

-- Drop the existing function to recreate it with new parameters
DROP FUNCTION IF EXISTS rpc_upsert_coffee(
    p_bean_species species_enum,
    p_decaf boolean,
    p_description_md text,
    p_direct_buy_url text,
    p_name text,
    p_notes_raw jsonb,
    p_platform_product_id text,
    p_process process_enum,
    p_process_raw text,
    p_roast_level roast_level_enum,
    p_roast_level_raw text,
    p_roast_style_raw text,
    p_roaster_id text,
    p_slug text,
    p_source_raw jsonb,
    p_status coffee_status_enum
);

-- Create the extended function with all Epic C parameters
CREATE OR REPLACE FUNCTION rpc_upsert_coffee(
    -- Required parameters (no defaults)
    p_bean_species species_enum,
    p_process process_enum,
    p_roast_level roast_level_enum,
    p_roaster_id text,
    p_platform_product_id text,
    p_name text,
    p_slug text,
    p_description_md text,
    p_direct_buy_url text,
    p_process_raw text,
    p_roast_level_raw text,
    p_roast_style_raw text,
    
    -- Optional parameters (all have defaults)
    p_decaf boolean DEFAULT false,
    p_notes_raw jsonb DEFAULT NULL,
    p_source_raw jsonb DEFAULT NULL,
    p_status coffee_status_enum DEFAULT 'active',
    
    -- Epic C.3: Tags & Notes parameters
    p_tags text[] DEFAULT NULL,
    
    -- Epic C.4: Grind & Species parameters  
    p_default_grind grind_enum DEFAULT NULL,
    
    -- Epic C.5: Varieties & Geographic parameters
    p_varieties text[] DEFAULT NULL,
    p_region text DEFAULT NULL,
    p_country text DEFAULT NULL,
    p_altitude integer DEFAULT NULL,
    
    -- Epic C.6: Sensory & Hash parameters
    p_acidity numeric DEFAULT NULL,
    p_body numeric DEFAULT NULL,
    p_flavors text[] DEFAULT NULL,
    p_content_hash text DEFAULT NULL,
    p_raw_hash text DEFAULT NULL,
    
    -- Epic C.7: Text Cleaning parameters
    p_title_cleaned text DEFAULT NULL,
    p_description_cleaned text DEFAULT NULL
)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_coffee_id text;
    v_existing_id text;
BEGIN
    -- Check if coffee already exists by platform_product_id and roaster_id
    SELECT id INTO v_existing_id
    FROM coffees
    WHERE platform_product_id = p_platform_product_id
    AND roaster_id = p_roaster_id;
    
    IF v_existing_id IS NOT NULL THEN
        -- Update existing coffee
        UPDATE coffees SET
            name = p_name,
            slug = p_slug,
            description_md = p_description_md,
            direct_buy_url = p_direct_buy_url,
            vendor_sku = p_platform_product_id,
            status = p_status,
            decaf = p_decaf,
            roast_level = p_roast_level,
            roast_level_raw = p_roast_level_raw,
            roast_style_raw = p_roast_style_raw,
            process = p_process,
            process_raw = p_process_raw,
            bean_species = p_bean_species,
            notes_raw = p_notes_raw,
            source_raw = p_source_raw,
            updated_at = NOW(),
            
            -- Epic C.3: Tags & Notes
            tags = p_tags,
            
            -- Epic C.5: Varieties & Geographic
            varieties = p_varieties,
            
            -- Epic C.7: Text Cleaning
            seo_title = COALESCE(p_title_cleaned, seo_title),
            seo_desc = COALESCE(p_description_cleaned, seo_desc)
        WHERE id = v_existing_id;
        
        v_coffee_id := v_existing_id;
    ELSE
        -- Insert new coffee
        INSERT INTO coffees (
            id, name, slug, roaster_id, description_md, direct_buy_url,
            platform_product_id, vendor_sku, status, decaf, roast_level,
            roast_level_raw, roast_style_raw, process, process_raw, bean_species,
            notes_raw, source_raw, created_at, updated_at,
            
            -- Epic C.3: Tags & Notes
            tags,
            
            -- Epic C.5: Varieties & Geographic
            varieties,
            
            -- Epic C.7: Text Cleaning
            seo_title, seo_desc
        ) VALUES (
            gen_random_uuid(), p_name, p_slug, p_roaster_id, p_description_md, p_direct_buy_url,
            p_platform_product_id, p_platform_product_id, p_status, p_decaf, p_roast_level,
            p_roast_level_raw, p_roast_style_raw, p_process, p_process_raw, p_bean_species,
            p_notes_raw, p_source_raw, NOW(), NOW(),
            
            -- Epic C.3: Tags & Notes
            p_tags,
            
            -- Epic C.5: Varieties & Geographic
            p_varieties,
            
            -- Epic C.7: Text Cleaning
            p_title_cleaned, p_description_cleaned
        ) RETURNING id INTO v_coffee_id;
    END IF;
    
    -- Handle Epic C.5: Geographic data in coffee_regions table
    IF p_region IS NOT NULL OR p_country IS NOT NULL THEN
        -- This would require additional logic to find/create region records
        -- For now, we'll store this in source_raw or create a separate function
        -- This is a placeholder for the geographic data handling
        NULL;
    END IF;
    
    -- Handle Epic C.6: Sensory data in sensory_params table
    IF p_acidity IS NOT NULL OR p_body IS NOT NULL OR p_flavors IS NOT NULL THEN
        -- Check if sensory_params record exists
        IF EXISTS (SELECT 1 FROM sensory_params WHERE coffee_id = v_coffee_id) THEN
            -- Update existing sensory_params
            UPDATE sensory_params SET
                acidity = COALESCE(p_acidity, acidity),
                body = COALESCE(p_body, body),
                updated_at = NOW()
            WHERE coffee_id = v_coffee_id;
        ELSE
            -- Insert new sensory_params
            INSERT INTO sensory_params (
                coffee_id, acidity, body, sweetness, bitterness, aftertaste, clarity,
                confidence, source, notes, created_at, updated_at
            ) VALUES (
                v_coffee_id, p_acidity, p_body, NULL, NULL, NULL, NULL,
                'high', 'icb_inferred', 'Epic C.6 sensory data', NOW(), NOW()
            );
        END IF;
            
        -- Handle flavor notes
        IF p_flavors IS NOT NULL AND array_length(p_flavors, 1) > 0 THEN
            -- This would require additional logic to find/create flavor_note records
            -- For now, we'll store this in the notes field
            UPDATE sensory_params 
            SET notes = COALESCE(notes, '') || ' Flavors: ' || array_to_string(p_flavors, ', ')
            WHERE coffee_id = v_coffee_id;
        END IF;
    END IF;
    
    -- Handle Epic C.6: Hash data
    IF p_content_hash IS NOT NULL OR p_raw_hash IS NOT NULL THEN
        -- Store hash data in source_raw for now
        -- This could be moved to a separate table if needed
        UPDATE coffees 
        SET source_raw = COALESCE(source_raw, '{}'::jsonb) || 
            jsonb_build_object(
                'content_hash', p_content_hash,
                'raw_hash', p_raw_hash
            )
        WHERE id = v_coffee_id;
    END IF;
    
    RETURN v_coffee_id;
END;
$$;

-- Add comments to document the Epic C parameters
COMMENT ON FUNCTION rpc_upsert_coffee IS 'Extended RPC function for Epic C normalization stories. Includes parameters for C.3 (tags/notes), C.4 (grind/species), C.5 (varieties/geographic), C.6 (sensory/hash), and C.7 (text cleaning).';

-- Create indexes for performance on new fields
CREATE INDEX IF NOT EXISTS idx_coffees_tags ON coffees USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_coffees_varieties ON coffees USING GIN (varieties);
CREATE INDEX IF NOT EXISTS idx_coffees_content_hash ON coffees ((source_raw->>'content_hash'));
CREATE INDEX IF NOT EXISTS idx_coffees_raw_hash ON coffees ((source_raw->>'raw_hash'));

-- Add constraints for data validation
ALTER TABLE coffees ADD CONSTRAINT chk_acidity_range CHECK (
    (source_raw->>'acidity')::numeric IS NULL OR 
    ((source_raw->>'acidity')::numeric >= 1 AND (source_raw->>'acidity')::numeric <= 10)
);

ALTER TABLE coffees ADD CONSTRAINT chk_body_range CHECK (
    (source_raw->>'body')::numeric IS NULL OR 
    ((source_raw->>'body')::numeric >= 1 AND (source_raw->>'body')::numeric <= 10)
);

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION rpc_upsert_coffee TO authenticated;
GRANT EXECUTE ON FUNCTION rpc_upsert_coffee TO service_role;

-- Create a helper function to get Epic C parameters from a coffee record
CREATE OR REPLACE FUNCTION get_epic_c_parameters(p_coffee_id text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'tags', tags,
        'varieties', varieties,
        'content_hash', source_raw->>'content_hash',
        'raw_hash', source_raw->>'raw_hash',
        'title_cleaned', seo_title,
        'description_cleaned', seo_desc
    ) INTO v_result
    FROM coffees
    WHERE id = p_coffee_id;
    
    RETURN v_result;
END;
$$;

COMMENT ON FUNCTION get_epic_c_parameters IS 'Helper function to retrieve Epic C parameters from a coffee record.';

-- Grant permissions for the helper function
GRANT EXECUTE ON FUNCTION get_epic_c_parameters TO authenticated;
GRANT EXECUTE ON FUNCTION get_epic_c_parameters TO service_role;
