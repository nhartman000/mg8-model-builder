# Owner Decision Register (generated projection, OFFLINE PROTOTYPE)

Decision-set digest: `sha256:7e151d9afae7a8e02d59493dcb70a2254f3cf40e73789b11117aedffcf7c4068`

Generated from the decision event log. Do not edit by hand. Readiness below is advisory, not authoritative.

| ID | Title | State | Contract | Value | Recommended | Head event |
|---|---|---|---|---|---|---|
| D0 | Model objective | PENDING (Recommended—awaiting owner approval) | complete |  | {"assurance_separation": "symbolic assurance results kept distinct from probabilistic output", "encoder": "deterministic NYCH encoder", "model_family": "tiny decoder-only causal LM", "prediction_target": "next NYCH token/symbol sequence"} |  |
| D1-context | Context window | PENDING (Recommended—awaiting owner approval) | complete |  | {"overflow_policy": "split_into_ordered_windows", "truncation": "never", "window_tokens": 1024} |  |
| D4 | Domain lexicon seed and thresholds | PENDING (owner input required) | INCOMPLETE: confidence_threshold, seed_lexicon, tie_policy |  |  |  |
| D5 | GST context assembly and lookup | APPROVED | complete | {"gst_format": "versioned GST JSON", "lookup": "exact canonical domain_id + action_key; ambiguity is cache miss", "origin_policy": "HUMAN_AUTHORED automatic structural/invariant validation; HOW_TO_EXTRACTED requires matching human approval; unknown origins fail closed", "storage": "Additive TOTE SQLite v2 (migration 002)", "user_version": 2} | {"gst_format": "versioned GST JSON", "lookup": "exact canonical domain_id + action_key; ambiguity is cache miss", "origin_policy": "HUMAN_AUTHORED automatic structural/invariant validation; HOW_TO_EXTRACTED requires matching human approval; unknown origins fail closed", "storage": "Additive TOTE SQLite v2 (migration 002)", "user_version": 2} | sha256:68384464cd51 |
| D6 | Symbol-selection call contract | PENDING (owner input required) | INCOMPLETE: endpoint, request_response_schema, tote_write_policy |  |  |  |
| D7 | Embeddings and position | PENDING (Recommended—awaiting owner approval) | complete |  | {"d_model": 128, "dtype": "float32", "embeddings": "learned_token_symbol", "position_limit": 1024, "positional_encoding": "RoPE"} |  |
| D8 | Attention | PENDING (Recommended—awaiting owner approval) | complete |  | {"head_width": 32, "heads": 4, "kv_cache": "none_in_reference", "layers": 2, "mask": "causal", "model_width": 128} |  |
| D9 | Transformer block | PENDING (Recommended—awaiting owner approval) | complete |  | {"dropout_inference": 0.0, "dropout_training": 0.1, "ffn": "SwiGLU", "ffn_hidden_width": 512, "norm": "pre_rmsnorm", "residual": "yes"} |  |
| D10 | Output head | PENDING (Recommended—awaiting owner approval) | complete |  | {"hard_output_constraints": "none_until_specified", "logits": "full_vocabulary", "loss": "next_token_cross_entropy", "softmax": "numerically_stable", "tied_embeddings": "yes"} |  |
| D11 | Neural corpus and training | PENDING (owner input required) | INCOMPLETE: corpus, license_review |  |  |  |
| D12 | Inspector evidence bar | PENDING (Recommended—awaiting owner approval) | complete |  | {"bar": "separate Inspector per Builder; exact contract match; positive/negative/boundary/adversarial cases; reproducible evidence; exact digest; reference comparison where applicable", "missing_evidence": "INTERMEDIATE"} |  |
| D13 | GitSON contract/runtime | PENDING (owner input required) | INCOMPLETE: schema_validator_runtime |  |  |  |
| D14 | Tiny-model size and resource budget | PENDING (owner input required) | INCOMPLETE: memory_latency_target, parameter_band, training_hardware |  |  |  |
| D15 | Benchmark and success criteria | PENDING (owner input required) | INCOMPLETE: thresholds |  |  |  |
| D16 | Packaging/release target | PENDING (owner input required) | INCOMPLETE: format, runtime_device |  |  |  |

## Blocked modules (advisory)

- B1: CONTRACT_NOT_MODELED_IN_CONSOLE, D12
- B2: CONTRACT_NOT_MODELED_IN_CONSOLE, D1-context, D12
- B3: CONTRACT_NOT_MODELED_IN_CONSOLE, D12
- B4: D12, D4
- B5: D12, D4
- B6: D12, D6
- B7: D0, D1-context, D12, D14, D7
- B8: D0, D1-context, D12, D14, D7, D8
- B9: D0, D1-context, D12, D14, D7, D8, D9
- B10: D0, D1-context, D10, D12, D14, D7, D8, D9
- B11: D0, D1-context, D10, D11, D12, D14, D15, D16, D7, D8, D9
- INTEGRATION: D12, D13
