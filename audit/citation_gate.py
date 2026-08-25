from __future__ import annotations
import json,re
from collections import Counter
from pathlib import Path
CIT=re.compile(r'\[(\d+(?:\s*[-–—,，]\s*\d+)*)\]')
REF=re.compile(r'^\s*\[(\d+)\]\s*')


def expand(s):
    s=s.replace('，',',').replace('–','-').replace('—','-');out=set()
    for part in s.split(','):
        part=part.strip()
        if '-' in part:
            a,b=part.split('-',1)
            if a.isdigit() and b.isdigit() and int(a)<=int(b) and int(b)-int(a)<=500:out.update(range(int(a),int(b)+1))
        elif part.isdigit():out.add(int(part))
    return out


def audit_ast(ast:dict,out_json:str|Path|None=None)->dict:
    cited=set();refs=[]
    for b in ast.get('blocks',[]):
        text=b.get('text','')
        if b.get('role')!='reference_entry':
            for m in CIT.finditer(text):cited.update(expand(m.group(1)))
        if b.get('role')=='reference_entry':
            m=REF.match(text)
            if m:refs.append(int(m.group(1)))
    rs=set(refs);missing=sorted(cited-rs);orphan=sorted(rs-cited);dup=sorted(k for k,v in Counter(refs).items() if v>1);findings=[]
    if missing:findings.append({'severity':'blocker','code':'CIT-MISSING-REF','numbers':missing})
    if orphan:findings.append({'severity':'warning','code':'CIT-ORPHAN-REF','numbers':orphan})
    if dup:findings.append({'severity':'blocker','code':'CIT-DUPLICATE-NUMBER','numbers':dup})
    status='FAIL' if any(x['severity']=='blocker' for x in findings) else ('PASS_W' if findings else 'PASS')
    r={'schema':'academic-citation-local-gate/v2','status':status,'cited_numbers':sorted(cited),'reference_numbers':refs,'findings':findings,'external_verification':'NOT_RUN'}
    if out_json:Path(out_json).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    return r


def verify_evidence_conservation(evidence:dict,out_json:str|Path|None=None)->dict:
    inp=evidence.get('input_count',0);verified=evidence.get('verified_count',0);invalid=evidence.get('invalid_count',0);pending=evidence.get('pending_count',0)
    ok=inp==verified+invalid+pending
    r={'schema':'academic-citation-evidence-conservation/v1','status':'PASS' if ok else 'FAIL','input_count':inp,'verified_count':verified,'invalid_count':invalid,'pending_count':pending,'conserved':ok}
    if out_json:Path(out_json).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    return r


def review_external(report:dict, *, min_verified_english:int=0, out_json:str|Path|None=None)->dict:
    """Turn a completed external lookup into a reviewer-style decision.

    A bad reference is normally a fixable manuscript defect, not a pipeline crash. The
    provider task therefore succeeds when it completed a traceable lookup; the academic
    reviewer decides whether the manuscript needs revision.
    """
    refs=report.get('references') if isinstance(report,dict) else None
    if not isinstance(refs,list):
        result={
            'schema':'academic-citation-review/v1','status':'FAIL','review_decision':'REJECT',
            'reason':'CITATION_PROVIDER_REPORT_INVALID','findings':[{'severity':'blocker','code':'CITATION_PROVIDER_REPORT_INVALID','required_action':'RERUN_VERIFICATION'}],
            'scheduler_recommendation':{'task_status':'FAIL','produce':[]},
        }
    else:
        findings=[];verified=0;pending=0;invalid=0;english_verified=0
        bad_status={'INVALID','ENTITY_MISMATCH','MISMATCH','NOT_FOUND','REJECTED','FALSE'}
        pending_status={'PENDING','UNVERIFIED','UNKNOWN','PARTIAL'}
        for ref in refs:
            st=str(ref.get('status','')).upper()
            ok=ref.get('verified') is True or st in {'VERIFIED','PASS','ACCEPTED','VERIFIED_STRONG'}
            lang=str(ref.get('language','')).lower()
            if ok:
                verified+=1
                if lang.startswith('en') or lang=='english':english_verified+=1
            elif st in pending_status:
                pending+=1
                findings.append({'severity':'minor','code':'CITATION_UNVERIFIED','reference':ref.get('number') or ref.get('id'),'required_action':'VERIFY_OR_REPLACE','owner':'reference_team'})
            else:
                invalid+=1
                findings.append({'severity':'major','code':'CITATION_ENTITY_MISMATCH' if st in bad_status else 'CITATION_NOT_VERIFIED','reference':ref.get('number') or ref.get('id'),'required_action':'REPLACE_OR_CORRECT_REFERENCE','owner':'reference_team'})
        if english_verified < int(min_verified_english or 0):
            findings.append({'severity':'major','code':'ENGLISH_VERIFIED_MIN_NOT_MET','verified_english':english_verified,'required':int(min_verified_english),'required_action':'ADD_VERIFIED_ENGLISH_REFERENCES','owner':'reference_team'})
        if any(x['severity']=='major' for x in findings):decision='MAJOR_REVISION'
        elif findings:decision='MINOR_REVISION'
        else:decision='ACCEPT'
        status='PASS' if decision=='ACCEPT' else 'PASS_W'
        produce=['CITATION_REVIEW_READY']
        result={
            'schema':'academic-citation-review/v1','status':status,'review_decision':decision,
            'counts':{'input':len(refs),'verified':verified,'invalid':invalid,'pending':pending,'verified_english':english_verified},
            'requirements':{'min_verified_english':int(min_verified_english or 0)},'findings':findings,
            'scheduler_recommendation':{'task_status':status,'produce':produce},
        }
    if out_json:Path(out_json).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
