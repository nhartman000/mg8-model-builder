import hashlib
import tempfile
import unittest
from pathlib import Path

from gitson_boundary import validate_declaration
from gitson_boundary.validator import canonical_json as declaration_json
from nych_inspector.b1_harness import SHORT, UNNORMALIZED, build_b1_evidence
from nych_inspector.review import canonical_json, review

DIGEST = "sha256:" + "ab" * 32
OTHER = "sha256:" + "cd" * 32
EMPTY = "sha256:" + "11" * 32


def _observation(status, length, digest=DIGEST, **extra):
    accepted = status == "ACCEPTED"
    row = {
        "byte_length": length,
        "input_sha256": digest,
        "raw_sha256": digest,
        "status": status,
        "text_byte_length": length if accepted else None,
        "text_present": accepted,
        "text_sha256": digest if accepted else None,
    }
    row.update(extra)
    return row


def _cases():
    return [
        {"class": "positive", "name": "short-utf8", "rule": "accept_short_utf8", "observation": _observation("ACCEPTED", 4)},
        {"class": "negative", "name": "empty", "rule": "reject_empty", "observation": _observation("REJECTED", 0, EMPTY)},
        {"class": "negative", "name": "malformed-utf8", "rule": "reject_malformed_utf8", "observation": _observation("REJECTED", 1)},
        {
            "class": "boundary",
            "name": "exactly-65536",
            "rule": "accept_65536",
            "observation": _observation("ACCEPTED", 65536, truncated=False),
        },
        {"class": "boundary", "name": "65537", "rule": "reject_65537", "observation": _observation("REJECTED", 65537)},
        {
            "class": "adversarial",
            "name": "not-normalized",
            "rule": "no_normalization",
            "observation": _observation("ACCEPTED", 2, rewritten=False, nfc_sha256=OTHER),
        },
        {
            "class": "adversarial",
            "name": "overlong-utf8",
            "rule": "overlong_utf8",
            "observation": _observation("REJECTED", 2),
        },
        {
            "class": "adversarial",
            "name": "fixture-absent",
            "rule": "fixture_absent_from_output",
            "observation": {
                "fixture_sha256": DIGEST,
                "output_contains_fixture": False,
                "output_sha256": OTHER,
            },
        },
    ]


def _contract():
    return {
        "module_id": "B1",
        "reference_baseline": None,
        "rules": {
            "accept_65536": "boundary",
            "accept_short_utf8": "positive",
            "fixture_absent_from_output": "adversarial",
            "no_normalization": "adversarial",
            "overlong_utf8": "adversarial",
            "reject_65537": "boundary",
            "reject_empty": "negative",
            "reject_malformed_utf8": "negative",
        },
    }


def _digest(cases):
    body = [
        {"class": case["class"], "name": case["name"], "observation": case["observation"], "rule": case["rule"]}
        for case in cases
    ]
    return "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()


def _bundle(cases=None):
    cases = _cases() if cases is None else cases
    digest = _digest(cases)
    return {
        "artifact_bytes_sha256": DIGEST,
        "candidate_digest": DIGEST,
        "cases": cases,
        "producer_id": "nych_inspector.b1_harness",
        "producer_role": "harness",
        "reference_comparison": "not_applicable",
        "reviewer_id": "I1",
        "runs": [digest, digest],
        "subject_module": "B1",
    }


def _declaration(module="B2"):
    evidence = "sha256:" + "33" * 32
    return {
        "schema": "mg8.gitson-boundary-declaration.v1",
        "declaration_id": "B1-to-B2",
        "source": {"module_id": "B1", "interface_version": "1"},
        "target": {"module_id": "B2", "interface_version": "1"},
        "artifact_digests": {"source": "sha256:" + "11" * 32, "target": "sha256:" + "22" * 32},
        "upstream_evidence": [
            {
                "inspector_id": "I" + module[1:],
                "module_id": module,
                "verdict": "PASS",
                "evidence_digest": evidence,
                "contract_match": True,
                "case_classes": ["adversarial", "boundary", "negative", "positive"],
                "reproducible": True,
                "exact_digest": True,
                "reference_comparison": "compared",
            }
        ],
        "trusted_host_validation": {
            "host_id": "mg8-trusted-host",
            "result": "PASS",
            "record_digest": "sha256:" + "44" * 32,
        },
    }


class InspectorReview(unittest.TestCase):
    def test_incomplete_bundle_is_intermediate_and_not_pass(self):
        bundle = _bundle()
        del bundle["runs"]
        bundle["validator_verdict"] = "PASS"
        result = review(DIGEST, _contract(), bundle)
        self.assertEqual(result["verdict"], "INTERMEDIATE")
        self.assertNotEqual(result["verdict"], "PASS")
        self.assertIn("reproducible second run", result["missing_evidence"])
        self.assertFalse(result["validator_was_the_inspector"])
        self.assertFalse(result["authorizes_wiring"])

    def test_complete_bundle_names_one_digest_and_four_classes(self):
        result = review(DIGEST, _contract(), _bundle())
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["candidate_digest"], DIGEST)
        self.assertEqual(result["case_classes"], ["adversarial", "boundary", "negative", "positive"])
        self.assertEqual(result["missing_evidence"], [])
        again = review(DIGEST, _contract(), _bundle())
        self.assertEqual(again, result)

    def test_failed_case_and_self_inspection_do_not_pass(self):
        cases = _cases()
        cases[0]["observation"]["status"] = "REJECTED"
        failed = review(DIGEST, _contract(), _bundle(cases))
        self.assertEqual(failed["verdict"], "FAIL")
        self.assertIn("accept_short_utf8 failed", failed["defects"])
        bundle = _bundle()
        bundle["producer_role"] = "builder"
        self.assertEqual(review(DIGEST, _contract(), bundle)["verdict"], "FAIL")
        bundle = _bundle()
        bundle["candidate_digests"] = [DIGEST, OTHER]
        self.assertNotEqual(review(DIGEST, _contract(), bundle)["verdict"], "PASS")

    def test_validator_rejects_evidence_that_omits_the_source_module(self):
        omitted = validate_declaration(declaration_json(_declaration("B2")))
        self.assertEqual(omitted["verdict"], "FAIL")
        self.assertTrue(any("does not include source module B1" in reason for reason in omitted["reasons"]))
        accepted = validate_declaration(declaration_json(_declaration("B1")))
        self.assertEqual(accepted["verdict"], "PASS")
        incomplete = _bundle()
        del incomplete["cases"]
        incomplete["declaration_validator_verdict"] = accepted["verdict"]
        self.assertEqual(review(DIGEST, _contract(), incomplete)["verdict"], "INTERMEDIATE")

    def test_pinned_b1_review_and_output_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "b1-metadata.json"
            evidence = build_b1_evidence(output)
            self.assertNotIn(SHORT, evidence["output_bytes"])
            self.assertNotIn(UNNORMALIZED, output.read_bytes())
            result = review(evidence["candidate_digest"], evidence["contract"], evidence["bundle"])
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["missing_evidence"], [])
        self.assertEqual(result["defects"], [])
        self.assertEqual(result["inspector_id"], "I1")
        self.assertEqual(result["module_id"], "B1")
        self.assertEqual(result["candidate_digest"], evidence["candidate_digest"])
        self.assertFalse(result["authorizes_wiring"])
        self.assertEqual(review(evidence["candidate_digest"], evidence["contract"], evidence["bundle"]), result)


if __name__ == "__main__":
    unittest.main()
