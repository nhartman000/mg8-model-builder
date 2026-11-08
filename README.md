# MG8 Model Builder

This repository defines the ICM/MG8 worker system that builds the NYCH language model. Each Builder has one bounded module responsibility. Each module has a separate Inspector who reviews the exact artifact and evidence digest.

## Build handoff

See [Grokbot NYCH Model Build Handoff V1](docs/GROKBOT_NYCH_MODEL_BUILD_HANDOFF_V1.md) for the consolidated build plan, owner decision queue, decision-console specification, parallel worker/inspector protocol, and current repository status.

## Repositories

- Builder system and worker/inspector specifications: `nhartman000/mg8-model-builder`
- NYCH model source and module outputs: `nhartman000/nych-language-model`

## Workflow

1. Freeze owner decisions and shared input/output contracts in `icm/MG8PK/DECISION_REGISTER.md`.
2. Run isolated Builder candidates concurrently against the frozen contracts.
3. Run separate Inspector reviews; builders cannot approve their own work.
4. Store each module under the NYCH model's standard `src/nych_language_model/` package layout.
5. Wire modules only after contract and evidence gates pass. Each GitSON handoff carries interface versions, artifact digests, and upstream PASS evidence.

Parallel building does not mean unreviewed integration. A blocked dependency can stop wiring while independent module candidates continue.

## Status

The B5 GST context module is integrated in the NYCH repo and independently reviewed; its 36-test suite passed. TOTE migration 002 is integrated into the TOTE repo, but has not been applied to an existing database and its tests are deferred. D0 and D1-context are approved. D5 is reconfirmed against the expanded catalog v3 definition. D4 has a recorded seed lexicon and lookup order. If a domain cannot be resolved, the working output is `unresolved domain`. The full domain-decision rule module is deferred. D4 records a confidence rule whose fail-at-or-below bar is 0.75 and remains incomplete because tie policy is still missing; D4 is not approved. D6 records the common emoji-library endpoint and remains incomplete because TOTE write policy is still missing; D6 is not approved. D7 and later decisions remain pending. Builder cards are plans, not claims that autonomous agents are currently running.

## Decision Console V1 — OFFLINE CORE / EXPORT PROTOTYPE (no UI yet)

`console/` holds the event core and file exports for the Decision Console in handoff §6. There is no interactive UI yet. It makes no network, provider, database, or build-launch calls, and its readiness output is advisory only (`readiness_authoritative: false`). Do not launch builders from it.

- Catalog `console/fixtures/catalog.v3.4.json` is the current contract. `catalog.v2.json` is the snapshot the D5 historical approval was recorded against. `catalog.v3.json` is the snapshot the D0, D1-context, and D5 reconfirm events were recorded against. `catalog.v3.1.json` records the D6 behavioral contract. `catalog.v3.2.json` records the D4 two-source lexicon. Pass snapshots oldest first. v3 adds cross-decision equality constraints (`D1-context.window_tokens` = `D7.position_limit`, and `D7.d_model` = `D8.model_width`) and numeric `maximum` / `step` bounds. v3.1 leaves D6 `endpoint` and `tote_write_policy` empty, so D6 stays incomplete and unapproved. v3.2 records the D4 seed lexicon and lookup order. v3.3 records that an unresolvable D4 result is written `unresolved domain` and that the full domain-decision rule module is deferred. v3.4 records the D4 confidence rule, with `confidence_threshold` 0.75 as the fail-at-or-below bar, and the D6 emoji-library endpoint. `tie_policy` and D6 `tote_write_policy` stay empty, so D4 and D6 stay incomplete and unapproved. An approval that breaks a declared bound, or that disagrees with a peer already approved against the same definition, is rejected. Recommendations in the catalog must already agree. Fields marked `owner_input_required` carry no recommendation. A decision with any such field is INCOMPLETE: it cannot be approved by recommendation, bulk approval skips it and lists it in every bulk event, and it keeps its modules blocked. An owner can still complete it explicitly with `CHOOSE_OTHER`. D14 stays owner-input text (`parameter_band`, `memory_latency_target`, `training_hardware`); no numeric size is invented for it.
- The D5 historical event is unchanged and still records the v2 fields (`storage`, `user_version`, `lookup`, `gst_format`, `origin_policy`). A later `APPROVE_RECOMMENDATION` reconfirms the expanded v3 definition: those five fields plus request-scoped GST, `nych-language-model/schemas/gst-context-v1.schema.json`, `gst_context.py` as source of truth, and deferred existing-database application of TOTE migration 002 plus its conformance tests. That reconfirm is what counts toward readiness. Do not mint a second historical approval.
- Events (`console/schemas/decision-event.v1.schema.json`) are append-only and hash-chained, with strict type and semantic validation, immutable supersession, and per-decision bulk events showing their exceptions. Each event records which catalog snapshot it was made against. When a definition changes, earlier approvals are kept but flagged for reconfirmation, and they stop counting toward readiness.
- Historical approvals can only be imported once, through `import_historical()`, and only when the catalog declares them (D5). Normal recording can't create them.
- Trust boundary: the hash chain can't detect a log whose last events were cut off, and `owner` is an unauthenticated label. For completeness, pass an externally trusted expected head/count (`MG8_EXPECTED_HEAD` / `MG8_EXPECTED_COUNT`); authorship has to come from signed commits or similar.
- Notes and rationales are free text and are stored in events and in `owner-decisions.v1.json` (QSON exports are metadata only). Never put real prompt text or user examples in them. The forbidden-key filter only catches obvious mistakes; it doesn't guarantee prompts aren't stored.
- Readiness is conservative. B1–B3 are always blocked because their contracts aren't modeled here, `ALL` decisions (D12) gate every module, and dependency closures apply.
- Regenerate: `PYTHONPATH=console python3 -m decision_console console/fixtures/events.v2.jsonl console/out console/fixtures/catalog.v2.json console/fixtures/catalog.v3.json console/fixtures/catalog.v3.1.json console/fixtures/catalog.v3.2.json console/fixtures/catalog.v3.3.json console/fixtures/catalog.v3.4.json`
- Test: `python3 -m unittest discover -s tests`

The log records the historical D5 approval, then owner approvals of D0 and D1-context and a D5 reconfirm against catalog v3. No later decision event was added for D4 or D6. D4 stays pending and incomplete (`tie_policy`). D6 stays pending and incomplete (`tote_write_policy`). D7 onward stays pending. `console/fixtures/archive/` keeps the superseded v1 fixtures from 25f884b unchanged. The generated register is a projection of that log; `icm/MG8PK/DECISION_REGISTER.md` is updated to the same status.
