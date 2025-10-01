# Quick Reference: Testing & Validation

## Before Committing Core Changes

```bash
# Run full regression suite
python test_runner.py

# Expected output:
# TOTAL: 45/45 tests passed (100.0%)
# SUCCESS: All tests passed!
```

If anything fails → **DO NOT COMMIT** until fixed!

## Quick Commands

```bash
# Test specific feature after changes
python test_runner.py --feature functions
python test_runner.py --feature loops
python test_runner.py --feature databinding
python test_runner.py --feature state
python test_runner.py --feature validation

# Verbose mode (see stack traces)
python test_runner.py --verbose

# Test individual file
python -c "
import sys; sys.path.insert(0, 'src')
from core.parser import QuantumParser
from runtime.component import ComponentRuntime
ast = QuantumParser().parse_file('examples/test-YOUR-FILE.q')
result = ComponentRuntime().execute_component(ast)
print(result)
"
```

## Files Changed → Features Affected

| Changed File | Run Tests For |
|--------------|---------------|
| `component.py` | ALL |
| `execution_context.py` | functions, loops, state |
| `parser.py` | ALL |
| `ast_nodes.py` | ALL |
| `validators.py` | validation |
| `function_registry.py` | functions |

## What Each Feature Tests

- **conditionals** (7 tests) - `q:if`, `q:else`, `q:elseif`
- **loops** (6 tests) - `q:loop` range/array/list
- **databinding** (4 tests) - `{variable}` syntax
- **state** (8 tests) - `q:set` operations
- **functions** (13 tests) - `q:function` definitions/calls
- **validation** (7 tests) - Built-in validators

## Red Flags (Run Full Suite!)

⚠️ **Changed:**
- Variable resolution logic
- Scope management (local/function/component)
- Databinding expression evaluation
- Loop execution flow
- Function call mechanism
- Type conversion logic

⚠️ **Added:**
- New ExecutionContext method
- New operator in expressions
- New loop type
- New validation rule

## Success Criteria

✓ All 45 tests pass
✓ No new errors introduced
✓ Expected failures still fail correctly
✓ Performance not degraded

## Emergency: Test Failures

1. **Read the error:**
   ```bash
   python test_runner.py --verbose
   ```

2. **Isolate the issue:**
   ```bash
   python test_runner.py --feature <failing-feature>
   ```

3. **Debug specific test:**
   - Read the .q file: `examples/test-failing-file.q`
   - Check what it's supposed to do
   - Add debug prints in `component.py`
   - Run individually (see command above)

4. **Fix the code** (not the test!)
   - Tests define correct behavior
   - Code should match test expectations

5. **Verify fix:**
   ```bash
   python test_runner.py
   ```

## Adding New Feature Tests

1. Create test file: `examples/test-{feature}-{scenario}.q`
2. Add feature to test_runner.py if new feature
3. Run: `python test_runner.py --feature {feature}`
4. Commit test WITH feature code

## Pre-Commit Checklist

- [ ] Ran `python test_runner.py`
- [ ] All 45/45 tests pass
- [ ] No debug prints left in code
- [ ] ROADMAP.md updated (if applicable)
- [ ] New tests added (if new feature)

---

**When in doubt: `python test_runner.py`**
