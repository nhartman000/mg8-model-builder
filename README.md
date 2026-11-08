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

The B5 GST context module is integrated in the NYCH repo and independently reviewed; its 36-test suite passed. TOTE migration 002 is integrated into the TOTE repo, but has not been applied to an existing database and its tests are deferred. D5 is approved. Remaining owner choices and the decision-console plan are in the build handoff. Builder cards are plans, not claims that autonomous agents are currently running.

## Decision Console V1 (offline)

`console/` holds the Model Builder Decision Console core specified in handoff §6: an append-only, hash-chained, versioned decision-event log (`console/schemas/decision-event.v1.schema.json`), per-decision bulk approval with visible exceptions, immutable supersession, and deterministic projections (`owner-decisions.v1.json`, generated register markdown, metadata-only QSON events). Stdlib Python only; no network, provider, or database side effects.

- Regenerate: `PYTHONPATH=console python3 -m decision_console console/fixtures/catalog.v1.json console/fixtures/events.v1.jsonl console/out`
- Test: `python3 -m unittest discover -s tests`

The only seeded event is the historical D5 approval. All other recommendations remain PENDING ("Recommended—awaiting owner approval"); the generated register does not replace `icm/MG8PK/DECISION_REGISTER.md` until the owner approves that switch.
