"""
Test Execution Service for Quantum Admin
Manages test execution using test_runner.py
"""
import asyncio
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class TestExecutionService:
    """Service for running Quantum tests and tracking results"""

    # Store active test processes for cancellation
    active_processes: Dict[int, asyncio.subprocess.Process] = {}

    @staticmethod
    async def run_tests(
        db,
        project_id: int,
        suite_filter: Optional[str] = None,
        verbose: bool = False,
        stop_on_fail: bool = False,
        triggered_by: str = "manual"
    ) -> int:
        """
        Execute test_runner.py and track results

        Args:
            db: Database session
            project_id: Project ID
            suite_filter: Optional suite name to run (e.g., 'loops', 'query')
            verbose: Enable verbose output
            stop_on_fail: Stop on first failure
            triggered_by: Who triggered the test

        Returns:
            int: Test run ID

        Raises:
            Exception: If test execution fails
        """
        # Import models here to avoid circular imports
        try:
            from . import models
        except ImportError:
            import models

        # Create test run record
        test_run = models.TestRun(
            project_id=project_id,
            status='running',
            started_at=datetime.utcnow(),
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            triggered_by=triggered_by,
            suite_filter=suite_filter
        )
        db.add(test_run)
        db.commit()
        db.refresh(test_run)

        logger.info(f"🧪 Starting test run {test_run.id} for project {project_id}")

        # Build command
        project_root = Path(__file__).parent.parent.parent  # Go up to quantum/ directory
        test_runner_path = project_root / "test_runner.py"

        cmd = ['python', str(test_runner_path)]
        if suite_filter:
            cmd.extend(['--feature', suite_filter])
        if verbose:
            cmd.append('--verbose')

        logger.info(f"📋 Command: {' '.join(cmd)}")

        try:
            # Execute tests asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project_root)
            )

            # Store process for potential cancellation
            TestExecutionService.active_processes[test_run.id] = process

            # Wait for completion
            stdout, stderr = await process.communicate()

            # Remove from active processes
            TestExecutionService.active_processes.pop(test_run.id, None)

            # Parse test results
            output = stdout.decode('utf-8')
            results = TestExecutionService._parse_test_output(output)

            # Update test run
            test_run.status = 'completed' if process.returncode == 0 else 'failed'
            test_run.completed_at = datetime.utcnow()
            test_run.total_tests = results['total']
            test_run.passed_tests = results['passed']
            test_run.failed_tests = results['failed']
            test_run.duration_seconds = int((test_run.completed_at - test_run.started_at).total_seconds())

            # Save individual test results
            for test in results['tests']:
                test_result = models.TestResult(
                    test_run_id=test_run.id,
                    suite_name=test['suite'],
                    test_file=test['file'],
                    status=test['status'],
                    duration_seconds=test.get('duration', 0),
                    error_message=test.get('error'),
                    output=test.get('output')
                )
                db.add(test_result)

            db.commit()

            logger.info(f"✅ Test run {test_run.id} completed: {test_run.passed_tests}/{test_run.total_tests} passed")
            return test_run.id

        except asyncio.CancelledError:
            # Handle cancellation
            test_run.status = 'cancelled'
            test_run.completed_at = datetime.utcnow()
            test_run.duration_seconds = int((test_run.completed_at - test_run.started_at).total_seconds())
            db.commit()

            logger.info(f"⚠️ Test run {test_run.id} cancelled")
            raise

        except Exception as e:
            test_run.status = 'error'
            test_run.error_message = str(e)
            test_run.completed_at = datetime.utcnow()
            test_run.duration_seconds = int((test_run.completed_at - test_run.started_at).total_seconds())
            db.commit()

            logger.error(f"❌ Test run {test_run.id} failed: {e}")
            raise

    @staticmethod
    def _parse_test_output(output: str) -> Dict:
        """
        Parse test_runner.py output and extract results

        Args:
            output: Raw stdout from test_runner.py

        Returns:
            dict: Parsed results with structure:
                {
                    'total': int,
                    'passed': int,
                    'failed': int,
                    'tests': [
                        {
                            'suite': str,
                            'file': str,
                            'status': 'passed'|'failed',
                            'error': str (optional),
                            'output': str (optional)
                        }
                    ]
                }
        """
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'tests': []
        }

        # Parse summary line: "TOTAL: 97/97 tests passed (100.0%)"
        summary_match = re.search(r'TOTAL: (\d+)/(\d+) tests passed', output)
        if summary_match:
            results['passed'] = int(summary_match.group(1))
            results['total'] = int(summary_match.group(2))
            results['failed'] = results['total'] - results['passed']

        # Parse individual test results
        current_suite = None

        # Look for feature headers: "Feature: Loops"
        for line in output.split('\n'):
            feature_match = re.match(r'Feature: (.+)', line)
            if feature_match:
                current_suite = feature_match.group(1).strip()
                continue

            # Parse test results: "  PASS test-loop-basic.q" or "  FAIL test-loop-error.q"
            test_match = re.match(r'\s+(PASS|FAIL)\s+(test-.+\.q)(?:\s+\((.+)\))?', line)
            if test_match and current_suite:
                status = test_match.group(1).lower()
                filename = test_match.group(2)
                note = test_match.group(3)  # e.g., "expected failure"

                test_info = {
                    'suite': current_suite,
                    'file': filename,
                    'status': status,
                    'error': None,
                    'output': None
                }

                # Handle expected failures
                if note and 'expected failure' in note:
                    # Expected failure that failed = PASS (test is correct)
                    if status == 'fail':
                        test_info['status'] = 'passed'
                    # Expected failure that passed = FAIL (test is wrong)
                    elif status == 'pass':
                        test_info['status'] = 'failed'
                        test_info['error'] = 'Should have failed but passed'

                results['tests'].append(test_info)

        # Parse error messages (lines starting with "       Error:")
        for i, line in enumerate(output.split('\n')):
            if line.strip().startswith('Error:'):
                error_msg = line.strip()[7:]  # Remove "Error: " prefix
                # Find the previous test result and add error
                if results['tests']:
                    results['tests'][-1]['error'] = error_msg

        return results

    @staticmethod
    async def cancel_test_run(db, test_run_id: int) -> bool:
        """
        Cancel a running test execution

        Args:
            db: Database session
            test_run_id: Test run ID to cancel

        Returns:
            bool: True if cancelled successfully, False otherwise
        """
        try:
            from . import models
        except ImportError:
            import models

        # Check if test run exists and is running
        test_run = db.query(models.TestRun).filter(
            models.TestRun.id == test_run_id
        ).first()

        if not test_run:
            logger.warning(f"Test run {test_run_id} not found")
            return False

        if test_run.status != 'running':
            logger.warning(f"Test run {test_run_id} is not running (status: {test_run.status})")
            return False

        # Get process if active
        process = TestExecutionService.active_processes.get(test_run_id)
        if process:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()

            TestExecutionService.active_processes.pop(test_run_id, None)

        # Update database
        test_run.status = 'cancelled'
        test_run.completed_at = datetime.utcnow()
        test_run.duration_seconds = int((test_run.completed_at - test_run.started_at).total_seconds())
        db.commit()

        logger.info(f"✅ Test run {test_run_id} cancelled")
        return True

    @staticmethod
    def get_test_run_status(db, test_run_id: int) -> Optional[Dict]:
        """
        Get current status of a test run

        Args:
            db: Database session
            test_run_id: Test run ID

        Returns:
            dict: Status information or None if not found
        """
        try:
            from . import models
        except ImportError:
            import models

        test_run = db.query(models.TestRun).filter(
            models.TestRun.id == test_run_id
        ).first()

        if not test_run:
            return None

        # Calculate progress
        progress_percentage = 0.0
        if test_run.total_tests > 0:
            completed = test_run.passed_tests + test_run.failed_tests
            progress_percentage = (completed / test_run.total_tests) * 100

        # Get current suite (from latest test result)
        current_suite = None
        if test_run.test_results:
            latest_result = sorted(test_run.test_results, key=lambda r: r.id)[-1]
            current_suite = latest_result.suite_name

        # Estimate time remaining (rough estimate)
        estimated_time_remaining = None
        if test_run.status == 'running' and progress_percentage > 0:
            elapsed = (datetime.utcnow() - test_run.started_at).total_seconds()
            total_estimated = elapsed / (progress_percentage / 100)
            estimated_time_remaining = int(total_estimated - elapsed)

        return {
            'id': test_run.id,
            'status': test_run.status,
            'total_tests': test_run.total_tests,
            'passed_tests': test_run.passed_tests,
            'failed_tests': test_run.failed_tests,
            'current_suite': current_suite,
            'progress_percentage': progress_percentage,
            'estimated_time_remaining': estimated_time_remaining
        }

    @staticmethod
    async def stream_test_output(test_run_id: int) -> AsyncGenerator[str, None]:
        """
        Stream test output in real-time (for future SSE implementation)

        Args:
            test_run_id: Test run ID

        Yields:
            str: Log lines as they are generated
        """
        # Get process if active
        process = TestExecutionService.active_processes.get(test_run_id)
        if not process or not process.stdout:
            return

        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode('utf-8')
        except Exception as e:
            logger.error(f"Error streaming output for test run {test_run_id}: {e}")
