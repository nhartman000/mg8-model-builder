# Statistical Compendium Index — V1 Design

## Purpose

Provide deterministic, local statistical evidence for word continuation and typo interpretation. The compendium is an aggregate index built from a versioned, licensed corpus. It is not a runtime LLM and does not retain user prompts.

## Recommended storage

Use a versioned SQLite database for runtime lookup, with a small JSON manifest alongside it. Owner-approved corpus composition: a general English corpus plus separate technical/scientific and name lexicons; never use prompt logs. Owner-selected source: the complete English Wikipedia dump `enwiki-20261001` for general English weights. This was the latest complete dump identified on 2026-11-07; the `20261101` dump was still in progress. Use article namespace only, preserve snapshot/page/revision provenance, and follow applicable attribution/share-alike conditions. Keep derived artifacts private until license review clears intended distribution. Technical/name lexicons remain separate and versioned. No prompt logs are permitted. See `WIKIPEDIA_CORPUS_PROVENANCE_V1.md` for the source record and controls. SQLite provides indexed key lookups and deterministic local access; the manifest binds the weights to their source and build procedure.

### Candidate lexicon composition

The owner approved a general English candidate-lexicon seed derived from the same `enwiki-20261001` snapshot: article text vocabulary plus page titles and redirects. Keep proper-name and technical/scientific lexicons as separate versioned layers. The proper-name lexicon covers people, places, organizations, and similar entities. Wikidata is the approved versioned master candidate source: extract English labels and aliases from a dated weekly JSON entity dump, include entities classified as people, places, organizations, and comparable named-entity classes; retain QID, entity type, dump date, and source provenance. Do not admit unclassified items as confirmed proper-name entries; leave them unresolved. Wikidata structured data is CC0. If a surface form maps to multiple QIDs, preserve every candidate QID, type, and provenance; do not infer identity from the name alone. D2 emits all candidate QIDs and the unresolved status. Defer contextual identity resolution to a separate later stage. Resolve only if the one-sided 95% Clopper–Pearson lower confidence bound for held-out identity-resolution precision is at least 99%; otherwise leave identity unresolved. Evaluate this gate separately from typo correction. Candidate matches do not establish identity and the lexicon is not claimed to be exhaustive. Wikipedia article titles and redirects alone do not establish proper-name membership. For this proper-name type filter, classification method is approved: use P31 (instance of), follow P279 (subclass of) links to a versioned allowlist of accepted root classes with cycle-safe traversal, and leave items without a supported path unresolved. Approved root classes for V1 are human Q5, organization Q43229, organization unit Q10387680, geographic location Q2221906, and geographical feature Q618123. Additional approved roots are occurrence Q1190554, creative work Q17537576, product Q2424752, brand Q431289, and character Q95074. Further root classes remain open; the technical/scientific lexicon source remains pending. This is entity-type filtering only; it is not NYCH D4 domain mapping. This candidate lexicon is not claimed to be a complete dictionary. Missing entries remain representable through the approved internal UTF-8 byte fallback. Apply the same corpus provenance and license review controls before extracting vocabulary candidates.

### D2 page-level evaluation split

Before building n-grams, partition article-namespace pages in the snapshot by stable page ID by computing SHA-256 over the UTF-8 encoding of `NYCH-D2-SPLIT-v1`, a NUL byte, the snapshot ID, a NUL byte, and the decimal page ID; interpret the digest as an unsigned big-endian integer and take modulo 100. Assign buckets 0–89 to train, 90–94 to validation, and 95–99 to test. Build n-gram weights from train pages only; use validation pages for correction-cutoff calibration; reserve test pages, unseen during construction and calibration, for final evaluation. Record page IDs/revisions and partition assignments in the build manifest. This split applies to the D2 statistical compendium and correction evaluation only; it does not decide the D10 neural model-training corpus split.

### Manifest fields

- `schema_version`
- `compendium_id`
- `corpus_id`, license/reference, and corpus SHA-256
- tokenizer/normalizer version
- n-gram order and smoothing method/version
- build code version and artifact digest
- keyboard-layout map IDs and versions, stored as separate resources. Initial registry: US QWERTY, UK QWERTY, AZERTY, and QWERTZ. Use device/user layout when available; if unknown, keyboard corroboration requires agreement across enabled layouts.

### Statistical tables

**`ngram_counts`**

| Column | Meaning |
|---|---|
| `order_n` | Context length, initially 1–3 |
| `context_key` | Canonically serialized ordered prior-token sequence |
| `candidate_token` | Candidate next word/token |
| `count` | Observed count in the approved corpus |
| `context_total` | Total continuations observed for that context |
| `probability` | Smoothed conditional probability |
| `log_probability` | Stable additive score used for sequence ranking |

Keep integer counts as evidence and smoothed probabilities/log probabilities for comparable scoring. Use explicit backoff/interpolation for contexts with sparse counts; record its algorithm/version in the manifest.

### Example entry

For the sequence “water-shed moment”, an index row can represent:

`order_n=1, context_key=["water-shed"], candidate_token="moment", count=N, context_total=T, probability=P, log_probability=log(P)`

The values `N`, `T`, and `P` come from the approved corpus; this example does not assign invented counts.

## Keyboard-aware candidate generation and deterministic correction order

1. Preserve the exact observed surface token and byte span.
2. Generate candidate words only from the versioned general-English, proper-name, and technical/scientific lexicon layers. For each configured keyboard layout, candidate generation may replace a character with a key adjacent to it or remove a character. Do not add insertion, transposition, phonetic, or other edit operations without a separate owner decision.
3. Prefer candidates requiring the fewest total replacements/removals. Among candidates at the same minimum edit count, rank using next-token probabilities conditioned on the previous two or three words, with shorter-context backoff when needed; include right-context evidence when available. Retain the counts/probabilities and keyboard layout/edit path as evidence. If layout is unknown, enabled layouts must agree on the proposed correction or the token remains unresolved.
4. A statistical candidate that is not supported by an allowed keyboard edit is not a keyboard-based typo correction. If the original token is a valid term and the thought remains coherent, keep it literal. If candidates remain ambiguous or evidence is weak, keep the token literal and unresolved.
5. Preserve any correction as a separate hypothesis with surface form, candidate, evidence, edit count, layout, and confidence. Never overwrite the input text or silently force an emoji.

Calibrate the correction cutoff and score margin on held-out, representative typo and coherent-word cases. Enable automatic internal correction only when the one-sided 95% exact-binomial (Clopper–Pearson) lower confidence bound for held-out precision is at least 99%; otherwise preserve tokens literally and leave them unresolved. Report precision and false-correction rates separately for proper names, scientific terms, coherent rare words, ambiguous candidates, and each keyboard layout.

## Data and audit boundaries

- Build weights only from owner-approved, license-cleared corpora.
- Store aggregate counts and weights, not raw prompts.
- Record corpus, tokenizer, normalization, smoothing, keyboard-layout, and build-artifact versions.
- Report correction accuracy and false-correction rate separately, including names, scientific terms, and coherent rare-word cases.
- If the needed corpus or layout evidence is absent, preserve the literal token rather than guessing.
