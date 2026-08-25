from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_VERIFIED = {'VERIFIED_STRONG', 'VERIFIED', 'PASS', 'ACCEPTED'}
_PENDING = {'PENDING', 'UNVERIFIED', 'UNKNOWN', 'PARTIAL'}
_BAD = {'INVALID', 'INVALID_ENTITY_MISMATCH', 'ENTITY_MISMATCH', 'MISMATCH', 'NOT_FOUND', 'REJECTED', 'FALSE'}


def _text(v: Any) -> str:
    return str(v or '').strip()


def _status(ref: dict) -> str:
    return _text(ref.get('status')).upper()


def _is_verified(ref: dict) -> bool:
    return ref.get('verified') is True or _status(ref) in _VERIFIED


def _language(ref: dict) -> str:
    raw = _text(ref.get('language')).lower()
    if raw in {'english', 'en', 'en-us', 'en-gb'} or raw.startswith('en-'):
        return 'en'
    if raw in {'chinese', 'zh', 'zh-cn', '中文'} or raw.startswith('zh-'):
        return 'zh'
    return raw or 'unknown'


def _ref_type(ref: dict) -> str:
    return _text(ref.get('type') or ref.get('reference_type') or 'journal_article').lower()


def _stable_id(ref: dict) -> str:
    explicit = _text(ref.get('reference_id') or ref.get('candidate_id') or ref.get('id'))
    if explicit:
        return explicit
    basis = '|'.join([
        _text(ref.get('doi')).lower(),
        _text(ref.get('title')).lower(),
        _text(ref.get('year')),
        _text(ref.get('journal') or ref.get('publisher') or ref.get('institution')).lower(),
    ])
    return 'REF_' + hashlib.sha256(basis.encode('utf-8')).hexdigest()[:12].upper()


def _identity_missing(ref: dict) -> list[str]:
    missing: list[str] = []
    typ = _ref_type(ref)
    if not _text(ref.get('title')):
        missing.append('title')
    if not (ref.get('authors') or ref.get('author')):
        missing.append('authors')
    if not _text(ref.get('year')):
        missing.append('year')
    if typ in {'journal', 'journal_article', 'article'} and not _text(ref.get('journal')):
        missing.append('journal')
    if typ in {'standard', 'technical_standard'} and not _text(ref.get('standard_no') or ref.get('identifier')):
        missing.append('standard_no')
    if typ in {'thesis', 'dissertation'} and not _text(ref.get('institution')):
        missing.append('institution')
    if typ in {'book', 'monograph'} and not _text(ref.get('publisher')):
        missing.append('publisher')
    if not (_text(ref.get('doi')) or _text(ref.get('source_url')) or _text(ref.get('resolver_record_id'))):
        missing.append('provenance_locator')
    if not _text(ref.get('resolver') or ref.get('verification_source')):
        missing.append('resolver')
    return missing


def _canonical_entry(ref: dict, reference_id: str) -> dict:
    authors = ref.get('authors') or ref.get('author') or []
    if isinstance(authors, str):
        authors = [authors]
    numbers = ref.get('citation_numbers') or ([] if ref.get('number') is None else [ref.get('number')])
    numbers = [int(x) for x in numbers if str(x).isdigit()]
    return {
        'reference_id': reference_id,
        'type': _ref_type(ref),
        'title': _text(ref.get('title')),
        'authors': list(authors),
        'journal': _text(ref.get('journal')) or None,
        'publisher': _text(ref.get('publisher')) or None,
        'institution': _text(ref.get('institution')) or None,
        'year': ref.get('year'),
        'volume': ref.get('volume'),
        'issue': ref.get('issue'),
        'pages': ref.get('pages'),
        'article_number': ref.get('article_number'),
        'doi': _text(ref.get('doi')).lower() or None,
        'isbn': _text(ref.get('isbn')) or None,
        'standard_no': _text(ref.get('standard_no') or ref.get('identifier')) or None,
        'language': _language(ref),
        'source_url': _text(ref.get('source_url')) or None,
        'citation_numbers': numbers,
        'topic_tags': list(ref.get('topic_tags') or []),
        'locked': True,
    }


def _fingerprint(entry: dict) -> str:
    core = {k: entry.get(k) for k in ('type', 'title', 'authors', 'journal', 'publisher', 'institution', 'year', 'doi', 'isbn', 'standard_no')}
    raw = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def build_supply(
    report: dict,
    *,
    min_verified_english: int = 5,
    min_total_verified: int = 0,
    phase: str = 'prewrite',
    out_dir: str | Path | None = None,
) -> dict:
    """Build the only reference assets writers are allowed to consume.

    Discovery may be noisy. The locked registry is not: only itemized, externally
    verified entities with sufficient identity/provenance fields enter it. Invalid or
    pending candidates are preserved in quarantine/evidence so the next worker can
    replace them without losing audit history.
    """
    if phase not in {'prewrite', 'audit'}:
        raise ValueError('phase must be prewrite or audit')
    refs = report.get('references') if isinstance(report, dict) else None
    findings: list[dict] = []
    locked: list[dict] = []
    evidence_records: list[dict] = []
    quarantine: list[dict] = []
    claim_map: list[dict] = []
    seen_identity: dict[str, str] = {}

    if not isinstance(refs, list):
        result = {
            'schema': 'academic-reference-supply-review/v1',
            'status': 'FAIL',
            'review_decision': 'REJECT',
            'reason': 'ITEMIZED_REFERENCE_METADATA_REQUIRED',
            'findings': [{
                'severity': 'blocker', 'code': 'ITEMIZED_REFERENCE_METADATA_REQUIRED',
                'owner': 'reference_team', 'required_action': 'RERUN_ITEMIZED_ENTITY_VERIFICATION',
                'review_comment': '汇总计数不足以形成可追溯文献注册表；必须返回逐篇真实元数据和核验来源。',
            }],
            'scheduler_recommendation': {'task_status': 'FAIL', 'produce': []},
        }
        if out_dir:
            p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
            (p / 'reference_supply_review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result

    for raw in refs:
        ref = raw if isinstance(raw, dict) else {}
        rid = _stable_id(ref)
        st = _status(ref)
        used = bool(ref.get('used_in_manuscript') or ref.get('citation_numbers') or ref.get('number') is not None)
        missing = _identity_missing(ref) if _is_verified(ref) else []
        verification = {
            'reference_id': rid,
            'status': st or ('VERIFIED' if ref.get('verified') is True else 'UNKNOWN'),
            'verified': _is_verified(ref) and not missing,
            'resolver': _text(ref.get('resolver') or ref.get('verification_source')) or None,
            'lookup_key': _text(ref.get('lookup_key') or ref.get('doi') or ref.get('standard_no') or ref.get('title')) or None,
            'source_url': _text(ref.get('source_url')) or None,
            'checked_at': ref.get('checked_at') or ref.get('resolved_at'),
            'field_matches': ref.get('field_matches') or {},
            'provider_reason': ref.get('reason'),
            'used_in_manuscript': used,
        }

        if _is_verified(ref) and not missing:
            entry = _canonical_entry(ref, rid)
            fp = _fingerprint(entry)
            identity_key = entry.get('doi') or entry.get('standard_no') or fp
            if identity_key in seen_identity:
                quarantine.append({'reference_id': rid, 'status': 'DUPLICATE', 'duplicate_of': seen_identity[identity_key], 'raw_status': st})
                evidence_records.append({**verification, 'verified': False, 'status': 'DUPLICATE'})
                findings.append({'severity': 'advisory', 'code': 'REFERENCE_DUPLICATE_QUARANTINED', 'reference': rid, 'duplicate_of': seen_identity[identity_key], 'owner': 'reference_team'})
                continue
            seen_identity[identity_key] = rid
            entry['entity_fingerprint'] = fp
            locked.append(entry)
            evidence_records.append(verification)
            supports = list(ref.get('supports') or ref.get('supported_claims') or [])
            does_not_support = list(ref.get('does_not_support') or [])
            claim_map.append({
                'reference_id': rid,
                'topic_tags': entry.get('topic_tags', []),
                'supports': supports,
                'does_not_support': does_not_support,
                'scope_status': 'READY' if supports else 'MISSING_SCOPE',
            })
            if not supports:
                findings.append({'severity': 'advisory', 'code': 'REFERENCE_SUPPORT_SCOPE_MISSING', 'reference': rid, 'owner': 'reference_team', 'required_action': 'ADD_SUPPORT_SCOPE'})
            continue

        reason = 'IDENTITY_FIELDS_MISSING' if missing else ('PENDING_VERIFICATION' if st in _PENDING or not st else 'ENTITY_NOT_VERIFIED')
        if st in _BAD:
            reason = 'ENTITY_MISMATCH_OR_INVALID'
        quarantine.append({
            'reference_id': rid, 'status': st or 'UNKNOWN', 'reason': reason,
            'missing_fields': missing, 'used_in_manuscript': used,
            'candidate_title': ref.get('title'), 'citation_numbers': ref.get('citation_numbers') or ([ref.get('number')] if ref.get('number') is not None else []),
        })
        evidence_records.append({**verification, 'verified': False, 'missing_fields': missing})
        severity = 'major' if (phase == 'audit' and used) else 'advisory'
        findings.append({
            'severity': severity,
            'code': 'CITED_REFERENCE_REJECTED' if severity == 'major' else 'REFERENCE_CANDIDATE_QUARANTINED',
            'reference': rid, 'owner': 'reference_team',
            'required_action': 'REPLACE_OR_CORRECT_REFERENCE' if severity == 'major' else 'SEARCH_REPLACEMENT_IF_NEEDED',
            'reason': reason,
        })

    english_verified = sum(1 for x in locked if x.get('language') == 'en')
    if english_verified < int(min_verified_english or 0):
        findings.append({
            'severity': 'major', 'code': 'ENGLISH_VERIFIED_MIN_NOT_MET',
            'verified_english': english_verified, 'required': int(min_verified_english),
            'owner': 'reference_team', 'required_action': 'DISCOVER_AND_VERIFY_ENGLISH_REFERENCES',
        })
    if len(locked) < int(min_total_verified or 0):
        findings.append({
            'severity': 'major', 'code': 'TOTAL_VERIFIED_MIN_NOT_MET',
            'verified_total': len(locked), 'required': int(min_total_verified),
            'owner': 'reference_team', 'required_action': 'DISCOVER_AND_VERIFY_MORE_REFERENCES',
        })

    has_major = any(x.get('severity') == 'major' for x in findings)
    decision = 'MAJOR_REVISION' if has_major else 'ACCEPT'
    status = 'PASS_W' if findings else 'PASS'
    if has_major:
        status = 'PASS_W'
        produce = ['REFERENCE_REWORK_REQUIRED']
    else:
        produce = ['REFERENCE_REGISTRY_READY', 'REFERENCE_EVIDENCE_READY', 'REFERENCE_CLAIM_MAP_READY', 'CITATION_REVIEW_READY']

    registry = {
        'schema': 'academic-reference-registry/v1',
        'locked': not has_major,
        'references': sorted(locked, key=lambda x: x['reference_id']),
        'counts': {'verified_total': len(locked), 'verified_english': english_verified},
        'requirements': {'min_verified_english': int(min_verified_english or 0), 'min_total_verified': int(min_total_verified or 0)},
        'writer_contract': {
            'may_use_only_locked_reference_ids': True,
            'may_not_modify_identity_metadata': True,
            'citation_token_format': '{{CITE:REFERENCE_ID}}',
        },
    }
    registry['registry_hash'] = hashlib.sha256(json.dumps(registry['references'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    evidence = {'schema': 'academic-reference-evidence/v1', 'records': evidence_records}
    mapping = {'schema': 'academic-reference-claim-map/v1', 'references': claim_map}
    quarantine_doc = {'schema': 'academic-reference-quarantine/v1', 'references': quarantine}
    review = {
        'schema': 'academic-reference-supply-review/v1',
        'status': status,
        'review_decision': decision,
        'phase': phase,
        'counts': {
            'input': len(refs), 'locked_verified': len(locked), 'verified_english': english_verified,
            'quarantined': len(quarantine), 'support_scope_missing': sum(1 for x in claim_map if x['scope_status'] != 'READY'),
        },
        'requirements': registry['requirements'],
        'findings': findings,
        'scheduler_recommendation': {'task_status': status, 'produce': produce},
    }

    artifacts = {}
    if out_dir:
        p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
        docs = {
            'reference_registry.json': registry,
            'reference_evidence.json': evidence,
            'reference_claim_map.json': mapping,
            'reference_quarantine.json': quarantine_doc,
            'reference_supply_review.json': review,
        }
        for name, obj in docs.items():
            path = p / name
            path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
            artifacts[name] = str(path)
    review['artifacts'] = artifacts
    review['registry'] = registry
    return review
