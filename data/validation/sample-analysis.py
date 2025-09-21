#!/usr/bin/env python3
"""
Sample Data Analysis Script

This script analyzes your sample data to provide insights about:
- Product types and categories
- Data structure and completeness
- Coffee vs non-coffee products
- Price ranges and variants
"""

import json
from pathlib import Path
from typing import Dict, Any, Counter
from collections import defaultdict


class SampleAnalyzer:
    """Analyzes sample data for insights"""
    
    def __init__(self, samples_dir: Path):
        self.samples_dir = samples_dir
    
    def analyze_shopify_sample(self, sample_file: str) -> Dict[str, Any]:
        """Analyze a Shopify sample file"""
        sample_path = self.samples_dir / "shopify" / sample_file
        
        with open(sample_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        products = data.get("products", [])
        
        analysis = {
            "total_products": len(products),
            "product_types": Counter(),
            "vendors": Counter(),
            "tags": Counter(),
            "price_ranges": defaultdict(int),
            "variants_count": defaultdict(int),
            "coffee_products": 0,
            "non_coffee_products": 0,
            "missing_fields": defaultdict(int),
            "sample_file": sample_file
        }
        
        for product in products:
            # Product types
            product_type = product.get("product_type", "Unknown")
            analysis["product_types"][product_type] += 1
            
            # Vendors
            vendor = product.get("vendor", "Unknown")
            analysis["vendors"][vendor] += 1
            
            # Tags
            tags = product.get("tags", [])
            for tag in tags:
                analysis["tags"][tag] += 1
            
            # Price analysis
            variants = product.get("variants", [])
            analysis["variants_count"][len(variants)] += 1
            
            if variants:
                prices = [float(v.get("price", 0)) for v in variants if v.get("price")]
                if prices:
                    min_price = min(prices)
                    if min_price < 100:
                        analysis["price_ranges"]["< ₹100"] += 1
                    elif min_price < 500:
                        analysis["price_ranges"]["₹100-500"] += 1
                    elif min_price < 1000:
                        analysis["price_ranges"]["₹500-1000"] += 1
                    elif min_price < 2000:
                        analysis["price_ranges"]["₹1000-2000"] += 1
                    else:
                        analysis["price_ranges"]["> ₹2000"] += 1
            
            # Coffee classification
            if self._is_coffee_product(product):
                analysis["coffee_products"] += 1
            else:
                analysis["non_coffee_products"] += 1
            
            # Missing fields
            required_fields = ["title", "handle", "variants"]
            for field in required_fields:
                if not product.get(field):
                    analysis["missing_fields"][field] += 1
        
        return analysis
    
    def analyze_woocommerce_sample(self, sample_file: str) -> Dict[str, Any]:
        """Analyze a WooCommerce sample file"""
        sample_path = self.samples_dir / "woocommerce" / sample_file
        
        with open(sample_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        analysis = {
            "total_products": len(products),
            "categories": Counter(),
            "tags": Counter(),
            "price_ranges": defaultdict(int),
            "variations_count": defaultdict(int),
            "coffee_products": 0,
            "non_coffee_products": 0,
            "missing_fields": defaultdict(int),
            "sample_file": sample_file
        }
        
        for product in products:
            # Categories
            categories = product.get("categories", [])
            for category in categories:
                analysis["categories"][category.get("name", "Unknown")] += 1
            
            # Tags
            tags = product.get("tags", [])
            for tag in tags:
                analysis["tags"][tag.get("name", "Unknown")] += 1
            
            # Price analysis
            prices = product.get("prices", {})
            if prices:
                price = float(prices.get("price", 0))
                if price < 100:
                    analysis["price_ranges"]["< ₹100"] += 1
                elif price < 500:
                    analysis["price_ranges"]["₹100-500"] += 1
                elif price < 1000:
                    analysis["price_ranges"]["₹500-1000"] += 1
                elif price < 2000:
                    analysis["price_ranges"]["₹1000-2000"] += 1
                else:
                    analysis["price_ranges"]["> ₹2000"] += 1
            
            # Variations
            variations = product.get("variations", [])
            analysis["variations_count"][len(variations)] += 1
            
            # Coffee classification
            if self._is_coffee_product(product):
                analysis["coffee_products"] += 1
            else:
                analysis["non_coffee_products"] += 1
            
            # Missing fields
            required_fields = ["name", "permalink", "prices"]
            for field in required_fields:
                if not product.get(field):
                    analysis["missing_fields"][field] += 1
        
        return analysis
    
    def _is_coffee_product(self, product: Dict[str, Any]) -> bool:
        """Determine if a product is coffee-related"""
        # Shopify logic
        if "product_type" in product:
            coffee_types = ["coffee", "single estate coffee", "producer series"]
            if product.get("product_type", "").lower() in coffee_types:
                return True
        
        # WooCommerce logic
        if "categories" in product:
            for category in product.get("categories", []):
                if "coffee" in category.get("name", "").lower():
                    return True
        
        # Check tags
        tags = product.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, dict):
                    tag_name = tag.get("name", "")
                else:
                    tag_name = str(tag)
                if "coffee" in tag_name.lower():
                    return True
        
        # Check title/name
        title = product.get("title", product.get("name", "")).lower()
        coffee_keywords = ["coffee", "roast", "bean", "arabica", "robusta"]
        if any(keyword in title for keyword in coffee_keywords):
            return True
        
        return False
    
    def print_analysis(self, analysis: Dict[str, Any]):
        """Print analysis results"""
        print(f"\n{'='*60}")
        print(f"ANALYSIS: {analysis['sample_file']}")
        print(f"{'='*60}")
        
        print("\n📊 PRODUCT OVERVIEW:")
        print(f"   Total products: {analysis['total_products']}")
        print(f"   Coffee products: {analysis['coffee_products']}")
        print(f"   Non-coffee products: {analysis['non_coffee_products']}")
        
        if analysis['coffee_products'] > 0:
            coffee_percentage = (analysis['coffee_products'] / analysis['total_products']) * 100
            print(f"   Coffee percentage: {coffee_percentage:.1f}%")
        
        # Product types (Shopify) or Categories (WooCommerce)
        if "product_types" in analysis:
            print("\n🏷️  PRODUCT TYPES (Top 10):")
            for product_type, count in analysis["product_types"].most_common(10):
                print(f"   {product_type}: {count}")
        
        if "categories" in analysis:
            print("\n📂 CATEGORIES (Top 10):")
            for category, count in analysis["categories"].most_common(10):
                print(f"   {category}: {count}")
        
        # Price ranges
        if analysis["price_ranges"]:
            print("\n💰 PRICE RANGES:")
            for price_range, count in sorted(analysis["price_ranges"].items()):
                print(f"   {price_range}: {count}")
        
        # Variants/Variations
        if "variants_count" in analysis and analysis["variants_count"]:
            print("\n🔄 VARIANTS COUNT:")
            for variant_count, count in sorted(analysis["variants_count"].items()):
                print(f"   {variant_count} variants: {count} products")
        
        if "variations_count" in analysis and analysis["variations_count"]:
            print("\n🔄 VARIATIONS COUNT:")
            for variation_count, count in sorted(analysis["variations_count"].items()):
                print(f"   {variation_count} variations: {count} products")
        
        # Missing fields
        if analysis["missing_fields"]:
            print("\n⚠️  MISSING FIELDS:")
            for field, count in analysis["missing_fields"].items():
                print(f"   {field}: {count} products")
        
        # Top tags
        if analysis["tags"]:
            print("\n🏷️  TOP TAGS (Top 15):")
            for tag, count in analysis["tags"].most_common(15):
                print(f"   {tag}: {count}")
    
    def run_analysis(self):
        """Run analysis on all sample files"""
        print("🔍 SAMPLE DATA ANALYSIS")
        print("=" * 60)
        
        # Analyze Shopify samples
        shopify_samples = list((self.samples_dir / "shopify").glob("*.json"))
        for sample_file in shopify_samples:
            analysis = self.analyze_shopify_sample(sample_file.name)
            self.print_analysis(analysis)
        
        # Analyze WooCommerce samples
        woo_samples = list((self.samples_dir / "woocommerce").glob("*.json"))
        for sample_file in woo_samples:
            analysis = self.analyze_woocommerce_sample(sample_file.name)
            self.print_analysis(analysis)


def main():
    """Main analysis function"""
    samples_dir = Path(__file__).parent.parent / "samples"
    
    if not samples_dir.exists():
        print(f"❌ Samples directory not found: {samples_dir}")
        return
    
    analyzer = SampleAnalyzer(samples_dir)
    analyzer.run_analysis()


if __name__ == "__main__":
    main()
