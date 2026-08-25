from __future__ import annotations

import re
from typing import Iterable

CLAIM_TYPES = (
    'measured',
    'simulated',
    'calculated',
    'literature',
    'design_target',
    'interpretive',
)

_PATTERNS = {
    'measured': [
        r'现场实测', r'实测(?:结果|数据)?', r'样机(?:试验|测试)', r'试验(?:结果|数据)?表明',
        r'实验(?:结果|数据)?表明', r'测试结果表明', r'测得', r'实验证明', r'现场测试',
        r'field\s+test', r'experiment(?:al)?\s+results?', r'measured\s+',
    ],
    'simulated': [
        r'仿真(?:结果|分析)?表明', r'有限元(?:分析|结果)', r'模态(?:分析|结果)', r'仿真得到',
        r'ANSYS.{0,24}(?:结果|应力|变形|模态|云图)', r'Abaqus.{0,24}(?:结果|应力|变形)',
        r'Fluent.{0,24}(?:结果|流场|压力)', r'Simulink.{0,24}(?:结果|响应|仿真)',
        r'simulation\s+results?', r'finite[- ]element\s+(?:analysis|result)',
    ],
    'calculated': [
        r'经计算', r'计算结果(?:为|表明|得到)', r'由式.{0,24}(?:得|可得)', r'代入.{0,24}(?:得|可得)',
        r'校核结果(?:为|表明)', r'理论计算', r'安全系数(?:为|约为|达到)', r'求得', r'可计算得',
        r'calculated\s+', r'calculation\s+shows?', r'by\s+substituting',
    ],
    'literature': [
        r'研究表明', r'已有研究', r'文献(?:指出|表明|报道|认为)', r'据文献', r'相关研究',
        r'prior\s+(?:work|studies)', r'literature\s+(?:shows|reports|indicates)',
    ],
    'design_target': [
        r'设计目标', r'设计指标', r'要求(?:不低于|不高于|达到|满足)', r'目标值', r'拟达到',
        r'计划(?:达到|采用|实现)', r'应(?:达到|满足|不低于|不大于)', r'预期(?:达到|实现)',
        r'design\s+target', r'requirement', r'shall\s+',
    ],
}

_ABSOLUTE = [
    r'绝对不会', r'完全排除', r'彻底杜绝', r'彻底避免', r'根绝', r'百分之百', r'100%',
    r'零损伤', r'全生命周期.{0,16}(?:不会|无)', r'必然(?:不会|能够|实现)', r'完全保证',
    r'absolutely\s+', r'completely\s+eliminat', r'guarantee(?:d)?\s+',
]

_CIT = re.compile(r'\[(\d+(?:\s*[-–—,，]\s*\d+)*)\]')
_EVIDENCE = re.compile(r'\[\[EVIDENCE:([^\]|\s]+)(?:\|[^\]]+)?\]\]', re.I)
_SPLIT = re.compile(r'(?<=[。！？!?；;])\s*')
_NUMERIC = re.compile(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?\s*(?:%|N(?:·m|\.m)?|Pa|kPa|MPa|GPa|W|kW|r/min|rpm|mm|cm|m|kg|s|ms|Hz|°)?', re.I)


def _expand_citations(raw: str) -> list[int]:
    raw = raw.replace('，', ',').replace('–', '-').replace('—', '-')
    out: set[int] = set()
    for part in raw.split(','):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-', 1)
            if a.isdigit() and b.isdigit() and int(a) <= int(b) and int(b) - int(a) <= 500:
                out.update(range(int(a), int(b) + 1))
        elif part.isdigit():
            out.add(int(part))
    return sorted(out)


def classify_claim(text: str) -> str:
    normalized = ' '.join((text or '').split())
    for kind in ('measured', 'simulated', 'calculated', 'literature', 'design_target'):
        if any(re.search(p, normalized, re.I) for p in _PATTERNS[kind]):
            return kind
    if _CIT.search(normalized):
        return 'literature'
    return 'interpretive'


def required_evidence(kind: str) -> list[str]:
    return {
        'measured': ['experiment', 'dataset', 'raw_data', 'test_log'],
        'simulated': ['simulation', 'model', 'solver_output', 'result_figure'],
        'calculated': ['equation', 'derivation', 'calculation_record'],
        'literature': ['citation'],
        'design_target': [],
        'interpretive': [],
    }.get(kind, [])


def risk_for(kind: str, text: str) -> str:
    if kind in {'measured', 'simulated'}:
        return 'high'
    if kind in {'calculated', 'literature'}:
        return 'medium'
    if any(re.search(p, text, re.I) for p in _ABSOLUTE):
        return 'high'
    return 'low'


def extract_claims(blocks: Iterable[dict]) -> list[dict]:
    claims: list[dict] = []
    allowed = {'body', 'heading_2', 'heading_3', 'table', 'table_caption', 'figure_caption'}
    for block_index, block in enumerate(blocks):
        if block.get('role') not in allowed:
            continue
        text = ' '.join((block.get('text') or '').split())
        if not text:
            continue
        clauses = [text] if block.get('role') == 'table' else [x.strip() for x in _SPLIT.split(text) if x.strip()]
        for clause_index, clause in enumerate(clauses):
            kind = classify_claim(clause)
            absolute_terms = [p for p in _ABSOLUTE if re.search(p, clause, re.I)]
            has_numeric = bool(_NUMERIC.search(clause))
            if kind == 'interpretive' and not absolute_terms and not has_numeric:
                continue
            cites: set[int] = set()
            for m in _CIT.finditer(clause):
                cites.update(_expand_citations(m.group(1)))
            markers = [m.group(1) for m in _EVIDENCE.finditer(clause)]
            claims.append({
                'id': f'c{len(claims)+1:05d}',
                'block_id': block.get('id'),
                'block_index': block_index,
                'clause_index': clause_index,
                'claim_type': kind,
                'text': clause[:600],
                'risk': risk_for(kind, clause),
                'requires_evidence': bool(required_evidence(kind)),
                'required_evidence_kinds': required_evidence(kind),
                'citation_numbers': sorted(cites),
                'evidence_markers': markers,
                'absolute_assertion': bool(absolute_terms),
                'has_numeric': has_numeric,
                'confidence': 'heuristic',
            })
    return claims
