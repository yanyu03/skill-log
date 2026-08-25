#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from core.run_workspace import create_run, verify_run_baseline
from core.config_lock import verify_lock
from core.scheduler import Scheduler
from core.plan_builder import build_plan
from core.execution import initialize as scheduler_initialize, ready as scheduler_ready, complete as scheduler_complete
from template_compiler.compiler import compile_template
from ingest.markitdown_adapter import capabilities as markitdown_capabilities, convert as markitdown_convert
from semantic.markdown_parser import parse_markdown
from semantic.inventory import inventory_ast
from audit.content_gate import compare as compare_content
from office.job_contract import build as build_office_job
from office.providers.microsoft import declared_capabilities as ms_caps
from office.providers.wps import declared_capabilities as wps_caps
from audit.citation_gate import audit_ast as citation_local_audit
from audit.template_contamination_gate import audit_ast as contamination_audit
from figures.assets import prepare as prepare_figures
from office.provider_registry import select as select_provider, load_manifests
from core.gates import record as record_gate, final_gate
from audit.structure_gate import audit as structure_audit
from audit.template_gate import audit as template_audit
from audit.visual_gate import prepare_review as visual_prepare, evaluate as visual_evaluate
from office.host_bridge import dispatch as office_dispatch, accept_response as office_accept
from office.result_validator import validate_job_result
from office.acceptance import evaluate as provider_acceptance
from office.provider_binding import bind as provider_bind, unbound as provider_unbound
from core.recovery import inspect as recovery_inspect
from core.delivery import package as delivery_package
from audit.font_preflight import requirements as font_requirements, evaluate as font_evaluate
from audit.semantic_gate import audit as semantic_audit
from references.supply_chain import build_supply as build_reference_supply


def emit(x):print(json.dumps(x,ensure_ascii=False,indent=2))
def caps_to_dict(c):return {'provider':c.provider,'actions':sorted(c.actions),'metadata':c.metadata}

def main():
    p=argparse.ArgumentParser(prog='academic-workflow-engine');s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('compile-template');q.add_argument('--source',required=True);q.add_argument('--out',required=True);q.add_argument('--template-id',required=True);q.add_argument('--version',default='1.0.0')
    q=s.add_parser('verify-template');q.add_argument('--template-pack',required=True)
    q=s.add_parser('init-run');q.add_argument('--template-pack',required=True);q.add_argument('--runs-root',default=str(ROOT/'runs'));q.add_argument('--run-id')
    q=s.add_parser('verify-run');q.add_argument('--run-dir',required=True)
    q=s.add_parser('plan');q.add_argument('--mode',default='full');q.add_argument('--figures',action='store_true');q.add_argument('--research',action='store_true');q.add_argument('--citation-verify',action='store_true');q.add_argument('--no-roundtrip',action='store_true');q.add_argument('--no-semantic-validate',action='store_true');q.add_argument('--out')
    q=s.add_parser('scheduler-init');q.add_argument('--run-dir',required=True);q.add_argument('--mode',default='full');q.add_argument('--figures',action='store_true');q.add_argument('--research',action='store_true');q.add_argument('--citation-verify',action='store_true');q.add_argument('--no-roundtrip',action='store_true');q.add_argument('--no-semantic-validate',action='store_true')
    q=s.add_parser('scheduler-ready');q.add_argument('--run-dir',required=True);q.add_argument('--capabilities',default='')
    q=s.add_parser('scheduler-complete');q.add_argument('--run-dir',required=True);q.add_argument('--task',required=True);q.add_argument('--status',required=True);q.add_argument('--produced',default='');q.add_argument('--evidence')
    q=s.add_parser('capabilities')
    q=s.add_parser('ingest');q.add_argument('--input',required=True);q.add_argument('--out',required=True)
    q=s.add_parser('semantic-parse');q.add_argument('--input',required=True);q.add_argument('--out',required=True);q.add_argument('--inventory')
    q=s.add_parser('office-job');q.add_argument('--ast',required=True);q.add_argument('--run-config',required=True);q.add_argument('--out',required=True);q.add_argument('--provider',default='auto')
    q=s.add_parser('content-gate');q.add_argument('--expected',required=True);q.add_argument('--actual',required=True);q.add_argument('--out')
    q=s.add_parser('citation-local');q.add_argument('--ast',required=True);q.add_argument('--out')
    q=s.add_parser('citation-review');q.add_argument('--report',required=True);q.add_argument('--min-verified-english',type=int,default=0);q.add_argument('--out')
    q=s.add_parser('reference-lock');q.add_argument('--report',required=True);q.add_argument('--out-dir',required=True);q.add_argument('--phase',choices=['prewrite','audit'],default='prewrite');q.add_argument('--min-verified-english',type=int,default=5);q.add_argument('--min-total-verified',type=int,default=0)
    q=s.add_parser('semantic-gate');q.add_argument('--ast',required=True);q.add_argument('--evidence');q.add_argument('--citation-review');q.add_argument('--strict',action='store_true');q.add_argument('--out')
    q=s.add_parser('figure-prep');q.add_argument('--ast',required=True);q.add_argument('--asset-root',required=True);q.add_argument('--out-dir',required=True);q.add_argument('--manifest')
    q=s.add_parser('template-contamination');q.add_argument('--ast',required=True);q.add_argument('--discarded-hashes',required=True);q.add_argument('--out')
    q=s.add_parser('provider-select');q.add_argument('--job',required=True);q.add_argument('--providers',required=True);q.add_argument('--preference',default='')
    q=s.add_parser('gate-record');q.add_argument('--run-dir',required=True);q.add_argument('--gate',required=True);q.add_argument('--status',required=True);q.add_argument('--evidence')
    q=s.add_parser('final-gate');q.add_argument('--run-dir',required=True)
    q=s.add_parser('structure-gate');q.add_argument('--docx',required=True);q.add_argument('--ast',required=True);q.add_argument('--job');q.add_argument('--out')
    q=s.add_parser('template-gate');q.add_argument('--docx',required=True);q.add_argument('--ast',required=True);q.add_argument('--config',required=True);q.add_argument('--job');q.add_argument('--out')
    q=s.add_parser('visual-prepare');q.add_argument('--pdf',required=True);q.add_argument('--out-dir',required=True);q.add_argument('--out')
    q=s.add_parser('visual-gate');q.add_argument('--review-pack',required=True);q.add_argument('--reviewer');q.add_argument('--out')
    q=s.add_parser('provider-dispatch');q.add_argument('--job',required=True);q.add_argument('--provider',required=True);q.add_argument('--run-dir',required=True);q.add_argument('--out')
    q=s.add_parser('provider-accept');q.add_argument('--response',required=True);q.add_argument('--run-dir',required=True);q.add_argument('--out')
    q=s.add_parser('provider-result-validate');q.add_argument('--job',required=True);q.add_argument('--response',required=True)
    q=s.add_parser('provider-acceptance');q.add_argument('--provider-id',required=True);q.add_argument('--job',required=True);q.add_argument('--office-result',required=True);q.add_argument('--structure',required=True);q.add_argument('--template',required=True);q.add_argument('--visual',required=True);q.add_argument('--content');q.add_argument('--font-preflight');q.add_argument('--out')
    q=s.add_parser('provider-bind');q.add_argument('--provider-id',required=True);q.add_argument('--family',required=True);q.add_argument('--actions',required=True);q.add_argument('--binding-ref',required=True);q.add_argument('--acceptance',required=True);q.add_argument('--out',required=True)
    q=s.add_parser('provider-unbound');q.add_argument('--provider-id',required=True);q.add_argument('--family',required=True);q.add_argument('--actions',required=True);q.add_argument('--out',required=True);q.add_argument('--reason',default='NOT_CONNECTED')
    q=s.add_parser('recovery');q.add_argument('--run-dir',required=True);q.add_argument('--capabilities',default='')
    q=s.add_parser('delivery');q.add_argument('--run-dir',required=True);q.add_argument('--artifacts',required=True);q.add_argument('--out')
    q=s.add_parser('font-requirements');q.add_argument('--config',required=True);q.add_argument('--out')
    q=s.add_parser('font-preflight');q.add_argument('--requirements',required=True);q.add_argument('--provider-report');q.add_argument('--out')
    a=p.parse_args()
    if a.cmd=='compile-template':emit(compile_template(a.source,a.out,a.template_id,a.version))
    elif a.cmd=='verify-template':emit(verify_lock(a.template_pack))
    elif a.cmd=='init-run':emit(create_run(a.runs_root,a.template_pack,a.run_id))
    elif a.cmd=='verify-run':emit(verify_run_baseline(a.run_dir))
    elif a.cmd=='plan':
        tasks=build_plan(a.mode,has_figures=a.figures,research=a.research,citation_verify=a.citation_verify,roundtrip=not a.no_roundtrip,semantic_validate=not a.no_semantic_validate); obj={'schema':'academic-workflow-plan/v3','mode':a.mode,'semantic_validate':not a.no_semantic_validate,'tasks':[t.__dict__ for t in tasks]}
        if a.out:Path(a.out).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
        emit(obj)
    elif a.cmd=='scheduler-init':
        tasks=build_plan(a.mode,has_figures=a.figures,research=a.research,citation_verify=a.citation_verify,roundtrip=not a.no_roundtrip,semantic_validate=not a.no_semantic_validate);emit(scheduler_initialize(a.run_dir,tasks))
    elif a.cmd=='scheduler-ready':emit({'ready':scheduler_ready(a.run_dir,set(filter(None,(x.strip() for x in a.capabilities.split(',')))) )})
    elif a.cmd=='scheduler-complete':
        ev=json.loads(Path(a.evidence).read_text(encoding='utf-8')) if a.evidence else None
        emit(scheduler_complete(a.run_dir,a.task,a.status,list(filter(None,(x.strip() for x in a.produced.split(',')))),ev))
    elif a.cmd=='capabilities':emit({'markitdown':markitdown_capabilities(),'office':{'microsoft':caps_to_dict(ms_caps()),'wps':caps_to_dict(wps_caps())}})
    elif a.cmd=='ingest':emit(markitdown_convert(a.input,a.out))
    elif a.cmd=='semantic-parse':
        ast=parse_markdown(a.input,a.out); result={'status':'PASS','ast':a.out,'blocks':len(ast['blocks']),'engineering_conditions':len(ast['engineering_conditions']),'claims':len(ast.get('claims',[]))}
        if a.inventory: inventory_ast(ast,a.inventory); result['inventory']=a.inventory
        emit(result)
    elif a.cmd=='office-job':emit(build_office_job(json.loads(Path(a.ast).read_text(encoding='utf-8')),a.run_config,a.out,a.provider))
    elif a.cmd=='content-gate':
        r=compare_content(json.loads(Path(a.expected).read_text(encoding='utf-8')),json.loads(Path(a.actual).read_text(encoding='utf-8')),a.out);emit(r);raise SystemExit(0 if r['status']=='PASS' else 2)
    elif a.cmd=='citation-local':
        r=citation_local_audit(json.loads(Path(a.ast).read_text(encoding='utf-8')),a.out);emit(r);raise SystemExit(2 if r['status']=='FAIL' else 0)
    elif a.cmd=='citation-review':
        from audit.citation_gate import review_external
        r=review_external(json.loads(Path(a.report).read_text(encoding='utf-8')),min_verified_english=a.min_verified_english,out_json=a.out);emit(r);raise SystemExit(2 if r['status']=='FAIL' else 0)
    elif a.cmd=='reference-lock':
        r=build_reference_supply(json.loads(Path(a.report).read_text(encoding='utf-8')),min_verified_english=a.min_verified_english,min_total_verified=a.min_total_verified,phase=a.phase,out_dir=a.out_dir);emit(r);raise SystemExit(2 if r['status']=='FAIL' else 0)
    elif a.cmd=='semantic-gate':
        ast=json.loads(Path(a.ast).read_text(encoding='utf-8')); evidence=json.loads(Path(a.evidence).read_text(encoding='utf-8')) if a.evidence else None
        citation_review=json.loads(Path(a.citation_review).read_text(encoding='utf-8')) if a.citation_review else None
        r=semantic_audit(ast,evidence,citation_review=citation_review,strict=a.strict,out_json=a.out);emit(r);raise SystemExit(0 if r['status'] in {'PASS','PASS_W'} else 2)
    elif a.cmd=='figure-prep':
        r=prepare_figures(json.loads(Path(a.ast).read_text(encoding='utf-8')),a.asset_root,a.out_dir,a.manifest);emit(r);raise SystemExit(2 if r['status']=='FAIL' else 0)
    elif a.cmd=='template-contamination':
        r=contamination_audit(json.loads(Path(a.ast).read_text(encoding='utf-8')),a.discarded_hashes,a.out);emit(r);raise SystemExit(2 if r['status']=='FAIL' else 0)
    elif a.cmd=='provider-select':
        job=json.loads(Path(a.job).read_text(encoding='utf-8'));r=select_provider(set(job.get('required_actions',[])),load_manifests(a.providers),list(filter(None,(x.strip() for x in a.preference.split(',')))));emit(r);raise SystemExit(0 if r['status']=='PASS' else 3)
    elif a.cmd=='gate-record':
        ev=json.loads(Path(a.evidence).read_text(encoding='utf-8')) if a.evidence else {};emit(record_gate(a.run_dir,a.gate,a.status,ev))
    elif a.cmd=='final-gate':
        r=final_gate(a.run_dir);emit(r);raise SystemExit(0 if r['status']=='PASS' else 2)
    elif a.cmd=='structure-gate':
        ast=json.loads(Path(a.ast).read_text(encoding='utf-8'));job=json.loads(Path(a.job).read_text(encoding='utf-8')) if a.job else None;r=structure_audit(a.docx,ast,job,a.out);emit(r);raise SystemExit(0 if r['status'] in {'PASS','PASS_W'} else 2)
    elif a.cmd=='template-gate':
        ast=json.loads(Path(a.ast).read_text(encoding='utf-8'));job=json.loads(Path(a.job).read_text(encoding='utf-8')) if a.job else None;r=template_audit(a.docx,ast,a.config,job=job,out_json=a.out);emit(r);raise SystemExit(0 if r['status'] in {'PASS','PASS_W'} else 2)
    elif a.cmd=='visual-prepare':emit(visual_prepare(a.pdf,a.out_dir,a.out))
    elif a.cmd=='visual-gate':
        pack=json.loads(Path(a.review_pack).read_text(encoding='utf-8'));reviewer=json.loads(Path(a.reviewer).read_text(encoding='utf-8')) if a.reviewer else None;r=visual_evaluate(pack,reviewer,a.out);emit(r);raise SystemExit(0 if r['status'] in {'PASS','PASS_W'} else 2)
    elif a.cmd=='provider-dispatch':
        job=json.loads(Path(a.job).read_text(encoding='utf-8'));provider=json.loads(Path(a.provider).read_text(encoding='utf-8'));r=office_dispatch(job,provider,a.run_dir,a.out);emit(r);raise SystemExit(0 if r['status']=='WAITING_EXTERNAL_PROVIDER' else 3)
    elif a.cmd=='provider-accept':emit(office_accept(json.loads(Path(a.response).read_text(encoding='utf-8')),a.run_dir,a.out))
    elif a.cmd=='provider-result-validate':
        r=validate_job_result(json.loads(Path(a.job).read_text(encoding='utf-8')),json.loads(Path(a.response).read_text(encoding='utf-8')));emit(r);raise SystemExit(0 if r['status']=='PASS' else 2)
    elif a.cmd=='provider-acceptance':
        load=lambda x:json.loads(Path(x).read_text(encoding='utf-8'));r=provider_acceptance(a.provider_id,load(a.job),load(a.office_result),load(a.structure),load(a.template),load(a.visual),load(a.content) if a.content else None,load(a.font_preflight) if a.font_preflight else None,a.out);emit(r);raise SystemExit(0 if r['status']=='PASS' else 2)
    elif a.cmd=='provider-bind':
        ac=json.loads(Path(a.acceptance).read_text(encoding='utf-8'));emit(provider_bind(a.provider_id,a.family,list(filter(None,(x.strip() for x in a.actions.split(',')))),a.binding_ref,a.out,ac))
    elif a.cmd=='provider-unbound':emit(provider_unbound(a.provider_id,a.family,list(filter(None,(x.strip() for x in a.actions.split(',')))),a.out,a.reason))
    elif a.cmd=='recovery':emit(recovery_inspect(a.run_dir,set(filter(None,(x.strip() for x in a.capabilities.split(','))))))
    elif a.cmd=='delivery':
        arts=json.loads(Path(a.artifacts).read_text(encoding='utf-8'));emit(delivery_package(a.run_dir,arts,a.out))
    elif a.cmd=='font-requirements':
        r=font_requirements(a.config);
        if a.out:Path(a.out).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        emit(r)
    elif a.cmd=='font-preflight':
        req=json.loads(Path(a.requirements).read_text(encoding='utf-8'));report=json.loads(Path(a.provider_report).read_text(encoding='utf-8')) if a.provider_report else None;r=font_evaluate(req,report,a.out);emit(r);raise SystemExit(0 if r['status'] in {'PASS','PASS_W'} else 2)
if __name__=='__main__':main()
