#!/usr/bin/env python3
"""Native ACL denial with exact saved-DACL restoration on a preopened handle."""
import contextlib, ctypes, os, pathlib, subprocess, tempfile
from ctypes import wintypes

def api():
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);security=ctypes.WinDLL('advapi32',use_last_error=True)
 kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];kernel.CreateFileW.restype=wintypes.HANDLE
 kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
 kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
 pointer=ctypes.POINTER(ctypes.c_void_p)
 security.GetSecurityInfo.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.DWORD,pointer,pointer,pointer,pointer,pointer];security.GetSecurityInfo.restype=wintypes.DWORD
 security.SetSecurityInfo.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.DWORD,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];security.SetSecurityInfo.restype=wintypes.DWORD
 security.GetSecurityDescriptorControl.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.WORD),ctypes.POINTER(wintypes.DWORD)];security.GetSecurityDescriptorControl.restype=wintypes.BOOL
 return kernel,security

@contextlib.contextmanager
def denied_acl(directory, inheritance):
 kernel,security=api();invalid=ctypes.c_void_p(-1).value
 # Keep WRITE_DAC and READ_CONTROL capability before changing access. Restoring
 # by pathname after denial can itself be denied by the fixture.
 handle=kernel.CreateFileW(str(directory),0x20000|0x40000,7,None,3,0x02000000,None)
 assert handle!=invalid,ctypes.get_last_error()
 descriptor=ctypes.c_void_p();dacl=ctypes.c_void_p();saved=False
 try:
  error=security.GetSecurityInfo(handle,1,4,None,None,ctypes.byref(dacl),None,ctypes.byref(descriptor));assert error==0,error
  control=wintypes.WORD();revision=wintypes.DWORD()
  assert security.GetSecurityDescriptorControl(descriptor,ctypes.byref(control),ctypes.byref(revision))
  saved=True
  denied=subprocess.run(['icacls',str(directory),'/deny',os.environ['USERNAME']+':'+inheritance+'(RD,REA,RA,X)','/L'],capture_output=True,text=True)
  assert denied.returncode==0,denied.stdout+denied.stderr
  yield
 finally:
  try:
   if saved:
    protection=0x80000000 if control.value&0x1000 else 0x20000000
    error=security.SetSecurityInfo(handle,1,4|protection,None,None,dacl,None);assert error==0,error
  finally:
   if descriptor.value:kernel.LocalFree(descriptor)
   kernel.CloseHandle(handle)

@contextlib.contextmanager
def denied_read(directory):
 # An inherited deny may follow an explicit child grant in the access check.
 # Deny the actual observed leaf explicitly, then deny directory enumeration.
 # Restore the parent before the leaf, using both preopened original DACLs.
 with denied_acl(directory/'plain.txt',''):
  with denied_acl(directory,'(OI)(CI)'):
   yield

def assert_denied(directory):
 try:
  with os.scandir(directory) as entries:list(entries)
  raise AssertionError('directory enumeration was not denied')
 except PermissionError:pass
 kernel,_=api();handle=kernel.CreateFileW(str(directory/'plain.txt'),0x80,7,None,3,0x02000000,None)
 if handle!=ctypes.c_void_p(-1).value:
  kernel.CloseHandle(handle);raise AssertionError('Nift following FILE_READ_ATTRIBUTES observation was not denied')
 assert ctypes.get_last_error()==5,ctypes.get_last_error()

if __name__=='__main__':
 assert os.name=='nt','Windows-only fixture preflight'
 with tempfile.TemporaryDirectory(prefix='nift-identity-acl-preflight-') as temporary:
  directory=pathlib.Path(temporary)/'parent';directory.mkdir();leaf=directory/'plain.txt';leaf.write_text('plain')
  with denied_read(directory):assert_denied(directory)
  assert leaf.read_text()=='plain'
  with os.scandir(directory) as entries:assert len(list(entries))==1
 print('Windows native following denial and saved-DACL restoration PASS')
