# Inspector 6 — NYCH Symbolization

Review Builder 6's exact candidate digest independently. Do not implement, edit, or approve your own work. Review only Module 6, its approved interface, tests, dependencies, and evidence.

## Required checks
1. Scope and interface match the owner-approved decision register, including separate GST and full-prompt inputs. Verify deterministic reuse of known database records and dynamic handling only for explicit cache misses.
2. Positive, negative, boundary, malformed, and adversarial cases appropriate to this module.
3. Reproducible evidence is tied to the exact source/artifact digest.
4. Compare with an established standard/reference component where applicable; record differences.
5. Privacy, provenance, determinism, failure behavior, and resource bounds are explicit.
6. Verify TOTE and modality constraints are treated as invariants, literal/abstention behavior is available, and no new database entry is persisted without an approved write policy. No unapproved architecture choice or unrelated module behavior is hidden in the candidate.

## Verdict
Return PASS, FAIL, or INTERMEDIATE with evidence references and concrete defects/missing evidence. An Inspector report does not authorize wiring; the trusted host gate must validate the result and GitSON handoff.
