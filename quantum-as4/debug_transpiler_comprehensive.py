"""Comprehensive transpiler test - all edge cases"""
import re

def transpile_body(body: str) -> list:
    """Transpile ActionScript to JavaScript"""
    lines = []

    for line in body.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Skip comment lines entirely
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

        # Split by strings to avoid replacing inside them
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

                    # Get context before the identifier
                    start_pos = match.start()
                    before_text = parts[i][:start_pos].strip()

                    # Don't prefix if after var/let/const declaration
                    if before_text.endswith(('var', 'let', 'const')):
                        return match.group(0)

                    # Don't prefix JavaScript keywords
                    if ident in keywords:
                        return match.group(0)

                    # Don't prefix JavaScript literals
                    if ident in literals:
                        return match.group(0)

                    # Don't prefix global classes
                    if ident in global_classes:
                        return match.group(0)

                    # Check if already has this.
                    if match.group(0).startswith('this.'):
                        return match.group(0)

                    # Add this. prefix for instance members
                    return f'this.{ident}'

                # Replace identifiers: complete word + negative lookahead for ( and :
                parts[i] = re.sub(r'\b([a-zA-Z_][\w]*)\b(?!\s*[\(:])', replace_identifier, parts[i])

        line = ''.join(parts)

        if comment_part:
            line = line + ' ' + comment_part

        lines.append(line)

    return lines


# Test cases
test_cases = [
    # Test 1: Object literals
    (
        "Object Literals",
        """var product = {
    id: 123,
    name: productName,
    price: productPrice
};""",
        """var product = {
id: 123,
name: this.productName,
price: this.productPrice
};"""
    ),

    # Test 2: Variable declarations
    (
        "Variable Declarations",
        """var count = 0;
let message = "hello";
const MAX = 100;""",
        """var count = 0;
let message = "hello";
const MAX = 100;"""
    ),

    # Test 3: If statements
    (
        "If Statements",
        """if (condition) {
    doSomething();
} else {
    doOther();
}""",
        """if (this.condition) {
this.doSomething();
} else {
this.doOther();
}"""
    ),

    # Test 4: Function calls
    (
        "Function Calls",
        """Alert.show("Message", "Title");
myFunction();""",
        """Alert.show("Message", "Title");
this.myFunction();"""
    ),

    # Test 5: Property access
    (
        "Property Access",
        """var len = items.length;
var name = user.name;""",
        """var len = this.items.length;
var name = this.user.name;"""
    ),

    # Test 6: Boolean literals
    (
        "Boolean Literals",
        """isActive = true;
isValid = false;
data = null;""",
        """this.isActive = true;
this.isValid = false;
this.data = null;"""
    ),

    # Test 7: Mixed complex case
    (
        "Mixed Complex",
        """var newUser = {
    id: userId,
    name: userName,
    active: true
};
users.push(newUser);""",
        """var newUser = {
id: this.userId,
name: this.userName,
active: true
};
this.users.push(newUser);"""
    ),

    # Test 8: Return statement
    (
        "Return Statement",
        """return value + 10;""",
        """return this.value + 10;"""
    ),
]

# Run tests
print("=" * 70)
print("COMPREHENSIVE TRANSPILER TEST SUITE")
print("=" * 70)

passed = 0
failed = 0

for test_name, input_code, expected_output in test_cases:
    print(f"\n[TEST] {test_name}")
    print("-" * 70)

    result_lines = transpile_body(input_code)
    result = '\n'.join(result_lines)

    if result == expected_output:
        print("[PASS]")
        passed += 1
    else:
        print("[FAIL]")
        print("\nExpected:")
        print(expected_output)
        print("\nGot:")
        print(result)
        print("\nDifferences:")
        expected_lines = expected_output.split('\n')
        result_lines_split = result.split('\n')
        for i, (exp, got) in enumerate(zip(expected_lines, result_lines_split)):
            if exp != got:
                print(f"  Line {i+1}:")
                print(f"    Expected: {repr(exp)}")
                print(f"    Got:      {repr(got)}")
        failed += 1

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Passed: {passed}/{len(test_cases)}")
print(f"Failed: {failed}/{len(test_cases)}")
print("=" * 70)
