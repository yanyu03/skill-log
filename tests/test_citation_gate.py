from __future__ import annotations
import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from audit.citation_gate import audit_ast,verify_evidence_conservation,review_external
class CitationGateTests(unittest.TestCase):
    def test_local_bijection(self):
        ast={'blocks':[{'role':'body','text':'Prior work [1-2].'},{'role':'reference_entry','text':'[1] A'},{'role':'reference_entry','text':'[2] B'}]}
        self.assertEqual(audit_ast(ast)['status'],'PASS');ast['blocks'].pop();self.assertEqual(audit_ast(ast)['status'],'FAIL')
    def test_evidence_conservation(self):
        self.assertEqual(verify_evidence_conservation({'input_count':10,'verified_count':7,'invalid_count':1,'pending_count':2})['status'],'PASS')
        self.assertEqual(verify_evidence_conservation({'input_count':10,'verified_count':7,'invalid_count':1,'pending_count':1})['status'],'FAIL')
    def test_external_mismatch_is_recoverable_major_revision(self):
        report={'references':[{'number':1,'language':'en','status':'VERIFIED','verified':True},{'number':2,'language':'en','status':'ENTITY_MISMATCH','verified':False}]}
        r=review_external(report,min_verified_english=1);self.assertEqual(r['status'],'PASS_W');self.assertEqual(r['review_decision'],'MAJOR_REVISION');self.assertEqual(r['scheduler_recommendation']['produce'],['CITATION_REVIEW_READY'])
if __name__=='__main__':unittest.main()
