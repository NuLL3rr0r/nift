#!/usr/bin/env python3
"""Native ACL fixture: deny once at the parent, restore even if setup fails."""
import contextlib, os, pathlib, subprocess, tempfile
@contextlib.contextmanager
def denied_read(directory):
 user=os.environ['USERNAME']
 try:
  denied=subprocess.run(['icacls',str(directory),'/deny',user+':(OI)(CI)(RX)','/L'],capture_output=True,text=True)
  assert denied.returncode==0,denied.stdout+denied.stderr
  yield
 finally:
  restored=subprocess.run(['icacls',str(directory),'/remove:d',user,'/L'],capture_output=True,text=True)
  assert restored.returncode==0,restored.stdout+restored.stderr
if __name__=='__main__':
 assert os.name=='nt','Windows-only fixture preflight'
 with tempfile.TemporaryDirectory(prefix='nift-identity-acl-preflight-') as temporary:
  directory=pathlib.Path(temporary)/'parent';directory.mkdir();leaf=directory/'plain.txt';leaf.write_text('plain')
  with denied_read(directory):
   try:os.lstat(leaf);raise AssertionError('inheritable deny did not block observation')
   except PermissionError:pass
  assert leaf.read_text()=='plain'
 print('Windows inheritable ACL denial/restoration PASS')
