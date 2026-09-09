"""
Expression Transformer
======================

Transforms Quantum expressions to target language syntax.
Handles differences between Python and JavaScript expression syntax.
"""

import ast
import re
from typing import Optional, Dict, Any


class ExpressionTransformer:
    """
    Transforms Quantum expressions to target language.

    Quantum expressions are Python-like but need transformation for:
    - JavaScript: == becomes ===, and/or become &&/||
    - Both: property access, method calls, list comprehensions
    """

    # Built-in function mappings
    PYTHON_BUILTINS = {
        'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set',
        'sum', 'min', 'max', 'abs', 'round', 'range', 'enumerate',
        'sorted', 'reversed', 'zip', 'map', 'filter', 'any', 'all',
        'upper', 'lower', 'strip', 'split', 'join', 'replace',
        'startswith', 'endswith', 'format', 'isinstance', 'type',
    }

    # Python to JavaScript function mappings
    PY_TO_JS_FUNCTIONS = {
        'len': lambda arg: f'{arg}.length',
        'str': lambda arg: f'String({arg})',
        'int': lambda arg: f'parseInt({arg})',
        'float': lambda arg: f'parseFloat({arg})',
        'bool': lambda arg: f'Boolean({arg})',
        'abs': lambda arg: f'Math.abs({arg})',
        'round': lambda arg: f'Math.round({arg})',
        'min': lambda *args: f'Math.min({", ".join(args)})',
        'max': lambda *args: f'Math.max({", ".join(args)})',
        'sum': lambda arg: f'{arg}.reduce((a, b) => a + b, 0)',
        'sorted': lambda arg: f'[...{arg}].sort()',
        'reversed': lambda arg: f'[...{arg}].reverse()',
        'range': '_range',  # Special handling needed
        'enumerate': '_enumerate',  # Special handling needed
    }

    # Python string methods to JavaScript
    PY_TO_JS_METHODS = {
        'upper': 'toUpperCase',
        'lower': 'toLowerCase',
        'strip': 'trim',
        'lstrip': 'trimStart',
        'rstrip': 'trimEnd',
        'split': 'split',
        'join': '_join',  # Special: "sep".join(list) -> list.join("sep")
        'replace': 'replace',
        'startswith': 'startsWith',
        'endswith': 'endsWith',
        'find': 'indexOf',
        'count': '_count',  # Special handling
        'isdigit': '_isDigit',  # Special handling
        'isalpha': '_isAlpha',  # Special handling
    }

    def __init__(self, target: str = 'python'):
        """
        Initialize the transformer.

        Args:
            target: Target language ('python' or 'javascript')
        """
        self.target = target.lower()

    def transform(self, expr: str) -> str:
        """
        Transform a Quantum expression to target language.

        Args:
            expr: The expression to transform (may have {})

        Returns:
            Transformed expression string
        """
        if not expr:
            return ''

        expr = str(expr).strip()

        # Remove { } wrapper if present
        if expr.startswith('{') and expr.endswith('}'):
            expr = expr[1:-1].strip()

        if not expr:
            return ''

        # Quick path: if no transformation needed
        if self.target == 'python' and not self._needs_transformation(expr):
            return expr

        try:
            # Parse as Python AST
            tree = ast.parse(expr, mode='eval')
            return self._transform_node(tree.body)
        except SyntaxError:
            # Fallback: return as-is with basic transformations
            return self._basic_transform(expr)

    def _needs_transformation(self, expr: str) -> bool:
        """Check if expression needs any transformation."""
        # For Python target, most expressions work as-is
        if self.target == 'python':
            return False
        # For JavaScript, check for Python-specific syntax
        return any(x in expr for x in ['and ', 'or ', 'not ', ' in ', 'True', 'False', 'None'])

    def _basic_transform(self, expr: str) -> str:
        """Apply basic transformations without full AST parsing."""
        if self.target == 'javascript':
            # Replace Python operators with JavaScript equivalents
            expr = re.sub(r'\band\b', '&&', expr)
            expr = re.sub(r'\bor\b', '||', expr)
            expr = re.sub(r'\bnot\b', '!', expr)
            expr = re.sub(r'\bTrue\b', 'true', expr)
            expr = re.sub(r'\bFalse\b', 'false', expr)
            expr = re.sub(r'\bNone\b', 'null', expr)
            # == to === (careful with !=)
            expr = re.sub(r'([^!<>=])={2}([^=])', r'\1===\2', expr)
            expr = re.sub(r'!=', '!==', expr)
        return expr

    def _transform_node(self, node: ast.expr) -> str:
        """Transform an AST node to target language."""
        method_name = f'_transform_{type(node).__name__}'
        transformer = getattr(self, method_name, self._transform_default)
        return transformer(node)

    def _transform_default(self, node: ast.expr) -> str:
        """Default transformation: use Python's unparse."""
        result = ast.unparse(node)
        if self.target == 'javascript':
            return self._basic_transform(result)
        return result

    # =========================================================================
    # AST Node Transformers
    # =========================================================================

    def _transform_Constant(self, node: ast.Constant) -> str:
        """Transform constants."""
        value = node.value
        if value is True:
            return 'true' if self.target == 'javascript' else 'True'
        elif value is False:
            return 'false' if self.target == 'javascript' else 'False'
        elif value is None:
            return 'null' if self.target == 'javascript' else 'None'
        elif isinstance(value, str):
            # Use repr for proper escaping
            return repr(value)
        else:
            return str(value)

    def _transform_Name(self, node: ast.Name) -> str:
        """Transform variable names."""
        name = node.id
        if self.target == 'javascript':
            # Map Python built-in names to JavaScript
            mappings = {'True': 'true', 'False': 'false', 'None': 'null'}
            return mappings.get(name, name)
        return name

    def _transform_BinOp(self, node: ast.BinOp) -> str:
        """Transform binary operations."""
        left = self._transform_node(node.left)
        right = self._transform_node(node.right)
        op = self._get_binop(node.op)
        return f'({left} {op} {right})'

    def _get_binop(self, op: ast.operator) -> str:
        """Get binary operator string."""
        ops = {
            ast.Add: '+',
            ast.Sub: '-',
            ast.Mult: '*',
            ast.Div: '/',
            ast.FloorDiv: '//' if self.target == 'python' else 'Math.floor(/',
            ast.Mod: '%',
            ast.Pow: '**',
            ast.BitOr: '|',
            ast.BitXor: '^',
            ast.BitAnd: '&',
            ast.LShift: '<<',
            ast.RShift: '>>',
        }
        return ops.get(type(op), '+')

    def _transform_Compare(self, node: ast.Compare) -> str:
        """Transform comparison operations."""
        left = self._transform_node(node.left)
        parts = [left]

        for op, comparator in zip(node.ops, node.comparators):
            comp_str = self._transform_node(comparator)

            if isinstance(op, ast.Eq):
                parts.append('===' if self.target == 'javascript' else '==')
            elif isinstance(op, ast.NotEq):
                parts.append('!==' if self.target == 'javascript' else '!=')
            elif isinstance(op, ast.Lt):
                parts.append('<')
            elif isinstance(op, ast.LtE):
                parts.append('<=')
            elif isinstance(op, ast.Gt):
                parts.append('>')
            elif isinstance(op, ast.GtE):
                parts.append('>=')
            elif isinstance(op, ast.In):
                if self.target == 'javascript':
                    # x in y -> y.includes(x)
                    return f'{comp_str}.includes({left})'
                parts.append('in')
            elif isinstance(op, ast.NotIn):
                if self.target == 'javascript':
                    return f'!{comp_str}.includes({left})'
                parts.append('not in')
            elif isinstance(op, ast.Is):
                parts.append('===' if self.target == 'javascript' else 'is')
            elif isinstance(op, ast.IsNot):
                parts.append('!==' if self.target == 'javascript' else 'is not')
            else:
                parts.append('==')

            parts.append(comp_str)

        return ' '.join(parts)

    def _transform_BoolOp(self, node: ast.BoolOp) -> str:
        """Transform boolean operations (and/or)."""
        if isinstance(node.op, ast.And):
            op = '&&' if self.target == 'javascript' else 'and'
        else:
            op = '||' if self.target == 'javascript' else 'or'

        values = [self._transform_node(v) for v in node.values]
        return f' {op} '.join(f'({v})' for v in values)

    def _transform_UnaryOp(self, node: ast.UnaryOp) -> str:
        """Transform unary operations."""
        operand = self._transform_node(node.operand)

        if isinstance(node.op, ast.Not):
            op = '!' if self.target == 'javascript' else 'not '
        elif isinstance(node.op, ast.USub):
            op = '-'
        elif isinstance(node.op, ast.UAdd):
            op = '+'
        elif isinstance(node.op, ast.Invert):
            op = '~'
        else:
            op = ''

        return f'{op}{operand}'

    def _transform_IfExp(self, node: ast.IfExp) -> str:
        """Transform ternary/conditional expressions."""
        test = self._transform_node(node.test)
        body = self._transform_node(node.body)
        orelse = self._transform_node(node.orelse)

        if self.target == 'javascript':
            return f'({test} ? {body} : {orelse})'
        else:
            return f'({body} if {test} else {orelse})'

    def _transform_Attribute(self, node: ast.Attribute) -> str:
        """Transform attribute access."""
        value = self._transform_node(node.value)
        attr = node.attr

        if self.target == 'javascript':
            # Map Python methods to JavaScript
            if attr in self.PY_TO_JS_METHODS:
                js_method = self.PY_TO_JS_METHODS[attr]
                if not js_method.startswith('_'):
                    return f'{value}.{js_method}'
                # Special handling needed - return as-is for now
                return f'{value}.{attr}'

        return f'{value}.{attr}'

    def _transform_Subscript(self, node: ast.Subscript) -> str:
        """Transform subscript access (indexing)."""
        value = self._transform_node(node.value)
        slice_node = node.slice

        if isinstance(slice_node, ast.Constant):
            index = self._transform_node(slice_node)
            return f'{value}[{index}]'
        elif isinstance(slice_node, ast.Slice):
            return self._transform_slice(value, slice_node)
        else:
            index = self._transform_node(slice_node)
            return f'{value}[{index}]'

    def _transform_slice(self, value: str, node: ast.Slice) -> str:
        """Transform slice operations."""
        lower = self._transform_node(node.lower) if node.lower else ''
        upper = self._transform_node(node.upper) if node.upper else ''
        step = self._transform_node(node.step) if node.step else ''

        if self.target == 'javascript':
            if step:
                # JavaScript doesn't have native slice with step
                return f'{value}.slice({lower or 0}, {upper or "undefined"})'
            return f'{value}.slice({lower or 0}, {upper or "undefined"})'
        else:
            return f'{value}[{lower}:{upper}{":" + step if step else ""}]'

    def _transform_Call(self, node: ast.Call) -> str:
        """Transform function calls."""
        args = [self._transform_node(arg) for arg in node.args]
        kwargs = [f'{kw.arg}={self._transform_node(kw.value)}' for kw in node.keywords]
        all_args = ', '.join(args + kwargs)

        # Handle method calls
        if isinstance(node.func, ast.Attribute):
            obj = self._transform_node(node.func.value)
            method = node.func.attr

            if self.target == 'javascript':
                # Special method mappings
                if method == 'join':
                    # Python: "sep".join(list) -> JS: list.join("sep")
                    return f'{args[0]}.join({obj})'
                elif method in self.PY_TO_JS_METHODS:
                    js_method = self.PY_TO_JS_METHODS[method]
                    if not js_method.startswith('_'):
                        return f'{obj}.{js_method}({all_args})'

            return f'{obj}.{method}({all_args})'

        # Handle regular function calls
        if isinstance(node.func, ast.Name):
            func_name = node.func.id

            if self.target == 'javascript' and func_name in self.PY_TO_JS_FUNCTIONS:
                mapping = self.PY_TO_JS_FUNCTIONS[func_name]
                if callable(mapping):
                    return mapping(*args)
                # Special handling marker
                if mapping == '_range':
                    return self._js_range(args)
                elif mapping == '_enumerate':
                    return f'{args[0]}.entries()'

            return f'{func_name}({all_args})'

        # Fallback
        func = self._transform_node(node.func)
        return f'{func}({all_args})'

    def _js_range(self, args: list) -> str:
        """Generate JavaScript range equivalent."""
        if len(args) == 1:
            return f'Array.from({{length: {args[0]}}}, (_, i) => i)'
        elif len(args) == 2:
            return f'Array.from({{length: {args[1]} - {args[0]}}}, (_, i) => i + {args[0]})'
        else:
            return f'Array.from({{length: Math.ceil(({args[1]} - {args[0]}) / {args[2]})}}, (_, i) => {args[0]} + i * {args[2]})'

    def _transform_List(self, node: ast.List) -> str:
        """Transform list literals."""
        elements = [self._transform_node(el) for el in node.elts]
        return f'[{", ".join(elements)}]'

    def _transform_Dict(self, node: ast.Dict) -> str:
        """Transform dictionary literals."""
        pairs = []
        for key, value in zip(node.keys, node.values):
            k = self._transform_node(key) if key else '...'
            v = self._transform_node(value)
            if self.target == 'javascript' and isinstance(key, ast.Constant) and isinstance(key.value, str):
                # JavaScript object literal with string keys
                pairs.append(f'{key.value}: {v}')
            else:
                pairs.append(f'{k}: {v}')

        if self.target == 'javascript':
            return '{' + ', '.join(pairs) + '}'
        else:
            return '{' + ', '.join(pairs) + '}'

    def _transform_ListComp(self, node: ast.ListComp) -> str:
        """Transform list comprehensions."""
        if self.target == 'javascript':
            return self._listcomp_to_js(node)
        else:
            return ast.unparse(node)

    def _listcomp_to_js(self, node: ast.ListComp) -> str:
        """Convert list comprehension to JavaScript map/filter."""
        gen = node.generators[0]
        var = self._transform_node(gen.target)
        iterable = self._transform_node(gen.iter)
        expr = self._transform_node(node.elt)

        if gen.ifs:
            # Has filter condition
            conditions = [self._transform_node(if_) for if_ in gen.ifs]
            filter_expr = ' && '.join(f'({c})' for c in conditions)
            return f'{iterable}.filter({var} => {filter_expr}).map({var} => {expr})'
        else:
            return f'{iterable}.map({var} => {expr})'

    def _transform_Lambda(self, node: ast.Lambda) -> str:
        """Transform lambda expressions."""
        args = ', '.join(arg.arg for arg in node.args.args)
        body = self._transform_node(node.body)

        if self.target == 'javascript':
            return f'({args}) => {body}'
        else:
            return f'lambda {args}: {body}'

    def _transform_JoinedStr(self, node: ast.JoinedStr) -> str:
        """Transform f-strings."""
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                expr = self._transform_node(value.value)
                if self.target == 'javascript':
                    parts.append('${' + expr + '}')
                else:
                    parts.append('{' + expr + '}')

        if self.target == 'javascript':
            return '`' + ''.join(parts) + '`'
        else:
            return "f'" + ''.join(parts) + "'"
