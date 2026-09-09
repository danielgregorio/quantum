"""Debug regex matching"""
import re

regex = r'\b([a-zA-Z_][\w]*)\b(?!\s*[\(:])'

test_cases = [
    "doSomething()",
    "doSomething ()",
    "items.length",
    "id: value",
    "var count",
]

print("Testing regex:", regex)
print()

for test in test_cases:
    print(f"Input: {test!r}")
    matches = list(re.finditer(regex, test))
    print(f"  Matches: {len(matches)}")
    for m in matches:
        print(f"    - '{m.group(1)}' at pos {m.start()}-{m.end()}")
        # Check what's after the match
        after = test[m.end():m.end()+3]
        print(f"      After: {after!r}")
    print()
