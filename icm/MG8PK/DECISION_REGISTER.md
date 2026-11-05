# NYCH Language Model V1 — Owner Decision Register

Reply with “accept recommended defaults except D#…” or specify replacements. These choices freeze the contracts before all module builders are launched concurrently.

## Approved

- Ingest accepts UTF-8 bytes up to 65,536 bytes; it rejects empty, malformed, or oversized input without normalization or truncation.
- Raw prompt text remains in request memory only. Never persist it or include it in QSON. QSON may contain digest and metadata only.
- Candidate builds and independent inspections run in parallel against frozen contracts. Integration is dependency-gated.
- Weight pruning is deferred to Builder Pro V2.
- GitHub repositories were created private; public release is not implied.

## Decisions required

| ID | Choice | Recommended default | Status |
|---|---|---|---|
| D0 | Model objective | Deterministic NYCH encoder plus tiny decoder-only causal LM predicting the next NYCH token/symbol sequence. Keep symbolic assurance results distinct from probabilistic output. | Pending |
| D1 | Language and context | English V1; 1,024 tokenizer tokens per window; split longer accepted inputs into ordered windows, never silently truncate. | Pending |
| D2 / B2 | Tokenization | Byte-level BPE; 8,192 vocabulary; no normalization; preserve byte offsets; explicit special-token registry and versioned tokenizer artifact. | Pending |
| D3 / B3 | Trace identity | SHA-256 per word occurrence, followed by a vowel-stripped consonant skeleton with adjacent repeated consonants collapsed. Domain remains a separate B4 field. Decide exact vowel set, case, delimiters, and occurrence identity inputs. | Pending |
| D4 / B4 | Domain lexicon | Versioned local associative lexicon only; no LLM calls; return ranked multi-label evidence and UNKNOWN when evidence is insufficient. Owner supplies or approves seed lexicon and tie/threshold policy. | Pending |
| D5 / B5 | NYCH symbolization | Apply canonical NYCH operators; preserve negation, modality, quantifiers, pronouns, predicate/argument roles, and observation/belief/intention/action distinctions. Unsupported claims remain UNKNOWN. | Pending |
| D6 / B6 | Embeddings and position | d_model 128, learned token/symbol embeddings, RoPE, 1,024 position limit, float32 reference implementation. | Pending |
| D7 / B7 | Attention | Two causal decoder layers total, four heads, head width 32, causal mask, no KV cache in the reference build. | Pending |
| D8 / B8 | Transformer block | Pre-RMSNorm, residual connections, SwiGLU, hidden width 512, dropout 0.1 in training and off at inference. | Pending |
| D9 / B9 | Output head | Tie input/output embeddings, emit full-vocabulary logits, stable softmax, next-token cross-entropy; no hard output constraints until separately specified and tested. | Pending |
| D10 / B10 | Data and training | Owner-approved license-cleared English corpus, no prompt logs, deduplicated fixed train/validation/test split, recorded hashes/config/seed/hardware; train a standard baseline on the same split. | Pending |
| D11 | Inspector pass bar | Separate inspector per builder; exact contract match, positive/negative/boundary tests, reproducible evidence, artifact digest, and standard/reference comparison where applicable. Missing evidence = INTERMEDIATE. | Pending |
| D12 | GitSON harness | One declaration per module boundary, under 500,000 bytes; source/target IDs, interface versions, artifact digests, upstream PASS evidence; trusted host validator authorizes wiring. | Pending |

After these choices are frozen, run all isolated candidate builds and their separate inspections concurrently. Modules may use schema-matched mocks when other modules are unfinished. Merge and GitSON wiring follow the dependency graph after PASS.
