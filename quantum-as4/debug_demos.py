#!/usr/bin/env python3
"""
Automated Demo Test Runner for Quantum MXML Compiler

This script:
1. Tests all compiled demos via HTTP
2. Checks health status via window.__quantumHealth
3. Validates no JavaScript errors
4. Auto-recompiles on failure
5. Generates test report

Usage:
    python test_demos.py [--recompile] [--verbose]
"""

import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("[WARNING] Selenium not available. Install with: pip install selenium")


class DemoTester:
    """Test runner for Quantum MXML demos"""

    def __init__(self, base_url: str = "http://localhost:8547", verbose: bool = False):
        self.base_url = base_url
        self.verbose = verbose
        self.results = []
        self.driver = None

        # List of demos to test (directory name, display name)
        self.demos = [
            ("hello", "Hello World"),
            ("databinding", "Data Binding"),
            ("stopwatch", "Stopwatch"),
            ("components-demo", "Components Demo"),
            ("nested-containers", "Nested Containers"),
            ("fase1-mvp-demo", "FASE 1 MVP Demo"),
            ("advanced-components", "Advanced Components"),
            ("enhanced-components-demo", "Enhanced Components"),
            ("effects-demo", "Effects Demo"),
            ("formatters-demo", "Formatters Demo"),
            ("ecommerce-admin", "E-Commerce Admin Dashboard"),
            ("quantum-integration-demo", "Quantum Integration Demo"),
        ]

    def setup_driver(self):
        """Initialize Chrome driver in headless mode"""
        if not SELENIUM_AVAILABLE:
            print("[ERROR] Selenium not available. Cannot run tests.")
            return False

        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # Suppress console logs unless verbose
            if not self.verbose:
                chrome_options.add_argument("--log-level=3")
                chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(10)
            return True

        except Exception as e:
            print(f"[ERROR] Failed to initialize Chrome driver: {e}")
            print("Make sure Chrome and ChromeDriver are installed")
            return False

    def test_demo(self, demo_path: str, demo_name: str) -> Dict:
        """
        Test a single demo

        Returns:
            Dict with test results:
            {
                'name': str,
                'path': str,
                'url': str,
                'status': 'pass' | 'fail' | 'error',
                'health': dict or None,
                'errors': list,
                'warnings': list,
                'load_time': float,
                'message': str
            }
        """
        url = f"{self.base_url}/{demo_path}/"
        result = {
            'name': demo_name,
            'path': demo_path,
            'url': url,
            'status': 'error',
            'health': None,
            'errors': [],
            'warnings': [],
            'load_time': 0,
            'message': ''
        }

        try:
            start_time = time.time()

            # Load the page
            if self.verbose:
                print(f"  Loading {url}...")
            self.driver.get(url)

            # Wait for health check to initialize (max 3 seconds)
            try:
                WebDriverWait(self.driver, 3).until(
                    lambda d: d.execute_script("return window.__quantumHealth !== undefined")
                )
            except:
                result['status'] = 'fail'
                result['message'] = 'Health check system not initialized'
                return result

            # Wait for app to be ready (max 5 seconds)
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: d.execute_script("return window.__quantumHealth && window.__quantumHealth.status !== 'initializing'")
                )
            except:
                result['status'] = 'fail'
                result['message'] = 'Application stuck in initializing state'
                health = self.driver.execute_script("return window.__quantumHealth")
                result['health'] = health
                return result

            # Get health status
            health = self.driver.execute_script("return window.__quantumHealth")
            result['health'] = health
            result['errors'] = health.get('errors', [])
            result['warnings'] = health.get('warnings', [])

            load_time = time.time() - start_time
            result['load_time'] = round(load_time, 2)

            # Check status
            if health['status'] == 'ready':
                result['status'] = 'pass'
                result['message'] = f'Application loaded successfully in {result["load_time"]}s'
            elif health['status'] == 'error':
                result['status'] = 'fail'
                error_messages = [e['message'] for e in result['errors']]
                result['message'] = f'Application has errors: {", ".join(error_messages)}'
            else:
                result['status'] = 'fail'
                result['message'] = f'Unknown status: {health["status"]}'

            # Get browser console logs
            try:
                logs = self.driver.get_log('browser')
                for log in logs:
                    if log['level'] == 'SEVERE':
                        result['errors'].append({
                            'message': log['message'],
                            'source': log['source']
                        })
                    elif log['level'] == 'WARNING':
                        result['warnings'].append({
                            'message': log['message'],
                            'source': log['source']
                        })
            except:
                pass  # Browser logs not available in all drivers

        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'Test error: {str(e)}'

        return result

    def run_all_tests(self) -> List[Dict]:
        """Run tests for all demos"""
        print("\n" + "=" * 70)
        print("QUANTUM MXML DEMO TEST SUITE")
        print("=" * 70)

        if not self.setup_driver():
            return []

        print(f"\nTesting {len(self.demos)} demos at {self.base_url}")
        print("-" * 70)

        for demo_path, demo_name in self.demos:
            print(f"\n[{len(self.results) + 1}/{len(self.demos)}] Testing: {demo_name}")

            result = self.test_demo(demo_path, demo_name)
            self.results.append(result)

            # Print result
            if result['status'] == 'pass':
                print(f"  [PASS] {result['message']}")
            elif result['status'] == 'fail':
                print(f"  [FAIL] {result['message']}")
                if result['errors']:
                    print(f"  Errors: {len(result['errors'])}")
                    for err in result['errors'][:3]:  # Show first 3 errors
                        print(f"    - {err['message']}")
            else:
                print(f"  [ERROR] {result['message']}")

        self.driver.quit()
        return self.results

    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r['status'] == 'pass')
        failed = sum(1 for r in self.results if r['status'] == 'fail')
        errors = sum(1 for r in self.results if r['status'] == 'error')
        total = len(self.results)

        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"Errors: {errors} ({errors/total*100:.1f}%)")

        if failed > 0 or errors > 0:
            print("\nFailed/Error demos:")
            for result in self.results:
                if result['status'] in ['fail', 'error']:
                    print(f"  - {result['name']}: {result['message']}")

        print("=" * 70)

    def save_report(self, filename: str = "test_report.json"):
        """Save test results to JSON file"""
        report = {
            'timestamp': time.time(),
            'base_url': self.base_url,
            'total': len(self.results),
            'passed': sum(1 for r in self.results if r['status'] == 'pass'),
            'failed': sum(1 for r in self.results if r['status'] == 'fail'),
            'errors': sum(1 for r in self.results if r['status'] == 'error'),
            'results': self.results
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nTest report saved to: {filename}")

    def recompile_failed_demos(self) -> List[str]:
        """Recompile demos that failed"""
        failed_demos = [r for r in self.results if r['status'] in ['fail', 'error']]

        if not failed_demos:
            print("\nNo failed demos to recompile.")
            return []

        print(f"\n" + "=" * 70)
        print(f"RECOMPILING {len(failed_demos)} FAILED DEMOS")
        print("=" * 70)

        recompiled = []

        for result in failed_demos:
            demo_path = result['path']
            demo_name = result['name']

            # Find MXML source file
            mxml_file = Path(f"examples/{demo_path}.mxml")
            if not mxml_file.exists():
                print(f"\n[SKIP] {demo_name}: MXML source not found")
                continue

            print(f"\n[RECOMPILE] {demo_name}")
            print(f"  Source: {mxml_file}")

            try:
                # Run compiler
                cmd = ["python", "quantum-mxml", "build", str(mxml_file)]
                subprocess.run(cmd, check=True, capture_output=True, text=True)

                # Copy to docs folder
                subprocess.run([
                    "cp", "dist/app.js", f"docs/{demo_path}/app.js"
                ], check=True)

                print(f"  [SUCCESS] Recompiled successfully")
                recompiled.append(demo_name)

            except subprocess.CalledProcessError as e:
                print(f"  [ERROR] Recompile failed: {e}")

        return recompiled


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test Quantum MXML demos")
    parser.add_argument('--recompile', action='store_true', help='Recompile failed demos')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--url', default='http://localhost:8547', help='Base URL for demos')
    args = parser.parse_args()

    if not SELENIUM_AVAILABLE:
        print("[ERROR] Selenium is required to run tests.")
        print("Install with: pip install selenium")
        print("Also install ChromeDriver: https://chromedriver.chromium.org/")
        sys.exit(1)

    tester = DemoTester(base_url=args.url, verbose=args.verbose)

    # Run tests
    tester.run_all_tests()

    # Print summary
    tester.print_summary()

    # Save report
    tester.save_report()

    # Recompile if requested
    if args.recompile:
        recompiled = tester.recompile_failed_demos()
        if recompiled:
            print(f"\nRecompiled {len(recompiled)} demos. Run tests again to verify fixes.")

    # Exit with error code if any tests failed
    failed = sum(1 for r in tester.results if r['status'] != 'pass')
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
