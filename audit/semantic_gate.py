from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

_ALLOWED_EVIDENCE = {
    'measured': {'experiment', 'dataset', 'raw_data', 'test_log', 'measurement', 'photo', 'video'},
    'simulated': {'simulation', 'model', 'solver_output', 'result_figure', 'simulation_log', 'project_file'},
    'calculated': {'equation', 'derivation', 'calculation_record', 'spreadsheet', 'script'},
    'literature': {'citation', 'source', 'doi', 'paper'},
}


def _evidence_indexes(evidence: dict | None):
    by_claim: dict[str, list[dict]] = defaultdict(list)
    by_block: dict[str, list[dict]] = defaultdict(list)
    by_id: dict[str, dict] = {}
    if not evidence:
        return by_claim, by_block, by_id
    artifacts = evidence.get('artifacts', []) if isinstance(evidence, dict) else []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        eid = str(item.get('id') or '')
        if eid:
            by_id[eid] = item
        for cid in item.get('claim_ids', []) or []:
            by_claim[str(cid)].append(item)
        for bid in item.get('block_ids', []) or []:
            by_block[str(bid)].append(item)
    return by_claim, by_block, by_id


def _is_verified(item: dict) -> bool:
    return item.get('verified') is True or str(item.get('status', '')).upper() in {'PASS', 'VERIFIED', 'ACCEPTED'}


def _kind(item: dict) -> str:
    return str(item.get('kind') or item.get('type') or '').strip().lower()


def _nearby_equation(ast: dict, claim: dict, radius: int = 4) -> bool:
    blocks = ast.get('blocks', [])
    idx = claim.get('block_index')
    if not isinstance(idx, int):
        return False
    parent = None
    if 0 <= idx < len(blocks):
        parent = blocks[idx].get('parent')
    lo, hi = max(0, idx - radius), min(len(blocks), idx + radius + 1)
    for b in blocks[lo:hi]:
        if b.get('role') == 'equation' and (parent is None or b.get('parent') == parent):
            return True
    return False


def _finding(*, review_severity:str, code:str, claim:dict|None=None, required_action:str, owner:str, comment:str, **extra)->dict:
    item={
        'severity':'blocker' if review_severity=='reject' else ('warning' if review_severity in {'minor','editorial'} else 'major'),
        'review_severity':review_severity,
        'code':code,'required_action':required_action,'owner':owner,'review_comment':comment,
    }
    if claim:
        item.update({'claim_id':str(claim.get('id')),'block_id':str(claim.get('block_id')),'claim_type':claim.get('claim_type'),'risk':claim.get('risk','low'),'text':claim.get('text','')[:240]})
    item.update(extra)
    return item


def _decision(findings:list[dict])->str:
    severities={x.get('review_severity') for x in findings}
    if 'reject' in severities:return 'REJECT'
    if 'major' in severities:return 'MAJOR_REVISION'
    if severities & {'minor','editorial'}:return 'MINOR_REVISION'
    return 'ACCEPT'


def audit(ast: dict, evidence: dict | None = None, *, citation_review:dict|None=None, strict: bool = False, out_json: str | Path | None = None) -> dict:
    """Review manuscript claims like an academic reviewer rather than a binary linter.

    In strict mode MAJOR_REVISION blocks Office composition but remains a recoverable
    rework decision; REJECT is reserved for non-reviewable/provider-integrity failures.
    """
    claims = ast.get('claims', []) or []
    by_claim, by_block, by_id = _evidence_indexes(evidence)
    reference_numbers = {
        int(b.get('metadata', {}).get('number'))
        for b in ast.get('blocks', [])
        if b.get('role') == 'reference_entry' and str(b.get('metadata', {}).get('number', '')).isdigit()
    }
    findings: list[dict[str, Any]] = []
    verified_claims = 0

    for claim in claims:
        cid = str(claim.get('id'));bid = str(claim.get('block_id'));kind = claim.get('claim_type');risk = claim.get('risk', 'low')
        attached = list(by_claim.get(cid, [])) + list(by_block.get(bid, []))
        for marker in claim.get('evidence_markers', []) or []:
            item = by_id.get(str(marker))
            if item:attached.append(item)
        attached = [x for x in attached if _is_verified(x)]
        allowed = _ALLOWED_EVIDENCE.get(kind, set());matched = [x for x in attached if not allowed or _kind(x) in allowed]

        supported = False
        if kind == 'literature':
            cited = set(claim.get('citation_numbers', []) or [])
            supported = bool(cited) and cited <= reference_numbers
            if not cited:
                findings.append(_finding(review_severity='major',code='LITERATURE_CLAIM_WITHOUT_CITATION',claim=claim,required_action='ADD_OR_REMOVE_CITATION',owner='writer',comment='该文献性判断没有明确引文。补可核验引文，或改成作者自己的限定性分析。'))
            elif not cited <= reference_numbers:
                findings.append(_finding(review_severity='major',code='LITERATURE_CITATION_NOT_IN_REFERENCE_LIST',claim=claim,required_action='REPAIR_CITATION_LINKAGE',owner='reference_team',comment='正文引文与参考文献表无法闭合。'))
        elif kind == 'calculated':
            supported = bool(matched) or _nearby_equation(ast, claim)
            if not supported:
                sev='major' if claim.get('has_numeric') else 'minor'
                findings.append(_finding(review_severity=sev,code='CALCULATION_CLAIM_WITHOUT_DERIVATION',claim=claim,required_action='ADD_DERIVATION_OR_CALCULATION_RECORD',owner='calculation_team',comment='计算结论应能回到公式、输入和复算记录；核心数值缺推导按大修处理。'))
        elif kind in {'measured', 'simulated'}:
            supported = bool(matched)
            if not supported:
                code='MEASURED_CLAIM_WITHOUT_EVIDENCE' if kind=='measured' else 'SIMULATION_CLAIM_WITHOUT_EVIDENCE'
                findings.append(_finding(review_severity='major',code=code,claim=claim,required_action='PROVIDE_EVIDENCE_OR_DOWNGRADE_CLAIM',owner='writer',comment='这是可修复的大修项：有原始证据就绑定证据；没有则降级为理论分析、设计目标或预期，不应伪装成实测/仿真结果。'))
        else:
            supported = True

        if supported:verified_claims += 1

        if claim.get('absolute_assertion'):
            findings.append(_finding(review_severity='major' if risk=='high' else 'minor',code='ABSOLUTE_ASSERTION_REQUIRES_DOWNGRADE_OR_STRONG_EVIDENCE',claim=claim,required_action='DOWNGRADE_WORDING_OR_STRENGTHEN_EVIDENCE',owner='writer',comment='审稿时不建议使用“绝对不会/彻底杜绝/零损伤”等无边界断言。改成带工况和证据范围的条件化表述。'))

    if citation_review:
        cdec=str(citation_review.get('review_decision','')).upper()
        for f in citation_review.get('findings',[]) or []:
            sev='major' if str(f.get('severity','')).lower() in {'major','blocker'} else 'minor'
            findings.append(_finding(review_severity=sev,code=str(f.get('code','CITATION_REVIEW_FINDING')),required_action=str(f.get('required_action','VERIFY_OR_REPLACE_REFERENCE')),owner='reference_team',comment='外部文献核验发现可修复问题，先退回文献工位处理，再由审稿门复核。',reference=f.get('reference')))
        if cdec=='REJECT':
            findings.append(_finding(review_severity='reject',code='CITATION_PROVIDER_REJECTED',required_action='RERUN_CITATION_VERIFICATION',owner='reference_team',comment='文献核验本身不可用或不可信，无法进入学术审稿。'))

    decision=_decision(findings)
    if decision=='REJECT':status='FAIL';recommend={'task_status':'FAIL','produce':[]}
    elif decision=='MAJOR_REVISION':
        status='FAIL' if strict else 'PASS_W'
        recommend={'task_status':'PASS_W','produce':['SEMANTIC_REWORK_REQUIRED']}
    elif decision=='MINOR_REVISION':
        status='PASS_W';recommend={'task_status':'PASS_W','produce':['SEMANTIC_GATE_PASS']}
    else:
        status='PASS';recommend={'task_status':'PASS','produce':['SEMANTIC_GATE_PASS']}

    interventions=[{
        'target_claim_id':x.get('claim_id'),'owner':x.get('owner'),'action':x.get('required_action'),
        'blocking':x.get('review_severity') in {'major','reject'},'review_comment':x.get('review_comment')
    } for x in findings]
    result = {
        'schema': 'academic-semantic-review/v2','status':status,'strict':strict,'review_decision':decision,
        'claim_count': len(claims),'verified_claim_count': verified_claims,
        'unresolved_claim_count': len({x.get('claim_id') for x in findings if x.get('claim_id')}),
        'findings': findings,'interventions':interventions,'scheduler_recommendation':recommend,
        'policy': {
            'reviewer_style_decisions':['ACCEPT','MINOR_REVISION','MAJOR_REVISION','REJECT'],
            'major_revision_is_recoverable_rework':True,'headings_are_not_claims':True,
            'measured_and_simulated_require_verified_artifacts': True,
            'literature_claims_require_reference_linkage': True,
            'calculation_claims_require_nearby_derivation_or_artifact': True,
            'absolute_assertions_are_flagged': True,
        },
    }
    if out_json:Path(out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
