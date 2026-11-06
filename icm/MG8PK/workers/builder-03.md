# Builder 3 — Trace Identity

## Mandate
Build only Module 3 (Trace Identity) for NYCH Language Model V1. Write module code at `src/nych_language_model/pipeline/trace_identity.py` in `nhartman000/nych-language-model`.

## Responsibility
Assign occurrence-level trace identity to one word span at a time and generate the D3 consonant-skeleton suffix. English-only V1 is approved. Accent-fold only the derived suffix (recommended implementation: NFKD plus removal of combining marks); never rewrite source text or offsets. The supplied examples remove a/e/i/o/u, retain y, and collapse repeated adjacent consonants; implement these as provisional examples until remaining D3 choices are frozen.

## Before implementation
Use only the owner-approved decision and versioned interface recorded in `icm/MG8PK/DECISION_REGISTER.md`. If a required decision is unresolved, return a design question or an interface-neutral prototype; do not decide for the owner.

## Required outputs
- Implementation and focused tests in the NYCH model repository.
- Versioned input/output contract and examples.
- Reproducible evidence, dependencies, artifact digest, and concise build report.
- Synthetic fixtures only; never put raw prompts in tests, logs, reports, or QSON.

## Boundaries
Do not infer domains or silently merge repeated occurrences. Runtime domain-to-emoji mapping is deterministic and inventory-validated; no runtime LLM call. If an LLM-assisted mapping draft is requested, emit exactly one inventory emoji plus the base word in the fixed `[emoji:word]` form, with no extra text or modifiers, then validate it in code.
Do not change files outside this module without an approved shared-interface change. Do not self-approve. Work concurrently against the frozen schema and use mocks for unfinished modules. Do not GitSON-wire or merge the module graph.

## Completion
Submit the candidate and evidence bound to its digest for Inspector 3. The Inspector—not the Builder—returns PASS, FAIL, or INTERMEDIATE.
