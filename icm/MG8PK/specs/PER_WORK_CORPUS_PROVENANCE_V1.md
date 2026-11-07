# Per-Work Corpus Provenance Record — V1

Create one record for every text considered for the B2 statistical compendium. Inclusion requires an item-level rights review and a reproducible content hash.

## Required fields

| Field | Requirement |
|---|---|
| `work_id` | Stable internal identifier |
| `title` | Work title as published |
| `creator` | Author/creator, when known |
| `publication_date` | First publication date or documented range |
| `jurisdiction` | Rights jurisdiction evaluated; V1 default is United States |
| `source_url` | Direct catalog/source record for this individual work |
| `source_artifact_sha256` | SHA-256 of the exact downloaded source artifact |
| `clean_text_sha256` | SHA-256 of the normalized text actually used to derive counts |
| `rights_status` | `verified_us_public_domain`, `rejected`, or `pending_review` |
| `rights_evidence_url` | Work-specific evidence, such as the work's own copyright/licensing notice and corroborating bibliographic record |
| `reviewed_at` | UTC date of rights review |
| `review_basis` | Concise, evidence-based reason for the status |
| `transformations` | Ordered preprocessing operations and version IDs |
| `included_in_compendium` | Boolean; true only for verified work |
| `compendium_build_id` | Exact aggregate-count build that used this work, if included |

## Inclusion gates

1. Review each work independently. A collection-level statement does not clear every item.
2. Include only works explicitly marked `verified_us_public_domain` for the target jurisdiction. Permission-only/copyrighted works are excluded unless separately licensed and owner-approved.
3. Record source and cleaned-text hashes so the aggregate counts can be rebuilt and audited.
4. Store work metadata and derived aggregate counts in the project. Do not place raw prompts or user messages in the corpus.
5. Where a source has separate trademark, attribution, or redistribution terms, record how the workflow complies before inclusion. For Project Gutenberg items, inspect the individual ebook notice/license and do not assume every item has the same status.
6. Recheck rights before distributing raw text, corpus packages, weights, or a trained model; this record documents source review but is not a substitute for legal review.

## Example shape

```json
{
  "work_id": "work-000001",
  "title": "Example Work",
  "creator": "Example Author",
  "publication_date": "1901",
  "jurisdiction": "US",
  "source_url": "https://example.org/catalog/work-000001",
  "source_artifact_sha256": "<64 lowercase hex>",
  "clean_text_sha256": "<64 lowercase hex>",
  "rights_status": "pending_review",
  "rights_evidence_url": "https://example.org/catalog/work-000001/rights",
  "reviewed_at": null,
  "review_basis": "",
  "transformations": [],
  "included_in_compendium": false,
  "compendium_build_id": null
}
```

The example is schema-only; it does not assert rights for a real work.
