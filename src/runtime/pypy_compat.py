"""
PyPy Compatibility Module - Phase 3 Performance Optimization

Ensures Quantum Framework runs correctly on both CPython and PyPy.
PyPy provides automatic JIT compilation for 5-10x speedup on hot paths.

Features:
- Runtime detection of Python implementation
- Alternative implementations for incompatible code
- Performance recommendations for PyPy users
- Dependency compatibility checks

Usage:
    from runtime.pypy_compat import is_pypy, get_implementation_info

    if is_pypy():
        # PyPy-specific optimizations
        pass
"""

import sys
import platform
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass


# Runtime detection
def is_pypy() -> bool:
    """Check if running on PyPy"""
    return platform.python_implementation() == 'PyPy'


def is_cpython() -> bool:
    """Check if running on CPython"""
    return platform.python_implementation() == 'CPython'


def get_python_version() -> Tuple[int, int, int]:
    """Get Python version as tuple"""
    return sys.version_info[:3]


def get_implementation_info() -> Dict[str, Any]:
    """Get detailed information about the Python implementation"""
    return {
        'implementation': platform.python_implementation(),
        'version': platform.python_version(),
        'version_tuple': get_python_version(),
        'compiler': platform.python_compiler(),
        'is_pypy': is_pypy(),
        'is_cpython': is_cpython(),
        'is_64bit': sys.maxsize > 2**32,
        'platform': sys.platform,
    }


@dataclass
class CompatibilityResult:
    """Result of a compatibility check"""
    name: str
    compatible: bool
    message: str
    severity: str  # 'info', 'warning', 'error'
    workaround: Optional[str] = None


class DependencyChecker:
    """
    Check compatibility of dependencies with PyPy.

    Some packages have C extensions that may not work with PyPy.
    This checker identifies potential issues.
    """

    # Known compatibility status of common dependencies
    KNOWN_DEPS = {
        # Fully compatible
        'flask': ('compatible', 'Flask works well with PyPy'),
        'jinja2': ('compatible', 'Jinja2 works well with PyPy'),
        'click': ('compatible', 'Click works well with PyPy'),
        'requests': ('compatible', 'Requests works well with PyPy'),
        'pyyaml': ('compatible', 'PyYAML works with PyPy (pure Python mode)'),
        'json': ('builtin', 'Standard library, fully compatible'),
        'sqlite3': ('builtin', 'Standard library, fully compatible'),
        'asyncio': ('builtin', 'Standard library, fully compatible'),
        'pathlib': ('builtin', 'Standard library, fully compatible'),
        're': ('builtin', 'Standard library, fully compatible'),

        # Compatible with caveats
        'lxml': ('caveat', 'lxml works but may need cffi version: pip install lxml-cffi'),
        'numpy': ('caveat', 'NumPy works but performance may differ'),
        'psutil': ('caveat', 'psutil requires cffi build'),
        'watchdog': ('caveat', 'watchdog works but may need extra setup'),

        # Potentially incompatible
        'uvloop': ('incompatible', 'uvloop uses Cython, not compatible with PyPy'),
        'cython': ('incompatible', 'Cython extensions not compatible with PyPy'),
    }

    @classmethod
    def check_dependency(cls, name: str) -> CompatibilityResult:
        """Check a single dependency for PyPy compatibility"""
        name_lower = name.lower()

        if name_lower in cls.KNOWN_DEPS:
            status, message = cls.KNOWN_DEPS[name_lower]
            compatible = status in ('compatible', 'builtin', 'caveat')
            severity = 'info' if status in ('compatible', 'builtin') else \
                      'warning' if status == 'caveat' else 'error'
            return CompatibilityResult(
                name=name,
                compatible=compatible,
                message=message,
                severity=severity,
            )

        # Unknown - assume compatible but warn
        return CompatibilityResult(
            name=name,
            compatible=True,
            message=f'Unknown compatibility status for {name}',
            severity='info',
        )

    @classmethod
    def check_installed_packages(cls) -> List[CompatibilityResult]:
        """Check all installed packages for PyPy compatibility"""
        results = []

        try:
            import pkg_resources
            for pkg in pkg_resources.working_set:
                result = cls.check_dependency(pkg.key)
                if result.severity in ('warning', 'error'):
                    results.append(result)
        except ImportError:
            pass

        return results

    @classmethod
    def check_quantum_dependencies(cls) -> List[CompatibilityResult]:
        """Check Quantum Framework's core dependencies"""
        core_deps = [
            'flask',
            'jinja2',
            'click',
            'pyyaml',
            'requests',
            'watchdog',
        ]

        return [cls.check_dependency(dep) for dep in core_deps]


class PyPyOptimizer:
    """
    Provides PyPy-specific optimizations and recommendations.
    """

    @staticmethod
    def get_recommendations() -> List[str]:
        """Get performance recommendations for PyPy users"""
        if not is_pypy():
            return ['Not running on PyPy - no PyPy-specific recommendations']

        return [
            'PyPy JIT is warming up - first requests may be slower',
            'Avoid using eval() in hot paths - use pre-compiled expressions',
            'Large dictionaries perform well on PyPy',
            'Use list comprehensions instead of map/filter for best JIT optimization',
            'Avoid metaclasses in performance-critical code',
            'PyPy startup is slower than CPython - use for long-running processes',
            'Consider using PyPy 7.3+ for best compatibility',
        ]

    @staticmethod
    def optimize_for_jit():
        """
        Apply PyPy-specific optimizations to help the JIT compiler.
        Should be called during application startup.
        """
        if not is_pypy():
            return

        # Hint to PyPy JIT about frequently used functions
        # This is mostly documentation - PyPy will optimize automatically
        pass

    @staticmethod
    def warmup_jit(iterations: int = 1000):
        """
        Warm up PyPy JIT by running common operations.
        Call this during application startup for faster first requests.

        Args:
            iterations: Number of warmup iterations
        """
        if not is_pypy():
            return

        # Warm up common operations
        for _ in range(iterations):
            # Dictionary operations
            d = {'key': 'value', 'num': 42}
            _ = d.get('key')
            d['new'] = 'item'

            # List operations
            lst = [1, 2, 3, 4, 5]
            _ = [x * 2 for x in lst]

            # String operations
            s = "hello world"
            _ = s.upper()
            _ = s.split()

            # Arithmetic
            x = 42
            y = x * 2 + 10 - 5


class QuantumPyPyAdapter:
    """
    Adapter that provides PyPy-compatible alternatives for
    any CPython-specific code in Quantum Framework.
    """

    @staticmethod
    def get_memory_usage() -> float:
        """
        Get current memory usage in MB.
        Uses different methods for PyPy vs CPython.
        """
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # Fallback for when psutil is not available
            import resource
            try:
                return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            except:
                return 0.0

    @staticmethod
    def gc_collect():
        """
        Force garbage collection.
        PyPy has different GC behavior than CPython.
        """
        import gc
        gc.collect()

        if is_pypy():
            # PyPy may need multiple collections
            gc.collect()
            gc.collect()

    @staticmethod
    def compile_expression(expr: str, mode: str = 'eval'):
        """
        Compile a Python expression.
        Both CPython and PyPy support this identically.
        """
        return compile(expr, '<quantum-expr>', mode)


def print_compatibility_report():
    """Print a detailed compatibility report for the current environment"""
    info = get_implementation_info()

    print("\n" + "=" * 60)
    print("  QUANTUM FRAMEWORK - PYTHON COMPATIBILITY REPORT")
    print("=" * 60)

    print(f"\n  Implementation: {info['implementation']}")
    print(f"  Version: {info['version']}")
    print(f"  Platform: {info['platform']}")
    print(f"  64-bit: {info['is_64bit']}")

    if is_pypy():
        print("\n  Status: Running on PyPy (JIT enabled)")
        print("\n  Recommendations:")
        for rec in PyPyOptimizer.get_recommendations():
            print(f"    - {rec}")
    else:
        print("\n  Status: Running on CPython")
        print("\n  To use PyPy for better performance:")
        print("    1. Install PyPy 3.9+ from https://www.pypy.org/")
        print("    2. Create virtual environment: pypy3 -m venv venv-pypy")
        print("    3. Install dependencies: pip install -r requirements.txt")
        print("    4. Run Quantum: pypy3 src/cli/runner.py start")

    print("\n  Dependency Compatibility:")
    results = DependencyChecker.check_quantum_dependencies()
    for result in results:
        status = "OK" if result.compatible else "ISSUE"
        print(f"    [{status}] {result.name}: {result.message}")

    print("\n" + "=" * 60)


# Export commonly used functions
__all__ = [
    'is_pypy',
    'is_cpython',
    'get_python_version',
    'get_implementation_info',
    'DependencyChecker',
    'PyPyOptimizer',
    'QuantumPyPyAdapter',
    'print_compatibility_report',
]
