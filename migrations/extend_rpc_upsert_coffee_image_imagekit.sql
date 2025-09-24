-- migrations/extend_rpc_upsert_coffee_image_imagekit.sql
-- Extend rpc_upsert_coffee_image function to support imagekit_url parameter

CREATE OR REPLACE FUNCTION public.rpc_upsert_coffee_image(
    p_coffee_id TEXT,
    p_url TEXT,
    p_alt TEXT DEFAULT NULL,
    p_width INTEGER DEFAULT NULL,
    p_height INTEGER DEFAULT NULL,
    p_sort_order INTEGER DEFAULT NULL,
    p_source_raw JSONB DEFAULT NULL,
    p_content_hash VARCHAR(64) DEFAULT NULL,
    p_imagekit_url VARCHAR(255) DEFAULT NULL -- New parameter for ImageKit CDN URL
)
RETURNS TEXT
LANGUAGE plpgsql
AS $function$
DECLARE
    v_image_id TEXT;
BEGIN
    -- Check if an image with the same content_hash already exists for this coffee
    IF p_content_hash IS NOT NULL THEN
        SELECT id INTO v_image_id
        FROM public.coffee_images
        WHERE coffee_id = p_coffee_id AND content_hash = p_content_hash
        LIMIT 1;

        IF v_image_id IS NOT NULL THEN
            -- If a duplicate is found, update it with ImageKit URL if provided
            IF p_imagekit_url IS NOT NULL THEN
                UPDATE public.coffee_images
                SET imagekit_url = p_imagekit_url,
                    updated_at = NOW()
                WHERE id = v_image_id;
            END IF;
            
            -- Return existing ID and skip insertion
            RETURN v_image_id;
        END IF;
    END IF;

    -- Upsert logic for new or non-deduplicated images
    INSERT INTO public.coffee_images (
        coffee_id, url, alt, width, height, sort_order, source_raw, content_hash, imagekit_url
    ) VALUES (
        p_coffee_id, p_url, p_alt, p_width, p_height, p_sort_order, p_source_raw, p_content_hash, p_imagekit_url
    )
    ON CONFLICT (coffee_id, url) DO UPDATE SET
        alt = EXCLUDED.alt,
        width = EXCLUDED.width,
        height = EXCLUDED.height,
        sort_order = EXCLUDED.sort_order,
        source_raw = EXCLUDED.source_raw,
        content_hash = EXCLUDED.content_hash,
        imagekit_url = EXCLUDED.imagekit_url, -- Update ImageKit URL if provided
        updated_at = NOW()
    RETURNING id INTO v_image_id;

    RETURN v_image_id;
END;
$function$;
