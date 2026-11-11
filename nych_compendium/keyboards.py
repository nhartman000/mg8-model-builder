"""Keyboard maps named by D2.

The four ids are the approved registry. The coordinate tables and the
one-character neighbor test are interpreted: the owner named the layouts and
neighboring-key substitutions, and did not publish a key coordinate table.
Other key-error classes stay unresolved and are not guessed.
"""
from __future__ import annotations

LAYOUTS = {
    "us-qwerty": ("qwertyuiop", "asdfghjkl", "zxcvbnm"),
    "uk-qwerty": ("qwertyuiop", "asdfghjkl", "zxcvbnm"),
    "azerty": ("azertyuiop", "qsdfghjklm", "wxcvbn"),
    "qwertz": ("qwertzuiop", "asdfghjkl", "yxcvbnm"),
}
LAYOUT_VERSION = "interpreted-adjacency-v1"


def _neighbors(rows: tuple[str, ...]) -> dict[str, set[str]]:
    coords = {}
    for row_index, row in enumerate(rows):
        for column, char in enumerate(row):
            coords[char] = (column + (0.5 if row_index % 2 else 0.0), float(row_index))
    neighbors = {char: set() for char in coords}
    keys = list(coords)
    for left_index, left in enumerate(keys):
        lx, ly = coords[left]
        for right in keys[left_index + 1 :]:
            rx, ry = coords[right]
            if max(abs(lx - rx), abs(ly - ry)) <= 1.0:
                neighbors[left].add(right)
                neighbors[right].add(left)
    return neighbors


NEIGHBORS = {name: _neighbors(rows) for name, rows in LAYOUTS.items()}


def neighbor_substitution(surface: str, candidate: str, layout: str) -> bool:
    """True when the candidate replaces exactly one character with a neighbor."""
    if layout not in NEIGHBORS:
        raise KeyError(layout)
    if not isinstance(surface, str) or not isinstance(candidate, str):
        return False
    if len(surface) != len(candidate) or surface == candidate or len(surface) == 0:
        return False
    changes = [(left, right) for left, right in zip(surface, candidate) if left != right]
    if len(changes) != 1:
        return False
    old, new = changes[0]
    return new.lower() in NEIGHBORS[layout].get(old.lower(), set())


def layouts_agree(surface: str, candidate: str, layout: str | None) -> bool:
    """Known layout uses that map. Unknown layout requires all four to agree."""
    if layout is not None:
        return neighbor_substitution(surface, candidate, layout)
    answers = {neighbor_substitution(surface, candidate, name) for name in LAYOUTS}
    return answers == {True}
