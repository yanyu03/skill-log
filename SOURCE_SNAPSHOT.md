# Upstream source snapshot

GitHub `main` is the development mirror of the Drive-side `academic-workflow-engine` v1.1 semantic-gate baseline.

- Upstream package: `academic-workflow-engine-v1.1-semantic-gate.zip`
- Upstream full-package SHA-256: `3e64fc8e2a8caf092873401a86ea3e3ac610a41eaf9981644468108ce03ab746`
- GitHub source-only archive: `baseline/academic-workflow-engine-v1.1-source-only.zip`
- Source-only SHA-256: `d58cc62ef9082c744df3f054bb60e7d2161074729fedf7d7b418f0944dd9ed82`

The source-only archive preserves text source, schemas, configuration and template metadata needed for code review. Generated run artifacts and large binary test/template fixtures are intentionally excluded from this GitHub snapshot; the full Drive package remains the binary upstream reference.

Changes intended for production should be developed on branches and reviewed against this baseline instead of modifying the Drive-side upstream in place.
