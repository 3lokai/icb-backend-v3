-- Migration: Add content_hash column to coffee_images table for image deduplication
-- Created: 2025-01-12
-- Purpose: Enable content-based image deduplication using SHA256 hashes

-- Add content_hash column to coffee_images table
ALTER TABLE coffee_images 
ADD COLUMN content_hash VARCHAR(64);

-- Add comment to document the column purpose
COMMENT ON COLUMN coffee_images.content_hash IS 'SHA256 hash of image content for deduplication';

-- Create index on content_hash for fast duplicate detection
CREATE INDEX idx_coffee_images_content_hash ON coffee_images(content_hash);

-- Add comment to document the index purpose
COMMENT ON INDEX idx_coffee_images_content_hash IS 'Index for fast duplicate image detection based on content hash';

-- Optional: Add constraint to ensure content_hash is valid SHA256 format (64 hex characters)
-- Note: This constraint is commented out as it may be too restrictive for some use cases
-- ALTER TABLE coffee_images 
-- ADD CONSTRAINT chk_content_hash_format 
-- CHECK (content_hash ~ '^[a-f0-9]{64}$');

-- Update existing records with NULL content_hash (they will be populated during next processing)
-- This is safe as the column allows NULL values
UPDATE coffee_images 
SET content_hash = NULL 
WHERE content_hash IS NULL;

-- Add helpful comment about the migration
COMMENT ON TABLE coffee_images IS 'Images associated with coffees, now with content-based deduplication support';
