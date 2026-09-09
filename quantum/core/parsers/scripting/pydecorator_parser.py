"""
PyDecorator Parser - Parse q:decorator statements
"""

import textwrap
from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import PyDecoratorNode


class PyDecoratorParser(BaseTagParser):
    """
    Parser for q:decorator statements for Python decorator definitions.

    Examples:
        <!-- Caching decorator -->
        <q:decorator name="cached">
            from functools import wraps
            def decorator(func):
                cache = {}
                @wraps(func)
                def wrapper(*args):
                    if args in cache:
                        return cache[args]
                    result = func(*args)
                    cache[args] = result
                    return result
                return wrapper
            return decorator
        </q:decorator>

        <!-- Decorator with parameters -->
        <q:decorator name="retry" params="attempts, delay">
            import time
            def decorator(func):
                def wrapper(*args, **kwargs):
                    for i in range(attempts):
                        try:
                            return func(*args, **kwargs)
                        except Exception as e:
                            if i == attempts - 1:
                                raise
                            time.sleep(delay)
                return wrapper
            return decorator
        </q:decorator>
    """

    @property
    def tag_names(self) -> List[str]:
        return ['decorator', 'pydecorator']

    def parse(self, element: ET.Element) -> PyDecoratorNode:
        """Parse q:decorator element"""
        name = element.get('name', '')
        code = element.text or ""
        code = textwrap.dedent(code).strip()

        # Parse params (comma-separated)
        params_str = element.get('params', '')
        params = [p.strip() for p in params_str.split(',') if p.strip()]

        return PyDecoratorNode(
            name=name,
            code=code,
            params=params
        )
