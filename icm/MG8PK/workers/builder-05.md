# Builder 5 — GST Context Assembly

## Mandate
Build only Module 5 (GST Context Assembly) for NYCH Language Model V1. Own the request-scoped global `.gst` artifact and its producer-side interface in `nhartman000/nych-language-model`.

## Responsibility
Check the versioned action/domain database deterministically as domain/action information becomes available, then assemble supported context and matches into the `.gst`: domain → subdomain → sub-subdomain → function → technique → TOTE loop; loop actor, action, object or tool, and modality; narrative perspective and tense; grammatical/semantic roles; temporal intervals; and explicit relationships. Preserve evidence and unknowns. The GST is delivered to B6 together with, but distinct from, the complete source prompt.
TOTE structure and modality operators are invariants, never guessed. If no matching database entry exists, record a cache miss and pass it to B6 for dynamic resolution during the first symbol-selection call. The database is intended to grow toward broad coverage; do not write new entries until validation, provenance, conflict, and persistence policy are approved. Schema, endpoint, and evidence model remain open. Never invent missing context or convert uncertain inference into fact.

## Before implementation
Use only the owner-approved decision and versioned interface recorded in `icm/MG8PK/DECISION_REGISTER.md` and `docs/NYCH_GST_CONTEXT_FLOW_V1.md`. Raw prompt text is request-memory-only and must not be persisted or written to QSON.

## Required outputs
- Module implementation or interface-neutral prototype and focused synthetic fixtures.
- Versioned GST input/output contract, examples, and explicit unknown/evidence representation.
- Reproducible evidence, dependencies, artifact digest, and concise build report.
- No real user prompts in tests, logs, reports, or QSON.

## Boundaries
Do not perform B4 domain assignment or B6 emoji/gestalt selection. Use deterministic lookup for existing entries; do not make an LLM call or resolve cache misses yourself. Do not alter the full prompt; B6 receives GST and full prompt as separate inputs. Do not change files outside this module without an approved shared-interface change. Do not self-approve, GitSON-wire, or merge the module graph.

## Completion
Submit the candidate and evidence bound to its digest for Inspector 5. The Inspector—not the Builder—returns PASS, FAIL, or INTERMEDIATE.
