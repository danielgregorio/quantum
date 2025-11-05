# Invocation Feature - Dataset

This directory contains example `.q` files demonstrating correct and incorrect usage of the `<q:invoke>` feature.

## Directory Structure

- **positive/** - Valid invocation examples that should parse and execute successfully
- **negative/** - Invalid invocation examples that should fail validation with specific error messages

## Positive Examples (10 files)

### Basic Invocations
- `invoke-function-basic.q` - Simple function call with parameters
- `invoke-component-call.q` - Local component invocation

### HTTP/REST Invocations
- `invoke-http-get-simple.q` - Basic HTTP GET request
- `invoke-http-post-json.q` - HTTP POST with JSON body
- `invoke-http-with-headers.q` - Custom headers in HTTP request
- `invoke-query-params.q` - HTTP GET with query parameters

### Authentication
- `invoke-http-bearer-auth.q` - Bearer token authentication

### Advanced Features
- `invoke-http-retry.q` - Retry logic with configurable attempts
- `invoke-http-with-cache.q` - Result caching with TTL
- `invoke-result-metadata.q` - Using result object metadata (success, error, execution_time)

## Negative Examples (9 files)

### Missing Required Attributes
- `invoke-missing-name.q` - Missing required 'name' attribute
- `invoke-no-target.q` - No invocation target specified
- `invoke-header-missing-name.q` - Header missing name attribute
- `invoke-header-missing-value.q` - Header missing value attribute
- `invoke-param-missing-name.q` - Parameter missing name attribute

### Invalid Configurations
- `invoke-multiple-targets.q` - Multiple targets specified (ambiguous)
- `invoke-invalid-method.q` - Invalid HTTP method
- `invoke-invalid-auth-type.q` - Invalid authentication type

### Runtime Errors
- `invoke-function-not-found.q` - Invoking non-existent function

## Usage

These examples serve multiple purposes:

1. **Documentation** - Show developers how to use `<q:invoke>` correctly
2. **Testing** - Provide test cases for parser and runtime validation
3. **Training** - Can be used for LLM fine-tuning on Quantum syntax
4. **Validation** - Ensure error messages are clear and helpful

## Feature Coverage

| Feature | Positive | Negative |
|---------|----------|----------|
| Function invocation | ✅ | ✅ |
| Component invocation | ✅ | - |
| HTTP GET | ✅ | - |
| HTTP POST | ✅ | - |
| Custom headers | ✅ | ✅ |
| Query parameters | ✅ | ✅ |
| Bearer auth | ✅ | - |
| API Key auth | - | - |
| Basic auth | - | - |
| Retry logic | ✅ | - |
| Caching | ✅ | - |
| Result metadata | ✅ | - |
| Method validation | - | ✅ |
| Auth type validation | - | ✅ |
| Target validation | - | ✅ |

## Notes

- HTTP examples use `jsonplaceholder.typicode.com` for testing (public REST API)
- Bearer auth examples use placeholder tokens (not real)
- Negative examples include error comments explaining expected validation errors
