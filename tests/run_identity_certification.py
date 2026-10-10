#!/usr/bin/env python3
"""Serialized native certification; never invokes release or publish workflows."""
import argparse,hashlib,json,os,pathlib,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--e3b',required=True);p.add_argument('--e2',required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parent.parent;out=root/'.build/identity';out.mkdir(parents=True,exist_ok=True)
suffix='.exe' if os.name=='nt' else '';binary=root/('nift'+suffix)
def call(name,command):
 with (out/(name+'.log')).open('w') as log:
  result=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode:print((out/(name+'.log')).read_text());raise SystemExit(result.returncode)
def test(name,script,*args):call(name,[sys.executable,'tests/'+script,'--nift',str(binary),*map(str,args)])
call('build-probes',[sys.executable,'tests/build_identity_probes.py'])
call('spelling',[str(out/('spelling'+suffix))])
test('publication','identity_publication_contracts.py','--baseline',a.e3b,'--probe',out/('probe'+suffix),'--fault-nift',out/('nift-fault'+suffix),'--output',out/'publication.json')
test('sidecar-state','sidecar_state_contracts.py','--baseline',a.e2,'--output',out/'sidecar-state.json')
test('sidecar-platform','sidecar_platform_contracts.py','--output',out/'sidecar-platform.json','--export',out/'sidecar-export.json')
test('snapshots','consumer_dependency_snapshots.py','--output',out/'snapshots.json')
test('targeted','shared_dependency_targeted_reproducer.py','--require-clean','--output',out/'targeted.json')
test('randomized','randomized_incremental_differential.py','--seeds','0,1,2','--steps','32','--output',out/'randomized.json')
test('transitions','incremental_state_transitions_adversarial.py')
test('pagination','pagination_incremental_equivalence.py')
receipt={'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'platform':sys.platform,'passed':True,'e3b_binary_sha256':hashlib.sha256(pathlib.Path(a.e3b).read_bytes()).hexdigest(),'e2_binary_sha256':hashlib.sha256(pathlib.Path(a.e2).read_bytes()).hexdigest()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
