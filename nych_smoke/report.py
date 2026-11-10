"""Per-stage status for the first smoke run."""
from __future__ import annotations

import json

from gitson_boundary import SCHEMA_DIGEST, validate_declaration
from gitson_boundary.validator import canonical_json

from nych_smoke.pipeline import artifact_digest, load_english_sample, run_text
from nych_smoke.tiny_train import train_sample


def _validator_check() -> dict:
    document = {
        "schema": "mg8.gitson-boundary-declaration.v1",
        "declaration_id": "smoke-B2-to-B3",
        "source": {"module_id": "B2", "interface_version": "smoke"},
        "target": {"module_id": "B3", "interface_version": "smoke"},
        "artifact_digests": {
            "source": "sha256:" + "ab" * 32,
            "target": "sha256:" + "cd" * 32,
        },
        "upstream_evidence": [
            {
                "inspector_id": "I2",
                "module_id": "B2",
                "verdict": "PASS",
                "evidence_digest": "sha256:" + "ef" * 32,
                "contract_match": True,
                "case_classes": ["adversarial", "boundary", "negative", "positive"],
                "reproducible": True,
                "exact_digest": True,
                "reference_comparison": "compared",
            }
        ],
        "trusted_host_validation": {
            "host_id": "smoke-host",
            "result": "PASS",
            "record_digest": "sha256:" + "11" * 32,
        },
    }
    result = validate_declaration(canonical_json(document))
    return {
        "status": "wired and passing" if result["verdict"] == "PASS" else "wired and failing",
        "schema_digest": SCHEMA_DIGEST,
        "validator_verdict": result["verdict"],
        "note": "This checks the validator on a structural fixture. It is not an inspector PASS for the smoke artifacts.",
    }


def stage_report() -> dict:
    sample = load_english_sample()
    text_report = run_text(sample["text"])
    open_gestalts = [row for row in text_report["gestalts"] if str(row["status"]).startswith("open:")]
    training = train_sample()
    validator = _validator_check()
    return {
        "sample_identifier": sample["identifier"],
        "sample_license": sample["license"],
        "input_sha256": text_report["input_sha256"],
        "artifact_sha256": artifact_digest(text_report),
        "token_count": len(text_report["tokens"]),
        "open_gestalt_count": len(open_gestalts),
        "stages": {
            "english_sample": {
                "status": "wired and passing",
                "note": "One English row selected by the dataset language field. Not the full corpus.",
            },
            "tokenize_spans": {
                "status": "wired and passing",
                "note": "Whitespace, punctuation, internal apostrophes and hyphens, and exact UTF-8 offsets.",
            },
            "emoji_inventory": {
                "status": "not runnable here",
                "note": "The versioned canonical emoji inventory is not in this environment.",
            },
            "typo_compendium": {
                "status": "not runnable here",
                "note": "Needs the enwiki-20261001 dump, the n-gram compendium, and the 99% precision gate.",
            },
            "wikidata_names": {
                "status": "not runnable here",
                "note": "Needs a dated Wikidata dump. The technical lexicon source is still pending.",
            },
            "trace_id": {
                "status": "wired and passing",
                "note": "D3 hash and consonant suffix. The suffix is not the D15 gestalt abbreviation.",
            },
            "gestalt_abbreviation": {
                "status": "wired and passing",
                "note": f"{len(open_gestalts)} token(s) stayed open, including hyphenated words. Unlisted pairs were not compounded.",
            },
            "domain_switch": {
                "status": "not wired",
                "note": "dom>x=food / x=12 remains an interpretation. Placement, reversion, global naming, and nesting are open.",
            },
            "domain_lexicon": {
                "status": "not wired",
                "note": "D4 is approved, and the full domain-decision rule module is still deferred.",
            },
            "gitson_validator": validator,
            "inspector": {
                "status": "not runnable here",
                "note": "No separate inspector ran. D12 says missing evidence is INTERMEDIATE.",
            },
            "b1_ingest": {
                "status": "not runnable here",
                "note": "B1 is not modeled in the decision console. The smoke hashed the exact input bytes for the D3 payload only.",
            },
            "b5_gst": {
                "status": "not runnable here",
                "note": "The GST module is in nhartman000/nych-language-model, which is not checked out here.",
            },
            "b6_symbol_call": {
                "status": "not runnable here",
                "note": "Needs the approved emoji endpoint and a symbol-selection call. No prompt was sent.",
            },
            "training": {
                "status": "wired and passing" if training["losses"] and all(loss == loss for loss in training["losses"]) else "wired and failing",
                "note": "Three Adam steps on CPU for this one document. A V100 full-corpus run did not happen.",
                "detail": training,
            },
        },
    }


def main() -> None:
    print(json.dumps(stage_report(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
