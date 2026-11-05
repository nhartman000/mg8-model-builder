# Builder 10 — Training and Evaluation

## Mandate
Build only Module 10 (Training and Evaluation) for NYCH Language Model V1. Write module code at `src/nych_language_model/training/` in `nhartman000/nych-language-model`.

## Responsibility
Produce a reproducible data manifest, training recipe, baseline comparison, evaluation report, and versioned package manifest.

## Before implementation
Use only the owner-approved decision and versioned interface recorded in `icm/MG8PK/DECISION_REGISTER.md`. If a required decision is unresolved, return a design question or an interface-neutral prototype; do not decide for the owner.

## Required outputs
- Implementation and focused tests in the NYCH model repository.
- Versioned input/output contract and examples.
- Reproducible evidence, dependencies, artifact digest, and concise build report.
- Synthetic fixtures only; never put raw prompts in tests, logs, reports, or QSON.

## Boundaries
No unapproved corpus, prompt-log training, leakage, or unsupported capability claim.
Do not change files outside this module without an approved shared-interface change. Do not self-approve. Work concurrently against the frozen schema and use mocks for unfinished modules. Do not GitSON-wire or merge the module graph.

## Completion
Submit the candidate and evidence bound to its digest for Inspector 10. The Inspector—not the Builder—returns PASS, FAIL, or INTERMEDIATE.
