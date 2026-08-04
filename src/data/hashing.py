"""SHA256 kwa partitions na configs (DF-01, spec §2 + §8).

Hash ni ya **bytes za faili**, si ya maudhui yaliyofasiriwa: partition
ikibadilishwa kwa namna yoyote (hata metadata), hash inabadilika. Ndiyo maana
hii inatosha kama kipimo cha immutability.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_BYTES = 1 << 20  # 1 MiB
PREFIX = "sha256:"


def sha256_bytes(payload: bytes) -> str:
    return PREFIX + hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str | Path, chunk_bytes: int = CHUNK_BYTES) -> str:
    """SHA256 ya faili nzima, ikisomwa kwa vipande (partitions ni GB)."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk_bytes)
            if not block:
                break
            digest.update(block)
    return PREFIX + digest.hexdigest()


def is_sha256(value: str) -> bool:
    if not value.startswith(PREFIX):
        return False
    hexpart = value[len(PREFIX) :]
    return len(hexpart) == 64 and all(c in "0123456789abcdef" for c in hexpart)
