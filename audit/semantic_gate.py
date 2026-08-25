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


def audit(ast: dict, evidence: dict | None = None, *, strict: bool = False, out_json: str | Path | None = None) -> dict:
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
        cid = str(claim.get('id'))
        bid = str(claim.get('block_id'))
        kind = claim.get('claim_type')
        risk = claim.get('risk', 'low')
        attached = list(by_claim.get(cid, [])) + list(by_block.get(bid, []))
        for marker in claim.get('evidence_markers', []) or []:
            item = by_id.get(str(marker))
            if item:
                attached.append(item)
        attached = [x for x in attached if _is_verified(x)]
        allowed = _ALLOWED_EVIDENCE.get(kind, set())
        matched = [x for x in attached if not allowed or _kind(x) in allowed]

        supported = False
        reason = None
        if kind == 'literature':
            cited = set(claim.get('citation_numbers', []) or [])
            supported = bool(cited) and cited <= reference_numbers
            if not cited:
                reason = 'LITERATURE_CLAIM_WITHOUT_CITATION'
            elif not cited <= reference_numbers:
                reason = 'LITERATURE_CITATION_NOT_IN_REFERENCE_LIST'
        elif kind == 'calculated':
            supported = bool(matched) or _nearby_equation(ast, claim)
            if not supported:
                reason = 'CALCULATION_CLAIM_WITHOUT_DERIVATION'
        elif kind in {'measured', 'simulated'}:
            supported = bool(matched)
            if not supported:
                reason = 'MEASURED_CLAIM_WITHOUT_EVIDENCE' if kind == 'measured' else 'SIMULATION_CLAIM_WITHOUT_EVIDENCE'
        else:
            supported = True

        if supported:
            verified_claims += 1
        elif reason:
            severity = 'blocker' if strict and risk == 'high' else 'warning'
            findings.append({
                'severity': severity,
                'code': reason,
                'claim_id': cid,
                'block_id': bid,
                'claim_type': kind,
                'risk': risk,
                'text': claim.get('text', '')[:240],
            })

        if claim.get('absolute_assertion'):
            severity = 'blocker' if strict and risk == 'high' else 'warning'
            findings.append({
                'severity': severity,
                'code': 'ABSOLUTE_ASSERTION_REQUIRES_DOWNGRADE_OR_STRONG_EVIDENCE',
                'claim_id': cid,
                'block_id': bid,
                'claim_type': kind,
                'risk': risk,
                'text': claim.get('text', '')[:240],
            })

    blockers = [x for x in findings if x['severity'] == 'blocker']
    status = 'FAIL' if blockers else ('PASS_W' if findings else 'PASS')
    result = {
        'schema': 'academic-semantic-gate/v1',
        'status': status,
        'strict': strict,
        'claim_count': len(claims),
        'verified_claim_count': verified_claims,
        'unresolved_claim_count': len({x.get('claim_id') for x in findings if x.get('claim_id')}),
        'findings': findings,
        'policy': {
            'measured_and_simulated_require_verified_artifacts': True,
            'literature_claims_require_reference_linkage': True,
            'calculation_claims_require_nearby_derivation_or_artifact': True,
            'absolute_assertions_are_flagged': True,
        },
    }
    if out_json:
        Path(out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
