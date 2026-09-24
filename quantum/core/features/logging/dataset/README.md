# q:log Feature Dataset

This directory contains comprehensive examples demonstrating correct and incorrect usage of the `<q:log>` feature.

## Directory Structure

- **positive/** - Valid logging examples across multiple pattern categories (50 examples)
- **negative/** - Invalid logging examples that should fail validation (7 examples)

## Positive Examples (50 files)

### Basic Patterns (10 examples)
- `log-01-basic-info.q` - Basic info level logging
- `log-02-basic-error.q` - Basic error level logging
- `log-03-basic-warning.q` - Basic warning level logging
- `log-04-basic-debug.q` - Basic debug level logging
- `log-05-basic-trace.q` - Basic trace level logging
- `log-06-basic-critical.q` - Basic critical level logging
- `log-07-databinding-message.q` - Logging with databinding in message
- `log-08-structured-context.q` - Logging with structured context data
- `log-09-multiple-logs.q` - Multiple log statements in sequence
- `log-10-long-message.q` - Logging with very long message

### Integration Patterns (10 examples)
- `log-11-integration-loop.q` - Logging inside loops
- `log-12-integration-conditional.q` - Conditional logging with q:if
- `log-13-integration-api-result.q` - Logging API result with when attribute
- `log-14-integration-function-call.q` - Logging function execution
- `log-15-integration-data-import.q` - Logging data import results
- `log-16-integration-validation-error.q` - Logging validation errors
- `log-17-integration-nested-loops.q` - Logging in nested loops
- `log-18-integration-event-dispatch.q` - Logging event dispatch
- `log-19-integration-multiple-contexts.q` - Logging with multiple structured contexts
- `log-20-integration-computed-message.q` - Logging with computed message

### Edge Cases (10 examples)
- `log-21-edge-empty-message.q` - Logging with empty message
- `log-22-edge-null-context.q` - Logging with null context
- `log-23-edge-special-chars.q` - Logging with special characters
- `log-24-edge-unicode.q` - Logging with Unicode characters
- `log-25-edge-newlines.q` - Logging with newline characters
- `log-26-edge-large-context.q` - Logging with very large context object
- `log-27-edge-deeply-nested.q` - Logging with deeply nested context
- `log-28-edge-undefined-variable.q` - Logging with undefined variable reference
- `log-29-edge-array-context.q` - Logging with array as context
- `log-30-edge-when-false.q` - Logging with when condition that's false

### Real-World Patterns (10 examples)
- `log-31-realworld-user-login.q` - Real-world user login tracking
- `log-32-realworld-payment-processing.q` - Real-world payment processing log
- `log-33-realworld-api-latency.q` - Real-world API latency monitoring
- `log-34-realworld-data-export.q` - Real-world data export audit log
- `log-35-realworld-security-alert.q` - Real-world security alert logging
- `log-36-realworld-batch-processing.q` - Real-world batch job processing log
- `log-37-realworld-gdpr-compliance.q` - Real-world GDPR compliance audit log
- `log-38-realworld-error-recovery.q` - Real-world error recovery logging
- `log-39-realworld-database-migration.q` - Real-world database migration logging
- `log-40-realworld-cache-invalidation.q` - Real-world cache invalidation logging

### Complex Scenarios (10 examples)
- `log-41-complex-multi-condition.q` - Complex multi-condition logging
- `log-42-complex-transaction-chain.q` - Complex transaction chain logging
- `log-43-complex-aggregation.q` - Complex aggregation with logging
- `log-44-complex-retry-logic.q` - Complex retry logic with logging
- `log-45-complex-distributed-trace.q` - Complex distributed tracing with correlation IDs
- `log-46-complex-performance-metrics.q` - Complex performance metrics collection
- `log-47-complex-multi-service-orchestration.q` - Complex multi-service orchestration logging
- `log-48-complex-data-pipeline.q` - Complex data pipeline with stage logging
- `log-49-complex-conditional-branching.q` - Complex conditional branching with detailed logging
- `log-50-complex-state-machine.q` - Complex state machine with transition logging

## Negative Examples (7 files)

### Missing Required Attributes
- `log-neg-01-missing-level.q` - Missing required 'level' attribute
- `log-neg-02-missing-message.q` - Missing required 'message' attribute

### Invalid Attribute Values
- `log-neg-03-invalid-level.q` - Invalid log level (not one of: trace, debug, info, warning, error, critical)
- `log-neg-04-invalid-when-expression.q` - Invalid 'when' expression syntax
- `log-neg-05-invalid-context-json.q` - Invalid JSON in context attribute
- `log-neg-07-empty-level.q` - Empty level attribute

### Invalid Syntax
- `log-neg-06-self-closing-tag.q` - Log tag with child elements (should be self-closing)

## Usage

These examples serve multiple purposes:

1. **Documentation** - Show developers how to use `<q:log>` correctly
2. **Testing** - Provide test cases for parser and runtime validation
3. **Training** - Can be used for LLM fine-tuning on Quantum syntax
4. **Validation** - Ensure error messages are clear and helpful

## Feature Coverage

| Feature | Positive | Negative |
|---------|----------|----------|
| Log levels (trace, debug, info, warning, error, critical) | ✅ | ✅ |
| Message with databinding | ✅ | - |
| Structured context | ✅ | ✅ |
| Conditional logging (when attribute) | ✅ | ✅ |
| Integration with loops | ✅ | - |
| Integration with conditionals | ✅ | - |
| Integration with API calls | ✅ | - |
| Integration with functions | ✅ | - |
| Integration with data import | ✅ | - |
| Edge cases (empty, null, unicode, special chars) | ✅ | - |
| Real-world patterns (security, audit, performance) | ✅ | - |
| Complex scenarios (multi-condition, distributed tracing) | ✅ | - |
| Missing required attributes | - | ✅ |
| Invalid attribute values | - | ✅ |

## Dataset Statistics

- **Total Examples**: 57
- **Positive Examples**: 50
- **Negative Examples**: 7
- **Coverage Categories**: 5 (Basic, Integration, Edge Cases, Real-World, Complex)
- **Training Readiness**: Production-ready (50+ examples with comprehensive coverage)

## Notes

- All log levels are demonstrated (trace, debug, info, warning, error, critical)
- Examples show integration with all major Quantum features (loops, conditionals, functions, API calls, data import)
- Real-world patterns cover security, compliance, performance monitoring, and audit logging
- Complex scenarios demonstrate distributed tracing, state machines, and multi-service orchestration
- Negative examples include expected error messages in comments
- All examples use proper XML namespace (`xmlns:q="https://quantum.lang/ns"`)
