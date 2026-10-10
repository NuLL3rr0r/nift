import json,subprocess,time
from pathlib import Path
p=Path('/tmp/nift-sidecar-experiment');sha='7d36fd91133bc41f8a01ad2f046835367f2cc901';last={}
def fetch(command,target):
 r=subprocess.run(command,capture_output=True,text=True,timeout=40)
 if r.returncode:print('Transient GitHub read failure; retrying next interval',flush=True);return None
 value=json.loads(r.stdout);t=p/(target+'.tmp');t.write_text(json.dumps(value,indent=2)+'\n');t.replace(p/target);return value
while True:
 try:
  runs=fetch(['gh','run','list','--commit',sha,'--limit','40','--json','databaseId,workflowName,status,conclusion,headSha,event'],'hosted-current.json')
  if runs:
   assert len(runs)==11 and all(r['headSha']==sha for r in runs),(len(runs),runs)
   for r in runs:
    state=(r['status'],r['conclusion'])
    if last.get(r['workflowName'])!=state:print(r['databaseId'],r['workflowName'],*state,flush=True);last[r['workflowName']]=state
   native=next(r for r in runs if r['workflowName']=='E3B native sidecar certification')
   jobs=fetch(['gh','run','view',str(native['databaseId']),'--json','status,conclusion,jobs'],'native-current.json')
   if jobs:
    for j in jobs['jobs']:
     step=next((s['name'] for s in j['steps'] if s['status']=='in_progress'),'');state=(j['status'],j['conclusion'],step)
     if last.get(j['name'])!=state:print(j['databaseId'],j['name'],*state,flush=True);last[j['name']]=state
    if any(j['conclusion']=='failure' for j in jobs['jobs']):print('ACTION: Native failure requires analysis',flush=True);break
   if any(r['conclusion']=='failure' for r in runs):print('ACTION: Hosted failure requires analysis',flush=True);break
   if all(r['status']=='completed' for r in runs):print('All exact-SHA walls completed',flush=True);break
 except (subprocess.TimeoutExpired,json.JSONDecodeError):print('Transient GitHub timeout; retrying next interval',flush=True)
 time.sleep(60)
