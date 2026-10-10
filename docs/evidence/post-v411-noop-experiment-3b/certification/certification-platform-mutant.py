from pathlib import Path
import subprocess,shlex,json
repo=Path('/home/nick/Repositories/nift/nift');p=Path('/tmp/nift-sidecar-experiment')
plans=subprocess.check_output(['make','-n','-W','src/ProjectInfo.cpp','nift'],cwd=repo,text=True).splitlines()
compile=shlex.split(next(x for x in plans if '-c src/ProjectInfo.cpp ' in x));link=shlex.split(next(x for x in reversed(plans) if x.endswith(' -o nift')))
obj=p/'certification-platform-mutant.o';binary=p/'certification-platform-mutant'
f=p/'mutant-trust-platform.cpp'
subprocess.run([str(f) if x=='src/ProjectInfo.cpp' else str(obj) if x=='src/ProjectInfo.o' else x for x in compile],cwd=repo,check=True)
subprocess.run([str(obj) if x=='src/ProjectInfo.o' else str(binary) if x=='nift' else x for x in link],cwd=repo,check=True)
r=subprocess.run(['python3','tests/sidecar_platform_contracts.py','--nift',str(binary),'--imports',str(p/'foreign-unit'),'--output',str(p/'mutant-platform.json'),'--export',str(p/'mutant-export.json')],cwd=repo,capture_output=True,text=True)
(p/'certification-platform-mutant.txt').write_text(r.stdout+r.stderr)
assert r.returncode!=0 and 'AssertionError' in r.stderr,(r.stdout,r.stderr)
(p/'certification-platform-mutant.json').write_text(json.dumps({'caught':True,'returncode':r.returncode,'source':'mutant-trust-platform.cpp','test':'sidecar_platform_contracts.py','purpose':'prove imported-provenance test detects bypass'},indent=2)+'\n')
print('Imported-provenance mutant caught')
