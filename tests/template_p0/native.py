"""Exact baseline/candidate P0 differential and copied-source counter proof.
Production sources are never instrumented; diagnostic copies are built separately.
"""
from pathlib import Path
import argparse, hashlib, io, json, os, shutil, subprocess, tarfile, zipfile
ROOT=Path(__file__).resolve().parents[2]
BASE='445f4d3545cf031bcce4bf77a2b4a61ffb3b4c4f'
p=argparse.ArgumentParser();p.add_argument('--work',default='.build/template-p0-native');p.add_argument('--reuse-baseline');p.add_argument('--reuse-candidate');args=p.parse_args()
work=Path(args.work).resolve();work.mkdir(parents=True,exist_ok=True)
fixtures=work/'fixtures'
with zipfile.ZipFile(ROOT/'tests/template_p0/fixtures.zip') as z:z.extractall(fixtures)
compiler=os.environ.get('CXX','c++');suffix='.exe' if os.name=='nt' else ''
def run(cmd,cwd=ROOT,timeout=1800):
 result=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout)
 if result.returncode:
  print(result.stdout[-6000:],result.stderr[-6000:],flush=True)
 result.check_returncode()
 return result
header='''#include <atomic>
#include <iostream>
namespace p0proof { static std::atomic<unsigned long long> parse{0},prepare{0},execute{0},lookup{0}; struct Dump { ~Dump(){std::cerr<<"P0COUNTERS "<<parse<<" "<<prepare<<" "<<execute<<" "<<lookup<<"\\n";} }; static Dump dump; }
'''
binaries={};identities={}
for label in ['baseline','candidate']:
 source=work/label;source.mkdir(exist_ok=True)
 if label=='baseline':
  archive=subprocess.run(['git','archive',BASE],cwd=ROOT,check=True,capture_output=True)
  with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as t:t.extractall(source,filter='data')
 else:
  paths=run(['git','ls-files','-z']).stdout.split('\0')
  for name in paths:
   f=ROOT/name
   if name and f.is_file():
    dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
 file=source/'src/ParserTemplate.cpp';text=file.read_text()
 identities[label]=hashlib.sha256(file.read_bytes()).hexdigest()
 expected={'baseline':'0b9226dfd270bc6f8eb857d0102b56fde2d4ca2c16a4f7131185300f10a2db29','candidate':'817d19a864deb1feaa47ff540dc7b5dbf82153315968646a7e8958ba1128501c'}
 assert identities[label]==expected[label],(label,'runtime identity changed')
 anchor='SourceProvenance source_provenance, nift::detail::SourceView view) {'
 assert text.count(anchor)==1
 text=header+text.replace(anchor,anchor+'++p0proof::parse;')
 if label=='candidate':
  changes=[('    return plan;','    ++p0proof::prepare;return plan;'),('    const fs::path& source_path, int depth, SourceProvenance source_provenance) {','    const fs::path& source_path, int depth, SourceProvenance source_provenance) {++p0proof::execute;'),('        nift::RuntimeValue expression_value;','        ++p0proof::lookup;nift::RuntimeValue expression_value;')]
  for a,b in changes:
   # expression_value also occurs in canonical parser; instrument only emission helper.
   if a.startswith('        nift::'):
    split=text.index('RenderResult Parser::parse(');pre=text[:split];assert pre.count(a)==1;text=pre.replace(a,b)+text[split:]
   else:assert text.count(a)==1;text=text.replace(a,b)
 file.write_text(text)
 reuse=args.reuse_baseline if label=='baseline' else args.reuse_candidate
 if reuse:
  shutil.copy2(Path(reuse).resolve(),source/'libnift_c.a')
  run([compiler,'-std=c++17','-O2','-pthread','-I'+str(source/'src'),'-I'+str(source/'include'),'-I'+str(source/'minifypp/include'),'-I'+str(source/'markuppp/include'),'-c',str(file),'-o',str(source/'ParserTemplate.o')])
  run(['ar','r',str(source/'libnift_c.a'),str(source/'ParserTemplate.o')])
 else:run(['make','-j2','libnift_c.a'],source)
 binary=work/(label+'-probe'+suffix)
 cmd=[compiler,'-std=c++17','-O2','-pthread','-I'+str(source/'include'),str(ROOT/'tests/template_p0/probe.cpp'),str(source/'libnift_c.a'),'-o',str(binary)]
 if os.name!='nt' and os.uname().sysname!='Darwin':cmd+=['-ldl']
 run(cmd);binaries[label]=binary
rows=[]
for fixture in sorted(fixtures.iterdir()):
 row={'fixture':fixture.name};counts={}
 for label in binaries:
  command=[str(binaries[label]),str(fixture)]
  if fixture.name in ['simple','nested','metadata','constant']:command+=['concurrent']
  result=run(command,timeout=30)
  row[label]=[json.loads(x) for x in result.stdout.split('\n@@@\n') if x.strip()]
  lines=[x for x in result.stderr.splitlines() if x.startswith('P0COUNTERS ')]
  assert len(lines)==1,(label,fixture.name,result.stderr)
  counts[label]=list(map(int,lines[0].split()[1:]))
 assert row['baseline']==row['candidate'],fixture.name
 row['counters']=counts;rows.append(row)
(work/'differential.json').write_text(json.dumps(rows,indent=2)+'\n')
assert len(rows)==274 and sum(len(x['candidate']) for x in rows)==1128
simple=next(x for x in rows if x['fixture']=='simple')['counters']
assert simple['candidate']==[12,12,108,216],simple
assert simple['baseline'][0]==120,simple
for row in rows:
 if row['fixture'].startswith('fallback-') and row['fixture']!='fallback-nested':
  assert row['counters']['candidate'][1:]==[0,0,0],row['fixture']
volume=work/'exact-10000';volume.mkdir(exist_ok=True)
with zipfile.ZipFile(ROOT/'tests/template_p0/exact-10000.zip') as z:z.extractall(volume)
exact={}
for label,binary in binaries.items():
 result=run([str(binary),str(volume)],timeout=60)
 exact[label]=[json.loads(x) for x in result.stdout.split('\n@@@\n') if x.strip()]
 lines=[x for x in result.stderr.splitlines() if x.startswith('P0COUNTERS ')]
 assert len(lines)==1
 exact[label+'_counters']=list(map(int,lines[0].split()[1:]))
assert exact['baseline']==exact['candidate']
assert exact['baseline_counters'][0]==40004,exact['baseline_counters']
assert exact['candidate_counters']==[4,4,40000,80000],exact['candidate_counters']
(work/'exact-10000.json').write_text(json.dumps(exact,indent=2)+'\n')
summary={'baseline':BASE,'source_sha256':identities,'fixtures':274,'results':1128,'simple_counters':simple,'exact_10000_counters':{k:v for k,v in exact.items() if k.endswith('_counters')},'eligibility':{x['fixture']:x['counters']['candidate'][1] for x in rows}}
(work/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('PASS P0: 274 fixtures, 1128 results; preparation, live lookup, whole-body fallback and parser reduction')
