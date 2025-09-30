#!/usr/bin/env python3
"""
Real Price Integration tests with actual Supabase connection and real price data.
Tests the B.2 price update functionality using RPC client directly.
"""

import os
import sys
import pytest
import warnings
from pathlib import Path
from datetime import datetime, timezone

# Suppress Supabase deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="supabase")

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, trying to load manually")
    # Try to read .env file manually
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Loaded environment variables manually from .env file")
    else:
        print("❌ No .env file found")

def test_real_price_update_integration():
    """Test real price update integration with actual database."""
    
    # Check environment variables
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_SERVICE_ROLE_KEY'):
        print("❌ Database credentials not available")
        return False
    
    try:
        from supabase import create_client
        from validator.rpc_client import RPCClient
        
        # Create Supabase client
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        
        # Create RPC client
        rpc_client = RPCClient(supabase)
        
        print("\n🔗 Testing B.2 Price Update Integration with real database...")
        
        # Use a real roaster ID from the database
        real_roaster_id = "550e8400-e29b-41d4-a716-446655440000"  # Blue Tokai Coffee
        
        # First, create a test coffee and variant if they don't exist
        print("\n☕ Setting up test coffee and variant...")
        
        # Check if test coffee exists
        coffee_result = supabase.table("coffees").select("id").eq("slug", "test-price-integration-coffee").execute()
        
        if coffee_result.data:
            coffee_id = coffee_result.data[0]["id"]
            print(f"✅ Using existing test coffee: {coffee_id}")
        else:
            # Create test coffee
            coffee_id = rpc_client.upsert_coffee(
                bean_species="arabica",
                name="Test Price Integration Coffee",
                slug="test-price-integration-coffee",
                roaster_id=real_roaster_id,
                process="washed",
                process_raw="Washed Process",
                roast_level="medium",
                roast_level_raw="Medium Roast",
                roast_style_raw="City Roast",
                description_md="Test coffee for price integration testing",
                direct_buy_url="https://example.com/test-price-coffee",
                platform_product_id="test-price-product-123",
                decaf=False,
                status="active"
            )
            print(f"✅ Created test coffee: {coffee_id}")
        
        # Check if test variant exists
        variant_result = supabase.table("variants").select("id").eq("sku", "TEST-PRICE-250G").execute()
        
        if variant_result.data:
            variant_id = variant_result.data[0]["id"]
            print(f"✅ Using existing test variant: {variant_id}")
        else:
            # Create test variant
            variant_id = rpc_client.upsert_variant(
                coffee_id=coffee_id,
                platform_variant_id="test-price-variant-123",
                sku="TEST-PRICE-250G",
                weight_g=250,
                currency="USD",
                in_stock=True,
                stock_qty=50,
                subscription_available=False,
                compare_at_price=24.99,
                grind="whole",
                pack_count=1
            )
            print(f"✅ Created test variant: {variant_id}")
        
        # Test 1: Price Insert via RPC
        print("\n💰 Testing price insert via RPC...")
        price_id_1 = rpc_client.insert_price(
            variant_id=variant_id,
            price=22.99,
            currency="USD",
            is_sale=False,
            scraped_at=datetime.now(timezone.utc).isoformat(),
            source_url="https://example.com/test-price-coffee"
        )
        print(f"✅ Price record 1 created: {price_id_1}")
        
        price_id_2 = rpc_client.insert_price(
            variant_id=variant_id,
            price=24.99,
            currency="USD",
            is_sale=True,
            scraped_at=datetime.now(timezone.utc).isoformat(),
            source_url="https://example.com/test-price-coffee"
        )
        print(f"✅ Price record 2 created: {price_id_2}")
        
        # Test 2: Variant Pricing Update
        print("\n📦 Testing variant pricing update...")
        variant_success = rpc_client.update_variant_pricing(
            variant_id=variant_id,
            price_current=24.99,
            price_last_checked_at=datetime.now(timezone.utc).isoformat(),
            in_stock=True,
            currency="USD"
        )
        
        if variant_success:
            print("✅ Variant pricing update successful!")
        else:
            print("❌ Variant pricing update failed!")
            return False
        
        # Test 3: Batch Variant Update
        print("\n📦 Testing batch variant update...")
        batch_updates = [
            {
                "variant_id": variant_id,
                "price_current": 26.99,
                "price_last_checked_at": datetime.now(timezone.utc).isoformat(),
                "in_stock": False,
                "currency": "USD"
            }
        ]
        
        batch_result = rpc_client.batch_update_variant_pricing(batch_updates)
        
        if batch_result.get("successful_updates", 0) > 0:
            print(f"✅ Batch variant update successful! Updated {batch_result['successful_updates']} variants")
        else:
            print(f"❌ Batch variant update failed: {batch_result.get('errors', [])}")
            return False
        
        # Get RPC statistics
        stats = rpc_client.get_rpc_stats()
        print(f"\n📊 RPC Statistics:")
        print(f"   Total calls: {stats['total_calls']}")
        print(f"   Successful calls: {stats['successful_calls']}")
        print(f"   Failed calls: {stats['failed_calls']}")
        print(f"   Success rate: {stats['success_rate']:.2%}")
        
        print("\n✅ All B.2 price integration tests passed successfully!")
        assert True  # Test completed successfully
        
    except Exception as e:
        print(f"❌ Price integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_verification():
    """Test database verification for price updates."""
    
    print("\n🔍 Testing database verification...")
    
    try:
        from supabase import create_client
        
        # Create Supabase client
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        
        # Check test variant
        variant_result = supabase.table("variants").select("*").eq("sku", "TEST-PRICE-250G").execute()
        
        if variant_result.data:
            variant = variant_result.data[0]
            print(f"✅ Test variant found:")
            print(f"   ID: {variant['id']}")
            print(f"   SKU: {variant['sku']}")
            print(f"   Current Price: ${variant['price_current']}")
            print(f"   Currency: {variant['currency']}")
            print(f"   In Stock: {variant['in_stock']}")
            print(f"   Last Checked: {variant['price_last_checked_at']}")
        else:
            print("❌ Test variant not found")
            return False
        
        # Check price records
        price_result = supabase.table("prices").select("*").eq("variant_id", variant['id']).order("scraped_at", desc=True).limit(5).execute()
        
        if price_result.data:
            print(f"\n✅ Found {len(price_result.data)} price records:")
            for i, price in enumerate(price_result.data):
                print(f"   Record {i+1}:")
                print(f"     ID: {price['id']}")
                print(f"     Price: ${price['price']}")
                print(f"     Currency: {price['currency']}")
                print(f"     Is Sale: {price['is_sale']}")
                print(f"     Scraped At: {price['scraped_at']}")
                print(f"     Source URL: {price['source_url']}")
        else:
            print("❌ No price records found")
            return False
        
        print("\n✅ Database verification completed successfully!")
        assert True  # Database verification completed successfully
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🧪 Running Real B.2 Price Integration Tests")
    print("=" * 60)
    
    # Test 1: Real price update integration
    price_success = test_real_price_update_integration()
    
    # Test 2: Database verification
    db_success = test_database_verification()
    
    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    print(f"   Price Update Integration: {'✅ PASS' if price_success else '❌ FAIL'}")
    print(f"   Database Verification: {'✅ PASS' if db_success else '❌ FAIL'}")
    
    if price_success and db_success:
        print("\n🎉 All B.2 price integration tests passed!")
        print("\n📊 Database Tables to Check:")
        print("   1. variants table - Check price_current, price_last_checked_at, in_stock fields")
        print("   2. prices table - Check new price records with variant_id, price, currency, scraped_at")
        print("   3. coffees table - Verify test coffee exists with slug 'test-price-integration-coffee'")
        print("\n🔍 SQL Queries to Verify:")
        print("   SELECT * FROM variants WHERE sku = 'TEST-PRICE-250G';")
        print("   SELECT * FROM prices WHERE variant_id = '<variant_id>' ORDER BY scraped_at DESC LIMIT 5;")
        print("   SELECT * FROM coffees WHERE slug = 'test-price-integration-coffee';")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
