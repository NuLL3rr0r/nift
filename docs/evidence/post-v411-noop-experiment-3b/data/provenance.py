import pathlib,json,subprocess,tempfile,sys
sys.path.insert(0,'/home/nick/Repositories/nift/nift/tests')
from shared_dependency_targeted_reproducer import setup
from consumer_dependency_snapshots import python_tool,hash_bytes
binary='/tmp/nift-sidecar-experiment/nift-e3b';rows=[]
with tempfile.TemporaryDirectory(prefix='nift-sidecar-provenance-') as td:
 for mode in ['hash','hybrid']:
  p=pathlib.Path(td)/mode;p.mkdir();setup(p,mode,'explicit')
  for name in ['one.txt','two.txt']:(p/'data'/name).write_text(name)
  initial=json.dumps({'dependencies':['data/one.txt']});intermediate=json.dumps({'dependencies':['data/two.txt']})
  side=p/'content/a.deps.json';side.write_text(initial)
  for phase,text in [('pre',intermediate),('post',initial)]:
   (p/(phase+'.py')).write_text('from pathlib import Path\nPath("content/a.deps.json").write_text('+repr(text)+')\n')
   (p/(phase+'.f')).write_text('r := run('+json.dumps(python_tool())+', '+json.dumps(phase+'.py')+')\n')
  tracking=json.loads((p/'.nift/tracked.json').read_text());tracking['tracked'][0].update({'pre build':'pre.f','post build':'post.f'});(p/'.nift/tracked.json').write_text(json.dumps(tracking))
  r=subprocess.run([binary,'build','a'],cwd=p,capture_output=True,text=True)
  metadata=json.loads((p/'.nift/public/a.info.json').read_text()) if (p/'.nift/public/a.info.json').exists() else None
  row=dict(mode=mode,rc=r.returncode,stdout=r.stdout,stderr=r.stderr,initial_bytes=initial,second_parse_bytes=intermediate,final_bytes=side.read_text(),initial_hash=str(hash_bytes(initial.encode())),second_parse_hash=str(hash_bytes(intermediate.encode())),metadata=metadata)
  assert r.returncode==0,row
  assert metadata['dependency-hashes']['content/a.deps.json']==row['initial_hash'],row
  assert 'data/two.txt' in metadata['dependencies'] and 'data/one.txt' not in metadata['dependencies'],row
  assert 'sidecar-state' not in metadata,row
  rows.append(row)
pathlib.Path('/tmp/nift-sidecar-experiment/provenance.json').write_text(json.dumps(dict(passed=True,cases=rows),indent=2)+'\n')
print('E2 hash/declaration provenance separation demonstrated',len(rows))
