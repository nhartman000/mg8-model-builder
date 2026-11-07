# Builder 2 — NYCH Tokenization

## Mandate
Build only Module 2 (Tokenization) for NYCH Language Model V1 at `src/nych_language_model/pipeline/tokenization.py` in `nhartman000/nych-language-model`.

## Owner-approved direction
- Use whitespace boundaries to identify English surface-word spans and preserve exact UTF-8 source byte offsets.
- Emit punctuation as its own token; keep apostrophes and hyphens internal to a lexical word span (for example, `can't` and `red-barn`). Preserve each token's exact source byte span.
- Emit each ordinary space as `<SPACE>`; use distinct tokens for tabs and line breaks. Preserve repeated whitespace as repeated tokens and retain exact byte spans.
- Treat each recognized emoji grapheme as one atomic token, selected from a versioned canonical inventory.
- Canonicalize only explicit, approved non-meaning-changing aliases to their inventory default. Skin-tone modifiers and presentation variants may fold to the default when the alias table says so. Never collapse a meaning-changing sequence by stripping code points.
- Preserve original source bytes/text; do not modify the input while creating normalized token views. Words need not map to emoji; do not replace scientific names, proper names, or other unmatched words with a forced emoji.
- Keep B3 occurrence trace IDs separate from model vocabulary token IDs.
- Use a layered, versioned lexicon for common English plus approved technical/scientific and proper-name terms.
- Resolve likely typos in this order: rank candidates statistically from a versioned local n-gram compendium using the previous two or three words (and right context when available), then check top candidates against configured keyboard-layout maps as secondary evidence. Preserve the original surface spelling and byte span; emit a separate candidate hypothesis with evidence/confidence.
- If the original word is a valid term and the thought remains coherent, do not correct it. If no clear candidate emerges, leave it literal and unresolved.
- Build general n-gram weights from the complete English Wikipedia snapshot `enwiki-20261001`, article namespace only. Preserve dump checksum and per-page/revision provenance; follow applicable attribution/share-alike terms. Keep the dump and extracted text out of the NYCH repo. Keep derived artifacts private pending license review.
- Follow `icm/MG8PK/specs/STATISTICAL_COMPENDIUM_INDEX_V1.md` and `icm/MG8PK/specs/WIKIPEDIA_CORPUS_PROVENANCE_V1.md`.
- Do not force a correction when candidates are ambiguous or weak. Keep the token literal/unknown; do not substitute an emoji.

## Still unresolved
Do not select an OOV/unknown-word representation, punctuation policy, whitespace token representation, or model vocabulary encoding until the owner freezes those contracts. If a required choice is open, return a concrete design question or interface-neutral prototype.

## Required outputs
- Implementation and focused tests in the NYCH model repository after D2 is frozen.
- Versioned input/output contract and examples.
- Reproducible evidence, dependencies, artifact digest, and concise build report.
- Synthetic fixtures only; never put raw prompts in tests, logs, reports, or QSON.

## Boundaries
Do not apply D3 accent folding in the tokenizer; that transform is confined to the derived trace suffix. Do not infer semantics or call an LLM to choose emoji. Do not change files outside this module without an approved shared-interface change. Do not self-approve or GitSON-wire. Work concurrently against the frozen schema and use mocks for unfinished modules.

## Completion
Submit the candidate and evidence bound to its digest for Inspector 2. The Inspector—not the Builder—returns PASS, FAIL, or INTERMEDIATE.
