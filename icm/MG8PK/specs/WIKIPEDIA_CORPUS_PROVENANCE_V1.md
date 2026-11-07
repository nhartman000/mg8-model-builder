# English Wikipedia Corpus Provenance — V1

## Selected general-statistics source

- Project: English Wikipedia article dump.
- Snapshot: `20261001`, selected as the latest complete snapshot found on 2026-11-07.
- Source directory: `https://dumps.wikimedia.org/enwiki/20261001/`
- Article source file: `enwiki-20261001-pages-articles-multistream.xml.bz2` (25.1 GB compressed, according to the dump index).
- The `20261101` snapshot was still marked in progress on 2026-11-07; do not build from an incomplete dump.
- Use article namespace text only for general continuation statistics; exclude templates, talk pages, user pages, logs, files/media, and project/meta namespaces.
- Record the official checksum of the downloaded dump and the SHA-256 of the exact downloaded artifact and extracted corpus.

## Per-page provenance fields

| Field | Requirement |
|---|---|
| `snapshot_id` | `enwiki-20261001` or a later explicitly approved complete snapshot |
| `page_id` | Stable page identifier |
| `revision_id` | Exact revision represented in the dump |
| `title` | Page title |
| `page_url` | Stable page link for attribution and audit |
| `namespace_id` | Include only approved article namespace |
| `page_text_sha256` | Digest of extracted page text used in the build |
| `license_basis` | Applicable license evidence and any page-specific exception |
| `excluded_reason` | Required if the page is excluded |
| `extraction_version` | Parser and cleaning pipeline version |
| `included_in_compendium` | Boolean |
| `compendium_build_id` | Exact n-gram build using this page |

## License and release controls

Wikimedia reports that most text is under CC BY-SA 4.0 and GFDL; individual pages can have imported material and additional attribution notices. Preserve page-level title/revision/URL provenance, exclude content with incompatible or unclear notices when identifiable, and include attribution and license notices with any shared source-derived artifacts as required.

The exact obligations for aggregated n-gram counts, model weights, or generated output are not determined by this source record. Keep the statistical compendium and derived model private until a qualified license review clears their intended distribution. This is a release gate, not a claim that a particular artifact is or is not an adaptation.

Do not put raw user prompts into the corpus. Do not commit the raw Wikipedia dump or extracted article text to the model repository. Keep only approved derived artifacts and provenance records there.
