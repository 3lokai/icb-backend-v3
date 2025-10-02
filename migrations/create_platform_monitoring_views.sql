-- Platform Monitoring Views
-- Created for Story A.6: Platform-Based Fetcher Selection with Automatic Fallback
-- These views provide monitoring and analytics for platform distribution and usage

-- View 1: Platform Distribution Summary
-- Shows the distribution of roasters across different platforms
CREATE OR REPLACE VIEW platform_distribution AS
SELECT 
    platform,
    COUNT(*) as roaster_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
    COUNT(*) FILTER (WHERE is_active = true) as active_roasters,
    COUNT(*) FILTER (WHERE is_active = false) as inactive_roasters,
    COUNT(*) FILTER (WHERE use_firecrawl_fallback = true) as firecrawl_enabled,
    AVG(firecrawl_budget_limit) as avg_firecrawl_budget,
    MIN(created_at) as first_roaster_created,
    MAX(updated_at) as last_roaster_updated
FROM roasters 
WHERE platform IS NOT NULL
GROUP BY platform
ORDER BY roaster_count DESC;

-- View 2: Platform Usage Statistics
-- Shows detailed usage statistics for each platform
CREATE OR REPLACE VIEW platform_usage_stats AS
SELECT 
    r.platform,
    COUNT(DISTINCT r.id) as total_roasters,
    COUNT(DISTINCT c.id) as total_coffees,
    COUNT(DISTINCT v.id) as total_variants,
    COUNT(DISTINCT p.id) as total_prices,
    ROUND(AVG(c.rating_avg), 2) as avg_coffee_rating,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'active') as active_coffees,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'inactive') as inactive_coffees,
    COUNT(DISTINCT v.id) FILTER (WHERE v.in_stock = true) as in_stock_variants,
    COUNT(DISTINCT v.id) FILTER (WHERE v.in_stock = false) as out_of_stock_variants,
    ROUND(AVG(p.price), 2) as avg_price,
    MIN(p.scraped_at) as earliest_price,
    MAX(p.scraped_at) as latest_price
FROM roasters r
LEFT JOIN coffees c ON r.id = c.roaster_id
LEFT JOIN variants v ON c.id = v.coffee_id
LEFT JOIN prices p ON v.id = p.variant_id
WHERE r.platform IS NOT NULL
GROUP BY r.platform
ORDER BY total_roasters DESC;

-- View 3: Firecrawl Usage Tracking
-- Shows Firecrawl usage and budget consumption
CREATE OR REPLACE VIEW firecrawl_usage_tracking AS
SELECT 
    r.platform,
    COUNT(*) as total_roasters,
    COUNT(*) FILTER (WHERE r.use_firecrawl_fallback = true) as firecrawl_enabled_count,
    ROUND(COUNT(*) FILTER (WHERE r.use_firecrawl_fallback = true) * 100.0 / COUNT(*), 2) as firecrawl_enabled_percentage,
    AVG(r.firecrawl_budget_limit) as avg_budget_limit,
    MIN(r.firecrawl_budget_limit) as min_budget_limit,
    MAX(r.firecrawl_budget_limit) as max_budget_limit,
    SUM(r.firecrawl_budget_limit) as total_budget_allocated,
    COUNT(*) FILTER (WHERE r.is_active = true AND r.use_firecrawl_fallback = true) as active_firecrawl_roasters
FROM roasters r
WHERE r.platform IS NOT NULL
GROUP BY r.platform
ORDER BY total_roasters DESC;

-- View 4: Platform Performance Metrics
-- Shows performance metrics for each platform
CREATE OR REPLACE VIEW platform_performance_metrics AS
SELECT 
    r.platform,
    COUNT(DISTINCT r.id) as roaster_count,
    COUNT(DISTINCT c.id) as coffee_count,
    ROUND(COUNT(DISTINCT c.id)::numeric / COUNT(DISTINCT r.id), 2) as avg_coffees_per_roaster,
    COUNT(DISTINCT v.id) as variant_count,
    ROUND(COUNT(DISTINCT v.id)::numeric / COUNT(DISTINCT c.id), 2) as avg_variants_per_coffee,
    COUNT(DISTINCT p.id) as price_count,
    ROUND(COUNT(DISTINCT p.id)::numeric / COUNT(DISTINCT v.id), 2) as avg_prices_per_variant,
    ROUND(AVG(c.rating_avg), 2) as avg_rating,
    COUNT(DISTINCT c.id) FILTER (WHERE c.rating_count > 0) as rated_coffees,
    ROUND(COUNT(DISTINCT c.id) FILTER (WHERE c.rating_count > 0) * 100.0 / COUNT(DISTINCT c.id), 2) as rating_coverage_percentage
FROM roasters r
LEFT JOIN coffees c ON r.id = c.roaster_id
LEFT JOIN variants v ON c.id = v.coffee_id
LEFT JOIN prices p ON v.id = p.variant_id
WHERE r.platform IS NOT NULL
GROUP BY r.platform
ORDER BY roaster_count DESC;

-- View 5: Recent Platform Activity
-- Shows recent activity and changes for each platform
CREATE OR REPLACE VIEW recent_platform_activity AS
SELECT 
    r.platform,
    COUNT(*) as total_roasters,
    COUNT(*) FILTER (WHERE r.updated_at > NOW() - INTERVAL '7 days') as updated_last_7_days,
    COUNT(*) FILTER (WHERE r.updated_at > NOW() - INTERVAL '30 days') as updated_last_30_days,
    COUNT(*) FILTER (WHERE r.created_at > NOW() - INTERVAL '7 days') as created_last_7_days,
    COUNT(*) FILTER (WHERE r.created_at > NOW() - INTERVAL '30 days') as created_last_30_days,
    MAX(r.updated_at) as last_roaster_update,
    MAX(r.created_at) as last_roaster_creation,
    COUNT(*) FILTER (WHERE r.is_active = true) as currently_active,
    COUNT(*) FILTER (WHERE r.is_active = false) as currently_inactive
FROM roasters r
WHERE r.platform IS NOT NULL
GROUP BY r.platform
ORDER BY total_roasters DESC;

-- View 6: Platform Health Dashboard
-- Provides a comprehensive health dashboard for platform monitoring
CREATE OR REPLACE VIEW platform_health_dashboard AS
SELECT 
    r.platform,
    COUNT(*) as total_roasters,
    COUNT(*) FILTER (WHERE r.is_active = true) as active_roasters,
    COUNT(*) FILTER (WHERE r.is_active = false) as inactive_roasters,
    ROUND(COUNT(*) FILTER (WHERE r.is_active = true) * 100.0 / COUNT(*), 2) as active_percentage,
    COUNT(*) FILTER (WHERE r.use_firecrawl_fallback = true) as firecrawl_enabled,
    ROUND(COUNT(*) FILTER (WHERE r.use_firecrawl_fallback = true) * 100.0 / COUNT(*), 2) as firecrawl_percentage,
    AVG(r.firecrawl_budget_limit) as avg_budget_limit,
    COUNT(DISTINCT c.id) as total_coffees,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'active') as active_coffees,
    ROUND(AVG(c.rating_avg), 2) as avg_rating,
    COUNT(DISTINCT c.id) FILTER (WHERE c.rating_count > 0) as rated_coffees,
    MAX(r.updated_at) as last_activity,
    CASE 
        WHEN MAX(r.updated_at) > NOW() - INTERVAL '7 days' THEN 'Recent'
        WHEN MAX(r.updated_at) > NOW() - INTERVAL '30 days' THEN 'Moderate'
        ELSE 'Stale'
    END as activity_status
FROM roasters r
LEFT JOIN coffees c ON r.id = c.roaster_id
WHERE r.platform IS NOT NULL
GROUP BY r.platform
ORDER BY total_roasters DESC;

-- Grant permissions for the views
GRANT SELECT ON platform_distribution TO authenticated;
GRANT SELECT ON platform_usage_stats TO authenticated;
GRANT SELECT ON firecrawl_usage_tracking TO authenticated;
GRANT SELECT ON platform_performance_metrics TO authenticated;
GRANT SELECT ON recent_platform_activity TO authenticated;
GRANT SELECT ON platform_health_dashboard TO authenticated;

-- Add comments for documentation
COMMENT ON VIEW platform_distribution IS 'Shows the distribution of roasters across different platforms with percentages and activity metrics';
COMMENT ON VIEW platform_usage_stats IS 'Shows detailed usage statistics for each platform including coffee counts, ratings, and pricing';
COMMENT ON VIEW firecrawl_usage_tracking IS 'Tracks Firecrawl usage and budget consumption across platforms';
COMMENT ON VIEW platform_performance_metrics IS 'Shows performance metrics for each platform including averages and coverage';
COMMENT ON VIEW recent_platform_activity IS 'Shows recent activity and changes for each platform over different time periods';
COMMENT ON VIEW platform_health_dashboard IS 'Comprehensive health dashboard for platform monitoring with activity status';
