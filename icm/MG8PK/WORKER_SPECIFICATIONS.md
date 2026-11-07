# Builder and Inspector roster

The individual role cards are under `workers/` and `inspectors/`. Each Builder works only on its numbered module in the NYCH model repository. Each Inspector independently reviews the exact candidate digest. No worker is represented as a running job.

| Pair | Module | NYCH repository path |
|---|---|---|
| B1 / I1 | Ingest | `src/nych_language_model/pipeline/ingest.py` |
| B2 / I2 | Tokenization | `src/nych_language_model/pipeline/tokenization.py` |
| B3 / I3 | Trace identity and consonant skeleton | `src/nych_language_model/pipeline/trace_identity.py` |
| B4 / I4 | Deterministic domain resolution | `src/nych_language_model/pipeline/domain_resolution.py` |
| B5 / I5 | GST context assembly and domain/action database lookup | `src/nych_language_model/pipeline/gst_context.py` |
| B6 / I6 | NYCH symbolization and invariants | `src/nych_language_model/pipeline/nych_symbolization.py` |
| B7 / I7 | Embeddings and position | `src/nych_language_model/model/embeddings.py` |
| B8 / I8 | Causal self-attention | `src/nych_language_model/model/attention.py` |
| B9 / I9 | Transformer block | `src/nych_language_model/model/transformer_block.py` |
| B10 / I10 | Output projection and softmax | `src/nych_language_model/model/output_head.py` |
| B11 / I11 | Training, evaluation, packaging | `src/nych_language_model/training/` |

## Parallelism and integration

Builders can implement independently in parallel after shared contracts are frozen. A missing upstream implementation does not block a candidate if the Builder uses contract-conforming mocks. Inspectors review each candidate separately. Integration and GitSON wiring respect dependency edges and require PASS evidence.

Every Builder returns source, focused tests, interface/version information, dependencies, artifact digest, and a short evidence report. Raw user prompts are prohibited in artifacts, tests, logs, reports, and QSON.
