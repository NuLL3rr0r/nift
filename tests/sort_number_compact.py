#!/usr/bin/env python3
"""Number-key compact sorting: exact frozen fallback, stability and callback oracles."""
import argparse,json,subprocess,tempfile
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--nift',default='./nift');ap.add_argument('--baseline');args=ap.parse_args()
binaries=[str(Path(args.nift).resolve())]
if args.baseline:binaries.append(str(Path(args.baseline).resolve()))
cases=json.loads(Path(__file__).with_name('data').joinpath('sort_number_compact.json').read_text())
with tempfile.TemporaryDirectory(prefix='nift-number-sort-') as directory:
 root=Path(directory)
 for case in cases:
  f=root/(case['name']+'.f');f.write_text(case['source']+'\n')
  for binary in binaries:
   q=subprocess.run([binary,str(f)],cwd=root,capture_output=True,text=True,timeout=90)
   actual=(q.returncode,q.stdout,q.stderr.replace(str(root),'$FIXTURE_ROOT'))
   expected=(case['exit'],case['stdout'],case['stderr'])
   assert actual==expected,(case['name'],binary,actual,expected)
print('PASS',len(cases),'compact Number sort/fallback/callback/ownership contracts')
