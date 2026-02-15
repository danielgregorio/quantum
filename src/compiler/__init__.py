"""
Quantum Transpiler
==================

Transpiles Quantum (.q) files to native Python and JavaScript code.

Usage:
    from compiler import Transpiler

    transpiler = Transpiler(target='python')
    result = transpiler.compile_file('app.q')
    print(result.code)

CLI:
    quantum compile app.q -o app.py
    quantum compile app.q -o app.js --target=javascript
"""

from .transpiler import Transpiler, CompilationResult
from .base_generator import CodeGenerator
from .expression_transformer import ExpressionTransformer

__all__ = [
    'Transpiler',
    'CompilationResult',
    'CodeGenerator',
    'ExpressionTransformer',
]

__version__ = '1.0.0'
