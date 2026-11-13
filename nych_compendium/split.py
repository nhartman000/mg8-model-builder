"""D2 page split. The payload and bucket ranges are the approved rule."""
from __future__ import annotations

import hashlib

SNAPSHOT_ID = "enwiki-20261001"
SPLIT_TAG = "NYCH-D2-SPLIT-v1"


def bucket(page_id: int, snapshot_id: str = SNAPSHOT_ID) -> int:
    if not isinstance(page_id, int) or isinstance(page_id, bool) or page_id < 0:
        raise ValueError("page_id must be a non-negative integer")
    payload = SPLIT_TAG.encode("utf-8") + b"\x00" + snapshot_id.encode("utf-8") + b"\x00" + str(page_id).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest(), "big") % 100


def split_name(page_id: int, snapshot_id: str = SNAPSHOT_ID) -> str:
    value = bucket(page_id, snapshot_id)
    if value <= 89:
        return "train"
    if value <= 94:
        return "validation"
    return "test"
