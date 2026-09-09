"""Improved transpiler with better context awareness"""
import re

def transpile_body_v2(body: str) -> list:
    """Transpile ActionScript to JavaScript - Version 2"""
    lines = []

    for line in body.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Skip comment lines
        if line.startswith('//'):
            lines.append(line)
            continue

        # Handle inline comments
        comment_part = ""
        code_part = line
        if '//' in line:
            parts_temp = re.split(r'("(?:[^"\\]|\\.)*")', line)
            for i, part in enumerate(parts_temp):
                if i % 2 == 0 and '//' in part:
                    comment_idx = part.index('//')
                    code_part = ''.join(parts_temp[:i]) + part[:comment_idx]
                    comment_part = part[comment_idx:]
                    break

        # trace() → console.log()
        code_part = code_part.replace('trace(', 'console.log(')

        # Split by strings
        parts = re.split(r'("(?:[^"\\]|\\.)*")', code_part)

        for i in range(len(parts)):
            if i % 2 == 0:  # Only process non-string parts
                keywords = {
                    'const', 'let', 'var', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue',
                    'return', 'throw', 'try', 'catch', 'finally', 'function', 'class', 'extends', 'new', 'this', 'super',
                    'import', 'export', 'default', 'async', 'await', 'yield', 'typeof', 'instanceof', 'delete',
                    'void', 'in', 'of', 'with', 'debugger'
                }

                literals = {'true', 'false', 'null', 'undefined', 'NaN', 'Infinity'}

                global_classes = {
                    'Alert', 'Math', 'Date', 'String', 'Number', 'Boolean', 'Array', 'Object',
                    'JSON', 'console', 'window', 'document', 'navigator', 'location'
                }

                def replace_identifier(match):
                    ident = match.group(1)
                    full_match = match.group(0)
                    start_pos = match.start()

                    # Get text before and after the identifier
                    before_text = parts[i][:start_pos]
                    after_text = parts[i][match.end():]

                    # Don't prefix if preceded by dot (property access like items.length)
                    if before_text.rstrip().endswith('.'):
                        return full_match

                    # Don't prefix if after var/let/const
                    words_before = before_text.strip().split()
                    if words_before and words_before[-1] in {'var', 'let', 'const'}:
                        return full_match

                    # Don't prefix JavaScript keywords
                    if ident in keywords:
                        return full_match

                    # Don't prefix JavaScript literals
                    if ident in literals:
                        return full_match

                    # Don't prefix global classes
                    if ident in global_classes:
                        return full_match

                    # Check if already has this.
                    if full_match.startswith('this.'):
                        return full_match

                    # Add this. prefix for instance members
                    return f'this.{ident}'

                # Match identifiers with negative lookahead for : only
                # We DO want to match function calls like myMethod() -> this.myMethod()
                # We DON'T want to match object keys like { id: value }
                parts[i] = re.sub(r'\b([a-zA-Z_][\w]*)\b(?!\s*:)', replace_identifier, parts[i])

        line = ''.join(parts)

        if comment_part:
            line = line + ' ' + comment_part

        lines.append(line)

    return lines


# Test cases from previous version
test_cases = [
    ("Object Literals",
     """var product = {
    id: 123,
    name: productName,
    price: productPrice
};""",
     """var product = {
id: 123,
name: this.productName,
price: this.productPrice
};"""),

    ("Variable Declarations",
     """var count = 0;
let message = "hello";
const MAX = 100;""",
     """var count = 0;
let message = "hello";
const MAX = 100;"""),

    ("If Statements",
     """if (condition) {
    doSomething();
}""",
     """if (this.condition) {
this.doSomething();
}"""),

    ("Function Calls",
     """myFunction();
Alert.show("Message");""",
     """this.myFunction();
Alert.show("Message");"""),

    ("Property Access",
     """var len = items.length;
var name = user.name;""",
     """var len = this.items.length;
var name = this.user.name;"""),

    ("Boolean Literals",
     """isActive = true;
data = null;""",
     """this.isActive = true;
this.data = null;"""),

    ("Return Statement",
     """return value + 10;""",
     """return this.value + 10;"""),
]

# Run tests
print("=" * 70)
print("TRANSPILER V2 TEST SUITE")
print("=" * 70)

passed = 0
failed = 0

for test_name, input_code, expected_output in test_cases:
    print(f"\n[TEST] {test_name}")

    result_lines = transpile_body_v2(input_code)
    result = '\n'.join(result_lines)

    if result == expected_output:
        print("[PASS]")
        passed += 1
    else:
        print("[FAIL]")
        print("Expected:", repr(expected_output))
        print("Got:     ", repr(result))
        failed += 1

print(f"\n{'='*70}")
print(f"PASSED: {passed}/{len(test_cases)}")
print(f"FAILED: {failed}/{len(test_cases)}")
print('='*70)
