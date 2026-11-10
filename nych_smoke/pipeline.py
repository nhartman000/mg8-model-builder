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
from nych_smoke.upstream import ingest_bytes

SAMPLE_PATH = Path(__file__).resolve().parent / "fixtures" / "common_corpus_english_sample.json"


def load_english_sample(path: Path = SAMPLE_PATH) -> dict:
    sample = json.loads(path.read_text(encoding="utf-8"))
    if sample.get("language") != "English":
        raise ValueError("D11 selects English with the dataset language field")
    if not sample.get("license") or not sample.get("text"):
        raise ValueError("sample must keep its license and text")
    return sample


def run_text(raw: bytes, *, request_id: str, received_at: str) -> dict:
    """Run B1 before B2 and B3 using the authoritative NYCH B1 implementation.

    The raw request is never included in the returned report. Accepted text is
    used in memory only, and B1's digest is checked against the original bytes.
    """
    if not isinstance(raw, bytes):
        raise TypeError("run_text requires the exact request bytes")
    ingress = ingest_bytes(raw, request_id=request_id, received_at=received_at)
    if ingress.status != "ACCEPTED" or ingress.text is None:
        raise ValueError(f"B1 rejected request: {ingress.error_code}")
    if ingress.raw_sha256 != hashlib.sha256(raw).hexdigest():
        raise RuntimeError("B1 digest does not match original request bytes")
    if ingress.text.encode("utf-8") != raw:
        raise RuntimeError("B1 changed accepted request bytes")
    token_bytes, tokens = tokenize(ingress.text)
    if token_bytes != raw:
        raise RuntimeError("B2 did not preserve the B1-accepted bytes")
    raw = token_bytes
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
        "ingest": {
            "status": ingress.status,
            "request_id": ingress.request_id,
            "encoding": ingress.encoding,
            "byte_length": ingress.byte_length,
            "raw_sha256": "sha256:" + ingress.raw_sha256,
            "ingest_version": ingress.ingest_version,
        },
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
