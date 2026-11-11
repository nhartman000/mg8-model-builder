"""Review one builder's evidence bundle under the approved D12 bar.

Missing evidence is INTERMEDIATE. A defect is FAIL only when every required
element is present and contradicts the contract. PASS is not granted because
a GitSON declaration validator accepts a declaration; this module never calls
that validator. An inspector verdict does not authorize wiring.

The evidence object shape is interpreted plumbing. The required elements are
the D12 bar: contract match, the four case classes, reproducibility, one
exact digest, and a reference comparison where a baseline is named.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

VERDICTS = ("PASS", "FAIL", "INTERMEDIATE")
CASE_CLASSES = ("adversarial", "boundary", "negative", "positive")
PAIRS = {f"B{number}": f"I{number}" for number in range(1, 12)}
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
FORBIDDEN_KEYS = frozenset({"prompt", "raw_prompt", "user_example", "example_prompt"})

# Rules named by the B1 acceptance list in the build spec. A contract that
# names one of these is checked from observations. Any other rule id has no
# evaluator here, so it stays missing evidence rather than a guessed pass.
RULES = {
    "accept_short_utf8": "positive",
    "reject_empty": "negative",
    "reject_malformed_utf8": "negative",
    "accept_65536": "boundary",
    "reject_65537": "boundary",
    "no_normalization": "adversarial",
    "fixture_absent_from_output": "adversarial",
    "overlong_utf8": "adversarial",
}


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj)).hexdigest()


def _sha(value: Any) -> bool:
    return isinstance(value, str) and DIGEST.fullmatch(value) is not None


def _forbidden(obj: Any, path: str, found: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                found.append(path + "." + key)
            _forbidden(value, f"{path}.{key}", found)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            _forbidden(value, f"{path}[{index}]", found)


def _accepted_unchanged(obs: dict, *, exact_length: int | None = None) -> bool:
    length = obs.get("byte_length")
    if obs.get("status") != "ACCEPTED" or obs.get("text_present") is not True:
        return False
    if not isinstance(length, int) or isinstance(length, bool) or length < 1:
        return False
    if exact_length is not None and length != exact_length:
        return False
    if obs.get("text_byte_length") != length:
        return False
    digest = obs.get("raw_sha256")
    return _sha(digest) and digest == obs.get("text_sha256") == obs.get("input_sha256")


def _rejected_without_text(obs: dict, length: int) -> bool:
    return (
        obs.get("status") == "REJECTED"
        and obs.get("text_present") is False
        and obs.get("text_sha256") is None
        and obs.get("byte_length") == length
        and _sha(obs.get("raw_sha256"))
        and obs.get("raw_sha256") == obs.get("input_sha256")
    )


def _rule_passes(rule: str, obs: dict) -> bool:
    if rule == "accept_short_utf8":
        length = obs.get("byte_length")
        return _accepted_unchanged(obs) and isinstance(length, int) and length < 65536
    if rule == "reject_empty":
        return _rejected_without_text(obs, 0)
    if rule == "reject_malformed_utf8":
        length = obs.get("byte_length")
        return _rejected_without_text(obs, length) if isinstance(length, int) and length > 0 else False
    if rule == "accept_65536":
        return _accepted_unchanged(obs, exact_length=65536) and obs.get("truncated") is False
    if rule == "reject_65537":
        return _rejected_without_text(obs, 65537)
    if rule == "no_normalization":
        return (
            _accepted_unchanged(obs)
            and obs.get("rewritten") is False
            and _sha(obs.get("nfc_sha256"))
            and obs.get("nfc_sha256") != obs.get("raw_sha256")
        )
    if rule == "fixture_absent_from_output":
        return (
            obs.get("output_contains_fixture") is False
            and _sha(obs.get("output_sha256"))
            and _sha(obs.get("fixture_sha256"))
            and obs.get("output_sha256") != obs.get("fixture_sha256")
        )
    if rule == "overlong_utf8":
        return _rejected_without_text(obs, obs.get("byte_length")) and obs.get("byte_length") == 2
    return False


def review(candidate_digest: str, contract: dict, bundle: dict) -> dict:
    """Return PASS, FAIL, or INTERMEDIATE for one candidate digest.

    ``candidate_digest`` is the only artifact digest this review names. The
    same bytes produce the same verdict.
    """
    missing: list[str] = []
    defects: list[str] = []
    if not isinstance(contract, dict):
        missing.append("contract")
        contract = {}
    if not isinstance(bundle, dict):
        missing.append("bundle")
        bundle = {}
    forbidden: list[str] = []
    _forbidden(bundle, "$", forbidden)
    if forbidden:
        defects.append("bundle contains a forbidden key")

    subject = bundle.get("subject_module")
    reviewer = bundle.get("reviewer_id")
    if subject not in PAIRS:
        missing.append("subject_module")
    elif contract.get("module_id") != subject:
        if contract.get("module_id") is None:
            missing.append("contract.module_id")
        else:
            defects.append("contract module does not match the subject")
    if reviewer is None:
        missing.append("reviewer_id")
    elif subject in PAIRS and reviewer != PAIRS[subject]:
        defects.append("reviewer is not the paired inspector")
    if reviewer == subject:
        defects.append("builder inspected itself")

    producer_role = bundle.get("producer_role")
    producer_id = bundle.get("producer_id")
    if producer_role is None:
        missing.append("producer_role")
    elif producer_role == "builder" or producer_id == subject:
        defects.append("builder inspected itself")
    elif producer_role != "harness":
        defects.append("producer_role is not the independent harness")
    if not isinstance(producer_id, str) or not producer_id:
        missing.append("producer_id")

    named = bundle.get("candidate_digest")
    if not _sha(candidate_digest) or not _sha(named):
        missing.append("candidate_digest")
    elif candidate_digest != named or named != bundle.get("artifact_bytes_sha256"):
        defects.append("candidate digest does not match the artifact bytes")
    if isinstance(bundle.get("candidate_digests"), list):
        defects.append("bundle names more than one candidate digest")

    pinned = contract.get("source_commit")
    if pinned is not None:
        if bundle.get("observed_commit") != pinned or bundle.get("pinned_commit") != pinned:
            if bundle.get("observed_commit") is None:
                missing.append("observed_commit")
            else:
                defects.append("observed commit is not the pinned source")

    rules = contract.get("rules")
    if not isinstance(rules, dict) or not rules:
        missing.append("contract.rules")
        rules = {}
    cases = bundle.get("cases")
    if not isinstance(cases, list) or not cases:
        missing.append("cases")
        cases = []
    present: set[str] = set()
    seen_rules: set[str] = set()
    comparable: list[dict] = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            defects.append(f"case {index} is not an object")
            continue
        rule = case.get("rule")
        kind = case.get("class")
        observation = case.get("observation")
        if not isinstance(case.get("name"), str) or not case.get("name"):
            missing.append(f"cases[{index}].name")
        if kind not in CASE_CLASSES:
            missing.append(f"cases[{index}].class")
        else:
            present.add(kind)
        if rule not in rules:
            missing.append(f"cases[{index}].rule")
            continue
        if rules[rule] != kind:
            defects.append(f"{rule} is not in its contract case class")
        if rule not in RULES:
            missing.append(f"evaluator for {rule}")
            continue
        if not isinstance(observation, dict):
            missing.append(f"cases[{index}].observation")
            continue
        seen_rules.add(rule)
        comparable.append({"class": kind, "name": case["name"], "observation": observation, "rule": rule})
        if not _rule_passes(rule, observation):
            defects.append(f"{rule} failed")
    for rule in rules:
        if rule not in seen_rules:
            missing.append(f"case for {rule}")
    for kind in CASE_CLASSES:
        if kind not in present:
            missing.append(f"case class {kind}")

    runs = bundle.get("runs")
    if not isinstance(runs, list) or len(runs) != 2:
        missing.append("reproducible second run")
    else:
        first, second = runs
        if first != second or not _sha(first):
            defects.append("two runs do not agree")
        elif comparable and first != _digest(comparable):
            defects.append("run digest does not match the submitted cases")

    if "reference_baseline" not in contract:
        missing.append("reference_baseline")
    elif contract.get("reference_baseline") is None:
        if bundle.get("reference_comparison") is None:
            missing.append("reference_comparison")
        elif bundle.get("reference_comparison") != "not_applicable":
            defects.append("reference comparison invents a baseline")
    else:
        if bundle.get("reference_comparison") != "compared" or "reference_result" not in bundle:
            missing.append("reference_comparison")

    if missing:
        verdict = "INTERMEDIATE"
    elif defects:
        verdict = "FAIL"
    else:
        verdict = "PASS"
    return {
        "authorizes_wiring": False,
        "candidate_digest": named if _sha(named) else None,
        "case_classes": sorted(present),
        "defects": sorted(set(defects)),
        "inspector_id": reviewer if isinstance(reviewer, str) else None,
        "missing_evidence": sorted(set(missing)),
        "module_id": subject if isinstance(subject, str) else None,
        "validator_was_the_inspector": False,
        "verdict": verdict,
    }
