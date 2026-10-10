import pathlib,json,subprocess,os,tempfile,sys,hashlib
sys.path.insert(0,'/home/nick/Repositories/nift/nift/tests')
from shared_dependency_targeted_reproducer import setup
binary='/tmp/nift-sidecar-experiment/nift-e3b';rows=[]
def run(p,*a):
 r=subprocess.run([binary,*a],cwd=p,capture_output=True,text=True);return dict(rc=r.returncode,stdout=r.stdout,stderr=r.stderr)
with tempfile.TemporaryDirectory(prefix='nift-sidecar-preserved-') as td:
 for mode in ['modified','hash','hybrid']:
  for case in ['add','remove','replace','malformed','invalid-parent','same-length']:
   p=pathlib.Path(td)/(mode+'-'+case);p.mkdir();setup(p,mode,'explicit')
   for f in ['one.txt','two.txt']:(p/'data'/f).write_text(f)
   side=p/'content/a.deps.json';initial=json.dumps({'dependencies':['data/one.txt']},separators=(',',':'));side.write_text(initial)
   stamp=1_600_000_000_123456789;os.utime(side,ns=(stamp,stamp))
   for f in (p/'data').iterdir():os.utime(f,ns=(stamp,stamp))
   assert run(p,'build','--all')['rc']==0
   before=json.loads((p/'.nift/public/a.info.json').read_text())
   decl={'add':['data/one.txt','data/two.txt'],'remove':[],'replace':['data/two.txt'],'invalid-parent':['../outside'],'same-length':['data/two.txt']}.get(case)
   current='{broken' if case=='malformed' else json.dumps({'dependencies':decl},separators=(',',':'))
   if case=='same-length':assert len(current)==len(initial)
   side.write_text(current);os.utime(side,ns=(stamp,stamp));assert side.stat().st_mtime_ns==stamp
   status=run(p,'status');build=run(p,'build');after=json.loads((p/'.nift/public/a.info.json').read_text())
   row=dict(mode=mode,case=case,initial_bytes=initial,current_bytes=current,exact_mtime_before_and_after=stamp,metadata_before=before,status=status,build=build,metadata_after=after)
   if case in ['malformed','invalid-parent']:assert build['rc']!=0,row
   elif mode=='modified':assert 'up to date' in status['stdout'],row
   else:assert 'content/a.deps.json' in status['stdout'],row
   if case in ['add','replace','same-length']:
    (p/'data/two.txt').unlink();row['new_declared_path_deleted_status']=run(p,'status');row['new_declared_path_deleted_build']=run(p,'build');assert row['new_declared_path_deleted_build']['rc']!=0,row
   if case=='remove':
    (p/'data/one.txt').write_text('later');future=(p/'.nift/public/a.info.json').stat().st_mtime_ns+2_000_000_000;os.utime(p/'data/one.txt',ns=(future,future));row['removed_path_changed_status']=run(p,'status');row['removed_path_changed_build']=run(p,'build');row['metadata_after_later_build']=json.loads((p/'.nift/public/a.info.json').read_text())
   rows.append(row)
pathlib.Path('/tmp/nift-sidecar-experiment/preserved.json').write_text(json.dumps(dict(passed=True,cases=rows),indent=2)+'\n')
print('Preserved exact-mtime E2 controls PASS',len(rows))
