"""Provisional proper-name step for the owner-stated capital-letter rule.

The rule is not approved. Verbatim: if it begins with a capital letter and
isn't in the dictionary, it's a name. No dictionary is selected, so a
capitalized word is never classified as a name. Sentence-initial words,
possible dictionary words, and all-caps words are flagged and left open.
"""
from __future__ import annotations

from nych_smoke.tokenize import tokenize

SENTENCE_END = {".", "!", "?"}


def classify_names(text: str) -> list[dict]:
    """Return one provisional row per word token. Nothing here is approved."""
    _raw, tokens = tokenize(text)
    rows: list[dict] = []
    sentence_start = True
    for index, token in enumerate(tokens):
        if token.kind == "word":
            rows.append(_row(index, token.text, sentence_start))
            sentence_start = False
            continue
        if token.kind == "punct" and token.text in SENTENCE_END:
            sentence_start = True
    return rows


def _row(index: int, word: str, sentence_initial: bool) -> dict:
    letters = [char for char in word if char.isalpha()]
    capitalized = bool(letters) and letters[0].isupper()
    if not capitalized:
        return {
            "token_index": index,
            "text": word,
            "approved": False,
            "provisional": True,
            "verdict": "not-capitalized",
            "flags": [],
        }
    flags = ["dictionary-unknown", "dictionary-word-case-open"]
    if sentence_initial:
        flags.append("sentence-initial")
    if len(letters) >= 2 and all(char.isupper() for char in letters):
        flags.append("all-caps")
    return {
        "token_index": index,
        "text": word,
        "approved": False,
        "provisional": True,
        "verdict": "undecided",
        "flags": flags,
    }
