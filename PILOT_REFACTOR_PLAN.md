# Pilot Feature Refactoring Plan: State Management

**Date:** 2025-01-01
**Feature:** `state_management` (q:set)
**Status:** 📋 Ready to Execute (When Phase 1 Complete)
**Estimated Duration:** 3-5 days

---

## 🎯 Objectives

1. Migrate `state_management` feature to new folder structure
2. Validate new architecture works in practice
3. Identify and document refactoring challenges
4. Maintain 100% backward compatibility
5. Ensure all tests still pass (45/45)
6. Create reusable migration template

---

## 📊 Current State Analysis

### Existing Implementation

**Files Currently Involved:**

1. **src/core/ast_nodes.py** (Lines 85-105)
   ```python
   @dataclass
   class SetNode(QuantumNode):
       name: str
       type: str = "string"
       value: str = ""
       operation: str = "assign"
       scope: str = "local"
       validate: str = None
       operand: str = None
       transformation: str = None
   ```

2. **src/core/parser.py** (Lines 250-280)
   ```python
   def _parse_set(self, element: Element) -> SetNode:
       """Parse <q:set> element"""
       # ... implementation
   ```

3. **src/runtime/component.py** (Lines 460-550)
   ```python
   def _execute_set(self, set_node: SetNode, context: dict, exec_context: ExecutionContext):
       """Execute q:set statement"""
       # ... implementation (90 lines)
   ```

4. **src/runtime/validators.py** (Used by set)
   ```python
   class QuantumValidators:
       # Validation methods used by q:set
   ```

### Test Coverage

**Existing Test Files:**
- `examples/test-set-simple.q` ✓
- `examples/test-set-increment.q` ✓
- `examples/test-set-add.q` ✓
- `examples/test-set-array-append.q` ✓
- `examples/test-set-string-uppercase.q` ✓
- `examples/test-set-validation-email.q` ✓
- `examples/test-set-validation-email-invalid.q` ✓ (expected failure)
- `examples/test-set-scoped.q` ✓

**Total:** 8 tests, all passing

### Dependencies

**Features that `state_management` depends on:**
- `databinding` - Uses {variable} expressions
- `validation` - Uses QuantumValidators

**Features that depend on `state_management`:**
- `loops` - Uses q:set to update loop variables
- `functions` - Uses q:set for local variables
- All features - Most use q:set in some capacity

### Metrics

**Current Code:**
- AST Node: ~20 lines
- Parser: ~30 lines
- Runtime: ~90 lines
- Total: ~140 lines of feature-specific code

---

## 📁 Target Structure

### New Directory Layout

```
src/core/features/state_management/
│
├── manifest.yaml                     # Feature metadata
│
├── src/                              # Implementation
│   ├── __init__.py                  # Exports
│   ├── ast_node.py                  # SetNode definition
│   ├── parser.py                    # parse_set method
│   └── runtime.py                   # execute_set method
│
├── intentions/                       # Semantic goals
│   ├── primary.intent               # Main intention
│   ├── variants.intent              # Common patterns
│   └── edge_cases.intent            # Boundary conditions
│
├── dataset/                          # Training data
│   ├── positive/
│   │   ├── simple.json              # Basic operations
│   │   ├── complex.json             # Advanced usage
│   │   └── real_world.json          # Practical examples
│   ├── negative/
│   │   ├── invalid_syntax.json      # Parse errors
│   │   ├── missing_required.json    # Validation errors
│   │   └── type_mismatch.json       # Type errors
│   └── metadata.json                # Dataset statistics
│
├── tests/                            # Feature tests
│   ├── __init__.py
│   ├── test_ast_node.py             # Node tests
│   ├── test_parser.py               # Parser tests
│   ├── test_runtime.py              # Runtime tests
│   └── test_integration.py          # End-to-end tests
│
└── docs/                             # Documentation
    ├── README.md                     # Overview
    ├── api.md                        # API reference
    ├── examples.md                   # Usage examples
    └── rationale.md                  # Design decisions
```

---

## 📝 Step-by-Step Execution Plan

### Pre-Refactor Checklist

- [ ] Verify baseline: `python test_runner.py` shows 45/45 ✓
- [ ] Ensure no uncommitted changes: `git status`
- [ ] Create feature branch: `git checkout -b refactor/pilot-state-management`
- [ ] Backup current state: `git tag pre-refactor-pilot`

---

### Step 1: Create Folder Structure

**Commands:**
```bash
# Create main feature directory
mkdir -p src/core/features/state_management

# Create subdirectories
mkdir -p src/core/features/state_management/src
mkdir -p src/core/features/state_management/intentions
mkdir -p src/core/features/state_management/dataset/positive
mkdir -p src/core/features/state_management/dataset/negative
mkdir -p src/core/features/state_management/tests
mkdir -p src/core/features/state_management/docs
```

**Validation:**
```bash
tree src/core/features/state_management
```

**Expected Output:**
```
src/core/features/state_management/
├── dataset
│   ├── negative
│   └── positive
├── docs
├── intentions
├── src
└── tests
```

---

### Step 2: Write Intention Files

**File: `intentions/primary.intent`**

```yaml
intention:
  name: "State Management with q:set"
  version: "1.0.0"
  category: "state"

  goal: |
    Enable developers to declare and manipulate component state variables
    with type safety, validation, and scope management.

  why: |
    Components need to maintain state across their lifecycle.
    State changes should be predictable, type-safe, and traceable.

  capabilities:
    - "Create variables with explicit types"
    - "Update variables with operations (assign, increment, add, etc.)"
    - "Validate values against rules (email, cpf, url, etc.)"
    - "Manage scope (local, function, component, session)"
    - "Transform strings (uppercase, lowercase, trim, etc.)"

  examples:
    - intent: "I want to store a user's email address"
      usage: |
        <q:set name="userEmail" type="string" value="user@example.com" validate="email" />

    - intent: "I want to count items in a loop"
      usage: |
        <q:set name="count" type="number" value="0" />
        <q:loop items="{myArray}" var="item">
          <q:set name="count" operation="increment" />
        </q:loop>

    - intent: "I want to accumulate a total"
      usage: |
        <q:set name="total" type="number" value="0" />
        <q:set name="total" operation="add" value="{price}" />

  syntax:
    tag: "q:set"
    attributes:
      - name: "name"
        type: "string"
        required: true
        description: "Variable name"

      - name: "type"
        type: "enum"
        required: false
        values: ["string", "number", "boolean", "array", "object"]
        default: "string"
        description: "Variable type"

      - name: "value"
        type: "string|expression"
        required: true
        description: "Initial value or databinding expression"

      - name: "operation"
        type: "enum"
        required: false
        values: ["assign", "increment", "decrement", "add", "subtract", "multiply", "divide", "append", "prepend", "uppercase", "lowercase", "trim"]
        description: "Operation to perform"

      - name: "validate"
        type: "string"
        required: false
        description: "Validation rule name"

      - name: "scope"
        type: "enum"
        required: false
        values: ["local", "function", "component", "session"]
        default: "local"
        description: "Variable scope"

  constraints:
    - "Variable name must be valid identifier"
    - "Type must match value format"
    - "Validation rules must exist in QuantumValidators"
    - "Operations must be compatible with type"
    - "Scope must be valid in current context"

  dependencies:
    - feature: "databinding"
      reason: "Expressions use {variable} syntax"

    - feature: "validation"
      reason: "Uses QuantumValidators for validation"

  future:
    - "Add computed properties (derived state)"
    - "Add reactive watchers (onChange handlers)"
    - "Add state persistence (localStorage integration)"
```

**Validation:**
```bash
# Check YAML is valid
python -c "import yaml; yaml.safe_load(open('src/core/features/state_management/intentions/primary.intent'))"
```

---

### Step 3: Build Dataset from Existing Tests

**File: `dataset/positive/simple.json`**

```json
{
  "dataset_type": "positive",
  "feature": "state_management",
  "version": "1.0.0",
  "examples": [
    {
      "id": "set-001",
      "intent": "Create a simple string variable",
      "input": {
        "natural_language": "I want to store a username",
        "context": {
          "available_vars": [],
          "scope": "component"
        }
      },
      "expected_output": {
        "quantum_code": "<q:set name=\"username\" type=\"string\" value=\"JohnDoe\" />",
        "ast": {
          "type": "SetNode",
          "attributes": {
            "name": "username",
            "type": "string",
            "value": "JohnDoe",
            "operation": "assign"
          }
        },
        "result": "username = 'JohnDoe'"
      },
      "metadata": {
        "difficulty": "easy",
        "tags": ["assignment", "string", "simple"],
        "source_test": "examples/test-set-simple.q"
      }
    },
    {
      "id": "set-002",
      "intent": "Increment a counter",
      "input": {
        "natural_language": "I want to count how many items are processed",
        "context": {
          "available_vars": ["count"],
          "scope": "loop"
        }
      },
      "expected_output": {
        "quantum_code": "<q:set name=\"count\" operation=\"increment\" />",
        "ast": {
          "type": "SetNode",
          "attributes": {
            "name": "count",
            "operation": "increment"
          }
        },
        "result": "count += 1"
      },
      "metadata": {
        "difficulty": "easy",
        "tags": ["increment", "counter", "operation"],
        "source_test": "examples/test-set-increment.q"
      }
    }
  ]
}
```

**File: `dataset/negative/invalid_syntax.json`**

```json
{
  "dataset_type": "negative",
  "feature": "state_management",
  "version": "1.0.0",
  "examples": [
    {
      "id": "set-error-001",
      "intent": "Missing required attribute",
      "input": {
        "natural_language": "I want to create a variable",
        "attempted_code": "<q:set value=\"123\" />"
      },
      "expected_error": {
        "type": "ParseError",
        "message": "Missing required attribute 'name'"
      },
      "correction": {
        "quantum_code": "<q:set name=\"myVar\" value=\"123\" />",
        "explanation": "The 'name' attribute is required to identify the variable"
      },
      "metadata": {
        "error_category": "missing_required",
        "severity": "high"
      }
    },
    {
      "id": "set-error-002",
      "intent": "Invalid email validation",
      "input": {
        "natural_language": "I want to store an email with validation",
        "attempted_code": "<q:set name=\"email\" value=\"not-an-email\" validate=\"email\" />"
      },
      "expected_error": {
        "type": "ValidationError",
        "message": "Invalid email format"
      },
      "correction": {
        "quantum_code": "<q:set name=\"email\" value=\"user@example.com\" validate=\"email\" />",
        "explanation": "Email must be in valid format: user@domain.com"
      },
      "metadata": {
        "error_category": "validation_failure",
        "severity": "high",
        "source_test": "examples/test-set-validation-email-invalid.q"
      }
    }
  ]
}
```

**File: `dataset/metadata.json`**

```json
{
  "feature": "state_management",
  "version": "1.0.0",
  "statistics": {
    "total_examples": 20,
    "positive_examples": 15,
    "negative_examples": 5,
    "difficulty_distribution": {
      "easy": 8,
      "medium": 9,
      "hard": 3
    }
  },
  "coverage": {
    "operations": {
      "assign": 5,
      "increment": 3,
      "decrement": 1,
      "add": 2,
      "subtract": 1,
      "append": 2,
      "uppercase": 1
    },
    "types": {
      "string": 8,
      "number": 6,
      "boolean": 1
    },
    "validations": {
      "email": 2,
      "cpf": 1
    }
  },
  "last_updated": "2025-01-01",
  "contributors": ["Claude", "Daniel"]
}
```

---

### Step 4: Extract AST Node

**File: `src/ast_node.py`**

```python
"""
AST Node for State Management (q:set)
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict

# Import from parent ast_nodes.py temporarily
# Later we'll refactor base classes too
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


@dataclass
class SetNode(QuantumNode):
    """
    Represents a <q:set> tag for state management

    State management enables variable creation, updates, and validation
    with proper scope management.

    Attributes:
        name: Variable name (required)
        type: Variable type (string|number|boolean|array|object)
        value: Initial value or expression
        operation: Operation to perform (assign|increment|add|etc.)
        scope: Variable scope (local|function|component|session)
        validate: Validation rule name
        operand: Operand for binary operations
        transformation: String transformation (uppercase|lowercase|trim)
    """

    name: str
    type: str = "string"
    value: str = ""
    operation: str = "assign"
    scope: str = "local"
    validate: Optional[str] = None
    operand: Optional[str] = None
    transformation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation"""
        return {
            "type": "SetNode",
            "name": self.name,
            "var_type": self.type,
            "value": self.value,
            "operation": self.operation,
            "scope": self.scope,
            "validate": self.validate,
            "operand": self.operand,
            "transformation": self.transformation
        }
```

---

### Step 5: Extract Parser Logic

**File: `src/parser.py`**

```python
"""
Parser for State Management (q:set)
"""

from typing import Any
from xml.etree.ElementTree import Element
from .ast_node import SetNode


def parse_set(element: Element, parser: Any) -> SetNode:
    """
    Parse <q:set> element into SetNode

    Args:
        element: XML element to parse
        parser: QuantumParser instance (for recursive parsing if needed)

    Returns:
        SetNode instance

    Raises:
        ParseError: If required attributes missing or invalid

    Example:
        <q:set name="count" type="number" value="0" />
        → SetNode(name="count", type="number", value="0")
    """

    # Validate required attributes
    if 'name' not in element.attrib:
        raise ParseError("Missing required attribute 'name' in <q:set>")

    # Extract attributes
    name = element.attrib['name']
    var_type = element.attrib.get('type', 'string')
    value = element.attrib.get('value', '')
    operation = element.attrib.get('operation', 'assign')
    scope = element.attrib.get('scope', 'local')
    validate = element.attrib.get('validate', None)
    operand = element.attrib.get('operand', None)
    transformation = element.attrib.get('transformation', None)

    # Validate type
    valid_types = ['string', 'number', 'boolean', 'array', 'object']
    if var_type not in valid_types:
        raise ParseError(f"Invalid type '{var_type}'. Must be one of: {valid_types}")

    # Validate operation
    valid_operations = [
        'assign', 'increment', 'decrement', 'add', 'subtract',
        'multiply', 'divide', 'append', 'prepend'
    ]
    if operation not in valid_operations:
        raise ParseError(f"Invalid operation '{operation}'. Must be one of: {valid_operations}")

    return SetNode(
        name=name,
        type=var_type,
        value=value,
        operation=operation,
        scope=scope,
        validate=validate,
        operand=operand,
        transformation=transformation
    )


class ParseError(Exception):
    """Parser error"""
    pass
```

---

### Step 6: Extract Runtime Logic

**File: `src/runtime.py`**

```python
"""
Runtime execution for State Management (q:set)
"""

from typing import Any, Dict
from .ast_node import SetNode

# Import ExecutionContext from main runtime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from runtime.execution_context import ExecutionContext
from runtime.validators import QuantumValidators


def execute_set(
    node: SetNode,
    context: Dict[str, Any],
    exec_context: ExecutionContext,
    databinding_fn: Any
) -> None:
    """
    Execute SetNode - create or update variable

    Args:
        node: SetNode to execute
        context: Variable context dictionary
        exec_context: Execution context for scope management
        databinding_fn: Function to apply databinding to expressions

    Raises:
        RuntimeError: If execution fails
        ValidationError: If validation fails
    """

    # Apply databinding to value
    value = databinding_fn(node.value, context)

    # Type conversion
    if node.type == 'number':
        try:
            value = float(value) if '.' in str(value) else int(value)
        except ValueError:
            raise RuntimeError(f"Cannot convert '{value}' to number")
    elif node.type == 'boolean':
        value = value in ['true', 'True', '1', 1, True]

    # Perform operation
    if node.operation == 'assign':
        result = value

    elif node.operation == 'increment':
        current = exec_context.get_variable(node.name)
        if not isinstance(current, (int, float)):
            raise RuntimeError(f"Cannot increment non-numeric variable '{node.name}'")
        result = current + 1

    elif node.operation == 'decrement':
        current = exec_context.get_variable(node.name)
        if not isinstance(current, (int, float)):
            raise RuntimeError(f"Cannot decrement non-numeric variable '{node.name}'")
        result = current - 1

    elif node.operation == 'add':
        current = exec_context.get_variable(node.name)
        if not isinstance(current, (int, float)):
            raise RuntimeError(f"Cannot add to non-numeric variable '{node.name}'")
        result = current + value

    elif node.operation == 'subtract':
        current = exec_context.get_variable(node.name)
        result = current - value

    elif node.operation == 'multiply':
        current = exec_context.get_variable(node.name)
        result = current * value

    elif node.operation == 'divide':
        current = exec_context.get_variable(node.name)
        if value == 0:
            raise RuntimeError("Division by zero")
        result = current / value

    elif node.operation == 'append':
        current = exec_context.get_variable(node.name)
        if isinstance(current, list):
            result = current + [value]
        elif isinstance(current, str):
            result = current + str(value)
        else:
            raise RuntimeError(f"Cannot append to {type(current)}")

    elif node.operation == 'prepend':
        current = exec_context.get_variable(node.name)
        if isinstance(current, list):
            result = [value] + current
        elif isinstance(current, str):
            result = str(value) + current
        else:
            raise RuntimeError(f"Cannot prepend to {type(current)}")

    else:
        raise RuntimeError(f"Unknown operation: {node.operation}")

    # Apply string transformations
    if node.transformation:
        if not isinstance(result, str):
            raise RuntimeError(f"Cannot apply transformation to {type(result)}")

        if node.transformation == 'uppercase':
            result = result.upper()
        elif node.transformation == 'lowercase':
            result = result.lower()
        elif node.transformation == 'trim':
            result = result.strip()

    # Validation
    if node.validate:
        is_valid, error_msg = QuantumValidators.validate(result, node.validate)
        if not is_valid:
            raise ValidationError(f"Validation failed for '{node.name}': {error_msg}")

    # Determine scope and set variable
    is_update = node.operation in ['increment', 'decrement', 'add', 'subtract', 'multiply', 'divide', 'append', 'prepend']

    if is_update or (exec_context.has_variable(node.name) and node.scope == "local"):
        # Update existing variable
        exec_context.update_variable(node.name, result)
    else:
        # Create new variable
        actual_scope = node.scope
        if node.scope == "local" and exec_context.parent is not None:
            actual_scope = "function"
        exec_context.set_variable(node.name, result, scope=actual_scope)

    # Update context dict for legacy compatibility
    context[node.name] = result


class ValidationError(Exception):
    """Validation error"""
    pass
```

---

### Step 7: Create Feature __init__.py

**File: `src/__init__.py`**

```python
"""
State Management Feature (q:set)

Enables declaration and manipulation of component state variables
with type safety, validation, and scope management.
"""

from .ast_node import SetNode
from .parser import parse_set
from .runtime import execute_set

__all__ = [
    'SetNode',
    'parse_set',
    'execute_set'
]

__version__ = '1.0.0'
```

---

### Step 8: Update Main Parser

**File: `src/core/parser.py`**

```python
# Add at top with other imports
from .features.state_management.src import SetNode, parse_set

class QuantumParser:
    def _parse_element(self, element: Element):
        # ...existing code...

        if element.tag == 'q:set':
            return parse_set(element, self)

        # ... rest of parsing logic
```

---

### Step 9: Update Main Runtime

**File: `src/runtime/component.py`**

```python
# Add at top with other imports
from ..core.features.state_management.src import SetNode, execute_set

class ComponentRuntime:
    def execute_node(self, node, context, exec_context):
        # ...existing code...

        if isinstance(node, SetNode):
            return execute_set(node, context, exec_context, self._apply_databinding)

        # ... rest of execution logic
```

---

### Step 10: Create Feature Tests

**File: `tests/test_parser.py`**

```python
"""
Tests for State Management Parser
"""

import pytest
from ..src.parser import parse_set, ParseError
from ..src.ast_node import SetNode
from xml.etree.ElementTree import Element


class TestSetParser:
    """Test q:set parser"""

    def test_parse_simple_assignment(self):
        """Test basic variable assignment"""
        element = Element('q:set')
        element.set('name', 'username')
        element.set('value', 'JohnDoe')

        node = parse_set(element, None)

        assert isinstance(node, SetNode)
        assert node.name == 'username'
        assert node.value == 'JohnDoe'
        assert node.operation == 'assign'

    def test_parse_with_type(self):
        """Test variable with explicit type"""
        element = Element('q:set')
        element.set('name', 'age')
        element.set('type', 'number')
        element.set('value', '25')

        node = parse_set(element, None)

        assert node.type == 'number'
        assert node.value == '25'

    def test_parse_increment_operation(self):
        """Test increment operation"""
        element = Element('q:set')
        element.set('name', 'count')
        element.set('operation', 'increment')

        node = parse_set(element, None)

        assert node.operation == 'increment'

    def test_parse_with_validation(self):
        """Test variable with validation rule"""
        element = Element('q:set')
        element.set('name', 'email')
        element.set('value', 'user@example.com')
        element.set('validate', 'email')

        node = parse_set(element, None)

        assert node.validate == 'email'

    def test_parse_missing_name_raises_error(self):
        """Test that missing name attribute raises ParseError"""
        element = Element('q:set')
        element.set('value', '123')

        with pytest.raises(ParseError, match="Missing required attribute 'name'"):
            parse_set(element, None)

    def test_parse_invalid_type_raises_error(self):
        """Test that invalid type raises ParseError"""
        element = Element('q:set')
        element.set('name', 'var')
        element.set('type', 'invalid')

        with pytest.raises(ParseError, match="Invalid type"):
            parse_set(element, None)
```

---

### Step 11: Run Tests

```bash
# Run feature-specific tests
pytest src/core/features/state_management/tests/ -v

# Expected output:
# test_parser.py::TestSetParser::test_parse_simple_assignment PASSED
# test_parser.py::TestSetParser::test_parse_with_type PASSED
# ... all tests PASSED

# Run full regression suite
python test_runner.py

# CRITICAL: Must show 45/45 tests passed
```

---

### Step 12: Create Manifest

**File: `manifest.yaml`**

```yaml
feature:
  name: "state_management"
  display_name: "State Management (q:set)"
  version: "1.0.0"
  status: "stable"

description: |
  Enables declaration and manipulation of component state variables
  with type safety, validation, and scope management.

tags:
  - "state"
  - "variables"
  - "data-manipulation"

maintainers:
  - "Daniel"
  - "Claude"

dependencies:
  required:
    - feature: "databinding"
      version: ">=1.0.0"
      reason: "Uses {variable} expressions"

    - feature: "validation"
      version: ">=1.0.0"
      reason: "Uses QuantumValidators"

  optional:
    - feature: "loops"
      version: ">=1.0.0"
      reason: "Often used in loop contexts"

capabilities:
  syntax:
    - "Variable declaration with types"
    - "Value assignment"
    - "Operations (increment, add, etc.)"
    - "Validation rules"
    - "Scope management"

  runtime:
    - "Variable creation"
    - "Type checking"
    - "Operation execution"
    - "Validation enforcement"
    - "Scope resolution"

api:
  ast_node: "SetNode"
  parser: "src/features/state_management/src/parser.py::parse_set"
  runtime: "src/features/state_management/src/runtime.py::execute_set"

testing:
  unit_tests: 15
  integration_tests: 8
  coverage: 95

documentation:
  guide: "docs/guide/state-management.md"
  api: "docs/api/q-set.md"
  examples: "docs/examples/state-management.md"

metrics:
  lines_of_code: 140
  complexity: "medium"
  performance: "O(1) for variable operations"

changelog:
  - version: "1.0.0"
    date: "2025-01-01"
    changes:
      - "Migrated to feature-based structure"
      - "18+ operations supported"
      - "Full validation integration"
      - "Scope management with ExecutionContext"
```

---

### Step 13: Create Documentation

**File: `docs/README.md`**

```markdown
# State Management (q:set)

## Overview

The `<q:set>` tag enables developers to create and manipulate component state variables with type safety, validation, and scope management.

## Quick Start

```xml
<!-- Create a variable -->
<q:set name="username" type="string" value="JohnDoe" />

<!-- Increment a counter -->
<q:set name="count" type="number" value="0" />
<q:set name="count" operation="increment" />

<!-- Validate email -->
<q:set name="email" value="{userInput}" validate="email" />
```

## Use Cases

- **Store component state**: Maintain data across component lifecycle
- **Counter variables**: Track iterations, totals, counts
- **Validated input**: Ensure data quality with built-in validators
- **Scoped variables**: Control variable visibility (local, function, component)

## See Also

- [API Reference](api.md)
- [Examples](examples.md)
- [Design Rationale](rationale.md)
```

---

### Step 14: Register in Registry

**File: `src/core/features/REGISTRY.yaml`**

```yaml
registry_version: "1.0.0"

features:
  - name: "state_management"
    semantic_tags: ["state", "variables", "mutation", "storage"]
    capabilities: ["create variables", "update values", "validate input", "manage scope"]
    path: "features/state_management"
    intention_file: "features/state_management/intentions/primary.intent"
    version: "1.0.0"
    status: "stable"
```

---

### Step 15: Final Validation

```bash
# 1. Run full test suite
python test_runner.py

# Expected: 45/45 tests passed (100%)

# 2. Validate all imports work
python -c "
from src.core.features.state_management.src import SetNode, parse_set, execute_set
print('✓ Imports successful')
"

# 3. Test backward compatibility
for file in examples/test-set-*.q; do
  python -c "
import sys; sys.path.insert(0, 'src')
from core.parser import QuantumParser
from runtime.component import ComponentRuntime
ast = QuantumParser().parse_file('$file')
result = ComponentRuntime().execute_component(ast)
print(f'✓ {$file} works')
  "
done

# 4. Check no broken imports in main files
python -m py_compile src/core/parser.py
python -m py_compile src/runtime/component.py

# 5. Build documentation
cd docs && vitepress build && cd ..
```

---

## 📊 Success Metrics

### Checklist

- [ ] Feature folder structure created
- [ ] Intention files complete (primary, variants, edge cases)
- [ ] Dataset complete (15 positive, 5 negative examples)
- [ ] Dataset metadata accurate
- [ ] AST node extracted and working
- [ ] Parser extracted and working
- [ ] Runtime extracted and working
- [ ] Feature __init__.py exports correct API
- [ ] Main parser updated and working
- [ ] Main runtime updated and working
- [ ] Feature tests created and passing
- [ ] Full regression tests passing (45/45)
- [ ] Manifest complete and accurate
- [ ] Documentation created
- [ ] Registry updated
- [ ] No performance degradation
- [ ] No broken imports
- [ ] Backward compatibility maintained

### Validation Criteria

✅ **Pilot is successful when ALL of these are true:**

1. **Tests:** 45/45 regression tests pass + new feature tests pass
2. **Performance:** No measurable slowdown
3. **Compatibility:** All existing examples work unchanged
4. **Code Quality:** Cleaner code organization than before
5. **Documentation:** Complete and accurate
6. **Intentions:** Comprehensive and useful
7. **Dataset:** 20+ examples ready for LLM training

---

## 🚨 Rollback Plan

### If Problems Occur

**Minor Issues:**
- Fix and re-test
- Document in lessons learned

**Major Issues (Breaking Changes):**
```bash
# Rollback to pre-refactor state
git reset --hard pre-refactor-pilot
git branch -D refactor/pilot-state-management

# Document what went wrong
# Revise strategy
# Try again when ready
```

---

## 📝 Post-Pilot Documentation

### File: `LESSONS_LEARNED.md`

**Template to fill after pilot:**

```markdown
# Lessons Learned: State Management Pilot Refactor

**Date Completed:** YYYY-MM-DD
**Duration:** X days

## What Worked Well
- [List successes]

## What Was Challenging
- [List difficulties]

## What We'd Do Differently
- [List improvements]

## Time/Effort
- Estimated: 3-5 days
- Actual: X days
- Variance: Y%

## Recommendations for Next Feature
- [Actionable advice]

## Surprises/Unexpected Issues
- [Things we didn't anticipate]

## Tools/Scripts That Would Help
- [Automation opportunities]
```

---

## 🎯 Next Steps After Pilot

### If Successful

1. **Create migration template** from pilot experience
2. **Build automation scripts** for repetitive tasks
3. **Update IMPLEMENTATION_STRATEGY.md** with lessons
4. **Proceed to next feature:** databinding or validation
5. **Continue incremental migration**

### If Unsuccessful

1. **Document what went wrong**
2. **Revise folder structure** if needed
3. **Adjust strategy**
4. **Retry when ready**

---

*This pilot refactoring plan ensures we validate the new architecture on a single feature before committing to full migration.*
