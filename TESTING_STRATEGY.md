# Quantum Language - Testing & Regression Strategy

## Problem Statement

When making architectural or core changes to the Quantum runtime (like the recent ExecutionContext changes for function loops), there's a risk of breaking existing features. We need a systematic way to validate that changes don't introduce regressions.

## Solution: Automated Regression Testing

### 1. Test Organization

Tests are organized by **feature area**:

```
examples/
├── test-conditionals-*.q      # q:if, q:else, q:elseif
├── test-loop-*.q               # q:loop (range, array, list)
├── test-databinding-*.q        # {variable} syntax
├── test-set-*.q                # q:set (state management)
├── test-function-*.q           # q:function (definitions, calls)
└── test-*-validation-*.q       # Validation rules
```

### 2. Test Runner (`test_runner.py`)

**Basic Usage:**
```bash
# Run all tests
python test_runner.py

# Run specific feature
python test_runner.py --feature functions

# Verbose mode
python test_runner.py --verbose
```

**Features:**
- Automatic test discovery and categorization
- Expected failure support (negative tests)
- Detailed error reporting
- Summary by feature area
- Exit code for CI/CD integration

### 3. Test Coverage (45 tests)

| Feature | Tests | Status |
|---------|-------|--------|
| Conditionals | 7 | ✓ 100% |
| Loops | 6 | ✓ 100% |
| Databinding | 4 | ✓ 100% |
| State Management | 8 | ✓ 100% |
| Functions | 13 | ✓ 100% |
| Validation | 7 | ✓ 100% |
| **TOTAL** | **45** | **✓ 100%** |

## Workflow: Making Core Changes

### Before Making Changes

1. **Run baseline tests:**
   ```bash
   python test_runner.py
   ```
   Ensure all tests pass (100%)

2. **Identify affected features:**
   - ExecutionContext changes → affects: functions, loops, state
   - Databinding changes → affects: all features
   - Parser changes → affects: specific tags

### During Development

3. **Make incremental changes:**
   - Change one component at a time
   - Run relevant feature tests after each change:
     ```bash
     python test_runner.py --feature functions
     ```

4. **Add new tests:**
   - Create test-{feature}-{scenario}.q for new functionality
   - Add both positive and negative tests

### After Changes

5. **Run full regression suite:**
   ```bash
   python test_runner.py
   ```

6. **If tests fail:**
   - Check if it's an expected failure (marked in test runner)
   - Review error messages
   - Use `--verbose` flag for stack traces
   - Fix code or update tests

7. **Document changes:**
   - Update ROADMAP.md
   - Note which features were affected
   - List test coverage

## Test Categories

### 1. Positive Tests
Tests that should **succeed** and return expected output.

**Example:** `test-function-simple.q`
```xml
<q:function name="add" returnType="number">
  <q:param name="a" type="number" required="true" />
  <q:param name="b" type="number" required="true" />
  <q:return value="{a + b}" />
</q:function>
```
Expected: Returns sum of two numbers

### 2. Negative Tests (Expected Failures)
Tests that should **fail** with specific errors.

**Example:** `test-set-validation-email-invalid.q`
```xml
<q:set name="email" type="string" value="not-an-email" validate="email" />
```
Expected: ValidationError - "Invalid email format"

**Naming Convention:** Include `-invalid` or `-error` in filename

### 3. Edge Cases
Tests for boundary conditions:
- Empty arrays/lists
- Null values
- Maximum/minimum values
- Nested structures (loops in loops, functions calling functions)

## CI/CD Integration

The test runner returns proper exit codes:
- `0` - All tests passed
- `1` - One or more tests failed

**Example GitHub Actions workflow:**
```yaml
name: Regression Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Run regression tests
        run: python test_runner.py
```

## Recent Validation Example

**Change:** Fixed ExecutionContext usage in function loops (2025-01-01)

**Affected Areas:**
- Loop execution inside functions
- Variable scoping (local vs function scope)
- Databinding in loop contexts

**Test Results:**
- Before: 13/13 function tests passing
- After changes: 13/13 function tests passing ✓
- Full suite: 45/45 tests passing ✓

**What This Validates:**
- Loops still work at component level
- Databinding still resolves variables correctly
- State management still updates variables
- Functions still call correctly
- Validation still works

## Recommendations

### When to Run Full Regression

**Always run before:**
- Committing core changes
- Merging pull requests
- Releasing new versions

**Always run after changing:**
- `component.py` - Core runtime execution
- `execution_context.py` - Variable scoping
- `parser.py` - XML parsing
- `ast_nodes.py` - AST structure
- `validators.py` - Validation rules

### Adding New Features

When adding a new feature:

1. **Create test files first** (TDD approach):
   ```
   examples/test-{feature}-simple.q
   examples/test-{feature}-complex.q
   examples/test-{feature}-edge-case.q
   examples/test-{feature}-invalid.q  # Negative test
   ```

2. **Register in test_runner.py:**
   ```python
   self.suites['new-feature'] = FeatureTestSuite(
       'New Feature',
       'Description of what this feature does'
   )
   ```

3. **Run tests while developing:**
   ```bash
   python test_runner.py --feature new-feature
   ```

### Debugging Failed Tests

**1. Use verbose mode:**
```bash
python test_runner.py --verbose
```

**2. Run individual test:**
```bash
python -c "
import sys
sys.path.insert(0, 'src')
from core.parser import QuantumParser
from runtime.component import ComponentRuntime

ast = QuantumParser().parse_file('examples/test-failing.q')
result = ComponentRuntime().execute_component(ast)
print(f'Result: {result}')
"
```

**3. Add debug output in component.py:**
```python
print(f'[DEBUG] Variable: {name}, Value: {value}, Scope: {scope}')
```

## Metrics & Goals

**Current Coverage:**
- ✓ 45 test files
- ✓ 6 feature areas
- ✓ 100% pass rate
- ✓ ~200 lines of test infrastructure

**Future Goals:**
- Add performance benchmarks
- Add memory leak detection
- Add concurrency tests (when async is implemented)
- Add integration tests with external systems
- Target: 80+ tests covering all features

## Conclusion

This testing strategy ensures:
1. **Confidence** - Make changes knowing you won't break existing features
2. **Speed** - Automated tests run in seconds
3. **Documentation** - Tests serve as usage examples
4. **Quality** - Catch regressions before users do

**Bottom Line:** Always run `python test_runner.py` before committing core changes!
