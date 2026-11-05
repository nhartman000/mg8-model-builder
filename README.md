# MG8 Model Builder

This repository defines the ICM/MG8 worker system that builds the NYCH language model. Each Builder has one bounded module responsibility. Each module has a separate Inspector who reviews the exact artifact and evidence digest.

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

Worker cards are definitions, not claims that autonomous jobs are currently running. The design decisions listed as pending must be answered before implementation agents are launched.
