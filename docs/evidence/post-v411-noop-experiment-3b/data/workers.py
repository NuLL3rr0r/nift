from pathlib import Path
import subprocess,json,os,time,resource,statistics
p=Path('/tmp/nift-sidecar-experiment');d=Path('/tmp/nift-noop-investigation/fixture-10000-nift');store=p/'states/10000';os.sched_setaffinity(0,{0,1,2,3});current='e2';rows=[];original={}
def swap(target):
 global current
 if current!=target:(d/'.nift').rename(store/current);(store/target).rename(d/'.nift');current=target
try:
 for label in ['e2','e3b']:
  swap(label);original[label]=(d/'.nift/config.json').read_bytes()
 for threads in [1,2,4,8]:
  for label in ['e2','e3b']:
   swap(label);conf=json.loads(original[label]);conf['config']['build-threads']=threads;(d/'.nift/config.json').write_text(json.dumps(conf))
  for i in range(12):
   for label in (['e2','e3b'] if i%2==0 else ['e3b','e2']):
    swap(label);old=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter_ns();r=subprocess.run([str(p/f'nift-{label}'),'build'],cwd=d,capture_output=True,text=True);wall=(time.perf_counter_ns()-start)/1e6;new=resource.getrusage(resource.RUSAGE_CHILDREN);assert r.returncode==0 and 'up to date' in r.stdout,(label,r.stdout,r.stderr)
    rows.append(dict(threads=threads,binary=label,round=i,warmup=i<2,wall_ms=wall,cpu_ms=1000*(new.ru_utime+new.ru_stime-old.ru_utime-old.ru_stime)))
  for label in ['e2','e3b']:
   swap(label)
   for k in range(3):
    r=subprocess.run(['/usr/bin/time','-f','%M','-o',str(p/f'rss-{threads}-{label}-{k}.txt'),str(p/f'nift-{label}'),'build'],cwd=d,capture_output=True,text=True);assert r.returncode==0 and 'up to date' in r.stdout
  (p/'workers.json').write_text(json.dumps(rows,indent=2));print(threads,[(label,statistics.median(x['wall_ms'] for x in rows if x['threads']==threads and x['binary']==label and not x['warmup'])) for label in ['e2','e3b']],flush=True)
finally:
 for label,raw in original.items():swap(label);(d/'.nift/config.json').write_bytes(raw)
 swap('e2')
