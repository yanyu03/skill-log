# academic-workflow-engine

Reusable academic-document workflow engine for thesis/report production. The engine treats a real thesis DOCX as a **formatting exemplar only**: layout, styles, paragraph behavior, section/page-number rules, table prototypes, header/footer structure and equation rules can be reused; exemplar thesis content, figures, citations and personal metadata are discarded.

## Design status: v1.1 semantic-writing gate

Implemented:
- immutable versioned Template Packs + per-run physical config copies;
- write-before path policy, read-only baseline and post-run SHA-256 verification;
- Template Compiler: layout, style roles, cover title inference, semantic section rules, table prototypes, header/footer field structure, figure/table caption rules, native-OMML observations and content-free skeleton;
- MarkItDown content-bus adapter with lossless Markdown/TXT passthrough and no silent fallback for Office/PDF formats;
- Thesis AST, engineering-condition roles, claim/provenance extraction and figure/table cross-reference inventory;
- dynamic DAG modes (`full`, `format_only`, `audit_only`, `citation_only`, `template_migration`) with persisted checkpoints and transition guards;
- local citation bijection, external-evidence contract, claim-level semantic gate, figure preflight/hash manifest and template-content contamination gate;
- `academic-office-job/v2`: semantic section blueprint + semantic formatting roles, never hardcoded school font constants in business logic;
- Office Host Bridge and Provider Registry for Microsoft Word Skill / WPS Word Skill;
- provider acceptance lock: a provider cannot become `BOUND` without matching acceptance evidence;
- font preflight, native OMML requirement, TOC/field/cross-reference contracts;
- six mandatory delivery gates: CONFIG / SEMANTIC / STRUCTURE / CONTENT / TEMPLATE / VISUAL;
- full-mode convergence rule: RESEARCH/CITATION verification must feed SEMANTIC_AUDIT before OFFICE_COMPOSE; format-only/template-migration remain content-neutral;
- delivery manifest with artifact hashes and safe resume/recovery semantics.

## Current real template

`templates/changchun_ih/undergraduate_thesis_2026/1.1.0/` is the first real one-school baseline. It is evidence for this template only, not a claim that other universities use the same format. New universities are onboarded by compiling new immutable Template Packs; the core workflow is unchanged.

## External dependencies intentionally not faked

Microsoft Word Skill and WPS Word Skill are currently represented by `UNBOUND` provider manifests. Production binding requires the real skill plus the provider acceptance suite. MarkItDown is an optional runtime dependency; this construction environment had no network access, so DOCX/PDF round-trip cannot be falsely marked PASS here. Markdown/TXT input remains fully testable.

`reference-test-provider` exists only to prove engine contracts/gates end to end. It is explicitly non-production and must never be used as evidence of Microsoft/WPS fidelity.
