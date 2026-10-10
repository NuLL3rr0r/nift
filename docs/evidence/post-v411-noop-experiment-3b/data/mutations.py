from pathlib import Path
import subprocess,shlex,json
p=Path('/tmp/nift-sidecar-experiment');r=p/'core';source=(p/'ProjectInfo.cpp').read_text();rows=[]
plans=subprocess.check_output(['make','-n','-W','src/ProjectInfo.cpp','all'],cwd=r,text=True).splitlines();compile=shlex.split(next(x for x in plans if '-c src/ProjectInfo.cpp ' in x));link=shlex.split(next(x for x in reversed(plans) if x.endswith(' -o nift')))
mutants=[('skip-byte-comparison','previous_bytes!=*current','false','preserved'),('trust-version','state["version"].num!=1','false','contracts'),('trust-platform','state["platform"].string!=sidecar_platform()','false','contracts'),('trust-index-type','!value.is_number()','false','contracts'),('trust-index-range','value.num>=edges.size()','false','contracts'),('trust-duplicates','if(!first&&index<=previous)return false;','if(false)return false;','contracts'),('publish-after-hook','certificate_valid?&authoritative_sidecar:nullptr','&authoritative_sidecar','contracts')]
for name,old,new,suite in mutants:
 assert source.count(old)==1,(name,source.count(old));f=p/f'mutant-{name}.cpp';f.write_text(source.replace(old,new));obj=p/'mutant.o';binary=p/'nift-mutant'
 cmd=[str(f) if x=='src/ProjectInfo.cpp' else str(obj) if x=='src/ProjectInfo.o' else x for x in compile];subprocess.run(cmd,cwd=r,check=True)
 cmd=[str(obj) if x=='src/ProjectInfo.o' else str(binary) if x=='nift' else x for x in link];subprocess.run(cmd,cwd=r,check=True)
 if suite=='contracts':cmd=['python3','/home/nick/Repositories/nift/nift/tests/sidecar_state_contracts.py','--nift',str(binary),'--baseline',str(p/'nift-e2'),'--output',str(p/'mutant-contract.json')]
 else:
  text=(p/'preserved.py').read_text().replace(str(p/'nift-e3b'),str(binary)).replace(str(p/'preserved.json'),str(p/'mutant-preserved.json'));test=p/'mutant-test.py';test.write_text(text);cmd=['python3',str(test)]
 result=subprocess.run(cmd,cwd=r,capture_output=True,text=True);(p/f'mutant-{name}.txt').write_text(result.stdout+result.stderr);assert result.returncode!=0 and 'AssertionError' in result.stderr,(name,result.stdout,result.stderr)
 rows.append(dict(name=name,caught=True,returncode=result.returncode,diagnostic=result.stderr.splitlines()[-1]));(p/'mutations.json').write_text(json.dumps(dict(passed=False,in_progress=True,results=rows),indent=2));print('caught',name,flush=True)
(p/'mutations.json').write_text(json.dumps(dict(passed=True,caught=len(rows),missed=0,results=rows),indent=2)+'\n')
