"""Test codegen transpiler directly"""
import sys
import re

# Copy the _transpile_body logic here
def transpile_body_test(body: str) -> list:
    lines = []

    for line in body.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Skip comment lines entirely
        if line.startswith('//'):
            lines.append(line)
            continue

        # Handle inline comments - split line into code and comment
        comment_part = ""
        code_part = line
        if '//' in line:
            # Find comment (but not in strings)
            parts_temp = re.split(r'("(?:[^"\\]|\\.)*")', line)
            for i, part in enumerate(parts_temp):
                if i % 2 == 0 and '//' in part:  # Non-string part with comment
                    comment_idx = part.index('//')
                    # Reconstruct: everything before comment
                    code_part = ''.join(parts_temp[:i]) + part[:comment_idx]
                    comment_part = part[comment_idx:]
                    break

        # Simple transformations
        # trace() → console.log()
        code_part = code_part.replace('trace(', 'console.log(')

        # For now, use a simple regex approach that preserves strings
        # Replace bare identifiers with this.identifier (but not in strings)

        # Split by strings to avoid replacing inside them
        parts = re.split(r'("(?:[^"\\]|\\.)*")', code_part)

        for i in range(len(parts)):
            # Only process non-string parts (even indices)
            if i % 2 == 0:
                # Add this. to identifiers that are NOT:
                # - keywords
                # - already prefixed with this.
                # - followed by (  (function calls)
                # - numbers

                # JavaScript keywords that should NEVER have 'this.' prefix
                keywords = {
                    'const', 'let', 'var', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue',
                    'return', 'throw', 'try', 'catch', 'finally', 'function', 'class', 'extends', 'new', 'this', 'super',
                    'import', 'export', 'default', 'async', 'await', 'yield', 'typeof', 'instanceof', 'delete',
                    'void', 'in', 'of', 'with', 'debugger'
                }

                # JavaScript literals that should NEVER have 'this.' prefix
                literals = {'true', 'false', 'null', 'undefined', 'NaN', 'Infinity'}

                # Known global classes that are used as static members (don't prefix)
                global_classes = {
                    'Alert', 'Math', 'Date', 'String', 'Number', 'Boolean', 'Array', 'Object',
                    'JSON', 'console', 'window', 'document', 'navigator', 'location'
                }

                # Match word boundaries for identifiers
                def replace_identifier(match):
                    ident = match.group(1)

                    # Don't prefix JavaScript keywords
                    if ident in keywords:
                        return match.group(0)

                    # Don't prefix JavaScript literals
                    if ident in literals:
                        return match.group(0)

                    # Don't prefix global classes (likely static member access like Alert.show)
                    if ident in global_classes:
                        return match.group(0)

                    # Check if already has this.
                    if match.group(0).startswith('this.'):
                        return match.group(0)

                    # Add this. prefix for instance members
                    return f'this.{ident}'

                # Replace identifiers: complete word + negative lookahead for :
                # This avoids adding this. to:
                # - Function calls: foo() (excluded by (?!\s*\()
                # - Object literal keys: { id: value } (excluded by (?!\s*:))
                # Using \b at both ends ensures we match complete words
                parts[i] = re.sub(r'\b([a-zA-Z_][\w]*)\b(?!\s*[\(:])', replace_identifier, parts[i])

        line = ''.join(parts)

        # Add comment back if it was present
        if comment_part:
            line = line + ' ' + comment_part

        lines.append(line)

    return lines

# Create test MXML with object literal
test_body = """
var newProduct = {
    id: newId,
    name: formProductName,
    price: formProductPrice
};
products.push(newProduct);
"""

print("INPUT ActionScript:")
print(test_body)
print("\n" + "="*60)

# Call transpiler
result = transpile_body_test(test_body)

print("\nOUTPUT JavaScript:")
for line in result:
    print(line)
