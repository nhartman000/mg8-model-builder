# Owner Decision Register (generated projection, OFFLINE PROTOTYPE)

Decision-set digest: `sha256:fb72df90b3f8f6d40599f55e3d2732425f028de6f09f4f9cd551ffa502e3fc10`

Generated from the decision event log. Do not edit by hand. Readiness below is advisory, not authoritative.

| ID | Title | State | Contract | Value | Recommended | Head event |
|---|---|---|---|---|---|---|
| D0 | Model objective | APPROVED | complete | {"assurance_separation": "symbolic assurance results kept distinct from probabilistic output", "encoder": "deterministic NYCH encoder", "model_family": "tiny decoder-only causal LM", "prediction_target": "next NYCH token/symbol sequence"} | {"assurance_separation": "symbolic assurance results kept distinct from probabilistic output", "encoder": "deterministic NYCH encoder", "model_family": "tiny decoder-only causal LM", "prediction_target": "next NYCH token/symbol sequence"} | sha256:d738cb0d586c |
| D1-context | Context window | APPROVED | complete | {"overflow_policy": "split_into_ordered_windows", "truncation": "never", "window_tokens": 1024} | {"overflow_policy": "split_into_ordered_windows", "truncation": "never", "window_tokens": 1024} | sha256:c7f6907b34fb |
| D4 | Domain lexicon seed and thresholds | PENDING (Recommended—awaiting owner approval) | complete |  | {"confidence_rule": "A 100% letter-for-letter match equals confidence 10 (100%). If one to three letters are off, and those differences are likely suffixes \\"ing\\", \\"ion\\", \\"ed\\", or \\"er\\", confidence remains high at 80–85%. After that, confidence of 75% or lower is unacceptable and results in writing unresolved domain. A confidence at or below 0.75 writes unresolved domain.", "confidence_threshold": 0.75, "method": "versioned local associative lexicon; no LLM calls; ranked multi-label evidence; if unresolvable, write unresolved domain; no forced symbol", "rule_module": "The actual rules for domain decisions will be an extensive module needing expansion, and will be an entire evening of work one day. For now, the current rule and lists will suffice. If unresolvable, write unresolved domain.", "scoring_rubric": "The professional TLD list at https://tld-list.com/tld-categories/professional is primary. If a domain exists on that list, it is domain-specific and tied to that .domain extension; a host of websites therefore exist from which terminology and structures can be extracted easily. If the domain is not part of the professional domain list, fall back to the attached NYCH taxonomy lexicon committed at icm/MG8PK/lexicons/nych-professional-domain-taxonomy.md. That lexicon will be updated with every proper NYCH update.", "seed_lexicon": "The professional TLD list at https://tld-list.com/tld-categories/professional is primary. If a domain exists on that list, it is domain-specific and tied to that .domain extension; a host of websites therefore exist from which terminology and structures can be extracted easily. If the domain is not part of the professional domain list, fall back to the attached NYCH taxonomy lexicon committed at icm/MG8PK/lexicons/nych-professional-domain-taxonomy.md. That lexicon will be updated with every proper NYCH update.", "tie_policy": "In the strange case of matching — a tie, when two or more domains receive the same score — include both (or all tied domains) and do not prune either domain. Instead use both as possible root domains and reason within both."} |  |
| D5 | GST context assembly and lookup | APPROVED | complete | {"existing_db_migration_002": "deferred; not applied to an existing database", "gst_format": "versioned GST JSON", "gst_schema_path": "nych-language-model/schemas/gst-context-v1.schema.json", "gst_scope": "request-scoped", "gst_source_of_truth": "nych-language-model/src/nych_language_model/pipeline/gst_context.py", "lookup": "exact canonical domain_id + action_key; ambiguity is cache miss", "migration_002_conformance_tests": "deferred; not run", "origin_policy": "HUMAN_AUTHORED automatic structural/invariant validation; HOW_TO_EXTRACTED requires matching human approval; unknown origins fail closed", "storage": "Additive TOTE SQLite v2 (migration 002)", "user_version": 2} | {"existing_db_migration_002": "deferred; not applied to an existing database", "gst_format": "versioned GST JSON", "gst_schema_path": "nych-language-model/schemas/gst-context-v1.schema.json", "gst_scope": "request-scoped", "gst_source_of_truth": "nych-language-model/src/nych_language_model/pipeline/gst_context.py", "lookup": "exact canonical domain_id + action_key; ambiguity is cache miss", "migration_002_conformance_tests": "deferred; not run", "origin_policy": "HUMAN_AUTHORED automatic structural/invariant validation; HOW_TO_EXTRACTED requires matching human approval; unknown origins fail closed", "storage": "Additive TOTE SQLite v2 (migration 002)", "user_version": 2} | sha256:8916be3481d2 |
| D6 | Symbol-selection call contract | PENDING (owner input required) | INCOMPLETE: tote_write_policy |  |  |  |
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

## Cross-decision constraints

- D1-context.window_tokens = D7.position_limit
- D7.d_model = D8.model_width

## Numeric bounds (current catalog)

- D1-context.window_tokens: minimum 1, maximum null, step 1
- D4.confidence_threshold: minimum 0, maximum 1, step null
- D5.user_version: minimum 2, maximum 2, step 1
- D7.d_model: minimum 1, maximum null, step 1
- D7.position_limit: minimum 1, maximum null, step 1
- D8.layers: minimum 1, maximum null, step 1
- D8.heads: minimum 1, maximum null, step 1
- D8.head_width: minimum 1, maximum null, step 1
- D8.model_width: minimum 1, maximum null, step 1
- D9.ffn_hidden_width: minimum 1, maximum null, step 1
- D9.dropout_training: minimum 0, maximum 1, step null
- D9.dropout_inference: minimum 0, maximum 1, step null
- D13.max_bytes_exclusive: minimum 1, maximum 500000, step 1

## Blocked modules (advisory)

- B1: CONTRACT_NOT_MODELED_IN_CONSOLE, D12
- B2: CONTRACT_NOT_MODELED_IN_CONSOLE, D12
- B3: CONTRACT_NOT_MODELED_IN_CONSOLE, D12
- B4: D12, D4
- B5: D12, D4
- B6: D12, D6
- B7: D12, D14, D7
- B8: D12, D14, D7, D8
- B9: D12, D14, D7, D8, D9
- B10: D10, D12, D14, D7, D8, D9
- B11: D10, D11, D12, D14, D15, D16, D7, D8, D9
- INTEGRATION: D12, D13
