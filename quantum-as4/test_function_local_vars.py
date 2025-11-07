"""Test that function-local variables are NOT parsed as class variables"""
import sys
sys.path.insert(0, 'compiler')
from compiler.as4_parser import AS4Parser

# Sample code with class vars AND function-local vars
code = """
[Bindable] public var products:Array = [];
[Bindable] public var selectedProduct:Object = null;

public function saveProduct():void {
    var newId = products.length + 1;
    var newProduct = {
        id: newId,
        name: formProductName
    };
    products.push(newProduct);
}

public function updateStatus():void {
    var currentStatus = selectedOrder.status;
    var newStatus = "Active";
}
"""

parser = AS4Parser()
ast = parser.parse(code)

print("=" * 70)
print("CLASS-LEVEL VARIABLES (should be 2):")
print("=" * 70)
for var in ast.variables:
    print(f"  - {var.name}: {var.type} = {repr(var.value)[:50]}...")

print(f"\nTotal: {len(ast.variables)} class variables")

print("\n" + "=" * 70)
print("FUNCTIONS (should be 2):")
print("=" * 70)
for func in ast.functions:
    print(f"  - {func.name}() with {len(func.body.split('var'))-1} local vars")

print(f"\nTotal: {len(ast.functions)} functions")

# Check result
print("\n" + "=" * 70)
if len(ast.variables) == 2:
    print("[PASS] Correctly parsed only class variables")
else:
    print(f"[FAIL] Expected 2 class variables, got {len(ast.variables)}")
    print("Extra variables found:")
    for var in ast.variables[2:]:
        print(f"  - {var.name} (should be function-local)")
print("=" * 70)
