-- Create RPC function to check for existing content hash
-- This function is used by the F.1 deduplication service to check for duplicates

CREATE OR REPLACE FUNCTION public.rpc_check_content_hash(
    p_content_hash VARCHAR(64)
)
RETURNS TEXT
LANGUAGE plpgsql
AS $function$
DECLARE
    v_image_id TEXT;
BEGIN
    -- Check if an image with the same content_hash already exists
    SELECT id INTO v_image_id
    FROM public.coffee_images
    WHERE content_hash = p_content_hash
    LIMIT 1;

    -- Return the image ID if found, NULL if not found
    RETURN v_image_id;
END;
$function$;
