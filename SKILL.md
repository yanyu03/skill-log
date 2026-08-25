---
name: academic-workflow-engine
description: Reusable academic document scheduler that compiles a thesis example into an immutable formatting Template Pack, normalizes new content into a Thesis AST, routes academic tasks as a DAG, dispatches semantic Office jobs to accepted Microsoft/WPS providers, and requires evidence-backed delivery gates. Use when reusing thesis formatting without copying content or when onboarding another university template.
---

# Academic Workflow Engine

## Hard invariants

1. **Example content is disposable; formatting is reusable.** Never copy exemplar thesis body text, figures, citations, equations, table cells or personal metadata into new work.
2. **Baseline Template Packs are immutable.** Runtime tasks never write `templates/**`, `example/**` or defaults. Every run gets a physical writable copy in `runs/<run_id>/config/`.
3. **Template changes are additive versions.** Never overwrite an existing template version.
4. **Markdown carries content; Office carries formatting.** MarkItDown is an ingest/round-trip content bus, never a template-format extractor.
5. **Physical source section count is observation, not a rule.** Runtime Office jobs use a canonical semantic section blueprint. Repeated source `main_body` sections are not cloned into every new thesis.
6. **Scheduler owns order; Office providers own Office mechanics.** Business logic never branches on COM/MCP/WPS implementation details.
7. **Declared capability is not binding.** Microsoft/WPS can be `BOUND` only after provider acceptance evidence passes.
8. **No gate, no delivery.** CONFIG, SEMANTIC, STRUCTURE, CONTENT, TEMPLATE and VISUAL must all execute and return PASS/PASS_W.
9. **Template is frozen from academic substance.** Formatting/template modes never invent, rewrite, or validate thesis claims; semantic validation belongs to the writing/content path before Office composition.

## Runtime flow

A full run is dependency-driven, not a fixed eight-step script:

`CONFIG_VERIFY -> TPL_RESOLVE`

`INGEST -> SEMANTIC_PARSE -> TEMPLATE_CONTAMINATION / CITATION / FIGURE_PREP / RESEARCH`

For `full` mode, research/citation branches converge at `SEMANTIC_AUDIT`. External citation verification produces review evidence, not an automatic terminal run failure. The semantic reviewer owns the academic disposition: `ACCEPT`, `MINOR_REVISION`, `MAJOR_REVISION`, or `REJECT`. `MAJOR_REVISION` blocks Office composition but routes the manuscript to a recoverable rework task; only `SEMANTIC_GATE_PASS` unlocks `OFFICE_COMPOSE -> FIELD_REFRESH`. `format_only` and `template_migration` intentionally skip semantic judgment so the template layer remains content-neutral.

Then run independent audits: `STRUCTURE_AUDIT`, `TEMPLATE_AUDIT`, `RENDER -> VISUAL_AUDIT`, and `ROUNDTRIP -> CONTENT_AUDIT`. Only their gate artifacts unlock `FINAL_GATES -> DELIVERY`.

## Thesis AST

`academic-thesis-ast/v1` represents title, abstracts, headings, body, figures, tables, captions, equations, references and acknowledgments. It carries claim/provenance records (`measured`, `simulated`, `calculated`, `literature`, `design_target`, `interpretive`) and evidence-linked engineering conditions.

## Writing-layer semantic contract

The engine does not write the thesis itself, but `full` mode validates academic claims before formatting:

- **measured** claims require verified experiment/dataset/raw-data/test-log evidence;
- **simulated** claims require verified solver/model/output evidence;
- **calculated** claims require a nearby derivation/equation or a verified calculation artifact;
- **literature** claims require valid local citation linkage and may additionally require external citation verification;
- **design_target** statements are allowed without pretending they are measured results;
- absolute claims such as “完全排除/绝对不会/零损伤” are flagged for downgrade or stronger evidence.

Writers or research providers may bind explicit evidence with `[[EVIDENCE:<id>]]` markers or an evidence manifest. Reviewer authority is intervention-oriented rather than binary: unsupported high-risk measured/simulated claims normally become `MAJOR_REVISION` with an explicit action such as provide evidence or downgrade the claim; reference entity mismatches are routed to the reference team; low-risk wording issues may be `MINOR_REVISION`. `REJECT` is reserved for non-reviewable integrity/provider failures. QA may recommend a wording downgrade but must never silently rewrite academic substance.

## Office compatibility layer

Production provider families are `microsoft-word-skill` and `wps-word-skill`. Provider transport is `host_skill`: the engine writes a provider request, the host invokes the real skill, then the engine validates/accepts the returned artifacts. Scheduler owns order; Office providers own Office mechanics.

## Gates

- `CONFIG_GATE`: baseline lock/hash still valid.
- `SEMANTIC_GATE`: reviewer-style academic disposition. `ACCEPT`/eligible `MINOR_REVISION` may pass; `MAJOR_REVISION` creates a rework loop and blocks Office composition; `REJECT` terminates the academic path.
- `STRUCTURE_GATE`: required semantic blocks, sections, fields, native OMML and unresolved slots.
- `CONTENT_GATE`: MarkItDown round-trip preserves semantic content inventory.
- `TEMPLATE_GATE`: semantic section blueprint, geometry and role formatting conform to the run Template Pack.
- `VISUAL_GATE`: every rendered page receives host-vision PASS/PASS_W/FAIL evidence.

Final delivery produces a hashed delivery manifest and rechecks the immutable baseline. Scheduler events should carry the actual audit/review evidence used for each disposition so a later reviewer can reconstruct why a task was accepted, returned for revision, or rejected.

## Non-goals

Excel/PPT workflows remain outside the thesis-first profile. Citation live lookup remains a provider-neutral `citation_verify` capability. The engine must block when an external capability is absent rather than replace it silently.
