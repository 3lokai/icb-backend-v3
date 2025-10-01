#!/usr/bin/env python3
"""
Grafana Dashboard Importer for G.1 Monitoring

This script imports the G.1 dashboards to your Grafana Cloud instance.
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GrafanaDashboardImporter:
    """Import G.1 dashboards to Grafana Cloud."""
    
    def __init__(self):
        self.grafana_url = os.getenv("GRAFANA_CLOUD_URL")
        self.api_key = os.getenv("GRAFANA_CLOUD_API_KEY")
        
        if not self.grafana_url or not self.api_key:
            raise ValueError("GRAFANA_CLOUD_URL and GRAFANA_CLOUD_API_KEY must be set in .env")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def test_connection(self):
        """Test connection to Grafana Cloud."""
        try:
            response = requests.get(
                f"{self.grafana_url}/api/health",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                print("SUCCESS: Connected to Grafana Cloud successfully!")
                return True
            else:
                print(f"ERROR: Failed to connect to Grafana Cloud: {response.status_code}")
                return False
        except Exception as e:
            print(f"ERROR: Connection error: {e}")
            return False
    
    def create_pipeline_overview_dashboard(self):
        """Create the pipeline overview dashboard."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "ICB-Backend Pipeline Overview",
                "tags": ["icb-backend", "pipeline", "monitoring"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "Pipeline Health Score",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": "icb_pipeline_health_score",
                                "refId": "A",
                                "legendFormat": "Health Score"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 50},
                                        {"color": "green", "value": 80}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": 2,
                        "title": "Fetch Operations Rate",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 6, "y": 0},
                        "targets": [
                            {
                                "expr": "rate(icb_fetch_operations_total[5m])",
                                "refId": "A",
                                "legendFormat": "{{source}} - {{status}}"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Artifact Count",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                        "targets": [
                            {
                                "expr": "icb_artifacts_total",
                                "refId": "A",
                                "legendFormat": "Total Artifacts"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "Review Rate",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                        "targets": [
                            {
                                "expr": "icb_review_rate_percent",
                                "refId": "A",
                                "legendFormat": "Review Rate %"
                            }
                        ]
                    },
                    {
                        "id": 5,
                        "title": "Database Queries",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                        "targets": [
                            {
                                "expr": "rate(icb_database_queries_total[5m])",
                                "refId": "A",
                                "legendFormat": "{{query_type}} - {{success}}"
                            }
                        ]
                    }
                ],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s"
            },
            "overwrite": True
        }
        
        return self._import_dashboard(dashboard, "Pipeline Overview")
    
    def create_database_health_dashboard(self):
        """Create the database health dashboard."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "ICB-Backend Database Health",
                "tags": ["icb-backend", "database", "health"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "Database Health Score",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": "icb_database_health_score",
                                "refId": "A",
                                "legendFormat": "Health Score"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 50},
                                        {"color": "green", "value": 80}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": 2,
                        "title": "Query Performance",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 6, "y": 0},
                        "targets": [
                            {
                                "expr": "rate(icb_database_queries_total[5m])",
                                "refId": "A",
                                "legendFormat": "{{query_type}}"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Connection Pool",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                        "targets": [
                            {
                                "expr": "icb_database_connections_active",
                                "refId": "A",
                                "legendFormat": "Active Connections"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "Table Sizes",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                        "targets": [
                            {
                                "expr": "icb_table_size_bytes",
                                "refId": "A",
                                "legendFormat": "{{table_name}}"
                            }
                        ]
                    },
                    {
                        "id": 5,
                        "title": "Query Duration",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.95, rate(icb_database_query_duration_seconds_bucket[5m]))",
                                "refId": "A",
                                "legendFormat": "95th percentile"
                            }
                        ]
                    }
                ],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s"
            },
            "overwrite": True
        }
        
        return self._import_dashboard(dashboard, "Database Health")
    
    def create_roaster_monitoring_dashboard(self):
        """Create the roaster-specific monitoring dashboard."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "ICB-Backend Roaster Monitoring",
                "tags": ["icb-backend", "roaster", "monitoring"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "Roaster Performance",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": "rate(icb_roaster_fetch_operations_total[5m])",
                                "refId": "A",
                                "legendFormat": "{{roaster_name}}"
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "title": "Price Updates",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                        "targets": [
                            {
                                "expr": "rate(icb_price_updates_total[5m])",
                                "refId": "A",
                                "legendFormat": "{{roaster_name}}"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Data Quality Score",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 8},
                        "targets": [
                            {
                                "expr": "icb_data_quality_score",
                                "refId": "A",
                                "legendFormat": "Quality Score"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "Error Rate by Roaster",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 6, "y": 8},
                        "targets": [
                            {
                                "expr": "rate(icb_roaster_errors_total[5m])",
                                "refId": "A",
                                "legendFormat": "{{roaster_name}} - {{error_type}}"
                            }
                        ]
                    }
                ],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s"
            },
            "overwrite": True
        }
        
        return self._import_dashboard(dashboard, "Roaster Monitoring")
    
    def _import_dashboard(self, dashboard, name):
        """Import a dashboard to Grafana."""
        try:
            response = requests.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=dashboard,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"SUCCESS: {name} dashboard imported successfully!")
                print(f"   Dashboard URL: {self.grafana_url}/d/{result['uid']}")
                return True
            else:
                print(f"ERROR: Failed to import {name} dashboard: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Error importing {name} dashboard: {e}")
            return False
    
    def import_all_dashboards(self):
        """Import all G.1 dashboards."""
        print("Starting Grafana Dashboard Import")
        print("=" * 50)
        
        # Test connection first
        if not self.test_connection():
            return False
        
        # Import dashboards
        dashboards = [
            self.create_pipeline_overview_dashboard,
            self.create_database_health_dashboard,
            self.create_roaster_monitoring_dashboard
        ]
        
        success_count = 0
        for dashboard_func in dashboards:
            if dashboard_func():
                success_count += 1
        
        print("\n" + "=" * 50)
        print(f"Dashboard import completed!")
        print(f"SUCCESS: Successfully imported: {success_count}/{len(dashboards)} dashboards")
        
        if success_count == len(dashboards):
            print("\nNext steps:")
            print("1. Go to your Grafana Cloud dashboard")
            print("2. Check that data is flowing from your icb-backend")
            print("3. Configure alerting rules as needed")
            print("4. Customize dashboards for your specific needs")
        
        return success_count == len(dashboards)

def main():
    """Main function to import dashboards."""
    try:
        importer = GrafanaDashboardImporter()
        importer.import_all_dashboards()
    except Exception as e:
            print(f"ERROR: Failed to initialize dashboard importer: {e}")
        print("\nMake sure your .env file has:")
        print("   - GRAFANA_CLOUD_URL")
        print("   - GRAFANA_CLOUD_API_KEY")

if __name__ == "__main__":
    main()
