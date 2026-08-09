from __future__ import annotations
import argparse,csv,json,sys
sys.dont_write_bytecode=True
from collections import defaultdict
from pathlib import Path

def merge_type(old,new):
    if old in {None,"NULL"}: return new
    if new=="NULL": return old
    if old==new:return old
    numeric={"INTEGER","FLOAT"}
    if old in numeric and new in numeric:return "FLOAT"
    return "MIXED"

def type_of(v):
    if v is None or v=="": return "NULL"
    if isinstance(v,bool):return "BOOLEAN"
    if isinstance(v,int) and not isinstance(v,bool):return "INTEGER"
    if isinstance(v,float):return "FLOAT"
    if isinstance(v,(dict,list)):return "OBJECT" if isinstance(v,dict) else "ARRAY"
    s=str(v)
    try:int(s);return "INTEGER"
    except:pass
    try:float(s);return "FLOAT"
    except:pass
    if s.lower() in {"true","false"}:return "BOOLEAN"
    return "STRING"

def flatten(obj,prefix=""):
    if isinstance(obj,dict):
        for k,v in obj.items():
            p=f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v,dict): yield from flatten(v,p)
            else: yield p,v
    else: yield prefix or "$",obj

def _scan_records(records,max_records):
    stats=defaultdict(lambda:{"observed_type":None,"non_null":0,"missing":0})
    seen=0
    all_fields=set()
    for rec in records:
        if seen>=max_records:break
        flat=dict(flatten(rec)) if isinstance(rec,dict) else {"$":rec}
        all_fields.update(flat)
        for p in all_fields:
            v=flat.get(p)
            t=type_of(v)
            stats[p]["observed_type"]=merge_type(stats[p]["observed_type"],t)
            if t=="NULL":stats[p]["missing"]+=1
            else:stats[p]["non_null"]+=1
        seen+=1
    # fields discovered late need missing counts for prior rows
    for p,s in stats.items():
        accounted=s["non_null"]+s["missing"]
        if accounted<seen:s["missing"]+=seen-accounted
    return seen,[{"field_path":p,**stats[p]} for p in sorted(stats)]

def scan(path:Path,max_records=10000):
    suffix=path.suffix.lower()
    if suffix=='.csv':
        with path.open(newline='',encoding='utf-8-sig') as fh:
            reader=csv.DictReader(fh); seen,fields=_scan_records(reader,max_records)
        fmt='CSV'
    elif suffix in {'.jsonl','.ndjson'}:
        def it():
            with path.open(encoding='utf-8') as fh:
                for line in fh:
                    if line.strip():yield json.loads(line)
        seen,fields=_scan_records(it(),max_records); fmt='JSONL'
    elif suffix=='.json':
        obj=json.loads(path.read_text(encoding='utf-8'))
        records=obj if isinstance(obj,list) else [obj]
        seen,fields=_scan_records(iter(records),max_records); fmt='JSON'
    elif suffix=='.parquet':
        try: import pyarrow.parquet as pq
        except ImportError as exc: raise RuntimeError('Parquet scanning is optional; install pyarrow in an approved later environment') from exc
        table=pq.read_table(path)
        records=table.to_pylist(); seen,fields=_scan_records(iter(records),max_records); fmt='PARQUET'
    else: raise ValueError(f'unsupported format: {suffix}')
    return {'path':path.as_posix(),'format':fmt,'records_scanned':seen,'fields':fields}

def signature(result):
    return tuple((x['field_path'],x['observed_type']) for x in result['fields'])

def compare(old,new):
    a=dict(signature(old)); b=dict(signature(new))
    return {'added':sorted(set(b)-set(a)),'removed':sorted(set(a)-set(b)),'type_changed':sorted(k for k in set(a)&set(b) if a[k]!=b[k])}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('path',type=Path);ap.add_argument('--max-records',type=int,default=10000);ap.add_argument('--output',type=Path)
    args=ap.parse_args(); out=scan(args.path,args.max_records); text=json.dumps(out,indent=2)+'\n'
    if args.output: args.output.write_text(text,encoding='utf-8')
    else: print(text,end='')
if __name__=='__main__':main()
