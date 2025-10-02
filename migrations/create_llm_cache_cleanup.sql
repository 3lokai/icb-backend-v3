-- Create cleanup function for expired LLM cache entries
-- This function can be called periodically to clean up expired cache entries

CREATE OR REPLACE FUNCTION cleanup_expired_llm_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete expired cache entries
    DELETE FROM llm_cache 
    WHERE expires_at IS NOT NULL 
    AND expires_at < NOW();
    
    -- Get count of deleted rows
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Log the cleanup operation
    RAISE NOTICE 'Cleaned up % expired LLM cache entries', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled cleanup job (if pg_cron is available)
-- This would run every hour to clean up expired entries
-- SELECT cron.schedule('cleanup-llm-cache', '0 * * * *', 'SELECT cleanup_expired_llm_cache();');

-- Add comment for documentation
COMMENT ON FUNCTION cleanup_expired_llm_cache() IS 'Cleans up expired LLM cache entries and returns count of deleted rows';
