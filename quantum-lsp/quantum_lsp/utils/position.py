"""
Position utilities for converting between offsets and line/column positions.
"""

from typing import Tuple


def offset_to_position(text: str, offset: int) -> Tuple[int, int]:
    """
    Convert a character offset to (line, column) position.

    Args:
        text: The full document text
        offset: Character offset (0-based)

    Returns:
        Tuple of (line, column), both 0-based
    """
    if offset < 0:
        return (0, 0)

    line = 0
    col = 0

    for i, char in enumerate(text):
        if i >= offset:
            break
        if char == '\n':
            line += 1
            col = 0
        else:
            col += 1

    return (line, col)


def position_to_offset(text: str, line: int, column: int) -> int:
    """
    Convert a (line, column) position to character offset.

    Args:
        text: The full document text
        line: Line number (0-based)
        column: Column number (0-based)

    Returns:
        Character offset (0-based)
    """
    lines = text.split('\n')

    if line < 0:
        return 0

    offset = 0

    # Add lengths of all lines before target line
    for i in range(min(line, len(lines))):
        offset += len(lines[i]) + 1  # +1 for newline

    # Add column offset
    if line < len(lines):
        offset += min(column, len(lines[line]))

    return offset


def get_line_at_position(text: str, line: int) -> str:
    """
    Get the text of a specific line.

    Args:
        text: The full document text
        line: Line number (0-based)

    Returns:
        The line text, or empty string if line doesn't exist
    """
    lines = text.split('\n')
    if 0 <= line < len(lines):
        return lines[line]
    return ""


def get_word_at_offset(text: str, offset: int) -> Tuple[str, int, int]:
    """
    Get the word at a given offset.

    Args:
        text: The full document text
        offset: Character offset

    Returns:
        Tuple of (word, start_offset, end_offset)
    """
    if offset < 0 or offset >= len(text):
        return ("", offset, offset)

    # Find word start
    start = offset
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] in '_:-'):
        start -= 1

    # Find word end
    end = offset
    while end < len(text) and (text[end].isalnum() or text[end] in '_:-'):
        end += 1

    return (text[start:end], start, end)
