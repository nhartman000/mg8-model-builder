"""Provisional proper-name step for the owner-stated capital-letter rule.

The rule and the later sentence answers are not approved. No dictionary is
selected. A mid-sentence capital that is not all-caps is an interpreted name.
A sentence-initial capital stays undecided. An all-caps word stays undecided.
The surface form is not rewritten.
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
    base = {
        "token_index": index,
        "text": word,
        "approved": False,
        "provisional": True,
        "interpreted": False,
    }
    if not capitalized:
        return {**base, "verdict": "not-capitalized", "flags": []}
    all_caps = len(letters) >= 2 and all(char.isupper() for char in letters)
    if all_caps:
        flags = ["all-caps", "dictionary-unknown"]
        if sentence_initial:
            flags.append("sentence-initial")
        return {**base, "verdict": "undecided", "flags": flags}
    if sentence_initial:
        return {
            **base,
            "verdict": "undecided",
            "flags": ["sentence-initial", "dictionary-unknown"],
            "surface_form": word,
        }
    return {
        **base,
        "interpreted": True,
        "verdict": "name",
        "flags": ["mid-sentence-capital"],
        "surface_form": word,
    }
