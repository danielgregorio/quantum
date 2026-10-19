"""The little of PNG the compiler needs: a file's size (to count a sheet's frames) and writing one (the font).

No decoding: the daemon reads the sheets itself. Both are the standard's
own: an 8-byte signature, then chunks of length, type, data, CRC; the first
chunk is IHDR with the width and the height.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Iterable, Tuple

SIGNATURE = b'\x89PNG\r\n\x1a\n'


def size_of(path: Path) -> Tuple[int, int]:
    """(width, height) of a PNG, or a ValueError for what is not one."""
    with open(path, 'rb') as f:
        head = f.read(33)
    if head[:8] != SIGNATURE or head[12:16] != b'IHDR':
        raise ValueError(f'{path.name} is not a PNG')
    width, height = struct.unpack('>II', head[16:24])
    if not width or not height:
        raise ValueError(f'{path.name} is empty')
    return width, height


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)


def write(path: Path, width: int, height: int, rows: Iterable[bytes]) -> None:
    """Writes an 8-bit RGBA PNG: each row is width*4 bytes."""
    raw = b''.join(b'\x00' + row for row in rows)
    data = (SIGNATURE
            + _chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + _chunk(b'IDAT', zlib.compress(raw, 9))
            + _chunk(b'IEND', b''))
    path.write_bytes(data)
