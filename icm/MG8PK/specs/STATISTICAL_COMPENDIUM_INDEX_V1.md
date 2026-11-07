
## Purpose

Provide deterministic, local statistical evidence for word continuation and typo interpretation. The compendium is an aggregate index built from a versioned, licensed corpus. It is not a runtime LLM and does not retain user prompts.

## Recommended storage

Use a versioned SQLite database for runtime lookup, with a small JSON manifest alongside it. Owner-approved corpus composition: a general English corpus plus separate technical/scientific and name lexicons; never use prompt logs. Owner-selected source: the complete English Wikipedia dump `enwiki-20261001` for general English weights. This was the latest complete dump identified on 2026-11-07; the `20261101` dump was still in progress. Use article namespace only, preserve snapshot/page/revision provenance, and follow applicable attribution/share-alike conditions. Keep derived artifacts private until license review clears intended distribution. Technical/name lexicons remain separate and versioned. No prompt logs are permitted. See `WIKIPEDIA_CORPUS_PROVENANCE_V1.md` for the source record and controls. SQLite provides indexed key lookups and deterministic local access; the manifest binds the weights to their source and build procedure.

### Candidate lexicon composition

The owner approved a general English candidate-lexicon seed derived from the same `enwiki-20261001` snapshot: article text vocabulary plus page titles and redirects. Keep proper-name and technical/scientific lexicons as separate versioned layers; their exact source sets and inclusion rules remain pending. This candidate lexicon is not claimed to be a complete dictionary. Missing entries remain representable through the approved internal UTF-8 byte fallback. Apply the same corpus provenance and license review controls before extracting vocabulary candidates.

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

## Deterministic correction order

1. Preserve the exact observed surface token and byte span.
2. Query the statistical compendium first. Rank lexical candidates from the previous two or three words, with shorter-context backoff when necessary. Where available, include right-context evidence to distinguish alternatives.
3. Check the top statistical candidates against the versioned keyboard-layout maps. Neighboring-key substitutions and other plausible key errors provide secondary evidence; they do not replace context statistics.
4. Correct only when the statistical/context evidence is clear and keyboard evidence is compatible for a keyboard typo. If the original token is a valid term and the thought remains coherent, keep it literal. If no clear candidate emerges, keep it literal and unresolved.
5. Preserve correction as a separate hypothesis with evidence and confidence. Never overwrite the input text or silently force an emoji.

Calibrate the correction cutoff and score margin on held-out, representative typo and coherent-word cases. Automatic internal correction is allowed only if its measured precision is at least 99%; otherwise preserve tokens literally and leave them unresolved. Report precision and false-correction rates for proper names, scientific terms, coherent rare words, ambiguous candidates, and each keyboard layout.

## Data and audit boundaries

- Build weights only from owner-approved, license-cleared corpora.
- Store aggregate counts and weights, not raw prompts.
- Record corpus, tokenizer, normalization, smoothing, keyboard-layout, and build-artifact versions.
- Report correction accuracy and false-correction rate separately, including names, scientific terms, and coherent rare-word cases.
- If the needed corpus or layout evidence is absent, preserve the literal token rather than guessing.
