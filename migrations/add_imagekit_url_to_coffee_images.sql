-- migrations/add_imagekit_url_to_coffee_images.sql
-- Add imagekit_url column to coffee_images table for ImageKit CDN integration

-- Add imagekit_url column to store ImageKit CDN URLs
ALTER TABLE public.coffee_images
ADD COLUMN imagekit_url VARCHAR(255);

-- Create index on imagekit_url for fast CDN URL lookups
CREATE INDEX idx_coffee_images_imagekit_url ON public.coffee_images (imagekit_url);

-- Add comment to document the new column
COMMENT ON COLUMN public.coffee_images.imagekit_url IS 'ImageKit CDN URL for optimized image delivery';
