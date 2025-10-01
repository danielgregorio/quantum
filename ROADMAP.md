# Quantum Development Roadmap

## 🎯 Current Priority Order
1. **🔄 Loop Structures** (`q:loop`) - **PRIORITY 1**
2. **🔗 Variable Databinding** (`{variable}`) - **PRIORITY 2**  
3. **📝 State Management** (`q:set`) - **PRIORITY 3**
4. **⚙️ Function Definitions** (`q:function`) - **PRIORITY 4**
5. **🗃️ Database Integration** - User has different plans

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