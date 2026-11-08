# Inspector 5 — GST Context Assembly

Review Builder 5's exact candidate digest independently. Do not implement, edit, or approve your own work. Review only Module 5, its approved interface, tests, dependencies, and evidence.

## Required checks
1. Scope and interface match the owner-approved decision register; distinguish approved architecture from still-open schema and extraction decisions.
2. GST preserves the approved hierarchy and invariant TOTE/modality structure, narrative perspective/tense, semantic roles, intervals, relationships, and explicit unknowns. Verify the candidate uses the existing TOTE schema accurately: `tote_loops.domain`, `tote_steps.plain_text`/`nych_text`, `operator_id`, `proposition_kind`, and `provenance`; verify action keys and hierarchy/actor/object/tool structures against TOTE migration 002 / SQLite v2 (`PRAGMA user_version=2`) as integrated on T.O.T.E-loops main; do not assume pre-migration absence, and do not claim an existing database has been migrated (deferred). Existing matching records must be retrieved deterministically and cache misses passed to B6. The trusted lookup path must recompute `NYCH-TOTE-LOOP-DIGEST-V1` for every hit, require the latest validation PASS and required human review to match both digest and version, and reject `admission_status` as sufficient proof. Review golden fixtures for row-order invariance and semantic-field sensitivity. Verify search-derived hierarchy candidates retain source provenance, and how-to-derived loop candidates are not canonically admitted before human validation. For future human-authored submissions, verify automatic checks cover schema integrity, required actor/action/object-or-tool/modality, approved modality operators, proposition/provenance consistency, and TOTE transition/exit integrity.
3. Verify evidence traceability and that unsupported information is not invented or promoted from uncertain inference to fact.
4. Verify the prompt and GST remain request-scoped; no raw prompt appears in persisted artifacts, logs, reports, or QSON.
5. Reproducible evidence is tied to the exact source/artifact digest; include positive, negative, boundary, malformed, and adversarial cases.
6. Compare with an established reference where applicable and report differences; flag every unresolved contract dependency.
7. No B4 domain resolution, B6 symbol selection, unapproved LLM call, or unapproved database write is included. Earlier wording about an absent normalized action key and missing hierarchy/actor/object tables is superseded by migration 002 (historical). Report remaining gaps: existing-database application and TOTE tests deferred, B4→B5 interface, and the write/admission endpoint; do not claim the future authoring interface or verifier is implemented.

## Verdict
Return PASS, FAIL, or INTERMEDIATE with evidence references and concrete defects/missing evidence. An Inspector report does not authorize wiring; the trusted host gate must validate the result and GitSON handoff.
