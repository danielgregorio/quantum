# Feature Structure Specification

**Version:** 1.0.0
**Date:** 2025-01-01
**Status:** 📐 Technical Specification

---

## 🎯 Purpose

This document provides the complete technical specification for the feature-based folder structure in Quantum Language. It defines:
- Exact directory layout
- File naming conventions
- Required and optional files
- Content templates
- Integration contracts
- Migration procedures

---

## 📁 Directory Structure

### Root Layout

```
src/core/features/
├── README.md                    # Features overview
├── REGISTRY.yaml                # Central intent registry
├── templates/                   # Templates for new features
│   ├── primary.intent.template
│   ├── manifest.yaml.template
│   └── ast_node.py.template
│
├── {feature_name}/              # Individual feature (see detailed structure below)
│   ├── src/
│   ├── intentions/
│   ├── dataset/
│   ├── tests/
│   ├── docs/
│   └── manifest.yaml
│
├── state_management/            # Example: State Management (q:set)
├── loops/                       # Example: Loops (q:loop)
├── conditionals/                # Example: Conditionals (q:if/q:else)
├── functions/                   # Example: Functions (q:function)
├── databinding/                 # Example: Databinding ({variable})
└── validation/                  # Example: Validation
```

---

## 🗂️ Feature Directory Structure

### Complete Layout for Single Feature

```
{feature_name}/
│
├── manifest.yaml                # Feature metadata (REQUIRED)
│
├── src/                         # Implementation code (REQUIRED)
│   ├── __init__.py             # Feature exports
│   ├── ast_node.py             # AST node definition
│   ├── parser.py               # Parser logic
│   └── runtime.py              # Runtime execution
│
├── intentions/                  # Semantic goals (REQUIRED)
│   ├── primary.intent          # Main intention definition
│   ├── variants.intent         # Common usage patterns (optional)
│   └── edge_cases.intent       # Boundary conditions (optional)
│
├── dataset/                     # Training/evaluation data (REQUIRED)
│   ├── positive/               # Valid usage examples
│   │   ├── simple.json
│   │   ├── complex.json
│   │   └── real_world.json
│   ├── negative/               # Invalid examples
│   │   ├── invalid_syntax.json
│   │   ├── missing_required.json
│   │   └── type_mismatch.json
│   └── metadata.json           # Dataset statistics
│
├── tests/                       # Unit/integration tests (REQUIRED)
│   ├── __init__.py
│   ├── test_ast_node.py        # AST node tests
│   ├── test_parser.py          # Parser tests
│   ├── test_runtime.py         # Runtime tests
│   └── test_integration.py     # End-to-end tests
│
└── docs/                        # Documentation (REQUIRED)
    ├── README.md               # Feature overview
    ├── api.md                  # API reference
    ├── examples.md             # Usage examples
    └── rationale.md            # Design decisions
```

---

## 📋 File Specifications

### 1. manifest.yaml (REQUIRED)

**Purpose:** Feature metadata and dependencies
**Location:** `{feature_name}/manifest.yaml`

**Required Fields:**
```yaml
feature:
  name: string                   # Unique feature identifier (snake_case)
  display_name: string           # Human-readable name
  version: string                # Semantic version (e.g., "1.0.0")
  status: enum                   # stable | beta | experimental | deprecated

description: string              # Multi-line feature description

tags: array[string]              # Searchable tags

maintainers: array[string]       # Responsible developers

dependencies:
  required: array                # Required features
    - feature: string
      version: string            # Version constraint (e.g., ">=1.0.0")
      reason: string

  optional: array                # Optional features
    - feature: string
      version: string
      reason: string

capabilities:
  syntax: array[string]          # What syntax is provided
  runtime: array[string]         # What runtime capabilities

api:
  ast_node: string               # AST node class name
  parser: string                 # Parser method path
  runtime: string                # Runtime method path

testing:
  unit_tests: number             # Count of unit tests
  integration_tests: number      # Count of integration tests
  coverage: number               # Coverage percentage (0-100)

documentation:
  guide: string                  # Path to guide doc
  api: string                    # Path to API doc
  examples: string               # Path to examples doc

metrics:
  lines_of_code: number
  complexity: enum               # low | medium | high
  performance: string            # Big-O or description
```

**Example:**
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

  optional:
    - feature: "validation"
      version: ">=1.0.0"
      reason: "Integrates with QuantumValidators"

capabilities:
  syntax:
    - "Variable declaration with types"
    - "Operations (assign, increment, add, etc.)"
  runtime:
    - "Variable creation and updates"
    - "Type checking"
    - "Validation enforcement"

api:
  ast_node: "SetNode"
  parser: "src/state_management/parser.py::parse_set"
  runtime: "src/state_management/runtime.py::execute_set"

testing:
  unit_tests: 15
  integration_tests: 8
  coverage: 95

documentation:
  guide: "docs/guide/state-management.md"
  api: "docs/api/q-set.md"
  examples: "docs/examples/state-management.md"

metrics:
  lines_of_code: 450
  complexity: "medium"
  performance: "O(1) for variable operations"
```

---

### 2. intentions/primary.intent (REQUIRED)

**Purpose:** Machine-readable intention definition
**Format:** YAML
**Location:** `{feature_name}/intentions/primary.intent`

**Required Sections:**
```yaml
intention:
  name: string                   # Feature name
  version: string                # Intention version
  category: string               # Feature category

  goal: string                   # High-level purpose (multi-line)
  why: string                    # Rationale (multi-line)

  capabilities: array[string]    # User-facing capabilities

  examples: array                # Natural language examples
    - intent: string             # What user wants to do
      usage: string              # Quantum code example

  syntax:                        # Formal syntax specification
    tag: string                  # XML tag name
    attributes: array
      - name: string
        type: string
        required: boolean
        description: string
        values: array            # For enum types
        default: any             # Default value

  constraints: array[string]     # Behavioral constraints

  dependencies: array            # Feature dependencies
    - feature: string
      reason: string

  future: array[string]          # Future enhancements
```

**Template Available:** `templates/primary.intent.template`

---

### 3. intentions/variants.intent (OPTIONAL)

**Purpose:** Document common usage patterns
**Format:** YAML

```yaml
variants:
  - name: string                 # Variant name
    pattern: string              # Code pattern template
    frequency: enum              # high | medium | low
    use_case: string             # When to use this variant
    examples: array[string]      # Concrete examples
```

---

### 4. intentions/edge_cases.intent (OPTIONAL)

**Purpose:** Define boundary conditions and expected behavior
**Format:** YAML

```yaml
edge_cases:
  - name: string                 # Edge case name
    scenario: string             # Description of scenario
    expected_behavior: string    # What should happen
    test_case: string            # Quantum code example
    expected_error: string       # If error expected
```

---

### 5. dataset/positive/{name}.json (REQUIRED)

**Purpose:** Valid usage examples for training
**Format:** JSON

```json
{
  "dataset_type": "positive",
  "feature": "feature_name",
  "version": "1.0.0",
  "examples": [
    {
      "id": "unique-id",
      "intent": "Natural language description",
      "input": {
        "natural_language": "User's intent",
        "context": {
          "available_vars": [],
          "scope": "component"
        }
      },
      "expected_output": {
        "quantum_code": "<q:tag ... />",
        "ast": {
          "type": "NodeType",
          "attributes": {}
        }
      },
      "metadata": {
        "difficulty": "easy|medium|hard",
        "tags": []
      }
    }
  ]
}
```

**Naming Conventions:**
- `simple.json` - Basic usage (5-10 examples)
- `complex.json` - Advanced usage (5-10 examples)
- `real_world.json` - Real-world scenarios (5-10 examples)

---

### 6. dataset/negative/{name}.json (REQUIRED)

**Purpose:** Invalid examples showing error handling
**Format:** JSON

```json
{
  "dataset_type": "negative",
  "feature": "feature_name",
  "version": "1.0.0",
  "examples": [
    {
      "id": "error-unique-id",
      "intent": "What user tried to do",
      "input": {
        "natural_language": "User's misguided intent",
        "attempted_code": "<q:tag ... />"
      },
      "expected_error": {
        "type": "ErrorType",
        "message": "Error message"
      },
      "correction": {
        "quantum_code": "<q:tag ... />",
        "explanation": "Why this is correct"
      },
      "metadata": {
        "error_category": "missing_required|type_mismatch|...",
        "severity": "high|medium|low"
      }
    }
  ]
}
```

**Naming Conventions:**
- `invalid_syntax.json` - Syntax errors
- `missing_required.json` - Missing required attributes
- `type_mismatch.json` - Type compatibility errors

---

### 7. dataset/metadata.json (REQUIRED)

**Purpose:** Dataset statistics and coverage metrics
**Format:** JSON

```json
{
  "feature": "feature_name",
  "version": "1.0.0",
  "statistics": {
    "total_examples": 45,
    "positive_examples": 30,
    "negative_examples": 15,
    "difficulty_distribution": {
      "easy": 15,
      "medium": 20,
      "hard": 10
    }
  },
  "coverage": {
    "operations": {},
    "types": {},
    "attributes": {}
  },
  "last_updated": "YYYY-MM-DD",
  "contributors": []
}
```

---

### 8. src/__init__.py (REQUIRED)

**Purpose:** Feature exports and public API
**Format:** Python

```python
"""
{Feature Display Name}

{Brief description}
"""

from .ast_node import {NodeClass}
from .parser import parse_{feature}
from .runtime import execute_{feature}

__all__ = [
    '{NodeClass}',
    'parse_{feature}',
    'execute_{feature}'
]

__version__ = '1.0.0'
```

---

### 9. src/ast_node.py (REQUIRED)

**Purpose:** AST node class definition
**Format:** Python
**Requirements:**
- Use `@dataclass` decorator
- Inherit from `QuantumNode` (or appropriate base)
- Include all attributes from intention syntax spec
- Implement `to_dict()` method
- Include type hints
- Include docstring

```python
"""
AST Node for {Feature Name}
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from ...ast_nodes import QuantumNode

@dataclass
class {NodeClass}(QuantumNode):
    """
    Represents a {feature description}

    Attributes:
        attr1: Description
        attr2: Description
    """

    attr1: str
    attr2: Optional[str] = None
    attr3: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation"""
        return {
            "type": "{NodeClass}",
            "attr1": self.attr1,
            "attr2": self.attr2,
            "attr3": self.attr3
        }
```

---

### 10. src/parser.py (REQUIRED)

**Purpose:** Parser logic for feature syntax
**Format:** Python
**Requirements:**
- Parse XML element to AST node
- Validate required attributes
- Handle optional attributes with defaults
- Raise descriptive errors
- Include type hints
- Include docstring

```python
"""
Parser for {Feature Name}
"""

from typing import Any
from xml.etree.ElementTree import Element
from .ast_node import {NodeClass}
from ...parser import QuantumParser

def parse_{feature}(element: Element, parser: QuantumParser) -> {NodeClass}:
    """
    Parse <q:{tag}> element into {NodeClass}

    Args:
        element: XML element to parse
        parser: Parser instance for recursive parsing

    Returns:
        {NodeClass} instance

    Raises:
        ParseError: If required attributes missing or invalid
    """

    # Validate required attributes
    if 'required_attr' not in element.attrib:
        raise ParseError(f"Missing required attribute 'required_attr' in <q:{tag}>")

    # Parse attributes
    attr1 = element.attrib['attr1']
    attr2 = element.attrib.get('attr2', default_value)

    # Parse children if needed
    children = [parser.parse_element(child) for child in element]

    return {NodeClass}(
        attr1=attr1,
        attr2=attr2,
        children=children
    )
```

---

### 11. src/runtime.py (REQUIRED)

**Purpose:** Runtime execution logic
**Format:** Python
**Requirements:**
- Execute AST node
- Use ExecutionContext for variables
- Apply databinding to expressions
- Handle all operations from intention
- Validate inputs
- Return appropriate results
- Include type hints
- Include docstring

```python
"""
Runtime execution for {Feature Name}
"""

from typing import Any, Dict
from .ast_node import {NodeClass}
from ...runtime.execution_context import ExecutionContext

def execute_{feature}(
    node: {NodeClass},
    context: Dict[str, Any],
    exec_context: ExecutionContext
) -> Any:
    """
    Execute {NodeClass}

    Args:
        node: AST node to execute
        context: Variable context
        exec_context: Execution context for scope management

    Returns:
        Execution result

    Raises:
        RuntimeError: If execution fails
    """

    # Apply databinding to attributes
    value = apply_databinding(node.value, context)

    # Execute operation
    if node.operation == 'example':
        result = perform_operation(value)
    else:
        raise RuntimeError(f"Unknown operation: {node.operation}")

    return result
```

---

### 12. tests/test_*.py (REQUIRED)

**Purpose:** Automated tests
**Format:** Python (pytest)
**Required Files:**
- `test_ast_node.py` - Test node creation and serialization
- `test_parser.py` - Test XML parsing
- `test_runtime.py` - Test execution logic
- `test_integration.py` - End-to-end tests

**Requirements:**
- Use pytest framework
- Test all examples from dataset
- Include positive and negative tests
- Use parametrize for similar tests
- Assert exact expected outputs
- Achieve >90% code coverage

```python
"""
Tests for {Feature Name}
"""

import pytest
from src.core.features.{feature}.src.parser import parse_{feature}
from src.core.features.{feature}.src.runtime import execute_{feature}

class TestParser:
    def test_parse_simple(self):
        """Test basic parsing"""
        # Arrange
        xml = '<q:{tag} attr="value" />'

        # Act
        node = parse_{feature}(xml)

        # Assert
        assert node.attr == "value"

    @pytest.mark.parametrize("xml,expected_error", [
        ('<q:{tag} />', "Missing required attribute"),
        ('<q:{tag} attr="invalid" />', "Invalid value"),
    ])
    def test_parse_errors(self, xml, expected_error):
        """Test error handling"""
        with pytest.raises(ParseError, match=expected_error):
            parse_{feature}(xml)

class TestRuntime:
    def test_execute_simple(self):
        """Test basic execution"""
        # Test implementation
        pass
```

---

### 13. docs/README.md (REQUIRED)

**Purpose:** Feature overview for users
**Format:** Markdown
**Sections:**
1. Overview - What the feature does
2. Quick Start - Minimal working example
3. Use Cases - When to use this feature
4. See Also - Links to other docs

```markdown
# {Feature Display Name}

## Overview
{Brief description of what this feature does and why it's useful}

## Quick Start

```xml
<q:{tag} attr="value">
  <!-- Example usage -->
</q:{tag}>
```

## Use Cases

- **Use Case 1**: Description
- **Use Case 2**: Description

## See Also

- [API Reference](api.md)
- [Examples](examples.md)
- [Design Rationale](rationale.md)
```

---

### 14. docs/api.md (REQUIRED)

**Purpose:** Complete API reference
**Format:** Markdown
**Sections:**
1. Syntax - XML tag and attributes
2. Attributes - Detailed attribute documentation
3. Return Value - What the feature produces
4. Errors - Possible errors and causes

---

### 15. docs/examples.md (REQUIRED)

**Purpose:** Usage examples
**Format:** Markdown
**Content:** Copy examples directly from intention file and dataset

---

### 16. docs/rationale.md (OPTIONAL but RECOMMENDED)

**Purpose:** Design decisions and tradeoffs
**Format:** Markdown
**Content:**
- Why certain design choices were made
- Alternative approaches considered
- Tradeoffs and limitations
- Future evolution plans

---

## 🔗 Integration Points

### Registry Integration

Every feature MUST be registered in `src/core/features/REGISTRY.yaml`:

```yaml
features:
  - name: "{feature_name}"
    semantic_tags: [...]
    capabilities: [...]
    path: "features/{feature_name}"
    intention_file: "features/{feature_name}/intentions/primary.intent"
```

### Parser Integration

Parser must recognize feature tag:

```python
# In main parser.py
from .features.{feature_name}.src.parser import parse_{feature}

def parse_element(self, element: Element):
    if element.tag == 'q:{tag}':
        return parse_{feature}(element, self)
    # ... other tags
```

### Runtime Integration

Runtime must execute feature nodes:

```python
# In main component.py
from .features.{feature_name}.src.runtime import execute_{feature}

def execute_node(self, node, context, exec_context):
    if isinstance(node, {NodeClass}):
        return execute_{feature}(node, context, exec_context)
    # ... other nodes
```

---

## 🚀 Migration Procedure

### Migrating Existing Feature

1. **Create Feature Folder**
   ```bash
   mkdir -p src/core/features/{feature_name}/{src,intentions,dataset,tests,docs}
   ```

2. **Move Existing Code**
   ```bash
   # Move AST node
   mv src/core/ast_nodes.py::NodeClass → src/core/features/{feature}/src/ast_node.py

   # Move parser logic
   mv src/core/parser.py::parse_method → src/core/features/{feature}/src/parser.py

   # Move runtime logic
   mv src/runtime/component.py::execute_method → src/core/features/{feature}/src/runtime.py
   ```

3. **Create Intention File**
   - Start from template
   - Document existing behavior
   - Extract examples from existing tests

4. **Build Dataset**
   - Convert existing tests to dataset format
   - Add 10-15 positive examples
   - Add 5-10 negative examples

5. **Write Manifest**
   - Document dependencies
   - Calculate metrics
   - List capabilities

6. **Create Documentation**
   - Extract from existing docs if available
   - Generate from intentions if not

7. **Update Registry**
   - Add entry to REGISTRY.yaml

8. **Update Imports**
   - Update parser imports
   - Update runtime imports
   - Update test imports

9. **Run Tests**
   ```bash
   python test_runner.py --feature {feature_name}
   ```

10. **Verify Integration**
    ```bash
    python test_runner.py  # Full regression
    ```

---

## ✅ Validation Checklist

Before considering a feature complete:

- [ ] manifest.yaml exists and is valid
- [ ] intentions/primary.intent complete with all sections
- [ ] Dataset has 20+ examples (15 positive, 5 negative)
- [ ] dataset/metadata.json accurate
- [ ] src/__init__.py exports public API
- [ ] src/ast_node.py has proper docstrings and type hints
- [ ] src/parser.py handles all attributes
- [ ] src/runtime.py executes all operations
- [ ] tests/ has 15+ test cases
- [ ] Code coverage >90%
- [ ] docs/README.md clear and concise
- [ ] docs/api.md complete
- [ ] docs/examples.md has 5+ examples
- [ ] Registered in REGISTRY.yaml
- [ ] Integrated with main parser
- [ ] Integrated with main runtime
- [ ] All tests pass (feature + regression)

---

## 📐 Naming Conventions

### Feature Names
- **snake_case** for directory names
- Examples: `state_management`, `loops`, `conditionals`

### File Names
- **snake_case** for Python files
- **kebab-case** for markdown files
- Examples: `ast_node.py`, `api-reference.md`

### Class Names
- **PascalCase** for classes
- Examples: `SetNode`, `LoopNode`

### Function Names
- **snake_case** for functions
- Prefix with action: `parse_`, `execute_`, `validate_`
- Examples: `parse_set`, `execute_loop`

### Test Names
- **snake_case** with descriptive names
- Prefix: `test_`
- Examples: `test_parse_simple`, `test_execute_with_validation`

---

## 🎨 Code Style

### Python
- Follow PEP 8
- Use type hints (Python 3.7+)
- Include docstrings (Google style)
- Maximum line length: 100 characters
- Use `black` for formatting
- Use `isort` for import sorting

### YAML
- 2-space indentation
- Use `|` for multi-line strings
- Consistent key ordering

### Markdown
- Use ATX-style headers (#)
- Code blocks with language specification
- One sentence per line (for better diffs)

---

## 🔧 Tooling Support

### Linting
```bash
# Python
black src/core/features/{feature}/src/
isort src/core/features/{feature}/src/
mypy src/core/features/{feature}/src/

# YAML
yamllint src/core/features/{feature}/manifest.yaml
```

### Testing
```bash
# Run feature tests
pytest src/core/features/{feature}/tests/ -v --cov

# Run with coverage
pytest --cov=src/core/features/{feature}/src --cov-report=html
```

### Documentation
```bash
# Generate docs
python tools/generate_docs.py {feature_name}

# Preview docs
vitepress dev docs/
```

---

*This specification ensures consistency, maintainability, and LLM-compatibility across all Quantum Language features.*
