"""Smoke path: exact bytes, B2 spans, B3 trace IDs, then the D15 abbreviation helper.

Domain-switch tags stay unwired. Their placement, reversion, global naming,
and nesting are still open, and the dom>x=food reading is an interpretation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from nych_preview.gestalt_abbreviation import COMPOUNDS, GestaltAbbrevError, abbreviate_owner_compound, abbreviate_word
from nych_smoke.proper_names import classify_token_rows
from nych_smoke.tokenize import Token, tokenize
from nych_smoke.trace_id import consonant_suffix, input_digest, trace_id

SAMPLE_PATH = Path(__file__).resolve().parent / "fixtures" / "common_corpus_english_sample.json"


def load_english_sample(path: Path = SAMPLE_PATH) -> dict:
    sample = json.loads(path.read_text(encoding="utf-8"))
    if sample.get("language") != "English":
        raise ValueError("D11 selects English with the dataset language field")
    if not sample.get("license") or not sample.get("text"):
        raise ValueError("sample must keep its license and text")
    return sample


def run_text(text: str) -> dict:
    raw, tokens = tokenize(text)
    digest = input_digest(raw)
    traced = []
    for index, token in enumerate(tokens):
        suffix = consonant_suffix(token.text if token.kind == "word" else "")
        traced.append(
            {
                "index": index,
                "kind": token.kind,
                "text": token.text,
                "start": token.start,
                "end": token.end,
                "source": raw[token.start:token.end].decode("utf-8"),
                "suffix": suffix,
                "trace_id": trace_id(digest, index, token.start, token.end, suffix),
            }
        )
    return {
        "byte_length": len(raw),
        "input_sha256": "sha256:" + digest.hex(),
        "tokens": traced,
        "gestalts": _gestalts(tokens, _acronym_indexes(tokens)),
    }


def _acronym_indexes(tokens: tuple[Token, ...]) -> set[int]:
    return {row["token_index"] for row in classify_token_rows(tokens) if row["verdict"] == "acronym"}


def _gestalts(tokens: tuple[Token, ...], acronyms: set[int]) -> list[dict]:
    words = [(index, token.text) for index, token in enumerate(tokens) if token.kind == "word"]
    rows: list[dict] = []
    position = 0
    while position < len(words):
        index, word = words[position]
        if index in acronyms:
            rows.append(
                {
                    "token_indexes": [index],
                    "surface": [word],
                    "abbrev": None,
                    "status": "acronym-excluded",
                }
            )
            position += 1
            continue
        if position + 1 < len(words) and words[position + 1][0] not in acronyms:
            pair = [words[position][1], words[position + 1][1]]
            if tuple(word.lower() for word in pair) in COMPOUNDS:
                try:
                    abbrev = abbreviate_owner_compound(pair, contains_proper_name=pair[0][:1].isupper())
                    status = "owner-listed-compound"
                except GestaltAbbrevError as err:
                    abbrev = None
                    status = f"open: {err}"
                rows.append(
                    {
                        "token_indexes": [words[position][0], words[position + 1][0]],
                        "surface": pair,
                        "abbrev": abbrev,
                        "status": status,
                    }
                )
                position += 2
                continue
        index, word = words[position]
        try:
            abbrev = abbreviate_word(word)
            status = "abbreviated"
        except GestaltAbbrevError as err:
            abbrev = None
            status = f"open: {err}"
        rows.append({"token_indexes": [index], "surface": [word], "abbrev": abbrev, "status": status})
        position += 1
    return rows


def artifact_digest(report: dict) -> str:
    body = json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()
