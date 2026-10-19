"""The one error of the screen compiler, with the line it names."""

from __future__ import annotations

from typing import Optional


class ScreenCompileError(Exception):
    def __init__(self, message: str, line: Optional[int] = None, file: Optional[str] = None):
        self.message = message
        self.line = line
        self.file = file
        super().__init__(message)

    def __str__(self) -> str:
        where = ''
        if self.file:
            where = f'{self.file}:'
        if self.line is not None:
            where += f'{self.line}:'
        return f'{where} {self.message}' if where else self.message
