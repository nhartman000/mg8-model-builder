"""Provisional proper-name step for the owner-stated capital-letter rule.

The rule and the later answers are not approved. Sentence-initial words are
checked against the SCOWL and Spread the Wordlist substitutes, which are not
Merriam-Webster. A mid-sentence capital that is not all-caps is an interpreted
name. A word of at least two letters that is all capitals is an interpreted
acronym. Acronyms keep their surface form and are excluded from gestalting.
"""
from __future__ import annotations

from nych_inventory.dictionary_lists import in_dictionary, load_dictionary
from nych_smoke.tokenize import tokenize

SENTENCE_END = {".", "!", "?"}


def classify_names(text: str, dictionary: set[str] | None = None) -> list[dict]:
    """Return one provisional row per word token. Nothing here is approved."""
    _raw, tokens = tokenize(text)
    return classify_token_rows(tokens, dictionary)


def classify_token_rows(tokens, dictionary: set[str] | None = None) -> list[dict]:
    """Classify already-tokenized words. Nothing here is approved."""
    if dictionary is None:
        dictionary, _crossword_loaded = load_dictionary()
    rows: list[dict] = []
    sentence_start = True
    for index, token in enumerate(tokens):
        if token.kind == "word":
            rows.append(_row(index, token.text, sentence_start, dictionary))
            sentence_start = False
            continue
        if token.kind == "punct" and token.text in SENTENCE_END:
            sentence_start = True
    return rows


def _row(index: int, word: str, sentence_initial: bool, dictionary: set[str]) -> dict:
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
        return {
            **base,
            "interpreted": True,
            "verdict": "acronym",
            "flags": ["all-caps"],
            "surface_form": word,
            "gestalt": "excluded",
        }
    if sentence_initial:
        if in_dictionary(word, dictionary):
            return {
                **base,
                "verdict": "ordinary",
                "flags": ["sentence-initial", "in-substitute-dictionary"],
                "surface_form": word,
            }
        return {
            **base,
            "interpreted": True,
            "verdict": "name",
            "flags": ["sentence-initial", "not-in-substitute-dictionary"],
            "surface_form": word,
        }
    return {
        **base,
        "interpreted": True,
        "verdict": "name",
        "flags": ["mid-sentence-capital"],
        "surface_form": word,
    }
