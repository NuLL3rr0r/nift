from pathlib import Path
import subprocess,shutil,os
r=Path('/home/nick/Repositories/nift/nift');p=Path('/tmp/nift-sidecar-experiment');c=p/'core';c.mkdir(exist_ok=True)
for name in subprocess.check_output(['git','ls-files'],cwd=r,text=True).splitlines():
 f=r/name;t=c/name
 if f.is_file():t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,t)
for name in ['src','minifypp','markuppp','.build','dist/embed-prefix']:
 shutil.copytree(r/name,c/name,dirs_exist_ok=True)
if not (c/'jsonic').exists():(c/'jsonic').symlink_to(r/'jsonic')
for name in ['ProjectInfo.cpp','ProjectInfo.h','ProjectInfo.o']:shutil.copy2(p/name,c/'src'/name)
shutil.copy2(p/'nift-e3b',c/'nift')
print(c)
