"""
Error handling and resilience testing for sample data processing.

This module provides comprehensive error handling tests for malformed data,
graceful degradation, and recovery from processing failures.
"""

import asyncio
import json
import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock, patch

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ErrorScenario:
    """Error scenario for testing."""
    name: str
    description: str
    data_corruption_type: str
    expected_error_type: str
    should_recover: bool
    recovery_timeout: float = 5.0


@dataclass
class ErrorTestResult:
    """Result of an error handling test."""
    scenario_name: str
    error_occurred: bool
    error_type: Optional[str]
    recovery_successful: bool
    processing_continued: bool
    execution_time: float
    error_message: Optional[str] = None


class MalformedDataInjector:
    """Framework for injecting malformed data for error testing."""
    
    def __init__(self):
        self.corruption_types = [
            'json_syntax_error',
            'missing_required_fields',
            'invalid_data_types',
            'truncated_data',
            'encoding_error',
            'null_values',
            'empty_objects',
            'circular_references'
        ]
    
    def create_malformed_data(self, original_data: Dict[str, Any], corruption_type: str) -> Dict[str, Any]:
        """Create malformed data based on corruption type."""
        if corruption_type == 'json_syntax_error':
            return self._inject_json_syntax_error(original_data)
        elif corruption_type == 'missing_required_fields':
            return self._remove_required_fields(original_data)
        elif corruption_type == 'invalid_data_types':
            return self._inject_invalid_types(original_data)
        elif corruption_type == 'truncated_data':
            return self._truncate_data(original_data)
        elif corruption_type == 'encoding_error':
            return self._inject_encoding_error(original_data)
        elif corruption_type == 'null_values':
            return self._inject_null_values(original_data)
        elif corruption_type == 'empty_objects':
            return self._create_empty_objects(original_data)
        elif corruption_type == 'circular_references':
            return self._create_circular_references(original_data)
        else:
            return original_data
    
    def _inject_json_syntax_error(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inject JSON syntax errors."""
        # This would create invalid JSON, but we'll simulate it
        return {"invalid_json": "missing_closing_brace"}
    
    def _remove_required_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove required fields from data."""
        if 'products' in data:
            for product in data['products']:
                if 'id' in product:
                    del product['id']
        return data
    
    def _inject_invalid_types(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inject invalid data types."""
        if 'products' in data:
            for product in data['products']:
                if 'price' in product:
                    product['price'] = "invalid_price_string"
                if 'inventory' in product:
                    product['inventory'] = "not_a_number"
        return data
    
    def _truncate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Truncate data to simulate incomplete data."""
        if 'products' in data and len(data['products']) > 0:
            # Keep only first product
            data['products'] = data['products'][:1]
        return data
    
    def _inject_encoding_error(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inject encoding errors."""
        if 'products' in data:
            for product in data['products']:
                if 'title' in product:
                    product['title'] = "Invalid \x00 encoding \x01 characters"
        return data
    
    def _inject_null_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inject null values in critical fields."""
        if 'products' in data:
            for product in data['products']:
                product['id'] = None
                product['title'] = None
        return data
    
    def _create_empty_objects(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create empty objects."""
        return {}
    
    def _create_circular_references(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create circular references."""
        if 'products' in data:
            for product in data['products']:
                product['self_reference'] = product
        return data


class ErrorRecoveryTester:
    """Test error recovery and graceful degradation."""
    
    def __init__(self):
        self.recovery_strategies = [
            'skip_invalid_records',
            'use_default_values',
            'retry_with_delay',
            'skip_and_continue',
            'log_and_continue'
        ]
    
    async def test_graceful_degradation(self, corrupted_data: Dict[str, Any], strategy: str) -> ErrorTestResult:
        """Test graceful degradation with corrupted data."""
        start_time = datetime.now()
        error_occurred = False
        error_type = None
        recovery_successful = False
        processing_continued = False
        error_message = None
        
        try:
            # Simulate processing with error handling
            result = await self._process_with_error_handling(corrupted_data, strategy)
            processing_continued = True
            recovery_successful = True
            
        except Exception as e:
            error_occurred = True
            error_type = type(e).__name__
            error_message = str(e)
            
            # Try recovery
            try:
                await self._attempt_recovery(corrupted_data, strategy)
                recovery_successful = True
                processing_continued = True
            except Exception as recovery_error:
                recovery_successful = False
                processing_continued = False
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return ErrorTestResult(
            scenario_name=f"graceful_degradation_{strategy}",
            error_occurred=error_occurred,
            error_type=error_type,
            recovery_successful=recovery_successful,
            processing_continued=processing_continued,
            execution_time=execution_time,
            error_message=error_message
        )
    
    async def _process_with_error_handling(self, data: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        """Process data with error handling strategy."""
        if strategy == 'skip_invalid_records':
            return await self._skip_invalid_records(data)
        elif strategy == 'use_default_values':
            return await self._use_default_values(data)
        elif strategy == 'retry_with_delay':
            return await self._retry_with_delay(data)
        elif strategy == 'skip_and_continue':
            return await self._skip_and_continue(data)
        elif strategy == 'log_and_continue':
            return await self._log_and_continue(data)
        else:
            return data
    
    async def _skip_invalid_records(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Skip invalid records and continue processing."""
        if 'products' in data:
            valid_products = []
            for product in data['products']:
                if self._is_valid_product(product):
                    valid_products.append(product)
            data['products'] = valid_products
        return data
    
    async def _use_default_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Use default values for missing or invalid data."""
        if 'products' in data:
            for product in data['products']:
                if not product.get('id'):
                    product['id'] = f"default_{random.randint(1000, 9999)}"
                if not product.get('title'):
                    product['title'] = "Unknown Product"
                if not product.get('price'):
                    product['price'] = 0.0
        return data
    
    async def _retry_with_delay(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Retry processing with delay."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Simulate processing
                await asyncio.sleep(0.1)
                return data
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)  # Delay before retry
                else:
                    raise
    
    async def _skip_and_continue(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Skip problematic data and continue."""
        # Remove problematic entries
        if 'products' in data:
            data['products'] = [p for p in data['products'] if self._is_valid_product(p)]
        return data
    
    async def _log_and_continue(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Log errors and continue processing."""
        logger.warning("Processing data with potential issues")
        return data
    
    def _is_valid_product(self, product: Dict[str, Any]) -> bool:
        """Check if product data is valid."""
        return (
            product.get('id') is not None and
            product.get('title') is not None and
            product.get('title') != ""
        )
    
    async def _attempt_recovery(self, data: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        """Attempt to recover from error."""
        # Simulate recovery process
        await asyncio.sleep(0.1)
        return data


class ErrorHandlingTestSuite:
    """Comprehensive error handling test suite."""
    
    def __init__(self):
        self.data_injector = MalformedDataInjector()
        self.recovery_tester = ErrorRecoveryTester()
        self.error_scenarios = self._create_error_scenarios()
    
    def _create_error_scenarios(self) -> List[ErrorScenario]:
        """Create error scenarios for testing."""
        return [
            ErrorScenario(
                name="json_syntax_error",
                description="Invalid JSON syntax",
                data_corruption_type="json_syntax_error",
                expected_error_type="JSONDecodeError",
                should_recover=True
            ),
            ErrorScenario(
                name="missing_required_fields",
                description="Missing required product fields",
                data_corruption_type="missing_required_fields",
                expected_error_type="KeyError",
                should_recover=True
            ),
            ErrorScenario(
                name="invalid_data_types",
                description="Invalid data types in product fields",
                data_corruption_type="invalid_data_types",
                expected_error_type="TypeError",
                should_recover=True
            ),
            ErrorScenario(
                name="truncated_data",
                description="Incomplete data due to truncation",
                data_corruption_type="truncated_data",
                expected_error_type="IndexError",
                should_recover=True
            ),
            ErrorScenario(
                name="encoding_error",
                description="Invalid character encoding",
                data_corruption_type="encoding_error",
                expected_error_type="UnicodeDecodeError",
                should_recover=True
            ),
            ErrorScenario(
                name="null_values",
                description="Null values in critical fields",
                data_corruption_type="null_values",
                expected_error_type="AttributeError",
                should_recover=True
            ),
            ErrorScenario(
                name="empty_objects",
                description="Empty data objects",
                data_corruption_type="empty_objects",
                expected_error_type="KeyError",
                should_recover=True
            ),
            ErrorScenario(
                name="circular_references",
                description="Circular references in data",
                data_corruption_type="circular_references",
                expected_error_type="RecursionError",
                should_recover=False
            )
        ]
    
    async def run_error_handling_tests(self, sample_data_path: str) -> List[ErrorTestResult]:
        """Run comprehensive error handling tests."""
        results = []
        
        # Load sample data
        sample_data = self._load_sample_data(sample_data_path)
        
        for scenario in self.error_scenarios:
            logger.info(f"Testing error scenario: {scenario.name}")
            
            # Create corrupted data
            corrupted_data = self.data_injector.create_malformed_data(sample_data, scenario.data_corruption_type)
            
            # Test each recovery strategy
            for strategy in self.recovery_tester.recovery_strategies:
                result = await self.recovery_tester.test_graceful_degradation(corrupted_data, strategy)
                result.scenario_name = f"{scenario.name}_{strategy}"
                results.append(result)
        
        return results
    
    def _load_sample_data(self, sample_data_path: str) -> Dict[str, Any]:
        """Load sample data for testing."""
        sample_files = list(Path(sample_data_path).glob("**/*.json"))
        
        if not sample_files:
            # Return mock data if no sample files found
            return {
                "products": [
                    {
                        "id": "test_product_1",
                        "title": "Test Product",
                        "price": 10.99,
                        "inventory": 100
                    }
                ]
            }
        
        # Load first sample file
        with open(sample_files[0], 'r', encoding='utf-8') as f:
            return json.load(f)


# Test cases for error handling
class TestErrorHandling:
    """Test cases for error handling and resilience testing."""
    
    @pytest.fixture
    def malformed_data_injector(self):
        """Malformed data injector fixture."""
        return MalformedDataInjector()
    
    @pytest.fixture
    def error_recovery_tester(self):
        """Error recovery tester fixture."""
        return ErrorRecoveryTester()
    
    @pytest.fixture
    def error_handling_suite(self):
        """Error handling test suite fixture."""
        return ErrorHandlingTestSuite()
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {
            "products": [
                {
                    "id": "test_product_1",
                    "title": "Test Product 1",
                    "price": 10.99,
                    "inventory": 100
                },
                {
                    "id": "test_product_2",
                    "title": "Test Product 2",
                    "price": 15.99,
                    "inventory": 50
                }
            ]
        }
    
    def test_malformed_data_injection(self, malformed_data_injector, sample_data):
        """Test malformed data injection."""
        # Test missing required fields
        corrupted_data = malformed_data_injector.create_malformed_data(sample_data, 'missing_required_fields')
        
        # Check that required fields are removed
        for product in corrupted_data.get('products', []):
            assert 'id' not in product or product['id'] is None
    
    def test_invalid_data_types_injection(self, malformed_data_injector, sample_data):
        """Test invalid data types injection."""
        corrupted_data = malformed_data_injector.create_malformed_data(sample_data, 'invalid_data_types')
        
        # Check that data types are corrupted
        for product in corrupted_data.get('products', []):
            if 'price' in product:
                assert isinstance(product['price'], str)
    
    def test_data_truncation(self, malformed_data_injector, sample_data):
        """Test data truncation."""
        corrupted_data = malformed_data_injector.create_malformed_data(sample_data, 'truncated_data')
        
        # Check that data is truncated
        assert len(corrupted_data.get('products', [])) <= 1
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_skip_invalid(self, error_recovery_tester, sample_data):
        """Test graceful degradation with skip invalid records strategy."""
        # Create corrupted data
        corrupted_data = sample_data.copy()
        corrupted_data['products'][0]['id'] = None  # Make first product invalid
        
        result = await error_recovery_tester.test_graceful_degradation(corrupted_data, 'skip_invalid_records')
        
        assert result.processing_continued is True
        assert result.recovery_successful is True
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_default_values(self, error_recovery_tester, sample_data):
        """Test graceful degradation with default values strategy."""
        # Create corrupted data
        corrupted_data = sample_data.copy()
        corrupted_data['products'][0]['id'] = None
        corrupted_data['products'][0]['title'] = None
        
        result = await error_recovery_tester.test_graceful_degradation(corrupted_data, 'use_default_values')
        
        assert result.processing_continued is True
        assert result.recovery_successful is True
    
    @pytest.mark.asyncio
    async def test_error_handling_suite(self, error_handling_suite):
        """Test comprehensive error handling suite."""
        # Mock sample data path
        sample_data_path = "data/samples"
        
        # Mock the sample data loading
        with patch.object(error_handling_suite, '_load_sample_data') as mock_load:
            mock_load.return_value = {
                "products": [
                    {"id": "test_1", "title": "Test 1", "price": 10.99},
                    {"id": "test_2", "title": "Test 2", "price": 15.99}
                ]
            }
            
            results = await error_handling_suite.run_error_handling_tests(sample_data_path)
            
            # Should have results for each scenario and strategy combination
            expected_results = len(error_handling_suite.error_scenarios) * len(error_handling_suite.recovery_tester.recovery_strategies)
            assert len(results) == expected_results
    
    def test_error_scenarios_creation(self, error_handling_suite):
        """Test error scenarios creation."""
        scenarios = error_handling_suite.error_scenarios
        
        assert len(scenarios) > 0
        
        # Check that each scenario has required fields
        for scenario in scenarios:
            assert scenario.name
            assert scenario.description
            assert scenario.data_corruption_type
            assert scenario.expected_error_type
            assert isinstance(scenario.should_recover, bool)


if __name__ == "__main__":
    # Run error handling tests
    pytest.main([__file__, "-v"])
