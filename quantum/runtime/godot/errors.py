"""The compile error: a message, and the line of the .q it is about."""

from typing import Optional


class GameCompileError(Exception):
    def __init__(self, message: str, line: Optional[int] = None, file: Optional[str] = None):
        self.message = message
        self.line = line
        self.file = file
        super().__init__(self.__str__())

    def __str__(self) -> str:
        where = ''
        if self.file:
            where = self.file
        if self.line:
            where += f':{self.line}'
        return f'{where}: {self.message}' if where else self.message
