"""Exact reviewed S0 differential, independent baseline and native AST contracts."""
from pathlib import Path
import argparse,subprocess,os,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
BASE='639797175ed026dc2918ba713906f28309c1e971'
EXPECTED={'Ast.h':'f206bff461cb9a7b530a5ddb45c43185891e5b9d56fe23c5e13504f49a2d90c4','Ast.cpp':'268e336a544fcf9bf92f4d6b3aeb7c5c83a5a270f795b501777e357646a66364'}
p=argparse.ArgumentParser();p.add_argument('--work',default='.build/scalar-s0-native');p.add_argument('--msvc',action='store_true');p.add_argument('--sanitize',action='store_true');a=p.parse_args()
w=Path(a.work).resolve();w.mkdir(parents=True,exist_ok=True);base=w/'baseline';base.mkdir(exist_ok=True)
def run(cmd):
 result=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=1200)
 if result.returncode:print(result.stdout.decode(errors='replace')[-8000:],result.stderr.decode(errors='replace')[-8000:])
 result.check_returncode();return result
for name,want in EXPECTED.items():
 if hashlib.sha256((ROOT/'src'/name).read_bytes()).hexdigest()!=want:raise RuntimeError('reviewed runtime bytes changed: '+name)
 (base/name).write_bytes(run(['git','show',BASE+':src/'+name]).stdout)
def build(name,driver,label,layout=None):
 output=w/(name+('.exe' if os.name=='nt' else ''))
 src=base if label=='baseline' else ROOT/'src'
 inputs=[str(ROOT/'tests/scalar_s0'/driver),str(src/'Ast.cpp'),str(ROOT/'src/RuntimeValue.cpp')]
 inc=[str(src),str(ROOT/'src'),str(ROOT/'include')]
 if a.msvc:
  cmd=['cl','/nologo','/std:c++17','/EHsc','/O2','/DS0']+[('/I'+x) for x in inc]+inputs+['/Fe:'+str(output),'/Fo:'+str(w)+os.sep]
  if label=='baseline':cmd.remove('/DS0')
 else:
  cmd=[os.environ.get('CXX','c++'),'-std=c++17','-O2','-pthread']+[('-I'+x) for x in inc]+(['-DS0'] if label=='candidate' else [])
  if a.sanitize:cmd+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
  cmd+=inputs+['-o',str(output)]
 if layout is not None:
  flag="/D" if a.msvc else "-D"
  cmd += [flag+key+"="+str(value) for key,value in zip(["S0_BASE_SIZE","S0_BASE_SPAN","S0_BASE_OP"],layout)]
 run(cmd);return output
outputs=[]
for label in ['baseline','candidate']:
 exe=build('differential-'+label,'differential.cpp',label);out=run([str(exe)]).stdout;(w/(label+'.txt')).write_bytes(out);outputs.append(out)
if outputs[0]!=outputs[1]:raise RuntimeError('37700-case semantic differential differs')
if len(outputs[0].splitlines())!=37701:raise RuntimeError('unexpected matrix coverage')
layout=[int(v) for v in outputs[0].splitlines()[0].split()[1:]]
proof=build('contracts','contracts.cpp','candidate',layout);out=run([str(proof)]).stdout;print(out.decode(),end='')
summary={'PASS':True,'base':BASE,'candidate_commit':run(['git','rev-parse','HEAD']).stdout.decode().strip(),'cases':37700,'parity':'byte-for-byte on same native compiler','layout':outputs[0].splitlines()[0].decode(),'matrix_sha256':hashlib.sha256(outputs[0]).hexdigest(),'runtime_sha256':EXPECTED,'compiler':os.environ.get('CXX','cl' if a.msvc else 'c++'),'sanitized':a.sanitize,'contracts':out.decode()}
(w/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
