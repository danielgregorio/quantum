# Quantum Language Architecture

**Last Updated:** 2025-01-01
**Status:** Hybrid Architecture (Legacy + Feature Modules)

---

## 🏗️ Overview

Quantum Language uses a **hybrid architecture** combining legacy monolithic code with modern feature modules.

### Why Hybrid?

We started with rapid prototyping (monolithic) but evolved toward intent-driven development (modular). The hybrid approach allows us to:
- ✅ Keep existing features working (no rewrites needed)
- ✅ Build new features properly from day 1
- ✅ Collect LLM training data (intentions + datasets)
- ✅ Migrate legacy features incrementally with minimal risk

---

## 📦 Architecture Types

### Type 1: Legacy Features (Option C Migration)

**What:** 6 core features built before feature-module architecture
**Status:** Being migrated incrementally
**Approach:** AST only migration (parser & runtime stay in core)

**Migrated:**
1. ✅ `state_management` (q:set) - COMPLETE

**TODO:**
2. `loops` (q:loop)
3. `conditionals` (q:if/q:else)
4. `functions` (q:function)
5. `databinding` ({variable})
6. `validation`

**Structure:**
```
src/core/features/state_management/
├── src/
│   ├── __init__.py
│   └── ast_node.py          ← ONLY AST node migrated
├── intentions/
│   └── primary.intent       ← Intent specification
├── dataset/
│   ├── positive/            ← Training examples
│   └── negative/            ← Error examples
└── manifest.yaml            ← Feature metadata

# Parser & Runtime REMAIN IN CORE:
src/core/parser.py           ← parse_set() method
src/runtime/component.py     ← _execute_set() method

# Import workaround:
src/core/ast_nodes.py:
  from .features.state_management.src.ast_node import SetNode
```

**Why Option C?**
- ⏱️ Fast: 15 minutes per feature
- 🛡️ Safe: 100% tests passing
- 🎯 Achieves goal: Intentions + datasets in place
- 📊 Enables: LLM training data collection
- ♻️ Optional: Full migration can happen later (low priority)

---

### Type 2: New Features (Proper Structure)

**What:** Features built after architecture was established
**Status:** Not yet started
**Approach:** Fully self-contained modules

**Planned:**
- `rest_api` - REST endpoint support
- `database` - Database operations
- `events` - Event handling
- `components` - Component system

**Structure:**
```
src/core/features/rest_api/
├── src/
│   ├── __init__.py
│   ├── ast_node.py          ← AST nodes
│   ├── parser.py            ← Parser logic
│   └── runtime.py           ← Runtime execution
├── intentions/
│   ├── primary.intent
│   ├── variants.intent
│   └── edge_cases.intent
├── dataset/
│   ├── positive/
│   │   ├── simple.json
│   │   └── complex.json
│   └── negative/
│       └── invalid.json
├── tests/
│   ├── test_parser.py
│   ├── test_runtime.py
│   └── test_integration.py
├── docs/
│   ├── README.md
│   ├── api.md
│   └── examples.md
└── manifest.yaml

# Clean integration:
src/core/parser.py:
  from .features.rest_api.src import RestEndpointNode, parse_rest_endpoint

src/runtime/component.py:
  from ..core.features.rest_api.src import execute_rest_endpoint
```

**Benefits:**
- 🎨 Clean: No legacy baggage
- 📦 Self-contained: Everything in one place
- 🤖 LLM-ready: Intentions + datasets from day 1
- ✅ Tested: Feature-specific test suites
- 📖 Documented: Complete docs alongside code

---

## 🎯 Decision Matrix

| Question | Answer | Action |
|----------|--------|--------|
| Is this a NEW feature? | Yes | Use Type 2 (proper structure) |
| Is this an EXISTING feature? | Yes, already migrated | Use as-is |
| Is this an EXISTING feature? | Yes, not migrated yet | Migrate with Option C |

---

## 📊 Current State

### Codebase Statistics

**Migrated Features:** 1/6 (17%)
**New Features:** 0
**Total Features:** 6 active

**Test Coverage:**
- Total tests: 45
- Pass rate: 100%
- Feature-based tests: 8 (state_management)

**Intentions:**
- state_management: ✅ Complete
- Others: 📝 To be written

**Datasets:**
- state_management: 4 examples
- Others: 0

---

## 🚀 Migration Roadmap

### Phase 1: Legacy Migration (Option C)
**Timeline:** 1-2 weeks
**Effort:** ~15 mins per feature

- [x] state_management - COMPLETE ✅
- [ ] loops
- [ ] conditionals
- [ ] functions
- [ ] databinding
- [ ] validation

### Phase 2: New Feature Development
**Timeline:** Ongoing
**Approach:** Proper structure from day 1

- [ ] rest_api
- [ ] database
- [ ] events
- [ ] components

### Phase 3: Dataset Collection
**Timeline:** Continuous
**Goal:** 500+ examples for LLM training

---

## 💡 Design Decisions

### Why NOT Full Migration (Option A)?

**Option A would require:**
- Extract parser logic (30-50 lines per feature)
- Extract runtime logic (90+ lines per feature)
- Update dozens of imports
- Risk breaking tests
- **Time:** 2-4 hours per feature × 6 = 12-24 hours
- **Risk:** High

**Option C achieves the same goals:**
- Feature structure exists ✅
- Intentions can be written ✅
- Datasets can be created ✅
- LLM training enabled ✅
- **Time:** 15 mins per feature × 6 = 90 mins
- **Risk:** Very low (just imports)

**Return on Investment:**
- Option A: 24 hours effort, marginal benefit
- Option C: 90 mins effort, same functional benefit
- **Savings:** 22.5 hours better spent building new features

### Future: Option A Migration?

Option C features COULD be fully migrated someday, but it's **low priority** because:
- They work perfectly as-is
- No user-facing difference
- Parser/runtime logic is well-tested
- Zero technical debt issues
- Migration effort better spent elsewhere

**Trigger for full migration:**
- Performance issues (unlikely - code is fast)
- Circular dependencies (none exist)
- Team request (would need justification)

---

## 📝 File Organization

### Core Files (Legacy)
```
src/
├── core/
│   ├── ast_nodes.py          # Base classes + imports
│   ├── parser.py             # Main parser + legacy parsing
│   └── features/             # Feature modules
│       ├── state_management/ # Option C migration
│       └── rest_api/         # New feature (future)
│
└── runtime/
    ├── component.py          # Main runtime + legacy execution
    ├── execution_context.py  # Scope management
    ├── function_registry.py  # Function handling
    └── validators.py         # Validation rules
```

### Test Files
```
examples/
├── test-set-*.q              # State management tests
├── test-loop-*.q             # Loop tests
├── test-function-*.q         # Function tests
└── ...

test_runner.py                # Automated regression suite
```

### Documentation
```
docs/
├── guide/                    # User guides
├── api/                      # API reference
└── examples/                 # Code examples

ARCHITECTURE.md               # This file
FEATURE_STRUCTURE_SPEC.md     # Feature structure specification
IMPLEMENTATION_STRATEGY.md    # Phased rollout plan
```

---

## 🔍 Finding Code

### "Where is feature X implemented?"

**For migrated features (Option C):**
```
AST:     src/core/features/{feature}/src/ast_node.py
Parser:  src/core/parser.py (search for parse_{feature})
Runtime: src/runtime/component.py (search for _execute_{feature})
Tests:   examples/test-{feature}-*.q
Docs:    docs/guide/{feature}.md
```

**For new features (proper structure):**
```
AST:     src/core/features/{feature}/src/ast_node.py
Parser:  src/core/features/{feature}/src/parser.py
Runtime: src/core/features/{feature}/src/runtime.py
Tests:   src/core/features/{feature}/tests/
Docs:    src/core/features/{feature}/docs/
```

---

## 🤝 Contributing

### Adding a New Feature

1. **Determine type:**
   - New feature → Use proper structure (Type 2)
   - Existing feature → Migrate with Option C (Type 1)

2. **Follow appropriate guide:**
   - New: See FEATURE_STRUCTURE_SPEC.md
   - Migration: See PILOT_REFACTOR_PLAN.md

3. **Always include:**
   - Intention files
   - Dataset examples
   - Tests
   - Documentation
   - Manifest

4. **Validate:**
   ```bash
   python test_runner.py  # Must stay 100%
   ```

---

## 📈 Success Metrics

**Migration Success:**
- ✅ All tests passing (100%)
- ✅ Intentions documented
- ✅ Datasets created
- ✅ <30 mins per feature

**Overall Success:**
- Target: 500+ dataset examples
- Target: 100% test coverage
- Target: All features with intentions
- Target: Ready for LLM integration

---

## 🔮 Future Vision

### Short Term (1-3 months)
- Complete Option C migration of 6 legacy features
- Build 3-5 new features with proper structure
- Collect 100+ dataset examples

### Medium Term (3-6 months)
- 500+ dataset examples
- LLM integration operational
- Intent-driven development pilot

### Long Term (6-12 months)
- `<q:intent>` tag implementation
- Autonomous code generation
- Self-improving system

---

*This architecture balances pragmatism (keep what works) with vision (build the future right).*
