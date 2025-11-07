# 🐛 BUG REPORT: Missing `else` Blocks in Compiled JavaScript

**Date**: 2025-01-07
**Severity**: CRITICAL (Breaks execution - SyntaxError)
**Affected Files**: All compiled applications with if-else statements
**Root Cause**: `codegen.py` line-by-line processing removes `} else {` lines

---

## 📋 **PROBLEM SUMMARY**

The Quantum MXML compiler (`quantum-as4`) is **removing all `else` blocks** from compiled JavaScript code, causing:

1. **Syntax Errors**: Unexpected `{` tokens
2. **Logic Errors**: Missing else branches
3. **Incomplete Blocks**: Unclosed `if` statements

**Browser Error:**
```
Uncaught SyntaxError: unexpected token: '{' app.js:2572:17
```

---

## 🔴 **REPRODUCTION**

### Step 1: Compile MXML with if-else
```bash
cd quantum-as4
./quantum-mxml examples/ecommerce-admin.mxml
```

### Step 2: Check compiled output
```bash
cd docs/ecommerce-admin
# Count else blocks in source
grep -c "} else {" ../../examples/ecommerce-admin.mxml
# Output: 2

# Count else blocks in compiled JavaScript
grep -c "} else {" app.js
# Output: 0  ← BUG: ALL else blocks removed!
```

### Step 3: Open in browser
```
http://localhost:8547/ecommerce-admin/
```

**Browser Console Error:**
```
Uncaught SyntaxError: unexpected token: '{' app.js:2572:17
```

---

## 📂 **FILE LOCATIONS**

### Source File (Correct ActionScript):
```
quantum-as4/examples/ecommerce-admin.mxml
```

### Compiled Output (Broken JavaScript):
```
quantum-as4/docs/ecommerce-admin/app.js (line 2572+)
```

### Compiler Source (Bug Location):
```
quantum-as4/compiler/codegen.py (lines 135-240: _transpile_body method)
```

---

## 🔍 **CONCRETE EXAMPLES**

### Example 1: saveProduct() Function (Line 2572)

**✅ CORRECT (Source MXML - lines ~380-410):**
```actionscript
public function saveProduct():void {
    if (selectedProduct != null) {
        // Update existing product
        selectedProduct.name = formProductName;
        selectedProduct.price = formProductPrice;
        selectedProduct.stock = formProductStock;
        selectedProduct.category = formProductCategory;

        Alert.show("Product updated successfully!", "Success", Alert.OK, null, null, Alert.INFO);
    } else {
        // Add new product
        var newId = products.length + 1;
        var newProduct = {
            id: newId,
            name: formProductName,
            category: formProductCategory,
            price: formProductPrice,
            stock: formProductStock,
            status: formProductStock > 20 ? "Active" : "Low Stock"
        };
        products.push(newProduct);

        Alert.show("Product added successfully!", "Success", Alert.OK, null, null, Alert.INFO);
    }

    editingProduct = false;
    selectedProduct = null;
}
```

**❌ INCORRECT (Generated JavaScript - lines 2572-2582):**
```javascript
saveProduct() {
  if (this.selectedProduct != null) {
  // Update existing product
  this.selectedProduct.name = this.formProductName;
  this.selectedProduct.price = this.formProductPrice;
  this.selectedProduct.stock = this.formProductStock;
  this.selectedProduct.category = this.formProductCategory;
  Alert.show("Product updated successfully!", "Success", Alert.OK, null, null, Alert.INFO);
}

cancelEdit() {  // ← Next function starts immediately! else block is GONE!
  this.editingProduct = false;
  this.selectedProduct = null;
}
```

**Problems:**
1. `} else {` line was **completely removed**
2. Entire `else` block (15+ lines) is **missing**
3. Function ends prematurely without closing properly
4. Next function `cancelEdit()` appears immediately

---

### Example 2: deleteProduct() Function (Line 2587)

**✅ CORRECT (Source MXML):**
```actionscript
public function deleteProduct():void {
    if (selectedProduct != null) {
        Alert.show("Product deleted: " + selectedProduct.name, "Deleted", Alert.OK, null, null, Alert.WARNING);
        // In real app, would remove from array
        selectedProduct = null;
    }
}
```

**❌ INCORRECT (Generated JavaScript):**
```javascript
deleteProduct() {
  if (this.selectedProduct != null) {
  Alert.show("Product deleted: " + this.selectedProduct.name, "Deleted", Alert.OK, null, null, Alert.WARNING);
  // In real app, would remove from array
  this.selectedProduct = null;
}  // ← Missing closing brace for the function!
```

**Problems:**
1. Only one closing `}` (closes if block)
2. Missing second `}` (should close function)
3. Causes next function to be nested inside this one

---

## 🔬 **ROOT CAUSE ANALYSIS**

### Location: `compiler/codegen.py` lines 135-240

The `_transpile_body()` method processes ActionScript line-by-line:

```python
def _transpile_body(self, body: str) -> list:
    """
    Transpile ActionScript function body to JavaScript

    Simplified approach: Just add 'this.' to known instance variables
    More sophisticated parsing can be added later
    """
    import re

    lines = []

    for line in body.split('\n'):  # ← BUG: Processes line-by-line
        line = line.strip()
        if not line:
            continue

        # ... process identifiers, add 'this.' prefix ...

        lines.append(line)

    return lines
```

**The Problem:**

1. **Line-by-line processing**: Doesn't understand block structure
2. **Empty line handling**: `} else {` becomes an empty line after stripping
3. **No AST awareness**: Doesn't track braces, blocks, or control flow
4. **Line skipping**: Lines with only structural elements (braces) are skipped

**What happens to `} else {`:**

```python
line = "} else {"
line = line.strip()  # → "} else {"
if not line:  # → False (line exists)
    continue

# Process identifiers:
# - "else" is in keywords set, so no replacement
# - No identifiers to add 'this.' to
# - Line has only structural elements

# But there's a bug in the regex logic:
# The line might be getting skipped or not properly appended
```

**Critical Issue:**

Looking at lines 146-154:

```python
for line in body.split('\n'):
    line = line.strip()
    if not line:
        continue  # ← Skips empty lines

    # Skip comment lines entirely
    if line.startswith('//'):
        lines.append(line)
        continue
```

**The `} else {` line doesn't match any special case**, so it should be processed normally. But looking at the regex logic (lines 207-230), the issue is:

```python
# Match word boundaries for identifiers
def replace_identifier(match):
    # ... check keywords, literals, globals ...
    return match.group(0)  # or f'this.{ident}'

# Replace identifiers: look for word followed by not-(
parts[i] = re.sub(r'\b([a-zA-Z_]\w*)(?!\s*\()', replace_identifier, parts[i])
```

**The regex pattern** `\b([a-zA-Z_]\w*)(?!\s*\()` matches:
- `} else {` → matches "else"
- Since "else" is a keyword, it returns unchanged
- Result should be: `} else {`

**But the line is being lost!** Let me check if there's a condition that skips it...

Actually, looking at the code flow:
1. Line comes in: `} else {`
2. Not empty, not a comment
3. No inline comment
4. Regex processes "else" → returns "else" (keyword)
5. Line should be: `} else {`
6. Line should be appended

**The bug must be in how the body is being split or joined!**

Let me check the AS4 parser...

---

## 🎯 **ACTUAL ROOT CAUSE**

After deeper analysis, the issue is likely in **how the function body is extracted** from the MXML, not in the transpilation itself.

**Hypothesis**: The AS4 parser (`as4_parser.py`) is not correctly extracting multi-line function bodies, particularly when `} else {` appears on its own line.

**Need to check:**
1. `as4_parser.py` - How it extracts function bodies
2. Whether it's preserving line breaks correctly
3. Whether it's handling braces correctly

---

## 🔧 **INVESTIGATION STEPS**

### Step 1: Check what the AS4 parser extracts

Add debug print to `codegen.py` line 90:

```python
# Before this line:
body_lines = self._transpile_body(func.body)

# Add:
print(f"DEBUG: Function {func.name} body:")
print(func.body)
print("=" * 50)
```

### Step 2: Re-compile and check output

```bash
./quantum-mxml examples/ecommerce-admin.mxml 2>&1 | grep -A 20 "saveProduct"
```

This will show us what the parser extracted vs what the transpiler output.

---

## 📊 **IMPACT**

### Affected Applications:
- ❌ **E-Commerce Admin Dashboard** (SyntaxError at line 2572)
- ❌ **Any app with if-else statements**

### Working Applications:
- ✅ Apps without else blocks (only simple if statements)
- ✅ Apps without ActionScript logic

### Statistics:
```bash
# Count else blocks in MXML examples:
find examples -name "*.mxml" -exec grep -l "} else {" {} \;
# Output: ecommerce-admin.mxml

# Count else blocks in compiled JS:
find docs -name "app.js" -exec grep -l "} else {" {} \;
# Output: (none)
```

**Affected Lines in ecommerce-admin.mxml:**
- Line ~395: `saveProduct()` function if-else
- Line ~445: `updateOrderStatus()` function if-else

---

## ✅ **EXPECTED BEHAVIOR**

After fixing, the compiled JavaScript should:

1. ✅ Preserve all `} else {` lines
2. ✅ Preserve all code inside else blocks
3. ✅ Maintain proper block structure
4. ✅ Close functions correctly
5. ✅ No SyntaxError in browser

**Expected output for saveProduct():**

```javascript
saveProduct() {
  if (this.selectedProduct != null) {
    // Update existing product
    this.selectedProduct.name = this.formProductName;
    this.selectedProduct.price = this.formProductPrice;
    this.selectedProduct.stock = this.formProductStock;
    this.selectedProduct.category = this.formProductCategory;
    Alert.show("Product updated successfully!", "Success", Alert.OK, null, null, Alert.INFO);
  } else {
    // Add new product
    var newId = this.products.length + 1;
    var newProduct = {
      id: newId,
      name: this.formProductName,
      category: this.formProductCategory,
      price: this.formProductPrice,
      stock: this.formProductStock,
      status: this.formProductStock > 20 ? "Active" : "Low Stock"
    };
    this.products.push(newProduct);
    Alert.show("Product added successfully!", "Success", Alert.OK, null, null, Alert.INFO);
  }

  this.editingProduct = false;
  this.selectedProduct = null;
}
```

---

## 🔧 **SUGGESTED FIX**

### Option A: Fix the line-by-line processing

Modify `_transpile_body()` to preserve structural lines:

```python
def _transpile_body(self, body: str) -> list:
    import re

    lines = []

    for line in body.split('\n'):
        original_line = line
        line = line.strip()

        if not line:
            continue

        # Preserve structural lines (braces, else, etc.)
        if re.match(r'^[\s\{\}]*$', line):  # Only braces/spaces
            lines.append(line)
            continue

        if re.match(r'^\}\s*else\s*\{$', line):  # } else {
            lines.append(line)
            continue

        # ... rest of processing ...
```

### Option B: Use proper AST parsing

Instead of line-by-line, use a proper JavaScript/TypeScript parser:

```python
import esprima  # or acorn.js

def _transpile_body(self, body: str) -> str:
    # Parse AS4 to AST
    ast = esprima.parseScript(body)

    # Walk AST and transform identifiers
    for node in ast.body:
        if node.type == 'Identifier':
            if not is_keyword(node.name):
                node.name = f'this.{node.name}'

    # Generate JavaScript from modified AST
    return escodegen.generate(ast)
```

This would properly preserve all structure.

---

## 🧪 **TEST CASES**

After fixing, these should compile correctly:

### Test 1: Simple if-else
```actionscript
if (condition) {
    doSomething();
} else {
    doSomethingElse();
}
```

**Should generate:**
```javascript
if (this.condition) {
    this.doSomething();
} else {
    this.doSomethingElse();
}
```

### Test 2: if-else-if chain
```actionscript
if (x > 10) {
    result = "high";
} else if (x > 5) {
    result = "medium";
} else {
    result = "low";
}
```

**Should generate:**
```javascript
if (this.x > 10) {
    this.result = "high";
} else if (this.x > 5) {
    this.result = "medium";
} else {
    this.result = "low";
}
```

### Test 3: Nested if-else
```actionscript
if (outer) {
    if (inner) {
        doA();
    } else {
        doB();
    }
} else {
    doC();
}
```

**Should generate:**
```javascript
if (this.outer) {
    if (this.inner) {
        this.doA();
    } else {
        this.doB();
    }
} else {
    this.doC();
}
```

---

## 🚀 **YOUR TASK**

Please investigate and fix:

1. **Debug the AS4 parser**: Check if function body extraction is correct
2. **Debug the transpiler**: Check why `} else {` lines are being lost
3. **Implement fix**: Either Option A (preserve structural lines) or Option B (proper AST)
4. **Test**: Recompile ecommerce-admin.mxml and verify no SyntaxError
5. **Verify**: Count else blocks in output should match source

**Good luck!** 🔍

---

**Repository**: https://github.com/danielgregorio/quantum
**Branch**: main
**Last Update**: 2025-01-07
