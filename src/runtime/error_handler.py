"""
Enhanced Error Handler - Phase C: Developer Experience

Provides better error messages with:
- Context (line numbers, code snippets)
- Suggestions (did you mean...?)
- Helpful hints
- Color-coded output
"""

import sys
from pathlib import Path
from typing import Optional, List
import difflib

class QuantumError(Exception):
    """Base class for Quantum errors with enhanced context"""

    def __init__(self, message: str, file_path: Optional[str] = None,
                 line: Optional[int] = None, column: Optional[int] = None,
                 suggestion: Optional[str] = None, hint: Optional[str] = None):
        self.message = message
        self.file_path = file_path
        self.line = line
        self.column = column
        self.suggestion = suggestion
        self.hint = hint
        super().__init__(self.format_error())

    def format_error(self) -> str:
        """Format error message with context"""
        parts = []

        # Header
        parts.append("=" * 60)
        parts.append("❌ QUANTUM ERROR")
        parts.append("=" * 60)

        # Location
        if self.file_path:
            location = f"📂 File: {self.file_path}"
            if self.line:
                location += f":{self.line}"
                if self.column:
                    location += f":{self.column}"
            parts.append(location)

        # Error message
        parts.append(f"\n💥 {self.message}")

        # Code context
        if self.file_path and self.line:
            context = self._get_code_context()
            if context:
                parts.append("\n📝 Code:")
                parts.append(context)

        # Suggestion
        if self.suggestion:
            parts.append(f"\n💡 Suggestion: {self.suggestion}")

        # Hint
        if self.hint:
            parts.append(f"\n🔍 Hint: {self.hint}")

        parts.append("=" * 60)

        return "\n".join(parts)

    def _get_code_context(self, context_lines: int = 3) -> Optional[str]:
        """Get code context around error line"""
        try:
            file_path = Path(self.file_path)
            if not file_path.exists():
                return None

            lines = file_path.read_text(encoding='utf-8').splitlines()

            start = max(0, self.line - context_lines - 1)
            end = min(len(lines), self.line + context_lines)

            context_parts = []
            for i in range(start, end):
                line_num = i + 1
                line_content = lines[i]

                # Mark error line with arrow
                if line_num == self.line:
                    context_parts.append(f"  → {line_num:4d} | {line_content}")
                    # Add column pointer if available
                    if self.column:
                        pointer = " " * (self.column + 10) + "^"
                        context_parts.append(pointer)
                else:
                    context_parts.append(f"    {line_num:4d} | {line_content}")

            return "\n".join(context_parts)

        except Exception:
            return None


class ComponentNotFoundError(QuantumError):
    """Component import not found"""

    def __init__(self, component_name: str, file_path: str, line: int,
                 available_components: List[str] = None):
        # Find similar component names
        suggestion = None
        if available_components:
            matches = difflib.get_close_matches(component_name, available_components, n=3, cutoff=0.6)
            if matches:
                if len(matches) == 1:
                    suggestion = f"Did you mean '{matches[0]}'?"
                else:
                    suggestion = f"Did you mean one of: {', '.join(matches)}?"

        hint = f"Add: <q:import component=\"{component_name}\" />"

        super().__init__(
            f"Component '{component_name}' not found",
            file_path=file_path,
            line=line,
            suggestion=suggestion,
            hint=hint
        )


class ValidationErrorWithContext(QuantumError):
    """Validation error with context"""

    def __init__(self, field_name: str, validation_type: str,
                 value: any, file_path: str = None, line: int = None):
        message = f"Validation failed for field '{field_name}' ({validation_type})"

        if validation_type == "required":
            suggestion = f"Field '{field_name}' is required but was not provided"
        elif validation_type == "type":
            suggestion = f"Expected type differs from provided value: {value}"
        elif validation_type == "minlength":
            suggestion = f"Value '{value}' is too short"
        elif validation_type == "maxlength":
            suggestion = f"Value '{value}' is too long"
        elif validation_type == "pattern":
            suggestion = f"Value '{value}' doesn't match required pattern"
        else:
            suggestion = f"Validation '{validation_type}' failed for value: {value}"

        super().__init__(
            message,
            file_path=file_path,
            line=line,
            suggestion=suggestion
        )


class QueryErrorWithContext(QuantumError):
    """Query error with SQL context"""

    def __init__(self, query_name: str, sql: str, error: str,
                 file_path: str = None, line: int = None):
        message = f"Query '{query_name}' failed"

        # Provide SQL-specific suggestions
        suggestion = None
        if "syntax error" in error.lower():
            suggestion = "Check your SQL syntax"
        elif "table" in error.lower() and "doesn't exist" in error.lower():
            suggestion = "Table doesn't exist - check your database schema"
        elif "column" in error.lower():
            suggestion = "Column doesn't exist - check your table structure"
        elif "duplicate" in error.lower():
            suggestion = "Duplicate entry - check for unique constraints"

        hint = f"SQL: {sql[:100]}..." if len(sql) > 100 else f"SQL: {sql}"

        super().__init__(
            f"{message}: {error}",
            file_path=file_path,
            line=line,
            suggestion=suggestion,
            hint=hint
        )


class TransactionErrorWithContext(QuantumError):
    """Transaction error with rollback info"""

    def __init__(self, error: str, statements_executed: int,
                 file_path: str = None, line: int = None):
        message = "Transaction failed and was rolled back"

        suggestion = f"{statements_executed} statement(s) were executed before failure"
        hint = "All changes have been rolled back. Check the error above and fix the issue."

        super().__init__(
            f"{message}: {error}",
            file_path=file_path,
            line=line,
            suggestion=suggestion,
            hint=hint
        )


class FileUploadErrorWithContext(QuantumError):
    """File upload error with details"""

    def __init__(self, error: str, filename: str = None,
                 file_size: int = None, max_size: int = None,
                 file_path: str = None, line: int = None):
        message = f"File upload failed"

        suggestion = None
        if "too large" in error.lower():
            if file_size and max_size:
                suggestion = f"File is {file_size} bytes but maximum is {max_size} bytes"
        elif "type" in error.lower() or "extension" in error.lower():
            suggestion = "File type not allowed - check allowed extensions"

        hint = None
        if filename:
            hint = f"Filename: {filename}"

        super().__init__(
            f"{message}: {error}",
            file_path=file_path,
            line=line,
            suggestion=suggestion,
            hint=hint
        )


class ErrorHandler:
    """Central error handler for better error reporting"""

    @staticmethod
    def handle_parse_error(error: Exception, file_path: str) -> QuantumError:
        """Convert parse errors to enhanced errors"""
        error_msg = str(error)

        # Extract line and column from XML parse errors
        line = None
        column = None
        if "line" in error_msg:
            import re
            match = re.search(r'line (\d+)', error_msg)
            if match:
                line = int(match.group(1))
            match = re.search(r'column (\d+)', error_msg)
            if match:
                column = int(match.group(1))

        return QuantumError(
            f"Parse error: {error_msg}",
            file_path=file_path,
            line=line,
            column=column,
            suggestion="Check your XML syntax",
            hint="Make sure all tags are properly closed and attributes are quoted"
        )

    @staticmethod
    def handle_runtime_error(error: Exception, component_name: str,
                            file_path: str = None) -> QuantumError:
        """Convert runtime errors to enhanced errors"""
        return QuantumError(
            f"Runtime error in component '{component_name}': {error}",
            file_path=file_path,
            suggestion="Check your component logic and variable names",
            hint="Use quantum inspect <component> to debug"
        )

    @staticmethod
    def print_warning(message: str):
        """Print formatted warning"""
        print(f"⚠️  Warning: {message}", file=sys.stderr)

    @staticmethod
    def print_info(message: str):
        """Print formatted info"""
        print(f"ℹ️  {message}")

    @staticmethod
    def print_success(message: str):
        """Print formatted success"""
        print(f"✅ {message}")
