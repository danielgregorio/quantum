# qHTML Phase 1: Template Mixing - Detailed Architecture

**Date:** 2025-11-05
**Status:** 🏗️ Architecture Design
**Goal:** Enable HTML rendering in Quantum components with minimal complexity

---

## 🎯 Objective

Enable developers to write HTML directly in `.q` components, with Quantum tags (loops, conditionals, queries) seamlessly integrated.

**Example:**
```xml
<q:component name="UserProfile">
  <q:query name="user" datasource="db">
    SELECT * FROM users WHERE id = :id
    <q:param name="id" value="{userId}" type="integer" />
  </q:query>

  <div class="profile">
    <h1>{user[0].name}</h1>
    <p>{user[0].email}</p>

    <q:if condition="{user[0].verified}">
      <span class="badge">Verified ✓</span>
    </q:if>
  </div>
</q:component>
```

**Output HTML:**
```html
<div class="profile">
  <h1>John Doe</h1>
  <p>john@example.com</p>
  <span class="badge">Verified ✓</span>
</div>
```

---

## 🏗️ System Architecture

### High-Level Flow

```
.q File → Parser → AST (Mixed HTML + Quantum) → Executor → Renderer → HTML String
```

### Components

1. **Parser** - Parse mixed HTML/Quantum XML
2. **AST Nodes** - Represent HTML elements alongside Quantum nodes
3. **Executor** - Execute Quantum logic (queries, loops, etc.)
4. **Renderer** - Convert executed AST to HTML string
5. **Web Server** - Serve rendered HTML via HTTP

---

## 📦 AST Node Extensions

### New Node Types

**File:** `src/core/ast_nodes.py`

```python
# ============================================
# HTML RENDERING NODES
# ============================================

class HTMLNode(QuantumNode):
    """
    Represents an HTML element that should be passed through to output.

    Examples:
      <div class="container">...</div>
      <img src="/logo.png" />
      <a href="/about">About</a>
    """

    def __init__(
        self,
        tag: str,
        attributes: Optional[Dict[str, str]] = None,
        children: Optional[List[QuantumNode]] = None,
        self_closing: bool = False
    ):
        self.tag = tag
        self.attributes = attributes or {}
        self.children = children or []
        self.self_closing = self_closing or tag in HTML_VOID_ELEMENTS

    def __repr__(self):
        return f'<HTMLNode tag={self.tag} attrs={len(self.attributes)} children={len(self.children)}>'


class TextNode(QuantumNode):
    """
    Represents raw text content, possibly with databinding expressions.

    Examples:
      "Hello World"
      "User: {user.name}"
      "Total: ${price * quantity}"
    """

    def __init__(self, content: str):
        self.content = content
        self.has_databinding = '{' in content and '}' in content

    def __repr__(self):
        preview = self.content[:30] + '...' if len(self.content) > 30 else self.content
        return f'<TextNode "{preview}">'


class DocTypeNode(QuantumNode):
    """
    Represents HTML DOCTYPE declaration.

    Example:
      <!DOCTYPE html>
    """

    def __init__(self, value: str = "html"):
        self.value = value

    def __repr__(self):
        return f'<DocTypeNode {self.value}>'


class CommentNode(QuantumNode):
    """
    Represents HTML/XML comments.

    Example:
      <!-- This is a comment -->
    """

    def __init__(self, content: str):
        self.content = content

    def __repr__(self):
        return f'<CommentNode>'


# HTML void elements (self-closing)
HTML_VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr'
}
```

### Updated ComponentNode

```python
class ComponentNode(QuantumNode):
    """
    Root component - can now contain mixed HTML and Quantum nodes.
    """

    def __init__(self, name: str):
        self.name = name
        self.params = []
        self.body = []  # Can contain HTMLNode, LoopNode, IfNode, etc.
        self.queries = []
        self.functions = []
        # ... existing fields

    def has_html_output(self) -> bool:
        """Check if component produces HTML output"""
        return any(isinstance(node, (HTMLNode, TextNode)) for node in self.body)
```

---

## 🔍 Parser Extensions

### Strategy

The parser needs to distinguish between:
- **Quantum tags** (`q:*` namespace) - Process as Quantum nodes
- **HTML tags** (everything else) - Process as HTML nodes
- **Text content** - Process as text nodes with databinding

### Implementation

**File:** `src/core/parser.py`

```python
class QuantumParser:

    # ... existing methods

    def _parse_component_body(self, component_element: ET.Element) -> List[QuantumNode]:
        """
        Parse component body - can contain mixed HTML and Quantum tags.
        """
        body = []

        # Handle direct text content
        if component_element.text and component_element.text.strip():
            body.append(TextNode(component_element.text))

        # Parse child elements
        for child in component_element:
            node = self._parse_element(child)
            if node:
                body.append(node)

            # Handle tail text (text after element)
            if child.tail and child.tail.strip():
                body.append(TextNode(child.tail))

        return body


    def _parse_element(self, element: ET.Element) -> Optional[QuantumNode]:
        """
        Parse a single element - could be Quantum tag or HTML tag.

        Decision tree:
        - q:query → QueryNode
        - q:loop → LoopNode
        - q:if → IfNode
        - q:set → SetNode
        - q:function → FunctionNode
        - div, span, p, etc → HTMLNode
        """

        tag = element.tag

        # Skip XML namespace declarations
        if tag in ['{https://quantum.lang/ns}component']:
            return None

        # Quantum namespace tags
        if tag.startswith('q:') or tag.startswith('{https://quantum.lang/ns}'):
            # Remove namespace prefix
            clean_tag = tag.replace('{https://quantum.lang/ns}', '').replace('q:', '')
            return self._parse_quantum_tag(clean_tag, element)

        # Special HTML elements
        elif tag == 'DOCTYPE' or element.tag.startswith('!'):
            return self._parse_doctype(element)

        # HTML comments
        elif isinstance(element, ET.Comment):
            return CommentNode(element.text)

        # Regular HTML tags
        else:
            return self._parse_html_element(element)


    def _parse_html_element(self, element: ET.Element) -> HTMLNode:
        """
        Parse HTML element into HTMLNode.
        """

        tag = element.tag
        attributes = {}
        children = []

        # Parse attributes (apply databinding to attribute values)
        for key, value in element.attrib.items():
            attributes[key] = value  # Keep original, renderer will apply databinding

        # Parse text content before first child
        if element.text and element.text.strip():
            children.append(TextNode(element.text))

        # Parse child elements recursively
        for child in element:
            child_node = self._parse_element(child)
            if child_node:
                children.append(child_node)

            # Parse text after child element
            if child.tail and child.tail.strip():
                children.append(TextNode(child.tail))

        return HTMLNode(
            tag=tag,
            attributes=attributes,
            children=children
        )


    def _parse_quantum_tag(self, tag_name: str, element: ET.Element) -> Optional[QuantumNode]:
        """
        Parse Quantum-specific tags.
        """

        if tag_name == 'query':
            return self._parse_query_statement(element)

        elif tag_name == 'loop':
            return self._parse_loop_statement(element)

        elif tag_name == 'if':
            return self._parse_if_statement(element)

        elif tag_name == 'else':
            return ElseNode()

        elif tag_name == 'elseif':
            return self._parse_elseif_statement(element)

        elif tag_name == 'set':
            return self._parse_set_statement(element)

        elif tag_name == 'function':
            return self._parse_function_definition(element)

        elif tag_name == 'return':
            return self._parse_return_statement(element)

        elif tag_name == 'invoke':
            return self._parse_invoke_statement(element)

        elif tag_name == 'dump':
            return self._parse_dump_statement(element)

        elif tag_name == 'log':
            return self._parse_log_statement(element)

        else:
            raise ParseError(f"Unknown Quantum tag: q:{tag_name}")


    def _parse_doctype(self, element: ET.Element) -> DocTypeNode:
        """
        Parse DOCTYPE declaration.
        """
        # <!DOCTYPE html>
        return DocTypeNode("html")
```

---

## 🎨 Renderer Implementation

### Core Renderer

**File:** `src/runtime/renderer.py` (NEW)

```python
"""
Quantum HTML Renderer

Converts executed AST to HTML string output.
"""

from typing import Any, Dict, List
from src.core.ast_nodes import *
from src.runtime.execution_context import ExecutionContext
import html
import re


class HTMLRenderer:
    """
    Renders Quantum AST to HTML string.

    Handles:
    - HTML elements passthrough
    - Databinding replacement
    - Loop expansion
    - Conditional rendering
    - Query result rendering
    """

    def __init__(self, context: ExecutionContext):
        self.context = context


    def render(self, node: QuantumNode) -> str:
        """
        Main render dispatch method.
        """

        if isinstance(node, HTMLNode):
            return self._render_html_node(node)

        elif isinstance(node, TextNode):
            return self._render_text_node(node)

        elif isinstance(node, DocTypeNode):
            return self._render_doctype(node)

        elif isinstance(node, CommentNode):
            return self._render_comment(node)

        elif isinstance(node, ComponentNode):
            return self._render_component(node)

        elif isinstance(node, ReturnNode):
            return str(node.value)  # Simple string return

        # Quantum tags should NOT appear here - they're executed, not rendered
        # Loops/conditions are handled during execution phase
        else:
            return ''


    def render_all(self, nodes: List[QuantumNode]) -> str:
        """
        Render list of nodes.
        """
        return ''.join(self.render(node) for node in nodes)


    def _render_html_node(self, node: HTMLNode) -> str:
        """
        Render HTML element with attributes and children.

        Example:
          HTMLNode(tag='div', attributes={'class': 'container'}, children=[...])
          → <div class="container">...</div>
        """

        # Build opening tag
        tag_parts = [f'<{node.tag}']

        # Add attributes with databinding applied
        for key, value in node.attributes.items():
            # Apply databinding to attribute value
            processed_value = self._apply_databinding(value)
            # Escape for HTML attribute safety
            escaped_value = html.escape(processed_value, quote=True)
            tag_parts.append(f'{key}="{escaped_value}"')

        opening_tag = ' '.join(tag_parts)

        # Self-closing tags
        if node.self_closing:
            return opening_tag + ' />'

        # Regular tags with children
        opening_tag += '>'
        children_html = self.render_all(node.children)
        closing_tag = f'</{node.tag}>'

        return opening_tag + children_html + closing_tag


    def _render_text_node(self, node: TextNode) -> str:
        """
        Render text content with databinding applied.

        Example:
          TextNode("Hello {user.name}!") with context['user.name'] = 'John'
          → "Hello John!"
        """

        text = node.content

        # Apply databinding if needed
        if node.has_databinding:
            text = self._apply_databinding(text)

        # HTML escape to prevent XSS
        # (unless text is explicitly marked as safe HTML)
        return html.escape(text)


    def _render_doctype(self, node: DocTypeNode) -> str:
        """
        Render DOCTYPE declaration.
        """
        return f'<!DOCTYPE {node.value}>'


    def _render_comment(self, node: CommentNode) -> str:
        """
        Render HTML comment.
        """
        return f'<!-- {node.content} -->'


    def _render_component(self, node: ComponentNode) -> str:
        """
        Render entire component body.
        """
        return self.render_all(node.body)


    def _apply_databinding(self, text: str) -> str:
        """
        Replace {variable} and {expression} with actual values from context.

        Examples:
          "{name}" → "John"
          "{user.email}" → "john@example.com"
          "{price * quantity}" → "49.99"
          "{items.length}" → "5"
        """

        def replace_binding(match):
            expression = match.group(1).strip()

            try:
                # Resolve expression from context
                value = self.context.evaluate_expression(expression)
                return str(value) if value is not None else ''

            except Exception as e:
                # If evaluation fails, return original or empty
                return f'{{ERROR: {expression}}}'

        # Find and replace all {expression} patterns
        pattern = r'\{([^}]+)\}'
        result = re.sub(pattern, replace_binding, text)

        return result
```

---

## ⚙️ Executor Integration

The executor (ComponentRuntime) needs small updates to handle HTML nodes.

**File:** `src/runtime/component.py`

```python
class ComponentRuntime:

    # ... existing code

    def _execute_statement(self, node: QuantumNode, context: Dict[str, Any]) -> Any:
        """
        Execute a single AST node.
        """

        # ... existing cases (LoopNode, IfNode, QueryNode, etc.)

        # NEW: HTML nodes are stored for later rendering
        elif isinstance(node, HTMLNode):
            return node  # Pass through to renderer

        elif isinstance(node, TextNode):
            return node  # Pass through to renderer

        elif isinstance(node, DocTypeNode):
            return node  # Pass through to renderer

        elif isinstance(node, CommentNode):
            return node  # Pass through to renderer

        # ... rest of existing code
```

**Key Insight:** HTML nodes are NOT executed, just stored in the AST for the renderer to process later.

---

## 🌐 Web Server Integration

### Flask-based Web Server

**File:** `src/runtime/web_server.py`

```python
"""
Quantum Web Server

Serves .q components as HTML pages via HTTP.
"""

from flask import Flask, request, Response, send_from_directory
from pathlib import Path
from src.core.parser import QuantumParser
from src.runtime.component import ComponentRuntime
from src.runtime.renderer import HTMLRenderer
from src.runtime.execution_context import ExecutionContext
import os

app = Flask(__name__)

# Configuration
COMPONENTS_DIR = os.getenv('QUANTUM_COMPONENTS_DIR', 'components')
STATIC_DIR = os.getenv('QUANTUM_STATIC_DIR', 'static')


@app.route('/')
def index():
    """Default index route"""
    return render_component_file('index')


@app.route('/<path:route_path>')
def dynamic_route(route_path):
    """
    Dynamic routing - maps URLs to .q components.

    Examples:
      /products → components/products.q
      /users/profile → components/users/profile.q
      /api/products → components/api/products.q
    """

    # Try to render as component
    try:
        return render_component_file(route_path)
    except FileNotFoundError:
        return Response("404 - Component not found", status=404)


@app.route('/static/<path:filepath>')
def serve_static(filepath):
    """Serve static files (CSS, JS, images)"""
    return send_from_directory(STATIC_DIR, filepath)


def render_component_file(component_path: str, params: dict = None) -> Response:
    """
    Load, parse, execute, and render a .q component file.

    Args:
        component_path: Path to component (without .q extension)
        params: Optional parameters to pass to component

    Returns:
        Flask Response with rendered HTML
    """

    # Build file path
    file_path = Path(COMPONENTS_DIR) / f'{component_path}.q'

    if not file_path.exists():
        raise FileNotFoundError(f"Component not found: {file_path}")

    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse to AST
    parser = QuantumParser()
    ast = parser.parse(content)

    # Create execution context
    context = ExecutionContext()

    # Add request parameters to context
    if params:
        context.set_variable('params', params, scope='component')

    # Add query parameters from URL
    query_params = dict(request.args)
    if query_params:
        context.set_variable('query', query_params, scope='component')

    # Execute component (runs queries, loops, functions, etc.)
    runtime = ComponentRuntime(context)
    runtime.execute(ast)

    # Render to HTML
    renderer = HTMLRenderer(context)
    html = renderer.render(ast)

    return Response(html, mimetype='text/html')


def start_server(host='0.0.0.0', port=8080, debug=True):
    """
    Start the Quantum web server.
    """
    print(f"🚀 Quantum Web Server starting on http://{host}:{port}")
    print(f"📁 Components directory: {COMPONENTS_DIR}")
    print(f"📦 Static files directory: {STATIC_DIR}")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    start_server()
```

---

## 📁 Project Structure After Implementation

```
quantum/
├── src/
│   ├── core/
│   │   ├── ast_nodes.py         # [MODIFIED] Add HTMLNode, TextNode, DocTypeNode
│   │   └── parser.py            # [MODIFIED] Add HTML parsing
│   │
│   └── runtime/
│       ├── component.py         # [MODIFIED] Handle HTML nodes
│       ├── renderer.py          # [NEW] HTML renderer
│       └── web_server.py        # [NEW] Flask web server
│
├── components/                   # [NEW] .q component files for web
│   ├── index.q
│   ├── products.q
│   └── users/
│       └── profile.q
│
├── static/                      # [NEW] Static assets
│   ├── css/
│   ├── js/
│   └── images/
│
└── examples/
    └── html-rendering/          # [NEW] HTML rendering examples
        ├── simple-page.q
        ├── products-list.q
        └── user-profile.q
```

---

## 🧪 Test Cases

### Test 1: Simple HTML Passthrough
**File:** `examples/html-rendering/test-simple.q`

```xml
<q:component name="SimpleHTML">
  <div>
    <h1>Hello World</h1>
    <p>This is a paragraph.</p>
  </div>
</q:component>
```

**Expected Output:**
```html
<div>
  <h1>Hello World</h1>
  <p>This is a paragraph.</p>
</div>
```

---

### Test 2: Databinding in HTML
**File:** `examples/html-rendering/test-databinding.q`

```xml
<q:component name="DatabindingTest">
  <q:set name="username" value="Alice" />
  <q:set name="age" value="25" />

  <div class="profile">
    <h1>Welcome, {username}!</h1>
    <p>You are {age} years old.</p>
  </div>
</q:component>
```

**Expected Output:**
```html
<div class="profile">
  <h1>Welcome, Alice!</h1>
  <p>You are 25 years old.</p>
</div>
```

---

### Test 3: Loop Rendering
**File:** `examples/html-rendering/test-loop.q`

```xml
<q:component name="LoopTest">
  <q:set name="fruits" type="array" value="['Apple', 'Banana', 'Orange']" />

  <ul>
    <q:loop items="{fruits}" var="fruit" type="array">
      <li>{fruit}</li>
    </q:loop>
  </ul>
</q:component>
```

**Expected Output:**
```html
<ul>
  <li>Apple</li>
  <li>Banana</li>
  <li>Orange</li>
</ul>
```

---

### Test 4: Conditional Rendering
**File:** `examples/html-rendering/test-conditional.q`

```xml
<q:component name="ConditionalTest">
  <q:set name="isLoggedIn" type="boolean" value="true" />
  <q:set name="username" value="Alice" />

  <div>
    <q:if condition="{isLoggedIn}">
      <p>Welcome back, {username}!</p>
    <q:else>
      <p>Please log in.</p>
    </q:if>
  </div>
</q:component>
```

**Expected Output:**
```html
<div>
  <p>Welcome back, Alice!</p>
</div>
```

---

### Test 5: Query + Loop Integration
**File:** `examples/html-rendering/test-query-loop.q`

```xml
<q:component name="ProductsList">
  <q:query name="products" datasource="db">
    SELECT id, name, price FROM products LIMIT 5
  </q:query>

  <div class="products">
    <h2>Products ({products_result.recordCount})</h2>

    <ul>
      <q:loop items="{products}" var="p" type="array">
        <li>{p.name} - ${p.price}</li>
      </q:loop>
    </ul>
  </div>
</q:component>
```

**Expected Output:**
```html
<div class="products">
  <h2>Products (5)</h2>

  <ul>
    <li>Product A - $19.99</li>
    <li>Product B - $29.99</li>
    <li>Product C - $39.99</li>
    <li>Product D - $49.99</li>
    <li>Product E - $59.99</li>
  </ul>
</div>
```

---

### Test 6: Full Page
**File:** `examples/html-rendering/test-full-page.q`

```xml
<q:component name="FullPage">
  <q:set name="title" value="My Quantum Page" />
  <q:set name="greeting" value="Hello, World!" />

  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/css/main.css">
  </head>
  <body>
    <header>
      <h1>{title}</h1>
    </header>

    <main>
      <p>{greeting}</p>
    </main>

    <footer>
      <p>&copy; 2025 Quantum</p>
    </footer>
  </body>
  </html>
</q:component>
```

**Expected Output:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My Quantum Page</title>
  <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
  <header>
    <h1>My Quantum Page</h1>
  </header>

  <main>
    <p>Hello, World!</p>
  </main>

  <footer>
    <p>&copy; 2025 Quantum</p>
  </footer>
</body>
</html>
```

---

## 🔐 Security Considerations

### 1. XSS Prevention
**Problem:** User input could inject malicious HTML/JavaScript

**Solution:**
```python
import html

def _render_text_node(self, node: TextNode) -> str:
    text = self._apply_databinding(node.content)
    return html.escape(text)  # Escapes <, >, &, ", '
```

### 2. SQL Injection
**Already Solved:** q:query uses parameterized queries

### 3. Path Traversal
**Problem:** URLs like `/../../etc/passwd` could access arbitrary files

**Solution:**
```python
from pathlib import Path

def render_component_file(component_path: str):
    # Normalize path and ensure it's within components directory
    file_path = Path(COMPONENTS_DIR) / f'{component_path}.q'
    file_path = file_path.resolve()

    if not str(file_path).startswith(str(Path(COMPONENTS_DIR).resolve())):
        raise SecurityError("Path traversal detected")
```

---

## 📈 Performance Considerations

### 1. Template Caching (Future)
Cache parsed AST to avoid re-parsing on every request.

```python
# Future optimization
template_cache = {}

def render_component_file(component_path: str):
    if component_path in template_cache:
        ast = template_cache[component_path]
    else:
        ast = parser.parse_file(file_path)
        template_cache[component_path] = ast
```

### 2. Streaming (Future)
For large pages, stream HTML chunks instead of building entire string in memory.

### 3. Static Generation (Future - Phase 2)
Pre-render pages at build time for static content.

---

## ✅ Success Criteria

Phase 1 is complete when:

- ✅ Can write HTML directly in `.q` components
- ✅ Databinding `{variable}` works in HTML text and attributes
- ✅ Loops generate repeated HTML elements
- ✅ Conditionals show/hide HTML sections
- ✅ Web server serves `.q` files as HTML pages
- ✅ Query results can be rendered in HTML
- ✅ All 6 test cases passing
- ✅ XSS protection implemented
- ✅ Documentation written

---

## 🚀 Implementation Timeline

### Day 1: AST + Parser
- [ ] Add HTMLNode, TextNode, DocTypeNode, CommentNode to ast_nodes.py
- [ ] Add HTML_VOID_ELEMENTS constant
- [ ] Update QuantumParser with _parse_html_element()
- [ ] Update _parse_element() to route to HTML vs Quantum
- [ ] Test: Parser can parse mixed HTML/Quantum files

### Day 2: Renderer
- [ ] Create src/runtime/renderer.py
- [ ] Implement HTMLRenderer class
- [ ] Implement _render_html_node()
- [ ] Implement _render_text_node() with databinding
- [ ] Implement _apply_databinding() with XSS protection
- [ ] Test: Can render simple HTML
- [ ] Test: Databinding replacement works

### Day 3: Web Server + Integration
- [ ] Create src/runtime/web_server.py
- [ ] Implement Flask routes
- [ ] Integrate parser + executor + renderer
- [ ] Add static file serving
- [ ] Create test components
- [ ] Test: Full end-to-end rendering
- [ ] Documentation: Usage guide

---

## 📝 Documentation Needed

1. **User Guide:** How to write HTML in Quantum components
2. **API Reference:** New AST nodes
3. **Examples:** Real-world component examples
4. **Migration Guide:** For developers familiar with ColdFusion

---

**Ready to implement?** Let's start with Day 1! 🚀
