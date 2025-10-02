-- Create LLM cache table for storing LLM enrichment results
-- This table supports the D.1 LLM call wrapper & cache story

CREATE TABLE IF NOT EXISTS llm_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on key for fast lookups
CREATE INDEX IF NOT EXISTS idx_llm_cache_key ON llm_cache(key);

-- Create index on expires_at for cleanup operations
CREATE INDEX IF NOT EXISTS idx_llm_cache_expires_at ON llm_cache(expires_at);

-- Create index on created_at for analytics
CREATE INDEX IF NOT EXISTS idx_llm_cache_created_at ON llm_cache(created_at);

-- Add RLS (Row Level Security) if needed
-- ALTER TABLE llm_cache ENABLE ROW LEVEL SECURITY;

-- Create function to automatically update updated_at
CREATE OR REPLACE FUNCTION update_llm_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER trigger_update_llm_cache_updated_at
    BEFORE UPDATE ON llm_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_llm_cache_updated_at();

-- Add comment for documentation
COMMENT ON TABLE llm_cache IS 'Cache table for LLM enrichment results with TTL support';
COMMENT ON COLUMN llm_cache.key IS 'Cache key (typically llm:hash:field format)';
COMMENT ON COLUMN llm_cache.value IS 'Cached LLM result as JSON string';
COMMENT ON COLUMN llm_cache.expires_at IS 'Expiration timestamp for TTL support';
