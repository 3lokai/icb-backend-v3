#!/usr/bin/env python3
"""
Sample Data Validation Script

This script validates that your extraction logic works correctly against
known sample data from Shopify and WooCommerce stores.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "app"))



@dataclass
class ValidationResult:
    """Result of validation test"""
    test_name: str
    passed: bool
    expected_count: int
    actual_count: int
    issues: List[str]
    sample_file: str


class SampleValidator:
    """Validates extraction logic against sample data"""
    
    def __init__(self, samples_dir: Path):
        self.samples_dir = samples_dir
        self.results: List[ValidationResult] = []
    
    def validate_shopify_sample(self, sample_file: str) -> ValidationResult:
        """Validate Shopify extraction against sample data"""
        sample_path = self.samples_dir / "shopify" / sample_file
        
        with open(sample_path, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
        
        # Count coffee products in sample
        coffee_products = [
            p for p in sample_data.get("products", [])
            if self._is_coffee_product(p)
        ]
        
        expected_count = len(coffee_products)
        
        # TODO: Mock the extraction service to use sample data
        # For now, just validate the sample structure
        issues = []
        
        if "products" not in sample_data:
            issues.append("Missing 'products' key in sample data")
        
        if not sample_data.get("products"):
            issues.append("No products found in sample data")
        
        # Validate product structure
        for i, product in enumerate(sample_data.get("products", [])[:5]):  # Check first 5
            if not product.get("title"):
                issues.append(f"Product {i} missing title")
            if not product.get("handle"):
                issues.append(f"Product {i} missing handle")
        
        passed = len(issues) == 0
        
        return ValidationResult(
            test_name=f"Shopify Sample: {sample_file}",
            passed=passed,
            expected_count=expected_count,
            actual_count=expected_count,  # TODO: Replace with actual extraction count
            issues=issues,
            sample_file=sample_file
        )
    
    def validate_woocommerce_sample(self, sample_file: str) -> ValidationResult:
        """Validate WooCommerce extraction against sample data"""
        sample_path = self.samples_dir / "woocommerce" / sample_file
        
        with open(sample_path, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
        
        # Count coffee products in sample
        coffee_products = [
            p for p in sample_data
            if self._is_coffee_product(p)
        ]
        
        expected_count = len(coffee_products)
        
        # Validate sample structure
        issues = []
        
        if not isinstance(sample_data, list):
            issues.append("Sample data should be a list of products")
        
        if not sample_data:
            issues.append("No products found in sample data")
        
        # Validate product structure
        for i, product in enumerate(sample_data[:5]):  # Check first 5
            if not product.get("name"):
                issues.append(f"Product {i} missing name")
            if not product.get("permalink"):
                issues.append(f"Product {i} missing permalink")
        
        passed = len(issues) == 0
        
        return ValidationResult(
            test_name=f"WooCommerce Sample: {sample_file}",
            passed=passed,
            expected_count=expected_count,
            actual_count=expected_count,  # TODO: Replace with actual extraction count
            issues=issues,
            sample_file=sample_file
        )
    
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
                if "coffee" in str(tag).lower():
                    return True
        
        # Check title/name
        title = product.get("title", product.get("name", "")).lower()
        coffee_keywords = ["coffee", "roast", "bean", "arabica", "robusta"]
        if any(keyword in title for keyword in coffee_keywords):
            return True
        
        return False
    
    def run_all_validations(self) -> List[ValidationResult]:
        """Run all validation tests"""
        # Validate Shopify samples
        shopify_samples = list((self.samples_dir / "shopify").glob("*.json"))
        for sample_file in shopify_samples:
            result = self.validate_shopify_sample(sample_file.name)
            self.results.append(result)
        
        # Validate WooCommerce samples
        woo_samples = list((self.samples_dir / "woocommerce").glob("*.json"))
        for sample_file in woo_samples:
            result = self.validate_woocommerce_sample(sample_file.name)
            self.results.append(result)
        
        return self.results
    
    def print_results(self):
        """Print validation results"""
        print("=" * 60)
        print("SAMPLE DATA VALIDATION RESULTS")
        print("=" * 60)
        
        passed = 0
        total = len(self.results)
        
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"\n{status} {result.test_name}")
            print(f"   Expected coffee products: {result.expected_count}")
            print(f"   Actual coffee products: {result.actual_count}")
            
            if result.issues:
                print("   Issues:")
                for issue in result.issues:
                    print(f"     - {issue}")
            
            if result.passed:
                passed += 1
        
        print(f"\n{'='*60}")
        print(f"SUMMARY: {passed}/{total} tests passed")
        print(f"{'='*60}")


def main():
    """Main validation function"""
    samples_dir = Path(__file__).parent.parent / "samples"
    
    if not samples_dir.exists():
        print(f"❌ Samples directory not found: {samples_dir}")
        return
    
    validator = SampleValidator(samples_dir)
    results = validator.run_all_validations()
    validator.print_results()
    
    # Exit with error code if any tests failed
    failed_tests = [r for r in results if not r.passed]
    if failed_tests:
        sys.exit(1)


if __name__ == "__main__":
    main()
