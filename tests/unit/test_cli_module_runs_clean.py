"""`python -m quantum.cli.runner` — what the installation guide offers when the
`quantum` script is not on PATH — runs without a warning.

quantum/cli/__init__.py imported runner, so running it as a module printed a
RuntimeWarning ("found in sys.modules ... unpredictable behaviour") before
every command.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_the_module_form_prints_no_warning():
    result = subprocess.run([sys.executable, '-W', 'error::RuntimeWarning', '-m', 'quantum.cli.runner', '--version'],
                            capture_output=True, text=True, cwd=str(REPO), timeout=120)
    assert result.returncode == 0, result.stderr
    assert 'RuntimeWarning' not in result.stderr
