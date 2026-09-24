"""
The CLI is the front door and had almost no tests.

Measured: `quantum/cli/runner.py` 9.4% coverage, `deploy.py` 0%, `mq.py`
9.5%, `jobs.py` 0%, `pkg.py` 0%. Every user touches the CLI before anything
else, and only by running the installer was it found, by chance, that
`quantum apps` pointed to a private host.

What these tests lock is the CONTRACT, not the format of the output:

1. Failing returns a code != 0. A command that fails and exits with 0 breaks
   any script and any CI that depends on it.
2. No raw traceback in the user's face. A traceback is for whoever wrote the
   framework; whoever uses it deserves a sentence.
3. The message says what to do, not only what happened.

They are subprocesses on purpose: `main()` called in-process can go through
paths the real entry point does not, and the exit code only really exists in
a process.
"""

import pathlib
import subprocess
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
TRACEBACK = "Traceback (most recent call last)"


def cli(*args, timeout=180, cwd=REPO):
    return subprocess.run(
        [sys.executable, "-m", "quantum.cli.runner", *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(cwd),
    )


def output(result):
    return (result.stdout or "") + (result.stderr or "")


@pytest.fixture
def invalid_file():
    path = pathlib.Path(tempfile.mkdtemp()) / "broken.q"
    path.write_text('<q:component name="X"><q:if></q:component>',
                    encoding="utf-8")
    return path


@pytest.fixture
def valid_file():
    path = pathlib.Path(tempfile.mkdtemp()) / "ok.q"
    path.write_text(
        '<q:component name="Ok"><q:set name="n" value="2" type="number" />'
        '<q:return value="{n}" /></q:component>', encoding="utf-8")
    return path


class TestFailingReturnsAnErrorCode:
    """Exiting with 0 after failing breaks every script that trusts the CLI."""

    def test_an_unknown_subcommand(self):
        assert cli("make-coffee").returncode != 0

    def test_a_missing_file(self):
        result = cli("run", "/does/not/exist/anywhere.q")
        assert result.returncode != 0

    def test_a_file_that_does_not_parse(self, invalid_file):
        result = cli("run", str(invalid_file))
        assert result.returncode != 0

    def test_run_without_an_argument(self):
        assert cli("run").returncode != 0

    def test_a_valid_file_exits_with_zero(self, valid_file):
        result = cli("run", str(valid_file))
        assert result.returncode == 0, output(result)[-400:]


class TestNoTracebackInTheUsersFace:
    """A traceback is for whoever wrote the framework."""

    def test_a_missing_file(self):
        assert TRACEBACK not in output(cli("run", "/does/not/exist.q"))

    def test_a_file_that_does_not_parse(self, invalid_file):
        assert TRACEBACK not in output(cli("run", str(invalid_file)))

    def test_an_unknown_subcommand(self):
        assert TRACEBACK not in output(cli("make-coffee"))

    # In an empty folder: `stop` acts on the .quantum.pid of its cwd, and in
    # the repository that file may be anyone's (see
    # test_reloader_child_skips_the_port_check).
    def test_status_without_a_server(self, tmp_path):
        assert TRACEBACK not in output(cli("status", cwd=tmp_path))

    def test_stop_without_a_server(self, tmp_path):
        assert TRACEBACK not in output(cli("stop", cwd=tmp_path))


class TestMessagesSayWhatToDo:
    def test_a_missing_file_says_the_path(self):
        text = output(cli("run", "/does/not/exist/file.q"))
        assert "file.q" in text

    def test_a_parse_error_points_to_the_line(self, invalid_file):
        text = output(cli("run", str(invalid_file)))
        assert "line" in text.lower()

    def test_help_lists_the_subcommands(self):
        text = output(cli("--help"))
        for command in ("run", "start", "migrate"):
            assert command in text


class TestNoArgumentPrintsHelp:
    """Not a failure: asking for help implicitly is legitimate use."""

    def test_exits_with_zero(self):
        assert cli().returncode == 0

    def test_shows_the_subcommands(self):
        text = output(cli())
        assert "run" in text and "start" in text


class TestSubcommandsAnswer:
    """A subcommand that does not even run is worse than one that fails."""

    # The runner's real list. An earlier version of this test included
    # "status", which is actually a subcommand of `migrate` — the test failed
    # by my mistake, not by a defect of the CLI.
    TOP = ["run", "start", "stop", "pkg", "jobs", "mq",
           "migrate", "admin", "console", "desktop", "check", "test"]

    @pytest.mark.parametrize("command", TOP)
    def test_the_subcommand_help_works(self, command):
        result = cli(command, "--help")
        assert result.returncode == 0, output(result)[-300:]
        assert TRACEBACK not in output(result)

    def test_this_list_matches_the_runner_s(self):
        # If someone adds a subcommand, this test says it is not covered —
        # instead of coverage dropping silently.
        import re
        source = (REPO / "quantum" / "cli" / "runner.py").read_text(
            encoding="utf-8")
        block = source.split("subparsers = ")[1]
        declared = set(re.findall(r"subparsers\.add_parser\(\s*'([a-z-]+)'",
                                  block))
        missing = declared - set(self.TOP)
        assert missing == set(), f"subcommands without a test: {missing}"

    def test_migrate_status_is_a_subcommand_of_migrate(self):
        result = cli("migrate", "status", "--help")
        assert result.returncode == 0
        assert TRACEBACK not in output(result)
