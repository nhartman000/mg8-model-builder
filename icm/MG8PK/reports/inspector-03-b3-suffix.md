# Inspector 3 report — B3 frozen-contract review

- **Module:** Builder 3 / word-occurrence identity, suffix, canonical B3 string
- **Candidate source blob:** `c5b5d1b4fe8453bde9b1c126092999a818c07395`
- **Candidate test blob:** `480e6a31d973de410e1449a13f6d8b9f6a022630`
- **Review verdict:** **PASS for the bounded B3 module against the frozen contract. B4 domain resolution is not reviewed or passed.**
- **Review basis:** independently fetched the exact current default-branch source and test blobs and ran `PYTHONPATH=src python -m unittest discover -s tests -p 'test_trace_identity.py' -v`; **14/14 tests passed**.

## Frozen B3 contract reviewed

Canonical serialization is `sha256:<64-lowercase-hex>_<suffix-or-∅>`; B4 `domain_id` is a separate field.

1. The occurrence digest payload is `NYCH-WORD-ID\x00v1\x00 || source_digest[32] || occurrence_index_u64be || byte_start_u64be || byte_end_u64be`. The tag/version and fixed-width fields make this payload unambiguous.
2. Source digest input must be a 64-character hex string decoding to 32 bytes. Hex input is normalized by decoding, and the output is deterministic canonical lowercase 64-character SHA-256 hex.
3. Occurrence index, start, and end must be integers (bool is rejected), nonnegative uint64 values; byte end must be greater than byte start. The API contract documents zero-based occurrence indexing and source-relative half-open byte offsets.
4. `format_trace_id` enforces exactly 64 lowercase hex characters and lowercase ASCII letters/digits for the suffix. It produces the approved `sha256:<digest>_<suffix>` form and renders an empty structured suffix as `∅`. The suffix is not folded into the hash. B4 domain is explicitly excluded from this string.
5. Tests independently reconstruct the binary hash payload; check full digest length/canonicalization, digest/index/span sensitivity and basic invalid inputs; and cover canonical formatting, empty suffix marker and rejection of noncanonical fields.
6. Suffix derivation applies NFKD accent folding only to the derived value, removes a/e/i/o/u, retains y, collapses repeated adjacent consonants, and rejects residual unsupported non-English letters. Source text is not modified. Emoji inventory validation remains separate and does not invoke an LLM.

## Integration invariants still required

This PASS covers the bounded B3 module behavior, not proof of upstream data provenance. At integration, B1 must supply SHA-256 of the exact UTF-8 input, and the tokenizer must supply correct zero-based occurrence indices and source-relative UTF-8 byte spans whose half-open boundaries match the intended token/word. The B3 helper validates representation/range but cannot verify those facts from a digest and offsets alone.

B4 `domain_id` resolution and its association with the canonical B3 result remain a separate gate. No B4 PASS is granted. Inspector 3 does **not** authorize GitSON wiring absent the required upstream gates.
