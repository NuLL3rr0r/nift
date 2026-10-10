from pathlib import Path
import shutil,subprocess,hashlib,json,statistics,csv,gzip
p=Path('/tmp/nift-sidecar-experiment');r=Path('/home/nick/Repositories/nift/nift');out=r/'docs/evidence/post-v411-noop-experiment-3b';data=out/'data';data.mkdir(parents=True,exist_ok=True)
for f in p.iterdir():
 if f.is_file() and f.name.endswith('.csv.paths'):
  (data/(f.name+'.gz')).write_bytes(gzip.compress(f.read_bytes(),mtime=0));(data/f.name).unlink(missing_ok=True)
 elif f.is_file() and (f.suffix in ['.py','.sh','.c','.json','.csv','.txt']):shutil.copy2(f,data/f.name)
for name in ['ProjectInfo.cpp','ProjectInfo.h']:
 shutil.copy2(p/name,data/name);result=subprocess.run(['diff','-u','--label','a/src/'+name,str(r/'src'/name),'--label','b/src/'+name,str(p/name)],capture_output=True,text=True);assert result.returncode in [0,1]
 with (data/'candidate.patch').open('a' if name.endswith('.h') else 'w') as f:f.write(result.stdout)
shutil.copy2(r/'tests/sidecar_state_contracts.py',data/'sidecar_state_contracts.py')
identity=dict(production_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),e2_runtime='64d68993a981fdb6aaf6a52e37c666b035073b3e',binaries={label:hashlib.sha256((p/f'nift-{label}').read_bytes()).hexdigest() for label in ['e2','e3b']},candidate_files=['src/ProjectInfo.cpp','src/ProjectInfo.h'],production_tracked_diff=subprocess.check_output(['git','diff','--stat'],cwd=r,text=True),compiled_from=p.as_posix(),implementation_authorization='NONE FURTHER',native_macos_windows='NOT RUN: local-only uncommitted candidate; hosted workflow checks out a remote ref and no remote publication is authorized')
(data/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
def metric(xs,name):
 vals=sorted(x[name] for x in xs);return dict(median=statistics.median(vals),minimum=min(vals),maximum=max(vals),p25=statistics.quantiles(vals,n=4)[0] if len(vals)>1 else vals[0],p75=statistics.quantiles(vals,n=4)[2] if len(vals)>1 else vals[0],samples=len(vals))
summary={}
for family,key in [('native','size'),('workers','threads'),('websites','size')]:
 rows=json.loads((p/f'{family}.json').read_text());groups={}
 for row in rows:
  if row['warmup']:continue
  group=str(row[key])+('/'+row['case'] if family=='websites' else '');groups.setdefault(group,{}).setdefault(row['binary'],[]).append(row)
 summary[family]={group:{label:{'wall_ms':metric(xs,'wall_ms'),'child_cpu_ms':metric(xs,'cpu_ms')} for label,xs in labels.items()} for group,labels in groups.items()}
 for group,labels in summary[family].items():labels['improvement_percent']=100*(1-labels['e3b']['wall_ms']['median']/labels['e2']['wall_ms']['median'])
summary['rss']={str(t):{label:statistics.median(int((p/f'rss-{t}-{label}-{k}.txt').read_text()) for k in range(3)) for label in ['e2','e3b']} for t in [1,2,4,8]}
(data/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=[]
for f in sorted(data.iterdir()):
 if f.is_file() and f.name!='SHA256SUMS':lines.append(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name)
(data/'SHA256SUMS').write_text('\n'.join(lines)+'\n');print(out)
