# Builder 2 — Tokenization

## Mandate
Build only Module 2 (Tokenization) for NYCH Language Model V1. Write module code at `src/nych_language_model/pipeline/tokenization.py` in `nhartman000/nych-language-model`.

## Responsibility
For English V1, define a versioned tokenizer interface and deterministic token IDs, special tokens, byte/character spans, and decode behavior.

## Before implementation
Use only the owner-approved decision and versioned interface recorded in `icm/MG8PK/DECISION_REGISTER.md`. If a required decision is unresolved, return a design question or an interface-neutral prototype; do not decide for the owner.

## Required outputs
- Implementation and focused tests in the NYCH model repository.
- Versioned input/output contract and examples.
- Reproducible evidence, dependencies, artifact digest, and concise build report.
- Synthetic fixtures only; never put raw prompts in tests, logs, reports, or QSON.

## Boundaries
Preserve original source bytes/text and source offsets. Do not apply D3 accent folding in the tokenizer; that transform is confined to the derived trace suffix. Do not infer semantics.
Do not change files outside this module without an approved shared-interface change. Do not self-approve. Work concurrently against the frozen schema and use mocks for unfinished modules. Do not GitSON-wire or merge the module graph.

## Completion
Submit the candidate and evidence bound to its digest for Inspector 2. The Inspector—not the Builder—returns PASS, FAIL, or INTERMEDIATE.
