# Questions for Nick Hartman

Catalog v3.13 fills the remaining open D14, D15, and D16 fields from one public reference. D12, D13, D14, D15, and D16 are approved at catalog v3.26. D12 and D13 were already complete and were not changed. Approved decisions D0, D1-context, and D4 through D11 were not edited.

Questions 1 and 2 are answered below. Both records live on D15, which is approved at catalog v3.26. The approval covers the recorded rules. Items labeled interpreted stay interpreted. Open questions remain unresolved. Catalog v3.16 adds the owner's later clarification: keep c, use `modOp`, and write object tags as `obj_` plus the abbreviated surface token with value `gst`. Catalog v3.17 records vowel-initial words: a leading `'` replaces the initial vowel, and a doubled consonant immediately after that vowel is kept, so apple is `'ppl` and opal is `'pl`. Catalog v3.18 records the fried-apple example and the discretionary y override. Catalog v3.19 records the long-I criterion for owner-only override entries, including eye -> `'y`. Catalog v3.20 records that ie is usually a hard I and is written as y before vowels are dropped. Catalog v3.21 changes the compound join to a capitalized apostrophe, so fried apple is `fryd'Ppl`, and records field as `f"ld` and piece as `p"c`. Catalog v3.22 leaves a standalone word of three letters or fewer unchanged, so eye stays eye and the v3.19 `'y` entry is superseded and removed. Inside a compound, short parts are still abbreviated, so hot dog is `htDg`. Catalog v3.23 records an invariant tag for a domain or subdomain switch, temporary or global. Catalog v3.24 gives the spelling: `dom><` plus a token number, or `dom><global`. Catalog v3.25 recorded a temporary form `dom>N`, for example `dom>12`. Catalog v3.26 records a later owner statement. The reading that a temporary switch opens as `dom>x=food` and closes as `x=12` is an interpretation and is not owner-confirmed. D6, D8, and D10 were not edited, because those decisions are already approved.

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

### 1. Which shortening rule builds the gestalt ID? — Answered. D15 is approved at catalog v3.26. Open questions remain unresolved.

Recorded on D15 `gestalt_id_abbreviation` in catalog v3.14 and included in the catalog v3.26 approval. D6 and D8 field text was not changed. Interpreted forms stay interpreted.

Verbatim: "drop vowels and double consonants keep y and capitalize if compound with a name like Fibonacci sequence gets FbncSqnc or compounded without name gets brick layer to brkLyr or computer programmer to cmptrPrgrmr"

Interpretation, flagged as interpretation: gestalt-ID abbreviation uses the same consonant skeleton as D3 (drop a, e, i, o, u; keep y; collapse doubled consonants). Compounds are joined with no separator. A compound containing a proper name capitalizes every part (PascalCase), for example Fibonacci sequence -> FbncSqnc. A compound without a name keeps the first part lowercase and capitalizes later parts (camelCase), for example brick layer -> brkLyr and computer programmer -> cmptrPrgrmr. B3, B6, and B8 would consume this as a hard string rule once the pending field is approved.

Owner clarification, verbatim: "just dont drop the c and modOp is better and (object_k) can be (obj_k) but yes it could be (obj_bmp=gst) (obj_k=gst)". Applied to this question: do not drop c. Only vowels are dropped, and identical adjacent letters collapse. The earlier brkLyr reading of brick layer is superseded. brick layer is brckLyr. FbncSqnc and cmptrPrgrmr stay.

Owner clarification, verbatim: "any word that starts with a vowel gets an ' and if it starts with a vowel and that vowel is followed by a double dont drop the double so apple = 'ppl that distinguishes it from opal = 'pl". A vowel-initial word is prefixed with `'` in place of the dropped initial vowel. If that vowel is immediately followed by a doubled consonant, both letters of that double are kept. apple is `'ppl`. opal is `'pl`. The helper `nych_preview/gestalt_abbreviation.py` follows these clarifications and is not wired into any Builder.

Owner example, verbatim: "fried apple  fryd"ppl". Interpretation, flagged as interpretation: in a compound, a vowel-initial later part joins with `"` instead of the apostrophe, and is not capitalized (`"ppl`, not `'Ppl`).

Owner answer, verbatim: "yes i thought about it and sometimes it just makes sense to preserve the sound and not introduce vowels by using a y". Interpretation, flagged as interpretation: a y may preserve a vowel sound without introducing vowels. It is discretionary ("sometimes"), so it is not a general algorithmic rule. The helper consults `nych_preview/fixtures/gestalt-abbrev-overrides.v1.json` before the default rule. That owner-only list starts with fried -> fryd, and fried apple is `fryd"ppl`. New override entries are owner-only. The default rule is unchanged for every other word.

Owner clarification, verbatim: "do it when a hard vowel like capital I sound is needed and for like eye 'y' it makes it distinct to use the ' as an annotaion of vowel sound but not use the vowel". Interpretation, flagged as interpretation: y is written when a long-I sound, a hard I as in the pronoun I, must be preserved, as in fried -> fryd. The apostrophe annotates a vowel sound without writing the vowel, so eye is `'y`. Detecting that sound from spelling is not deterministic, so the owner-curated override list remains the mechanism. eye -> `'y` is an owner-only entry. That long-I criterion is the owner's rule for adding further entries. The default rule is unchanged.

Owner clarification, verbatim: "i before e except after c  fried   died usually the ie is a hard I sound". Interpretation, flagged as interpretation: the letter sequence ie is written as y before the normal vowel-drop, so fried is fryd and died is dyd. Usually means exceptions exist. They are owner-only overrides, and no exception entries were added. fried -> fryd is now the default rule, so fried was removed from the override list as redundant. eye -> `'y` stays.

Owner statement, verbatim: "feeld peece frend scyence those are the phonetics but reallly fld p''c so change the rule from fryd"ppl to fryd'Ppl and then the double " is a marker for two consonants in a row anywhere". Owner correction, verbatim: " denotes that there are two vowels in a row here not always or exclusively the same vowels just that there is two". The correction supersedes the two-consonants wording. Interpretation, flagged as interpretation: `p''c` means `p"c`, so piece is `p"c`. A vowel-initial later part keeps its leading `'` and is capitalized, so fried apple is `fryd'Ppl`, which supersedes `fryd"ppl`. Owner confirmation, verbatim: "yes f"ld is correct". field is `f"ld`. field -> `f"ld` and piece -> `p"c` are owner-only overrides, because ie-to-y would give fyld and pyc. The `"` marker is not a general default yet. friend and science were only the phonetics frend and scyence, so no abbreviations were added.

Owner rule, verbatim: "one rule i had a while ago was no word of three letters or less is worth symbolizing or shortening". Owner follow-up, verbatim: "no dont shorten eye i just came back up with the no shorten at 3 or below". A standalone word of three letters or fewer stays as written, so eye stays eye. The v3.19 eye -> `'y` entry is superseded and removed. Owner example, verbatim: "hot dog can be htDg". Interpretation, flagged as interpretation: the limit is for standalone words only. Parts inside a compound are still abbreviated in camelCase, so hot dog is `htDg`.

Owner example, verbatim: "hot dog can be htDg". Interpretation, flagged as interpretation: the three-letter limit is for standalone words only. Parts inside a compound are still abbreviated in camelCase, so hot dog is `htDg`.

Owner criterion, verbatim: "if the adjective is imperative to the noun as an object it gets compounded meaning if the gestalt is lost without the adjective then the adjective and noun are a noun together its an object hot dog is lost without both words and must be compounded." An adjective and noun become one object only when the gestalt is lost without the adjective. That judgment is semantic, not a spelling test, so unlisted pairs are not guessed. The owner-only list is `nych_preview/fixtures/gestalt-compounds.v1.json`. hot dog is the pair given under this criterion. Fibonacci sequence, brick layer, computer programmer, and fried apple are on that list as examples given before the criterion. The illustration that a red car stays separate is not owner-given and is not a fixture entry. Owner rationale, verbatim: "that way if we are talking about a hot dog  as in the dog is hot it can be understood distinctly with out collision". Literal hot dog, a dog that is hot, stays separate words. The compound `htDg` is the food, so the two do not collide.

Owner statement, verbatim: "domains will switch globally and inter sentence structurally many times and thats why an invariant tag for domain or subdomain switch can be helpful just to indicate whether its a temporary switch like in subject for a  sentence and overall topic domain global for a chat". An invariant interlinear tag marks a domain or subdomain switch and its scope: temporary, sentence-level, such as a subject within a sentence, versus global, the overall topic domain for the chat. Interpretation, flagged as interpretation: that scope is what disambiguates a listed compound from a literal phrase, `htDg` the food versus the separate words hot dog. Owner spelling, verbatim: "dom><folloowed by a token number or dom><global". A global switch is `dom><global`. Owner clarification, verbatim: "temp is dom>12 and lands interlinear where it occurs and the number is for tokens from that point". A temporary switch is `dom>N`, for example `dom>12`, which supersedes `dom><N`. It lands in the interlinear line where it occurs. N counts tokens from that point. The illustrations `(dom_sw=tmp)` and `(dom_sw=glb)` stay superseded and were not fixtures. No parser is implemented beyond these forms. Open: whether the tag sits inside parentheses like the other tags.

Owner statement, verbatim: "dom>?=food and after however many tokens the domain switches back or to something else the tag ?=12  where ? is any variable like x or z". Interpretation, flagged as interpretation and not owner-confirmed: this supersedes `dom>N` for a temporary switch. It opens as `dom>x=food`. The writer picks the variable, such as x or z, and the value after `=` names the target domain. Where the switch ends, the same variable closes it as `x=12`, and that number is how many tokens the switch lasted. The global form stays `dom><global`. The preview `nych_preview/domain_switch.py` only formats these strings and is not wired into any Builder. The fixture entry `domain-switch-interpreted` is marked interpreted. Open: (a) whether the closing tag sits interlinear where the switch ends, and whether 12 counts back to the opening tag; (b) whether the domain reverts to the previous one automatically at the closing tag; (c) how `dom><global` names its domain, and whether that is `dom><global=food`; (d) whether switches nest or overlap when different variables are used.

Still open: whether `obj_k`, whose k comes from a short word, is affected; whether the double-keep applies only right after the initial vowel or anywhere; a y-initial word longer than three letters; an all-vowel word longer than three letters; compounds of 3 or more parts; capitalization of a vowel-initial first part; how the `"` marker interacts with ie-to-y and the initial-vowel apostrophe beyond the stated field and piece forms; whether the domain-switch tag sits in parentheses; (a) where the closing tag sits and whether its number counts back to the opening tag; (b) whether the domain reverts automatically at the closing tag; (c) how `dom><global` names its domain; and (d) whether different variables nest or overlap. A single proper-name word and a hyphenated compound were not resolved either. friend and science still have no abbreviation.

### 2. What must a NYCH output get right before the sidecar can go? — Answered. D15 is approved at catalog v3.26. Open questions remain unresolved.

Recorded on D15 `interlinear_annotation` and included in the catalog v3.26 approval. Catalog v3.15 includes the tag addendum in that same field. D10 `verification_sidecar` was not changed. The D15 loss rule remains in place. The `dom>x=food` / `x=12` reading stays interpreted, and the open questions below stay open.

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

The full carpenter sentence, kept above this addendum, is the first interlinear test fixture (`nych_preview/fixtures/interlinear_examples.json`, entry `full-sentence`). Its verbatim annotation uses `modalityOp`. That verbatim text is kept.

Owner clarification, verbatim: "just dont drop the c and modOp is better and (object_k) can be (obj_k) but yes it could be (obj_bmp=gst) (obj_k=gst)". Canonical modality tag key is `modOp`. Object tags use the prefix `obj_` plus the object's abbreviated surface token, and the value `gst` means gestalt. Owner-confirmed examples: `(obj_bmp=gst)` for "the bump" and `(obj_k=gst)` for "k". Interpretation, flagged as interpretation: `bmp` is the consonant skeleton of bump, and `gst` abbreviates gestalt.

Normalized carpenter line, beside the verbatim `modalityOp` fixture:

```
(domain=building_subdom=carpentry)(modOp=kine-int)(past-t)
the carpenter                                               freaked  out           after               he took the bump of k.
```

Normalized form of "he took the bump of k":

```
(pronoun)(modOp=kine-ext)(obj_bmp=gst)(obj_k=gst)
he took the bump of k
```

Still open, and not decided: the exact span alignment of each tag; the tag syntax grammar; whether tense is an existing modality operator or a new tag type; whether the interlinear line persists after gestalts are picked.

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

## Emoji inventory source — owner-stated, not approved

Owner statement, recorded 2026-11-10 at 3:46 AM ET: Nick gave the emoji inventory source as https://unicode.org/emoji/charts-12.0/full-emoji-list.html (Unicode Emoji 12.0 full emoji list).

Later owner statement, verbatim, 2026-11-10 at 3:55 AM ET: "use most current version of emoticon library."

This is a stated source change. It is not an approval, and no Decision Console approval event was written. The newest file Unicode publishes at https://unicode.org/Public/emoji/latest/emoji-test.txt is version 18.0. There is no numbered `/Public/emoji/18.0/` directory; that `latest` file is the released data, and its header says version 18.0. The chart at https://unicode.org/emoji/charts/full-emoji-list.html is titled Full Emoji List, v18.0. Both were retrieved on 2026-11-10. The inventory keeps fully-qualified code points, the CLDR short name, and the group and subgroup. Skin-tone sequences are their own fully-qualified rows and are not folded. It does not assign a NYCH gestalt. Version 18.0 is the same version already named by the approved D6 endpoint.

## Proper-name rule — owner-stated, not approved

Owner statement, verbatim, 2026-11-10 at 3:56 AM ET: "or easy rule instead of a list of names \"If it begins with a capital letter and isnt in the dictionary, its a name\"".

This stated rule replaces the pending Wikidata names list. It is not an approval, and no Decision Console approval event was written. The earlier builder card still describes a Wikidata candidate list; that card was not rewritten, because this statement is not an approval.

The repo has no English dictionary file. It has the domain taxonomy `icm/MG8PK/lexicons/nych-professional-domain-taxonomy.md` and a specified but absent Wikipedia dump. Neither is selected here as the dictionary in question (a).

Owner answer, verbatim, 2026-11-10 at 4:02 AM ET: "first word of a sentence should be in the dictionary. Names that are ordinary words will be capitalized mid sentence and names that are also common words and are the first word in a sentence will be subject to gestalt translation but it will not matter as ling as the name is preserved like the case of apple  if that was someones name".

This answer is owner-stated. It is not an approval, and no Decision Console approval event was written.

Interpretation, flagged as interpretation: (b) a sentence-initial capitalized word that is in the dictionary is an ordinary word, not a name. If it is not in the dictionary, the base rule applies. (c) a mid-sentence capitalized word is a name even when it is also a dictionary word, such as Apple or Rose. A sentence-initial name that is also a common word goes through ordinary gestalt translation. The owner accepts that, provided the original surface form, the name itself, is preserved.

Owner answer, verbatim, 2026-11-10 at 4:04 AM ET: "Acronyms are all caps and excluded from gestalting. Miriam Websters dictionary and websters Crossword dictionary".

This answer is owner-stated. It is not an approval, and no Decision Console approval event was written.

Interpretation, flagged as interpretation: the dictionary is Merriam-Webster's dictionary plus Merriam-Webster's crossword dictionary. The owner wrote "Miriam Websters" and "websters Crossword". A word that is all capitals and at least two letters long is an acronym. Acronyms keep their surface form and are excluded from gestalting.

(a) stays provisional. A check on 2026-11-10 of https://dictionaryapi.com/ found a per-word JSON lookup, not a downloadable headword list. The published non-commercial terms allow 1,000 queries a day for each API key and reference, and at most two references, after registering an account and confirming email. Those terms forbid automated or recorded queries unless Merriam-Webster approves them in writing, and they forbid copying the service. A key and a written license would be required before any lookup is wired. Merriam-Webster's Crossword Puzzle Dictionary is sold as a print book and a Kindle book. No official machine-readable word list or API for that book was found. No dictionary text was downloaded or committed.

(d) is answered by the statement above. The smoke step treats those all-caps words as interpreted acronyms.

The smoke step `nych_smoke/proper_names.py` remains provisional for dictionary membership. A mid-sentence capitalized word that is not all-caps is an interpreted name. A sentence-initial capitalized word that is not all-caps stays undecided because no dictionary file is in hand. An acronym is not gestalted, and its surface form is left as written.

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
