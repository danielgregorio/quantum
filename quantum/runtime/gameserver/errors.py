"""The game server's errors: a file that does not say a world, and a command the world says no to."""

from typing import Optional


class GameServerError(Exception):
    """What a world's file cannot be: a tag or an attribute with no entry in the schema, a value of the wrong kind,
    a map that cannot be read. A message, and the line of the .q it is about."""

    def __init__(self, message: str, line: Optional[int] = None, file: Optional[str] = None):
        self.message = message
        self.line = line
        self.file = file
        super().__init__(self.__str__())

    def __str__(self) -> str:
        where = self.file or ''
        if self.line:
            where += f':{self.line}'
        return f'{where}: {self.message}' if where else self.message


class Refused(Exception):
    """A command the world said no to: its q:require did not hold, it came too fast, or it was not one a player may
    send. Nothing it did stays (the transaction is rolled back); the player's client gets the reason."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class RuleError(Exception):
    """A rule that could not run: an expression that failed, a field that is not there. Inside a command it refuses
    the command; inside q:every or q:on-join it is kept in the world's errors, and the world goes on."""

    def __init__(self, message: str, line: Optional[int] = None):
        self.message = message
        self.line = line
        super().__init__(f'line {line}: {message}' if line else message)
