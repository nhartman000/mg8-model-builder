# Inspector 5 — GST Context Assembly

Review Builder 5's exact candidate digest independently. Do not implement, edit, or approve your own work. Review only Module 5, its approved interface, tests, dependencies, and evidence.

## Required checks
1. Scope and interface match the owner-approved decision register; distinguish approved architecture from still-open schema and extraction decisions.
2. GST preserves the approved hierarchy and invariant TOTE/modality structure, narrative perspective/tense, semantic roles, intervals, relationships, and explicit unknowns. Verify the candidate uses the existing TOTE schema accurately: `tote_loops.domain`, `tote_steps.plain_text`/`nych_text`, `operator_id`, `proposition_kind`, and `provenance`; it must not claim absent action keys or hierarchy/entity columns. Existing matching records must be retrieved deterministically and cache misses passed to B6.
3. Verify evidence traceability and that unsupported information is not invented or promoted from uncertain inference to fact.
4. Verify the prompt and GST remain request-scoped; no raw prompt appears in persisted artifacts, logs, reports, or QSON.
5. Reproducible evidence is tied to the exact source/artifact digest; include positive, negative, boundary, malformed, and adversarial cases.
6. Compare with an established reference where applicable and report differences; flag every unresolved contract dependency.
7. No B4 domain resolution, B6 symbol selection, unapproved LLM call, or unapproved database write is included. Report the absent normalized action key and missing hierarchy/actor/object tables as interface gaps.

## Verdict
Return PASS, FAIL, or INTERMEDIATE with evidence references and concrete defects/missing evidence. An Inspector report does not authorize wiring; the trusted host gate must validate the result and GitSON handoff.
