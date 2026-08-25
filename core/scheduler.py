from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Iterable

TERMINAL={'PASS','PASS_W','FAIL','SKIPPED'}

@dataclass
class Task:
    id:str
    requires:list[str]
    produces:list[str]
    capability_requirements:list[str]
    status:str='PENDING'

class Scheduler:
    def __init__(self,tasks:Iterable[Task]):
        self.tasks={t.id:t for t in tasks}
    def ready(self,available:set[str],capabilities:set[str]) -> list[Task]:
        return [t for t in self.tasks.values() if t.status=='PENDING' and set(t.requires)<=available and set(t.capability_requirements)<=capabilities]
    def set_status(self,task_id:str,status:str):
        if status not in TERMINAL|{'RUNNING'}: raise ValueError(status)
        self.tasks[task_id].status=status
    def available_artifacts(self,initial:Iterable[str]=()) -> set[str]:
        out=set(initial)
        for t in self.tasks.values():
            if t.status in {'PASS','PASS_W'}:out.update(t.produces)
        return out
    def dump(self,path:str|Path):
        Path(path).write_text(json.dumps({'schema':'academic-workflow-plan/v1','tasks':[asdict(t) for t in self.tasks.values()]},ensure_ascii=False,indent=2),encoding='utf-8')

def default_full_plan() -> list[Task]:
    return [
        Task('TPL_RESOLVE',[],['TEMPLATE_READY'],[]),
        Task('INGEST',[],['NORMALIZED_CONTENT'],['content_extract']),
        Task('SEMANTIC_PARSE',['NORMALIZED_CONTENT'],['CONTENT_READY'],[]),
        Task('RESEARCH',['CONTENT_READY'],['RESEARCH_READY'],['research']),
        Task('CITATION',['CONTENT_READY'],['CITATION_READY'],['citation_verify']),
        Task('OFFICE_COMPOSE',['TEMPLATE_READY','CONTENT_READY'],['DOCX_READY'],['office_compose']),
        Task('FIELD_REFRESH',['DOCX_READY'],['FIELDS_READY'],['field_refresh']),
        Task('STRUCTURE_AUDIT',['FIELDS_READY'],['STRUCTURE_READY'],[]),
        Task('RENDER',['FIELDS_READY'],['RENDER_READY'],['render']),
        Task('ROUNDTRIP',['FIELDS_READY'],['ROUNDTRIP_READY'],['content_extract']),
        Task('FINAL_GATES',['STRUCTURE_READY','RENDER_READY','ROUNDTRIP_READY'],['DELIVERY_READY'],[]),
    ]
