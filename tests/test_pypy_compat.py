"""
Tests for PyPy Compatibility Module - Phase 3 Performance Optimization

These tests verify that the compatibility layer works correctly
on both CPython and PyPy implementations.
"""

import pytest
import platform
from unittest.mock import patch, MagicMock

from runtime.pypy_compat import (
    is_pypy,
    is_cpython,
    get_python_version,
    get_implementation_info,
    DependencyChecker,
    PyPyOptimizer,
    QuantumPyPyAdapter,
    CompatibilityResult,
)


class TestRuntimeDetection:
    """Tests for runtime detection functions"""

    def test_is_pypy_or_cpython(self):
        """One of is_pypy() or is_cpython() should be True"""
        # At least one should be true (unless running on Jython, etc.)
        impl = platform.python_implementation()
        if impl == 'PyPy':
            assert is_pypy() is True
            assert is_cpython() is False
        elif impl == 'CPython':
            assert is_pypy() is False
            assert is_cpython() is True

    def test_get_python_version(self):
        """Version should be a tuple of 3 integers"""
        version = get_python_version()
        assert isinstance(version, tuple)
        assert len(version) == 3
        assert all(isinstance(v, int) for v in version)
        assert version[0] >= 3  # Python 3+

    def test_get_implementation_info(self):
        """Info dict should contain expected keys"""
        info = get_implementation_info()

        assert 'implementation' in info
        assert 'version' in info
        assert 'version_tuple' in info
        assert 'is_pypy' in info
        assert 'is_cpython' in info
        assert 'platform' in info

        # Consistency check
        assert info['is_pypy'] == is_pypy()
        assert info['is_cpython'] == is_cpython()

    @patch('platform.python_implementation')
    def test_is_pypy_mocked(self, mock_impl):
        """Test is_pypy with mocked implementation"""
        mock_impl.return_value = 'PyPy'
        assert is_pypy() is True

        mock_impl.return_value = 'CPython'
        assert is_pypy() is False

    @patch('platform.python_implementation')
    def test_is_cpython_mocked(self, mock_impl):
        """Test is_cpython with mocked implementation"""
        mock_impl.return_value = 'CPython'
        assert is_cpython() is True

        mock_impl.return_value = 'PyPy'
        assert is_cpython() is False


class TestCompatibilityResult:
    """Tests for CompatibilityResult dataclass"""

    def test_result_creation(self):
        result = CompatibilityResult(
            name='flask',
            compatible=True,
            message='Works great',
            severity='info',
        )
        assert result.name == 'flask'
        assert result.compatible is True
        assert result.severity == 'info'

    def test_result_with_workaround(self):
        result = CompatibilityResult(
            name='lxml',
            compatible=True,
            message='Needs cffi',
            severity='warning',
            workaround='pip install lxml-cffi',
        )
        assert result.workaround == 'pip install lxml-cffi'


class TestDependencyChecker:
    """Tests for DependencyChecker"""

    def test_check_flask(self):
        result = DependencyChecker.check_dependency('flask')
        assert result.name == 'flask'
        assert result.compatible is True
        assert result.severity == 'info'

    def test_check_sqlite3(self):
        result = DependencyChecker.check_dependency('sqlite3')
        assert result.compatible is True
        assert 'builtin' in result.message.lower() or 'compatible' in result.message.lower()

    def test_check_lxml(self):
        result = DependencyChecker.check_dependency('lxml')
        assert result.compatible is True  # With caveats
        assert result.severity == 'warning'

    def test_check_uvloop(self):
        result = DependencyChecker.check_dependency('uvloop')
        assert result.compatible is False
        assert result.severity == 'error'

    def test_check_unknown_package(self):
        result = DependencyChecker.check_dependency('unknown_package_xyz')
        assert result.compatible is True  # Assume compatible
        assert 'unknown' in result.message.lower()

    def test_check_quantum_dependencies(self):
        results = DependencyChecker.check_quantum_dependencies()
        assert len(results) > 0

        # All core deps should be at least somewhat compatible
        for result in results:
            assert result.compatible is True or result.severity != 'error'

    def test_case_insensitive(self):
        result1 = DependencyChecker.check_dependency('Flask')
        result2 = DependencyChecker.check_dependency('FLASK')
        result3 = DependencyChecker.check_dependency('flask')

        assert result1.compatible == result2.compatible == result3.compatible


class TestPyPyOptimizer:
    """Tests for PyPyOptimizer"""

    def test_get_recommendations(self):
        recs = PyPyOptimizer.get_recommendations()
        assert isinstance(recs, list)
        assert len(recs) > 0
        assert all(isinstance(r, str) for r in recs)

    def test_optimize_for_jit(self):
        # Should not raise
        PyPyOptimizer.optimize_for_jit()

    def test_warmup_jit(self):
        # Should not raise, even with many iterations
        PyPyOptimizer.warmup_jit(iterations=10)

    def test_warmup_jit_minimal(self):
        # Should handle 0 iterations
        PyPyOptimizer.warmup_jit(iterations=0)


class TestQuantumPyPyAdapter:
    """Tests for QuantumPyPyAdapter"""

    def test_get_memory_usage(self):
        memory = QuantumPyPyAdapter.get_memory_usage()
        assert isinstance(memory, float)
        assert memory >= 0

    def test_gc_collect(self):
        # Should not raise
        QuantumPyPyAdapter.gc_collect()

    def test_compile_expression_eval(self):
        code = QuantumPyPyAdapter.compile_expression("x + y * 2")
        assert code is not None

        # Should be executable
        result = eval(code, {}, {'x': 10, 'y': 5})
        assert result == 20

    def test_compile_expression_exec(self):
        code = QuantumPyPyAdapter.compile_expression("result = x + 1", mode='exec')
        assert code is not None

        # Should be executable
        context = {'x': 10}
        exec(code, {}, context)
        assert context['result'] == 11


class TestCrossImplementation:
    """Tests that verify code works on both CPython and PyPy"""

    def test_dict_operations(self):
        """Dictionary operations should work identically"""
        d = {'a': 1, 'b': 2, 'c': 3}

        assert d.get('a') == 1
        assert d.get('missing', 'default') == 'default'
        assert len(d) == 3

        d['d'] = 4
        assert 'd' in d

        del d['a']
        assert 'a' not in d

    def test_list_comprehensions(self):
        """List comprehensions should work identically"""
        result = [x * 2 for x in range(10)]
        assert result == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

    def test_generator_expressions(self):
        """Generator expressions should work identically"""
        gen = (x * 2 for x in range(5))
        result = list(gen)
        assert result == [0, 2, 4, 6, 8]

    def test_string_operations(self):
        """String operations should work identically"""
        s = "Hello World"

        assert s.upper() == "HELLO WORLD"
        assert s.lower() == "hello world"
        assert s.split() == ["Hello", "World"]
        assert s.replace("World", "PyPy") == "Hello PyPy"
        assert f"{s}!" == "Hello World!"

    def test_exception_handling(self):
        """Exception handling should work identically"""
        caught = False
        try:
            raise ValueError("test error")
        except ValueError as e:
            caught = True
            assert str(e) == "test error"

        assert caught is True

    def test_context_managers(self):
        """Context managers should work identically"""
        class TestContext:
            def __init__(self):
                self.entered = False
                self.exited = False

            def __enter__(self):
                self.entered = True
                return self

            def __exit__(self, *args):
                self.exited = True

        ctx = TestContext()
        with ctx:
            assert ctx.entered is True
        assert ctx.exited is True

    def test_decorators(self):
        """Decorators should work identically"""
        def double(func):
            def wrapper(*args):
                return func(*args) * 2
            return wrapper

        @double
        def add(a, b):
            return a + b

        assert add(3, 4) == 14  # (3 + 4) * 2

    def test_lambda_functions(self):
        """Lambda functions should work identically"""
        add = lambda x, y: x + y
        assert add(3, 4) == 7

        square = lambda x: x ** 2
        assert list(map(square, [1, 2, 3])) == [1, 4, 9]

    def test_class_inheritance(self):
        """Class inheritance should work identically"""
        class Base:
            def greet(self):
                return "Hello"

        class Child(Base):
            def greet(self):
                return super().greet() + " World"

        c = Child()
        assert c.greet() == "Hello World"

    def test_dataclasses(self):
        """Dataclasses should work identically"""
        from dataclasses import dataclass

        @dataclass
        class Point:
            x: int
            y: int

        p = Point(3, 4)
        assert p.x == 3
        assert p.y == 4

    def test_typing(self):
        """Type hints should work identically (not enforced)"""
        from typing import List, Dict, Optional

        def process(items: List[int]) -> Dict[str, int]:
            return {'sum': sum(items), 'count': len(items)}

        result = process([1, 2, 3])
        assert result == {'sum': 6, 'count': 3}


class TestPerformanceCriticalPaths:
    """
    Tests for performance-critical code paths that must work
    efficiently on both CPython and PyPy.
    """

    def test_expression_compilation(self):
        """Expression compilation should be fast and correct"""
        expressions = [
            ("1 + 2", {}, 3),
            ("x * y", {'x': 3, 'y': 4}, 12),
            ("a > b", {'a': 5, 'b': 3}, True),
            ("len(items)", {'items': [1, 2, 3]}, 3),
        ]

        for expr, ctx, expected in expressions:
            code = compile(expr, '<test>', 'eval')
            result = eval(code, {}, ctx)
            assert result == expected

    def test_loop_performance(self):
        """Loops should complete in reasonable time"""
        import time

        start = time.perf_counter()
        total = 0
        for i in range(10000):
            total += i
        elapsed = time.perf_counter() - start

        assert total == 49995000  # Correct result
        assert elapsed < 1.0  # Should be fast

    def test_dict_lookup_performance(self):
        """Dictionary lookups should be fast"""
        import time

        d = {f"key{i}": i for i in range(1000)}

        start = time.perf_counter()
        for _ in range(10000):
            _ = d.get("key500")
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0  # Should be very fast


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
