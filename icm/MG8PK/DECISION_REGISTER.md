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
| D1 | Language and context | English-only V1; 1,024 tokenizer tokens per window; split longer accepted inputs into ordered windows, never silently truncate. | English-only approved; context pending |
| D2 / B2 | Tokenization | Owner direction: whitespace-delimited English word units with exact source byte spans; each recognized emoji grapheme is one atomic token from a versioned canonical inventory. Fold only explicit, approved non-meaning-changing variants (including skin-tone modifiers) to inventory defaults; preserve original input and offsets. Words with no faithful emoji mapping, including scientific terms and proper names, remain literal text; never force a substitute emoji. Use a versioned local statistical compendium first, ranking candidates from the prior two or three words and context; check top candidates against keyboard-layout maps second. Preserve source text and byte spans; if the original is valid/coherent or no candidate is clear, leave it literal and unresolved. | Whitespace word spans, canonical emoji, and punctuation policy approved; whitespace token representation approved; corpus source selected: complete English Wikipedia dump `enwiki-20261001` for general statistical weights, with separate technical/name lexicons and no prompt logs. Record snapshot/page provenance and honor applicable attribution/share-alike terms; keep derived artifacts private pending license review. Keyboard layout registry approved (US/UK QWERTY, AZERTY, QWERTZ; consensus required if layout unknown); automatic typo interpretation must achieve at least 99% precision on held-out cases; OOV encoding pending |
| D3 / B3 | Trace identity | English V1; accent-fold only the derived suffix and preserve original source text/bytes; remove a/e/i/o/u, retain y, and collapse adjacent repeated consonants. Reject residual non-English letters that do not accent-fold to ASCII. Structured suffix is empty for all-vowel words and displays as `∅`. Hash payload: `NYCH-WORD-ID\\0v1\\0` tag, B1 exact-input SHA-256 digest bytes, zero-based occurrence index, and source-relative start-inclusive/end-exclusive byte offsets; encode integer fields as unsigned 64-bit big-endian and emit the full lowercase SHA-256 hex. Canonical ID display: `sha256:<64-lowercase-hex>_<suffix-or-∅>`. Runtime emoji comes from the approved inventory; domain stays a separate B4 field. | Hash payload, occurrence identity, suffix policy, and ID serialization approved; B4 domain lexicon/assignment policy remains pending under D4 |
| D4 / B4 | Domain lexicon | Versioned local associative lexicon only; no LLM calls; return ranked multi-label evidence and UNKNOWN when evidence is insufficient. Owner supplies or approves seed lexicon and tie/threshold policy. If no faithful canonical symbol applies, preserve the text and return UNKNOWN/no symbol instead of substituting an emoji. | Pending lexicon/threshold choices; no-forced-symbol rule approved |
| D5 / B5 | NYCH symbolization | Apply canonical NYCH operators; preserve negation, modality, quantifiers, pronouns, predicate/argument roles, and observation/belief/intention/action distinctions. Unsupported claims remain UNKNOWN. Preserve scientific names, proper names, and other spans without a faithful emoji as literal text; emoji mapping is optional and never forced. | No-forced-emoji/pass-through rule approved; remaining NYCH semantic contract pending |
| D6 / B6 | Embeddings and position | d_model 128, learned token/symbol embeddings, RoPE, 1,024 position limit, float32 reference implementation. | Pending |
| D7 / B7 | Attention | Two causal decoder layers total, four heads, head width 32, causal mask, no KV cache in the reference build. | Pending |
| D8 / B8 | Transformer block | Pre-RMSNorm, residual connections, SwiGLU, hidden width 512, dropout 0.1 in training and off at inference. | Pending |
| D9 / B9 | Output head | Tie input/output embeddings, emit full-vocabulary logits, stable softmax, next-token cross-entropy; no hard output constraints until separately specified and tested. | Pending |
| D10 / B10 | Data and training | Owner-approved license-cleared English corpus, no prompt logs, deduplicated fixed train/validation/test split, recorded hashes/config/seed/hardware; train a standard baseline on the same split. | Pending |
| D11 | Inspector pass bar | Separate inspector per builder; exact contract match, positive/negative/boundary tests, reproducible evidence, artifact digest, and standard/reference comparison where applicable. Missing evidence = INTERMEDIATE. | Pending |
| D12 | GitSON harness | One declaration per module boundary, under 500,000 bytes; source/target IDs, interface versions, artifact digests, upstream PASS evidence; trusted host validator authorizes wiring. | Pending |

After these choices are frozen, run all isolated candidate builds and their separate inspections concurrently. Modules may use schema-matched mocks when other modules are unfinished. Merge and GitSON wiring follow the dependency graph after PASS.
