"""Read the dimensions of editorial raster assets using only the standard library."""

from functools import lru_cache
from pathlib import Path
import struct


@lru_cache(maxsize=1024)
def image_metadata(path: Path) -> tuple[str, int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return "PNG", *struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return "GIF", *struct.unpack("<HH", data[6:10])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        offset = 12
        while offset + 8 <= len(data):
            kind = data[offset:offset + 4]
            size = int.from_bytes(data[offset + 4:offset + 8], "little")
            chunk = data[offset + 8:offset + 8 + size]
            if len(chunk) != size:
                break
            if kind == b"VP8X" and size >= 10:
                return "WEBP", 1 + int.from_bytes(chunk[4:7], "little"), 1 + int.from_bytes(chunk[7:10], "little")
            if kind == b"VP8 " and size >= 10 and chunk[3:6] == b"\x9d\x01\x2a":
                width, height = struct.unpack("<HH", chunk[6:10])
                return "WEBP", width & 0x3fff, height & 0x3fff
            if kind == b"VP8L" and size >= 5 and chunk[0] == 0x2f:
                bits = int.from_bytes(chunk[1:5], "little")
                return "WEBP", (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
            offset += 8 + size + (size % 2)
    if data[:2] == b"\xff\xd8":
        offset = 2
        while offset < len(data):
            if data[offset] != 0xff:
                break
            while offset < len(data) and data[offset] == 0xff:
                offset += 1
            if offset >= len(data):
                break
            marker = data[offset]
            offset += 1
            if marker in (0xd9, 0xda):
                break
            if marker == 0x01 or 0xd0 <= marker <= 0xd8:
                continue
            if offset + 2 > len(data):
                break
            size = int.from_bytes(data[offset:offset + 2], "big")
            if size < 2 or offset + size > len(data):
                break
            if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf) and size >= 7:
                height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
                return "JPEG", width, height
            offset += size
    raise ValueError(f"Unsupported or malformed raster image: {path.name}")
