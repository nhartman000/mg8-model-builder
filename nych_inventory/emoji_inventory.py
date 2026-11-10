"""Unicode Emoji 18.0 inventory from the fully-qualified rows of emoji-test.txt.

This is the owner-stated source recorded on 2026-11-10. It is not approved.
Entries carry code points, the CLDR short name, and group/subgroup.
There is no NYCH gestalt and no alias folding.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_CLDR_NAME = re.compile(r"\sE\d+\.\d+\s+(.*)$")

ROOT = Path(__file__).resolve().parent / "emoji"
TEST_PATH = ROOT / "emoji-test.txt"
SOURCES_PATH = ROOT / "SOURCES.json"


@dataclass(frozen=True)
class EmojiEntry:
    codepoints: tuple[int, ...]
    name: str
    group: str
    subgroup: str

    @property
    def text(self) -> str:
        return "".join(chr(cp) for cp in self.codepoints)


def load_sources() -> dict:
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def load_emoji() -> tuple[EmojiEntry, ...]:
    group = ""
    subgroup = ""
    entries: list[EmojiEntry] = []
    for line in TEST_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("# group:"):
            group = line.split(":", 1)[1].strip()
            continue
        if line.startswith("# subgroup:"):
            subgroup = line.split(":", 1)[1].strip()
            continue
        if not line or line.startswith("#") or "#" not in line or ";" not in line:
            continue
        left, right = line.split("#", 1)
        codepoints, status = left.split(";", 1)
        if status.strip() != "fully-qualified":
            continue
        sequence = tuple(int(piece, 16) for piece in codepoints.split())
        comment = right.strip()
        match = _CLDR_NAME.search(comment)
        if match is None:
            raise ValueError(f"emoji-test comment has no CLDR name: {comment}")
        entries.append(EmojiEntry(sequence, match.group(1), group, subgroup))
    return tuple(entries)


class EmojiTrie:
    def __init__(self, entries: tuple[EmojiEntry, ...]) -> None:
        self.root: dict = {}
        for entry in entries:
            node = self.root
            for codepoint in entry.codepoints:
                node = node.setdefault(codepoint, {})
            node["entry"] = entry

    def longest_at(self, text: str, index: int) -> tuple[EmojiEntry | None, int]:
        node = self.root
        found: EmojiEntry | None = None
        end = index
        cursor = index
        while cursor < len(text):
            node = node.get(ord(text[cursor]))
            if node is None:
                break
            cursor += 1
            entry = node.get("entry")
            if entry is not None:
                found = entry
                end = cursor
        return found, end


_TRIE: EmojiTrie | None = None


def emoji_trie() -> EmojiTrie:
    global _TRIE
    if _TRIE is None:
        _TRIE = EmojiTrie(load_emoji())
    return _TRIE
