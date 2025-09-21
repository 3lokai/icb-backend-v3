#!/usr/bin/env python3
"""
Sample Data Collection Script

This script helps you collect sample data from Shopify and WooCommerce stores
for validation and testing purposes.
"""

import json
import requests
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin


class SampleCollector:
    """Collects sample data from e-commerce stores"""
    
    def __init__(self, samples_dir: Path):
        self.samples_dir = samples_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def collect_shopify_sample(self, store_url: str, output_file: str) -> bool:
        """Collect sample data from a Shopify store"""
        try:
            # Clean the URL
            store_url = store_url.rstrip('/')
            if not store_url.startswith('http'):
                store_url = f'https://{store_url}'
            
            # Try to get products
            products_url = urljoin(store_url, '/products.json?limit=250')
            print(f"🔍 Collecting from: {products_url}")
            
            response = self.session.get(products_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Save the data
            output_path = self.samples_dir / "shopify" / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            product_count = len(data.get('products', []))
            print(f"✅ Collected {product_count} products from {store_url}")
            print(f"📁 Saved to: {output_path}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to collect from {store_url}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error collecting from {store_url}: {e}")
            return False
    
    def collect_woocommerce_sample(self, store_url: str, output_file: str) -> bool:
        """Collect sample data from a WooCommerce store"""
        try:
            # Clean the URL
            store_url = store_url.rstrip('/')
            if not store_url.startswith('http'):
                store_url = f'https://{store_url}'
            
            # Try WooCommerce Store API v2 first
            products_url = urljoin(store_url, '/wp-json/wc/store/products?per_page=100')
            print(f"🔍 Collecting from: {products_url}")
            
            response = self.session.get(products_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
            else:
                # Fallback to v1
                products_url = urljoin(store_url, '/wp-json/wc/store/v1/products?per_page=100')
                print(f"🔄 Trying v1 API: {products_url}")
                
                response = self.session.get(products_url, timeout=30)
                response.raise_for_status()
                data = response.json()
            
            # Save the data
            output_path = self.samples_dir / "woocommerce" / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            product_count = len(data) if isinstance(data, list) else len(data.get('products', []))
            print(f"✅ Collected {product_count} products from {store_url}")
            print(f"📁 Saved to: {output_path}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to collect from {store_url}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error collecting from {store_url}: {e}")
            return False
    
    def detect_platform(self, store_url: str) -> Optional[str]:
        """Detect if a store is Shopify or WooCommerce"""
        try:
            store_url = store_url.rstrip('/')
            if not store_url.startswith('http'):
                store_url = f'https://{store_url}'
            
            # Try Shopify first
            shopify_url = urljoin(store_url, '/products.json?limit=1')
            response = self.session.get(shopify_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'products' in data:
                    return 'shopify'
            
            # Try WooCommerce
            woo_url = urljoin(store_url, '/wp-json/wc/store/products?per_page=1')
            response = self.session.get(woo_url, timeout=10)
            if response.status_code == 200:
                return 'woocommerce'
            
            return None
            
        except Exception:
            return None


def main():
    """Main collection function"""
    samples_dir = Path(__file__).parent.parent / "samples"
    
    if not samples_dir.exists():
        print(f"❌ Samples directory not found: {samples_dir}")
        return
    
    collector = SampleCollector(samples_dir)
    
    if len(sys.argv) < 3:
        print("Usage: python collect-samples.py <store_url> <output_filename>")
        print("\nExamples:")
        print("  python collect-samples.py https://store.myshopify.com myshopify-store.json")
        print("  python collect-samples.py https://store.com store-woocommerce.json")
        print("\nOr run interactively:")
        print("  python collect-samples.py")
        return
    
    store_url = sys.argv[1]
    output_file = sys.argv[2]
    
    # Detect platform
    print(f"🔍 Detecting platform for: {store_url}")
    platform = collector.detect_platform(store_url)
    
    if platform == 'shopify':
        print("✅ Detected Shopify store")
        success = collector.collect_shopify_sample(store_url, output_file)
    elif platform == 'woocommerce':
        print("✅ Detected WooCommerce store")
        success = collector.collect_woocommerce_sample(store_url, output_file)
    else:
        print(f"❌ Could not detect platform for {store_url}")
        print("Trying both platforms...")
        
        success = collector.collect_shopify_sample(store_url, f"{output_file}-shopify.json")
        if not success:
            success = collector.collect_woocommerce_sample(store_url, f"{output_file}-woocommerce.json")
    
    if success:
        print("\n🎉 Sample collection completed!")
        print("Run 'python sample-analysis.py' to analyze the new data.")
    else:
        print("\n❌ Sample collection failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
