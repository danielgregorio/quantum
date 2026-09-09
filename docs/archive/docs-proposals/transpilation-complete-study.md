# Quantum Framework - Estudo Completo de Transpilação

**Data**: 2026-02-14
**Status**: Proposta Técnica Detalhada
**Autor**: Claude + Daniel

---

## 1. Sumário Executivo

### Objetivo
Implementar um transpilador que converta código Quantum (.q) em código nativo Python e JavaScript, eliminando o overhead de interpretação em runtime.

### Escopo Identificado
- **81 tipos de nós AST** a serem mapeados
- **2 targets principais**: Python (backend) e JavaScript (frontend)
- **Speedup esperado**: 10-20x sobre interpretação atual

### Recomendação
Implementar em 3 fases, começando com um MVP de ~20 nós essenciais.

---

## 2. Inventário Completo de Nós AST

### 2.1 Categorização por Prioridade

#### Tier 1: Core (MVP) - 20 nós
Essenciais para qualquer aplicação funcionar.

| Nó | Tag | Descrição | Python | JS |
|----|-----|-----------|--------|-----|
| ComponentNode | `<q:component>` | Container principal | ✓ | ✓ |
| SetNode | `<q:set>` | Atribuição de variável | ✓ | ✓ |
| LoopNode | `<q:loop>` | Iteração | ✓ | ✓ |
| IfNode | `<q:if>` | Condicional | ✓ | ✓ |
| FunctionNode | `<q:function>` | Definição de função | ✓ | ✓ |
| HTMLNode | `<div>`, etc | Elementos HTML | ✓ | ✓ |
| TextNode | texto | Conteúdo texto | ✓ | ✓ |
| ActionNode | `<q:action>` | Handler de form | ✓ | - |
| QueryNode | `<q:query>` | Query SQL | ✓ | - |
| RedirectNode | `<q:redirect>` | Redirect HTTP | ✓ | - |
| ImportNode | `<q:import>` | Import de componente | ✓ | ✓ |
| SlotNode | `<q:slot>` | Content projection | ✓ | ✓ |
| ComponentCallNode | `<MyComp>` | Chamada de componente | ✓ | ✓ |
| PythonNode | `<q:python>` | Bloco Python inline | ✓ | - |
| PyImportNode | `<q:pyimport>` | Import Python | ✓ | - |
| ApplicationNode | `<q:application>` | Container app | ✓ | ✓ |
| FlashNode | `<q:flash>` | Mensagem flash | ✓ | - |
| DocTypeNode | `<!DOCTYPE>` | Doctype HTML | ✓ | ✓ |
| CommentNode | `<!-- -->` | Comentário | ✓ | ✓ |
| QueryParamNode | `<q:param>` | Param de query | ✓ | - |

#### Tier 2: Data & Integration - 18 nós
Importação de dados e integrações externas.

| Nó | Tag | Descrição |
|----|-----|-----------|
| DataNode | `<q:data>` | Import CSV/JSON/XML |
| ColumnNode | `<q:column>` | Coluna CSV |
| FieldNode | `<q:field>` | Campo XML |
| TransformNode | `<q:transform>` | Pipeline transform |
| FilterNode | `<q:filter>` | Filtro de dados |
| SortNode | `<q:sort>` | Ordenação |
| LimitNode | `<q:limit>` | Limitação |
| ComputeNode | `<q:compute>` | Campo computado |
| HeaderNode | `<q:header>` | Header HTTP |
| InvokeNode | `<q:invoke>` | Chamada HTTP/REST |
| InvokeHeaderNode | - | Headers de invoke |
| FileNode | `<q:file>` | Upload/download |
| MailNode | `<q:mail>` | Envio de email |
| TransactionNode | `<q:transaction>` | Transação DB |
| PersistNode | `<q:persist>` | Persistência |
| LLMNode | `<q:llm>` | Chamada LLM |
| LLMMessageNode | `<q:message>` | Mensagem LLM |
| KnowledgeNode | - | Knowledge base |

#### Tier 3: Async & Events - 12 nós
Processamento assíncrono e eventos.

| Nó | Tag | Descrição |
|----|-----|-----------|
| JobNode | `<q:job>` | Job queue |
| ScheduleNode | `<q:schedule>` | Agendamento |
| ThreadNode | `<q:thread>` | Thread async |
| DispatchEventNode | `<q:dispatchEvent>` | Publicar evento |
| OnEventNode | `<q:onEvent>` | Ouvir evento |
| MessageNode | `<q:message>` | Mensagem MQ |
| MessageHeaderNode | - | Headers MQ |
| SubscribeNode | `<q:subscribe>` | Subscription |
| QueueNode | `<q:queue>` | Declarar fila |
| MessageAckNode | `<q:messageAck>` | ACK manual |
| MessageNackNode | `<q:messageNack>` | NACK |

#### Tier 4: Game Engine - 23 nós
Engine 2D para jogos.

| Nó | Descrição |
|----|-----------|
| SceneNode | Cena do jogo |
| SpriteNode | Sprite |
| PhysicsNode | Física |
| ColliderNode | Colisão |
| AnimationNode | Animação |
| CameraNode | Câmera |
| InputNode | Input |
| SoundNode | Áudio |
| ParticleNode | Partículas |
| TimerNode | Timer |
| SpawnNode | Spawn |
| HudNode | HUD |
| TweenNode | Tween |
| TilemapNode | Tilemap |
| TilemapLayerNode | Layer tilemap |
| BehaviorNode | Comportamento |
| UseNode | Uso de behavior |
| PrefabNode | Prefab |
| InstanceNode | Instância |
| GroupNode | Grupo |
| StateMachineNode | State machine |
| StateNode | Estado |
| TransitionNode | Transição |

#### Tier 5: Python Advanced - 4 nós
Integração avançada com Python.

| Nó | Tag | Descrição |
|----|-----|-----------|
| PyClassNode | `<q:class>` | Classe Python inline |
| PyDecoratorNode | `<q:decorator>` | Decorator |
| PyExprNode | `<q:expr>` | Expressão Python |

#### Tier 6: Utility - 4 nós
Classes utilitárias.

| Nó | Descrição |
|----|-----------|
| QuantumParam | Parâmetro de função |
| QuantumReturn | Tipo de retorno |
| QuantumRoute | Rota HTTP |
| RestConfig | Config REST |

---

## 3. Arquitetura do Transpilador

### 3.1 Visão Geral

```
┌─────────────────────────────────────────────────────────────────────┐
│                      QUANTUM TRANSPILER                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────────┐   │
│  │  Source  │──>│  Parser  │──>│   AST    │──>│  Transformer   │   │
│  │   .q     │   │(existente)│   │(existente)│   │   (novo)       │   │
│  └──────────┘   └──────────┘   └──────────┘   └───────┬────────┘   │
│                                                        │            │
│                     ┌──────────────────────────────────┼────────┐   │
│                     │              CodeGenerators      │        │   │
│                     │   ┌──────────────────────────────┴──────┐ │   │
│                     │   │                                     │ │   │
│                     │   ▼                                     ▼ │   │
│                     │ ┌─────────────┐              ┌───────────┐│   │
│                     │ │   Python    │              │JavaScript ││   │
│                     │ │  Generator  │              │ Generator ││   │
│                     │ └──────┬──────┘              └─────┬─────┘│   │
│                     │        │                           │      │   │
│                     └────────┼───────────────────────────┼──────┘   │
│                              │                           │          │
│                              ▼                           ▼          │
│                     ┌─────────────┐              ┌───────────┐      │
│                     │   app.py    │              │  app.js   │      │
│                     │  (output)   │              │ (output)  │      │
│                     └─────────────┘              └───────────┘      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Estrutura de Diretórios

```
src/
├── compiler/
│   ├── __init__.py
│   ├── transpiler.py           # Orquestrador principal
│   ├── transformer.py          # Transformações AST→AST
│   ├── base_generator.py       # Classe base para generators
│   ├── python/
│   │   ├── __init__.py
│   │   ├── generator.py        # Python code generator
│   │   ├── runtime.py          # Runtime helpers
│   │   └── templates/          # Templates Jinja2
│   │       ├── component.py.j2
│   │       ├── function.py.j2
│   │       └── ...
│   ├── javascript/
│   │   ├── __init__.py
│   │   ├── generator.py        # JS code generator
│   │   ├── runtime.js          # Runtime helpers
│   │   └── templates/
│   │       ├── component.js.j2
│   │       └── ...
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── scope_analyzer.py   # Análise de escopo
│   │   ├── type_inference.py   # Inferência de tipos
│   │   └── dependency.py       # Análise de dependências
│   ├── optimization/
│   │   ├── __init__.py
│   │   ├── constant_folding.py
│   │   ├── dead_code.py
│   │   └── inline.py
│   └── cli.py                  # Comando 'quantum compile'
├── core/
│   └── ast_nodes.py            # (existente)
└── runtime/
    └── ...                     # (existente - fallback)
```

### 3.3 Classes Principais

```python
# compiler/base_generator.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from core.ast_nodes import QuantumNode

class CodeGenerator(ABC):
    """Base class for all code generators."""

    def __init__(self):
        self.indent_level = 0
        self.indent_str = "    "
        self.output_lines: List[str] = []
        self.scope_stack: List[Dict[str, Any]] = [{}]

    @abstractmethod
    def generate(self, node: QuantumNode) -> str:
        """Generate code for a node."""
        pass

    def visit(self, node: QuantumNode) -> str:
        """Visitor pattern dispatcher."""
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: QuantumNode) -> str:
        """Fallback for unhandled nodes."""
        raise NotImplementedError(
            f"No visitor for {type(node).__name__}"
        )

    def emit(self, code: str):
        """Emit a line of code with proper indentation."""
        indent = self.indent_str * self.indent_level
        self.output_lines.append(f"{indent}{code}")

    def indent(self):
        """Increase indentation."""
        self.indent_level += 1

    def dedent(self):
        """Decrease indentation."""
        self.indent_level = max(0, self.indent_level - 1)

    def push_scope(self):
        """Enter a new variable scope."""
        self.scope_stack.append({})

    def pop_scope(self):
        """Exit current scope."""
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()

    def declare_var(self, name: str, type_hint: str = None):
        """Declare a variable in current scope."""
        self.scope_stack[-1][name] = type_hint

    def lookup_var(self, name: str) -> bool:
        """Check if variable exists in any scope."""
        for scope in reversed(self.scope_stack):
            if name in scope:
                return True
        return False
```

---

## 4. Mapeamentos Detalhados

### 4.1 Core Nodes (Tier 1)

#### SetNode → Python/JS

**Quantum:**
```xml
<q:set name="counter" value="0" />
<q:set name="total" value="{counter + 10}" />
<q:set name="items" value="{[1, 2, 3]}" />
```

**Python:**
```python
counter = 0
total = counter + 10
items = [1, 2, 3]
```

**JavaScript:**
```javascript
let counter = 0;
let total = counter + 10;
let items = [1, 2, 3];
```

**Implementação:**
```python
# compiler/python/generator.py

def visit_SetNode(self, node: SetNode) -> str:
    name = node.name
    value = self.transpile_expression(node.value)

    # Verificar se é reatribuição ou declaração
    if self.lookup_var(name):
        self.emit(f"{name} = {value}")
    else:
        self.declare_var(name)
        self.emit(f"{name} = {value}")

    return name
```

#### LoopNode → Python/JS

**Quantum (range):**
```xml
<q:loop from="1" to="10" var="i">
    <q:set name="total" value="{total + i}" />
</q:loop>
```

**Python:**
```python
for i in range(1, 11):
    total = total + i
```

**JavaScript:**
```javascript
for (let i = 1; i <= 10; i++) {
    total = total + i;
}
```

**Quantum (collection):**
```xml
<q:loop collection="{items}" var="item" index="idx">
    <div>{idx}: {item.name}</div>
</q:loop>
```

**Python:**
```python
for idx, item in enumerate(items):
    _html.append(f'<div>{idx}: {item["name"]}</div>')
```

**JavaScript:**
```javascript
items.forEach((item, idx) => {
    html += `<div>${idx}: ${item.name}</div>`;
});
```

**Implementação:**
```python
def visit_LoopNode(self, node: LoopNode) -> str:
    if node.collection:
        # Collection-based loop
        collection = self.transpile_expression(node.collection)
        var = node.var

        if node.index:
            self.emit(f"for {node.index}, {var} in enumerate({collection}):")
        else:
            self.emit(f"for {var} in {collection}:")
    else:
        # Range-based loop
        start = node.from_val or 0
        end = int(node.to_val) + 1  # Quantum is inclusive
        var = node.var

        if node.step:
            self.emit(f"for {var} in range({start}, {end}, {node.step}):")
        else:
            self.emit(f"for {var} in range({start}, {end}):")

    self.indent()
    self.push_scope()
    self.declare_var(node.var)

    for child in node.children:
        self.visit(child)

    self.pop_scope()
    self.dedent()
```

#### IfNode → Python/JS

**Quantum:**
```xml
<q:if condition="{user.role == 'admin'}">
    <AdminPanel />
</q:if>
<q:elseif condition="{user.role == 'editor'}">
    <EditorPanel />
</q:elseif>
<q:else>
    <UserPanel />
</q:else>
```

**Python:**
```python
if user["role"] == "admin":
    _html.append(AdminPanel())
elif user["role"] == "editor":
    _html.append(EditorPanel())
else:
    _html.append(UserPanel())
```

**JavaScript:**
```javascript
if (user.role === "admin") {
    html += AdminPanel();
} else if (user.role === "editor") {
    html += EditorPanel();
} else {
    html += UserPanel();
}
```

#### FunctionNode → Python/JS

**Quantum:**
```xml
<q:function name="calculateTotal" params="items, taxRate">
    <q:set name="subtotal" value="{sum(item.price for item in items)}" />
    <q:set name="tax" value="{subtotal * taxRate}" />
    <q:return value="{subtotal + tax}" />
</q:function>
```

**Python:**
```python
def calculateTotal(items, taxRate):
    subtotal = sum(item["price"] for item in items)
    tax = subtotal * taxRate
    return subtotal + tax
```

**JavaScript:**
```javascript
function calculateTotal(items, taxRate) {
    const subtotal = items.reduce((sum, item) => sum + item.price, 0);
    const tax = subtotal * taxRate;
    return subtotal + tax;
}
```

#### QueryNode → Python

**Quantum:**
```xml
<q:query name="users" datasource="main">
    SELECT * FROM users
    WHERE status = <q:param value="{status}" />
    ORDER BY created_at DESC
    LIMIT 10
</q:query>
```

**Python:**
```python
users = db.execute(
    "SELECT * FROM users WHERE status = ? ORDER BY created_at DESC LIMIT 10",
    [status]
).fetchall()
```

**Implementação:**
```python
def visit_QueryNode(self, node: QueryNode) -> str:
    # Extrair SQL e parâmetros
    sql, params = self.extract_sql_params(node)

    # Gerar código
    self.emit(f'{node.name} = db.execute(')
    self.indent()
    self.emit(f'"{sql}",')
    self.emit(f'{params}')
    self.dedent()
    self.emit(').fetchall()')

    return node.name
```

#### HTMLNode → Python/JS

**Quantum:**
```xml
<div class="card {isActive ? 'active' : ''}">
    <h1>{title}</h1>
    <p>{description}</p>
    <button onclick="{handleClick}">Click me</button>
</div>
```

**Python (string-based):**
```python
_html.append(f'''<div class="card {'active' if isActive else ''}">
    <h1>{title}</h1>
    <p>{description}</p>
    <button onclick="handleClick()">Click me</button>
</div>''')
```

**JavaScript (DOM-based):**
```javascript
const el = document.createElement('div');
el.className = `card ${isActive ? 'active' : ''}`;
el.innerHTML = `
    <h1>${title}</h1>
    <p>${description}</p>
    <button onclick="${handleClick}">Click me</button>
`;
```

---

## 5. Tratamento de Expressões

### 5.1 Parser de Expressões Quantum

Expressões em `{...}` precisam ser convertidas para a linguagem target.

**Transformações necessárias:**

| Quantum | Python | JavaScript |
|---------|--------|------------|
| `{x + y}` | `x + y` | `x + y` |
| `{x == y}` | `x == y` | `x === y` |
| `{x != y}` | `x != y` | `x !== y` |
| `{x and y}` | `x and y` | `x && y` |
| `{x or y}` | `x or y` | `x \|\| y` |
| `{not x}` | `not x` | `!x` |
| `{x if cond else y}` | `x if cond else y` | `cond ? x : y` |
| `{x.property}` | `x["property"]` | `x.property` |
| `{x[0]}` | `x[0]` | `x[0]` |
| `{len(x)}` | `len(x)` | `x.length` |
| `{x.upper()}` | `x.upper()` | `x.toUpperCase()` |
| `{x in y}` | `x in y` | `y.includes(x)` |
| `{[i*2 for i in x]}` | `[i*2 for i in x]` | `x.map(i => i*2)` |

### 5.2 Implementação do Expression Transformer

```python
# compiler/analysis/expression_transformer.py

import ast
from typing import Union

class ExpressionTransformer:
    """Transforms Quantum expressions to target language."""

    def __init__(self, target: str = "python"):
        self.target = target

    def transform(self, expr: str) -> str:
        """Transform a Quantum expression."""
        # Remove { } wrapper
        expr = expr.strip()
        if expr.startswith("{") and expr.endswith("}"):
            expr = expr[1:-1].strip()

        # Parse as Python AST
        try:
            tree = ast.parse(expr, mode='eval')
        except SyntaxError:
            # Fallback: return as-is
            return expr

        # Transform based on target
        if self.target == "javascript":
            return self._to_javascript(tree.body)
        else:
            return self._to_python(tree.body)

    def _to_python(self, node: ast.expr) -> str:
        """Convert AST to Python code."""
        # Python expressions are mostly compatible
        return ast.unparse(node)

    def _to_javascript(self, node: ast.expr) -> str:
        """Convert AST to JavaScript code."""
        if isinstance(node, ast.Compare):
            return self._js_compare(node)
        elif isinstance(node, ast.BoolOp):
            return self._js_boolop(node)
        elif isinstance(node, ast.UnaryOp):
            return self._js_unaryop(node)
        elif isinstance(node, ast.IfExp):
            return self._js_ternary(node)
        elif isinstance(node, ast.Attribute):
            return self._js_attribute(node)
        elif isinstance(node, ast.Call):
            return self._js_call(node)
        elif isinstance(node, ast.ListComp):
            return self._js_listcomp(node)
        # ... mais casos
        else:
            return ast.unparse(node)

    def _js_compare(self, node: ast.Compare) -> str:
        """Convert comparison to JS."""
        left = self._to_javascript(node.left)
        parts = [left]

        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, ast.Eq):
                parts.append("===")
            elif isinstance(op, ast.NotEq):
                parts.append("!==")
            elif isinstance(op, ast.In):
                # x in y -> y.includes(x)
                right = self._to_javascript(comparator)
                return f"{right}.includes({left})"
            else:
                parts.append(self._js_op(op))

            parts.append(self._to_javascript(comparator))

        return " ".join(parts)

    def _js_boolop(self, node: ast.BoolOp) -> str:
        """Convert boolean op to JS."""
        op = "&&" if isinstance(node.op, ast.And) else "||"
        values = [self._to_javascript(v) for v in node.values]
        return f" {op} ".join(values)

    def _js_listcomp(self, node: ast.ListComp) -> str:
        """Convert list comprehension to JS map/filter."""
        # [x*2 for x in items] -> items.map(x => x*2)
        # [x for x in items if x > 0] -> items.filter(x => x > 0)

        gen = node.generators[0]
        iter_var = gen.target.id
        iterable = self._to_javascript(gen.iter)
        expr = self._to_javascript(node.elt)

        if gen.ifs:
            # Has filter
            filter_expr = self._to_javascript(gen.ifs[0])
            return f"{iterable}.filter({iter_var} => {filter_expr}).map({iter_var} => {expr})"
        else:
            return f"{iterable}.map({iter_var} => {expr})"
```

---

## 6. Runtime Libraries

### 6.1 Python Runtime

```python
# compiler/python/runtime.py

"""
Quantum Runtime for Python
Generated code imports this module.
"""

from typing import Any, Dict, List, Optional
from functools import wraps
import html as html_module

# HTML escaping
def escape(value: Any) -> str:
    """Escape HTML entities."""
    if value is None:
        return ""
    return html_module.escape(str(value))

# Databinding helper
def bind(template: str, context: Dict[str, Any]) -> str:
    """Simple databinding for strings."""
    import re
    def replace(match):
        expr = match.group(1)
        try:
            return str(eval(expr, {}, context))
        except:
            return match.group(0)
    return re.sub(r'\{([^}]+)\}', replace, template)

# Component base class
class Component:
    """Base class for compiled components."""

    def __init__(self, **props):
        self.props = props
        self._html: List[str] = []

    def render(self) -> str:
        """Override in subclass."""
        raise NotImplementedError

    def __str__(self) -> str:
        return self.render()

# Flash messages
_flash_messages: List[Dict[str, str]] = []

def flash(message: str, category: str = "info"):
    """Add a flash message."""
    _flash_messages.append({"message": message, "category": category})

def get_flashed_messages() -> List[Dict[str, str]]:
    """Get and clear flash messages."""
    global _flash_messages
    messages = _flash_messages.copy()
    _flash_messages = []
    return messages

# Database helper (placeholder)
class Database:
    """Database connection wrapper."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._conn = None

    def execute(self, sql: str, params: List[Any] = None):
        """Execute SQL query."""
        # Implementation depends on database type
        pass

# Session helper
class Session(dict):
    """Session storage."""
    pass

# Request context
class RequestContext:
    """HTTP request context."""

    def __init__(self):
        self.form: Dict[str, Any] = {}
        self.args: Dict[str, Any] = {}
        self.cookies: Dict[str, str] = {}
        self.headers: Dict[str, str] = {}
        self.method: str = "GET"
        self.path: str = "/"

request = RequestContext()
session = Session()
```

### 6.2 JavaScript Runtime

```javascript
// compiler/javascript/runtime.js

/**
 * Quantum Runtime for JavaScript
 */

// HTML escaping
export function escape(value) {
    if (value == null) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Simple databinding
export function bind(template, context) {
    return template.replace(/\{([^}]+)\}/g, (match, expr) => {
        try {
            return eval(expr);
        } catch {
            return match;
        }
    });
}

// Component base class
export class Component {
    constructor(props = {}) {
        this.props = props;
    }

    render() {
        throw new Error('render() must be implemented');
    }

    toString() {
        return this.render();
    }
}

// State management
export function createStore(initialState) {
    let state = initialState;
    const listeners = [];

    return {
        getState: () => state,
        setState: (newState) => {
            state = { ...state, ...newState };
            listeners.forEach(fn => fn(state));
        },
        subscribe: (fn) => {
            listeners.push(fn);
            return () => listeners.splice(listeners.indexOf(fn), 1);
        }
    };
}

// HTTP helpers
export async function invoke(url, options = {}) {
    const response = await fetch(url, {
        method: options.method || 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        body: options.body ? JSON.stringify(options.body) : undefined
    });
    return response.json();
}

// Flash messages (browser)
const _flashMessages = [];

export function flash(message, category = 'info') {
    _flashMessages.push({ message, category });
}

export function getFlashedMessages() {
    const messages = [..._flashMessages];
    _flashMessages.length = 0;
    return messages;
}
```

---

## 7. CLI do Transpilador

### 7.1 Comandos

```bash
# Transpilar um arquivo
quantum compile app.q -o app.py
quantum compile app.q -o app.js --target=javascript

# Transpilar diretório
quantum compile src/ -o dist/ --target=python

# Watch mode
quantum compile src/ -o dist/ --watch

# Com otimizações
quantum compile app.q -o app.py --optimize

# Gerar source maps
quantum compile app.q -o app.js --sourcemap

# Verificar sem gerar código
quantum compile app.q --check
```

### 7.2 Implementação CLI

```python
# compiler/cli.py

import click
import sys
from pathlib import Path
from .transpiler import Transpiler

@click.group()
def cli():
    """Quantum Framework Compiler"""
    pass

@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(), help='Output file/directory')
@click.option('--target', type=click.Choice(['python', 'javascript']),
              default='python', help='Target language')
@click.option('--watch', is_flag=True, help='Watch for changes')
@click.option('--optimize', is_flag=True, help='Enable optimizations')
@click.option('--sourcemap', is_flag=True, help='Generate source maps')
@click.option('--check', is_flag=True, help='Check only, no output')
def compile(source, output, target, watch, optimize, sourcemap, check):
    """Compile Quantum source files."""

    source_path = Path(source)
    transpiler = Transpiler(target=target, optimize=optimize)

    if source_path.is_file():
        # Single file
        result = transpiler.compile_file(source_path)

        if check:
            click.echo(f"✓ {source} is valid")
            return

        if output:
            output_path = Path(output)
        else:
            ext = '.py' if target == 'python' else '.js'
            output_path = source_path.with_suffix(ext)

        output_path.write_text(result.code)
        click.echo(f"✓ Compiled {source} → {output_path}")

        if sourcemap and result.sourcemap:
            map_path = output_path.with_suffix(output_path.suffix + '.map')
            map_path.write_text(result.sourcemap)

    elif source_path.is_dir():
        # Directory
        if not output:
            output = str(source_path) + '_compiled'

        output_path = Path(output)
        output_path.mkdir(exist_ok=True)

        for q_file in source_path.rglob('*.q'):
            rel_path = q_file.relative_to(source_path)
            ext = '.py' if target == 'python' else '.js'
            out_file = output_path / rel_path.with_suffix(ext)
            out_file.parent.mkdir(parents=True, exist_ok=True)

            result = transpiler.compile_file(q_file)
            out_file.write_text(result.code)
            click.echo(f"✓ {q_file} → {out_file}")

    if watch:
        click.echo("Watching for changes... (Ctrl+C to stop)")
        # Implementar watch com watchdog
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        # ...

if __name__ == '__main__':
    cli()
```

---

## 8. Otimizações

### 8.1 Constant Folding

**Antes:**
```xml
<q:set name="x" value="{2 + 3}" />
<q:set name="y" value="{x * 4}" />
```

**Depois (Python):**
```python
x = 5  # Calculado em compile-time
y = x * 4
```

### 8.2 Dead Code Elimination

**Antes:**
```xml
<q:set name="unused" value="10" />
<q:set name="used" value="20" />
<div>{used}</div>
```

**Depois:**
```python
used = 20
_html.append(f'<div>{used}</div>')
# 'unused' foi removido
```

### 8.3 Loop Unrolling (pequenos loops)

**Antes:**
```xml
<q:loop from="1" to="3" var="i">
    <span>{i}</span>
</q:loop>
```

**Depois:**
```python
_html.append('<span>1</span>')
_html.append('<span>2</span>')
_html.append('<span>3</span>')
```

### 8.4 Expression Caching

**Antes:**
```xml
<div class="{getClass()}">{getClass()}</div>
```

**Depois:**
```python
_temp_0 = getClass()
_html.append(f'<div class="{_temp_0}">{_temp_0}</div>')
```

---

## 9. Cronograma de Implementação

### Fase 1: MVP (4 semanas)

**Semana 1: Fundação**
- [ ] Estrutura de diretórios
- [ ] CodeGenerator base class
- [ ] Expression transformer básico
- [ ] Testes unitários

**Semana 2: Python Generator (Tier 1 parcial)**
- [ ] SetNode, LoopNode, IfNode
- [ ] FunctionNode
- [ ] HTMLNode, TextNode
- [ ] Runtime básico

**Semana 3: Python Generator (Tier 1 completo)**
- [ ] QueryNode
- [ ] ActionNode
- [ ] ComponentNode, ImportNode
- [ ] Integração com Flask

**Semana 4: CLI e Integração**
- [ ] Comando `quantum compile`
- [ ] Testes de integração
- [ ] Documentação básica
- [ ] Benchmark de performance

### Fase 2: JavaScript + Data (4 semanas)

**Semana 5-6: JavaScript Generator**
- [ ] Todos os nós Tier 1 para JS
- [ ] Runtime JavaScript
- [ ] Integração com bundlers

**Semana 7-8: Data Nodes (Tier 2)**
- [ ] DataNode, TransformNode
- [ ] InvokeNode
- [ ] FileNode, MailNode

### Fase 3: Async + Polish (4 semanas)

**Semana 9-10: Async Nodes (Tier 3)**
- [ ] JobNode, ScheduleNode
- [ ] Event system

**Semana 11-12: Otimizações e Polish**
- [ ] Constant folding
- [ ] Dead code elimination
- [ ] Source maps
- [ ] VS Code integration

---

## 10. Métricas de Sucesso

| Métrica | Valor Alvo |
|---------|------------|
| Speedup vs interpretação | ≥ 10x |
| Cobertura de nós (MVP) | 100% Tier 1 |
| Cobertura de nós (Fase 2) | 100% Tier 1-2 |
| Testes unitários | ≥ 90% cobertura |
| Tempo de compilação | < 100ms/arquivo |
| Código gerado | Legível e debugável |

---

## 11. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Expressões complexas não mapeadas | Média | Alto | Fallback para eval() |
| Semântica diferente Python/JS | Alta | Médio | Testes de equivalência |
| Performance abaixo do esperado | Baixa | Médio | Benchmark contínuo |
| Debugging difícil | Média | Médio | Source maps |
| Manutenção dupla | Alta | Alto | AST como fonte única |

---

## 12. Conclusão

A transpilação é a abordagem com melhor custo-benefício para Quantum:

- **Esforço moderado**: 12 semanas para implementação completa
- **Speedup significativo**: 10-20x esperado
- **Baixo risco técnico**: Usa tecnologias maduras
- **Mantém compatibilidade**: Fallback para interpretador

### Recomendação Final

1. **Implementar Fase 1 (MVP)** em 4 semanas
2. **Validar speedup** com benchmarks
3. **Decidir continuação** baseado em métricas reais

---

## Apêndice A: Exemplo Completo

### Input (Quantum)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<q:component name="UserList">
    <q:pyimport module="flask" names="request, session" />

    <q:query name="users" datasource="main">
        SELECT id, name, email FROM users
        WHERE active = true
        ORDER BY name
    </q:query>

    <q:function name="formatEmail" params="email">
        <q:return value="{email.lower()}" />
    </q:function>

    <div class="user-list">
        <h1>Users ({len(users)})</h1>

        <q:if condition="{len(users) == 0}">
            <p>No users found.</p>
        </q:if>
        <q:else>
            <ul>
                <q:loop collection="{users}" var="user">
                    <li>
                        <strong>{user.name}</strong>
                        <span>{formatEmail(user.email)}</span>
                    </li>
                </q:loop>
            </ul>
        </q:else>
    </div>
</q:component>
```

### Output (Python)

```python
# Generated by Quantum Compiler v1.0
# Source: UserList.q

from quantum_runtime import Component, escape, Database
from flask import request, session

db = Database.get_connection("main")

def formatEmail(email):
    return email.lower()

class UserList(Component):
    def render(self):
        _html = []

        # Query
        users = db.execute(
            "SELECT id, name, email FROM users WHERE active = true ORDER BY name"
        ).fetchall()

        # Render
        _html.append('<div class="user-list">')
        _html.append(f'<h1>Users ({len(users)})</h1>')

        if len(users) == 0:
            _html.append('<p>No users found.</p>')
        else:
            _html.append('<ul>')
            for user in users:
                _html.append('<li>')
                _html.append(f'<strong>{escape(user["name"])}</strong>')
                _html.append(f'<span>{escape(formatEmail(user["email"]))}</span>')
                _html.append('</li>')
            _html.append('</ul>')

        _html.append('</div>')
        return '\n'.join(_html)

# Flask integration
def register_routes(app):
    @app.route('/users')
    def user_list():
        return UserList().render()
```

### Output (JavaScript)

```javascript
// Generated by Quantum Compiler v1.0
// Source: UserList.q

import { Component, escape } from 'quantum-runtime';

function formatEmail(email) {
    return email.toLowerCase();
}

export class UserList extends Component {
    async render() {
        let html = '';

        // Query (via API)
        const users = await fetch('/api/users?active=true').then(r => r.json());

        // Render
        html += '<div class="user-list">';
        html += `<h1>Users (${users.length})</h1>`;

        if (users.length === 0) {
            html += '<p>No users found.</p>';
        } else {
            html += '<ul>';
            for (const user of users) {
                html += '<li>';
                html += `<strong>${escape(user.name)}</strong>`;
                html += `<span>${escape(formatEmail(user.email))}</span>`;
                html += '</li>';
            }
            html += '</ul>';
        }

        html += '</div>';
        return html;
    }
}
```

---

*Documento gerado em 2026-02-14*
