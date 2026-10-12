#!/usr/bin/env python3
"""F1E7 exactly-once: one location-index execution."""
from pathlib import Path
import subprocess,tempfile,os,re
B=Path(os.environ.get('NIFT_BIN','./nift')).resolve()
with tempfile.TemporaryDirectory(prefix='nift-operand-smoke-') as t:
 cases=[('location_replay','a := [[1]]\nfn(index()) { print("INDEX"); return 0 }\nfn(mutate(x)) { x.push(2); return x }\nwhile(true) { line := read(); if(line == null) { break }; x := mutate(a[index()]); print(a.stringify()); print(same(x,a[0])) }\n','INDEX\n[[1,2]]\ntrue\n'),('return_and_root','a := [[1]]\nfn(id(x)) { return x }\nb := id(a[0]); a = [[9]]; b.push(2); print(a.stringify()); print(same(b,a[0]))\n','[[9,2]]\ntrue\n')]
 for name,source,expected in cases:
  p=Path(t)/(name+'.f');p.write_text(source);v=subprocess.run([str(B),str(p)],input='one\n',capture_output=True,text=True,timeout=30);assert (v.returncode,v.stdout,v.stderr)==(0,expected,''),(name,v.stdout,v.stderr)
 p=Path(t)/'diagnostic.f';p.write_text('fn(probe()) { print("EFFECT"); return 1/0 }\nwhile(true) { line := read(); if(line == null) { break }; print(probe().stringify()) }\n');v=subprocess.run([str(B),str(p)],input='one\n',capture_output=True,text=True,timeout=30);assert v.returncode==1 and v.stdout=='EFFECT\n';assert v.stderr=='error: '+str(p)+':1:39: division by zero\n',v.stderr
print('PASS operand location/alias/root-slot behavior and exact column-39 diagnostic')
