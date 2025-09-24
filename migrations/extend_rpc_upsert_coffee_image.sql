-- Migration: Extend rpc_upsert_coffee_image to support content_hash parameter
-- Created: 2025-01-12
-- Purpose: Enable image deduplication in RPC function

-- Create or replace the rpc_upsert_coffee_image function with content_hash support
CREATE OR REPLACE FUNCTION rpc_upsert_coffee_image(
    p_coffee_id TEXT,
    p_url TEXT,
    p_alt TEXT DEFAULT NULL,
    p_width INTEGER DEFAULT NULL,
    p_height INTEGER DEFAULT NULL,
    p_sort_order INTEGER DEFAULT NULL,
    p_source_raw JSONB DEFAULT NULL,
    p_content_hash VARCHAR(64) DEFAULT NULL
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    v_image_id TEXT;
    v_existing_image_id TEXT;
BEGIN
    -- Check if image with same content_hash already exists
    IF p_content_hash IS NOT NULL THEN
        SELECT id INTO v_existing_image_id
        FROM coffee_images
        WHERE content_hash = p_content_hash
        LIMIT 1;
        
        -- If duplicate found, return existing image ID
        IF v_existing_image_id IS NOT NULL THEN
            RETURN v_existing_image_id;
        END IF;
    END IF;
    
    -- Check if image with same URL already exists for this coffee
    SELECT id INTO v_existing_image_id
    FROM coffee_images
    WHERE coffee_id = p_coffee_id AND url = p_url;
    
    IF v_existing_image_id IS NOT NULL THEN
        -- Update existing image
        UPDATE coffee_images
        SET 
            alt = COALESCE(p_alt, alt),
            width = COALESCE(p_width, width),
            height = COALESCE(p_height, height),
            sort_order = COALESCE(p_sort_order, sort_order),
            source_raw = COALESCE(p_source_raw, source_raw),
            content_hash = COALESCE(p_content_hash, content_hash),
            updated_at = NOW()
        WHERE id = v_existing_image_id;
        
        v_image_id := v_existing_image_id;
    ELSE
        -- Insert new image
        INSERT INTO coffee_images (
            coffee_id,
            url,
            alt,
            width,
            height,
            sort_order,
            source_raw,
            content_hash,
            created_at,
            updated_at
        ) VALUES (
            p_coffee_id,
            p_url,
            p_alt,
            p_width,
            p_height,
            p_sort_order,
            p_source_raw,
            p_content_hash,
            NOW(),
            NOW()
        ) RETURNING id INTO v_image_id;
    END IF;
    
    RETURN v_image_id;
END;
$$;

-- Add comment to document the function
COMMENT ON FUNCTION rpc_upsert_coffee_image IS 'Upsert coffee image with content-based deduplication support';

-- Create helper function to check for duplicate images by content hash
CREATE OR REPLACE FUNCTION rpc_check_duplicate_image_hash(
    p_content_hash VARCHAR(64)
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    v_image_id TEXT;
BEGIN
    -- Check if image with content_hash exists
    SELECT id INTO v_image_id
    FROM coffee_images
    WHERE content_hash = p_content_hash
    LIMIT 1;
    
    RETURN v_image_id;
END;
$$;

-- Add comment to document the helper function
COMMENT ON FUNCTION rpc_check_duplicate_image_hash IS 'Check for duplicate image by content hash, returns image_id if found, NULL if not';
