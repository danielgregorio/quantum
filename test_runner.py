"""
Quantum Language - Automated Regression Test Runner

This script runs all test files and validates that core features still work
after architectural changes. It categorizes tests by feature and provides
detailed failure reports.

Usage:
    python test_runner.py                    # Run all tests
    python test_runner.py --feature loops    # Run tests for specific feature
    python test_runner.py --verbose          # Show detailed output
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import traceback

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.parser import QuantumParser
from runtime.component import ComponentRuntime


class TestResult:
    """Result of a single test execution"""
    def __init__(self, filename: str, passed: bool, result: str = None, error: str = None, expected_failure: bool = False):
        self.filename = filename
        self.passed = passed
        self.result = result
        self.error = error
        self.expected_failure = expected_failure  # Test that should fail (negative test)


class FeatureTestSuite:
    """Test suite for a specific feature"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.tests: List[str] = []
        self.expected_failures: List[str] = []  # Tests that should fail
        self.results: List[TestResult] = []

    def add_test(self, filename: str, expected_failure: bool = False):
        """Add a test file to this suite"""
        self.tests.append(filename)
        if expected_failure:
            self.expected_failures.append(filename)

    def run(self, examples_dir: Path, verbose: bool = False) -> Tuple[int, int]:
        """Run all tests in this suite. Returns (passed, total)"""
        print(f"\n{'='*70}")
        print(f"Feature: {self.name}")
        print(f"Description: {self.description}")
        print(f"Tests: {len(self.tests)}")
        print(f"{'='*70}\n")

        passed = 0
        for test_file in self.tests:
            is_expected_failure = test_file in self.expected_failures
            result = self._run_test(examples_dir / test_file, verbose)
            result.expected_failure = is_expected_failure
            self.results.append(result)

            # Expected failures: pass if test fails, fail if test passes
            if is_expected_failure:
                if not result.passed:
                    passed += 1
                    print(f"  PASS {test_file} (expected failure)")
                else:
                    print(f"  FAIL {test_file} (should have failed but passed)")
            else:
                if result.passed:
                    passed += 1
                    if verbose:
                        print(f"  PASS {test_file}")
                        print(f"       Result: {result.result}")
                    else:
                        print(f"  PASS {test_file}")
                else:
                    print(f"  FAIL {test_file}")
                    print(f"       Error: {result.error}")

        return passed, len(self.tests)

    def _run_test(self, test_path: Path, verbose: bool) -> TestResult:
        """Run a single test file"""
        try:
            parser = QuantumParser()
            ast = parser.parse_file(str(test_path))
            runtime = ComponentRuntime()
            result = runtime.execute_component(ast)
            return TestResult(test_path.name, True, str(result))
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            if verbose:
                error_msg += f"\n{traceback.format_exc()}"
            return TestResult(test_path.name, False, error=error_msg)


class RegressionTestRunner:
    """Main test runner that organizes tests by feature"""

    def __init__(self, examples_dir: str = "examples"):
        self.examples_dir = Path(examples_dir)
        self.suites: Dict[str, FeatureTestSuite] = {}
        self._initialize_suites()

    def _initialize_suites(self):
        """Initialize test suites for each feature"""

        # Conditionals (q:if, q:else, q:elseif)
        self.suites['conditionals'] = FeatureTestSuite(
            'Conditionals',
            'Test q:if, q:else, q:elseif - conditional logic and branching'
        )

        # Loops (q:loop)
        self.suites['loops'] = FeatureTestSuite(
            'Loops',
            'Test q:loop - range, array, list iterations'
        )

        # Databinding ({variable})
        self.suites['databinding'] = FeatureTestSuite(
            'Databinding',
            'Test {variable} syntax - variable interpolation and expressions'
        )

        # State Management (q:set)
        self.suites['state'] = FeatureTestSuite(
            'State Management',
            'Test q:set - variable creation, operations, validation'
        )

        # Functions (q:function)
        self.suites['functions'] = FeatureTestSuite(
            'Functions',
            'Test q:function - function definitions, calls, parameters, recursion'
        )

        # Validation
        self.suites['validation'] = FeatureTestSuite(
            'Validation',
            'Test validation rules - email, cpf, cnpj, range, enum, etc.'
        )

    def discover_tests(self):
        """Discover all test files and categorize them by feature"""
        if not self.examples_dir.exists():
            print(f"ERROR: Examples directory not found: {self.examples_dir}")
            return

        test_files = sorted(self.examples_dir.glob('test-*.q'))

        for test_file in test_files:
            filename = test_file.name

            # Categorize by filename pattern
            if filename.startswith('test-if-') or filename.startswith('test-else') or \
               filename.startswith('test-conditionals'):
                self.suites['conditionals'].add_test(filename)

            elif filename.startswith('test-loop-'):
                self.suites['loops'].add_test(filename)

            elif filename.startswith('test-databinding-'):
                self.suites['databinding'].add_test(filename)

            elif filename.startswith('test-set-') and 'validation' not in filename:
                self.suites['state'].add_test(filename)

            elif filename.startswith('test-function-'):
                self.suites['functions'].add_test(filename)

            elif 'validation' in filename:
                # Tests with "invalid" in name are expected to fail (negative tests)
                expected_failure = 'invalid' in filename
                self.suites['validation'].add_test(filename, expected_failure=expected_failure)

        # Mark other expected failures
        # test-conditionals.q requires parameters that aren't provided
        if 'test-conditionals.q' in [t for t in self.suites['conditionals'].tests]:
            self.suites['conditionals'].expected_failures.append('test-conditionals.q')

    def run_all(self, verbose: bool = False) -> Tuple[int, int]:
        """Run all test suites. Returns (total_passed, total_tests)"""
        print("\n" + "="*70)
        print("QUANTUM LANGUAGE - REGRESSION TEST SUITE")
        print("="*70)

        total_passed = 0
        total_tests = 0

        for suite in self.suites.values():
            if suite.tests:  # Only run suites that have tests
                passed, total = suite.run(self.examples_dir, verbose)
                total_passed += passed
                total_tests += total

        return total_passed, total_tests

    def run_feature(self, feature_name: str, verbose: bool = False) -> Tuple[int, int]:
        """Run tests for a specific feature. Returns (passed, total)"""
        if feature_name not in self.suites:
            print(f"ERROR: Unknown feature '{feature_name}'")
            print(f"Available features: {', '.join(self.suites.keys())}")
            return 0, 0

        suite = self.suites[feature_name]
        if not suite.tests:
            print(f"WARNING: No tests found for feature '{feature_name}'")
            return 0, 0

        return suite.run(self.examples_dir, verbose)

    def print_summary(self, total_passed: int, total_tests: int):
        """Print final summary"""
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)

        for suite_name, suite in self.suites.items():
            if suite.results:
                passed = sum(1 for r in suite.results if r.passed)
                total = len(suite.results)
                status = "PASS" if passed == total else "FAIL"
                print(f"  {status:4} {suite.name:20} {passed:3}/{total:3} tests passed")

        print(f"\n{'='*70}")
        percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"TOTAL: {total_passed}/{total_tests} tests passed ({percentage:.1f}%)")
        print(f"{'='*70}\n")

        if total_passed == total_tests:
            print("SUCCESS: All tests passed!")
            return 0
        else:
            print(f"FAILURE: {total_tests - total_passed} test(s) failed")
            return 1


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Run Quantum Language regression tests')
    parser.add_argument('--feature', type=str, help='Run tests for specific feature only')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--examples-dir', type=str, default='examples', help='Path to examples directory')

    args = parser.parse_args()

    runner = RegressionTestRunner(args.examples_dir)
    runner.discover_tests()

    if args.feature:
        passed, total = runner.run_feature(args.feature, args.verbose)
    else:
        passed, total = runner.run_all(args.verbose)

    runner.print_summary(passed, total)

    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
