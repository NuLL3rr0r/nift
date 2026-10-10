from pathlib import Path
import subprocess,os,json
p=Path('/tmp/nift-sidecar-experiment');d=Path('/tmp/nift-noop-investigation/fixture-10000-nift');store=p/'states/10000';current='e2';rows={};os.sched_setaffinity(0,{0,1,2,3})
def swap(target):
 global current
 if current!=target:(d/'.nift').rename(store/current);(store/target).rename(d/'.nift');current=target
try:
 for label in ['e2','e3b']:
  swap(label);files=list((d/'.nift').rglob('*.info.json'));rows[label]=dict(info_files=len(files),info_bytes=sum(f.stat().st_size for f in files))
  binary='/tmp/nift-silverback-2/nift-counters' if label=='e2' else str(p/'counters/nift-counters')
  r=subprocess.run([binary,'build'],cwd=d,env=os.environ|{'NIFT_DIAG_FILE':str(p/f'counts-{label}.csv')},capture_output=True,text=True);(p/f'counts-{label}.stdout').write_text(r.stdout+r.stderr);assert r.returncode==0 and 'up to date' in r.stdout
  r=subprocess.run([str(p/f'nift-{label}'),'build'],cwd=d,env=os.environ|{'LD_PRELOAD':str(p/'alloc.so'),'NIFT_ALLOC_FILE':str(p/f'alloc-{label}.json')},capture_output=True,text=True);assert r.returncode==0 and 'up to date' in r.stdout
 (p/'metadata.json').write_text(json.dumps(rows,indent=2)+'\n')
finally:swap('e2')
