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
