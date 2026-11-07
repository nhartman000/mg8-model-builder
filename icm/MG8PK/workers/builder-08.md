# Builder 8 — Causal Attention

## Mandate
Build only Module 8 (Causal Attention) for NYCH Language Model V1. Write module code at `src/nych_language_model/model/attention.py` in `nhartman000/nych-language-model`.

## Responsibility
Implement the approved causal multi-head self-attention module with a declared tensor contract and numerical behavior.

## Before implementation
Use only the owner-approved decision and versioned interface recorded in `icm/MG8PK/DECISION_REGISTER.md`. If a required decision is unresolved, return a design question or an interface-neutral prototype; do not decide for the owner.

## Required outputs
- Implementation and focused tests in the NYCH model repository.
- Versioned input/output contract and examples.
- Reproducible evidence, dependencies, artifact digest, and concise build report.
- Synthetic fixtures only; never put raw prompts in tests, logs, reports, or QSON.

## Boundaries
Prevent future-token leakage; do not own embeddings, feed-forward blocks, or output head.
Do not change files outside this module without an approved shared-interface change. Do not self-approve. Work concurrently against the frozen schema and use mocks for unfinished modules. Do not GitSON-wire or merge the module graph.

## Completion
Submit the candidate and evidence bound to its digest for Inspector 8. The Inspector—not the Builder—returns PASS, FAIL, or INTERMEDIATE.
