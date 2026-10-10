#!/usr/bin/env python3
"""Build diagnostic-only standalone/native failure controls after ordinary make."""
from pathlib import Path
import subprocess, shlex, os
root=Path(__file__).resolve().parent.parent;out=root/'.build/identity';out.mkdir(parents=True,exist_ok=True);suffix='.exe' if os.name=='nt' else ''
flags=['-std=c++17','-O2','-Wall','-Wextra','-pedantic','-pthread','-Isrc']
static=['-static','-static-libgcc','-static-libstdc++'] if os.name=='nt' else []
for source,filename,extra in [('tests/identity_catalogue_probe.cpp','probe',['src/FileSystem.cpp','-DNIFT_TEST_IDENTITY_PUBLICATION']),('tests/identity_spelling_differential.cpp','spelling',[])]:
 unicode=['-municode'] if os.name=='nt' and filename=='probe' else []
 subprocess.run(['g++',*flags,source,*extra,*static,*unicode,'-o',str(out/(filename+suffix))],cwd=root,check=True)
# The native runner may export a different prefixed MinGW CXX. The ordinary
# Windows build and these standalone controls use UCRT64 g++ from PATH.
make_compiler=['CXX=g++'] if os.name=='nt' else []
lines=subprocess.check_output(['make',*make_compiler,'-n','-W','src/ProjectInfo.cpp','nift'+suffix],cwd=root,text=True).splitlines()
compile=shlex.split(next(x for x in lines if '-c src/ProjectInfo.cpp ' in x));link=shlex.split(next(x for x in reversed(lines) if x.endswith(' -o nift'+suffix)))
compile=[str(out/'ProjectInfo-fault.o') if x=='src/ProjectInfo.o' else x for x in compile];compile.insert(1,'-DNIFT_TEST_IDENTITY_PUBLICATION');subprocess.run(compile,cwd=root,check=True)
link=[str(out/'ProjectInfo-fault.o') if x=='src/ProjectInfo.o' else str(out/('nift-fault'+suffix)) if x=='nift'+suffix else x for x in link];subprocess.run(link,cwd=root,check=True)
print(out)
