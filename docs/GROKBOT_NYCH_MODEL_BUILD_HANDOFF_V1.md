# NYCH Language Model V1 — Grokbot Build Handoff and Voltron Builder Plan

**Owner:** Nick Hartman  
**Prepared:** 2026-11-08  
**Audience:** Grokbot or another coding agent taking over implementation  
**Companion source:** uploaded Gptbuilder.md (compiled 2026-11-08)

## 1. Mission and authority

Build the NYCH Language Model V1 proof of concept through the MG8 Model Builder system. The deliverable is a small, inspectable NYCH processing pipeline plus a tiny next-token model, built as bounded modules with independent review, deterministic wiring, provenance, and reproducible evaluation.

Nick owns the semantic and product decisions. Builders may implement approved choices and recommend alternatives, but must not silently resolve an owner decision marked pending. Grokbot should conserve Nick’s conceptual time: group unresolved choices in a compact decision interface, show recommended defaults and consequences, accept one approval for all recommendations plus exceptions, and let independent builders work in parallel once their contracts are frozen.

The project’s target rigor is high-assurance engineering. Do not claim DARPA certification or equivalent external qualification. Produce evidence that an independent reviewer can reproduce.

## 2. Repository map and authoritative state

Keep repository responsibilities separate:

| Repository | Responsibility | Current state |
|---|---|---|
| [mg8-model-builder](https://github.com/nhartman000/mg8-model-builder) | Decision registry, builder/inspector cards, orchestration plan, decision interface | Private. README and decision register are present. Builder cards 01–11 (`icm/MG8PK/workers/`) and Inspector cards 01–11 (`icm/MG8PK/inspectors/`) are committed on main (verified at 2284ac9). The earlier “not found” finding is historical. Decision Console V1 (offline) lives under `console/`. |
| [nych-language-model](https://github.com/nhartman000/nych-language-model) | NYCH V1 implementation, module contracts, schemas, reports, tests | Private. B5 V2 is integrated and passed independent review. B1 remains pending independent review; B3 bounded module passed; B2/B4 integration and B6–B11 implementations are not complete. |
| [T.O.T.E-loops](https://github.com/nhartman000/T.O.T.E-loops) | Canonical TOTE SQLite schema, versioned migration, seed builder/export | Migration 002 and fresh-build schema are integrated on main at aacddbe744c18133c091b825a88327ba7fbf828a. Existing database migration and conformance tests are deferred; no database file has been migrated. |

Current B5 source of truth:

- [B5 implementation](https://github.com/nhartman000/nych-language-model/blob/main/src/nych_language_model/pipeline/gst_context.py)
- [GST JSON Schema](https://github.com/nhartman000/nych-language-model/blob/main/schemas/gst-context-v1.schema.json)
- [B5 report](https://github.com/nhartman000/nych-language-model/blob/main/reports/builder-05-gst-context.md)
- [TOTE migration instructions](https://github.com/nhartman000/T.O.T.E-loops/blob/main/migrations/README.md)

At the last independent review, the B5 candidate passed all 36 NYCH project tests. TOTE migration tests were not run, as requested; the guarded runner is python migrations/apply_002.py [database-path]. Do not imply the existing SQLite file is migrated.

### Current execution priority

The near-term product priority is to produce real model responses through mg8-runtime, enforce semantic admission before a response is treated as valid, and broaden the benchmark against a standard baseline. This priority does not mean a trained NYCH model or live provider integration already exists. Mark which runtime/provider is actually used; do not substitute mock output for a live-response demonstration. Keep module builders parallel where contracts allow, and measure semantic admission and baseline quality as separate evidence.

### Source precedence

1. Current code, schemas, and status reports on repository main.
2. Current owner decisions in the NYCH and MG8 decision registers.
3. This handoff, which consolidates the approved build plan and decision-interface requirements.
4. Gptbuilder.md, which is a historical snapshot and contains older status statements.

If a historical passage conflicts with current repository status or a later owner approval, preserve it as history and follow the newer decision. Record the conflict; do not quietly revive an obsolete open decision.

## 3. Review of Gptbuilder.md

The attached document is useful as a source transcript, but it is not a complete build specification. It contains a TEXporT Android fragment, repeated marker registers, and status statements that became stale as later decisions and code landed. This companion resolves those issues and accounts for the marked passages:

| Marker(s) | Treatment in this handoff |
|---|---|
| M1–M2 | Unrelated TEXporT Android interaction and UI selection text; excluded from NYCH model scope. |
| M3 | Core discussion: approved B5/B6 split, deterministic domain/action lookup, invariant modalities, TOTE as a database-backed technique, Google-sourced taxonomy candidates, human review for how-to loops, human authoring with automatic checks, and additive TOTE storage. Earlier statements that the schema/adapter were still unbuilt are historical; current B5 and migration status is in Section 2. |
| M4 | Preserved: request-scoped GST contains hierarchy, TOTE, modality, narrative and temporal context; the first symbol-selection LLM call receives GST and the full prompt as separate inputs; B3 trace suffix is applied only once. |
| M5–M9 | Preserved: B5 owns GST assembly/lookup, B6 owns symbol selection, downstream modules/Inspectors extend through B11, and worker/manifest/flow docs must remain synchronized. |
| M10 | Its “schema and validation remain open” status is superseded for the B5 storage and lookup contract. B5 V2 and TOTE migration 002 are now integrated. Runtime database application, live search policy, B4→B5 integration, and B6 write policy remain open. |
| M11–M12 | Preserved: original TOTE schema had five core tables and lacked hierarchy/action/actor/object/tool structures. Migration 002 adds those structures without changing legacy export fields. |
| M13 | Historical pointer to older GST flow docs; current links and status are in Section 2. |

## 4. Core system behavior

### Semantic pipeline

- **B1 — Ingest:** accept exact UTF-8 bytes only; maximum 65,536 bytes; reject empty, malformed, or oversized input. Do not normalize or truncate. Keep the raw prompt in request memory only; never put it in QSON, ordinary logs, or the database.
- **B2 — Tokenization and vocabulary:** whitespace-delimited English surface-word units with exact source byte spans; recognized emoji graphemes are one atomic token from a versioned canonical inventory. Preserve original source text. Approved aliases fold by explicit rules only. Use a versioned local statistical compendium first for typo candidates from the preceding two or three words/context, then keyboard-neighbor maps. If no candidate is clear or the original is coherent, leave it literal and unresolved. The selected general lexicon source is the enwiki-20261001 dump; technical/scientific and named-entity lexicons remain separately sourced. OOV representation may use UTF-8 byte fallback internally while preserving spans. Follow the owner decision register for the detailed corpus split, proper-name and precision gates.
- **B3 — Trace identity:** hash each word occurrence from the exact B1 input digest, zero-based occurrence index, and start-inclusive/end-exclusive UTF-8 byte offsets. Derive the English suffix separately: accent-fold the derived suffix only, remove a/e/i/o/u, retain y, and collapse adjacent repeated consonants. Never modify source text. Use the versioned payload tag and unsigned 64-bit big-endian fields specified in the decision register. B3 is not domain assignment.
- **B4 — Domain resolution:** deterministic, versioned local associative lexicon; no LLM call. Return ranked evidence, preserve multiple plausible labels, and output UNKNOWN when evidence/thresholds are insufficient. Do not force an emoji. Seed lexicon and score/tie thresholds still require Nick’s decision.
- **B5 — GST/context assembly:** exact canonical domain ID plus exact action key lookup in TOTE v2; ambiguity is a cache miss. Require SQLite user_version=2, recompute the versioned canonical loop digest on each hit, require ADMITTED plus matching digest/version and latest PASS validation, and require matching human approval for HOW_TO_EXTRACTED. HUMAN_AUTHORED entries require automatic structural/invariant validation. Other origins fail closed. Assemble request-scoped, versioned GST JSON; never persist prompts. B5 V2 is independently reviewed.
- **B6 — Symbolization:** the first symbol-selection LLM call receives B5’s GST and the complete natural-language prompt as separate inputs. Use known TOTE records before resolving a miss. The invariant modality inventory is fixed; never guess or rewrite it. Preserve negation, modality, quantifiers, pronouns, predicate/argument roles, narrative tense/perspective, and observation/belief/intention/action distinctions. Select one faithful inventory gestalt per eligible word; leave unsupported/scientific/proper-name text literal where no faithful mapping exists. Do not write a newly resolved loop to TOTE until the database write/admission contract is owner-approved.
- **B7 — Embeddings and position.**
- **B8 — Causal attention.**
- **B9 — Transformer block.**
- **B10 — Output projection and probability distribution.**
- **B11 — Data, training, evaluation, and packaging.**

The neural model is not yet built or trained. The model target is distinct from the symbolic assurance pipeline: NYCH/MG8 invariants remain explicit and inspectable; learned output remains probabilistic.

### TOTE, GST, evidence, and prediction

TOTE means Test–Operate–Test–Exit. Every admitted loop must carry at least one actor, one action, one object or tool, and a registered modality operator. A technique can have multiple loops and be shared across taxonomy branches; represent commonality with links, not copied loop records.

GST context records known hierarchy and loop information alongside narrative structure: subject/predicate and semantic roles, perspective, tense/aspect/order, temporal intervals, modality, and explicit/inferred/predicted provenance. Preserve unsupported values as UNKNOWN/null; do not elevate a prediction to a fact. The five-dimensional commonality axis is cross-technique/subdomain commonality; probability/path ranking is separate. Time is captured through narrative tense/aspect/order and explicit intervals.

Fixed modality distinctions must not be collapsed:

- 👀 external observation
- 👁️🧠 internal model/belief
- 🗯️ intention/goal
- 💪 action execution

Search and how-to extraction produce provenance-bearing candidates. Search results are not canonical facts or admitted loops until the applicable human review and automatic validation gates pass. The future contributor interface should let a person choose the domain hierarchy and modality operators from controlled lists, enter action text, and run automatic schema/invariant checks. Those checks establish structural conformance, not factual correctness.

## 5. Owner decision state

Do not ask Nick to decide again on items already approved. Use the decision interface to ask the remaining questions in compact groups. Existing precise decisions live in the linked decision registers; this summary is not a replacement for the exact B2/B3 specifications.

### Approved or implemented

- B1 strict UTF-8, 65,536-byte ceiling, reject empty/malformed/oversized, no normalization/truncation; no raw-prompt persistence.
- English-only V1 and D3 suffix behavior.
- D2 whitespace spans, atomic canonical emoji inventory, statistical typo library then keyboard check, unresolved literal fallback; corpus/source choices and precision gates are in the NYCH decision register.
- B3 SHA payload and suffix contract; bounded module passed independent inspection. End-to-end B1/B2 span provenance still needs integration checks.
- D0 model objective: deterministic NYCH encoder, tiny decoder-only causal LM, next NYCH token/symbol sequence, symbolic assurance kept distinct from probabilistic output.
- D1-context: 1,024 tokens per window, split longer accepted input into ordered windows, never truncate. A later D7 position limit must equal 1024. D7 is not approved.
- B5 additive TOTE SQLite v2, PRAGMA user_version=2, canonical digest, exact domain_id + action_key, ambiguity miss, versioned request-scoped GST JSON, schema `nych-language-model/schemas/gst-context-v1.schema.json`, source of truth `src/nych_language_model/pipeline/gst_context.py`, provider candidates unapproved pending review, origin-specific automatic/human validation. Reconfirmed against that expanded definition.
- B5 code/review: 36 tests passed independently.
- TOTE migration 002 merged to source control; no existing database applied or conformance-tested yet.
- Weight pruning deferred to Builder Pro V2.
- Repositories are private; no public release implied.
- One GitSON handoff per module boundary must be under 500,000 bytes (owner-stated constraint); the exact validator/schema is still pending.

### Pending owner choices to surface in the interface

| Decision | Module(s) | Needed before | Candidate question for Nick |
|---|---|---|---|
| Domain lexicon seed and thresholds | D4 | B4, B5 integration | Which seed lexicon and confidence/tie threshold should B4 use? Keep multi-label candidates and UNKNOWN when uncertain. |
| Symbol-selection call and cache-miss contract | D6 | B6 | Behavioral request/response contract is recorded in catalog v3.1 `request_response_schema` and is not an approval. Endpoint and TOTE write policy are still missing. Do not invent an exact JSON schema, HTTP path, or write-back rule. |
| Embedding and positional encoding | D7 | B7–B10 | Approve proposed d_model 128, learned embeddings, RoPE, float32 reference build? |
| Attention | D8 | B8–B10 | Approve two causal layers, four heads, head width 32, and no KV cache in the V1 reference? |
| Transformer block | D9 | B9–B10 | Approve Pre-RMSNorm, residual connections, SwiGLU width 512, dropout 0.1 only during training? |
| Output head | D10 | B10–B11 | Approve tied embeddings, full-vocabulary logits, stable softmax, next-token cross-entropy? |
| Neural corpus and training | D11 | B11 | Select a license-cleared English corpus distinct from the typo-statistics corpus; approve deduplication, fixed split, no prompts, and recorded seeds/config/hardware? |
| Inspector evidence bar | D12 | All merges | Approve contract coverage, negative/boundary/adversarial tests, reproducibility, exact digests, and baseline comparison; missing evidence blocks PASS? |
| GitSON contract/runtime | D13 | Integration | Approve interface-versioned per-boundary GitSON, exact artifact and upstream PASS digests, trusted host validation, <500,000-byte cap? |
| Tiny-model size and resource budget | New D14 | B7–B11 training | Choose a parameter-count band, memory/latency target, and available training hardware. Do not invent “tiny” as a numeric size. |
| Benchmark and success criteria | New D15 | B11/release | Choose minimum NYCH structural fidelity, semantic preservation, OOV/typo behavior, next-token metrics, latency, and baseline comparison measures. Report these separately. |
| Packaging/release target | New D16 | Final build | Choose downloadable format and supported runtime/device. Keep private until an explicit release decision. |

The numeric architecture choices above are recommendations from the existing register, not approvals. The interface must display them as “Recommended—awaiting owner approval.”

## 6. Streamlined decision interface specification

Build a small “Model Builder Decision Console” before asking Nick a long series of one-off questions.

### Decision card

Each card contains:

- Stable ID, short title, module owners, and dependency list.
- One-sentence question in ordinary language.
- Recommended option, alternatives, concise tradeoffs, and evidence/source links.
- Radio/dropdown controls for categorical choices; constrained sliders or numeric inputs only for numeric decisions, with units, range, and step shown.
- An explicit “Approve recommendation,” “Choose another,” and “Leave pending” action.
- Optional editorial note; never silently turn free text into an approved contract.
- State: PENDING, APPROVED, REJECTED, SUPERSEDED, or BLOCKED; owner, timestamp, rationale, and decision-set digest.

### Fast owner flow

1. Present a compact queue grouped by decision round: objective/size/context; semantics/domain; model architecture; data/training/evaluation; assurance/wiring/release.
2. Provide “Approve all recommended choices” with a visible exception list. The click records each decision individually. Do not treat viewing or leaving the page as approval.
3. If any answer is pending, show which builders are blocked and which can still start with a frozen mock interface.
4. Let Nick edit a decision later. Create a new immutable decision event and mark the old one SUPERSEDED; never rewrite history.
5. Export machine-readable owner-decisions.v1.json, human-readable DECISION_REGISTER.md, and a metadata-only QSON decision event. Do not include natural-language prompts or user examples.

### Dependency-aware parallel launch

The interface must separate **parallel module construction** from **dependency-ordered integration**.

- Launch every builder whose own contract is approved at the same time; do not serialize B2→B3→… building just because wiring depends on upstream outputs.
- Give each builder versioned interfaces, approved decisions, fixtures/mocks for unfinished upstream modules, allowed file scope, required evidence, and stop conditions.
- Start a distinct Inspector for each candidate as soon as the candidate is frozen. The Inspector reviews the exact commit/artifact digest and does not inherit the Builder’s approval.
- Wiring is dependency-gated: only connect modules after relevant contract and inspection PASS. Record wiring in small GitSON files under 500,000 bytes.
- A builder may not change another module’s contract or source. If it finds a dependency conflict, emit a proposed decision/change request; do not silently broaden scope.
- Use MG8/ICM units as the controller: one unit per builder/inspector; G8SON gates enforce scope, contract, artifact evidence and handoff; ORK determines allowed progression; QSON records metadata and decisions; GitSON connects only passing modules. Do not claim this orchestration is automated until the runner actually executes and validates it.

### Decision storage and review

The decision console is the only routine owner-question surface. It should update the MG8 decision register and the NYCH decision register from the same versioned decision object or a generated projection. Avoid duplicated conflicting manual copies. Every generated spec includes source decision IDs and digest. Keep a compact audit trail that proves who approved which contract and what exact builders received it.

## 7. Builder and Inspector operating contract

### Builder N

- Own exactly one module and its narrow integration contract.
- Read the handoff, current decision register, upstream interface schemas, and repository status before editing.
- Work on a dedicated branch; submit implementation, module schema/interface, focused tests, standard/reference comparison where applicable, report, file SHA-256s, and known limitations.
- Do not alter raw prompt privacy rules, shared schemas, model scope, or other modules without an explicit decision.
- Do not self-approve, merge, or describe an untested candidate as PASS.
- If an owner decision is pending, implement only portions whose contract is frozen and use explicit UNKNOWN/mock boundaries for the rest.

### Inspector N

- Be separate from the Builder context. Review the exact commit, not a description of it.
- Check scope, contract, correctness, privacy, provenance, schema conformance, positive/negative/boundary/adversarial tests, reproducibility, and artifact hashes.
- Use PASS only when evidence is complete; INTERMEDIATE for missing evidence or unresolved contracts; FAIL for a defect or unsafe bypass.
- Report exact blockers and evidence. Never change code under review.
- Re-run tests when the owner’s test policy allows it. For TOTE migration 002, testing is explicitly deferred; keep that status visible until the later pass.

### Merge gate

Merge a module only after Inspector PASS and all dependent contracts are frozen. The trusted host, not the LLM, validates artifact scope, tests, schemas, hashes, upstream PASS records, and GitSON before advancing ORK. Keep every commit reversible and avoid history rewrites.

## 8. Parallel work plan

### Immediate takeover

1. ~~Publish missing Builder/Inspector cards.~~ Done: all 22 cards are committed on main (verified at 2284ac9). Still audit NYCH and T.O.T.E-loops trees; the NYCH BUILD_STATUS is stale relative to the B5 V2 report and needs a separate reconciliation.
2. Update the MG8 and NYCH decision registers from this handoff. D0 and D1-context are approved. D5 is reconfirmed against the expanded definition; do not ask Nick again about B5 storage/version/lookup/GST defaults, request scope, schema path, or the deferred migration-002 application and tests.
3. Build the Decision Console and its versioned decision schema. The owner screen still shows D4, D6, and D7–D16. D4 is incomplete. D6 is incomplete and not approved: the behavioral request/response contract is recorded, and endpoint plus TOTE write policy are still open.
4. Collect the remaining owner decisions. D7–D11 are the next walkthrough. Do not launch architecture-dependent work until those choices are recorded.
5. Once choices are frozen, launch ready builders concurrently. B1 review, B2 implementation, B4 lexicon after D4, B6 after D6, B7–B10 after their shared architecture decisions, and B11 after corpus/metrics decisions may proceed as independent candidate jobs with mocks where needed.
6. Run separate Inspectors in parallel as candidates finish. Fix defects on new commits and re-inspect the corrected commit.
7. Wire passing modules through GitSON only after dependency gates pass.

### Integration order (not build order)

B1 → B2 → B3 → B4 → B5 → B6 supplies the semantic input path. B7/B8/B9/B10 form the neural model path and may be developed in parallel once their shared tensor, vocabulary, context, and training contracts are frozen. B11 consumes frozen model/data interfaces. The final package combines the deterministic pipeline, model, TOTE v2 schema dependency, and reproducible metadata.

The first runtime demonstration should show: exact input bytes → B1 digest → B2 spans → B3 trace IDs → B4 domain candidates/UNKNOWN → B5 GST hit or explicit miss → B6 faithful symbolization/literal fallback → model next-token output → inverse/reconstruction checks and QSON audit metadata. Do not claim quality based only on a successful model run.

## 9. Evidence and release criteria

Before calling V1 build complete, produce:

- Exact contracts and versioned schemas for every module and handoff.
- Independently reviewed modules with exact commit and artifact digests.
- Tests for valid, invalid, boundary, ambiguous, malformed provenance, cache-miss, and adversarial cases.
- TOTE migration rehearsal on a database copy: source version check, rollback test, integrity check, foreign-key check, user_version=2, seed/export compatibility. Then request/record authorization before changing any production/valuable database.
- Golden round-trip and invariant tests: no negation loss, no modality promotion, no role/argument swaps, no identity collisions, no unsupported emoji substitution, unresolved alternatives preserved.
- A tiny-model reference implementation with parameter count, memory, latency and deterministic configuration recorded.
- Same-data standard baseline and NYCH model comparison. Report next-token loss/perplexity and accuracy alongside NYCH semantic preservation, structural validity, calibration/confidence, OOV/typo slices, latency, memory and token/compression measures. Keep neural metrics separate from semantic/invariant metrics.
- Reproducible corpus manifest, licenses/attribution, exact split, deduplication evidence, seed, optimizer/config, hardware/runtime versions, training logs without prompts, checkpoint hashes.
- A packaging manifest and local inference example. Public release requires a separate explicit decision.

## 10. Scope limits and stop conditions

Stop the affected worker—not the entire parallel build—when its own choice is pending, evidence is missing, source provenance cannot be established, a candidate violates an invariant, or its upstream interface is ambiguous. Mark UNKNOWN/BLOCKED and state what owner decision or artifact would unblock it.

Do not:

- Guess the domain lexicon or confidence thresholds.
- Treat a Google result, model output, how-to extraction, or seed row as canonical without its specified provenance/admission path.
- Persist raw prompts or include them in QSON.
- Let B5 choose or infer narrative facts; it validates/passes through structured upstream narrative/provenance.
- Write cache-miss loops into TOTE automatically.
- Call a training corpus license-cleared without documented review.
- Claim a tiny trained NYCH model, live search, full MG8PK runner, decision UI, end-to-end wiring, or current-database migration exists until implemented and inspected.
- Label this work “DARPA-certified.” Say “reviewed against the project’s high-assurance criteria” only when cited evidence supports it.

## 11. Copy/paste kickoff for Grokbot

> Take over the NYCH Language Model V1 / MG8 Model Builder project using this handoff. First audit the live GitHub trees and current decision registers; use repository main as source of truth and verify the B5/TOTE commits cited here. Reconcile the MG8 README with the actual committed Builder/Inspector cards. Do not repeat questions already approved in D5/B5. Build the Model Builder Decision Console specified in Section 6 and populate it from the pending D0, D1-context, D4, D6–D16 choices. Ask Nick to approve/revise those decisions in one grouped session. Once a module’s contract is frozen, launch that module’s Builder and a separate Inspector in parallel with other ready modules. Builders may use interface-matched mocks; integration remains dependency-gated. Keep prompts out of logs/QSON, preserve explicit-vs-inferred-vs-predicted provenance, and treat UNKNOWN as a stop for the affected path. Do not claim TOTE migration testing or database application; Nick deferred those tests. Push each Builder/Inspector card and reviewed module evidence to its correct private repository. Merge only after independent PASS. Start with the audit and decision UI. Prioritize live responses through mg8-runtime, semantic admission, and broader benchmarking; do not claim mocks as live responses. Do not start neural training until owner decisions, licensed data plan, evaluation gates, and resource budget are recorded.
