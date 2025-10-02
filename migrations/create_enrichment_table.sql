-- Create simple enrichment table for storing LLM enrichment results
-- This table supports the D.2 confidence threshold logic story

CREATE TABLE IF NOT EXISTS enrichments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrichment_id TEXT NOT NULL UNIQUE,
    artifact_id TEXT NOT NULL,
    field TEXT NOT NULL,
    llm_result JSONB NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    applied BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create basic indexes for performance
CREATE INDEX IF NOT EXISTS idx_enrichments_artifact_id ON enrichments(artifact_id);
CREATE INDEX IF NOT EXISTS idx_enrichments_field ON enrichments(field);
CREATE INDEX IF NOT EXISTS idx_enrichments_applied ON enrichments(applied);
CREATE INDEX IF NOT EXISTS idx_enrichments_confidence_score ON enrichments(confidence_score);

-- Add comments for documentation
COMMENT ON TABLE enrichments IS 'Stores LLM enrichment results with confidence evaluation';
COMMENT ON COLUMN enrichments.enrichment_id IS 'Unique identifier for the enrichment record';
COMMENT ON COLUMN enrichments.artifact_id IS 'ID of the artifact being enriched';
COMMENT ON COLUMN enrichments.field IS 'Field being enriched (e.g., roast_level, process_method)';
COMMENT ON COLUMN enrichments.llm_result IS 'JSON result from LLM processing';
COMMENT ON COLUMN enrichments.confidence_score IS 'Confidence score from LLM (0.0-1.0)';
COMMENT ON COLUMN enrichments.applied IS 'Whether the enrichment was applied to the artifact';
