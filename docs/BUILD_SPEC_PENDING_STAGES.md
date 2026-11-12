# Build spec: five unwired stages

## Current implementation snapshot

This is the approved build contract; the status below records the current
builder-repo implementation and does not change any owner decisions.

| Stage | Current smoke status | Boundary |
|---|---|---|
| B1 ingest | Wired and passing | Calls the pinned NYCH implementation before tokenization; accepted text remains in memory. |
| B5 GST | Not runnable for the sample | Read-only bridge calls the NYCH implementation when B4 supplies explicit keys; this smoke sample has no B4 result. |
| B6 symbolization | Not runnable | Test-only literal stub checks channel separation; no model call is authorized. |
| Typo compendium | Not the real build | Batched on-disk builder with markup stripping (mwparserfromhell 0.6.6), split, keyboard maps, the 99% gate, and approved D2 smoothing (`chen-goodman-mkn-interpolated-v1`, context lengths 0–3) exist and are checked on synthetic fixtures. No dump is loaded here, so the smoke stage is not wired and passing. |
| Domain switch | Deferred | Approved V1 scope: one active domain per request; no switch tags emitted. The provisional parser in `nych_preview/domain_switch.py` is preview-only and is not called by the smoke path. |
| D12 inspector | I1 PASS on pinned B1 | I1 reviewed the pinned ingest. The bundle met the D12 bar, so the verdict is PASS. Missing evidence stays INTERMEDIATE. Validator acceptance is not an inspector pass. |

The build runner skips stages that are not `wired and passing` or `provisional`.
Do not promote a blocked stage merely because an adapter or validator exists.

Standalone instructions for a builder that has not seen the decision chat. This repo is `nhartman000/mg8-model-builder`. The NYCH implementation repo is `nhartman000/nych-language-model`. Do not invent owner values. Anything marked **interpreted** is a reading of the sources, not an owner decision. Do not persist raw prompts, and do not put them in tests, logs, reports, or QSON.

The smoke entry point is `python3 -m nych_smoke`. `nych_smoke/report.py` `stage_report()` reports each stage from what actually ran. `b5_gst`, `b6_symbol_call`, and `typo_compendium` stay not runnable for the real build. `b1_ingest` calls the pinned implementation. `inspector` is I1's verdict on that pinned ingest. Wire a stage by making that status honest. `scripts/gcp_build.sh` logs any stage whose status is not `wired and passing` or `provisional` as skipped. Do not add fake stages.

Approved decisions live in `console/fixtures/catalog.v3.26.json` and `console/fixtures/events.v2.jsonl`. The hand register is `icm/MG8PK/DECISION_REGISTER.md`.

## 1. B1 ingest

**Purpose.** Accept or reject the exact request bytes before any later stage. Builder card: `icm/MG8PK/workers/builder-01.md`. Target file, in the NYCH repo: `src/nych_language_model/pipeline/ingest.py`. This console does not model a B1 decision id (`CONTRACT_NOT_MODELED_IN_CONSOLE`).

**Inputs.** Raw request bytes. No path is specified. Do not read a prompt log.

**Outputs.** On accept: the original bytes unchanged, their SHA-256, and the byte length, held only in request memory. On reject: a failure, no text. No schema file exists in this repo. **Interpreted:** a JSON object `{ "sha256": "sha256:<64 hex>", "byte_length": <int>, "utf8": true }` is enough for the smoke, and it must not be written to QSON.

**Plug-in.** `nych_smoke/pipeline.py` `run_text` hashes the UTF-8 bytes with `nych_smoke/trace_id.py` `input_digest(raw: bytes) -> bytes` and then tokenizes. B1 runs first through the pinned NYCH implementation. `trace_id(raw_digest, index, start, end, suffix)` requires that 32-byte digest. The smoke report records metadata only; it does not include accepted text.

**Rules.** Register: UTF-8 only; maximum 65,536 bytes; reject empty, malformed UTF-8, and oversized input; no normalization and no truncation. No tokenization, trace IDs, domain inference, or semantic encoding (`builder-01.md`).

**Acceptance.** Accept a short valid UTF-8 fixture. Reject empty bytes, a bad UTF-8 sequence, and 65,537 bytes. Accept 65,536 bytes. The digest of the accepted bytes equals `input_digest`. No output file contains the fixture text.

**Open.** No B1 catalog decision. No owner-specified error code or exception type.

## 2. B5 GST

**Purpose.** Build one request-scoped GST and hand it to B6 separately from the full source prompt. D5 is approved.

**Inputs.** After B4 has a domain. Database, in the NYCH repo, as named by `builder-05.md`: `schema.sql` tables `modality_operators`, `gestalts`, `tote_loops`, `tote_steps`, `loop_gestalts`; built files `data/tote_loops.sqlite3` and `data/tote_loops.json` from `src/build_db.py`. Lookup key from D5: exact canonical `domain_id` + `action_key`. Ambiguity is a cache miss.

**Outputs.** Versioned GST JSON. D5 paths, both in the NYCH repo: schema `schemas/gst-context-v1.schema.json`; source of truth `src/nych_language_model/pipeline/gst_context.py`. Storage is additive TOTE SQLite v2. `PRAGMA user_version` is 2 and is part of the canonical digest. Scope is request-scoped. Origins: `HUMAN_AUTHORED` gets automatic structural and invariant validation; `HOW_TO_EXTRACTED` needs matching human approval; unknown origins fail closed.

**Plug-in.** This repo does not import `gst_context.py`. The smoke stage is `b5_gst`. Do not checkout or reimplement B5 here. The integration point is: call the NYCH `gst_context` producer, then pass its GST object as one argument and the untouched prompt string as another. `builder-05.md` says B5 does not call an LLM and does not resolve cache misses.

**Rules.** D5 as above. D6: modality operators are invariant; the TOTE loop is domain, subdomain, and technique, then at least one actor, one action, one object, and one modality operator. On a hit, recompute `NYCH-TOTE-LOOP-DIGEST-V1` over the current loop record. `admission_status` alone is not proof. A digest mismatch is a cache miss (`builder-05.md`, `inspector-05.md`). Do not write new loops until a write policy is approved. Migration of an existing database and migration-002 conformance tests are deferred (D5).

**Acceptance.** A fixture hit returns the same GST for the same `domain_id` and `action_key`. Two matches are a cache miss. A changed step changes the digest and becomes a miss. `HOW_TO_EXTRACTED` without a matching human approval is not admitted. The prompt string is unchanged and is absent from the GST file, logs, and QSON.

**Open.** The closed V1 set of modality operators is not restated in this repo (`icm/MG8PK/OWNER_QUESTIONS.md` question 6). Exact verifier rules and the schema extension for a future authoring form are open (`builder-05.md`). Live Google hierarchy enrichment, the B4-to-B5 interface, and the write/admission endpoint remain open (register, D5 row).

## 3. B6 symbolization

**Purpose.** Choose an emoji gestalt per word, or one gestalt for several words that form one idea. Unfaithful spans stay literal. D6 is approved.

**Inputs.** Two separate values (D6 `inputs`): the B5 GST, and the complete natural-language prompt. Also the token spans from `nych_smoke/tokenize.py` `tokenize(text) -> (raw_bytes, tokens)` and the trace ids from `trace_id`. Cache-miss markers come from B5. Do not merge the prompt into the GST.

**Outputs.** Target file, in the NYCH repo: `src/nych_language_model/pipeline/nych_symbolization.py`. No response schema file exists beyond the D6 prose. Each selection is an emoji from the approved endpoint plus a gestalt id, or a literal span. Gestalt id shape from D6: a name compound embeds with each part capitalized, owner example `fibbonacci sequence` → `FbncSqnc`; a normal id appends the short word after `_`, owner example `_wrd`; a second compounded word is capitalized, owner example `word smith` → `wrdSmth`. The current abbreviation helper is `nych_preview/gestalt_abbreviation.py`. It is not wired into a Builder. Acronyms are excluded from that helper by `nych_smoke/pipeline.py` (`status` `acronym-excluded`). That exclusion is an interpretation of a later owner statement, not a D6 approval.

**Plug-in.** Smoke stage `b6_symbol_call`. It must not send a prompt in this repo's tests. Call the symbolizer only behind a stub that records the two input channels and returns literals. The endpoint is `https://unicode.org/emoji/charts/full-emoji-list.html` and `https://www.unicode.org/emoji/charts-18.0/`, Unicode Emoji Charts v18.0 (D6). The owner-stated inventory actually loaded here is Unicode Emoji 18.0 fully-qualified rows in `nych_inventory/emoji/emoji-test.txt`. That file is a stated source, not a second approval.

**Rules.** D6: preserve negation, modality, quantifiers, pronouns, predicate/argument roles, and observation/belief/intention/action. Do not promote belief, intention, or action into observation. Reuse a database match. Resolve a cache miss only inside this call, under invariant TOTE structure and the modality inventory. Do not persist a new database row until the D6 write policy is implemented as approved: modality operators stay fixed; other loop words may be chosen dynamically; domain organization and loop sequence stay. Literal fallback when no faithful emoji exists. Apply the B3 trace suffix idempotently.

**Acceptance.** GST and prompt arrive as two arguments. A known match is reused with no model call. A miss is marked, not written to SQLite. A scientific term and a proper name without a faithful emoji stay literal. `FbncSqnc`, `_wrd`, and `wrdSmth` match the D6 examples when the abbreviation helper is applied to those owner strings. No prompt text appears in the artifact.

**Open.** The symbol-selection call is an LLM call. No model name, prompt template, or temperature is approved. Do not invent them. Chat-local symbols and the domain legend are in the approved D6 text; the legend file format is not a schema. Interlinear tag grammar, span alignment, and domain-switch tag placement are owner-stated on D15 and still open. See `icm/MG8PK/OWNER_QUESTIONS.md`.

## 4. Typo compendium

**Purpose.** Local n-gram evidence for typo candidates. It does not replace the surface token and it does not call an LLM. Specs: `icm/MG8PK/specs/STATISTICAL_COMPENDIUM_INDEX_V1.md`, `icm/MG8PK/specs/WIKIPEDIA_CORPUS_PROVENANCE_V1.md`. Builder notes: `icm/MG8PK/workers/builder-02.md`.

**Inputs.** The D2 general-statistics file, streamed, not loaded whole:

`enwiki-20261001-pages-articles-multistream.xml.bz2`

Directory: `https://dumps.wikimedia.org/enwiki/20261001/`. The provenance spec says the dump index lists it at 25.1 GB compressed. Use article-namespace pages only. Exclude templates, talk, user pages, logs, files/media, and project/meta pages. Do not use `pages-meta-history`. Record the dump's official checksum and the SHA-256 of the downloaded file. Do not commit the dump or extracted article text.

Build context for the machine that will run this, not a catalog field: about 4 GB free RAM and 8 cores. Stream-decompress and parse one page at a time. Do not materialize the dump or the extracted corpus in RAM.

**Outputs.** A private SQLite file plus a JSON manifest. No output path is approved. Manifest fields are listed in the compendium spec: `schema_version`, `compendium_id`, `corpus_id`, license reference, corpus SHA-256, tokenizer/normalizer version, n-gram order, smoothing method and version, build code version, artifact digest, and keyboard-layout map ids. Table `ngram_counts` columns: `order_n`, `context_key`, `candidate_token`, `count`, `context_total`, `probability`, `log_probability`. `order_n` starts at 1–3. Keep derived artifacts private until a license review. Page provenance fields are the table in `WIKIPEDIA_CORPUS_PROVENANCE_V1.md`.

**Plug-in.** Smoke stage `typo_compendium`. There is no function yet. It sits after `tokenize` and must not change token text or byte spans. A correction is a separate hypothesis (`surface`, `candidate`, `evidence`, `confidence`). `run_text` keeps the original token.

**Rules.** D2, as written in `builder-02.md` and the compendium spec. Split before counting: SHA-256 over the UTF-8 bytes of `NYCH-D2-SPLIT-v1`, a NUL, the snapshot id `enwiki-20261001`, a NUL, and the decimal page id; take the digest as a big-endian integer modulo 100. Buckets 0–89 train, 90–94 validation, 95–99 test. Counts come only from train pages. Cutoffs are tuned on validation. Test pages stay unseen. Rank candidates from the previous two or three words, with backoff, then right context when it exists. Keyboard maps are secondary: US QWERTY, UK QWERTY, AZERTY, and QWERTZ. If the layout is unknown, those enabled layouts must agree or the token stays unresolved. Automatic correction is allowed only when the one-sided 95% Clopper–Pearson lower confidence bound on held-out precision is at least 99%. Otherwise leave the token literal. Report precision and false corrections separately for proper names, scientific terms, coherent rare words, ambiguous candidates, and each layout. This split is not the D11 neural split. D11's neural corpus is Common Corpus.

**Acceptance.** A synthetic two-page fixture assigns stable buckets. Train counts ignore test pages. A held-out set below the 99% bound produces zero automatic replacements. The original token text is still in the pipeline output. The manifest digest changes when one train count changes.

**Open.** Smoothing algorithm is unnamed. Do not pick one. D11 does not name the typo-statistics corpus; do not assume it is this Wikipedia dump (`OWNER_QUESTIONS.md` question 4). The technical/scientific lexicon source is pending (question 3). Whether the compendium SQLite path is shared with `data/tote_loops.sqlite3` is not decided. **Interpreted:** it should be a different file, because the specs describe different stores.

## 5. D12 inspector

**Purpose.** An inspector reviews one builder's exact artifact. The builder does not inspect itself. D12 is approved. Cards: `icm/MG8PK/inspectors/inspector-01.md` through `inspector-11.md`.

**Inputs.** The candidate commit or artifact digest, the approved contract for that module, and the evidence bundle. There is no inspector source file in this repo.

**Outputs.** A verdict `PASS`, `FAIL`, or `INTERMEDIATE`. D12: missing evidence is `INTERMEDIATE`, not a silent pass and not a guessed fail. Evidence must show exact contract match, positive, negative, boundary, and adversarial cases, reproducibility, an exact digest, and a reference comparison where one exists. The existing checker is `gitson_boundary.validate_declaration`. It accepts a UTF-8 JSON document under 500,000 bytes matching `schemas/gitson-boundary-declaration.v1.schema.json`. A B-module declaration needs upstream PASS evidence for its source module, with `inspector_id` `I` plus the module number, `case_classes` containing `positive`, `negative`, `boundary`, and `adversarial`, and `reproducible`, `exact_digest`, and `reference_comparison` set. That checker is not an inspector. It only accepts a declaration that already claims PASS.

**Plug-in.** Smoke stage `inspector`. Do not mark it passing by running the validator alone. An inspector result may be cited inside a declaration. `validate_declaration` then checks the declaration shape. D13: the trusted host must still validate the handoff. An inspector report does not authorize wiring.

**Rules.** D12 `bar` and `missing_evidence`, as stored in catalog v3.26. One inspector per builder. Inspectors I1–I11 pair with B1–B11. INTEGRATION has no inspector id (`gitson_boundary`).

**Acceptance.** A bundle missing any D12 element is `INTERMEDIATE` and is not submitted as PASS. A complete bundle names one digest and the four case classes. A second run on the same bytes yields the same verdict. The validator rejects a declaration whose evidence omits the source module.

**Open.** No owner-specified inspector program name, report path, or diff format. Reference comparison has no mandated baseline except where a stage already names one (the compendium's held-out precision, the D10 unmodified path). Do not invent a baseline.
