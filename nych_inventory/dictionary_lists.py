"""Substitute dictionary lists. Not Merriam-Webster, and not an approval."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "dictionary"
ENGLISH_PATH = ROOT / "scowl-en-us-70.txt"
CROSSWORD_PATH = ROOT / "spreadthewordlist.txt"
SOURCES_PATH = ROOT / "SOURCES.json"

_CACHE: tuple[set[str], bool] | None = None


def load_sources() -> dict:
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def _read_words(path: Path) -> set[str]:
    words: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split(";", 1)[0].strip().casefold()
        if token:
            words.add(token)
    return words


def load_dictionary() -> tuple[set[str], bool]:
    """Return the substitute word set and whether the crossword file is present."""
    global _CACHE
    if _CACHE is None:
        words = _read_words(ENGLISH_PATH)
        crossword_loaded = CROSSWORD_PATH.is_file()
        if crossword_loaded:
            words |= _read_words(CROSSWORD_PATH)
        _CACHE = (words, crossword_loaded)
    return _CACHE


def in_dictionary(word: str, dictionary: set[str] | None = None) -> bool:
    key = word.casefold()
    if dictionary is None:
        dictionary, _loaded = load_dictionary()
    return key in dictionary
