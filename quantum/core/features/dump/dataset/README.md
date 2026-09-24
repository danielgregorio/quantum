# q:dump Feature Dataset

This directory contains comprehensive examples demonstrating correct and incorrect usage of the `<q:dump>` feature.

## Directory Structure

- **positive/** - Valid variable inspection examples across multiple pattern categories (50 examples)
- **negative/** - Invalid dump examples that should fail validation (7 examples)

## Positive Examples (50 files)

### Basic Patterns (10 examples)
- `dump-01-basic-string.q` - Dump basic string variable
- `dump-02-basic-integer.q` - Dump basic integer variable
- `dump-03-basic-boolean.q` - Dump basic boolean variable
- `dump-04-basic-array.q` - Dump basic array
- `dump-05-basic-object.q` - Dump basic object
- `dump-06-basic-with-label.q` - Dump with label attribute
- `dump-07-basic-null-value.q` - Dump null value
- `dump-08-basic-nested-object.q` - Dump nested object
- `dump-09-basic-multiple-dumps.q` - Multiple dump statements
- `dump-10-basic-format-html.q` - Dump with HTML format

### Integration Patterns (10 examples)
- `dump-11-integration-loop-variables.q` - Dump loop variables
- `dump-12-integration-conditional-dump.q` - Conditional dump with when
- `dump-13-integration-api-response.q` - Dump API response
- `dump-14-integration-function-result.q` - Dump function result
- `dump-15-integration-data-import-result.q` - Dump data import result
- `dump-16-integration-validation-result.q` - Dump validation result
- `dump-17-integration-nested-loop-vars.q` - Dump nested loop variables
- `dump-18-integration-event-data.q` - Dump event data
- `dump-19-integration-all-context-vars.q` - Dump all context variables
- `dump-20-integration-computed-value.q` - Dump computed value

### Edge Cases (10 examples)
- `dump-21-edge-empty-string.q` - Dump empty string
- `dump-22-edge-empty-array.q` - Dump empty array
- `dump-23-edge-empty-object.q` - Dump empty object
- `dump-24-edge-special-chars.q` - Dump special characters
- `dump-25-edge-unicode-chars.q` - Dump Unicode characters
- `dump-26-edge-very-large-array.q` - Dump very large array
- `dump-27-edge-deeply-nested.q` - Dump deeply nested structure
- `dump-28-edge-undefined-var.q` - Dump undefined variable
- `dump-29-edge-mixed-types-array.q` - Dump mixed types array
- `dump-30-edge-depth-limit.q` - Dump with depth limit

### Real-World Patterns (10 examples)
- `dump-31-realworld-debug-api-response.q` - Debug API response structure
- `dump-32-realworld-inspect-session-state.q` - Inspect session state
- `dump-33-realworld-troubleshoot-calculation.q` - Troubleshoot calculation error
- `dump-34-realworld-inspect-query-params.q` - Inspect query parameters
- `dump-35-realworld-debug-validation-failure.q` - Debug validation failure
- `dump-36-realworld-inspect-transformed-data.q` - Inspect data after transformation
- `dump-37-realworld-debug-loop-iteration.q` - Debug specific loop iteration
- `dump-38-realworld-inspect-error-state.q` - Inspect error state object
- `dump-39-realworld-debug-type-conversion.q` - Debug type conversion
- `dump-40-realworld-inspect-aggregated-result.q` - Inspect aggregated result

### Complex Scenarios (10 examples)
- `dump-41-complex-compare-before-after.q` - Compare state before and after transformation
- `dump-42-complex-multiple-format-dumps.q` - Dump same variable in multiple formats
- `dump-43-complex-conditional-depth.q` - Conditional dump with varying depth
- `dump-44-complex-dump-chain-results.q` - Dump results of chained operations
- `dump-45-complex-dump-multi-api-responses.q` - Dump multiple API responses for comparison
- `dump-46-complex-dump-performance-metrics.q` - Dump performance metrics with metadata
- `dump-47-complex-dump-state-machine-transitions.q` - Dump state machine transitions
- `dump-48-complex-dump-nested-loop-data.q` - Dump data from nested loops
- `dump-49-complex-dump-conditional-branches.q` - Dump from different conditional branches
- `dump-50-complex-dump-recursive-structure.q` - Dump recursive data structure

## Negative Examples (7 files)

### Missing Required Attributes
- `dump-neg-01-missing-var.q` - Missing required 'var' attribute
- `dump-neg-02-empty-var.q` - Empty var attribute

### Invalid Attribute Values
- `dump-neg-03-invalid-format.q` - Invalid format (not one of: html, json, text)
- `dump-neg-04-invalid-depth.q` - Invalid depth value (not a number)
- `dump-neg-05-negative-depth.q` - Negative depth value
- `dump-neg-06-invalid-when-expression.q` - Invalid 'when' expression syntax

### Invalid Syntax
- `dump-neg-07-child-elements.q` - Dump tag with child elements (should be self-closing)

## Usage

These examples serve multiple purposes:

1. **Documentation** - Show developers how to use `<q:dump>` correctly
2. **Testing** - Provide test cases for parser and runtime validation
3. **Training** - Can be used for LLM fine-tuning on Quantum syntax
4. **Validation** - Ensure error messages are clear and helpful

## Feature Coverage

| Feature | Positive | Negative |
|---------|----------|----------|
| Dump primitives (string, integer, boolean) | ✅ | - |
| Dump collections (array, object) | ✅ | - |
| Dump with label | ✅ | - |
| Dump with format (html, json, text) | ✅ | ✅ |
| Dump with depth limit | ✅ | ✅ |
| Conditional dumping (when attribute) | ✅ | ✅ |
| Integration with loops | ✅ | - |
| Integration with conditionals | ✅ | - |
| Integration with API calls | ✅ | - |
| Integration with functions | ✅ | - |
| Integration with data import | ✅ | - |
| Edge cases (empty, null, unicode, special chars) | ✅ | - |
| Real-world debugging scenarios | ✅ | - |
| Complex scenarios (comparisons, state tracking) | ✅ | - |
| Missing required attributes | - | ✅ |
| Invalid attribute values | - | ✅ |

## Dataset Statistics

- **Total Examples**: 57
- **Positive Examples**: 50
- **Negative Examples**: 7
- **Coverage Categories**: 5 (Basic, Integration, Edge Cases, Real-World, Complex)
- **Training Readiness**: Production-ready (50+ examples with comprehensive coverage)

## Notes

- All data types are demonstrated (primitives, arrays, objects, null, undefined)
- Examples show integration with all major Quantum features (loops, conditionals, functions, API calls, data import)
- Real-world patterns cover API debugging, state inspection, validation troubleshooting
- Complex scenarios demonstrate before/after comparisons, multi-format output, state machine tracking
- Negative examples include expected error messages in comments
- All examples use proper XML namespace (`xmlns:q="https://quantum.lang/ns"`)
- Format options: html (default, rich formatted), json (structured JSON), text (plain text tree)
- Depth limiting prevents infinite recursion and controls output verbosity
