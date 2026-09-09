"""Test object literal key bug"""
import re

# Test code
test_code = """var newProduct = {
    id: newId,
    name: formProductName,
    price: formProductPrice
};"""

print("ORIGINAL CODE:")
print(test_code)
print("\n" + "="*60)

# Current (buggy) regex - matches partial words!
buggy_regex = r'\b([a-zA-Z_]\w*)(?!\s*[\(:])'

# Fixed regex - complete word + negative lookahead AFTER the word
fixed_regex = r'\b([a-zA-Z_][\w]*)\b(?!\s*:)'

print("\nDEBUG: Checking why regex matches single letters:")
print(f"Buggy pattern: {buggy_regex}")
print(f"Fixed pattern: {fixed_regex}")
print("\nChecking 'id:' specifically:")
text = "id: value"

print("\nBUGGY REGEX:")
for i, m in enumerate(re.finditer(buggy_regex, text)):
    print(f"  Match {i}: '{m.group(0)}' at position {m.start()}-{m.end()}")

print("\nFIXED REGEX:")
for i, m in enumerate(re.finditer(fixed_regex, text)):
    print(f"  Match {i}: '{m.group(0)}' at position {m.start()}-{m.end()}")


def replace_identifier(match):
    ident = match.group(1)
    keywords = {'var', 'const', 'let'}

    if ident in keywords:
        return match.group(0)

    return f'this.{ident}'

result_buggy = re.sub(buggy_regex, replace_identifier, test_code)
result_fixed = re.sub(fixed_regex, replace_identifier, test_code)

print("\nRESULT WITH BUGGY REGEX:")
print(result_buggy)
print("\nRESULT WITH FIXED REGEX:")
print(result_fixed)
print("\n" + "="*60)

# Test if the negative lookahead works
print("\nTESTING REGEX PATTERNS:")

test_strings = [
    "id: value",
    "id :value",
    "id  : value",
    "id()",
    "id",
]

for test_str in test_strings:
    matches = list(re.finditer(buggy_regex, test_str))
    print(f"{test_str:20} -> {len(matches)} matches")
    for m in matches:
        print(f"  Matched: '{m.group(1)}'")
