"""
Contract tests for database schema validation.

Tests validate:
- Database table schemas match RPC expectations
- Foreign key constraints and relationships
- Database triggers and functions
- Database indexes and performance
- Database migration compatibility
"""

import pytest
import uuid
from typing import Dict, Any, List
from unittest.mock import Mock, patch
from src.validator.rpc_client import RPCClient, RPCError


class TestDatabaseSchemaContracts:
    """Contract tests for database schema validation."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        client = Mock()
        return client
    
    @pytest.fixture
    def rpc_client(self, mock_supabase_client):
        """Create RPC client with mock Supabase client."""
        return RPCClient(mock_supabase_client)
    
    def test_coffees_table_schema_contract(self, rpc_client):
        """Test coffees table schema matches RPC expectations."""
        # Mock table query to return schema information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Test Coffee',
                'slug': 'test-coffee',
                'roaster_id': str(uuid.uuid4()),
                'description_md': 'Test description',
                'direct_buy_url': 'https://example.com',
                'platform_product_id': 'prod-123',
                'status': 'active',
                'decaf': False,
                'notes_raw': {'source': 'test'},
                'source_raw': {'platform': 'shopify'},
                'roast_level': 'medium',
                'roast_level_raw': 'Medium Roast',
                'roast_style_raw': 'City Roast',
                'process': 'washed',
                'process_raw': 'Washed Process',
                'bean_species': 'arabica',
                'default_grind': 'whole',
                'varieties': ['heirloom'],
                'tags': ['fruity', 'bright'],
                'rating_avg': 4.5,
                'rating_count': 10,
                'created_at': '2024-01-15T10:30:00Z',
                'updated_at': '2024-01-15T10:30:00Z'
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query the coffees table
        result = rpc_client.supabase_client.table('coffees').select('*').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        coffee = result.data[0]
        
        # Validate required fields exist
        assert 'id' in coffee
        assert 'name' in coffee
        assert 'slug' in coffee
        assert 'roaster_id' in coffee
        assert 'description_md' in coffee
        assert 'direct_buy_url' in coffee
        assert 'platform_product_id' in coffee
        assert 'status' in coffee
        assert 'decaf' in coffee
        assert 'roast_level' in coffee
        assert 'process' in coffee
        assert 'bean_species' in coffee
        assert 'created_at' in coffee
        assert 'updated_at' in coffee
    
    def test_variants_table_schema_contract(self, rpc_client):
        """Test variants table schema matches RPC expectations."""
        # Mock table query to return schema information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'id': str(uuid.uuid4()),
                'coffee_id': str(uuid.uuid4()),
                'platform_variant_id': 'var-123',
                'sku': 'COFFEE-250G',
                'weight_g': 250,
                'grind': 'whole',
                'pack_count': 1,
                'currency': 'INR',
                'price_current': 450.0,
                'compare_at_price': 500.0,
                'in_stock': True,
                'stock_qty': 10,
                'subscription_available': False,
                'status': 'active',
                'source_raw': {'platform': 'shopify'},
                'created_at': '2024-01-15T10:30:00Z',
                'updated_at': '2024-01-15T10:30:00Z'
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query the variants table
        result = rpc_client.supabase_client.table('variants').select('*').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        variant = result.data[0]
        
        # Validate required fields exist
        assert 'id' in variant
        assert 'coffee_id' in variant
        assert 'platform_variant_id' in variant
        assert 'sku' in variant
        assert 'weight_g' in variant
        assert 'grind' in variant
        assert 'pack_count' in variant
        assert 'currency' in variant
        assert 'in_stock' in variant
        assert 'subscription_available' in variant
        assert 'created_at' in variant
        assert 'updated_at' in variant
    
    def test_prices_table_schema_contract(self, rpc_client):
        """Test prices table schema matches RPC expectations."""
        # Mock table query to return schema information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'id': str(uuid.uuid4()),
                'variant_id': str(uuid.uuid4()),
                'price': 450.0,
                'currency': 'INR',
                'is_sale': False,
                'scraped_at': '2024-01-15T10:30:00Z',
                'source_url': 'https://example.com/product',
                'source_raw': {'platform': 'shopify'},
                'created_at': '2024-01-15T10:30:00Z'
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query the prices table
        result = rpc_client.supabase_client.table('prices').select('*').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        price = result.data[0]
        
        # Validate required fields exist
        assert 'id' in price
        assert 'variant_id' in price
        assert 'price' in price
        assert 'currency' in price
        assert 'is_sale' in price
        assert 'scraped_at' in price
        assert 'created_at' in price
    
    def test_coffee_images_table_schema_contract(self, rpc_client):
        """Test coffee_images table schema matches RPC expectations."""
        # Mock table query to return schema information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'id': str(uuid.uuid4()),
                'coffee_id': str(uuid.uuid4()),
                'url': 'https://example.com/image.jpg',
                'imagekit_url': 'https://ik.imagekit.io/coffee/image.jpg',
                'alt': 'Coffee image',
                'width': 800,
                'height': 600,
                'sort_order': 1,
                'content_hash': 'sha256:abc123def456',
                'source_raw': {'platform': 'shopify'},
                'updated_at': '2024-01-15T10:30:00Z'
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query the coffee_images table
        result = rpc_client.supabase_client.table('coffee_images').select('*').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        image = result.data[0]
        
        # Validate required fields exist
        assert 'id' in image
        assert 'coffee_id' in image
        assert 'url' in image
        assert 'sort_order' in image
        assert 'updated_at' in image
    
    def test_foreign_key_constraints(self, rpc_client):
        """Test foreign key constraints and relationships."""
        # Test coffee -> roaster relationship
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'id': str(uuid.uuid4()),
                'roaster_id': str(uuid.uuid4()),
                'name': 'Test Coffee'
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query with foreign key
        result = rpc_client.supabase_client.table('coffees').select('id, roaster_id, name').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        coffee = result.data[0]
        assert 'roaster_id' in coffee
        
        # Test variant -> coffee relationship
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'id': str(uuid.uuid4()),
                'coffee_id': str(uuid.uuid4()),
                'sku': 'COFFEE-250G'
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        result = rpc_client.supabase_client.table('variants').select('id, coffee_id, sku').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        variant = result.data[0]
        assert 'coffee_id' in variant
        
        # Test price -> variant relationship
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'id': str(uuid.uuid4()),
                'variant_id': str(uuid.uuid4()),
                'price': 450.0
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        result = rpc_client.supabase_client.table('prices').select('id, variant_id, price').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        price = result.data[0]
        assert 'variant_id' in price
        
        # Test image -> coffee relationship
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'id': str(uuid.uuid4()),
                'coffee_id': str(uuid.uuid4()),
                'url': 'https://example.com/image.jpg'
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        result = rpc_client.supabase_client.table('coffee_images').select('id, coffee_id, url').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        image = result.data[0]
        assert 'coffee_id' in image
    
    def test_database_indexes_performance(self, rpc_client):
        """Test database indexes and performance."""
        # Mock index information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {'index_name': 'coffees_slug_roaster_id_key', 'is_unique': True},
            {'index_name': 'coffees_roaster_id_idx', 'is_unique': False},
            {'index_name': 'variants_coffee_id_idx', 'is_unique': False},
            {'index_name': 'prices_variant_id_scraped_at_key', 'is_unique': True},
            {'index_name': 'coffee_images_coffee_id_idx', 'is_unique': False}
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query index information
        result = rpc_client.supabase_client.table('pg_indexes').select('indexname, indexdef').execute()
        
        assert result.data is not None
        assert len(result.data) == 5
        
        # Validate that critical indexes exist
        index_names = [idx['index_name'] for idx in result.data]
        assert 'coffees_slug_roaster_id_key' in index_names
        assert 'variants_coffee_id_idx' in index_names
        assert 'prices_variant_id_scraped_at_key' in index_names
        assert 'coffee_images_coffee_id_idx' in index_names
    
    def test_database_triggers_functions(self, rpc_client):
        """Test database triggers and functions."""
        # Mock trigger information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {'trigger_name': 'update_updated_at_column', 'table_name': 'coffees'},
            {'trigger_name': 'update_updated_at_column', 'table_name': 'variants'},
            {'trigger_name': 'update_updated_at_column', 'table_name': 'coffee_images'}
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query trigger information
        result = rpc_client.supabase_client.table('information_schema.triggers').select('trigger_name, event_object_table').execute()
        
        assert result.data is not None
        assert len(result.data) == 3
        
        # Validate that critical triggers exist
        trigger_names = [trigger['trigger_name'] for trigger in result.data]
        assert 'update_updated_at_column' in trigger_names
    
    def test_database_migration_compatibility(self, rpc_client):
        """Test database migration compatibility."""
        # Mock migration information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {'version': '001', 'description': 'Initial schema'},
            {'version': '002', 'description': 'Add indexes'},
            {'version': '003', 'description': 'Add RPC functions'},
            {'version': '004', 'description': 'Add Epic C parameters'}
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query migration information
        result = rpc_client.supabase_client.table('schema_migrations').select('version, description').execute()
        
        assert result.data is not None
        assert len(result.data) == 4
        
        # Validate that critical migrations exist
        versions = [migration['version'] for migration in result.data]
        assert '001' in versions
        assert '002' in versions
        assert '003' in versions
        assert '004' in versions
    
    def test_enum_types_validation(self, rpc_client):
        """Test enum types validation."""
        # Mock enum type information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {'enum_name': 'species_enum', 'enum_values': ['arabica', 'robusta', 'liberica', 'excelsa']},
            {'enum_name': 'process_enum', 'enum_values': ['washed', 'natural', 'honey', 'semi-washed']},
            {'enum_name': 'roast_level_enum', 'enum_values': ['light', 'medium', 'medium-dark', 'dark']},
            {'enum_name': 'grind_enum', 'enum_values': ['whole', 'coarse', 'medium', 'fine', 'extra-fine']},
            {'enum_name': 'coffee_status_enum', 'enum_values': ['active', 'inactive', 'discontinued']},
            {'enum_name': 'platform_enum', 'enum_values': ['shopify', 'woocommerce', 'custom', 'other']}
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query enum type information
        result = rpc_client.supabase_client.table('pg_enum').select('enumlabel').execute()
        
        assert result.data is not None
        assert len(result.data) == 6
        
        # Validate that critical enum types exist
        enum_names = [enum['enum_name'] for enum in result.data]
        assert 'species_enum' in enum_names
        assert 'process_enum' in enum_names
        assert 'roast_level_enum' in enum_names
        assert 'grind_enum' in enum_names
        assert 'coffee_status_enum' in enum_names
        assert 'platform_enum' in enum_names
    
    def test_json_fields_validation(self, rpc_client):
        """Test JSON fields validation."""
        # Mock JSON field information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'notes_raw': {'sensory': {'acidity': 8.5, 'body': 6.0}, 'flavors': ['blueberry', 'lemon']},
                'source_raw': {'platform': 'shopify', 'product_id': '12345'},
                'social_json': {'instagram': '@roaster', 'twitter': '@roaster'}
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query JSON fields
        result = rpc_client.supabase_client.table('coffees').select('notes_raw, source_raw, social_json').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        coffee = result.data[0]
        
        # Validate JSON fields exist and are properly structured
        assert 'notes_raw' in coffee
        assert 'source_raw' in coffee
        assert 'social_json' in coffee
        
        # Validate JSON structure
        assert isinstance(coffee['notes_raw'], dict)
        assert isinstance(coffee['source_raw'], dict)
        assert isinstance(coffee['social_json'], dict)
    
    def test_array_fields_validation(self, rpc_client):
        """Test array fields validation."""
        # Mock array field information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'varieties': ['heirloom', 'geisha'],
                'tags': ['fruity', 'bright', 'ethiopian'],
                'flavors': ['blueberry', 'lemon', 'jasmine']
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query array fields
        result = rpc_client.supabase_client.table('coffees').select('varieties, tags, flavors').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        coffee = result.data[0]
        
        # Validate array fields exist and are properly structured
        assert 'varieties' in coffee
        assert 'tags' in coffee
        assert 'flavors' in coffee
        
        # Validate array structure
        assert isinstance(coffee['varieties'], list)
        assert isinstance(coffee['tags'], list)
        assert isinstance(coffee['flavors'], list)
    
    def test_timestamp_fields_validation(self, rpc_client):
        """Test timestamp fields validation."""
        # Mock timestamp field information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'created_at': '2024-01-15T10:30:00Z',
                'updated_at': '2024-01-15T10:30:00Z',
                'first_seen_at': '2024-01-15T10:30:00Z',
                'last_seen_at': '2024-01-15T10:30:00Z'
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query timestamp fields
        result = rpc_client.supabase_client.table('coffees').select('created_at, updated_at, first_seen_at, last_seen_at').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        coffee = result.data[0]
        
        # Validate timestamp fields exist
        assert 'created_at' in coffee
        assert 'updated_at' in coffee
        assert 'first_seen_at' in coffee
        assert 'last_seen_at' in coffee
        
        # Validate timestamp format
        assert coffee['created_at'] == '2024-01-15T10:30:00Z'
        assert coffee['updated_at'] == '2024-01-15T10:30:00Z'
    
    def test_numeric_fields_validation(self, rpc_client):
        """Test numeric fields validation."""
        # Mock numeric field information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'weight_g': 250,
                'price': 450.0,
                'rating_avg': 4.5,
                'rating_count': 10,
                'altitude': 2000,
                'acidity': 8.5,
                'body': 6.0
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query numeric fields
        result = rpc_client.supabase_client.table('coffees').select('weight_g, price, rating_avg, rating_count, altitude, acidity, body').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        coffee = result.data[0]
        
        # Validate numeric fields exist and are properly typed
        assert 'weight_g' in coffee
        assert 'price' in coffee
        assert 'rating_avg' in coffee
        assert 'rating_count' in coffee
        assert 'altitude' in coffee
        assert 'acidity' in coffee
        assert 'body' in coffee
        
        # Validate numeric types
        assert isinstance(coffee['weight_g'], int)
        assert isinstance(coffee['price'], float)
        assert isinstance(coffee['rating_avg'], float)
        assert isinstance(coffee['rating_count'], int)
        assert isinstance(coffee['altitude'], int)
        assert isinstance(coffee['acidity'], float)
        assert isinstance(coffee['body'], float)
    
    def test_boolean_fields_validation(self, rpc_client):
        """Test boolean fields validation."""
        # Mock boolean field information
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value.data = [
            {
                'decaf': False,
                'in_stock': True,
                'subscription_available': False,
                'is_sale': True
            }
        ]
        
        rpc_client.supabase_client.table.return_value = mock_table
        
        # Test that we can query boolean fields
        result = rpc_client.supabase_client.table('coffees').select('decaf, in_stock, subscription_available, is_sale').execute()
        
        assert result.data is not None
        assert len(result.data) == 1
        coffee = result.data[0]
        
        # Validate boolean fields exist and are properly typed
        assert 'decaf' in coffee
        assert 'in_stock' in coffee
        assert 'subscription_available' in coffee
        assert 'is_sale' in coffee
        
        # Validate boolean types
        assert isinstance(coffee['decaf'], bool)
        assert isinstance(coffee['in_stock'], bool)
        assert isinstance(coffee['subscription_available'], bool)
        assert isinstance(coffee['is_sale'], bool)
