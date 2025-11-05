# Data Import Feature - Dataset

This directory contains example `.q` files demonstrating correct and incorrect usage of the `<q:data>` feature.

## Directory Structure

- **positive/** - Valid data import examples that should parse and execute successfully
- **negative/** - Invalid data import examples that should fail validation with specific error messages

## Positive Examples (10 files)

### Basic Data Import
- `data-csv-basic.q` - CSV import with type conversion (integer, string, boolean)
- `data-json-simple.q` - Simple JSON import
- `data-xml-xpath.q` - XML import with XPath field mapping

### Data Transformations
- `data-transform-filter.q` - Filter data based on conditions
- `data-transform-sort.q` - Sort data by field (ascending/descending)
- `data-transform-limit.q` - Limit number of records returned
- `data-transform-compute.q` - Compute derived fields from existing data

### Advanced Features
- `data-http-headers.q` - Import from URL with custom HTTP headers
- `data-cache-ttl.q` - Data caching with TTL (time-to-live)
- `data-result-metadata.q` - Access result metadata (success, recordCount, loadTime)

## Negative Examples (9 files)

### Missing Required Attributes
- `data-missing-name.q` - Missing required 'name' attribute on q:data
- `data-missing-source.q` - Missing required 'source' attribute on q:data
- `data-column-missing-name.q` - Column missing name attribute
- `data-field-missing-name.q` - Field missing name attribute (XML)
- `data-field-missing-xpath.q` - Field missing xpath attribute (XML)
- `data-header-missing-name.q` - HTTP header missing name attribute

### Invalid Transformation Configurations
- `data-filter-missing-condition.q` - Filter without condition
- `data-sort-missing-by.q` - Sort without 'by' field
- `data-limit-missing-value.q` - Limit without value
- `data-compute-missing-field.q` - Compute without field name

## Usage

These examples serve multiple purposes:

1. **Documentation** - Show developers how to use `<q:data>` correctly
2. **Testing** - Provide test cases for parser and runtime validation
3. **Training** - Can be used for LLM fine-tuning on Quantum syntax
4. **Validation** - Ensure error messages are clear and helpful

## Feature Coverage

| Feature | Positive | Negative |
|---------|----------|----------|
| CSV import | ✅ | - |
| JSON import | ✅ | - |
| XML import with XPath | ✅ | - |
| Filter transformation | ✅ | ✅ |
| Sort transformation | ✅ | ✅ |
| Limit transformation | ✅ | ✅ |
| Compute transformation | ✅ | ✅ |
| HTTP headers | ✅ | ✅ |
| Caching/TTL | ✅ | - |
| Result metadata | ✅ | - |
| Missing name | - | ✅ |
| Missing source | - | ✅ |
| Missing column/field attrs | - | ✅ |

## Notes

- CSV examples demonstrate type conversion for integer, string, boolean types
- XML examples use XPath for field extraction (attribute access with @attr, text with text())
- Transformation examples show chaining operations within `<q:transform>`
- HTTP examples show databinding in header values
- Negative examples include expected error messages in comments
