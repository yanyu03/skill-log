# academic-workflow-engine

Reusable academic-document workflow engine for thesis/report production. A real thesis DOCX is treated as a formatting exemplar only; academic content, citations, figures and personal metadata are not reusable template assets.

## Design status: v1.2 reviewer-authority QA

The engine uses immutable Template Packs, a Thesis AST, a dependency-driven DAG, local/external citation review, claim/evidence review, Office provider contracts, and CONFIG / SEMANTIC / STRUCTURE / CONTENT / TEMPLATE / VISUAL delivery gates.

### Reviewer-authority QA

Academic QA behaves like a reviewer rather than a binary execution kill-switch. Citation/entity verification feeds a review report into the central semantic reviewer. The reviewer can `ACCEPT`, request `MINOR_REVISION`, request recoverable `MAJOR_REVISION`, or `REJECT` a non-reviewable/integrity failure.

`MAJOR_REVISION` blocks Office composition and routes the manuscript back to the responsible writer/reference/calculation worker. QA may prescribe an action or recommend a wording downgrade but never silently rewrites academic substance. Only a `SEMANTIC_GATE_PASS` unlocks final Office composition.

The undergraduate profile requires at least five externally verified English references.

## Baseline

`main` retains the Drive-side v1.1 semantic-gate baseline and a source-only archive under `baseline/`. Reviewer-authority changes are developed on `qa-reviewer-authority-v1.2` for comparison and review.
