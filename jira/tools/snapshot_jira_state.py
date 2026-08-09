import sys
sys.dont_write_bytecode = True
from datetime import datetime,timezone
import hashlib,json
from jira_pack_lib import JIRA_ROOT, load_records, rebuild_file_manifest
records=load_records(); now=datetime.now(timezone.utc); sid=now.strftime('%Y%m%dT%H%M%SZ')
state=[{'local_id':r['local_id'],'jira_key':r.get('jira_key',''),'workflow_state':r.get('workflow_state',''),'maturity_after':r.get('expected_maturity_after_completion',''),'evidence_state':r.get('evidence_state',''),'ready':r.get('ready',False)} for r in sorted(records,key=lambda x:x['local_id'])]
payload={'snapshot_id':sid,'generated_at':now.isoformat(),'schema_version':1,'issues':state,'sha256':hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest()}
out=JIRA_ROOT/'snapshots'/sid/'STATE.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
rebuild_file_manifest(); print(out)
