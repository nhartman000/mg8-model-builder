"""Measure the pinned B1 ingest. This harness is not Inspector I1 and not Builder B1.

Interpreted plumbing: the evidence object shape, the metadata-only output
file, and the producer id below. The acceptance rules and the 65,536-byte
ceiling come from the build spec. No fixture text is written into the bundle.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from nych_inspector.review import canonical_json
from nych_smoke.trace_id import input_digest
from nych_smoke.upstream import ingest_bytes, nych_model_src

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "icm" / "upstream-pins.json"
PRODUCER_ID = "nych_inspector.b1_harness"
RECEIVED_AT = "2026-11-10T00:00:00Z"
REQUEST_ID = "b1-inspector-harness"

# Synthetic fixtures, not prompts. They stay in this process and out of the bundle.
SHORT = "nych-b1-short".encode()
OVERLONG = b"\xc0\x80"
MALFORMED = b"\xff"
EMPTY = b""
AT_LIMIT = b"x" * 65536
OVER_LIMIT = b"x" * 65537
UNNORMALIZED = "e\u0301".encode()


def b1_contract() -> dict:
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    commit = pins["sources"][0]["commit"]
    return {
        "module_id": "B1",
        "reference_baseline": None,
        "rules": {
            "accept_short_utf8": "positive",
            "reject_empty": "negative",
            "reject_malformed_utf8": "negative",
            "accept_65536": "boundary",
            "reject_65537": "boundary",
            "no_normalization": "adversarial",
            "fixture_absent_from_output": "adversarial",
            "overlong_utf8": "adversarial",
        },
        "source_commit": commit,
        "source_repository": pins["sources"][0]["repository"],
    }


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _measure(raw: bytes) -> dict:
    result = ingest_bytes(raw, request_id=REQUEST_ID, received_at=RECEIVED_AT)
    text_sha = None if result.text is None else _sha256(result.text.encode("utf-8"))
    digest = "sha256:" + result.raw_sha256
    expected = "sha256:" + input_digest(raw).hex()
    return {
        "byte_length": result.byte_length,
        "input_sha256": expected,
        "output_contains_fixture": False,
        "raw_sha256": digest,
        "rewritten": result.text is not None and result.text.encode("utf-8") != raw,
        "status": result.status,
        "text_byte_length": None if result.text is None else len(result.text.encode("utf-8")),
        "text_present": result.text is not None,
        "text_sha256": text_sha,
        "truncated": result.text is not None and len(result.text.encode("utf-8")) != len(raw),
    }


def _cases(output_sha: str, fixture_sha: str) -> list[dict]:
    short = _measure(SHORT)
    empty = _measure(EMPTY)
    malformed = _measure(MALFORMED)
    at_limit = _measure(AT_LIMIT)
    over_limit = _measure(OVER_LIMIT)
    normalized = _measure(UNNORMALIZED)
    overlong = _measure(OVERLONG)
    normalized["nfc_sha256"] = _sha256(unicodedata.normalize("NFC", UNNORMALIZED.decode("utf-8")).encode("utf-8"))
    absent = {
        "fixture_sha256": fixture_sha,
        "output_contains_fixture": False,
        "output_sha256": output_sha,
    }
    return [
        {"class": "positive", "name": "short-utf8", "observation": short, "rule": "accept_short_utf8"},
        {"class": "negative", "name": "empty", "observation": empty, "rule": "reject_empty"},
        {"class": "negative", "name": "malformed-utf8", "observation": malformed, "rule": "reject_malformed_utf8"},
        {"class": "boundary", "name": "exactly-65536", "observation": at_limit, "rule": "accept_65536"},
        {"class": "boundary", "name": "65537", "observation": over_limit, "rule": "reject_65537"},
        {"class": "adversarial", "name": "not-normalized", "observation": normalized, "rule": "no_normalization"},
        {"class": "adversarial", "name": "overlong-utf8", "observation": overlong, "rule": "overlong_utf8"},
        {
            "class": "adversarial",
            "name": "fixture-absent",
            "observation": absent,
            "rule": "fixture_absent_from_output",
        },
    ]


def _run_digest(cases: list[dict]) -> str:
    body = [
        {"class": case["class"], "name": case["name"], "observation": case["observation"], "rule": case["rule"]}
        for case in cases
    ]
    return "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()


def build_b1_evidence(output_path: Path | None = None) -> dict:
    """Run the section-1 cases twice against the pinned ingest module.

    The returned bundle stores lengths and digests only. ``output_path``, when
    given, receives that same metadata and is checked for fixture bytes.
    """
    src = nych_model_src()
    ingest_path = src / "nych_language_model" / "pipeline" / "ingest.py"
    artifact = ingest_path.read_bytes()
    artifact_digest = _sha256(artifact)
    repo = src.parent
    observed = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    contract = b1_contract()
    fixture_bytes = SHORT + b"\n" + UNNORMALIZED
    metadata = {
        "artifact_bytes_sha256": artifact_digest,
        "byte_lengths": [len(SHORT), 0, len(MALFORMED), 65536, 65537, len(UNNORMALIZED), len(OVERLONG)],
        "pinned_commit": contract["source_commit"],
    }
    rendered = canonical_json(metadata)
    contains = fixture_bytes in rendered or SHORT in rendered or UNNORMALIZED in rendered
    if output_path is not None:
        output_path.write_bytes(rendered)
        contains = contains or fixture_bytes in output_path.read_bytes()
    output_sha = _sha256(rendered)
    fixture_sha = _sha256(fixture_bytes)
    first = _cases(output_sha, fixture_sha)
    second = _cases(output_sha, fixture_sha)
    first[-1]["observation"]["output_contains_fixture"] = contains
    second[-1]["observation"]["output_contains_fixture"] = contains
    bundle = {
        "artifact_bytes_sha256": artifact_digest,
        "candidate_digest": artifact_digest,
        "cases": first,
        "observed_commit": observed,
        "pinned_commit": contract["source_commit"],
        "producer_id": PRODUCER_ID,
        "producer_role": "harness",
        "reference_comparison": "not_applicable",
        "reviewer_id": "I1",
        "runs": [_run_digest(first), _run_digest(second)],
        "subject_module": "B1",
    }
    return {"bundle": bundle, "candidate_digest": artifact_digest, "contract": contract, "output_bytes": rendered}
