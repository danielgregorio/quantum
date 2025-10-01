# Feature Implementation Workflow Checklist

Use this checklist for implementing ANY new feature in Quantum Language.

---

## ✅ Phase 1: Pre-Flight Setup

- [ ] **Baseline Check:**
  ```bash
  python test_runner.py
  ```
  Expected: 45/45 tests passed (100%)

- [ ] **Create Feature Branch:**
  ```bash
  git checkout -b feature/{feature-name}
  ```

- [ ] **Verify Clean State:**
  - No uncommitted changes
  - No failing tests
  - All systems operational

---

## ✅ Phase 2: Test-Driven Development

- [ ] **Create Test Files:**
  ```bash
  touch examples/test-{feature}-simple.q
  touch examples/test-{feature}-complex.q
  touch examples/test-{feature}-edge-case.q
  touch examples/test-{feature}-invalid.q  # Expected failure
  ```

- [ ] **Write Test Cases:**
  - [ ] Simple use case (basic functionality)
  - [ ] Complex scenario (real-world usage)
  - [ ] Edge cases (boundaries, empty data, nulls)
  - [ ] Invalid inputs (negative test - should fail)

- [ ] **Register in Test Runner:**
  Edit `test_runner.py` and add:
  ```python
  self.suites['{feature}'] = FeatureTestSuite(
      '{Feature Name}',
      'Description of what this feature does'
  )
  ```

  In `discover_tests()`:
  ```python
  elif filename.startswith('test-{feature}-'):
      self.suites['{feature}'].add_test(filename)
      # Mark invalid tests as expected failures
      if 'invalid' in filename:
          self.suites['{feature}'].expected_failures.append(filename)
  ```

- [ ] **Run Tests (Should Fail):**
  ```bash
  python test_runner.py --feature {feature}
  ```
  Expected: 0/X tests passed (feature not implemented yet)

---

## ✅ Phase 3: Implementation

- [ ] **Create AST Nodes** (if needed):
  - Edit `src/core/ast_nodes.py`
  - Define node class with all attributes
  - Add `to_dict()` method
  - Document attributes with comments

- [ ] **Implement Parser:**
  - Edit `src/core/parser.py`
  - Add parsing method: `_parse_{feature}()`
  - Handle all XML attributes
  - Add to appropriate parent parsing logic

- [ ] **Implement Runtime:**
  - Edit `src/runtime/component.py`
  - Add execution method: `_execute_{feature}()`
  - Handle all operations
  - Integrate with ExecutionContext if needed
  - Add validation if needed

- [ ] **Iterative Testing:**
  Run after each component:
  ```bash
  python test_runner.py --feature {feature}
  ```
  Watch progress: 0/4 → 1/4 → 2/4 → 3/4 → 4/4 ✓

---

## ⚠️ Phase 4: CRITICAL - Regression Validation

- [ ] **Feature Tests Pass:**
  ```bash
  python test_runner.py --feature {feature}
  ```
  Expected: X/X tests passed (100%)

- [ ] **FULL Regression Suite:**
  ```bash
  python test_runner.py
  ```
  **Expected:** ALL tests pass (old + new)

  **If ANY failures occur:**
  - ❌ STOP - Do NOT proceed to documentation
  - 🔍 Investigate what broke
  - 🔧 Fix the regression
  - ♻️ Re-run full suite
  - ✅ Only proceed when 100% pass

- [ ] **Verify No Regressions In:**
  - [ ] Conditionals (q:if, q:else)
  - [ ] Loops (q:loop)
  - [ ] Databinding ({variable})
  - [ ] State Management (q:set)
  - [ ] Functions (q:function)
  - [ ] Validation

---

## ✅ Phase 5: Code Quality

- [ ] **Remove Debug Code:**
  - [ ] Remove all `print()` statements
  - [ ] Remove commented-out code
  - [ ] Remove temporary variables
  - [ ] Remove debug imports

- [ ] **Code Review:**
  - [ ] Check for code duplication
  - [ ] Verify error handling
  - [ ] Check type conversions
  - [ ] Verify scope management
  - [ ] Review performance

- [ ] **Verify Test Coverage:**
  ```bash
  python test_runner.py --feature {feature} --verbose
  ```
  Review test output for completeness

---

## ✅ Phase 6: Impact Analysis

- [ ] **Analyze Impact:**
  Use template from CLAUDE.md:
  - Direct Impact: New/modified components
  - Integration Impact: Parser/runtime changes
  - Breaking Changes: Backwards compatibility
  - Testing Impact: New/updated tests
  - Documentation Impact: What needs docs

- [ ] **Create Impact Analysis Document:**
  ```markdown
  ## Impact Analysis: {Feature Name}

  ### New Components:
  - {list}

  ### Modified Components:
  - {list with line numbers}

  ### Backwards Compatible: Yes/No

  ### Tests Added: X tests

  ### Documentation Needed:
  - {list}
  ```

- [ ] **Present to Daniel:**
  Wait for approval before proceeding

---

## ✅ Phase 7: Documentation (After Approval)

- [ ] **Create Feature Documentation:**
  ```bash
  touch docs/guide/{feature}.md
  ```

- [ ] **Document Structure:**
  - [ ] Overview (what it does, why it's useful)
  - [ ] Syntax (XML tag structure)
  - [ ] Attributes (all parameters explained)
  - [ ] Examples (copy from test files)
  - [ ] Use Cases (real-world scenarios)
  - [ ] Best Practices
  - [ ] Known Limitations

- [ ] **Update Existing Docs:**
  - [ ] Update relevant guides
  - [ ] Add to feature comparison tables
  - [ ] Update examples if needed

- [ ] **Update ROADMAP.md:**
  - [ ] Mark feature as completed
  - [ ] Update completion date
  - [ ] List test coverage
  - [ ] Note any limitations

---

## ✅ Phase 8: Component Revision (If Needed)

If impact analysis revealed affected components:

- [ ] **Update Each Component:**
  - [ ] List affected components
  - [ ] Update implementation
  - [ ] Update tests
  - [ ] Update documentation

- [ ] **Re-test Integration:**
  ```bash
  python test_runner.py
  ```

---

## ✅ Phase 9: Final Validation

- [ ] **Final Regression Check:**
  ```bash
  python test_runner.py
  ```
  Expected: 100% pass rate

- [ ] **Manual Smoke Test:**
  - [ ] Test basic scenario manually
  - [ ] Verify output is correct
  - [ ] Check error messages are clear

- [ ] **Documentation Review:**
  - [ ] Spell check
  - [ ] Code examples work
  - [ ] Links are valid
  - [ ] Formatting is correct

---

## ✅ Phase 10: Git Commit

- [ ] **Stage All Changes:**
  ```bash
  git add src/core/ast_nodes.py        # If modified
  git add src/core/parser.py            # If modified
  git add src/runtime/component.py      # If modified
  git add test_runner.py                # If modified
  git add examples/test-{feature}-*.q   # All test files
  git add docs/guide/{feature}.md       # Documentation
  git add ROADMAP.md                    # Updated roadmap
  ```

- [ ] **Commit with Message:**
  ```bash
  git commit -m "$(cat <<'EOF'
  feat: add {Feature Name} with full documentation

  - Implemented {Feature}Node AST with X attributes
  - Added parser support for <q:{feature}> tags
  - Created runtime execution with Y operations
  - Added Z test files covering all scenarios
  - Created comprehensive VitePress documentation
  - All tests passing: X/X feature + 45/45 regression

  Impact Analysis:
  - New components: {list}
  - Modified: {list}
  - Backwards compatible: Yes/No
  - Breaking changes: None/List

  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  EOF
  )"
  ```

- [ ] **Final Check:**
  ```bash
  git status  # Verify all files staged
  git log -1  # Review commit message
  ```

- [ ] **Push to Remote:**
  ```bash
  git push origin feature/{feature-name}
  ```

---

## 📊 Success Criteria

Your feature is complete when:

✅ All feature tests pass (100%)
✅ Full regression passes (100%)
✅ No regressions introduced
✅ Impact analysis approved by Daniel
✅ Documentation complete
✅ Code committed with proper message
✅ No debug code remains

---

## 🔄 Quick Commands Summary

```bash
# Pre-flight
python test_runner.py

# During development
python test_runner.py --feature {feature}

# Critical regression check
python test_runner.py  # BEFORE documentation

# Final validation
python test_runner.py  # BEFORE commit

# Commit
git add . && git commit -m "feat: add {feature}"
```

---

## ⏱️ Estimated Timeline

- **Phase 1-2 (Setup + Tests):** 30-60 minutes
- **Phase 3 (Implementation):** 2-4 hours (depends on complexity)
- **Phase 4 (Regression):** 5 minutes
- **Phase 5 (Quality):** 30 minutes
- **Phase 6 (Impact):** 30 minutes
- **Phase 7 (Documentation):** 1-2 hours
- **Phase 8 (Revision):** Variable
- **Phase 9 (Validation):** 15 minutes
- **Phase 10 (Commit):** 10 minutes

**Total:** 4-8 hours for typical feature

---

*Use this checklist for EVERY new feature to ensure quality and prevent regressions.*
