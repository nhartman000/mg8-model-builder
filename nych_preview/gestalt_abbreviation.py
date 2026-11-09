"""Gestalt-ID abbreviation preview. Not wired into any Builder.

This reproduces Nick Hartman's three compound examples and refuses the
open cases he has not decided. The ``ck`` -> ``k`` step is a flagged
interpretation: identical-letter collapse alone turns "brick" into "brck",
but the owner example is "brkLyr".
"""
from __future__ import annotations

VOWELS = frozenset("aeiou")


class GestaltAbbrevError(ValueError):
    """Raised when an input is an owner-open edge or otherwise unsupported."""


def _skeleton(word: str) -> str:
    if not word or any(not ch.isalpha() for ch in word):
        raise GestaltAbbrevError("open edge or unsupported word; not decided")
    if word[0].lower() in VOWELS:
        raise GestaltAbbrevError("word starting with a vowel; not decided")
    chars: list[str] = []
    for ch in word:
        low = ch.lower()
        if low in VOWELS:
            continue
        if chars and chars[-1] == low:
            continue
        if low == "k" and chars and chars[-1] == "c":
            chars[-1] = "k"
            continue
        chars.append(low)
    if not chars:
        raise GestaltAbbrevError("all-vowel word; not decided")
    return "".join(chars)


def abbreviate_compound(words: list[str], *, contains_proper_name: bool) -> str:
    """Join abbreviated parts with no separator.

    ``contains_proper_name`` True capitalizes every part. False keeps the
    first part lowercase and capitalizes the later parts. Only two-part
    compounds are accepted.
    """
    if not isinstance(contains_proper_name, bool):
        raise GestaltAbbrevError("contains_proper_name must be true or false")
    if len(words) != 2:
        raise GestaltAbbrevError("compound length other than 2 is not decided")
    parts = [_skeleton(word) for word in words]
    if contains_proper_name:
        return "".join(part.capitalize() for part in parts)
    return parts[0] + parts[1].capitalize()
