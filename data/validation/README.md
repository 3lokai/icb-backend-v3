# Sample Data Validation System

This directory contains tools to validate your extraction logic against known sample data from Shopify and WooCommerce stores.

## 📁 Directory Structure

```
data/
├── samples/
│   ├── shopify/                    # Shopify sample data
│   │   └── bluetokaicoffee-shopify.json
│   ├── woocommerce/               # WooCommerce sample data
│   │   └── bababeans-woocommerce.json
│   └── normalized/                # Expected normalized outputs
├── fixtures/                      # Test fixtures and configurations
├── validation/                    # Validation tools and scripts
│   ├── sample-validation.py      # Main validation script
│   ├── sample-analysis.py        # Data analysis script
│   └── README.md                 # This file
```

## 🚀 Quick Start

### 1. Analyze Your Sample Data

```bash
cd data/validation
python sample-analysis.py
```

This will show you:
- Total products vs coffee products
- Product types and categories
- Price ranges
- Missing fields
- Top tags

### 2. Validate Your Extraction Logic

```bash
cd data/validation
python sample-validation.py
```

This will test your extraction logic against the sample data and report:
- Expected vs actual coffee product counts
- Data structure validation
- Missing required fields

## 📊 Sample Data Insights

### Blue Tokai (Shopify)
- **Total Products**: ~200+
- **Product Types**: Single Estate Coffee, Equipment, Training, Subscriptions, Gifts
- **Coffee Products**: ~40-50% of total
- **Key Features**: Variants, detailed descriptions, multiple images

### Baba Beans (WooCommerce)
- **Total Products**: ~100+
- **Categories**: COLD BREW, Coffee, Equipment
- **Coffee Products**: ~60-70% of total
- **Key Features**: Detailed attributes, variations, rich descriptions

## 🔧 Adding New Sample Data

### 1. Collect Sample Data

```bash
# For Shopify stores
curl "https://store.myshopify.com/products.json?limit=250" > data/samples/shopify/store-name-shopify.json

# For WooCommerce stores
curl "https://store.com/wp-json/wc/store/products?per_page=100" > data/samples/woocommerce/store-name-woocommerce.json
```

### 2. Update Validation Logic

Edit `sample-validation.py` to add any new validation rules specific to your sample data.

### 3. Run Validation

```bash
python sample-validation.py
```

## 🎯 Validation Goals

### Quality Assurance
- ✅ Ensure extraction logic works with real data
- ✅ Validate data structure completeness
- ✅ Test edge cases and error handling
- ✅ Monitor extraction accuracy over time

### Development Benefits
- 🔧 Offline development without hitting live APIs
- 🧪 Consistent test data for reliable tests
- 📈 Performance benchmarking
- 📚 Documentation of expected data formats

### Continuous Improvement
- 🔄 Automated regression testing
- 📊 Quality metrics tracking
- 🚨 Alert on extraction quality drops
- 📝 Sample data versioning

## 🛠️ Integration with Your Pipeline

### 1. Pre-Processing Validation

Before running extraction on new stores, validate against known good samples:

```python
from data.validation.sample_validation import SampleValidator

validator = SampleValidator(Path("data/samples"))
results = validator.run_all_validations()

if any(not result.passed for result in results):
    print("⚠️ Validation failed - check extraction logic")
```

### 2. Quality Monitoring

Add validation to your CI/CD pipeline:

```yaml
# .github/workflows/validate.yml
- name: Validate Sample Data
  run: |
    cd data/validation
    python sample-validation.py
```

### 3. Performance Testing

Use samples to benchmark extraction performance:

```python
import time
from data.validation.sample_validation import SampleValidator

validator = SampleValidator(Path("data/samples"))
start_time = time.time()
results = validator.run_all_validations()
end_time = time.time()

print(f"Validation took {end_time - start_time:.2f} seconds")
```

## 📈 Expected Outcomes

### For Blue Tokai (Shopify)
- **Coffee Products**: 80-120 products
- **Product Types**: Single Estate Coffee, Producer Series
- **Price Range**: ₹200-₹2000+
- **Variants**: 1-10 per product

### For Baba Beans (WooCommerce)
- **Coffee Products**: 60-80 products
- **Categories**: COLD BREW, Coffee
- **Price Range**: ₹100-₹1000+
- **Variations**: 1-20 per product

## 🔍 Troubleshooting

### Common Issues

1. **Missing Required Fields**
   - Check if sample data structure matches expected format
   - Update validation logic for new field requirements

2. **Coffee Classification Errors**
   - Review `_is_coffee_product()` logic
   - Add new coffee keywords or product types

3. **Performance Issues**
   - Sample files too large? Consider chunking
   - Too many validation rules? Optimize logic

### Debug Mode

Add debug logging to validation scripts:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Contributing

When adding new sample data:

1. **Document the source**: Add comments about store and collection date
2. **Validate structure**: Ensure it matches expected format
3. **Update tests**: Add specific validation rules if needed
4. **Version control**: Keep sample data in git for reproducibility

## 🎯 Next Steps

1. **Add more sample stores** for better coverage
2. **Create normalized output samples** for end-to-end testing
3. **Add performance benchmarks** for extraction speed
4. **Integrate with CI/CD** for automated validation
5. **Create visual dashboards** for quality metrics
