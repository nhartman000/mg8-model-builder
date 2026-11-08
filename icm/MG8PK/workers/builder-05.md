# Builder 5 — GST Context Assembly

## Mandate
Build only Module 5 (GST Context Assembly) for NYCH Language Model V1. Own the request-scoped global `.gst` artifact and its producer-side interface in `nhartman000/nych-language-model`.

## Responsibility
Use the existing TOTE-loops SQLite schema as the loop source, with the approved storage direction to extend that same SQLite database additively. Follow the private draft `docs/GST_TAXONOMY_SCHEMA_PROPOSAL_V1.md`; it is a proposed contract, not an applied migration. Preserve the existing tables and exports until the migration is reviewed. `schema.sql` defines `modality_operators`, `gestalts`, `tote_loops`, `tote_steps`, and `loop_gestalts`; `src/build_db.py` builds `data/tote_loops.sqlite3` and deterministic `data/tote_loops.json`. Once B4 identifies a domain, enrich its hierarchy through Google search for applicable subdomains, sub-subdomains, functions, and techniques, retaining source provenance. Techniques may be extracted from how-to texts; extracted loop candidates require human validation before canonical admission. Query existing records deterministically as context is assembled, then build the `.gst` containing: domain → subdomain → sub-subdomain → function → technique → TOTE loop; loop actor, action, object or tool, and modality; narrative perspective and tense; grammatical/semantic roles; temporal intervals; and explicit relationships. Preserve evidence and unknowns. The GST is delivered to B6 together with, but distinct from, the complete source prompt.
The schema's `tote_loops.domain`, `tote_steps.plain_text`/`nych_text`, and step `operator_id`/`proposition_kind`/`provenance` are the available loop/domain/modality evidence. The current schema has no dedicated action key or separate subdomain/function/technique, actor, or object/tool tables. Keep search-derived hierarchy provenance distinct from existing database fields, and do not pretend missing fields are already stored. TOTE structure and modality operators are invariants, never guessed. If no matching database entry exists, record a cache miss and pass it to B6 for dynamic resolution during the first symbol-selection call. The database is intended to grow toward broad coverage. Human-authored loop submissions may be automatically validated for schema, required actor/action/object-or-tool/modality, valid operators, provenance, proposition-kind consistency, and TOTE transition/exit integrity. How-to-derived candidates remain pending human validation before admission. Do not write new entries until validation, provenance, conflict, and persistence policy are approved. A future web authoring interface should let a person select the domain/subdomain/sub-subdomain/function/technique from the registry, choose modality operators from a dropdown, and enter action text. Human submissions are then automatically checked against schema and NYCH/TOTE invariants; exact verifier rules and schema extension remain open. Never invent missing context or convert uncertain inference into fact.

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
