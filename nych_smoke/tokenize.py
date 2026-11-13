"""Whitespace tokenizer for the approved B2 span rules.

Approved and implemented here: whitespace-delimited spans, exact UTF-8 offsets,
punctuation as its own token, apostrophes and hyphens kept inside a word,
each ordinary space as <SPACE>, and distinct tab and line-break tokens.
Repeated whitespace stays repeated tokens.

A fully-qualified sequence from the owner-stated Unicode Emoji 18.0 inventory
is one atomic token. That inventory is not approved, and it does not fold
skin tones or assign a NYCH gestalt.

The typo compendium is a separate hypothesis layer. This tokenizer does not
correct spellings. The Wikidata proper-name lexicon is not in this environment.
"""
from __future__ import annotations

from dataclasses import dataclass

from nych_inventory.emoji_inventory import EmojiEntry, emoji_trie


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int
    kind: str
    emoji_name: str | None = None
    emoji_group: str | None = None
    emoji_subgroup: str | None = None
    emoji_codepoints: tuple[int, ...] | None = None


def tokenize(text: str) -> tuple[bytes, tuple[Token, ...]]:
    """Tokenize ``text``. Offsets are into the exact UTF-8 bytes of ``text``."""
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    raw = text.encode("utf-8")
    tokens: list[Token] = []
    offset = 0
    index = 0
    trie = emoji_trie()
    while index < len(text):
        entry, entry_end = trie.longest_at(text, index)
        if entry is not None:
            _append_emoji(tokens, text, offset, index, entry_end, entry)
            offset += len(text[index:entry_end].encode("utf-8"))
            index = entry_end
            continue
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


def _append_emoji(tokens: list[Token], text: str, offset: int, start: int, end: int, entry: EmojiEntry) -> None:
    piece = text[start:end]
    size = len(piece.encode("utf-8"))
    tokens.append(
        Token(
            piece,
            offset,
            offset + size,
            "emoji",
            entry.name,
            entry.group,
            entry.subgroup,
            entry.codepoints,
        )
    )


def _word_continue(text: str, index: int) -> bool:
    char = text[index]
    if char.isalnum():
        return True
    return char in {"'", "-"} and index + 1 < len(text) and text[index + 1].isalnum()
