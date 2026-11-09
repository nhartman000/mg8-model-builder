# Questions for Nick Hartman

Catalog v3.13 fills the remaining open D14, D15, and D16 fields from one public reference. Those values are recommendations. They are not approvals. D12 and D13 were already complete and were not changed. Approved decisions D0, D1-context, and D4 through D11 were not edited.

Questions 1 and 2 are answered below. Question 1 is stored on pending D15 `gestalt_id_abbreviation` in catalog v3.14. Question 2, including the later tag addendum, is stored on the same pending field `interlinear_annotation`, now in catalog v3.15. D6, D8, and D10 were not edited, because those decisions are already approved.

The reference is Ronen Eldan and Yuanzhi Li, TinyStories (2023), https://arxiv.org/abs/2305.07759, plus the float32 checkpoint configs at https://huggingface.co/roneneldan/TinyStories-1M/raw/main/config.json and https://huggingface.co/roneneldan/TinyStories-2Layers-33M/raw/main/config.json. It supplies a small-model training scale, a single-V100 hardware class, float32 packaging, and the practice of tracking evaluation loss separately from other scores. It does not supply NYCH symbol rules.

## Where the reference answers were applied

These do not need an owner answer unless the recommendation should be rejected.

| Field | Applied to | Manner |
|---|---|---|
| D14.parameter_band | B7, B8, B9, B10, B11 | Starting size band. Non-embedding count 524928 uses the approved shape (width 128, 2 layers, 4 heads, head width 32, SwiGLU width 512, RoPE, tied embeddings) and stated assumptions (no linear bias, RMSNorm scale only, two pre-norms per layer, one final RMSNorm, zero RoPE parameters). Vocabulary is not frozen, so the band is 1804928 parameters at 10000 tokens and 6957824 parameters at 50257 tokens. Those two vocab sizes are the paper's top-10K note and the published config `vocab_size`. |
| D14.memory_latency_target | B7 through B11, especially B11 | Starting memory budget. Float32 weights are 7219712 or 27831296 bytes at the two ends. Float32 Adam, excluding activations, is 28878848 or 111325184 bytes. No millisecond target and no KV cache, because the paper publishes neither a latency number nor a cache, and D8 already says the reference has no KV cache. Wall-clock class: one V100, at most 30 hours, for models in the paper's about 1M to 35M range. |
| D14.training_hardware | B11 | Starting device class: one NVIDIA V100. Not a measured NYCH run. |
| D15.thresholds | B11, and the D10 sidecar kept until the rule passes | Starting deletion rule for owner review, not a number from the paper. Keep the unmodified companion until the mixed path's validation cross-entropy is at most 1.05 times the companion on the same held-out documents for 3 consecutive evaluations. Report perplexity separately. Do not treat the loss rule as the definition of a correct NYCH string. The unchanged D15.reporting field still says to report each measure separately against a standard baseline. |
| D16.format | B11 packaging | Starting package shape: private float32 weights plus a JSON config of the approved NYCH shape, the real vocabulary size, the count assumptions, and the catalog digest. Not a GPT-Neo file. D16.visibility stays `private_until_explicit_release`. |
| D16.runtime_device | B11 | Starting runtime: one V100-class GPU, float32, no KV cache. |

## Questions only the owner can answer

A reference model cannot answer these. Approved choices are not asked again. That includes the D4 tie policy, the D6 symbol-selection contract, the D8 30/30/20/20 starting mix, the Common Corpus choice, and the approved layer widths.

### 1. Which shortening rule builds the gestalt ID? — Answered, not approved

Recorded on pending D15 `gestalt_id_abbreviation` in catalog v3.14. D6 and D8 field text was not changed.

Verbatim: "drop vowels and double consonants keep y and capitalize if compound with a name like Fibonacci sequence gets FbncSqnc or compounded without name gets brick layer to brkLyr or computer programmer to cmptrPrgrmr"

Interpretation, flagged as interpretation: gestalt-ID abbreviation uses the same consonant skeleton as D3 (drop a, e, i, o, u; keep y; collapse doubled consonants). Compounds are joined with no separator. A compound containing a proper name capitalizes every part (PascalCase), for example Fibonacci sequence -> FbncSqnc. A compound without a name keeps the first part lowercase and capitalizes later parts (camelCase), for example brick layer -> brkLyr and computer programmer -> cmptrPrgrmr. B3, B6, and B8 would consume this as a hard string rule once the pending field is approved.

Further interpretation, flagged because identical-letter collapse alone yields brckLyr: the preview helper also treats the adjacent digraph ck as a doubled consonant and keeps k. That step is not a rule for any other digraph. The helper is `nych_preview/gestalt_abbreviation.py`. It is not wired into any Builder.

Still open, and not decided: a single proper-name word (Fibonacci alone -> Fbnc?); a word starting with a vowel (apple -> ppl?); all-vowel words; hyphenated compounds; compounds of 3 or more parts.

### 2. What must a NYCH output get right before the sidecar can go? — Answered, not approved

Recorded on pending D15 `interlinear_annotation`. Catalog v3.15 includes the tag addendum in that same field. D10 `verification_sidecar` was not changed. The D15 loss rule remains in place.

Verbatim: "what I would like is a sort of info tree to exist interlinear so before gestalts are picked the nych output is still words but the info exists above in a sub-line interlinear style."

Example given:

```
(domain=building_subdom=carpentry)(modalityOp=kine-int)(past-t)
the carpenter                                               freaked  out           after               he took the bump of k.
```

Interpretation, flagged as interpretation, alignment unconfirmed by the owner: before gestalt selection, NYCH output is the original words on a base line, and an interlinear annotation line above carries span-aligned tags. In the example, domain=building and subdom=carpentry are read over "the carpenter", modalityOp=kine-int over "freaked out", and past-t possibly over "after" or over the clause. Structural checks for the sidecar should test this interlinear structure. B10 and B11 would apply those checks once the pending field is approved.

Module reading, interpretation only: B4 would produce the domain and subdomain tags; B5 or B6 would produce modalityOp from the TOTE modality operator; the source of tense (past-t) is unknown.

Owner addendum, confirmed: "he took the bump of k" also gets tags. Verbatim example:

```
(pronoun)(modOp=kine-ext)(object=gestalt)(object_k=gestalt)
he took the bump of k
```

Interpretation, flagged as interpretation: "he" maps to (pronoun); "took" maps to (modOp=kine-ext); "the bump" maps to (object=gestalt); "k" maps to (object_k=gestalt).

The full carpenter sentence, kept above this addendum, is the first interlinear test fixture (`nych_preview/fixtures/interlinear_examples.json`, entry `full-sentence`).

Still open, and not decided: the exact span alignment of each tag on the full sentence; the tag syntax grammar; whether tense is an existing modality operator or a new tag type; whether the interlinear line persists after gestalts are picked. The owner used both `modalityOp=` and `modOp=`; which spelling is canonical is open. `object_k` appears to name the object by its surface token; whether that is the convention is open.

### 3. What is the technical and scientific lexicon source?

The decision register and the B2 card leave the technical/scientific lexicon source pending. Wikipedia and Wikidata are already assigned to other lexicons.

Only the owner can name that source.

Consumed by the B2 lexicon set. It is outside the D14–D16 fields.

Applied as a hard source pointer for candidate lookup. It does not change the neural width.

### 4. Which corpus is the typo-statistics corpus?

D11 says the neural corpus stays distinct from the typo-statistics corpus and does not name that second corpus.

Only the owner can name it.

Consumed by D11 `corpus` as a separation constraint, and by B2 for typo statistics versus B11 for neural training.

Applied as a hard data-separation rule. The two corpora must not be mixed.

### 5. What shows that a domain lexicon has stabilized?

D8 says abbreviated words stay primary until dynamic domain lexicons have stabilized, and it sets no numeric threshold. The 30/30/20/20 mix is already the starting point to retune on natural language, so this question does not ask for a replacement mix.

Only the owner can say which observable counts as stabilized: a repetition count, a signed lexicon version, or a direct owner mark.

Consumed by D8 `primacy_tradeoff`, in B8.

Applied as the stop condition for the primacy switch. Until it exists, abbreviated words stay primary. It is not a new width or learning rate.

### 6. Which modality operators are closed for V1?

D6 says modality operators are invariant, and B5 reads them from the TOTE `modality_operators` table. The table's V1 membership is not restated as a closed list in this repository.

Only the owner can say whether that table is already the closed V1 set, or which operators are still missing.

Consumed by D6 `tote_write_policy` and the B5 GST contract, in B5 and B6.

Applied as a hard closed set. Builders must not invent an operator.

## What each module does

These lines are taken from the worker and inspector cards in this repository.

- **B1** Ingest. Validate strict UTF-8 bytes, enforce the approved 65,536-byte ceiling, hash original bytes, emit metadata, and return accepted text only in request memory. (`icm/MG8PK/workers/builder-01.md`)
- **B2** Tokenization. Use whitespace boundaries to identify English surface-word spans, preserve exact UTF-8 source byte offsets, and emit punctuation, whitespace, and recognized emoji graphemes as tokens from the versioned lexicon. (`icm/MG8PK/workers/builder-02.md`)
- **B3** Trace identity. Assign occurrence-level trace identity to one word span at a time and generate the consonant-skeleton suffix. (`icm/MG8PK/workers/builder-03.md`)
- **B4** Domain resolution. Resolve lexical spans with a versioned local associative lexicon, return evidence and ambiguity, and support UNKNOWN without an LLM call. (`icm/MG8PK/workers/builder-04.md`)
- **B5** GST context. Own the request-scoped global `.gst` artifact, query the TOTE-loops database, and deliver that GST together with, and distinct from, the complete source prompt. (`icm/MG8PK/workers/builder-05.md`)
- **B6** Symbolization. Consume the GST, database matches or cache-miss markers, and the separate complete natural-language prompt, and select canonical emoji gestalts only where faithful, preserving literal text otherwise. (`icm/MG8PK/workers/builder-06.md`)
- **B7** Embeddings and position. Implement learned embedding tables and the approved positional encoding with explicit tensor, serialization, and bounds contracts. (`icm/MG8PK/workers/builder-07.md`)
- **B8** Attention. Implement the approved causal multi-head self-attention module with a declared tensor contract and numerical behavior. (`icm/MG8PK/workers/builder-08.md`)
- **B9** Transformer block. Implement the approved normalization, residual, and feed-forward block with shape and gradient continuity. (`icm/MG8PK/workers/builder-09.md`)
- **B10** Output head. Project hidden states to vocabulary logits and compute stable probabilities and loss under the approved vocabulary contract. (`icm/MG8PK/workers/builder-10.md`)
- **B11** Training and evaluation. Produce a reproducible data manifest, training recipe, baseline comparison, evaluation report, and versioned package manifest. (`icm/MG8PK/workers/builder-11.md`)
- **INTEGRATION** Wiring. Integration and GitSON wiring respect dependency edges and require PASS evidence. An Inspector report does not authorize wiring; the trusted host gate must validate the result and GitSON handoff. (`icm/MG8PK/WORKER_SPECIFICATIONS.md`, `icm/MG8PK/inspectors/inspector-01.md`)
