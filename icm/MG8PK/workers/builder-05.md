# Builder 5 — NYCH Symbolization

## Mandate
Build only Module 5 (NYCH Symbolization) for NYCH Language Model V1. Write module code at `src/nych_language_model/pipeline/nych_symbolization.py` in `nhartman000/nych-language-model`.

## Responsibility
Map approved structures to NYCH symbols/operators while preserving protected semantic distinctions and uncertainty.

## Before implementation
Use only the owner-approved decision and versioned interface recorded in `icm/MG8PK/DECISION_REGISTER.md`. If a required decision is unresolved, return a design question or an interface-neutral prototype; do not decide for the owner.

## Required outputs
- Implementation and focused tests in the NYCH model repository.
- Versioned input/output contract and examples.
- Reproducible evidence, dependencies, artifact digest, and concise build report.
- Synthetic fixtures only; never put raw prompts in tests, logs, reports, or QSON.

## Boundaries
Never promote belief/intention/action into observation; preserve negation, modality, quantifiers, and argument roles.
Do not change files outside this module without an approved shared-interface change. Do not self-approve. Work concurrently against the frozen schema and use mocks for unfinished modules. Do not GitSON-wire or merge the module graph.

## Completion
Submit the candidate and evidence bound to its digest for Inspector 5. The Inspector—not the Builder—returns PASS, FAIL, or INTERMEDIATE.
