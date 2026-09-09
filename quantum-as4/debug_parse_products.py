"""Test AS4 parser to see what it captures for products array"""
import sys
sys.path.insert(0, 'compiler')
from compiler.as4_parser import AS4Parser

# Sample code from ecommerce-admin.mxml (exactly as it appears)
code = """[Bindable] public var products:Array = [
    {id: 1, name: "Laptop Pro 15\"", category: "Electronics", price: 1299.99, stock: 45, status: "Active"},
    {id: 2, name: "Wireless Mouse", category: "Electronics", price: 29.99, stock: 156, status: "Active"}
];

[Bindable] public var selectedProduct:Object = null;"""

parser = AS4Parser()
ast = parser.parse(code)

print("VARIABLES FOUND:")
for var in ast.variables:
    print(f"\nVariable: {var.name}")
    print(f"  Type: {var.type}")
    print(f"  Bindable: {var.is_bindable}")
    print(f"  Value: {repr(var.value)}")
    if var.value:
        print(f"  Value length: {len(var.value)} characters")
