"""Occurrence trace IDs from the approved D3 register row.

The payload is NYCH-WORD-ID, a NUL, v1, a NUL, the SHA-256 digest of the
exact input bytes, the zero-based occurrence index, and the start/end byte
offsets. Integers are unsigned 64-bit big-endian. The display form is
sha256:<hex>_<suffix or empty-mark>.

The suffix drops a, e, i, o, and u after accent-folding, keeps y, and
collapses identical adjacent letters. This is the D3 suffix. It is not the
later D15 gestalt-ID abbreviation.
"""
from __future__ import annotations

import hashlib
import unicodedata

EMPTY = "∅"
_TAG = b"NYCH-WORD-ID\x00v1\x00"


class TraceIdError(ValueError):
    """Raised when a suffix still contains a non-ASCII letter."""


def input_digest(raw: bytes) -> bytes:
    return hashlib.sha256(raw).digest()


def consonant_suffix(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in folded if not unicodedata.combining(ch))
    out: list[str] = []
    for char in ascii_text:
        if not char.isalpha():
            continue
        if ord(char) > 127:
            raise TraceIdError(f"suffix letter did not accent-fold to ASCII: {char!r}")
        lower = char.lower()
        if lower in "aeiou":
            continue
        if out and out[-1] == lower:
            continue
        out.append(lower)
    return "".join(out) if out else EMPTY


def trace_id(raw_digest: bytes, index: int, start: int, end: int, suffix: str) -> str:
    if len(raw_digest) != 32:
        raise TraceIdError("input digest must be 32 bytes")
    for value in (index, start, end):
        if type(value) is not int or value < 0:
            raise TraceIdError("index and offsets must be non-negative integers")
    payload = _TAG + raw_digest + index.to_bytes(8, "big") + start.to_bytes(8, "big") + end.to_bytes(8, "big")
    digest = hashlib.sha256(payload).hexdigest()
    return f"sha256:{digest}_{suffix}"
