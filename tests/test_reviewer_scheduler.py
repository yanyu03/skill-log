from __future__ import annotations
import tempfile,unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.plan_builder import build_plan
from core.execution import initialize,ready,complete

class ReviewerSchedulerTests(unittest.TestCase):
    def test_major_revision_routes_to_rework_without_unlocking_office(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);(run/'state').mkdir();tasks=build_plan('full',citation_verify=True);initialize(run,tasks)
            caps={'content_extract','citation_verify','office_compose','field_refresh','render','content_rewrite'}
            complete(run,'CONFIG_VERIFY','PASS');complete(run,'TPL_RESOLVE','PASS');complete(run,'INGEST','PASS');complete(run,'SEMANTIC_PARSE','PASS');complete(run,'TEMPLATE_CONTAMINATION','PASS');complete(run,'CITATION_LOCAL','PASS');complete(run,'CITATION_VERIFY','PASS_W',['CITATION_REVIEW_READY'])
            self.assertIn('SEMANTIC_AUDIT',{x['id'] for x in ready(run,caps)})
            complete(run,'SEMANTIC_AUDIT','PASS_W',['SEMANTIC_REWORK_REQUIRED'],{'review_decision':'MAJOR_REVISION'})
            ready_ids={x['id'] for x in ready(run,caps)}
            self.assertIn('SEMANTIC_REWORK',ready_ids);self.assertNotIn('OFFICE_COMPOSE',ready_ids)

if __name__=='__main__':unittest.main()
