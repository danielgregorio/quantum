"""
Tests for Expression Cache - Phase 1 Performance Optimization

Tests cover:
- Basic expression evaluation
- Cache hit/miss tracking
- Thread safety
- Security (dangerous expressions blocked)
- DataBinding integration
- Performance benchmarks
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from runtime.expression_cache import (
    ExpressionCache,
    DataBindingCache,
    CacheStats,
    get_expression_cache,
    get_databinding_cache,
    evaluate_expression,
    evaluate_condition,
)


class TestCacheStats:
    """Tests for CacheStats dataclass"""

    def test_initial_values(self):
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.compilations == 0
        assert stats.evaluations == 0

    def test_hit_rate_zero_when_empty(self):
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        stats = CacheStats(hits=80, misses=20)
        assert stats.hit_rate == 0.8

    def test_avg_compile_time(self):
        stats = CacheStats(compilations=10, total_compile_time_ms=50.0)
        assert stats.avg_compile_time_ms == 5.0

    def test_to_dict(self):
        stats = CacheStats(hits=10, misses=5)
        d = stats.to_dict()
        assert d['hits'] == 10
        assert d['misses'] == 5
        assert '66.7%' in d['hit_rate']


class TestExpressionCache:
    """Tests for ExpressionCache class"""

    @pytest.fixture
    def cache(self):
        """Fresh cache for each test"""
        return ExpressionCache(max_size=100)

    # Basic Evaluation Tests

    def test_evaluate_simple_arithmetic(self, cache):
        result = cache.evaluate("2 + 3", {})
        assert result == 5

    def test_evaluate_multiplication(self, cache):
        result = cache.evaluate("4 * 5", {})
        assert result == 20

    def test_evaluate_with_variables(self, cache):
        result = cache.evaluate("x + y", {"x": 10, "y": 20})
        assert result == 30

    def test_evaluate_complex_expression(self, cache):
        result = cache.evaluate("(x + y) * z - 5", {"x": 2, "y": 3, "z": 4})
        assert result == 15

    def test_evaluate_comparison(self, cache):
        result = cache.evaluate("x > y", {"x": 10, "y": 5})
        assert result is True

    def test_evaluate_boolean_logic(self, cache):
        result = cache.evaluate("x > 0 and y < 10", {"x": 5, "y": 3})
        assert result is True

    def test_evaluate_string_operations(self, cache):
        result = cache.evaluate("name + ' ' + greeting", {"name": "World", "greeting": "Hello"})
        assert result == "World Hello"

    def test_evaluate_list_operations(self, cache):
        result = cache.evaluate("len(items)", {"items": [1, 2, 3, 4, 5]})
        assert result == 5

    def test_evaluate_with_builtins(self, cache):
        result = cache.evaluate("max(a, b, c)", {"a": 1, "b": 5, "c": 3})
        assert result == 5

    def test_evaluate_conditional_expression(self, cache):
        result = cache.evaluate("'yes' if x > 0 else 'no'", {"x": 5})
        assert result == 'yes'

    def test_evaluate_empty_expression(self, cache):
        result = cache.evaluate("", {})
        assert result is None

    def test_evaluate_whitespace_expression(self, cache):
        result = cache.evaluate("   ", {})
        assert result is None

    # Error Handling Tests

    def test_evaluate_undefined_variable(self, cache):
        with pytest.raises(ValueError, match="Undefined variable"):
            cache.evaluate("undefined_var + 1", {})

    def test_evaluate_syntax_error(self, cache):
        with pytest.raises(ValueError, match="Syntax error"):
            cache.evaluate("2 + * 3", {})  # Invalid: can't have * after +

    def test_evaluate_dangerous_import(self, cache):
        with pytest.raises(ValueError, match="unsafe"):
            cache.evaluate("__import__('os')", {})

    def test_evaluate_dangerous_exec(self, cache):
        with pytest.raises(ValueError, match="unsafe"):
            cache.evaluate("exec('print(1)')", {})

    def test_evaluate_dangerous_eval(self, cache):
        with pytest.raises(ValueError, match="unsafe"):
            cache.evaluate("eval('1+1')", {})

    def test_evaluate_dangerous_open(self, cache):
        with pytest.raises(ValueError, match="unsafe"):
            cache.evaluate("open('/etc/passwd')", {})

    def test_evaluate_dangerous_dunder(self, cache):
        with pytest.raises(ValueError, match="unsafe"):
            cache.evaluate("x.__class__", {"x": 1})

    # Condition Evaluation Tests

    def test_evaluate_condition_true(self, cache):
        result = cache.evaluate_condition("x > 5", {"x": 10})
        assert result is True

    def test_evaluate_condition_false(self, cache):
        result = cache.evaluate_condition("x > 5", {"x": 3})
        assert result is False

    def test_evaluate_condition_complex(self, cache):
        result = cache.evaluate_condition(
            "x > 0 and y > 0 and x + y < 100",
            {"x": 10, "y": 20}
        )
        assert result is True

    # Cache Behavior Tests

    def test_cache_hit_on_repeated_expression(self, cache):
        # First evaluation - miss
        cache.evaluate("x + 1", {"x": 10})
        initial_misses = cache.stats.misses

        # Second evaluation - hit
        cache.evaluate("x + 1", {"x": 20})

        assert cache.stats.hits > 0
        assert cache.stats.misses == initial_misses

    def test_different_expressions_different_cache_entries(self, cache):
        cache.evaluate("x + 1", {"x": 10})
        cache.evaluate("x + 2", {"x": 10})

        # Both should be compiled
        assert cache.stats.compilations >= 2

    def test_same_expression_different_context(self, cache):
        # Same expression with different contexts should hit cache
        result1 = cache.evaluate("x * 2", {"x": 5})
        result2 = cache.evaluate("x * 2", {"x": 10})

        assert result1 == 10
        assert result2 == 20
        # Only one compilation
        info = cache.cache_info()
        assert info['hits'] >= 1

    def test_precompile(self, cache):
        expressions = ["x + 1", "y * 2", "z - 3"]
        results = cache.precompile(expressions)

        assert all(error is None for error in results.values())
        assert cache.cache_info()['size'] == 3

    def test_precompile_with_errors(self, cache):
        expressions = ["x + 1", "invalid syntax +-", "y * 2"]
        results = cache.precompile(expressions)

        assert results["x + 1"] is None
        assert results["y * 2"] is None
        assert results["invalid syntax +-"] is not None

    def test_cache_clear(self, cache):
        cache.evaluate("x + 1", {"x": 10})
        assert cache.cache_info()['size'] > 0

        cache.clear()
        assert cache.cache_info()['size'] == 0
        assert cache.stats.hits == 0

    # Variable Substitution Tests

    def test_substitute_variables_numeric(self, cache):
        result = cache.substitute_variables("x + y", {"x": 10, "y": 20})
        assert result == "10 + 20"

    def test_substitute_variables_string(self, cache):
        result = cache.substitute_variables("name", {"name": "Alice"})
        assert result == "'Alice'"

    def test_substitute_variables_partial(self, cache):
        # Should not replace 'x' in 'max'
        result = cache.substitute_variables("max(x, y)", {"x": 10, "y": 20})
        assert "max" in result  # 'max' should remain unchanged

    def test_substitute_longer_vars_first(self, cache):
        # 'count' should be replaced before 'c'
        result = cache.substitute_variables("count + c", {"count": 10, "c": 5})
        assert "10" in result
        assert "5" in result


class TestDataBindingCache:
    """Tests for DataBindingCache class"""

    @pytest.fixture
    def cache(self):
        return DataBindingCache()

    def test_apply_simple_variable(self, cache):
        result = cache.apply("{x}", {"x": 42})
        assert result == 42

    def test_apply_expression(self, cache):
        result = cache.apply("{x + y}", {"x": 10, "y": 20})
        assert result == 30

    def test_apply_mixed_content(self, cache):
        result = cache.apply("Hello {name}!", {"name": "World"})
        assert result == "Hello World!"

    def test_apply_multiple_expressions(self, cache):
        result = cache.apply("{a} + {b} = {c}", {"a": 2, "b": 3, "c": 5})
        assert result == "2 + 3 = 5"

    def test_apply_no_expressions(self, cache):
        result = cache.apply("Plain text", {})
        assert result == "Plain text"

    def test_apply_empty_text(self, cache):
        result = cache.apply("", {})
        assert result == ""

    def test_apply_none_text(self, cache):
        result = cache.apply(None, {})
        assert result is None

    def test_apply_undefined_variable(self, cache):
        # Should return original placeholder for undefined variables
        result = cache.apply("Value: {undefined}", {})
        assert result == "Value: {undefined}"


class TestThreadSafety:
    """Tests for thread-safe cache operations"""

    def test_concurrent_evaluations(self):
        cache = ExpressionCache(max_size=100)
        results = []
        errors = []

        def evaluate_task(i):
            try:
                result = cache.evaluate(f"x + {i}", {"x": 100})
                results.append(result)
            except Exception as e:
                errors.append(str(e))

        with ThreadPoolExecutor(max_workers=10) as executor:
            for i in range(100):
                executor.submit(evaluate_task, i)

        assert len(errors) == 0
        assert len(results) == 100

    def test_concurrent_different_expressions(self):
        cache = ExpressionCache(max_size=100)
        expressions = [
            "x + 1", "x * 2", "x - 3", "x / 4", "x ** 2",
            "x + y", "x * y", "x - y", "x > y", "x < y"
        ]
        results = []

        def evaluate_task(expr):
            result = cache.evaluate(expr, {"x": 10, "y": 5})
            results.append(result)

        threads = []
        for expr in expressions * 10:  # 100 total evaluations
            t = threading.Thread(target=evaluate_task, args=(expr,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(results) == 100


class TestGlobalCaches:
    """Tests for global singleton caches"""

    def test_get_expression_cache_singleton(self):
        cache1 = get_expression_cache()
        cache2 = get_expression_cache()
        assert cache1 is cache2

    def test_get_databinding_cache_singleton(self):
        cache1 = get_databinding_cache()
        cache2 = get_databinding_cache()
        assert cache1 is cache2

    def test_evaluate_expression_function(self):
        result = evaluate_expression("2 + 2", {})
        assert result == 4

    def test_evaluate_condition_function(self):
        result = evaluate_condition("x > 5", {"x": 10})
        assert result is True


class TestPerformance:
    """Performance benchmarks for the cache"""

    def test_cache_speedup(self):
        """Verify that cached expressions are faster than recompiling each time"""
        cache = ExpressionCache(max_size=100)
        expr = "x * y + z - w / 2"
        context = {"x": 10, "y": 20, "z": 30, "w": 40}

        # Warm up - first evaluation (cache miss)
        cache.evaluate(expr, context)

        # Time cached evaluations (compile once, eval many times)
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            cache.evaluate(expr, context)
        cached_time = time.perf_counter() - start

        # Time uncached evaluations (compile + eval each time)
        start = time.perf_counter()
        for _ in range(iterations):
            code = compile(expr, '<test>', 'eval')
            eval(code, {}, context)
        uncached_time = time.perf_counter() - start

        # Cached should be significantly faster than recompiling each time
        # The compile step is expensive, so cache should win handily
        assert cached_time < uncached_time

    def test_hit_rate_improves(self):
        """Verify hit rate improves with repeated expressions"""
        cache = ExpressionCache(max_size=100)
        expressions = ["x + 1", "x + 2", "x + 3", "x + 4", "x + 5"]

        # First pass - all misses
        for expr in expressions:
            cache.evaluate(expr, {"x": 10})

        initial_hit_rate = cache.stats.hit_rate

        # Second pass - all hits
        for expr in expressions:
            cache.evaluate(expr, {"x": 20})

        final_hit_rate = cache.stats.hit_rate

        assert final_hit_rate > initial_hit_rate
        assert final_hit_rate >= 0.5


class TestBuiltinFunctions:
    """Tests for safe built-in functions"""

    @pytest.fixture
    def cache(self):
        return ExpressionCache()

    def test_len(self, cache):
        assert cache.evaluate("len(items)", {"items": [1, 2, 3]}) == 3

    def test_max_min(self, cache):
        assert cache.evaluate("max(items)", {"items": [1, 5, 3]}) == 5
        assert cache.evaluate("min(items)", {"items": [1, 5, 3]}) == 1

    def test_sum(self, cache):
        assert cache.evaluate("sum(items)", {"items": [1, 2, 3, 4]}) == 10

    def test_abs(self, cache):
        assert cache.evaluate("abs(x)", {"x": -5}) == 5

    def test_round(self, cache):
        assert cache.evaluate("round(x, 2)", {"x": 3.14159}) == 3.14

    def test_str_int_float(self, cache):
        assert cache.evaluate("int(x)", {"x": "42"}) == 42
        assert cache.evaluate("float(x)", {"x": "3.14"}) == 3.14
        assert cache.evaluate("str(x)", {"x": 42}) == "42"

    def test_bool(self, cache):
        assert cache.evaluate("bool(x)", {"x": 1}) is True
        assert cache.evaluate("bool(x)", {"x": 0}) is False

    def test_list_operations(self, cache):
        assert cache.evaluate("list(range(5))", {}) == [0, 1, 2, 3, 4]
        assert cache.evaluate("sorted(items)", {"items": [3, 1, 2]}) == [1, 2, 3]

    def test_type_checking(self, cache):
        assert cache.evaluate("isinstance(x, int)", {"x": 42}) is True
        assert cache.evaluate("isinstance(x, str)", {"x": 42}) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
