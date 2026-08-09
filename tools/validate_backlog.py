from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path
from collections import defaultdict,deque

def rows(path):
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def seq(ids,prefix):
    nums=[]
    for x in ids:
        m=re.fullmatch(rf"{re.escape(prefix)}-(\d{{3}})",x)
        if not m:return False
        nums.append(int(m.group(1)))
    return nums==list(range(1,len(nums)+1))
def validate(root:Path):
    g=root/'governance'
    req=rows(g/'REQUIREMENTS_INDEX.csv'); ac=rows(g/'ACCEPTANCE_CONTROL_CATALOG.csv'); eps=rows(g/'EPIC_CATALOG.csv'); tasks=rows(g/'IMPLEMENTATION_WBS.csv')
    rt=rows(g/'REQUIREMENT_TASK_TRACEABILITY.csv'); at=rows(g/'ACCEPTANCE_TASK_TRACEABILITY.csv'); deps=rows(g/'TASK_DEPENDENCIES.csv'); cp=rows(g/'CRITICAL_PATH.csv')
    phases=rows(g/'IMPLEMENTATION_PHASES.csv'); packets=rows(g/'CODEX_WORK_PACKET_QUEUE.csv'); comps=rows(g/'IMPLEMENTATION_COMPLEXITY_CLASSES.csv')
    f=[]; tids=[x['task_id'] for x in tasks]; eids=[x['epic_id'] for x in eps]; pids=[x['phase_id'] for x in phases]
    if not seq(tids,'TASK'):f.append('task IDs not unique/sequential')
    if not seq(eids,'EPIC'):f.append('epic IDs not unique/sequential')
    if len(pids)!=5 or len(set(pids))!=5:f.append('exactly five implementation phases required')
    known_t=set(tids); known_e=set(eids); known_p=set(pids); known_c={x['class_id'] for x in comps}
    for t in tasks:
        if t['epic_id'] not in known_e:f.append(f"{t['task_id']} unknown epic")
        if t['phase_id'] not in known_p:f.append(f"{t['task_id']} unknown phase")
        if t['complexity_class'] not in known_c:f.append(f"{t['task_id']} unknown complexity")
        if not t['outputs'].strip():f.append(f"{t['task_id']} missing outputs")
        if not t['requirement_ids'].strip():f.append(f"{t['task_id']} missing requirement mapping")
        if not t['acceptance_control_ids'].strip():f.append(f"{t['task_id']} missing acceptance-control mapping")
        if re.search(r'\b\d+\s*(hours?|hrs?|days?|weeks?)\b',t['notes']+' '+t['outputs'],re.I):f.append(f"{t['task_id']} contains schedule estimate")
    edge_set=set()
    adj=defaultdict(list); indeg={t:0 for t in tids}
    for e in deps:
        a,b=e['predecessor_task_id'],e['successor_task_id']
        if a not in known_t or b not in known_t:f.append(f'unknown dependency {a}->{b}');continue
        if (a,b) in edge_set:f.append(f'duplicate dependency {a}->{b}');continue
        edge_set.add((a,b));adj[a].append(b);indeg[b]+=1
    # CSV depends_on must exactly match edge table
    for t in tasks:
        listed={x for x in t['depends_on'].split(';') if x}; edge={a for a,b in edge_set if b==t['task_id']}
        if listed!=edge:f.append(f"{t['task_id']} dependency representation mismatch")
    q=deque([x for x,d in indeg.items() if d==0]); seen=[]
    while q:
        x=q.popleft();seen.append(x)
        for y in adj[x]:
            indeg[y]-=1
            if indeg[y]==0:q.append(y)
    if len(seen)!=len(tids):f.append('task dependency graph contains cycle')
    reqids={x['requirement_id'] for x in req}; mapped={x['requirement_id'] for x in rt}
    if reqids!=mapped:f.append(f'requirement-task coverage mismatch missing={sorted(reqids-mapped)[:5]} extra={sorted(mapped-reqids)[:5]}')
    acids={x['control_id'] for x in ac}; amapped={x['control_id'] for x in at}
    if acids!=amapped:f.append(f'acceptance-task coverage mismatch missing={sorted(acids-amapped)[:5]} extra={sorted(amapped-acids)[:5]}')
    for x in rt:
        if x['task_id'] not in known_t:f.append('requirement trace unknown task')
    for x in at:
        if x['task_id'] not in known_t:f.append('acceptance trace unknown task')
    cpids=[x['task_id'] for x in cp]
    if len(cpids)!=len(set(cpids)) or any(x not in known_t for x in cpids):f.append('critical path has invalid/duplicate task')
    for x in cp:
        if x['not_a_duration_estimate'].lower()!='true':f.append('critical path duration disclaimer missing')
    if not any(t['replan_gate']=='W06_REPLAN' for t in tasks):f.append('no W06 replan-provisional tasks')
    if not any(t['owner_wave']=='W06' and t['critical_dependency_gate']=='YES' for t in tasks):f.append('W06 replan gate not represented')
    plan=json.loads((root/'configs/implementation_plan.json').read_text(encoding='utf-8'))
    if len(plan['phases'])!=5 or len(plan['tasks'])!=len(tasks):f.append('JSON plan differs from CSV WBS')
    packet_epics={x['epic_id'] for x in packets}
    if packet_epics!=known_e:f.append('packet queue does not cover every epic')
    return f

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,default=Path.cwd());a=ap.parse_args(); f=validate(a.repo_root.resolve())
    if f:
        print(f'FAIL: {len(f)} backlog finding(s)');[print('-',x) for x in f];return 1
    print('PASS: five-phase WBS, stable IDs, dependency DAG, task traceability, W06 replan and Codex packet contracts')
    return 0
if __name__=='__main__':raise SystemExit(main())
