# Inspector 3 — Trace Identity

Review Builder 3's exact candidate digest independently. Do not implement, edit, or approve your own work. Review only Module 3, its approved interface, tests, dependencies, and evidence.

## Required checks
1. Scope and interface match the owner-approved decision register.
2. Positive, negative, boundary, malformed, and adversarial cases appropriate to this module.
3. Reproducible evidence is tied to the exact source/artifact digest.
4. Compare with an established standard/reference component where applicable; record differences.
5. Privacy, provenance, determinism, failure behavior, and resource bounds are explicit.
6. No unapproved architecture choice or unrelated module behavior is hidden in the candidate.

## D3-specific checks\n- Confirm source text/byte spans are unchanged while only the derived suffix is accent-folded.\n- Include accented English names/loanwords (for example, “café” and “naïve”) and verify canonical-equivalent spellings yield the same suffix.\n- Check the approved a/e/i/o/u removal, y retention, repeated-consonant collapse, empty/unsupported inputs, and exact emoji-inventory membership.\n- Confirm the candidate does not invent SHA inputs, occurrence identity, separators, or domain binding while those decisions remain open.\n\n## Verdict
Return PASS, FAIL, or INTERMEDIATE with evidence references and concrete defects/missing evidence. An Inspector report does not authorize wiring; the trusted host gate must validate the result and GitSON handoff.
