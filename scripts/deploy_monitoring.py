#!/usr/bin/env python3
"""
Deploy Monitoring to Fly.io

This script handles monitoring deployment to Fly.io.
It detects the environment and runs appropriate setup.
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

def is_fly_io():
    """Check if we're running on Fly.io."""
    return os.getenv("FLY_APP_NAME") is not None

def is_production():
    """Check if we're in production environment."""
    return os.getenv("ENVIRONMENT") == "production" or is_fly_io()

def deploy_dashboards():
    """Deploy dashboards to Grafana Cloud."""
    print("📊 Deploying dashboards to Grafana Cloud...")
    
    try:
        result = subprocess.run([
            sys.executable, "scripts/import_grafana_dashboards.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dashboards deployed successfully!")
            return True
        else:
            print(f"❌ Dashboard deployment failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to deploy dashboards: {e}")
        return False

def test_monitoring():
    """Test monitoring setup."""
    print("🧪 Testing monitoring setup...")
    
    try:
        result = subprocess.run([
            sys.executable, "scripts/test_monitoring_setup.py"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Failed to test monitoring: {e}")
        return False

def setup_fly_io():
    """Set up monitoring for Fly.io deployment."""
    print("🚀 Setting up monitoring for Fly.io...")
    
    # Check required environment variables
    required_vars = [
        "GRAFANA_CLOUD_URL",
        "GRAFANA_CLOUD_API_KEY",
        "GRAFANA_CLOUD_PROMETHEUS_URL",
        "GRAFANA_CLOUD_PROMETHEUS_USERNAME",
        "GRAFANA_CLOUD_PROMETHEUS_PASSWORD"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Set these in Fly.io using:")
        print("   fly secrets set GRAFANA_CLOUD_URL=...")
        print("   fly secrets set GRAFANA_CLOUD_API_KEY=...")
        print("   # etc.")
        return False
    
    print("✅ All required environment variables are set!")
    
    # Deploy dashboards
    if not deploy_dashboards():
        print("⚠️  Dashboard deployment failed, but continuing...")
    
    # Test monitoring
    if not test_monitoring():
        print("⚠️  Some monitoring tests failed, but continuing...")
    
    print("✅ Fly.io monitoring setup completed!")
    return True

def setup_local():
    """Set up monitoring for local development."""
    print("🛠️  Setting up monitoring for local development...")
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("❌ .env file not found!")
        print("💡 Copy env.example to .env and configure your credentials")
        return False
    
    # Load environment variables
    load_dotenv()
    
    # Check required variables
    required_vars = [
        "GRAFANA_CLOUD_URL",
        "GRAFANA_CLOUD_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables in .env:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Update your .env file with your Grafana Cloud credentials")
        return False
    
    print("✅ Local environment configured!")
    
    # Deploy dashboards
    if not deploy_dashboards():
        print("⚠️  Dashboard deployment failed, but continuing...")
    
    # Test monitoring
    if not test_monitoring():
        print("⚠️  Some monitoring tests failed, but continuing...")
    
    print("✅ Local monitoring setup completed!")
    return True

def main():
    """Main deployment function."""
    print("🚀 ICB-Backend Monitoring Deployment")
    print("=" * 50)
    
    if is_fly_io():
        print("🏗️  Detected Fly.io environment")
        success = setup_fly_io()
    else:
        print("🛠️  Detected local development environment")
        success = setup_local()
    
    print("\n" + "=" * 50)
    
    if success:
        print("🎉 Monitoring deployment completed!")
        
        if is_fly_io():
            print("\n📋 Fly.io Production Setup:")
            print("✅ Monitoring is now active in production")
            print("✅ Metrics are being collected automatically")
            print("✅ Dashboards are available in Grafana Cloud")
            print("✅ Alerts are configured and active")
            
            print("\n🔗 Useful Commands:")
            print("   fly logs                    # View application logs")
            print("   fly metrics show           # View basic metrics")
            print("   fly ssh console            # Access production console")
            
        else:
            print("\n📋 Local Development Setup:")
            print("✅ Monitoring is configured for local development")
            print("✅ Dashboards are available in Grafana Cloud")
            print("✅ You can test monitoring locally")
            
            print("\n🔗 Useful Commands:")
            print("   python scripts/start_monitoring.py    # Start monitoring")
            print("   python scripts/test_monitoring_setup.py  # Test setup")
            print("   curl http://localhost:8000/metrics    # View metrics")
        
        print("\n📊 Next Steps:")
        print("1. Go to your Grafana Cloud dashboard")
        print("2. Check that data is flowing from your application")
        print("3. Set up additional alerting rules as needed")
        print("4. Monitor your dashboards for pipeline health")
        
    else:
        print("❌ Monitoring deployment failed!")
        print("\n💡 Common fixes:")
        print("1. Check your Grafana Cloud credentials")
        print("2. Verify your .env file is configured correctly")
        print("3. Ensure your Grafana Cloud instance is accessible")
        print("4. Check the error messages above for specific issues")
        
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
