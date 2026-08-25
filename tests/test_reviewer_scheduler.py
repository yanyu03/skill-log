from __future__ import annotations
import tempfile,unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.plan_builder import build_plan
from core.execution import initialize,ready,complete

class ReviewerSchedulerTests(unittest.TestCase):
    def test_reference_major_revision_routes_to_reference_rework_before_semantic(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);(run/'state').mkdir();tasks=build_plan('full',citation_verify=True);initialize(run,tasks)
            caps={'content_extract','citation_verify','research','office_compose','field_refresh','render','content_rewrite'}
            complete(run,'CONFIG_VERIFY','PASS');complete(run,'TPL_RESOLVE','PASS');complete(run,'INGEST','PASS');complete(run,'SEMANTIC_PARSE','PASS');complete(run,'TEMPLATE_CONTAMINATION','PASS');complete(run,'CITATION_LOCAL','PASS');complete(run,'CITATION_VERIFY','PASS',['REFERENCE_RESOLUTION_READY'])
            self.assertIn('REFERENCE_LOCK',{x['id'] for x in ready(run,caps)})
            complete(run,'REFERENCE_LOCK','PASS_W',['REFERENCE_REWORK_REQUIRED'],{'review_decision':'MAJOR_REVISION'})
            ready_ids={x['id'] for x in ready(run,caps)}
            self.assertIn('REFERENCE_REWORK',ready_ids);self.assertNotIn('SEMANTIC_AUDIT',ready_ids);self.assertNotIn('OFFICE_COMPOSE',ready_ids)

if __name__=='__main__':unittest.main()
