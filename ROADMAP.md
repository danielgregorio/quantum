# Quantum Development Roadmap

## 🎯 Current Status
- ✅ **Core Features Complete**: Loops, Databinding, State, Functions
- ✅ **Database Queries (Phase 1-2) Complete**: q:query with pagination, Query of Queries, metadata
- 🚀 **Next Phase**: Data Operations (q:invoke + q:data)
- 📅 **Last Updated**: 2025-01-03

---

## 📋 REVISED PRIORITY ORDER (2025)

### Current Focus
1. ✅ **🔄 Loop Structures** (`q:loop`) - **COMPLETED**
2. ✅ **🔗 Variable Databinding** (`{variable}`) - **COMPLETED**
3. ✅ **📝 State Management** (`q:set`) - **COMPLETED**
4. ✅ **⚙️ Function Definitions** (`q:function`) - **COMPLETED**
5. ✅ **🗃️ Database Queries Phase 1-2** (`q:query`) - **COMPLETED**

### Next Phase: Data Operations (Q1 2025)
6. 📌 **🔗 Universal Invocation** (`q:invoke`) - **PLANNED**
7. 📌 **📦 Data Import & Transform** (`q:data`) - **PLANNED**

### Future Phases
8. **🤖 LLM Integration** (`q:llm`) - Q2 2025
9. **🧠 AI Agents** (`q:agent`) - Q3 2025
10. **📧 Email** (`q:mail`) - Q3 2025
11. **🗃️ Database Queries Phase 3** (Transactions, Caching) - Q2 2025

---

## 🚀 NEW FEATURES (Documented & Planned)

### 📌 PHASE: Data Operations (Q1 2025)

#### q:invoke - Universal Invocation Component
**Status:** Planned | **Priority:** High | **Effort:** 2-3 weeks

**Vision:** One tag to rule them all - invoke local functions, components, HTTP APIs, remote services, GraphQL, gRPC, etc.

**Key Innovation:** Instead of separate tags (q:http, q:rpc, q:graphql), use intelligent protocol detection based on attributes.

**Phase 1 Scope:**
- Local function calls (`function="..."`)
- Local component calls (`component="..."`)
- HTTP REST (GET, POST, PUT, DELETE, PATCH)
- Headers, query params, JSON body
- Bearer & API Key authentication
- Result objects with success/error
- Basic caching

**Phase 2 Scope:**
- GraphQL queries (`type="graphql"`)
- SOAP web services (`type="soap"`)
- Remote Quantum services (`service="..."`)
- OAuth 2.0 authentication

**Phase 3 Scope:**
- WebSockets (`type="websocket"`)
- gRPC (`type="grpc"`)
- Message queues (AMQP, Kafka)

**Example:**
```xml
<!-- HTTP API -->
<q:invoke name="weather" url="https://api.weather.com/forecast" method="GET">
    <q:header name="API-Key" value="{apiKey}" />
    <q:param name="city" value="{userCity}" />
</q:invoke>

<!-- Local function -->
<q:invoke name="total" function="calculateTotal">
    <q:arg name="items" value="{cart.items}" />
</q:invoke>

<!-- Remote service (same syntax!) -->
<q:invoke name="order" service="order-service" component="OrderService.create">
    <q:arg name="customerId" value="{customerId}" />
</q:invoke>
```

**Documentation:** `src/core/features/invocation/docs/README.md`

---

#### q:data - Data Import & Transformation Component
**Status:** Planned | **Priority:** High | **Effort:** 2-3 weeks

**Vision:** Declarative ETL for Quantum - import CSV/JSON/XML and transform data for use in components.

**Phase 1 Scope:**
- CSV import (files and URLs)
- JSON import (files and URLs)
- XML import with XPath (files and URLs)
- Basic transformations (filter, sort, limit)
- Type conversion and validation
- Result objects
- Caching

**Phase 2 Scope:**
- Compute (derived fields)
- Group and aggregate (sum, avg, count, min, max)
- Rename fields
- Map (extract fields)
- Join operations

**Phase 3 Scope:**
- Streaming for large files
- Chunked processing
- Parallel transformations

**Example:**
```xml
<!-- Import CSV -->
<q:data name="products" source="data/products.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
    <q:column name="price" type="decimal" />
</q:data>

<!-- Transform existing data -->
<q:data name="available" source="{products}" type="transform">
    <q:transform>
        <q:filter condition="{stock > 0}" />
        <q:sort by="price" order="asc" />
        <q:limit value="10" />
    </q:transform>
</q:data>
```

**Documentation:** `src/core/features/data_import/docs/README.md`

---

### 🤖 PHASE: AI Features (Q2-Q3 2025)

#### q:llm - LLM Integration Component
**Status:** Planned | **Priority:** High | **Effort:** 2 weeks

**Vision:** First template language with native LLM integration. Start with local models (LM Studio), optionally migrate to cloud.

**Key Innovation:**
- **Local first** - Use LM Studio (free, unlimited requests)
- **Cloud optional** - Migrate to OpenAI/Anthropic/Cohere later (just change endpoint!)

**Phase 1 Scope:**
- LM Studio completions API
- LM Studio chat API
- Basic parameters (temperature, max_tokens)
- JSON response format
- Prompt databinding
- Result objects
- Response caching

**Phase 2 Scope:**
- OpenAI API support
- Anthropic Claude API support
- Cohere API support
- Cost tracking

**Phase 3 Scope:**
- Streaming responses
- Function calling (tool use)
- Vision models
- Embeddings generation

**Use Cases:**
1. Content generation (product descriptions, emails, copy)
2. Text classification (sentiment, category, intent)
3. Data extraction (structured data from unstructured text)
4. Translation with context
5. Summarization
6. Content moderation

**Example:**
```xml
<!-- Generate product description -->
<q:llm name="description"
       endpoint="http://localhost:1234/v1/completions"
       model="local-model">
    <q:prompt>
        Write an engaging product description for: {product.name}
        Features: {product.features}
    </q:prompt>
    <q:param name="temperature" value="0.8" />
</q:llm>

<!-- Extract structured data -->
<q:llm name="extracted"
       endpoint="http://localhost:1234/v1/completions"
       response_format="json">
    <q:prompt>
        Extract contact info from: {text}
        Return JSON: {"name": "", "email": "", "phone": ""}
    </q:prompt>
</q:llm>
```

**Documentation:** `src/core/features/llm_integration/docs/README.md`

---

#### q:agent - AI Agents with Tool Use
**Status:** Planned | **Priority:** Medium | **Effort:** 3-4 weeks

**Vision:** Autonomous AI agents that can use tools (functions, queries, APIs) to complete complex, multi-step tasks.

**Key Innovation:** Similar to AutoGPT/LangChain, but native to Quantum templates with explicit tool permissions.

**Phase 1 Scope:**
- Agent reasoning loop (think → act → observe)
- Tool definition
- Function tools (q:function)
- Query tools (q:query)
- System instructions
- Action logging
- Safety limits (max_iterations, timeout)

**Phase 2 Scope:**
- Invoke tools (q:invoke)
- LLM tools (q:llm)
- Data tools (q:data)
- Tool approval flow
- Parallel tool execution

**Phase 3 Scope:**
- Multi-agent systems
- Agent memory/context persistence
- Agent chaining
- Hierarchical agents

**Example:**
```xml
<q:agent name="support"
         model="local-model"
         endpoint="http://localhost:1234/v1/chat/completions">

    <q:instruction>
        You are a customer support agent. Help users with their orders.
        Use the available tools to look up information and take actions.
    </q:instruction>

    <q:tool name="getOrder" description="Get order details by ID">
        <q:param name="orderId" type="integer" required="true" />
        <q:function name="getOrderById">
            <q:query name="order" datasource="db">
                SELECT * FROM orders WHERE id = :orderId
                <q:param name="orderId" value="{orderId}" type="integer" />
            </q:query>
            <q:return value="{order[0]}" />
        </q:function>
    </q:tool>

    <q:tool name="updateStatus" description="Update order status">
        <q:param name="orderId" type="integer" required="true" />
        <q:param name="status" type="string" required="true" />
        <q:function name="updateOrderStatus">
            <q:query name="update" datasource="db">
                UPDATE orders SET status = :status WHERE id = :orderId
                <q:param name="orderId" value="{orderId}" type="integer" />
                <q:param name="status" value="{status}" type="string" />
            </q:query>
            <q:return value="Order updated" />
        </q:function>
    </q:tool>

    <q:execute task="Check status of order #1234 and mark as shipped" />
</q:agent>

<!-- Agent autonomously: calls getOrder(1234), then updateStatus(1234, "shipped") -->
<p>{support.result}</p>
```

**Documentation:** `src/core/features/agents/docs/README.md`

---

## ✅ COMPLETED: State Management (`q:set`)

**Status:** 100% Complete
**Completion Date:** 2025-01-01

### Implemented Features

#### Core Functionality
- ✅ SetNode AST with full attribute support
- ✅ Parser for `<q:set>` tags
- ✅ ExecutionContext with scope management (local, function, component, session)
- ✅ Integration with ComponentRuntime
- ✅ Type system (string, number, decimal, boolean, date, datetime, array, object, json, binary, null)
- ✅ Basic assign operation with databinding support

#### Operations (18+ supported)
- ✅ Arithmetic: assign, increment, decrement, add, multiply
- ✅ Arrays: append, prepend, remove, removeAt, clear, sort, reverse, unique
- ✅ Objects: merge, setProperty, deleteProperty, clone
- ✅ Strings: uppercase, lowercase, trim, format

#### Validation System
- ✅ Runtime validation integrated
- ✅ Built-in validators (10+):
  - email, url, cpf, cnpj, phone, cep
  - uuid, creditcard, ipv4, ipv6
- ✅ CPF/CNPJ with digit verification
- ✅ Validation attributes:
  - required, nullable, range, enum
  - min, max, minlength, maxlength
  - validate, pattern
- ✅ Descriptive error messages

#### Testing
- ✅ 13 test files created and passing
- ✅ Basic operations tested
- ✅ Loop integration tested
- ✅ Validation scenarios tested
- ✅ Error handling verified

#### Documentation
- ✅ Complete VitePress documentation (`docs/guide/state-management.md`)
- ✅ 20+ code examples
- ✅ All operations documented
- ✅ All validators documented
- ✅ Practical use cases included

### Files Modified/Created
- **Created:**
  - `src/runtime/execution_context.py` (170 lines)
  - `src/runtime/validators.py` (240 lines)
  - `docs/guide/state-management.md` (800+ lines)
  - 13 test files in `examples/`

- **Modified:**
  - `src/core/ast_nodes.py` (+100 lines - SetNode)
  - `src/core/parser.py` (+50 lines - parse q:set)
  - `src/runtime/component.py` (+350 lines - execution + validation)

### Architecture Highlights

#### Scope Management
```python
ExecutionContext:
  - local_vars: {}
  - function_vars: {}
  - component_vars: {}
  - session_vars: {}
```

#### Validation Pipeline
```
Value → Type Conversion → Validation Rules → Set in Scope
```

#### Integration with Loops
Variables in parent scopes are properly updated from within loop bodies.

### Known Limitations
- ⏳ Computed properties (reactive updates) - not implemented
- ⏳ Lazy evaluation - not implemented
- ⏳ Memoization - not implemented
- ⏳ Built-in masks (auto-formatting) - not implemented

---

## ✅ COMPLETED: Function Definitions (`q:function`)

**Status:** 100% Complete
**Completion Date:** 2025-01-01

### Implemented Features

#### Core Functionality
- ✅ FunctionNode AST with multi-layer architecture
- ✅ Parser for `<q:function>` tags with all attributes
- ✅ FunctionRegistry for scope management
- ✅ Function calls via databinding `{functionName(args)}`
- ✅ Nested function calls
- ✅ Recursive functions
- ✅ Parameter system (required, optional, defaults)
- ✅ Return values with conditional logic
- ✅ Local variable scoping with ExecutionContext

#### Function Scopes
- ✅ Component scope (default): accessible within component
- ✅ Global scope: accessible from any component
- ✅ API scope: exposed as REST endpoints
- ✅ Access control: public, private, protected
- ✅ Private functions (underscore prefix or access="private")

#### REST API Integration (Optional)
- ✅ Expose functions as REST endpoints
- ✅ HTTP methods: GET, POST, PUT, PATCH, DELETE
- ✅ Parameter sources: path, query, body, header, cookie
- ✅ Content types: produces/consumes (JSON, XML, text)
- ✅ Authentication: jwt, basic, apikey
- ✅ Rate limiting, CORS, custom status codes

#### Validation
- ✅ Parameter validation with built-in validators
- ✅ Validators: email, cpf, cnpj, url, phone, uuid, date, json
- ✅ Range validation: min, max, minlength, maxlength
- ✅ Pattern validation (regex)
- ✅ Enum validation
- ✅ Integration with QuantumValidators

#### Performance Optimization
- ✅ Caching with TTL (cache="60s")
- ✅ Memoization (automatic result caching)
- ✅ Pure function marking
- ✅ Retry logic with timeout

#### Event System (Partial)
- ✅ DispatchEventNode and OnEventNode AST
- ✅ Event dispatch/subscribe parsing
- ⏳ Full event execution (future implementation)

### Testing
- ✅ 13 test files created and passing
- ✅ Basic function calls tested
- ✅ Parameters (required, optional, defaults)
- ✅ Nested and recursive calls
- ✅ Conditional logic in functions
- ✅ Local variables and scoping
- ✅ Array processing with loops
- ✅ String operations
- ✅ REST API endpoint definitions

### Documentation
- ✅ Complete documentation (`docs/guide/functions.md`)
- ✅ 10+ detailed examples
- ✅ REST API integration guide
- ✅ Validation guide
- ✅ Performance optimization guide
- ✅ Best practices

### Files Created/Modified
- **Created:**
  - `src/runtime/function_registry.py` (118 lines)
  - `docs/guide/functions.md` (800+ lines)
  - 13 test files in `examples/`

- **Modified:**
  - `src/core/ast_nodes.py` (+300 lines - FunctionNode, DispatchEventNode, OnEventNode, RestConfig, ComponentNode updates)
  - `src/core/parser.py` (+200 lines - parse q:function, q:dispatchEvent, q:onEvent)
  - `src/runtime/component.py` (+250 lines - function execution, validation, databinding fix)

### Architecture Highlights

#### Multi-Layer Function Architecture
```
FunctionNode:
  Layer 1: Core (name, return_type, scope, access, params, body)
  Layer 2: Documentation (description, hint)
  Layer 3: Validation (validate_params)
  Layer 4: Performance (cache, memoize, pure)
  Layer 5: Behavior (async, retry, timeout)
  Layer 6: REST API (optional RestConfig)
```

#### Function Resolution Order
```
1. Local component functions
2. Global functions (qualified name: Component.function)
3. Imported module functions
```

#### Critical Databinding Fix
Fixed `_apply_databinding()` to allow empty context, enabling function calls without existing variables.

### Known Limitations
- ⏳ Event system full execution - partial implementation
- ⏳ Async function execution - not implemented
- ⏳ Module imports - not implemented
- ⏳ REST API runtime server - configuration only

---

---

## 📋 PRIORITY 1: Loop Structures (`q:loop`)

### 🔍 CFLOOP Analysis

Based on Adobe ColdFusion's CFLOOP tag, we identified these loop types that should be supported in Quantum:

#### **1. Index/Range Loop (Numeric)**
```xml
<!-- CFLOOP equivalent: <cfloop index="i" from="1" to="10" step="1"> -->
<q:loop type="range" var="i" from="1" to="10" step="1">
  <q:return value="Item {i}" />
</q:loop>
```

#### **2. Array Loop**
```xml
<!-- CFLOOP equivalent: <cfloop array="#myArray#" index="idx" item="value"> -->
<q:loop type="array" var="item" index="idx" items="{myArray}">
  <q:return value="Index {idx}: {item}" />
</q:loop>
```

#### **3. List Loop**
```xml
<!-- CFLOOP equivalent: <cfloop list="#myList#" index="item" delimiters=","> -->
<q:loop type="list" var="item" items="apple,banana,orange" delimiter=",">
  <q:return value="Fruit: {item}" />
</q:loop>
```

#### **4. Object/Structure Loop**
```xml
<!-- CFLOOP equivalent: <cfloop collection="#myStruct#" item="key"> -->
<q:loop type="object" var="value" key="name" items="{myObject}">
  <q:return value="{name}: {value}" />
</q:loop>
```

#### **5. Query/Data Loop**
```xml
<!-- CFLOOP equivalent: <cfloop query="myQuery"> -->
<q:loop type="query" var="row" items="{queryResults}">
  <q:return value="Name: {row.name}, Age: {row.age}" />
</q:loop>
```

#### **6. Conditional Loop (While)**
```xml
<!-- CFLOOP equivalent: <cfloop condition="counter lt 10"> -->
<q:loop type="while" condition="{counter < 10}">
  <q:set name="counter" value="{counter + 1}" />
  <q:return value="Counter: {counter}" />
</q:loop>
```

### 🏗️ Implementation Architecture

#### **AST Node: LoopNode**
```python
class LoopNode(QuantumNode):
    def __init__(self, loop_type: str, var_name: str):
        self.loop_type = loop_type  # range, array, list, object, query, while
        self.var_name = var_name    # variable name for current item
        self.index_name = None      # optional index variable
        self.items = None           # data source
        self.condition = None       # for while loops
        self.from_value = None      # for range loops
        self.to_value = None        # for range loops  
        self.step_value = 1         # for range loops
        self.delimiter = ","        # for list loops
        self.body = []              # statements inside loop
```

#### **Parser Extension**
```python
def _parse_loop_statement(self, loop_element: ET.Element) -> LoopNode:
    loop_type = loop_element.get('type', 'range')
    var_name = loop_element.get('var')
    
    loop_node = LoopNode(loop_type, var_name)
    
    # Configure based on loop type
    if loop_type == 'range':
        loop_node.from_value = loop_element.get('from')
        loop_node.to_value = loop_element.get('to') 
        loop_node.step_value = int(loop_element.get('step', 1))
    elif loop_type == 'array' or loop_type == 'list':
        loop_node.items = loop_element.get('items')
        loop_node.index_name = loop_element.get('index')
    # ... other types
    
    # Parse loop body
    for child in loop_element:
        statement = self._parse_statement(child)
        if statement:
            loop_node.body.append(statement)
    
    return loop_node
```

#### **Runtime Execution**
```python
def _execute_loop(self, loop_node: LoopNode, context: Dict[str, Any]):
    if loop_node.loop_type == 'range':
        return self._execute_range_loop(loop_node, context)
    elif loop_node.loop_type == 'array':
        return self._execute_array_loop(loop_node, context)
    elif loop_node.loop_type == 'list':
        return self._execute_list_loop(loop_node, context)
    # ... other types

def _execute_range_loop(self, loop_node: LoopNode, context: Dict[str, Any]):
    results = []
    start = int(self._evaluate_expression(loop_node.from_value, context))
    end = int(self._evaluate_expression(loop_node.to_value, context))
    step = loop_node.step_value
    
    for i in range(start, end + 1, step):
        # Set loop variable in context
        loop_context = context.copy()
        loop_context[loop_node.var_name] = i
        
        # Execute loop body
        for statement in loop_node.body:
            result = self._execute_statement(statement, loop_context)
            if result is not None:
                results.append(result)
    
    return results
```

### 🧪 Testing Strategy

#### **Test Cases to Implement:**
1. **Range Loop**: Simple numeric iteration
2. **Array Loop**: Iterate over predefined arrays
3. **List Loop**: Comma/custom delimited strings
4. **Nested Loops**: Loop within loop scenarios
5. **Empty Collections**: Handle empty arrays/lists
6. **Edge Cases**: Invalid ranges, malformed data

#### **Example Test Files:**
```xml
<!-- examples/test-loop-range.q -->
<q:component name="TestRangeLoop">
  <q:loop type="range" var="i" from="1" to="3">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>

<!-- examples/test-loop-array.q -->
<q:component name="TestArrayLoop">
  <q:param name="fruits" type="array" default="['apple','banana','orange']" />
  <q:loop type="array" var="fruit" index="idx" items="{fruits}">
    <q:return value="{idx}: {fruit}" />
  </q:loop>
</q:component>
```

### 📈 Success Metrics
- [ ] All 6 loop types implemented and tested
- [ ] Nested loops working correctly
- [ ] Loop variables accessible in body
- [ ] Performance acceptable for reasonable data sizes
- [ ] Error handling for malformed loops

---

## 🚀 Next Steps
1. Start with Range Loop (simplest implementation)
2. Add Array Loop support
3. Implement List Loop
4. Add remaining loop types
5. Comprehensive testing
6. Documentation and examples

---

*Last updated: 2025-01-01*