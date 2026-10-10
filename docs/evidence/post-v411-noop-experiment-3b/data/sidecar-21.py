import pathlib,json,subprocess,os,tempfile,sys,hashlib
sys.path.insert(0,'/home/nick/Repositories/nift/nift/tests')
from shared_dependency_targeted_reproducer import setup
binary='/tmp/nift-sidecar-experiment/nift-e3b';rows=[]
def run(p,*a):
 r=subprocess.run([binary,*a],cwd=p,capture_output=True,text=True);return dict(rc=r.returncode,stdout=r.stdout,stderr=r.stderr)
with tempfile.TemporaryDirectory(prefix='nift-sidecar-study-') as td:
 for mode in ['modified','hash','hybrid']:
  for case in ['malformed-old','missing-declaration-old','new-edge-old','equal-sidecar','deleted-sidecar','new-sidecar','unreadable-sidecar-old']:
   p=pathlib.Path(td)/(mode+'-'+case);p.mkdir();setup(p,mode,'explicit')
   side=p/'content/a.deps.json';side.write_text(json.dumps({'dependencies':['data/shared.html']}))
   if case=='new-sidecar':side.unlink()
   assert run(p,'build','--all')['rc']==0
   info=p/'.nift/public/a.info.json';stamp=info.stat().st_mtime_ns;old=stamp-2_000_000_000
   if case=='malformed-old':side.write_text('{bad')
   elif case=='missing-declaration-old':side.write_text(json.dumps({'dependencies':['data/not-here']}))
   elif case=='new-edge-old':
    extra=p/'data/new.txt';extra.write_text('old');os.utime(extra,ns=(old,old));side.write_text(json.dumps({'dependencies':['data/shared.html','data/new.txt']}))
   elif case=='equal-sidecar':pass
   elif case=='deleted-sidecar':side.unlink()
   elif case=='new-sidecar':side.write_text('{bad')
   elif case=='unreadable-sidecar-old':side.chmod(0)
   if side.exists():os.utime(side,ns=((stamp if case=='equal-sidecar' else old),)*2)
   first=run(p,'status');build=run(p,'build')
   row=dict(mode=mode,case=case,sidecar_older=case!='equal-sidecar',status=first,build=build)
   if case=='new-edge-old':
    extra.write_text('changed');os.utime(extra,ns=(stamp+5_000_000_000,)*2)
    row['after_named_dependency_change']=run(p,'status');row['second_build']=run(p,'build')
    assert 'data/new.txt' in row['after_named_dependency_change']['stdout'],row
   if case in ['malformed-old','missing-declaration-old','new-sidecar','unreadable-sidecar-old']:assert build['rc']!=0,row
   if case=='equal-sidecar' and mode!='hash':assert 'dependency changed: content/a.deps.json' in first['stdout'],row
   if case=='deleted-sidecar':assert 'dependency removed: content/a.deps.json' in first['stdout'],row
   if side.exists():side.chmod(0o644)
   rows.append(row)
 # Authored provenance ambiguity: two declarations, same saved dependency union.
 ambiguity=[]
 for label,decl in [('x','data/x'),('y','data/y')]:
  p=pathlib.Path(td)/label;p.mkdir();setup(p,'modified','explicit')
  (p/'data/x').write_text('X');(p/'data/y').write_text('Y')
  (p/'content/a.html').write_text('@dep("data/x")\n@dep("data/y")\nCONTENT')
  (p/'content/a.deps.json').write_text(json.dumps({'dependencies':[decl]}))
  assert run(p,'build','--all')['rc']==0
  ambiguity.append(dict(authored_declaration=decl,metadata=json.loads((p/'.nift/public/a.info.json').read_text())))
 assert ambiguity[0]['metadata']['sidecar-state']!=ambiguity[1]['metadata']['sidecar-state'],ambiguity
 assert {k:v for k,v in ambiguity[0]['metadata'].items() if k!='sidecar-state'}=={k:v for k,v in ambiguity[1]['metadata'].items() if k!='sidecar-state'},ambiguity
result=dict(binary_sha256=hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest(),cases=rows,provenance_ambiguity=ambiguity,passed=True)
pathlib.Path('/tmp/nift-sidecar-experiment/sidecar-21.json').write_text(json.dumps(result,indent=2)+'\n')
print('E2 sidecar study PASS',len(rows),'cases; exact metadata provenance ambiguity confirmed')
