"""Whitespace tokenizer for the approved B2 span rules that do not need an external lexicon.

Approved and implemented here: whitespace-delimited spans, exact UTF-8 offsets,
punctuation as its own token, apostrophes and hyphens kept inside a word,
each ordinary space as <SPACE>, and distinct tab and line-break tokens.
Repeated whitespace stays repeated tokens.

Not implemented, because the approved sources are not in this environment:
the versioned emoji inventory, the enwiki typo compendium, keyboard maps,
and the Wikidata proper-name lexicon.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int
    kind: str


def tokenize(text: str) -> tuple[bytes, tuple[Token, ...]]:
    """Tokenize ``text``. Offsets are into the exact UTF-8 bytes of ``text``."""
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    raw = text.encode("utf-8")
    tokens: list[Token] = []
    offset = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char in {" ", "\t", "\n", "\r"}:
            kind = {" ": "space", "\t": "tab", "\n": "line", "\r": "line"}[char]
            label = {" ": "<SPACE>", "\t": "<TAB>", "\n": "<LF>", "\r": "<CR>"}[char]
            size = len(char.encode("utf-8"))
            tokens.append(Token(label, offset, offset + size, kind))
            offset += size
            index += 1
            continue
        if char.isalnum():
            end = index + 1
            while end < len(text) and _word_continue(text, end):
                end += 1
            word = text[index:end]
            size = len(word.encode("utf-8"))
            tokens.append(Token(word, offset, offset + size, "word"))
            offset += size
            index = end
            continue
        size = len(char.encode("utf-8"))
        tokens.append(Token(char, offset, offset + size, "punct"))
        offset += size
        index += 1
    covered = b"".join(raw[token.start:token.end] for token in tokens)
    if covered != raw or offset != len(raw):
        raise RuntimeError("tokenizer spans do not cover the source bytes")
    return raw, tuple(tokens)


def _word_continue(text: str, index: int) -> bool:
    char = text[index]
    if char.isalnum():
        return True
    return char in {"'", "-"} and index + 1 < len(text) and text[index + 1].isalnum()
