"""Gestalt-ID abbreviation preview. Not wired into any Builder.

Vowels a, e, i, o, and u are dropped. Identical adjacent letters collapse.
The letter c is kept. A word that starts with a vowel is prefixed with '
in place of that vowel. A doubled consonant immediately after that vowel
is kept in full. y-initial words, all-vowel words, and apostrophes inside
compounds are still open and raise.
"""
from __future__ import annotations

VOWELS = frozenset("aeiou")


class GestaltAbbrevError(ValueError):
    """Raised when an input is an owner-open edge or otherwise unsupported."""


def _collapse(text: str) -> str:
    chars: list[str] = []
    for ch in text:
        low = ch.lower()
        if low in VOWELS:
            continue
        if chars and chars[-1] == low:
            continue
        chars.append(low)
    return "".join(chars)


def abbreviate_word(word: str) -> str:
    """Abbreviate one word. Vowel-initial words start with an apostrophe."""
    if not word or any(not ch.isalpha() for ch in word):
        raise GestaltAbbrevError("open edge or unsupported word; not decided")
    first = word[0].lower()
    if first == "y":
        raise GestaltAbbrevError("y-initial word; not decided")
    if first in VOWELS:
        rest = word[1:]
        if (
            len(rest) >= 2
            and rest[0].lower() == rest[1].lower()
            and rest[0].lower() not in VOWELS
            and rest[0].lower() != "y"
        ):
            body = rest[0].lower() + rest[1].lower() + _collapse(rest[2:])
        else:
            body = _collapse(rest)
        if not body:
            raise GestaltAbbrevError("all-vowel word; not decided")
        return "'" + body
    body = _collapse(word)
    if not body:
        raise GestaltAbbrevError("all-vowel word; not decided")
    return body


def abbreviate_compound(words: list[str], *, contains_proper_name: bool) -> str:
    """Join abbreviated parts with no separator.

    ``contains_proper_name`` True capitalizes every part. False keeps the
    first part lowercase and capitalizes the later parts. Only two-part
    compounds of consonant-initial words are accepted. A vowel-initial part
    is refused because capitalization next to the apostrophe is not decided.
    """
    if not isinstance(contains_proper_name, bool):
        raise GestaltAbbrevError("contains_proper_name must be true or false")
    if len(words) != 2:
        raise GestaltAbbrevError("compound length other than 2 is not decided")
    parts: list[str] = []
    for word in words:
        if not word or not word[0].isalpha():
            raise GestaltAbbrevError("open edge or unsupported word; not decided")
        if word[0].lower() in VOWELS or word[0].lower() == "y":
            raise GestaltAbbrevError("apostrophe or y-initial part in a compound is not decided")
        parts.append(abbreviate_word(word))
    if contains_proper_name:
        return "".join(part.capitalize() for part in parts)
    return parts[0] + parts[1].capitalize()
