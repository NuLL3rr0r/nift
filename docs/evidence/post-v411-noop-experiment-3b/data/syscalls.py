from pathlib import Path
import subprocess,os
p=Path('/tmp/nift-sidecar-experiment');d=Path('/tmp/nift-noop-investigation/fixture-10000-nift');store=p/'states/10000';current='e2';os.sched_setaffinity(0,{0,1,2,3})
def swap(target):
 global current
 if current!=target:(d/'.nift').rename(store/current);(store/target).rename(d/'.nift');current=target
try:
 for label in ['e2','e3b']:
  swap(label);r=subprocess.run(['strace','-f','-c','-o',str(p/f'strace-{label}.txt'),str(p/f'nift-{label}'),'build'],cwd=d,capture_output=True,text=True);(p/f'strace-{label}.stdout').write_text(r.stdout+r.stderr);assert r.returncode==0 and 'up to date' in r.stdout,(label,r.stdout,r.stderr)
finally:swap('e2')
