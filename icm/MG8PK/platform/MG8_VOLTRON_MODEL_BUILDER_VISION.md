# MG8 Voltron Model Builder — Platform Vision

## Product goal

Build one reusable model-construction system that can produce NYCH V1 and later support other model designs. NYCH is the flagship reference build, not a hard-coded limit on the platform.

A user should be able to define a model through a versioned specification form, review the consequences, generate a build plan, build modules independently, wire only compatible modules that pass inspection, and run reproducible evaluation.

## User workflow

1. **Choose a model family and objective.** Start from a template or a blank specification.
2. **Set bounded design choices.** Use sliders for numeric ranges with meaningful bounds; use dropdowns for enumerated options; use short questions when a choice needs explanation. Every control must show units, allowed range/options, default, and effect on compute, memory, data, or behavior.
3. **Validate and freeze the spec.** Show unresolved choices and incompatibilities. Produce a versioned, machine-readable model spec and a human-readable summary. Do not launch builders while required decisions are unresolved.
4. **Generate isolated module work.** Create one scoped Builder and one independent Inspector assignment per module. Builders may work in parallel against frozen interfaces and schema-matched mocks.
5. **Review candidate artifacts.** Capture source, configuration, dependencies, data provenance, hashes, and reproducibility evidence. An Inspector reports PASS, FAIL, or INTERMEDIATE; missing evidence cannot pass.
6. **Wire compatible modules.** Generate small GitSON declarations for module boundaries. A trusted host validator checks interface versions, artifact digests, dependency order, and upstream PASS evidence before wiring.
7. **Build and test the assembled model.** Run unit, integration, boundary, and task-level evaluations; compare with a standard reference baseline where meaningful. Present metrics, limitations, failures, and reproducibility details.
8. **Revise through explicit decisions.** A user may change a parameter or module choice, see the affected dependency graph, and rebuild only invalidated downstream work.

## Platform architecture

- **Model specification:** versioned schema for objective, data policy, tokenizer/representation, architecture, training, evaluation, resource limits, and user-approved constraints.
- **Configurator:** UI controls generated from schema metadata. Prefer dropdowns for discrete alternatives and sliders for bounded numeric values. Keep free-text decisions explicit and reviewable.
- **Planner:** maps the frozen spec to module contracts, dependency graph, builder cards, inspector cards, and acceptance criteria.
- **Builders:** narrowly scoped workers that create candidate modules and their artifacts.
- **Inspectors:** separate workers that verify contracts, tests, artifact identity, and evidence without approving their own builder's work.
- **Artifact registry:** stores immutable candidate versions and provenance; raw user prompts are excluded unless a separate explicit data policy permits them.
- **GitSON wiring layer:** expresses module connections; it does not itself prove compatibility. Host validation is the enforcement point.
- **Evaluation runner:** runs reproducible tests and reference comparisons and emits a report with metrics and artifact digests.
- **UI/status view:** shows decisions, module states, inspector findings, wiring readiness, test outcomes, and rebuild impact.

## NYCH V1 profile

The first profile is the NYCH language model pipeline and its bounded module set. Current owner choices include English-only V1 and accent folding of the derived trace suffix while preserving original source text. Other decisions remain explicitly pending in the NYCH decision register. A candidate module is not equivalent to a completed or integrated model.

## Acceptance principles

- The same frozen spec and pinned inputs produce traceable, reproducible build artifacts.
- Each module has a declared interface, owner, acceptance criteria, independent inspection, and versioned artifact digest.
- Invalid configurations and incompatible interfaces fail before wiring.
- Probabilistic model output is reported separately from deterministic NYCH assurance results.
- Evaluation reports expose both successful measurements and known failures; the builder does not label a model high-quality without evidence.
- New model families are added through profiles, schemas, module contracts, and evaluators rather than NYCH-specific assumptions in the core platform.
