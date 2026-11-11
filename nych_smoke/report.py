"""Per-stage status for the first smoke run."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from gitson_boundary import SCHEMA_DIGEST, validate_declaration
from gitson_boundary.validator import canonical_json

from nych_preview.domain_switch import scan_interlinear
from nych_smoke.pipeline import artifact_digest, load_english_sample, run_text
from nych_smoke.proper_names import classify_names
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


def _inspector_stage() -> dict:
    """Run I1 against the pinned B1 ingest. The validator is not the inspector."""
    from nych_inspector.b1_harness import build_b1_evidence
    from nych_inspector.review import review

    try:
        evidence = build_b1_evidence()
    except FileNotFoundError as err:
        return {
            "authorizes_wiring": False,
            "missing_evidence": ["pinned B1 source"],
            "note": f"I1 did not review B1 because the pinned source is unavailable: {err}",
            "status": "intermediate",
            "validator_was_the_inspector": False,
            "verdict": "INTERMEDIATE",
        }
    verdict = review(evidence["candidate_digest"], evidence["contract"], evidence["bundle"])
    status = {"PASS": "wired and passing", "FAIL": "wired and failing", "INTERMEDIATE": "intermediate"}[verdict["verdict"]]
    note = (
        f"I1 reviewed the pinned ingest at {evidence['contract']['source_commit']} "
        f"and returned {verdict['verdict']}. "
        "Missing evidence is INTERMEDIATE. This report does not authorize wiring, "
        "and gitson_boundary.validate_declaration was not the inspector."
    )
    return {
        "authorizes_wiring": False,
        "candidate_digest": verdict["candidate_digest"],
        "defects": verdict["defects"],
        "missing_evidence": verdict["missing_evidence"],
        "note": note,
        "pinned_commit": evidence["contract"]["source_commit"],
        "status": status,
        "validator_was_the_inspector": False,
        "verdict": verdict["verdict"],
    }


def stage_report() -> dict:
    sample = load_english_sample()
    text_report = run_text(
        sample["text"].encode("utf-8"),
        request_id="smoke:" + sample["identifier"],
        received_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    open_gestalts = [row for row in text_report["gestalts"] if str(row["status"]).startswith("open:")]
    names = classify_names(sample["text"])
    training = train_sample()
    validator = _validator_check()
    inspector = _inspector_stage()
    domain = scan_interlinear(sample["text"])
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
                "status": "wired and passing",
                "note": "Owner-stated Unicode Emoji 18.0 fully-qualified inventory, including skin-tone sequences as their own rows. Not approved. No NYCH gestalt is assigned.",
            },
            "typo_compendium": {
                "status": "not runnable here",
                "note": (
                    "The streaming builder, the D2 split, the four keyboard maps, and the "
                    "one-sided 95% Clopper-Pearson gate are implemented and covered by synthetic fixtures. "
                    "This run did not read enwiki-20261001, did not verify its official SHA-1, and has no "
                    "owner-chosen smoothing method, so probabilities were not computed. "
                    f"Automatic replacements on this sample: {text_report['typo']['automatic_replacements']}. "
                    "Original token text is unchanged. This is not the real compendium build."
                ),
                "automatic_replacements": text_report["typo"]["automatic_replacements"],
                "probabilities": "refused",
                "smoothing_method": None,
            },
            "proper_names": {
                "status": "provisional",
                "note": "Not approved. Sentence-initial words are checked against the SCOWL size-70 substitute and, when fetched, Spread the Wordlist. Those lists are not Merriam-Webster. An all-caps word of at least two letters is an interpreted acronym and is not gestalted.",
                "interpreted_names": sum(row["verdict"] == "name" for row in names),
                "undecided": sum(row["verdict"] == "undecided" for row in names),
                "not_capitalized": sum(row["verdict"] == "not-capitalized" for row in names),
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
                "status": "provisional",
                "note": (
                    "The parser accepts owner-stated dom><global and dom>N, and it accepts the interpreted "
                    "dom>x=food / x=12 form labeled interpreted. Questions (a) closing-tag placement and count "
                    "direction, (b) automatic reversion, (c) a domain on the global tag, (d) nesting of different "
                    "variables, overlap, and parentheses fail closed. No domain was assigned on this sample."
                ),
                "sample_tag_count": len(domain["tags"]),
                "unresolved": domain["unresolved"],
                "resumes_previous_domain": domain["resumes_previous_domain"],
            },
            "domain_lexicon": {
                "status": "not wired",
                "note": "D4 is approved, and the full domain-decision rule module is still deferred.",
            },
            "gitson_validator": validator,
            "inspector": inspector,
            "b1_ingest": {
                "status": "wired and passing" if text_report["ingest"]["status"] == "ACCEPTED" else "wired and failing",
                "note": "Calls the NYCH repo's B1 implementation before tokenization. Only status and digest metadata are reported; accepted text remains in request memory.",
                "byte_length": text_report["ingest"]["byte_length"],
                "raw_sha256": text_report["ingest"]["raw_sha256"],
                "ingest_version": text_report["ingest"]["ingest_version"],
            },
            "b5_gst": {
                "status": "not runnable here",
                "note": "A read-only bridge calls the NYCH B5 implementation, but this sample has no B4 domain_id/action_key. No domain or action is guessed, so this stage remains skipped.",
            },
            "b6_symbol_call": {
                "status": "not runnable here",
                "note": "A test-only stub verifies separate GST and prompt channels and returns literal spans. No symbol-selection model, prompt template, or temperature is approved, so no LLM call was sent.",
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
