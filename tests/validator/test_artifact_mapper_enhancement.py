"""
Integration tests for ArtifactMapper enhancement with tag normalization and notes extraction.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.validator.artifact_mapper import ArtifactMapper
from src.validator.integration_service import ValidatorIntegrationService
from src.config.validator_config import ValidatorConfig, TagConfig, NotesConfig
from src.parser.tag_normalization import TagNormalizationService, TagNormalizationResult
from src.parser.notes_extraction import NotesExtractionService, NotesExtractionResult


class TestArtifactMapperEnhancement:
    """Test cases for ArtifactMapper enhancement with parser services."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tag_config = TagConfig()
        self.notes_config = NotesConfig()
        self.validator_config = ValidatorConfig(
            enable_tag_normalization=True,
            tag_config=self.tag_config,
            enable_notes_extraction=True,
            notes_config=self.notes_config
        )
        
        # Mock integration service
        self.integration_service = Mock(spec=ValidatorIntegrationService)
        self.integration_service.config = self.validator_config
        self.integration_service.tag_normalization_service = TagNormalizationService(config=self.tag_config)
        self.integration_service.notes_extraction_service = NotesExtractionService(config=self.notes_config)
        
        # Mock weight parser
        self.weight_parser = Mock()
        self.weight_parser.parse_weight.return_value = Mock(grams=250)
        self.integration_service.weight_parser = self.weight_parser
        
        # Mock image services
        self.integration_service.image_deduplication_service = Mock()
        self.integration_service.imagekit_integration = Mock()
        
        # Mock all C story parser services (C.3, C.4, C.5, C.6, C.7, C.8)
        self.integration_service.grind_parser = Mock()
        self.integration_service.species_parser = Mock()
        self.integration_service.variety_parser = Mock()
        self.integration_service.geographic_parser = Mock()
        self.integration_service.sensory_parser = Mock()
        self.integration_service.content_hash_service = Mock()
        self.integration_service.text_cleaner = Mock()
        
        # Mock config for existing services only
        self.validator_config.enable_image_deduplication = False
        self.validator_config.enable_imagekit_upload = False
        # Note: C story config fields will be added when those stories are implemented
        
        # Create ArtifactMapper with mocked integration service
        self.artifact_mapper = ArtifactMapper(integration_service=self.integration_service)
    
    def create_test_artifact_with_tags_and_notes(self):
        """Create a test artifact with tags and notes for testing."""
        from src.validator.models import ArtifactModel, ProductModel, VariantModel, NormalizationModel, AuditModel, ImageModel
        from src.validator.models import SourceEnum, PlatformEnum, WeightUnitEnum, RoastLevelEnum, ProcessEnum, SpeciesEnum
        from datetime import datetime, timezone
        
        # Create test variant
        variant = VariantModel(
            platform_variant_id="var-123",
            sku="SKU123",
            title="250g Whole Bean",
            price="24.99",
            price_decimal=24.99,
            currency="USD",
            compare_at_price="29.99",
            compare_at_price_decimal=29.99,
            in_stock=True,
            grams=250,
            weight_unit=WeightUnitEnum.GRAMS
        )
        
        # Create test product
        product = ProductModel(
            platform_product_id="prod-123",
            platform=PlatformEnum.SHOPIFY,
            title="Premium Coffee from Karnataka",
            handle="premium-coffee",
            slug="premium-coffee",
            description_md="# Premium Coffee\nTasting notes: This coffee has chocolate and caramel flavors.",
            source_url="https://test.com/coffee",
            variants=[variant]
        )
        
        # Create test normalization
        normalization = NormalizationModel(
            is_coffee=True,
            content_hash="hash123",
            name_clean="Premium Coffee",
            description_md_clean="# Premium Coffee\nTasting notes: This coffee has chocolate and caramel flavors.",
            roast_level_enum=RoastLevelEnum.MEDIUM,
            roast_level_raw="Medium Roast",
            process_enum=ProcessEnum.WASHED,
            process_raw="Fully Washed",
            bean_species=SpeciesEnum.ARABICA,
            varieties=["Bourbon"],
            region="Karnataka",
            country="India",
            altitude_m=1200
        )
        
        # Create test audit
        audit = AuditModel(
            artifact_id="artifact-123",
            created_at=datetime.now(timezone.utc),
            collected_by="test-collector"
        )
        
        # Create test artifact
        artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test.com",
            scraped_at=datetime.now(timezone.utc),
            product=product,
            normalization=normalization,
            audit=audit
        )
        
        return artifact
    
    def test_artifact_mapper_initialization(self):
        """Test ArtifactMapper initialization with parser services."""
        assert self.artifact_mapper is not None
        assert self.artifact_mapper.weight_parser is not None
        assert self.artifact_mapper.deduplication_service is not None
        assert self.artifact_mapper.imagekit_integration is not None
    
    def test_extract_and_normalize_tags_success(self):
        """Test successful tag extraction and normalization."""
        # Mock product data
        product = Mock()
        product.platform_product_id = "test_product_123"
        product.title = "Premium Coffee from Karnataka"
        product.description_html = "<p>This coffee has chocolate and caramel flavors.</p>"
        product.description_md = "This coffee has chocolate and caramel flavors."
        
        # Test tag extraction
        result = self.artifact_mapper._extract_and_normalize_tags(product)
        
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(tag, str) for tag in result)
    
    def test_extract_and_normalize_tags_no_tags(self):
        """Test tag extraction when no meaningful tags are found."""
        # Mock product data with no meaningful tags
        product = Mock()
        product.platform_product_id = "test_product_123"
        product.title = "Item"
        product.description_html = "<p>This is an item.</p>"
        product.description_md = "This is an item."
        
        # Test tag extraction
        result = self.artifact_mapper._extract_and_normalize_tags(product)
        
        assert result is None or len(result) == 0
    
    def test_extract_and_normalize_tags_error_handling(self):
        """Test tag extraction error handling."""
        # Mock product data that will cause an error
        product = Mock()
        product.platform_product_id = "test_product_123"
        product.title = None
        product.description_html = None
        product.description_md = None
        
        # Test tag extraction with error handling
        result = self.artifact_mapper._extract_and_normalize_tags(product)
        
        assert result is None
    
    def test_extract_notes_from_description_success(self):
        """Test successful notes extraction from description."""
        # Mock product data
        product = Mock()
        product.platform_product_id = "test_product_123"
        product.description_html = "<p>Tasting notes: This coffee has chocolate and caramel flavors with a smooth finish.</p>"
        product.description_md = "Tasting notes: This coffee has chocolate and caramel flavors with a smooth finish."
        
        # Test notes extraction
        result = self.artifact_mapper._extract_notes_from_description(product)
        
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(note, str) for note in result)
    
    def test_extract_notes_from_description_no_notes(self):
        """Test notes extraction when no notes are found."""
        # Mock product data with no tasting notes
        product = Mock()
        product.platform_product_id = "test_product_123"
        product.description_html = "<p>This is a regular product description.</p>"
        product.description_md = "This is a regular product description."
        
        # Test notes extraction
        result = self.artifact_mapper._extract_notes_from_description(product)
        
        assert result is None or len(result) == 0
    
    def test_extract_notes_from_description_error_handling(self):
        """Test notes extraction error handling."""
        # Mock product data that will cause an error
        product = Mock()
        product.platform_product_id = "test_product_123"
        product.description_html = None
        product.description_md = None
        
        # Test notes extraction with error handling
        result = self.artifact_mapper._extract_notes_from_description(product)
        
        assert result is None
    
    def test_map_coffee_data_with_tags_and_notes(self):
        """Test mapping coffee data with tags and notes."""
        # Create proper test artifact
        artifact = self.create_test_artifact_with_tags_and_notes()

        # Test mapping
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact, 
            roaster_id="roaster_123", 
            metadata_only=False
        )
        
        assert result is not None
        assert 'coffee' in result
        assert 'variants' in result
        assert 'prices' in result
    
    def test_map_coffee_data_without_tags_and_notes(self):
        """Test mapping coffee data without tags and notes."""
        # Create simple test artifact
        artifact = self.create_test_artifact_with_tags_and_notes()
        artifact.product.title = "Simple Coffee"
        artifact.product.description_md = "This is a simple coffee."
        artifact.normalization.description_md_clean = "This is a simple coffee."
        
        # Test mapping
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact, 
            roaster_id="roaster_123", 
            metadata_only=False
        )
        
        assert result is not None
        assert 'coffee' in result
        assert 'variants' in result
        assert 'prices' in result
    
    def test_map_coffee_data_with_disabled_services(self):
        """Test mapping coffee data with disabled parser services."""
        # Create integration service with disabled parser services
        disabled_integration_service = Mock(spec=ValidatorIntegrationService)
        disabled_integration_service.config = ValidatorConfig(
            enable_tag_normalization=False,
            enable_notes_extraction=False,
            enable_image_deduplication=False,
            enable_imagekit_upload=False
        )
        disabled_integration_service.tag_normalization_service = None
        disabled_integration_service.notes_extraction_service = None
        disabled_integration_service.image_deduplication_service = None
        disabled_integration_service.imagekit_integration = None
        disabled_integration_service.grind_parser = None
        disabled_integration_service.species_parser = None
        disabled_integration_service.variety_parser = None
        disabled_integration_service.geographic_parser = None
        disabled_integration_service.sensory_parser = None
        disabled_integration_service.content_hash_service = None
        disabled_integration_service.text_cleaner = None
        
        # Create ArtifactMapper with disabled services
        artifact_mapper = ArtifactMapper(integration_service=disabled_integration_service)
        
        # Create test artifact
        artifact = self.create_test_artifact_with_tags_and_notes()
        
        # Test mapping
        result = artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact, 
            roaster_id="roaster_123", 
            metadata_only=False
        )
        
        assert result is not None
        assert 'coffee' in result
        assert 'variants' in result
        assert 'prices' in result
    
    def test_map_coffee_data_performance(self):
        """Test performance of mapping coffee data with parser services."""
        import time
        
        # Create test artifact
        artifact = self.create_test_artifact_with_tags_and_notes()
        
        # Measure performance
        start_time = time.time()
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact, 
            roaster_id="roaster_123", 
            metadata_only=False
        )
        end_time = time.time()
        
        assert result is not None
        assert 'coffee' in result
        assert 'variants' in result
        assert 'prices' in result
        
        # Verify performance is reasonable (less than 1 second)
        execution_time = end_time - start_time
        assert execution_time < 1.0
    
    def test_map_coffee_data_error_handling(self):
        """Test error handling in mapping coffee data."""
        # Mock product data that will cause an error
        product = Mock()
        product.platform_product_id = "test_product_123"
        product.title = None
        product.description_html = None
        product.description_md = None
        product.bean_species = None
        product.name = None
        product.slug = None
        product.roaster_id = None
        product.process = None
        product.process_raw = None
        product.roast_level = None
        product.roast_level_raw = None
        product.roast_style_raw = None
        product.description_md = None
        product.direct_buy_url = None
        product.decaf = None
        product.notes_raw = None
        product.source_raw = None
        product.status = None
        
        # Mock RPC client
        with patch('src.validator.rpc_client.RPCClient') as mock_rpc_client:
            mock_rpc_instance = Mock()
            mock_rpc_instance.upsert_coffee.side_effect = Exception("RPC error")
            mock_rpc_client.return_value = mock_rpc_instance
            
            # Test error handling
            with pytest.raises(Exception):
                self.artifact_mapper._map_coffee_data(product)
    
    def test_map_coffee_data_integration(self):
        """Test end-to-end integration of mapping coffee data."""
        # Create test artifact
        artifact = self.create_test_artifact_with_tags_and_notes()
        artifact.product.description_md = "Tasting notes: This coffee has chocolate and caramel flavors with a smooth finish."
        artifact.normalization.description_md_clean = "Tasting notes: This coffee has chocolate and caramel flavors with a smooth finish."
        
        # Test end-to-end mapping
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact, 
            roaster_id="roaster_123", 
            metadata_only=False
        )
        
        assert result is not None
        assert 'coffee' in result
        assert 'variants' in result
        assert 'prices' in result
    
    def test_artifact_mapper_logging(self):
        """Test logging in ArtifactMapper enhancement."""
        # Mock product data
        product = Mock()
        product.platform_product_id = "test_product_123"
        product.title = "Premium Coffee from Karnataka"
        product.description_html = "<p>Tasting notes: This coffee has chocolate and caramel flavors.</p>"
        product.description_md = "Tasting notes: This coffee has chocolate and caramel flavors."
        
        # Test logging for tag extraction
        with patch('src.validator.artifact_mapper.logger') as mock_logger:
            result = self.artifact_mapper._extract_and_normalize_tags(product)
            
            # Verify logging was called
            mock_logger.info.assert_called()
            mock_logger.warning.assert_not_called()
        
        # Test logging for notes extraction
        with patch('src.validator.artifact_mapper.logger') as mock_logger:
            result = self.artifact_mapper._extract_notes_from_description(product)
            
            # Verify logging was called
            mock_logger.info.assert_called()
            mock_logger.warning.assert_not_called()
    
    def test_artifact_mapper_configuration(self):
        """Test ArtifactMapper configuration handling."""
        # Test with different configurations
        configs = [
            ValidatorConfig(enable_tag_normalization=True, enable_notes_extraction=True),
            ValidatorConfig(enable_tag_normalization=True, enable_notes_extraction=False),
            ValidatorConfig(enable_tag_normalization=False, enable_notes_extraction=True),
            ValidatorConfig(enable_tag_normalization=False, enable_notes_extraction=False)
        ]
        
        for config in configs:
            integration_service = Mock(spec=ValidatorIntegrationService)
            integration_service.config = config
            integration_service.tag_normalization_service = TagNormalizationService() if config.enable_tag_normalization else None
            integration_service.notes_extraction_service = NotesExtractionService() if config.enable_notes_extraction else None
            integration_service.image_deduplication_service = Mock() if hasattr(config, 'enable_image_deduplication') and config.enable_image_deduplication else None
            integration_service.imagekit_integration = Mock() if hasattr(config, 'enable_imagekit_upload') and config.enable_imagekit_upload else None
            integration_service.grind_parser = Mock() if hasattr(config, 'enable_grind_parsing') and config.enable_grind_parsing else None
            integration_service.species_parser = Mock() if hasattr(config, 'enable_species_parsing') and config.enable_species_parsing else None
            integration_service.variety_parser = Mock() if hasattr(config, 'enable_variety_parsing') and config.enable_variety_parsing else None
            integration_service.geographic_parser = Mock() if hasattr(config, 'enable_geographic_parsing') and config.enable_geographic_parsing else None
            integration_service.sensory_parser = Mock() if hasattr(config, 'enable_sensory_parsing') and config.enable_sensory_parsing else None
            integration_service.content_hash_service = Mock() if hasattr(config, 'enable_content_hash') and config.enable_content_hash else None
            integration_service.text_cleaner = Mock() if hasattr(config, 'enable_text_cleaning') and config.enable_text_cleaning else None
            
            artifact_mapper = ArtifactMapper(integration_service=integration_service)
            assert artifact_mapper is not None
            assert artifact_mapper.weight_parser is not None
