from pathlib import Path
import subprocess,shlex,json
p=Path('/tmp/nift-sidecar-experiment');r=p/'core';source=(p/'ProjectInfo.cpp').read_text();rows=[]
plans=subprocess.check_output(['make','-n','-W','src/ProjectInfo.cpp','all'],cwd=r,text=True).splitlines();compile=shlex.split(next(x for x in plans if '-c src/ProjectInfo.cpp ' in x));link=shlex.split(next(x for x in reversed(plans) if x.endswith(' -o nift')))
mutants=[('reread-certificate-bytes','certificate_valid=current&&*current==authoritative_sidecar.bytes;','if(current)authoritative_sidecar.bytes=*current;certificate_valid=current.has_value();','contracts'),('reuse-missing-edge','if(saved_edges_clean&&cached_user_dependencies_match(info,document))','if(cached_user_dependencies_match(info,document))','contracts')]
for name,old,new,suite in mutants:
 assert source.count(old)==1,(name,source.count(old));f=p/f'mutant-{name}.cpp';f.write_text(source.replace(old,new));obj=p/'mutant.o';binary=p/'nift-mutant'
 cmd=[str(f) if x=='src/ProjectInfo.cpp' else str(obj) if x=='src/ProjectInfo.o' else x for x in compile];subprocess.run(cmd,cwd=r,check=True)
 cmd=[str(obj) if x=='src/ProjectInfo.o' else str(binary) if x=='nift' else x for x in link];subprocess.run(cmd,cwd=r,check=True)
 if suite=='contracts':cmd=['python3','/home/nick/Repositories/nift/nift/tests/sidecar_state_contracts.py','--nift',str(binary),'--baseline',str(p/'nift-e2'),'--output',str(p/'mutant-contract.json')]
 else:
  text=(p/'preserved.py').read_text().replace(str(p/'nift-e3b'),str(binary)).replace(str(p/'preserved.json'),str(p/'mutant-preserved.json'));test=p/'mutant-test.py';test.write_text(text);cmd=['python3',str(test)]
 result=subprocess.run(cmd,cwd=r,capture_output=True,text=True);(p/f'mutant-{name}.txt').write_text(result.stdout+result.stderr);assert result.returncode!=0 and 'AssertionError' in result.stderr,(name,result.stdout,result.stderr)
 rows.append(dict(name=name,caught=True,returncode=result.returncode,diagnostic=result.stderr.splitlines()[-1]));(p/'mutations-extra.json').write_text(json.dumps(dict(passed=False,in_progress=True,results=rows),indent=2));print('caught',name,flush=True)
(p/'mutations-extra.json').write_text(json.dumps(dict(passed=True,caught=len(rows),missed=0,results=rows),indent=2)+'\n')
