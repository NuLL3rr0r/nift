from pathlib import Path
import shutil,subprocess,os,json,hashlib,time,resource,statistics
p=Path('/tmp/nift-sidecar-experiment');os.sched_setaffinity(0,{0,1,2,3});rows=[];sizes=[100,1000,5000,10000]
def run(d,label,args):
 return subprocess.run([str(p/f'nift-{label}'),*args],cwd=d,capture_output=True,text=True)
def swap(d,size,current,target):
 if current==target:return
 store=p/'states'/str(size);(d/'.nift').rename(store/current);(store/target).rename(d/'.nift')
for size in sizes:
 d=Path(f'/tmp/nift-noop-investigation/fixture-{size}-nift');store=p/'states'/str(size);store.mkdir(parents=True,exist_ok=True)
 assert not (store/'e2').exists() and not (store/'e3b').exists()
 m=json.loads((d/'manifest.json').read_text());before={a['id']:hashlib.sha256((d/a['output']).read_bytes()).hexdigest() for a in m['actions']}
 stamps={f:(f.stat().st_atime_ns,f.stat().st_mtime_ns) for f in (d/'build').rglob('*') if f.is_file()}
 shutil.copytree(d/'.nift',store/'e3b');swap(d,size,'e2','e3b');current='e3b'
 try:
  print('preparing',size,flush=True);r=run(d,'e3b',['build','--all']);(p/f'prepare-{size}.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,(size,r.stdout,r.stderr)
  for f,stamp in stamps.items():os.utime(f,ns=stamp)
  files=list((d/'.nift').rglob('*.info.json'));assert len(files)==len(m['actions']);assert all('sidecar-state' in json.loads(f.read_text()) for f in files)
  assert before=={a['id']:hashlib.sha256((d/a['output']).read_bytes()).hexdigest() for a in m['actions']}
  for i in range(22):
   for label in (['e2','e3b'] if i%2==0 else ['e3b','e2']):
    swap(d,size,current,label);current=label;trace=d/'experiment2.trace';trace.unlink(missing_ok=True)
    old=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter_ns();r=subprocess.run([str(p/f'nift-{label}'),'build'],cwd=d,env=os.environ|{'BUILD_TRACE':str(trace)},capture_output=True,text=True);wall=(time.perf_counter_ns()-start)/1e6;new=resource.getrusage(resource.RUSAGE_CHILDREN)
    assert r.returncode==0 and not trace.exists(),(size,label,r.stdout,r.stderr)
    rows.append(dict(size=size,binary=label,round=i,warmup=i<2,wall_ms=wall,cpu_ms=1000*(new.ru_utime+new.ru_stime-old.ru_utime-old.ru_stime)))
   (p/'native.json').write_text(json.dumps(rows,indent=2)+'\n')
  assert before=={a['id']:hashlib.sha256((d/a['output']).read_bytes()).hexdigest() for a in m['actions']};assert subprocess.check_output([str(d/'build/bin/app.exe')],text=True)==m['expected_stdout']
  print(size,[(label,statistics.median(x['wall_ms'] for x in rows if x['size']==size and x['binary']==label and not x['warmup'])) for label in ['e2','e3b']],flush=True)
 finally:swap(d,size,current,'e2')
