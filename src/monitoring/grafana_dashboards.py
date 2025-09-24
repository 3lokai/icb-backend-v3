"""
Grafana dashboard configuration and management.

This module provides comprehensive Grafana dashboard configuration for
pipeline monitoring, including pipeline overview, roaster-specific dashboards,
price monitoring, and database health dashboards.
"""

import json
from typing import Dict, Any, List

from structlog import get_logger

logger = get_logger(__name__)


class GrafanaDashboardConfig:
    """
    Grafana dashboard configuration service.
    
    Provides dashboard configurations for:
    - Pipeline overview with core KPIs
    - Roaster-specific dashboards
    - Price monitoring dashboards
    - Database health dashboards
    - Alerting rules and thresholds
    """
    
    def __init__(self, grafana_api_url: str = None, api_key: str = None):
        """Initialize Grafana dashboard configuration."""
        self.grafana_api_url = grafana_api_url
        self.api_key = api_key
        self.dashboards = {}
    
    def create_pipeline_overview_dashboard(self) -> Dict[str, Any]:
        """Create pipeline overview dashboard with core KPIs."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "Coffee Scraper Pipeline Overview",
                "tags": ["coffee", "scraper", "pipeline"],
                "timezone": "browser",
                "panels": [
                    # Run Status Panel
                    {
                        "id": 1,
                        "title": "Run Status",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(rate(scrape_runs_total[5m]))",
                                "legendFormat": "Runs/min"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 0.1},
                                        {"color": "green", "value": 0.5}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
                    },
                    
                    # Success Rate Panel
                    {
                        "id": 2,
                        "title": "Success Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": (
                                    "sum(rate(scrape_runs_total{status=\"ok\"}[5m])) / "
                                    "sum(rate(scrape_runs_total[5m])) * 100"
                                ),
                                "legendFormat": "Success Rate %"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 80},
                                        {"color": "green", "value": 95}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
                    },
                    
                    # Artifact Quality Panel
                    {
                        "id": 3,
                        "title": "Artifact Quality",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": (
                                    "sum(rate(artifacts_total{status=\"valid\"}[5m])) / "
                                    "sum(rate(artifacts_total[5m])) * 100"
                                ),
                                "legendFormat": "Validation Rate %"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 85},
                                        {"color": "green", "value": 95}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
                    },
                    
                    # Price Updates Panel
                    {
                        "id": 4,
                        "title": "Price Updates",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(rate(price_deltas_total[5m]))",
                                "legendFormat": "Price Changes/min"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 1},
                                        {"color": "green", "value": 5}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
                    },
                    
                    # Fetch Latency Graph
                    {
                        "id": 5,
                        "title": "Fetch Latency",
                        "type": "timeseries",
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.95, rate(fetch_latency_seconds_bucket[5m]))",
                                "legendFormat": "95th percentile"
                            },
                            {
                                "expr": "histogram_quantile(0.50, rate(fetch_latency_seconds_bucket[5m]))",
                                "legendFormat": "50th percentile"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "s",
                                "color": {"mode": "palette-classic"}
                            }
                        },
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                    },
                    
                    # Error Rate Graph
                    {
                        "id": 6,
                        "title": "Error Rate",
                        "type": "timeseries",
                        "targets": [
                            {
                                "expr": "sum(rate(fetch_errors_total[5m])) by (error_type)",
                                "legendFormat": "{{error_type}}"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "reqps",
                                "color": {"mode": "palette-classic"}
                            }
                        },
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                    },
                    
                    # Database Health Panel
                    {
                        "id": 7,
                        "title": "Database Health",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(database_connections_active)",
                                "legendFormat": "Active Connections"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 5},
                                        {"color": "green", "value": 10}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 16}
                    },
                    
                    # System Resources Panel
                    {
                        "id": 8,
                        "title": "System Resources",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(system_resources_usage{resource_type=\"memory\"})",
                                "legendFormat": "Memory Usage"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "bytes",
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 1000000000},
                                        {"color": "red", "value": 2000000000}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 16}
                    },
                    
                    # Pipeline Health Score
                    {
                        "id": 9,
                        "title": "Pipeline Health Score",
                        "type": "gauge",
                        "targets": [
                            {
                                "expr": "avg(pipeline_health_score)",
                                "legendFormat": "Health Score"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "short",
                                "min": 0,
                                "max": 100,
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 70},
                                        {"color": "green", "value": 90}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 16}
                    },
                    
                    # Review Rate Panel
                    {
                        "id": 10,
                        "title": "Review Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "avg(review_rate_percent)",
                                "legendFormat": "Review Rate %"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 50},
                                        {"color": "green", "value": 80}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 16}
                    }
                ],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s"
            }
        }
        
        return dashboard
    
    def create_roaster_specific_dashboard(self, roaster_id: str) -> Dict[str, Any]:
        """Create roaster-specific dashboard."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": f"Coffee Scraper - {roaster_id}",
                "tags": ["coffee", "scraper", "roaster", roaster_id],
                "timezone": "browser",
                "panels": [
                    # Roaster Performance Panel
                    {
                        "id": 1,
                        "title": f"{roaster_id} Performance",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": f"sum(rate(fetch_latency_seconds{{roaster_id=\"{roaster_id}\"}}[5m]))",
                                "legendFormat": "Fetch Rate"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
                    },
                    
                    # Roaster Success Rate
                    {
                        "id": 2,
                        "title": f"{roaster_id} Success Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": (
                                    f"sum(rate(artifacts_total{{roaster_id=\"{roaster_id}\", "
                                    f"status=\"valid\"}}[5m])) / "
                                    f"sum(rate(artifacts_total{{roaster_id=\"{roaster_id}\"}}[5m])) * 100"
                                ),
                                "legendFormat": "Success Rate %"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 80},
                                        {"color": "green", "value": 95}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
                    },
                    
                    # Roaster Price Changes
                    {
                        "id": 3,
                        "title": f"{roaster_id} Price Changes",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": f"sum(rate(price_deltas_total{{roaster_id=\"{roaster_id}\"}}[5m]))",
                                "legendFormat": "Price Changes/min"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
                    },
                    
                    # Roaster Error Rate
                    {
                        "id": 4,
                        "title": f"{roaster_id} Error Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": f"sum(rate(fetch_errors_total{{roaster_id=\"{roaster_id}\"}}[5m]))",
                                "legendFormat": "Errors/min"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 0.1},
                                        {"color": "red", "value": 1}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
                    }
                ],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s"
            }
        }
        
        return dashboard
    
    def create_price_monitoring_dashboard(self) -> Dict[str, Any]:
        """Create price monitoring dashboard with B.1-B.3 metrics."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "Coffee Scraper Price Monitoring",
                "tags": ["coffee", "scraper", "price", "monitoring"],
                "timezone": "browser",
                "panels": [
                    # Price Changes Over Time
                    {
                        "id": 1,
                        "title": "Price Changes Over Time",
                        "type": "timeseries",
                        "targets": [
                            {
                                "expr": "sum(rate(price_deltas_total[5m])) by (roaster_id)",
                                "legendFormat": "{{roaster_id}}"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "reqps",
                                "color": {"mode": "palette-classic"}
                            }
                        },
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                    },
                    
                    # Price Spike Alerts
                    {
                        "id": 2,
                        "title": "Price Spike Alerts",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(rate(price_spike_alerts_total[5m]))",
                                "legendFormat": "Spike Alerts/min"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 0.1},
                                        {"color": "red", "value": 1}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
                    },
                    
                    # Price Job Performance
                    {
                        "id": 3,
                        "title": "Price Job Performance",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(rate(price_job_success_total[5m]))",
                                "legendFormat": "Successful Jobs/min"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
                    }
                ],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s"
            }
        }
        
        return dashboard
    
    def create_database_health_dashboard(self) -> Dict[str, Any]:
        """Create database health dashboard."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "Coffee Scraper Database Health",
                "tags": ["coffee", "scraper", "database", "health"],
                "timezone": "browser",
                "panels": [
                    # Database Connections
                    {
                        "id": 1,
                        "title": "Database Connections",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(database_connections_active)",
                                "legendFormat": "Active Connections"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 5},
                                        {"color": "green", "value": 10}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
                    },
                    
                    # Query Performance
                    {
                        "id": 2,
                        "title": "Query Performance",
                        "type": "timeseries",
                        "targets": [
                            {
                                "expr": "sum(rate(database_queries_total[5m])) by (query_type)",
                                "legendFormat": "{{query_type}}"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "reqps",
                                "color": {"mode": "palette-classic"}
                            }
                        },
                        "gridPos": {"h": 8, "w": 12, "x": 6, "y": 0}
                    },
                    
                    # Rate Limiting
                    {
                        "id": 3,
                        "title": "Rate Limiting",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(rate(rate_limit_errors_total[5m]))",
                                "legendFormat": "Rate Limit Errors/min"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 0.1},
                                        {"color": "red", "value": 1}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
                    }
                ],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s"
            }
        }
        
        return dashboard
    
    def create_alerting_rules(self) -> List[Dict[str, Any]]:
        """Create alerting rules for critical thresholds."""
        rules = [
            {
                "alert": "HighErrorRate",
                "expr": "sum(rate(fetch_errors_total[5m])) > 0.5",
                "for": "2m",
                "labels": {
                    "severity": "warning",
                    "service": "coffee-scraper"
                },
                "annotations": {
                    "summary": "High error rate detected in coffee scraper",
                    "description": "Error rate is {{ $value }} errors per minute"
                }
            },
            {
                "alert": "LowSuccessRate",
                "expr": "sum(rate(scrape_runs_total{status=\"ok\"}[5m])) / sum(rate(scrape_runs_total[5m])) * 100 < 80",
                "for": "5m",
                "labels": {
                    "severity": "critical",
                    "service": "coffee-scraper"
                },
                "annotations": {
                    "summary": "Low success rate in coffee scraper",
                    "description": "Success rate is {{ $value }}%"
                }
            },
            {
                "alert": "HighLatency",
                "expr": "histogram_quantile(0.95, rate(fetch_latency_seconds_bucket[5m])) > 60",
                "for": "3m",
                "labels": {
                    "severity": "warning",
                    "service": "coffee-scraper"
                },
                "annotations": {
                    "summary": "High fetch latency detected",
                    "description": "95th percentile latency is {{ $value }} seconds"
                }
            },
            {
                "alert": "DatabaseConnectionIssues",
                "expr": "sum(database_connections_active) < 1",
                "for": "1m",
                "labels": {
                    "severity": "critical",
                    "service": "coffee-scraper"
                },
                "annotations": {
                    "summary": "Database connection issues",
                    "description": "Active connections: {{ $value }}"
                }
            },
            {
                "alert": "PriceSpikeDetected",
                "expr": "sum(rate(price_spike_alerts_total[5m])) > 0",
                "for": "0m",
                "labels": {
                    "severity": "info",
                    "service": "coffee-scraper"
                },
                "annotations": {
                    "summary": "Price spike detected",
                    "description": "Price spike alerts: {{ $value }} per minute"
                }
            }
        ]
        
        return rules
    
    def get_all_dashboards(self) -> Dict[str, Any]:
        """Get all dashboard configurations."""
        return {
            "pipeline_overview": self.create_pipeline_overview_dashboard(),
            "roaster_specific": self.create_roaster_specific_dashboard("sample_roaster"),
            "price_monitoring": self.create_price_monitoring_dashboard(),
            "database_health": self.create_database_health_dashboard(),
            "alerting_rules": self.create_alerting_rules()
        }
    
    def export_dashboard_config(self, dashboard_name: str) -> str:
        """Export dashboard configuration as JSON."""
        dashboards = self.get_all_dashboards()
        
        if dashboard_name in dashboards:
            return json.dumps(dashboards[dashboard_name], indent=2)
        else:
            return json.dumps({"error": f"Dashboard '{dashboard_name}' not found"}, indent=2)
    
    def export_all_configs(self) -> str:
        """Export all dashboard configurations as JSON."""
        return json.dumps(self.get_all_dashboards(), indent=2)
