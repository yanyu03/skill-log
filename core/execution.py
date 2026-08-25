from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .scheduler import Scheduler, Task

STATE='scheduler_state.json'
class InvalidTaskTransition(RuntimeError): pass

def _now():return datetime.now(timezone.utc).isoformat()
def initialize(run_dir:str|Path,tasks:list[Task],initial_artifacts=())->dict:
    run=Path(run_dir);p=run/'state'/STATE
    if p.exists():raise FileExistsError(p)
    obj={'schema':'academic-workflow-scheduler-state/v1','created_at':_now(),'initial_artifacts':sorted(set(initial_artifacts)),'artifacts':sorted(set(initial_artifacts)),'tasks':[t.__dict__ for t in tasks],'events':[]}
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');return obj

def load(run_dir:str|Path)->dict:return json.loads((Path(run_dir)/'state'/STATE).read_text(encoding='utf-8'))
def save(run_dir,obj): (Path(run_dir)/'state'/STATE).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def _scheduler(obj):return Scheduler(Task(**t) for t in obj['tasks'])
def ready(run_dir:str|Path,capabilities:set[str])->list[dict]:
    obj=load(run_dir);s=_scheduler(obj);avail=set(obj.get('artifacts',[]));return [t.__dict__ for t in s.ready(avail,capabilities)]

def complete(run_dir:str|Path,task_id:str,status:str,produced_artifacts=(),evidence:dict|None=None)->dict:
    obj=load(run_dir);s=_scheduler(obj)
    if task_id not in s.tasks:raise KeyError(task_id)
    t=s.tasks[task_id]
    if t.status not in {'PENDING','RUNNING'}:raise InvalidTaskTransition(f'{task_id} already terminal: {t.status}')
    available=set(obj.get('artifacts',[]))
    if status in {'PASS','PASS_W'} and not set(t.requires)<=available:
        raise InvalidTaskTransition(f'{task_id} prerequisites missing: {sorted(set(t.requires)-available)}')
    declared=set(t.produces);given=set(produced_artifacts)
    if given and not given<=declared:raise InvalidTaskTransition(f'Undeclared artifacts: {sorted(given-declared)}')
    s.set_status(task_id,status);obj['tasks']=[x.__dict__ for x in s.tasks.values()]
    if status in {'PASS','PASS_W'}:obj['artifacts']=sorted(available | (given or declared))
    obj['events'].append({'at':_now(),'task_id':task_id,'status':status,'produced':list(produced_artifacts),'evidence':evidence or {}})
    save(run_dir,obj);return obj
