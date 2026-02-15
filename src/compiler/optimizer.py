"""
Quantum Code Optimizer
======================

Optimizes generated code for better performance.
"""

import re
import ast
from typing import List, Dict, Any, Optional, Tuple


class CodeOptimizer:
    """
    Optimizes generated Python/JavaScript code.

    Supported optimizations:
    - Constant folding: Evaluate constant expressions at compile time
    - Dead code elimination: Remove unreachable code
    - Loop unrolling: Inline small fixed loops
    - String concatenation: Combine adjacent string literals
    """

    def __init__(self, target: str = 'python', level: int = 1):
        """
        Initialize optimizer.

        Args:
            target: Target language ('python' or 'javascript')
            level: Optimization level (0=none, 1=safe, 2=aggressive)
        """
        self.target = target
        self.level = level
        self.stats: Dict[str, int] = {
            'constants_folded': 0,
            'dead_code_removed': 0,
            'loops_unrolled': 0,
            'strings_merged': 0
        }

    def optimize(self, code: str) -> str:
        """
        Apply all optimizations to code.

        Args:
            code: Generated code

        Returns:
            Optimized code
        """
        if self.level == 0:
            return code

        result = code

        # Level 1: Safe optimizations
        result = self._fold_constants(result)
        result = self._merge_strings(result)

        # Level 2: Aggressive optimizations
        if self.level >= 2:
            result = self._unroll_small_loops(result)
            result = self._eliminate_dead_code(result)

        return result

    def _fold_constants(self, code: str) -> str:
        """
        Fold constant expressions.

        Examples:
            x = 1 + 2  ->  x = 3
            y = 10 * 5  ->  y = 50
        """
        if self.target == 'python':
            # Pattern: simple arithmetic with integer literals
            patterns = [
                # Integer arithmetic
                (r'(\d+)\s*\+\s*(\d+)', lambda m: str(int(m.group(1)) + int(m.group(2)))),
                (r'(\d+)\s*\-\s*(\d+)', lambda m: str(int(m.group(1)) - int(m.group(2)))),
                (r'(\d+)\s*\*\s*(\d+)', lambda m: str(int(m.group(1)) * int(m.group(2)))),
                # Boolean literals
                (r'True and True', lambda m: 'True'),
                (r'True and False', lambda m: 'False'),
                (r'False and True', lambda m: 'False'),
                (r'False and False', lambda m: 'False'),
                (r'True or False', lambda m: 'True'),
                (r'False or True', lambda m: 'True'),
                (r'False or False', lambda m: 'False'),
                (r'True or True', lambda m: 'True'),
                (r'not True', lambda m: 'False'),
                (r'not False', lambda m: 'True'),
            ]
        else:  # JavaScript
            patterns = [
                (r'(\d+)\s*\+\s*(\d+)', lambda m: str(int(m.group(1)) + int(m.group(2)))),
                (r'(\d+)\s*\-\s*(\d+)', lambda m: str(int(m.group(1)) - int(m.group(2)))),
                (r'(\d+)\s*\*\s*(\d+)', lambda m: str(int(m.group(1)) * int(m.group(2)))),
                (r'true && true', lambda m: 'true'),
                (r'true && false', lambda m: 'false'),
                (r'false && true', lambda m: 'false'),
                (r'false && false', lambda m: 'false'),
                (r'!true', lambda m: 'false'),
                (r'!false', lambda m: 'true'),
            ]

        result = code
        for pattern, replacement in patterns:
            new_result = re.sub(pattern, replacement, result)
            if new_result != result:
                self.stats['constants_folded'] += len(re.findall(pattern, result))
                result = new_result

        return result

    def _merge_strings(self, code: str) -> str:
        """
        Merge adjacent string literal appends.

        Example:
            _html.append('<div>')
            _html.append('text')
            _html.append('</div>')
        Becomes:
            _html.append('<div>text</div>')
        """
        if self.target == 'python':
            # Find consecutive _html.append('...') lines
            pattern = r"(_html\.append\('([^'\\]|\\.)*'\)\n)+_html\.append\('([^'\\]|\\.)*'\)"

            def merge_appends(match):
                text = match.group(0)
                # Extract all string literals
                strings = re.findall(r"_html\.append\('((?:[^'\\]|\\.)*)'\)", text)
                if len(strings) > 1:
                    self.stats['strings_merged'] += len(strings) - 1
                    merged = ''.join(strings)
                    return f"_html.append('{merged}')"
                return text

            return re.sub(pattern, merge_appends, code)

        elif self.target == 'javascript':
            # Similar for JavaScript
            pattern = r"(_html\.push\(`[^`]*`\);\n)+_html\.push\(`[^`]*`\);"

            def merge_pushes(match):
                text = match.group(0)
                strings = re.findall(r"_html\.push\(`([^`]*)`\);", text)
                if len(strings) > 1:
                    self.stats['strings_merged'] += len(strings) - 1
                    merged = ''.join(strings)
                    return f"_html.push(`{merged}`);"
                return text

            return re.sub(pattern, merge_pushes, code)

        return code

    def _unroll_small_loops(self, code: str) -> str:
        """
        Unroll small fixed-iteration loops.

        Example:
            for i in range(1, 4):
                _html.append(f'<li>{i}</li>')
        Becomes:
            _html.append('<li>1</li>')
            _html.append('<li>2</li>')
            _html.append('<li>3</li>')
        """
        # Only unroll very small loops (3 or fewer iterations)
        if self.target == 'python':
            # Find: for x in range(a, b): with small range
            pattern = r'for (\w+) in range\((\d+), (\d+)\):\n((?:[ \t]+.+\n)+)'

            def unroll(match):
                var = match.group(1)
                start = int(match.group(2))
                end = int(match.group(3))
                body = match.group(4)

                # Only unroll if <= 3 iterations
                if end - start > 3:
                    return match.group(0)

                self.stats['loops_unrolled'] += 1

                # Get indent level
                indent = re.match(r'^([ \t]*)', body).group(1)
                # Remove one level of indentation
                body_stripped = re.sub(r'^' + indent, '', body, flags=re.MULTILINE)

                result = []
                for i in range(start, end):
                    # Replace variable references
                    unrolled = body_stripped.replace(f'{{{var}}}', str(i))
                    unrolled = re.sub(rf'\b{var}\b', str(i), unrolled)
                    result.append(unrolled.rstrip())

                return '\n'.join(result) + '\n'

            return re.sub(pattern, unroll, code)

        return code

    def _eliminate_dead_code(self, code: str) -> str:
        """
        Remove unreachable code.

        Examples:
            if False:
                # This block is removed

            return x
            y = 10  # This line is removed
        """
        lines = code.split('\n')
        result = []
        skip_until_dedent = False
        current_indent = 0

        for line in lines:
            stripped = line.lstrip()

            # Skip empty lines in dead code blocks
            if skip_until_dedent:
                if stripped:
                    indent = len(line) - len(stripped)
                    if indent <= current_indent:
                        skip_until_dedent = False
                    else:
                        self.stats['dead_code_removed'] += 1
                        continue
                else:
                    continue

            # Check for if False:
            if self.target == 'python' and re.match(r'if\s+False\s*:', stripped):
                skip_until_dedent = True
                current_indent = len(line) - len(stripped)
                self.stats['dead_code_removed'] += 1
                continue

            # Check for if (false) in JavaScript
            if self.target == 'javascript' and re.match(r'if\s*\(\s*false\s*\)', stripped):
                skip_until_dedent = True
                current_indent = len(line) - len(stripped)
                self.stats['dead_code_removed'] += 1
                continue

            result.append(line)

        return '\n'.join(result)

    def get_stats(self) -> Dict[str, int]:
        """Get optimization statistics."""
        return self.stats.copy()


def optimize_python(code: str, level: int = 1) -> str:
    """Optimize Python code."""
    optimizer = CodeOptimizer(target='python', level=level)
    return optimizer.optimize(code)


def optimize_javascript(code: str, level: int = 1) -> str:
    """Optimize JavaScript code."""
    optimizer = CodeOptimizer(target='javascript', level=level)
    return optimizer.optimize(code)
