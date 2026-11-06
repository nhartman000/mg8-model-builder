# Inspector 3 report — D3 suffix candidate

- **Module:** Builder 3 / word-skeleton suffix component
- **Candidate source blob:** `564bfe320d2fa364491a9551de803d0d7d9a93fc`
- **Candidate test blob:** `9dcf0a8eee84a17e71147281cef4ebcb770ca650`
- **Review verdict:** **INTERMEDIATE** for the complete Builder 3 module; the implemented suffix component passes the checked cases.
- **Review basis:** inspected the exact GitHub blobs above and ran `PYTHONPATH=src python -m unittest discover -s tests -p 'test_trace_identity.py' -v` in the NYCH model project; **7/7 tests passed**.

## Findings

1. The candidate preserves its input string, applies NFKD plus combining-mark removal only to the derived suffix, removes a/e/i/o/u, retains y, and collapses adjacent repeated consonants. The supplied Chinchilla and Attacking examples match.
2. Exact inventory membership rejects an unlisted multi-emoji string and skin-tone-modified variant in the tested inventory. Runtime code does not call an LLM to pick the emoji.
3. The code intentionally does not construct the SHA/occurrence/domain trace ID. It does not claim that this suffix helper is the complete trace identity.

## Blocking issue

The post-fold ASCII filter silently discards letters that do not decompose to ASCII under NFKD (for example, æ/œ/ø/ł). Distinct inputs can therefore collapse to the same suffix, and some words can lose information without an error. The owner-approved “accent fold” policy does not yet specify transliteration for these letters. Before accepting the suffix component, either:
- define and test a transliteration table, or
- reject unsupported residual letters explicitly rather than silently dropping them.

Also define the expected result when a word contains only vowels and therefore produces an empty suffix. The current implementation returns the empty string.

## Decision boundaries still open

- SHA-256 input material and how word occurrence identity is made unique.
- Final serialized trace-ID separators/order and domain binding.
- Handling policy for unsupported Latin letters and empty suffixes.
- Inventory artifact schema/version and the required guarantee that each member is exactly one approved emoji grapheme.

Do not wire this component or mark the complete Builder 3 module PASS until the blocking suffix behavior and remaining trace-ID contract are resolved.