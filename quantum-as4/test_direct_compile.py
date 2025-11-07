"""Test compilation directly with debug"""
import sys
sys.path.insert(0, 'compiler')

# Force reload to avoid cache
import importlib
if 'codegen' in sys.modules:
    importlib.reload(sys.modules['codegen'])

from mxml_parser import MXMLParser
from codegen import JSCodeGen

# Simple MXML with object literal
mxml_code = '''<?xml version="1.0" encoding="utf-8"?>
<s:Application xmlns:fx="http://ns.adobe.com/mxml/2009"
               xmlns:s="library://ns.adobe.com/flex/spark">
    <fx:Script>
    <![CDATA[
        private var products:Array = [];

        private function addProduct():void {
            var newProduct = {
                id: 123,
                name: productName,
                price: productPrice
            };
            products.push(newProduct);
        }
    ]]>
    </fx:Script>
</s:Application>'''

print("Parsing MXML...")
parser = MXMLParser()
app = parser.parse_string(mxml_code)

print("\nGenerating JavaScript...")
codegen = JSCodeGen()
output = codegen.generate(app)

print("\n" + "="*70)
print("GENERATED app.js:")
print("="*70)
# Find the addProduct function
lines = output['app.js'].split('\n')
in_function = False
for i, line in enumerate(lines):
    if 'addProduct()' in line:
        in_function = True
    if in_function:
        print(f"{i+1:4}: {line}")
        if line.strip() == '}' and 'var newProduct' in '\n'.join(lines[max(0, i-10):i]):
            break
