from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from semantic.markdown_parser import parse_markdown
from audit.semantic_gate import audit
from core.plan_builder import build_plan

SAMPLE = '''# 光伏巡检机器人验证样例

# 第1章 设计与验证
## 1.1 文献事实
已有研究表明积灰会降低组件输出功率[1]。

## 1.2 样机测试
现场实测表明，缺陷识别 Recall 为 98.2%。

## 1.3 有限元分析
ANSYS 仿真结果表明最大等效应力为 24.2 MPa。

## 1.4 理论校核
$$
P=T\\omega
$$
经计算，额定转矩为 7.43 N·m。

## 1.5 设计目标
设计目标要求清扫效率不低于 95%。

# 参考文献
[1] Regression fixture reference.
'''


class SemanticGateTests(unittest.TestCase):
    def _ast(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        p = Path(td.name) / 'x.md'; p.write_text(SAMPLE, encoding='utf-8')
        return parse_markdown(p)

    def test_claim_provenance_extraction(self):
        ast = self._ast(); kinds = {c['claim_type'] for c in ast['claims']}
        self.assertTrue({'measured', 'simulated', 'calculated', 'literature', 'design_target'} <= kinds)

    def test_strict_blocks_unbacked_measured_and_simulated_claims(self):
        result = audit(self._ast(), strict=True); self.assertEqual(result['status'], 'FAIL')
        codes = {x['code'] for x in result['findings']}; self.assertIn('MEASURED_CLAIM_WITHOUT_EVIDENCE', codes); self.assertIn('SIMULATION_CLAIM_WITHOUT_EVIDENCE', codes)

    def test_verified_evidence_allows_delivery(self):
        ast=self._ast(); artifacts=[]
        for claim in ast['claims']:
            if claim['claim_type']=='measured': artifacts.append({'id':'exp-1','kind':'experiment','claim_ids':[claim['id']],'verified':True})
            elif claim['claim_type']=='simulated': artifacts.append({'id':'sim-1','kind':'solver_output','claim_ids':[claim['id']],'verified':True})
        self.assertEqual(audit(ast, {'artifacts':artifacts}, strict=True)['status'],'PASS')

    def test_full_plan_converges_reference_supply_into_semantic_gate(self):
        tasks={t.id:t for t in build_plan('full',research=True,citation_verify=True)}
        for artifact in ('REFERENCE_CANDIDATES_READY','REFERENCE_REGISTRY_READY','REFERENCE_EVIDENCE_READY','REFERENCE_CLAIM_MAP_READY','CITATION_REVIEW_READY'):
            self.assertIn(artifact,tasks['SEMANTIC_AUDIT'].requires)
        self.assertIn('SEMANTIC_GATE_PASS',tasks['OFFICE_COMPOSE'].requires)

    def test_format_only_does_not_judge_academic_substance(self):
        self.assertNotIn('SEMANTIC_AUDIT',{t.id for t in build_plan('format_only')})

    def test_heading_label_is_not_a_claim(self):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup); p=Path(td.name)/'heading.md'; p.write_text('# 第2章 分析\n## 2.3 有限元结果\n本节介绍分析方法。\n',encoding='utf-8')
        ast=parse_markdown(p); self.assertFalse(any(c['text'] in {'2.3 有限元结果','有限元结果'} for c in ast['claims']))

    def test_reviewer_returns_major_revision_not_reject_for_fixable_missing_evidence(self):
        result=audit(self._ast(),strict=True); self.assertEqual(result['review_decision'],'MAJOR_REVISION'); self.assertEqual(result['scheduler_recommendation']['produce'],['SEMANTIC_REWORK_REQUIRED'])

    def test_external_citation_major_revision_is_folded_into_semantic_review(self):
        review={'review_decision':'MAJOR_REVISION','findings':[{'severity':'major','code':'CITATION_ENTITY_MISMATCH','reference':1,'required_action':'REPLACE_OR_CORRECT_REFERENCE'}]}
        result=audit(self._ast(),citation_review=review,strict=True); self.assertEqual(result['review_decision'],'MAJOR_REVISION'); self.assertTrue(any(x['owner']=='reference_team' for x in result['findings']))

if __name__ == '__main__': unittest.main()
