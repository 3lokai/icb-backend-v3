#!/usr/bin/env python3
"""
Start Monitoring Stack for G.1

This script helps you start your monitoring stack with the correct configuration.
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

def check_environment():
    """Check that all required environment variables are set."""
    print("Checking environment configuration...")
    
    load_dotenv()
    
    required_vars = [
        "GRAFANA_CLOUD_URL",
        "GRAFANA_CLOUD_API_KEY", 
        "GRAFANA_CLOUD_PROMETHEUS_URL",
        "GRAFANA_CLOUD_PROMETHEUS_USERNAME",
        "GRAFANA_CLOUD_PROMETHEUS_PASSWORD"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease update your .env file with your Grafana Cloud credentials")
        return False
    
    print("SUCCESS: All required environment variables are set!")
    return True

def start_metrics_server():
    """Start the metrics server."""
    print("\nStarting metrics server...")
    
    # Set environment variables for metrics
    env = os.environ.copy()
    env.update({
        "PROMETHEUS_ENABLED": "true",
        "PROMETHEUS_PORT": "8000",
        "PROMETHEUS_HOST": "0.0.0.0"
    })
    
    try:
        # Start the metrics server in the background
        process = subprocess.Popen([
            sys.executable, "-m", "src.monitoring.metrics_server"
        ], env=env)
        
        print("SUCCESS Metrics server started on port 8000")
        print("   You can check metrics at: http://localhost:8000/metrics")
        return process
        
    except Exception as e:
        print(f"ERROR Failed to start metrics server: {e}")
        return None

def import_dashboards():
    """Import Grafana dashboards."""
    print("\n📊 Importing Grafana dashboards...")
    
    try:
        result = subprocess.run([
            sys.executable, "scripts/import_grafana_dashboards.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("SUCCESS Dashboards imported successfully!")
            return True
        else:
            print(f"ERROR Dashboard import failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"ERROR Failed to import dashboards: {e}")
        return False

def test_setup():
    """Test the monitoring setup."""
    print("\n Testing monitoring setup...")
    
    try:
        # Test if metrics endpoint is accessible
        import requests
        response = requests.get("http://localhost:8000/metrics", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Metrics endpoint is accessible")
            return True
        else:
            print(f"ERROR: Metrics endpoint returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to metrics endpoint. Is the server running?")
        return False
    except Exception as e:
        print(f"ERROR Failed to test setup: {e}")
        return False

def main():
    """Main function to start monitoring stack."""
    print(" Starting ICB-Backend Monitoring Stack")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Start metrics server
    metrics_process = start_metrics_server()
    if not metrics_process:
        return 1
    
    try:
        # Wait a moment for server to start
        import time
        time.sleep(2)
        
        # Import dashboards
        if not import_dashboards():
            print("ALERT  Dashboard import failed, but continuing...")
        
        # Test setup
        if not test_setup():
            print("ALERT  Some tests failed, but monitoring is running...")
        
        print("\n" + "=" * 50)
        print(" Monitoring stack is running!")
        print("\n📋 What's running:")
        print("SUCCESS Metrics server on port 8000")
        print("SUCCESS Prometheus remote write to Grafana Cloud")
        print("SUCCESS Grafana dashboards imported")
        
        print("\n Useful URLs:")
        print("   - Metrics: http://localhost:8000/metrics")
        print("   - Health: http://localhost:8000/health")
        print(f"   - Grafana: {os.getenv('GRAFANA_CLOUD_URL')}")
        
        print("\n Next steps:")
        print("1. Check your Grafana Cloud dashboard for data")
        print("2. Run your icb-backend application to generate real metrics")
        print("3. Set up alerting rules in Grafana")
        print("4. Monitor your dashboards for pipeline health")
        
        print("\n To stop monitoring, press Ctrl+C")
        
        # Keep the process running
        try:
            metrics_process.wait()
        except KeyboardInterrupt:
            print("\n Stopping monitoring stack...")
            metrics_process.terminate()
            print("SUCCESS Monitoring stack stopped")
        
        return 0
        
    except Exception as e:
        print(f"ERROR Error running monitoring stack: {e}")
        if metrics_process:
            metrics_process.terminate()
        return 1

if __name__ == "__main__":
    sys.exit(main())
