"""Gestalt-ID abbreviation preview. Not wired into any Builder.

The letter sequence ie is written as y before vowels are dropped.
Vowels a, e, i, o, and u are dropped. Identical adjacent letters collapse.
The letter c is kept. A word that starts with a vowel is prefixed with '
in place of that vowel. A doubled consonant immediately after that vowel
is kept in full. In a compound, a vowel-initial later part keeps '
and the next letter is capitalized.

A standalone word of three letters or fewer is left as written. A short
part inside a compound is still abbreviated. An owner-only override list
is consulted before the default rule for longer words. New
entries are added only when Nick Hartman states them. y-initial words,
all-vowel words, and a vowel-initial first part of a compound still raise.
"""
from __future__ import annotations

import json
from pathlib import Path

VOWELS = frozenset("aeiou")
OVERRIDES_PATH = Path(__file__).resolve().parent / "fixtures" / "gestalt-abbrev-overrides.v1.json"
COMPOUNDS_PATH = Path(__file__).resolve().parent / "fixtures" / "gestalt-compounds.v1.json"


class GestaltAbbrevError(ValueError):
    """Raised when an input is an owner-open edge or otherwise unsupported."""


def _load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    words = data.get("words")
    if not isinstance(words, dict) or not words:
        raise GestaltAbbrevError("override list must map words to skeletons")
    out: dict[str, str] = {}
    for key, skeleton in words.items():
        if not isinstance(key, str) or key != key.lower() or not key.isalpha():
            raise GestaltAbbrevError("override keys are lowercase words")
        if not isinstance(skeleton, str) or not skeleton:
            raise GestaltAbbrevError("override skeleton must be a non-empty string")
        out[key] = skeleton
    return out


OVERRIDES = _load_overrides()


def _load_compounds(path: Path = COMPOUNDS_PATH) -> dict[tuple[str, ...], dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("compounds")
    if not isinstance(items, list) or not items:
        raise GestaltAbbrevError("compound list must be a non-empty list")
    out: dict[tuple[str, ...], dict] = {}
    for item in items:
        words = item.get("words")
        if not isinstance(words, list) or len(words) != 2:
            raise GestaltAbbrevError("each compound has two owner-stated words")
        key = tuple(word.lower() for word in words)
        if key in out:
            raise GestaltAbbrevError("duplicate compound")
        out[key] = item
    return out


COMPOUNDS = _load_compounds()


def abbreviate_owner_compound(words: list[str], *, contains_proper_name: bool) -> str:
    """Abbreviate a pair only when the owner has listed it.

    Unlisted pairs are not guessed. Whether an adjective is required for
    the gestalt is semantic and is not read from spelling.
    """
    key = tuple(word.lower() for word in words)
    if key not in COMPOUNDS:
        raise GestaltAbbrevError("pair is not an owner-stated compound")
    return abbreviate_compound(words, contains_proper_name=contains_proper_name)


def render_phrase(words: list[str], *, as_compound: bool) -> str:
    """Render a phrase as one object or as separate words.

    The compound list is consulted only when ``as_compound`` is true.
    A literal phrase stays separate words, so a hot dog the animal is
    "hot dog" and the food object is htDg.
    """
    if as_compound:
        return abbreviate_owner_compound(words, contains_proper_name=False)
    return " ".join(abbreviate_word(word) for word in words)


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


def _rewrite_ie(word: str) -> str:
    """Write the letter sequence ie as y before vowels are dropped.

    This is the default. The owner said it is usual, not universal, and
    cited except-after-c. Those exceptions are not guessed here.
    """
    out: list[str] = []
    index = 0
    while index < len(word):
        if index + 1 < len(word) and word[index].lower() == "i" and word[index + 1].lower() == "e":
            out.append("y")
            index += 2
        else:
            out.append(word[index])
            index += 1
    return "".join(out)


def _require_word(word: str) -> None:
    if not word or any(not ch.isalpha() for ch in word):
        raise GestaltAbbrevError("open edge or unsupported word; not decided")


def _abbreviate_token(word: str) -> str:
    """Abbreviate one token, including a short part inside a compound."""
    _require_word(word)
    override = OVERRIDES.get(word.lower())
    if override is not None:
        return override
    word = _rewrite_ie(word)
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


def abbreviate_word(word: str) -> str:
    """Abbreviate a standalone word. Three letters or fewer stay as written."""
    _require_word(word)
    if len(word) <= 3:
        return word
    return _abbreviate_token(word)


def abbreviate_compound(words: list[str], *, contains_proper_name: bool) -> str:
    """Join two abbreviated parts.

    A vowel-initial later part keeps its leading apostrophe and the next
    letter is capitalized, so fried apple is fryd'Ppl. A vowel-initial or
    y-initial first part stays undecided
    unless that word is in the owner override list.
    """
    if not isinstance(contains_proper_name, bool):
        raise GestaltAbbrevError("contains_proper_name must be true or false")
    if len(words) != 2:
        raise GestaltAbbrevError("compound length other than 2 is not decided")
    left_word, right_word = words
    if (
        not left_word
        or not right_word
        or any(not ch.isalpha() for ch in left_word)
        or any(not ch.isalpha() for ch in right_word)
    ):
        raise GestaltAbbrevError("open edge or unsupported word; not decided")
    if left_word[0].lower() in VOWELS or left_word[0].lower() == "y":
        if left_word.lower() not in OVERRIDES:
            raise GestaltAbbrevError("vowel-initial or y-initial first part in a compound is not decided")
    if right_word[0].lower() == "y" and right_word.lower() not in OVERRIDES:
        raise GestaltAbbrevError("y-initial word; not decided")
    left = _abbreviate_token(left_word)
    right = _abbreviate_token(right_word)
    if right_word[0].lower() in VOWELS or right.startswith("'"):
        if not right.startswith("'"):
            right = "'" + right
        if len(right) > 1 and right[1].isalpha():
            right = "'" + right[1].upper() + right[2:]
        if len(right) < 2:
            raise GestaltAbbrevError("all-vowel word; not decided")
        if contains_proper_name and left[:1].isalpha():
            left = left.capitalize()
        return left + right
    if contains_proper_name:
        return left.capitalize() + right.capitalize()
    return left + right.capitalize()
