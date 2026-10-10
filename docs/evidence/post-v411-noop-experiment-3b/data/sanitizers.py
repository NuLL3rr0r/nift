from pathlib import Path
import shlex,subprocess,os,json
p=Path('/tmp/nift-sidecar-experiment');r=Path('/home/nick/Repositories/nift/nift');rows=[]
for kind in ['san','san-lifetime']:
 target='.build/nift-sanitize'+('-lifetime' if kind=='san-lifetime' else '')
 subprocess.run(['make','-j2',target],cwd=p/'core',check=True)
 binary=p/'core'/target
 env=os.environ|{'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}
 for suite in ['dependency_status.py','consumer_dependency_snapshots.py']:
  out=p/f'{kind}-{suite}.json';result=subprocess.run(['python3',str(r/'tests'/suite),'--nift',str(binary),'--output',str(out)],capture_output=True,text=True,env=env);(p/f'{kind}-{suite}.txt').write_text(result.stdout+result.stderr);assert result.returncode==0,(kind,suite,result.stdout,result.stderr)
 result=subprocess.run(['python3',str(r/'tests/sidecar_state_contracts.py'),'--nift',str(binary),'--baseline',str(p/'nift-e2'),'--output',str(p/f'{kind}-sidecar-contracts.json')],capture_output=True,text=True,env=env);(p/f'{kind}-sidecar-contracts.txt').write_text(result.stdout+result.stderr);assert result.returncode==0,(kind,result.stdout,result.stderr)
 rows.append(dict(kind=kind,passed=True))
(p/'sanitizers.json').write_text(json.dumps(rows,indent=2)+'\n')
