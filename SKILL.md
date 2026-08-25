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

## Template Compiler

Compile `example.docx` once into a versioned Template Pack. Extract only formatting facts:
- page geometry, margins and section/page-number behavior;
- semantic paragraph roles and direct formatting (including cover title inference);
- table layout prototypes without cell text;
- header/footer structure and field codes without header/footer text;
- figure/table caption styles and numbering policy;
- native OMML equation observations/rules;
- styles/theme/font table via content-free `skeleton.docx`;
- discarded content SHA-256 fingerprints for contamination checks.

The template pack is then locked read-only. A new university means a new Template Pack, not changes to thesis business logic.

## Runtime flow

A full run is dependency-driven, not a fixed eight-step script:

`CONFIG_VERIFY -> TPL_RESOLVE`

`INGEST -> SEMANTIC_PARSE -> TEMPLATE_CONTAMINATION / CITATION / FIGURE_PREP / RESEARCH`

For `full` mode, research/citation branches converge at `SEMANTIC_AUDIT`. Only `SEMANTIC_GATE_PASS` can unlock `OFFICE_COMPOSE -> FIELD_REFRESH`. `format_only` and `template_migration` intentionally skip semantic judgment so the template layer remains content-neutral.

Then run independent audits: `STRUCTURE_AUDIT`, `TEMPLATE_AUDIT`, `RENDER -> VISUAL_AUDIT`, and `ROUNDTRIP -> CONTENT_AUDIT`.

Only their gate artifacts unlock `FINAL_GATES -> DELIVERY`.

## Thesis AST

`academic-thesis-ast/v1` represents title, abstracts, headings, body, figures, tables, captions, equations, references and acknowledgments. It also carries claim/provenance records (`measured`, `simulated`, `calculated`, `literature`, `design_target`, `interpretive`). Engineering conditions are separate evidence-linked records (`operating_envelope`, `worst_case`, `design_requirement`, `design_load`, `selected_component`, `verification_result`, etc.). Figure/table cross-reference relationships are recorded separately from formatting.

Display-math input should become equation blocks. Production Office providers must emit native OMML where equations exist; text/image fallback requires explicit PASS_W policy and may be rejected by the target profile.


## Writing-layer semantic contract

The engine does not write the thesis itself, but `full` mode now validates academic claims before formatting:

- **measured** claims require verified experiment/dataset/raw-data/test-log evidence;
- **simulated** claims require verified solver/model/output evidence;
- **calculated** claims require a nearby derivation/equation or a verified calculation artifact;
- **literature** claims require valid local citation linkage and may additionally require external citation verification;
- **design_target** statements are allowed without pretending they are measured results;
- absolute claims such as “完全排除/绝对不会/零损伤” are flagged for downgrade or stronger evidence.

Writers or research providers may bind explicit evidence with `[[EVIDENCE:<id>]]` markers or an evidence manifest. In strict mode, unsupported high-risk measured/simulated claims are blockers, not style warnings.

## Office compatibility layer

`academic-office-job/v2` contains:
- canonical semantic section blueprint;
- block IDs and semantic roles;
- target semantic sections;
- style references into the run config;
- asset refs and cross-reference relationships;
- required Office actions and post-actions;
- invariants forbidding baseline mutation and exemplar-content copying.

Production provider families are `microsoft-word-skill` and `wps-word-skill`. Provider transport is `host_skill`: the engine writes a provider request, the host invokes the real skill, then the engine validates/accepts the returned artifacts. Do not mark a provider bound manually.

Provider acceptance must cover sections/page numbers, TOC/field refresh, figures/captions/REF, table prototypes, native OMML, font coverage/substitution, PDF export/render, host visual review, MarkItDown round-trip and baseline immutability.

## Fonts

Font requirements are extracted from the Template Pack. Production providers must report available fonts/substitutions. Missing fonts with no explicit substitution fail preflight. Silent renderer substitution is not acceptable evidence.

## Gates

- `CONFIG_GATE`: baseline lock/hash still valid.
- `SEMANTIC_GATE`: claim provenance/evidence constraints pass before Office composition.
- `STRUCTURE_GATE`: required semantic blocks, sections, fields, native OMML and unresolved slots.
- `CONTENT_GATE`: MarkItDown round-trip preserves semantic content inventory.
- `TEMPLATE_GATE`: semantic section blueprint, geometry and role formatting conform to the run Template Pack.
- `VISUAL_GATE`: every rendered page receives host-vision PASS/PASS_W/FAIL evidence.

Final delivery produces a hashed delivery manifest and rechecks the immutable baseline.

## Non-goals

Excel/PPT workflows remain outside the thesis-first profile. Citation live lookup remains a provider-neutral `citation_verify` capability. The engine must block when an external capability is absent rather than replace it silently.
