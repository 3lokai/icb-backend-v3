#!/usr/bin/env python3
"""
Test script to validate tag normalization and notes extraction services against sample data.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from parser.tag_normalization import TagNormalizationService
from parser.notes_extraction import NotesExtractionService
from config.tag_config import TagConfig
from config.notes_config import NotesConfig


def load_sample_data():
    """Load sample data from the samples directory."""
    sample_data = {}
    
    # Load Shopify data
    shopify_files = [
        "data/samples/shopify/bluetokaicoffee-shopify.json",
        "data/samples/shopify/rosettecoffee-shopify.json"
    ]
    
    for file_path in shopify_files:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sample_data[Path(file_path).stem] = data
    
    # Load WooCommerce data
    woocommerce_files = [
        "data/samples/woocommerce/bababeans-woocommerce.json"
    ]
    
    for file_path in woocommerce_files:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sample_data[Path(file_path).stem] = data
    
    return sample_data


def extract_shopify_products(data):
    """Extract products from Shopify data."""
    products = []
    if 'products' in data:
        for product in data['products']:
            # Extract relevant fields
            product_info = {
                'id': product.get('id'),
                'title': product.get('title', ''),
                'description': product.get('body_html', ''),
                'tags': product.get('tags', []),
                'vendor': product.get('vendor', ''),
                'product_type': product.get('product_type', '')
            }
            products.append(product_info)
    return products


def extract_woocommerce_products(data):
    """Extract products from WooCommerce data."""
    products = []
    if isinstance(data, list):
        for product in data:
            # Extract relevant fields
            product_info = {
                'id': product.get('id'),
                'title': product.get('name', ''),
                'description': product.get('short_description', '') + ' ' + product.get('description', ''),
                'tags': [tag.get('name', '') for tag in product.get('tags', [])],
                'vendor': product.get('vendor', ''),
                'product_type': product.get('type', '')
            }
            products.append(product_info)
    return products


def test_tag_normalization(products):
    """Test tag normalization service on sample products."""
    print("=== Testing Tag Normalization Service ===")
    
    tag_service = TagNormalizationService()
    
    total_products = 0
    total_tags = 0
    successful_normalizations = 0
    
    for product in products:
        if not product.get('tags'):
            continue
            
        total_products += 1
        raw_tags = product['tags']
        total_tags += len(raw_tags)
        
        print(f"\nProduct: {product['title'][:50]}...")
        print(f"Raw tags: {raw_tags}")
        
        try:
            result = tag_service.normalize_tags(raw_tags)
            print(f"Normalized tags: {result.normalized_tags}")
            print(f"Confidence scores: {result.confidence_scores}")
            print(f"Warnings: {result.warnings}")
            
            if result.normalized_tags:
                successful_normalizations += 1
                
        except Exception as e:
            print(f"Error: {e}")
    
    print(f"\nTag Normalization Summary:")
    print(f"Total products processed: {total_products}")
    print(f"Total tags processed: {total_tags}")
    print(f"Successful normalizations: {successful_normalizations}")
    print(f"Success rate: {successful_normalizations/total_products*100:.1f}%" if total_products > 0 else "N/A")


def test_notes_extraction(products):
    """Test notes extraction service on sample products."""
    print("\n=== Testing Notes Extraction Service ===")
    
    notes_service = NotesExtractionService()
    
    total_products = 0
    successful_extractions = 0
    
    for product in products:
        if not product.get('description'):
            continue
            
        total_products += 1
        description = product['description']
        
        print(f"\nProduct: {product['title'][:50]}...")
        print(f"Description length: {len(description)} characters")
        
        try:
            result = notes_service.extract_notes(description)
            print(f"Extracted notes: {result.notes_raw}")
            print(f"Confidence scores: {result.confidence_scores}")
            print(f"Total notes: {result.total_notes}")
            print(f"Extraction success: {result.extraction_success}")
            print(f"Warnings: {result.warnings}")
            
            if result.extraction_success:
                successful_extractions += 1
                
        except Exception as e:
            print(f"Error: {e}")
    
    print(f"\nNotes Extraction Summary:")
    print(f"Total products processed: {total_products}")
    print(f"Successful extractions: {successful_extractions}")
    print(f"Success rate: {successful_extractions/total_products*100:.1f}%" if total_products > 0 else "N/A")


def main():
    """Main test function."""
    print("Testing Tag Normalization and Notes Extraction Services against Sample Data")
    print("=" * 80)
    
    # Load sample data
    sample_data = load_sample_data()
    print(f"Loaded {len(sample_data)} sample data files")
    
    all_products = []
    
    # Process Shopify data
    for key, data in sample_data.items():
        if 'shopify' in key:
            products = extract_shopify_products(data)
            all_products.extend(products)
            print(f"Extracted {len(products)} products from {key}")
    
    # Process WooCommerce data
    for key, data in sample_data.items():
        if 'woocommerce' in key:
            products = extract_woocommerce_products(data)
            all_products.extend(products)
            print(f"Extracted {len(products)} products from {key}")
    
    print(f"\nTotal products to test: {len(all_products)}")
    
    # Test tag normalization
    test_tag_normalization(all_products)
    
    # Test notes extraction
    test_notes_extraction(all_products)
    
    print("\n" + "=" * 80)
    print("Sample data testing completed!")


if __name__ == "__main__":
    main()
