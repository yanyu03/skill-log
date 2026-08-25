# Reference supply chain v1.3

The reference line is a supply chain, not a bibliography string generator.

## Authority split

- Discovery worker proposes candidates and search intent.
- External resolver/database owns entity identity (title/authors/venue/year/DOI/standard number).
- Deterministic `reference-lock` owns admission to the locked registry.
- Writer may consume locked IDs and support scopes but may not edit identity metadata.
- Semantic QA may reject misuse of a real source, but it does not invent replacement metadata.

## Artifacts handed downstream

A successful `reference-lock` writes:

- `reference_registry.json`: verified, immutable writer-consumable entities;
- `reference_evidence.json`: resolver/source/lookup/field-match audit trail;
- `reference_claim_map.json`: what each locked source is allowed to support;
- `reference_quarantine.json`: invalid, duplicate, pending or incomplete candidates;
- `reference_supply_review.json`: counts, requirements and reviewer/scheduler disposition.

The undergraduate profile requires at least five externally verified English references. There is intentionally no hard-coded total bibliography count unless a target profile adds one.

## Rework behavior

Candidate rejection during pre-writing is normal procurement noise. If enough verified sources remain, the registry can be published with warnings and quarantined candidates never reach the writer.

If an already-cited manuscript source is rejected, or the verified-English minimum is not met, `REFERENCE_LOCK` emits `REFERENCE_REWORK_REQUIRED`. Research finds a replacement, citation verification resolves it, and `REFERENCE_RELOCK` must succeed before semantic review or Office composition can proceed.

Legacy aggregate citation reports remain reviewable for backward compatibility, but they cannot create a v1.3 registry because they do not preserve itemized metadata for downstream use.
