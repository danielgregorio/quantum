"""Test transpiler with var assignment containing instance variable reference"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compiler'))
from compiler.compilers.web import WebCompiler
from pathlib import Path

# Create a test case that mimics the bug
test_code = """var newId = products.length + 1;
var currentStatus = selectedOrder.status;"""

print("INPUT:")
print(test_code)
print("\nPROCESSING...")

# Create WebCompiler instance
compiler = WebCompiler(Path('.'))

# Transpile the body
result = compiler._transpile_body(test_code)

print("\nOUTPUT:")
for line in result:
    print(line)

print("\n" + "="*70)
print("EXPECTED:")
print("var newId = this.products.length + 1;")
print("var currentStatus = this.selectedOrder.status;")
print("="*70)
