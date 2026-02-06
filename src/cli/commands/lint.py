"""
Quantum CLI - Lint Command

Lint and validate .q files.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

import click

from cli.utils import get_console, find_project_root, find_q_files


class Severity(Enum):
    """Lint issue severity levels."""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


@dataclass
class LintIssue:
    """A linting issue found in a file."""
    file: Path
    line: int
    column: int
    severity: Severity
    code: str
    message: str
    suggestion: Optional[str] = None


class QuantumLinter:
    """Linter for Quantum .q files."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.issues: List[LintIssue] = []

    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint a single .q file."""
        issues = []

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()

            # Run lint checks
            issues.extend(self._check_xml_structure(file_path, content, lines))
            issues.extend(self._check_quantum_conventions(file_path, content, lines))
            issues.extend(self._check_databinding(file_path, content, lines))
            issues.extend(self._check_component_structure(file_path, content, lines))
            issues.extend(self._check_accessibility(file_path, content, lines))

            # Try parsing with Quantum parser
            issues.extend(self._check_parse_errors(file_path, content))

        except Exception as e:
            issues.append(LintIssue(
                file=file_path,
                line=0,
                column=0,
                severity=Severity.ERROR,
                code='E001',
                message=f"Failed to read file: {e}"
            ))

        return issues

    def lint_directory(self, directory: Path, recursive: bool = True) -> List[LintIssue]:
        """Lint all .q files in a directory."""
        q_files = find_q_files(directory, recursive=recursive)
        all_issues = []

        for q_file in q_files:
            issues = self.lint_file(q_file)
            all_issues.extend(issues)

        return all_issues

    def _check_xml_structure(self, file_path: Path, content: str, lines: List[str]) -> List[LintIssue]:
        """Check XML structure and syntax."""
        issues = []
        import re

        # Check for unclosed tags
        tag_pattern = re.compile(r'<(\/?)(q:)?(\w+)([^>]*?)(/?)>')
        open_tags = []

        for i, line in enumerate(lines, 1):
            for match in tag_pattern.finditer(line):
                is_closing = match.group(1) == '/'
                is_self_closing = match.group(5) == '/'
                tag_name = match.group(3)

                if is_closing:
                    if open_tags and open_tags[-1] == tag_name:
                        open_tags.pop()
                    else:
                        issues.append(LintIssue(
                            file=file_path,
                            line=i,
                            column=match.start(),
                            severity=Severity.ERROR,
                            code='E010',
                            message=f"Unexpected closing tag </{tag_name}>"
                        ))
                elif not is_self_closing:
                    # Skip void elements
                    void_elements = ['br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'param', 'source', 'track', 'wbr']
                    if tag_name.lower() not in void_elements:
                        open_tags.append(tag_name)

        # Check for missing DOCTYPE/xml declaration (warning only)
        if lines and not lines[0].strip().startswith('<?xml') and not lines[0].strip().startswith('<!DOCTYPE') and not lines[0].strip().startswith('<!--'):
            # Not an error, just info
            pass

        return issues

    def _check_quantum_conventions(self, file_path: Path, content: str, lines: List[str]) -> List[LintIssue]:
        """Check Quantum-specific conventions."""
        issues = []
        import re

        # Check for component name matching filename
        component_pattern = re.compile(r'<q:component\s+name="([^"]+)"')
        for i, line in enumerate(lines, 1):
            match = component_pattern.search(line)
            if match:
                component_name = match.group(1)
                expected_name = file_path.stem

                # Component name should match file name (PascalCase)
                if component_name.lower() != expected_name.lower().replace('-', '').replace('_', ''):
                    issues.append(LintIssue(
                        file=file_path,
                        line=i,
                        column=match.start(),
                        severity=Severity.WARNING,
                        code='W001',
                        message=f"Component name '{component_name}' does not match filename '{file_path.name}'",
                        suggestion=f"Rename component to '{expected_name}' or rename file"
                    ))

        # Check for xmlns declaration
        if 'xmlns:q=' not in content and '<q:' in content:
            issues.append(LintIssue(
                file=file_path,
                line=1,
                column=0,
                severity=Severity.WARNING,
                code='W002',
                message="Missing xmlns:q namespace declaration",
                suggestion='Add xmlns:q="https://quantum.lang/ns" to root element'
            ))

        # Check for deprecated tags
        deprecated_tags = {
            'q:cfif': 'q:if',
            'q:cfset': 'q:set',
            'q:cfloop': 'q:loop',
            'q:cfquery': 'q:query',
        }

        for old_tag, new_tag in deprecated_tags.items():
            for i, line in enumerate(lines, 1):
                if f'<{old_tag}' in line.lower():
                    issues.append(LintIssue(
                        file=file_path,
                        line=i,
                        column=line.lower().find(f'<{old_tag}'),
                        severity=Severity.WARNING,
                        code='W003',
                        message=f"Deprecated tag '{old_tag}'",
                        suggestion=f"Use '{new_tag}' instead"
                    ))

        return issues

    def _check_databinding(self, file_path: Path, content: str, lines: List[str]) -> List[LintIssue]:
        """Check databinding syntax."""
        issues = []
        import re

        # Check for unclosed databinding braces
        for i, line in enumerate(lines, 1):
            # Count { and } not in strings
            open_count = line.count('{')
            close_count = line.count('}')

            # Simple check - might have false positives for multi-line expressions
            if open_count != close_count:
                # Check if it's a JavaScript object (common false positive)
                if not re.search(r'[=:]\s*\{', line):
                    issues.append(LintIssue(
                        file=file_path,
                        line=i,
                        column=0,
                        severity=Severity.WARNING,
                        code='W010',
                        message="Potentially unmatched databinding braces",
                        suggestion="Check for balanced { and } in expressions"
                    ))

        # Check for double-braces which might be a mistake
        double_brace_pattern = re.compile(r'\{\{([^}]+)\}\}')
        for i, line in enumerate(lines, 1):
            match = double_brace_pattern.search(line)
            if match:
                # Could be intentional (e.g., template syntax) - just info
                issues.append(LintIssue(
                    file=file_path,
                    line=i,
                    column=match.start(),
                    severity=Severity.INFO,
                    code='I010',
                    message="Double braces {{ }} detected - Quantum uses single braces { }",
                    suggestion="Use single braces for databinding: {expression}"
                ))

        return issues

    def _check_component_structure(self, file_path: Path, content: str, lines: List[str]) -> List[LintIssue]:
        """Check component structure best practices."""
        issues = []
        import re

        # Check for multiple root components
        component_count = content.count('<q:component')
        if component_count > 1:
            issues.append(LintIssue(
                file=file_path,
                line=1,
                column=0,
                severity=Severity.WARNING,
                code='W020',
                message=f"File contains {component_count} components - consider splitting",
                suggestion="One component per file is recommended"
            ))

        # Check for required params without defaults
        param_pattern = re.compile(r'<q:param\s+name="([^"]+)"[^>]*required="true"[^>]*/>')
        for i, line in enumerate(lines, 1):
            match = param_pattern.search(line)
            if match and 'default=' not in line:
                # This is fine, just informational
                pass

        # Check for unused params (simplified check)
        param_names = []
        param_lines = {}
        for i, line in enumerate(lines, 1):
            match = re.search(r'<q:param\s+name="([^"]+)"', line)
            if match:
                param_names.append(match.group(1))
                param_lines[match.group(1)] = i

        for param in param_names:
            # Check if param is used in databinding
            usage_pattern = re.compile(r'\{[^}]*\b' + re.escape(param) + r'\b[^}]*\}')
            if not usage_pattern.search(content):
                issues.append(LintIssue(
                    file=file_path,
                    line=param_lines[param],
                    column=0,
                    severity=Severity.INFO,
                    code='I020',
                    message=f"Parameter '{param}' may be unused",
                    suggestion="Remove unused parameters or verify usage"
                ))

        return issues

    def _check_accessibility(self, file_path: Path, content: str, lines: List[str]) -> List[LintIssue]:
        """Check accessibility best practices."""
        issues = []
        import re

        # Check for images without alt
        img_pattern = re.compile(r'<img\s+[^>]*>')
        for i, line in enumerate(lines, 1):
            for match in img_pattern.finditer(line):
                img_tag = match.group()
                if 'alt=' not in img_tag:
                    issues.append(LintIssue(
                        file=file_path,
                        line=i,
                        column=match.start(),
                        severity=Severity.WARNING,
                        code='A001',
                        message="Image missing alt attribute",
                        suggestion='Add alt="description" for accessibility'
                    ))

        # Check for buttons without type
        button_pattern = re.compile(r'<button\s+[^>]*>')
        for i, line in enumerate(lines, 1):
            for match in button_pattern.finditer(line):
                button_tag = match.group()
                if 'type=' not in button_tag:
                    issues.append(LintIssue(
                        file=file_path,
                        line=i,
                        column=match.start(),
                        severity=Severity.INFO,
                        code='A002',
                        message="Button missing type attribute",
                        suggestion='Add type="button" or type="submit"'
                    ))

        # Check for form inputs without labels
        input_pattern = re.compile(r'<input\s+[^>]*id="([^"]+)"[^>]*>')
        for i, line in enumerate(lines, 1):
            for match in input_pattern.finditer(line):
                input_id = match.group(1)
                label_pattern = re.compile(rf'<label\s+[^>]*for="{input_id}"')
                if not label_pattern.search(content):
                    issues.append(LintIssue(
                        file=file_path,
                        line=i,
                        column=match.start(),
                        severity=Severity.INFO,
                        code='A003',
                        message=f"Input '{input_id}' may be missing a label",
                        suggestion=f'Add <label for="{input_id}">Label</label>'
                    ))

        return issues

    def _check_parse_errors(self, file_path: Path, content: str) -> List[LintIssue]:
        """Check for parser errors."""
        issues = []

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from core.parser import QuantumParser, QuantumParseError

            parser = QuantumParser()
            parser.parse(content)

        except QuantumParseError as e:
            issues.append(LintIssue(
                file=file_path,
                line=getattr(e, 'line', 0) or 0,
                column=getattr(e, 'column', 0) or 0,
                severity=Severity.ERROR,
                code='E100',
                message=f"Parse error: {e}"
            ))
        except Exception as e:
            # Other parsing errors
            issues.append(LintIssue(
                file=file_path,
                line=0,
                column=0,
                severity=Severity.ERROR,
                code='E101',
                message=f"Failed to parse: {e}"
            ))

        return issues


@click.command('lint')
@click.argument('path', required=False, type=click.Path())
@click.option('--fix', is_flag=True, help='Attempt to fix issues automatically')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'github']), default='text',
              help='Output format')
@click.option('--severity', '-s', type=click.Choice(['error', 'warning', 'info']), default='warning',
              help='Minimum severity to report')
@click.option('--ignore', '-i', type=str, multiple=True, help='Issue codes to ignore')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode - only show errors')
def lint(
    path: Optional[str],
    fix: bool,
    format: str,
    severity: str,
    ignore: tuple,
    quiet: bool
):
    """Lint and validate .q files.

    Checks for syntax errors, best practices, and accessibility issues.

    Examples:

        quantum lint

        quantum lint ./components

        quantum lint --format json

        quantum lint --severity error

        quantum lint --ignore W001 --ignore W002
    """
    console = get_console(quiet=quiet)

    # Find project root
    project_root = find_project_root()
    if not project_root:
        project_root = Path.cwd()

    # Determine lint path
    if path:
        lint_path = Path(path)
        if not lint_path.is_absolute():
            lint_path = project_root / path
    else:
        lint_path = project_root

    if not lint_path.exists():
        console.error(f"Path not found: {lint_path}")
        raise click.Abort()

    console.header(
        "Quantum Linter",
        f"Checking: {lint_path}"
    )

    # Run linter
    linter = QuantumLinter(debug=False)

    if lint_path.is_file():
        issues = linter.lint_file(lint_path)
    else:
        issues = linter.lint_directory(lint_path)

    # Filter by severity
    severity_order = {'error': 0, 'warning': 1, 'info': 2}
    min_severity = severity_order[severity]
    issues = [i for i in issues if severity_order[i.severity.value] <= min_severity]

    # Filter by ignore codes
    if ignore:
        issues = [i for i in issues if i.code not in ignore]

    # Sort issues
    issues.sort(key=lambda i: (str(i.file), i.line, severity_order[i.severity.value]))

    # Output results
    if format == 'json':
        _output_json(issues)
    elif format == 'github':
        _output_github(issues)
    else:
        _output_text(issues, console, project_root)

    # Summary
    error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
    warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)
    info_count = sum(1 for i in issues if i.severity == Severity.INFO)

    console.print()
    if error_count > 0:
        console.error(f"Found {error_count} error(s), {warning_count} warning(s), {info_count} info(s)")
        sys.exit(1)
    elif warning_count > 0:
        console.warning(f"Found {warning_count} warning(s), {info_count} info(s)")
    else:
        console.success(f"No issues found! ({info_count} info messages)")


def _output_text(issues: List[LintIssue], console, project_root: Path):
    """Output issues in text format."""
    current_file = None

    for issue in issues:
        if issue.file != current_file:
            current_file = issue.file
            rel_path = issue.file.relative_to(project_root) if issue.file.is_relative_to(project_root) else issue.file
            console.print(f"\n[bold]{rel_path}[/bold]")

        severity_colors = {
            Severity.ERROR: 'red',
            Severity.WARNING: 'yellow',
            Severity.INFO: 'cyan',
        }
        color = severity_colors[issue.severity]

        location = f"{issue.line}:{issue.column}" if issue.column else str(issue.line)
        console.print(f"  [{color}]{issue.severity.value.upper()}[/{color}] [{issue.code}] {location}: {issue.message}")

        if issue.suggestion:
            console.print(f"    [dim]Suggestion: {issue.suggestion}[/dim]")


def _output_json(issues: List[LintIssue]):
    """Output issues in JSON format."""
    import json

    output = [
        {
            'file': str(issue.file),
            'line': issue.line,
            'column': issue.column,
            'severity': issue.severity.value,
            'code': issue.code,
            'message': issue.message,
            'suggestion': issue.suggestion,
        }
        for issue in issues
    ]

    print(json.dumps(output, indent=2))


def _output_github(issues: List[LintIssue]):
    """Output issues in GitHub Actions format."""
    severity_map = {
        Severity.ERROR: 'error',
        Severity.WARNING: 'warning',
        Severity.INFO: 'notice',
    }

    for issue in issues:
        severity = severity_map[issue.severity]
        print(f"::{severity} file={issue.file},line={issue.line},col={issue.column}::[{issue.code}] {issue.message}")
