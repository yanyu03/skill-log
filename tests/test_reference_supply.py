from __future__ import annotations
import json, tempfile, unittest, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from references.supply_chain import build_supply
from core.plan_builder import build_plan


def good(ref_id, lang='en', number=None):
    d={
        'reference_id':ref_id,'type':'journal_article','status':'VERIFIED_STRONG','verified':True,
        'language':lang,'title':f'Real paper {ref_id}','authors':['A. Author'],
        'journal':'Verified Journal','year':2025,'doi':f'10.1000/{ref_id.lower()}',
        'source_url':f'https://publisher.example/{ref_id}','resolver':'publisher',
        'checked_at':'2026-08-25','supports':['background','mechanical design'],
    }
    if number is not None:d['number']=number
    return d


def bad(ref_id, number, reason='ENTITY_MISMATCH'):
    return {
        'reference_id':ref_id,'number':number,'status':reason,'verified':False,'language':'en',
        'title':f'Wrong candidate {ref_id}','resolver':'publisher','source_url':'https://publisher.example/mismatch',
        'reason':'resolved metadata does not match manuscript entry',
    }


class ReferenceSupplyTests(unittest.TestCase):
    def test_prewrite_quarantines_bad_candidates_but_publishes_clean_registry(self):
        report={'references':[good(f'REF_{i}', 'en' if i<=5 else 'zh') for i in range(1,8)] + [bad('REF_14',14),bad('REF_17',17),bad('REF_19',19)]}
        for r in report['references'][-3:]:r.pop('number',None)
        with tempfile.TemporaryDirectory() as td:
            out=build_supply(report,min_verified_english=5,phase='prewrite',out_dir=td)
            self.assertEqual(out['review_decision'],'ACCEPT')
            self.assertEqual(out['counts']['locked_verified'],7)
            self.assertEqual(out['counts']['verified_english'],5)
            self.assertEqual(out['counts']['quarantined'],3)
            self.assertIn('REFERENCE_REGISTRY_READY',out['scheduler_recommendation']['produce'])
            reg=json.loads((Path(td)/'reference_registry.json').read_text(encoding='utf-8'))
            ids={x['reference_id'] for x in reg['references']}
            self.assertFalse({'REF_14','REF_17','REF_19'} & ids)
            self.assertTrue(reg['locked'])
            self.assertTrue(all(x['locked'] for x in reg['references']))

    def test_audit_cited_mismatches_force_reference_rework(self):
        report={'references':[good(f'REF_{i}', 'en' if i<=5 else 'zh', i) for i in range(1,8)] + [bad('REF_14',14),bad('REF_17',17),bad('REF_19',19)]}
        out=build_supply(report,min_verified_english=5,phase='audit')
        self.assertEqual(out['review_decision'],'MAJOR_REVISION')
        self.assertEqual(out['scheduler_recommendation']['produce'],['REFERENCE_REWORK_REQUIRED'])
        codes=[x['code'] for x in out['findings']]
        self.assertEqual(codes.count('CITED_REFERENCE_REJECTED'),3)
        self.assertFalse(out['registry']['locked'])

    def test_english_minimum_is_on_verified_registry_not_candidate_strings(self):
        report={'references':[good('REF_1','en'),good('REF_2','en'),good('REF_3','en'),good('REF_4','zh'),good('REF_5','zh')]}
        out=build_supply(report,min_verified_english=5,phase='prewrite')
        self.assertEqual(out['review_decision'],'MAJOR_REVISION')
        self.assertTrue(any(x['code']=='ENGLISH_VERIFIED_MIN_NOT_MET' for x in out['findings']))

    def test_legacy_aggregate_cannot_be_locked_for_downstream(self):
        out=build_supply({'input_count':20,'verified_count':5,'invalid_count':3,'pending_count':12},min_verified_english=5)
        self.assertEqual(out['review_decision'],'REJECT')
        self.assertEqual(out['reason'],'ITEMIZED_REFERENCE_METADATA_REQUIRED')

    def test_full_plan_requires_reference_assets_before_semantic_and_office(self):
        tasks={t.id:t for t in build_plan('full',research=True,citation_verify=True)}
        self.assertIn('REFERENCE_LOCK',tasks)
        self.assertIn('REFERENCE_REWORK',tasks)
        self.assertIn('REFERENCE_REVERIFY',tasks)
        self.assertIn('REFERENCE_RELOCK',tasks)
        for artifact in ('REFERENCE_REGISTRY_READY','REFERENCE_EVIDENCE_READY','REFERENCE_CLAIM_MAP_READY','CITATION_REVIEW_READY'):
            self.assertIn(artifact,tasks['SEMANTIC_AUDIT'].requires)
        self.assertIn('REFERENCE_REGISTRY_READY',tasks['OFFICE_COMPOSE'].requires)

if __name__=='__main__':unittest.main()
