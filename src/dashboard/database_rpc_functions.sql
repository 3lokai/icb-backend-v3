-- Database RPC functions for dashboard business metrics
-- These functions should be created in Supabase to support the dashboard

-- Get price trend for last 4 weeks (weekly cadence per PRD)
CREATE OR REPLACE FUNCTION get_price_trend_4w()
RETURNS TABLE (
    date DATE,
    price_updates BIGINT,
    avg_price NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        DATE(p.scraped_at) as date,
        COUNT(*) as price_updates,
        AVG(p.price) as avg_price
    FROM prices p
    WHERE p.scraped_at > NOW() - INTERVAL '28 days'  -- 4 weeks to show weekly cadence
    GROUP BY DATE(p.scraped_at)
    ORDER BY date DESC;
END;
$$ LANGUAGE plpgsql;

-- Get roaster performance metrics for last 30 days (weekly + monthly runs)
CREATE OR REPLACE FUNCTION get_roaster_performance_30d()
RETURNS TABLE (
    roaster_id UUID,
    roaster_name TEXT,
    total_runs BIGINT,
    successful_runs BIGINT,
    success_rate NUMERIC,
    avg_duration_seconds NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id as roaster_id,
        r.name as roaster_name,
        COUNT(sr.id) as total_runs,
        COUNT(CASE WHEN sr.status = 'ok' THEN 1 END) as successful_runs,
        CASE 
            WHEN COUNT(sr.id) > 0 THEN 
                ROUND((COUNT(CASE WHEN sr.status = 'ok' THEN 1 END)::NUMERIC / COUNT(sr.id)) * 100, 2)
            ELSE 0 
        END as success_rate,
        AVG(EXTRACT(EPOCH FROM (sr.finished_at - sr.started_at))) as avg_duration_seconds
    FROM roasters r
    LEFT JOIN product_sources ps ON r.id = ps.roaster_id
    LEFT JOIN scrape_runs sr ON ps.id = sr.source_id
    WHERE sr.started_at > NOW() - INTERVAL '30 days'  -- 30 days to capture weekly + monthly runs
    GROUP BY r.id, r.name
    ORDER BY success_rate DESC;
END;
$$ LANGUAGE plpgsql;

-- Get run statistics for last 30 days (weekly + monthly runs)
CREATE OR REPLACE FUNCTION get_run_statistics_30d()
RETURNS TABLE (
    date DATE,
    total_runs BIGINT,
    successful_runs BIGINT,
    failed_runs BIGINT,
    avg_duration_minutes NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        DATE(sr.started_at) as date,
        COUNT(*) as total_runs,
        COUNT(CASE WHEN sr.status = 'ok' THEN 1 END) as successful_runs,
        COUNT(CASE WHEN sr.status != 'ok' THEN 1 END) as failed_runs,
        ROUND(AVG(EXTRACT(EPOCH FROM (sr.finished_at - sr.started_at)) / 60), 2) as avg_duration_minutes
    FROM scrape_runs sr
    WHERE sr.started_at > NOW() - INTERVAL '30 days'  -- 30 days to capture weekly + monthly runs
    GROUP BY DATE(sr.started_at)
    ORDER BY date DESC;
END;
$$ LANGUAGE plpgsql;
