# Owner Decision Register (generated projection)

Decision-set digest: `sha256:90c863b54e27fd29d2e9f4a45b3c9ec97c4636cf54e01a05065fedfc071cdbe4`

Generated from the decision event log. Do not edit by hand.

| ID | Title | State | Value | Recommended | Head event |
|---|---|---|---|---|---|
| D0 | Model objective | PENDING (Recommended—awaiting owner approval) |  | "Deterministic NYCH encoder plus tiny decoder-only causal LM; symbolic assurance kept distinct from probabilistic output." |  |
| D1-context | Context window | PENDING (Recommended—awaiting owner approval) |  | 1024 |  |
| D4 | Domain lexicon seed and thresholds | PENDING (Recommended—awaiting owner approval) |  | "Owner-supplied versioned local associative lexicon; thresholds to be specified; UNKNOWN when uncertain." |  |
| D5 | GST context assembly and lookup | APPROVED | "Additive TOTE SQLite v2; user_version=2; exact domain_id + action_key lookup; ambiguity is cache miss; versioned GST JSON; unknown origins fail closed." | "Additive TOTE SQLite v2; user_version=2; exact domain_id + action_key lookup; ambiguity is cache miss; versioned GST JSON; unknown origins fail closed." | sha256:83a492c414f4 |
| D6 | Symbol-selection call contract | PENDING (Recommended—awaiting owner approval) |  | "GST and prompt as separate inputs; literal fallback; no TOTE write-back until write/admission contract approved." |  |
| D7 | Embedding width (d_model) | PENDING (Recommended—awaiting owner approval) |  | 128 |  |
| D8 | Attention heads | PENDING (Recommended—awaiting owner approval) |  | 4 |  |
| D9 | SwiGLU hidden width | PENDING (Recommended—awaiting owner approval) |  | 512 |  |
| D10 | Output head | PENDING (Recommended—awaiting owner approval) |  | "Tied embeddings, full-vocabulary logits, stable softmax, next-token cross-entropy." |  |
| D11 | Neural corpus and training | PENDING (Recommended—awaiting owner approval) |  | "Owner-approved license-cleared corpus; dedup; fixed split; no prompts; recorded seeds/config/hardware; baseline on same split." |  |
| D12 | Inspector evidence bar | PENDING (Recommended—awaiting owner approval) |  | "Separate Inspector per Builder; missing evidence means INTERMEDIATE." |  |
| D13 | GitSON contract/runtime | PENDING (Recommended—awaiting owner approval) |  | "Interface-versioned per-boundary GitSON; exact artifact and upstream PASS digests; trusted host validation; <500,000 bytes." |  |
| D14 | Tiny-model size and resource budget | PENDING (Recommended—awaiting owner approval) |  | "OWNER INPUT REQUIRED: no numeric size is assumed." |  |
| D15 | Benchmark and success criteria | PENDING (Recommended—awaiting owner approval) |  | "Report each measure separately against a standard baseline; thresholds owner-set." |  |
| D16 | Packaging/release target | PENDING (Recommended—awaiting owner approval) |  | "Private until an explicit release decision; format owner-set." |  |

## Blocked modules

- ALL: waiting on D12
- B10: waiting on D0, D1-context, D10, D14, D7, D8, D9
- B11: waiting on D0, D1-context, D10, D11, D14, D15, D16, D7, D8, D9
- B2: waiting on D1-context
- B4: waiting on D4
- B6: waiting on D6
- B7: waiting on D0, D1-context, D14, D7
- B8: waiting on D0, D1-context, D14, D7, D8
- B9: waiting on D0, D1-context, D14, D7, D8, D9
- INTEGRATION: waiting on D12, D13
