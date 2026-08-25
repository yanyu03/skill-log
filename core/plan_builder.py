from __future__ import annotations
from .scheduler import Task

VALID_MODES={'full','format_only','audit_only','citation_only','template_migration'}


def build_plan(mode='full', *, has_figures=False, research=False, citation_verify=False, roundtrip=True, semantic_validate=True) -> list[Task]:
    if mode not in VALID_MODES: raise ValueError(mode)
    tasks=[]
    def add(id,req,prod,caps=()): tasks.append(Task(id,list(req),list(prod),list(caps)))

    if mode=='citation_only':
        add('INGEST',[],['NORMALIZED_CONTENT'],['content_extract'])
        add('SEMANTIC_PARSE',['NORMALIZED_CONTENT'],['CONTENT_READY'])
        add('CITATION_LOCAL',['CONTENT_READY'],['CITATION_LOCAL_READY'])
        if research:
            add('RESEARCH',['CONTENT_READY'],['REFERENCE_CANDIDATES_READY'],['research'])
        if citation_verify:
            verify_req=['CITATION_LOCAL_READY']
            if research: verify_req.append('REFERENCE_CANDIDATES_READY')
            add('CITATION_VERIFY',verify_req,['REFERENCE_RESOLUTION_READY'],['citation_verify'])
            add('REFERENCE_LOCK',['REFERENCE_RESOLUTION_READY'],[
                'REFERENCE_REGISTRY_READY','REFERENCE_EVIDENCE_READY','REFERENCE_CLAIM_MAP_READY',
                'CITATION_REVIEW_READY','REFERENCE_REWORK_REQUIRED'])
            add('REFERENCE_REWORK',['REFERENCE_REWORK_REQUIRED'],['REFERENCE_CANDIDATES_REVISED'],['research'])
            add('REFERENCE_REVERIFY',['REFERENCE_CANDIDATES_REVISED'],['REFERENCE_RESOLUTION_REVISED'],['citation_verify'])
            add('REFERENCE_RELOCK',['REFERENCE_RESOLUTION_REVISED'],[
                'REFERENCE_REGISTRY_READY','REFERENCE_EVIDENCE_READY','REFERENCE_CLAIM_MAP_READY','CITATION_REVIEW_READY'])
        return tasks

    add('CONFIG_VERIFY',[],['CONFIG_READY'])
    add('TPL_RESOLVE',['CONFIG_READY'],['TEMPLATE_READY'])

    if mode=='audit_only':
        add('STRUCTURE_AUDIT',['TEMPLATE_READY'],['STRUCTURE_GATE_PASS'])
        add('TEMPLATE_AUDIT',['TEMPLATE_READY'],['TEMPLATE_GATE_PASS'])
        add('RENDER',['TEMPLATE_READY'],['RENDER_READY'],['render'])
        add('VISUAL_AUDIT',['RENDER_READY'],['VISUAL_GATE_PASS'],['visual_review'])
        add('FINAL_GATES',['CONFIG_READY','STRUCTURE_GATE_PASS','TEMPLATE_GATE_PASS','VISUAL_GATE_PASS'],['DELIVERY_READY'])
        return tasks

    add('INGEST',[],['NORMALIZED_CONTENT'],['content_extract'])
    add('SEMANTIC_PARSE',['NORMALIZED_CONTENT'],['CONTENT_READY'])
    add('TEMPLATE_CONTAMINATION',['TEMPLATE_READY','CONTENT_READY'],['TEMPLATE_CONTENT_CLEAN'])

    if mode=='full':
        add('CITATION_LOCAL',['CONTENT_READY'],['CITATION_LOCAL_READY'])
        if research:
            add('RESEARCH',['CONTENT_READY'],['REFERENCE_CANDIDATES_READY'],['research'])
        if citation_verify:
            verify_req=['CITATION_LOCAL_READY']
            if research: verify_req.append('REFERENCE_CANDIDATES_READY')
            add('CITATION_VERIFY',verify_req,['REFERENCE_RESOLUTION_READY'],['citation_verify'])
            add('REFERENCE_LOCK',['REFERENCE_RESOLUTION_READY'],[
                'REFERENCE_REGISTRY_READY','REFERENCE_EVIDENCE_READY','REFERENCE_CLAIM_MAP_READY',
                'CITATION_REVIEW_READY','REFERENCE_REWORK_REQUIRED'])
            # A reference defect is a supply-chain rework, not a dead run. The writer never sees
            # quarantined candidates because only a successful REFERENCE_LOCK publishes the registry.
            add('REFERENCE_REWORK',['REFERENCE_REWORK_REQUIRED'],['REFERENCE_CANDIDATES_REVISED'],['research'])
            add('REFERENCE_REVERIFY',['REFERENCE_CANDIDATES_REVISED'],['REFERENCE_RESOLUTION_REVISED'],['citation_verify'])
            add('REFERENCE_RELOCK',['REFERENCE_RESOLUTION_REVISED'],[
                'REFERENCE_REGISTRY_READY','REFERENCE_EVIDENCE_READY','REFERENCE_CLAIM_MAP_READY','CITATION_REVIEW_READY'])
    elif citation_verify:
        add('CITATION_LOCAL',['CONTENT_READY'],['CITATION_LOCAL_READY'])
        add('CITATION_VERIFY',['CITATION_LOCAL_READY'],['REFERENCE_RESOLUTION_READY'],['citation_verify'])
        add('REFERENCE_LOCK',['REFERENCE_RESOLUTION_READY'],[
            'REFERENCE_REGISTRY_READY','REFERENCE_EVIDENCE_READY','REFERENCE_CLAIM_MAP_READY',
            'CITATION_REVIEW_READY','REFERENCE_REWORK_REQUIRED'])

    if has_figures: add('FIGURE_PREP',['CONTENT_READY'],['FIGURE_READY'],['figure_assets'])

    if mode=='full' and semantic_validate:
        sem_req=['CONTENT_READY','CITATION_LOCAL_READY']
        if research: sem_req.append('REFERENCE_CANDIDATES_READY')
        if citation_verify:
            sem_req.extend(['REFERENCE_REGISTRY_READY','REFERENCE_EVIDENCE_READY','REFERENCE_CLAIM_MAP_READY','CITATION_REVIEW_READY'])
        add('SEMANTIC_AUDIT',sem_req,['SEMANTIC_GATE_PASS','SEMANTIC_REWORK_REQUIRED'])
        add('SEMANTIC_REWORK',['SEMANTIC_REWORK_REQUIRED'],['CONTENT_REVISED'],['content_rewrite'])
        reaudit_req=['CONTENT_REVISED','CITATION_LOCAL_READY']
        if research: reaudit_req.append('REFERENCE_CANDIDATES_READY')
        if citation_verify:
            reaudit_req.extend(['REFERENCE_REGISTRY_READY','REFERENCE_EVIDENCE_READY','REFERENCE_CLAIM_MAP_READY','CITATION_REVIEW_READY'])
        add('SEMANTIC_REAUDIT',reaudit_req,['SEMANTIC_GATE_PASS'])

    req=['TEMPLATE_READY','CONTENT_READY','TEMPLATE_CONTENT_CLEAN']
    if mode=='full': req.append('CITATION_LOCAL_READY')
    if mode=='full' and semantic_validate: req.append('SEMANTIC_GATE_PASS')
    if citation_verify: req.append('REFERENCE_REGISTRY_READY')
    if has_figures: req.append('FIGURE_READY')
    if citation_verify and not (mode=='full' and semantic_validate): req.append('CITATION_REVIEW_READY')
    add('OFFICE_COMPOSE',req,['DOCX_READY'],['office_compose'])
    add('FIELD_REFRESH',['DOCX_READY'],['FIELDS_READY'],['field_refresh'])
    add('STRUCTURE_AUDIT',['FIELDS_READY'],['STRUCTURE_GATE_PASS'])
    add('TEMPLATE_AUDIT',['FIELDS_READY'],['TEMPLATE_GATE_PASS'])
    add('RENDER',['FIELDS_READY'],['RENDER_READY'],['render'])
    add('VISUAL_AUDIT',['RENDER_READY'],['VISUAL_GATE_PASS'],['visual_review'])
    if roundtrip:
        add('ROUNDTRIP',['FIELDS_READY'],['ROUNDTRIP_READY'],['content_extract'])
        add('CONTENT_AUDIT',['ROUNDTRIP_READY'],['CONTENT_GATE_PASS'])
    final=['CONFIG_READY','STRUCTURE_GATE_PASS','TEMPLATE_GATE_PASS','VISUAL_GATE_PASS']
    if mode=='full' and semantic_validate: final.append('SEMANTIC_GATE_PASS')
    if roundtrip: final.append('CONTENT_GATE_PASS')
    add('FINAL_GATES',final,['DELIVERY_READY'])
    add('DELIVERY',['DELIVERY_READY'],['DELIVERED'])
    return tasks
