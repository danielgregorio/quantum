# qHTML Rendering Options - Quantum Language

**Date:** 2025-11-05
**Status:** 🎯 Analysis & Proposal
**Problem:** Quantum needs a way to render/integrate with HTML for web applications

---

## 🎯 Current Situation

### What We Have
- ✅ XML-based component system (`.q` files)
- ✅ Databinding `{variable}` expressions
- ✅ Control structures (loops, conditionals, functions)
- ✅ Database queries (`q:query`)
- ✅ Component runtime that executes AST

### What We're Missing
- ❌ HTML output/rendering capability
- ❌ Web server integration
- ❌ Page composition from components
- ❌ Client-side interactivity

### Current Component Example
```xml
<q:component name="HelloWorld">
  <q:return value="Hello World!" />
</q:component>
```
**Output:** Just a string - no HTML, no web page

---

## 🔍 Rendering Options Analysis

### Option 1: Template Mixing (ColdFusion/PHP Style)

**Concept:** Mix HTML and Quantum tags in the same file. HTML passes through, Quantum tags are processed.

#### Architecture
```xml
<q:component name="ProductPage">
  <q:query name="products" datasource="db">
    SELECT * FROM products WHERE active = true
  </q:query>

  <!DOCTYPE html>
  <html>
  <head>
    <title>Products - My Store</title>
    <link rel="stylesheet" href="/css/main.css">
  </head>
  <body>
    <h1>Our Products</h1>

    <div class="products-grid">
      <q:loop items="{products}" var="p" type="array">
        <div class="product-card">
          <img src="/images/{p.image}" alt="{p.name}">
          <h2>{p.name}</h2>
          <p>{p.description}</p>
          <span class="price">${p.price}</span>

          <q:if condition="{p.stock > 0}">
            <button>Add to Cart</button>
          <q:else>
            <span class="out-of-stock">Out of Stock</span>
          </q:if>
        </div>
      </q:loop>
    </div>
  </body>
  </html>
</q:component>
```

#### How It Works
1. Parser identifies HTML elements vs Quantum tags
2. HTML elements stored as `HTMLNode` in AST
3. Quantum tags processed normally (loops, conditions, queries)
4. Runtime executes AST, building HTML string
5. Databinding `{variable}` replaced during rendering
6. Final HTML string returned

#### Pros
- ✅ **Simple mental model** - developers write HTML directly
- ✅ **Familiar** - same as ColdFusion, PHP, JSP, ASP
- ✅ **SEO-friendly** - server-rendered HTML
- ✅ **No JavaScript required** - works without client-side code
- ✅ **Progressive enhancement** - can add JS later
- ✅ **Easy to implement** - straightforward parsing and rendering

#### Cons
- ⚠️ **No client-side reactivity** - full page reloads for updates
- ⚠️ **Mixing concerns** - HTML and logic together
- ⚠️ **Limited reusability** - harder to compose components

#### Implementation Effort
**2-3 days** - Low complexity

---

### Option 2: Component-Based Rendering (React/Vue Style)

**Concept:** Components return structured HTML. Compose pages from smaller components with props.

#### Architecture
```xml
<!-- ProductCard.q -->
<q:component name="ProductCard">
  <q:param name="product" type="object" />

  <q:template>
    <div class="product-card">
      <img src="/images/{product.image}" alt="{product.name}">
      <h2>{product.name}</h2>
      <p>{product.description}</p>
      <span class="price">${product.price}</span>

      <q:if condition="{product.stock > 0}">
        <button>Add to Cart</button>
      <q:else>
        <span class="out-of-stock">Out of Stock</span>
      </q:if>
    </div>
  </q:template>
</q:component>

<!-- ProductPage.q -->
<q:component name="ProductPage">
  <q:query name="products" datasource="db">
    SELECT * FROM products WHERE active = true
  </q:query>

  <q:template>
    <Layout title="Products">
      <h1>Our Products</h1>

      <div class="products-grid">
        <q:loop items="{products}" var="p" type="array">
          <ProductCard product="{p}" />
        </q:loop>
      </div>
    </Layout>
  </q:template>
</q:component>
```

#### How It Works
1. Components have `<q:template>` section for HTML
2. Components can be imported/used like custom tags
3. Props passed via attributes
4. Runtime resolves component hierarchy
5. Renders from leaf components upward

#### Pros
- ✅ **Composable** - build complex pages from simple components
- ✅ **Reusable** - components can be used anywhere
- ✅ **Separation of concerns** - each component encapsulated
- ✅ **Testable** - components can be tested in isolation
- ✅ **Type-safe props** - parameters with validation

#### Cons
- ⚠️ **More complex** - component resolution system needed
- ⚠️ **Learning curve** - developers need to understand composition
- ⚠️ **Import system** - need to resolve component references
- ⚠️ **Still no reactivity** - SSR only without extra work

#### Implementation Effort
**1-2 weeks** - Medium complexity

---

### Option 3: SSR + Hydration (Modern Full-Stack)

**Concept:** Server renders initial HTML, then "hydrates" in browser for interactivity.

#### Architecture
```xml
<q:component name="Counter" interactive="true">
  <q:state name="count" value="0" />

  <q:template>
    <div>
      <h2>Count: {count}</h2>
      <button q:click="increment">+</button>
      <button q:click="decrement">-</button>
    </div>
  </q:template>

  <q:script>
    function increment() {
      setState('count', count + 1);
    }

    function decrement() {
      setState('count', count - 1);
    }
  </q:script>
</q:component>
```

#### How It Works
1. Server renders initial HTML (SSR)
2. Generates JavaScript bundle with component logic
3. HTML sent to browser with `<script>` tag
4. JavaScript "hydrates" - attaches event listeners
5. Client-side state updates re-render only changed parts
6. Best of both worlds: fast initial load + interactivity

#### Pros
- ✅ **Interactive** - client-side reactivity
- ✅ **Fast initial load** - server-rendered HTML
- ✅ **SEO-friendly** - crawlers see full content
- ✅ **Modern** - same approach as Next.js, Nuxt, SvelteKit
- ✅ **Progressive enhancement** - works without JS, better with JS

#### Cons
- ⚠️ **Very complex** - needs bundler, virtual DOM, state management
- ⚠️ **JavaScript required** - for interactivity
- ⚠️ **Bundle size** - need to ship framework to client
- ⚠️ **Implementation time** - 1-2 months minimum
- ⚠️ **Maintenance** - complex system to maintain

#### Implementation Effort
**1-2 months** - High complexity

---

### Option 4: Hybrid Approach (Recommended)

**Concept:** Start with Template Mixing (Option 1), but design architecture to support components (Option 2) and future hydration (Option 3).

#### Phase 1: Template Mixing (Immediate - 2-3 days)
```xml
<q:component name="ProductPage">
  <q:query name="products" datasource="db">
    SELECT * FROM products WHERE active = true
  </q:query>

  <html>
    <body>
      <h1>Products</h1>
      <q:loop items="{products}" var="p">
        <div>{p.name} - ${p.price}</div>
      </q:loop>
    </body>
  </html>
</q:component>
```

**Delivers:**
- ✅ Immediate HTML rendering
- ✅ Works with all existing features
- ✅ Simple mental model
- ✅ Production-ready quickly

#### Phase 2: Component Composition (1-2 weeks later)
```xml
<q:component name="ProductPage">
  <q:import component="ProductCard" />
  <q:import component="Layout" />

  <q:query name="products" datasource="db">
    SELECT * FROM products WHERE active = true
  </q:query>

  <Layout title="Products">
    <h1>Our Products</h1>
    <q:loop items="{products}" var="p">
      <ProductCard product="{p}" />
    </q:loop>
  </Layout>
</q:component>
```

**Adds:**
- ✅ Component reusability
- ✅ Better code organization
- ✅ Composable architecture

#### Phase 3: Islands Architecture (Future - when needed)
```xml
<q:component name="ProductPage">
  <!-- Server-rendered static content -->
  <h1>Our Products</h1>
  <p>Check out our latest offerings</p>

  <!-- Interactive "island" - hydrated on client -->
  <SearchFilter interactive="true">
    <q:state name="query" value="" />
    <input q:model="query" />
    <button q:click="applyFilter">Filter</button>
  </SearchFilter>

  <!-- Server-rendered product list -->
  <q:loop items="{products}" var="p">
    <div>{p.name}</div>
  </q:loop>
</q:component>
```

**Adds:**
- ✅ Selective interactivity (only where needed)
- ✅ Minimal JavaScript bundle
- ✅ Best performance
- ✅ Modern architecture (Astro-style)

---

## 🎯 Recommendation: Hybrid Approach (Start with Phase 1)

### Why This is Best

1. **Immediate Value** - Get HTML rendering working in days, not weeks
2. **Low Risk** - Simple implementation, easy to debug
3. **Familiar** - Developers already know this pattern
4. **Foundation** - Architecture supports future enhancements
5. **Pragmatic** - Don't over-engineer for features we don't need yet

### Architecture Design Principles

1. **AST Extensibility**
   - Add `HTMLNode` to AST
   - Add `TemplateNode` for future components
   - Keep rendering logic separate from execution

2. **Renderer Abstraction**
   ```python
   class QuantumRenderer:
       def render(self, ast: ComponentNode) -> str:
           """Render AST to HTML string"""

   class HTMLRenderer(QuantumRenderer):
       """Template mixing renderer (Phase 1)"""

   class ComponentRenderer(QuantumRenderer):
       """Component composition renderer (Phase 2)"""

   class IslandRenderer(QuantumRenderer):
       """Hydration + islands renderer (Phase 3)"""
   ```

3. **Web Server Integration**
   - Flask/FastAPI web server
   - Routes map to `.q` components
   - Automatic content-type detection
   - Static file serving

---

## 📋 Phase 1 Implementation Plan

### 1. AST Extensions
**File:** `src/core/ast_nodes.py`

```python
class HTMLNode(QuantumNode):
    """Represents raw HTML to pass through"""
    def __init__(self, tag: str, attributes: Dict[str, str], children: List):
        self.tag = tag
        self.attributes = attributes
        self.children = children
        self.self_closing = tag in ['img', 'br', 'hr', 'input', 'meta', 'link']

class TextNode(QuantumNode):
    """Represents raw text content"""
    def __init__(self, content: str):
        self.content = content
```

### 2. Parser Extensions
**File:** `src/core/parser.py`

```python
def _parse_element(self, element: ET.Element) -> QuantumNode:
    """Parse element - could be Quantum tag or HTML"""

    # Quantum namespace tags
    if element.tag.startswith('q:'):
        return self._parse_quantum_tag(element)

    # HTML tags
    else:
        return self._parse_html_tag(element)

def _parse_html_tag(self, element: ET.Element) -> HTMLNode:
    """Parse HTML element"""
    tag = element.tag
    attributes = dict(element.attrib)
    children = []

    # Parse children
    if element.text:
        children.append(TextNode(element.text))

    for child in element:
        children.append(self._parse_element(child))
        if child.tail:
            children.append(TextNode(child.tail))

    return HTMLNode(tag, attributes, children)
```

### 3. Renderer Implementation
**File:** `src/runtime/renderer.py` (NEW)

```python
class HTMLRenderer:
    """Renders Quantum AST to HTML string"""

    def __init__(self, context: ExecutionContext):
        self.context = context

    def render(self, node: QuantumNode) -> str:
        """Render node to HTML"""

        if isinstance(node, HTMLNode):
            return self._render_html_node(node)

        elif isinstance(node, TextNode):
            return self._render_text_node(node)

        elif isinstance(node, LoopNode):
            return self._render_loop_node(node)

        elif isinstance(node, IfNode):
            return self._render_if_node(node)

        elif isinstance(node, ReturnNode):
            return str(node.value)

        # ... other node types

    def _render_html_node(self, node: HTMLNode) -> str:
        """Render HTML element"""

        # Build opening tag
        attrs = ' '.join(f'{k}="{v}"' for k, v in node.attributes.items())
        opening = f'<{node.tag}' + (f' {attrs}' if attrs else '') + '>'

        # Self-closing tags
        if node.self_closing:
            return opening.replace('>', ' />')

        # Render children
        content = ''.join(self.render(child) for child in node.children)

        # Build closing tag
        closing = f'</{node.tag}>'

        return opening + content + closing

    def _render_text_node(self, node: TextNode) -> str:
        """Render text with databinding"""
        return self._apply_databinding(node.content)

    def _apply_databinding(self, text: str) -> str:
        """Replace {variable} with actual values"""
        # Use existing databinding logic from component.py
        pass
```

### 4. Web Server Integration
**File:** `src/runtime/web_server.py`

```python
from flask import Flask, request, Response
from src.core.parser import QuantumParser
from src.runtime.component import ComponentRuntime
from src.runtime.renderer import HTMLRenderer

app = Flask(__name__)

@app.route('/<path:component_path>')
def render_component(component_path):
    """Render .q component to HTML"""

    # Load component file
    file_path = f'components/{component_path}.q'

    # Parse
    parser = QuantumParser()
    ast = parser.parse_file(file_path)

    # Execute (runs queries, loops, etc)
    runtime = ComponentRuntime()
    context = runtime.execute(ast)

    # Render to HTML
    renderer = HTMLRenderer(context)
    html = renderer.render(ast)

    return Response(html, mimetype='text/html')

if __name__ == '__main__':
    app.run(debug=True, port=8080)
```

### 5. Example Component
**File:** `examples/products-page.q`

```xml
<q:component name="ProductsPage">
  <q:query name="products" datasource="db">
    SELECT id, name, description, price, image, stock
    FROM products
    WHERE active = true
    ORDER BY created_at DESC
    LIMIT 20
  </q:query>

  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Products - Quantum Store</title>
    <link rel="stylesheet" href="/static/css/main.css">
  </head>
  <body>
    <header>
      <h1>Quantum Store</h1>
      <nav>
        <a href="/">Home</a>
        <a href="/products">Products</a>
        <a href="/cart">Cart</a>
      </nav>
    </header>

    <main>
      <h2>Our Products</h2>
      <p>Found {products_result.recordCount} products</p>

      <div class="products-grid">
        <q:loop items="{products}" var="product" type="array">
          <article class="product-card">
            <img src="/static/images/{product.image}" alt="{product.name}">
            <h3>{product.name}</h3>
            <p>{product.description}</p>

            <div class="product-footer">
              <span class="price">${product.price}</span>

              <q:if condition="{product.stock > 0}">
                <button class="btn-primary">Add to Cart</button>
              <q:else>
                <span class="out-of-stock">Out of Stock</span>
              </q:if>
            </div>
          </article>
        </q:loop>
      </div>
    </main>

    <footer>
      <p>&copy; 2025 Quantum Store. All rights reserved.</p>
    </footer>
  </body>
  </html>
</q:component>
```

---

## 🧪 Testing Strategy

### Test Cases

1. **Simple HTML passthrough**
   - Input: `<div>Hello</div>`
   - Output: `<div>Hello</div>`

2. **Databinding in HTML**
   - Input: `<h1>{title}</h1>` with `title="Welcome"`
   - Output: `<h1>Welcome</h1>`

3. **Loop rendering**
   - Loop over array, generate HTML for each item

4. **Conditional rendering**
   - Show/hide HTML based on conditions

5. **Nested structures**
   - HTML inside loops inside conditionals

6. **Self-closing tags**
   - `<img>`, `<br>`, `<input>` render correctly

7. **Attributes**
   - HTML attributes preserved and rendered

8. **Special characters**
   - HTML entities handled correctly

---

## 📈 Success Metrics

**Phase 1 Complete When:**
- ✅ Can write HTML directly in `.q` components
- ✅ Databinding `{variable}` works in HTML
- ✅ Loops generate repeated HTML elements
- ✅ Conditionals show/hide HTML sections
- ✅ Web server serves `.q` files as HTML pages
- ✅ At least 10 test cases passing
- ✅ Documentation with examples

**Timeline:** 2-3 days

---

## 🚀 Next Steps

1. **Day 1:** AST + Parser extensions (HTMLNode, TextNode)
2. **Day 2:** Renderer implementation + databinding
3. **Day 3:** Web server integration + testing

After Phase 1, we can evaluate:
- Do we need component composition? (Phase 2)
- Do we need interactivity? (Phase 3)
- Or is template mixing sufficient?

---

**Decision:** Start with Phase 1 (Template Mixing) - simple, fast, proven approach. ✅
