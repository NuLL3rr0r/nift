#!/usr/bin/env python3
"""Permanent immutable-syntax separation and high-volume lifetime contracts."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--nift', default='./nift')
parser.add_argument('--volume', type=int, default=100000)
args = parser.parse_args()
binary = str(Path(args.nift).resolve())
contracts = json.loads(Path(__file__).with_name('lambda_metadata_cases.json').read_text())
with tempfile.TemporaryDirectory(prefix='nift-lambda-metadata-') as directory:
    root = Path(directory)
    for name, source in contracts['fixtures'].items():
        (root / name).write_text(source, encoding='utf-8')
    cases = dict(contracts['expected'])
    count = args.volume
    if count < 100000:
        raise SystemExit('Certification requires at least 100000 factories')
    source = ('a:=[]; i:=0; while(i<' + str(count) + ') { a.push(' + str(count) + '-i); i+=1 }; '
              'a=a.sort_by(x=>x); i=0; while(i<' + str(count) + ') { '
              'if(a[i]!=i+1) { throw error("order") }; i+=1 }; '
              'print(a[0]); print(a[' + str(count-1) + '])\n')
    (root / 'volume.f').write_text(source, encoding='utf-8')
    cases['volume'] = f'1\n{count}\n'
    for name, expected in cases.items():
        result = subprocess.run([binary, str(root / (name + '.f'))], cwd=root,
                                capture_output=True, text=True, encoding='utf-8', timeout=600)
        actual = (result.returncode, result.stdout, result.stderr)
        if actual != (0, expected, ''):
            raise SystemExit(f'FAIL {name}: {actual!r}')
        print(f'PASS {name}', flush=True)
print(f'PASS {len(cases)} metadata contracts, {count} fresh factories/destruction and full vector order')
