from __future__ import annotations
from pathlib import Path
import csv, json
from typing import Iterable
from .contracts import SourceRecord

class CsvSourceAdapter:
    def __init__(self, source_id:str, dataset:str): self.source_id=source_id; self.dataset=dataset
    def read(self, path:Path)->tuple[SourceRecord,...]:
        with path.open(newline='',encoding='utf-8-sig') as fh:
            rows=[]
            for i,row in enumerate(csv.DictReader(fh),start=1):
                rows.append(SourceRecord(self.source_id,self.dataset,i,dict(row)))
        return tuple(rows)

class JsonSourceAdapter:
    def __init__(self, source_id:str, dataset:str): self.source_id=source_id; self.dataset=dataset
    def read(self, path:Path)->tuple[SourceRecord,...]:
        obj=json.loads(path.read_text(encoding='utf-8'))
        seq=obj if isinstance(obj,list) else [obj]
        if not all(isinstance(x,dict) for x in seq): raise ValueError('JSON source must contain object rows')
        return tuple(SourceRecord(self.source_id,self.dataset,i+1,dict(x)) for i,x in enumerate(seq))
