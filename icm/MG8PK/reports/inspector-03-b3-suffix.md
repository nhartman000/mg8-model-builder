# Inspector 3 report — B3 occurrence identity re-inspection

- **Module:** Builder 3 / word-occurrence digest and suffix component
- **Candidate source blob:** `3a401d722dbc9ea4cb901f8be66ffc6412658688`
- **Candidate test blob:** `084c26c995a3cc45c692b8f60dfddc9b3a3a9046`
- **Review verdict:** **PASS for the bounded occurrence-hash primitive and suffix component; INTERMEDIATE for complete Builder 3.**
- **Review basis:** independently fetched both exact blobs from the default branch and ran `PYTHONPATH=src python -m unittest discover -s tests -p 'test_trace_identity.py' -v`; **12/12 tests passed**.

## Occurrence-hash findings

1. The fixed, versioned payload is `NYCH-WORD-ID\x00v1\x00 || source_digest[32] || occurrence_index_u64be || byte_start_u64be || byte_end_u64be`. Fixed widths and the domain/version tag make the encoding unambiguous for this contract.
2. The source digest is required to be a 64-character hexadecimal string and decode to exactly 32 bytes. Uppercase hex is accepted; output is canonical lowercase full SHA-256 hex from `hexdigest()`.
3. The three numeric fields reject bools and non-integers, reject negative or >uint64 values, and the span requires `byte_end > byte_start`. The parameter contract documents a zero-based occurrence index and source-relative half-open byte offsets.
4. Tests independently reconstruct the payload and expected digest, compare the result, check 64-character output and uppercase-input equivalence, and verify changed digest/index/span values change the result. Validation tests cover malformed digest, zero-length span, negative occurrence index, and bool rejection.
5. The function hashes only the source digest and occurrence metadata. It does not combine the suffix or domain into the digest, and it does not perform domain assignment. The suffix display separately requires exact emoji inventory membership; runtime LLM selection is absent.

## Suffix findings

1. NFKD accent folding and combining-mark removal affect only the derived suffix. The source string is not mutated.
2. It removes a/e/i/o/u, retains y, and collapses adjacent repeated consonants. Accented English examples pass; residual non-ASCII letters that cannot fold to ASCII fail closed.
3. An all-vowel word has an empty structured suffix and renders as `∅`. Emoji selection must exactly match a normalized inventory entry.

## Remaining boundary and limitations

The bounded primitives pass their reviewed contracts. **Complete Builder 3 remains INTERMEDIATE.** The hash function cannot independently establish that the supplied digest is B1's SHA-256 of the exact UTF-8 prompt, that byte offsets identify the intended word boundaries, or that occurrence indexes are correctly assigned by the upstream tokenizer. Those are caller/integration invariants and need evidence at the interface. Final output serialization and domain assignment remain unresolved; the selected emoji here is supplied by the caller and only checked for inventory membership.

Inspector 3 does **not** authorize GitSON wiring or grant full-module PASS.
