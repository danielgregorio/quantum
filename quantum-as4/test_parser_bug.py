"""
Test to demonstrate the else block bug in AS4 parser
"""

import re

# This is the CURRENT (BUGGY) regex from as4_parser.py line 182
buggy_pattern = r'(?:async\s+)?(?:private|public)?\s*function\s+(\w+)\s*\((.*?)\)\s*(?::(\w+(?:<\w+>)?)?)?\s*\{(.*?)\}'

# Test code with if-else
test_code = '''
public function saveProduct():void {
    if (selectedProduct != null) {
        Alert.show("Update");
    } else {
        Alert.show("Add");
    }
    editingProduct = false;
}
'''

print("=" * 60)
print("BUGGY REGEX TEST")
print("=" * 60)

matches = list(re.finditer(buggy_pattern, test_code, re.DOTALL))
print(f"Number of matches: {len(matches)}")

for i, match in enumerate(matches):
    name = match.group(1)
    body = match.group(4)

    print(f"\nFunction {i+1}: {name}")
    print(f"Body extracted:\n{body}")
    print(f"\nBody length: {len(body)} characters")

    # Check if else is present
    if 'else' in body:
        print("[OK] else block found")
    else:
        print("[FAIL] else block MISSING!")

print("\n" + "=" * 60)
print("EXPECTED BEHAVIOR")
print("=" * 60)
print("Should extract full function body including else block")
print("Body should contain: if block + else block + editingProduct assignment")

# Let's try a better regex that counts braces
print("\n" + "=" * 60)
print("TESTING BRACE-COUNTING APPROACH")
print("=" * 60)

# Find function start
func_start_pattern = r'(?:private|public)?\s*function\s+(\w+)\s*\((.*?)\)\s*(?::(\w+))?\s*\{'
match = re.search(func_start_pattern, test_code)

if match:
    func_name = match.group(1)
    start_pos = match.end()  # Position right after opening {

    # Count braces to find matching closing brace
    brace_count = 1
    i = start_pos

    while i < len(test_code) and brace_count > 0:
        if test_code[i] == '{':
            brace_count += 1
        elif test_code[i] == '}':
            brace_count -= 1
        i += 1

    # Extract body between opening and closing braces
    body = test_code[start_pos:i-1]

    print(f"Function: {func_name}")
    print(f"Body extracted:\n{body}")
    print(f"\nBody length: {len(body)} characters")

    if 'else' in body:
        print("[OK] else block found")
    else:
        print("[FAIL] else block MISSING!")
