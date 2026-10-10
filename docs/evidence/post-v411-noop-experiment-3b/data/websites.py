import pathlib,json,subprocess,shutil,os,time,resource,statistics,hashlib
p=pathlib.Path('/tmp/nift-sidecar-experiment');os.sched_setaffinity(0,{0,1,2,3});bins={'e2':str(p/'nift-e2'),'e3b':str(p/'nift-e3b')};rows=[]
for n in [100,1000,5000]:
 base=p/f'website-{n}';shutil.rmtree(base,ignore_errors=True)
 for name in ['.nift','content','public','templates','data','partials']:(base/name).mkdir(parents=True,exist_ok=True)
 cfg={'content-dir':'content/','content-ext':'.html','output-dir':'public/','output-ext':'.html','default-template':'templates/0.html','build-threads':4,'incremental-mode':'modified','minify-exts':[]};(base/'.nift/config.json').write_text(json.dumps({'config':cfg}));entries=[dict(name='gen',title='generator',template='')]+[dict(name=str(i),title=str(i),template=f'templates/{i%4}.html',depends=['gen']) for i in range(n)];(base/'.nift/tracked.json').write_text(json.dumps({'tracked':entries}))
 for j in range(4):(base/f'templates/{j}.html').write_text(f'<html><body><!--LAYOUT{j}-->@input("partials/shared.html")@json(doc,"data/schema.json","data/shared.json")<data>$[doc.x]</data>@input("public/gen.html")<main>@content</main></body></html>\n')
 (base/'partials/shared.html').write_text('<nav>PARTIAL</nav>\n');(base/'data/schema.json').write_text('{"type":"object"}');(base/'data/shared.json').write_text('{"x":"DATA"}');(base/'content/gen.html').write_text('<aside>GENERATED</aside>\n')
 for i in range(n):(base/f'content/{i}.html').write_text(f'<h1>PAGE{i}</h1>\n')
 r=subprocess.run([bins['e2'],'build','--all'],cwd=base,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr)
 candidate=p/f'website-{n}-candidate';shutil.rmtree(candidate,ignore_errors=True);shutil.copytree(base,candidate);r=subprocess.run([bins['e3b'],'build','--all'],cwd=candidate,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr);bases={'e2':base,'e3b':candidate}
 expected={f'{i}.html':(base/f'public/{i}.html').read_bytes() for i in range(n)};assert all(b'<data>DATA</data>' in v for v in expected.values()),'json output'
 for case in ['noop','page','template','partial','data','generated']:
  rounds=12 if case=='noop' else 3
  for k in range(rounds):
   maps=[]
   for label in (['e2','e3b'] if k%2==0 else ['e3b','e2']):
    if case=='noop':d=bases[label]
    else:d=p/'website-working';shutil.rmtree(d,ignore_errors=True);shutil.copytree(bases[label],d)
    before={i:(d/f'.nift/public/{i}.info.json').stat().st_mtime_ns for i in range(n)};oracle=dict(expected)
    if case=='page':(d/'content/0.html').write_text('<h1>EDIT0</h1>\n');oracle['0.html']=oracle['0.html'].replace(b'PAGE0',b'EDIT0');expected_rebuilt=1
    elif case=='template':f=d/'templates/0.html';f.write_text(f.read_text()+'<!--TEMPLATE-EDIT-->\n');oracle={key:(value+b'<!--TEMPLATE-EDIT-->\n' if int(key[:-5])%4==0 else value) for key,value in oracle.items()};expected_rebuilt=(n+3)//4
    elif case=='partial':(d/'partials/shared.html').write_text('<nav>PARTIAL-EDIT</nav>\n');oracle={key:value.replace(b'PARTIAL',b'PARTIAL-EDIT') for key,value in oracle.items()};expected_rebuilt=n
    elif case=='data':(d/'data/shared.json').write_text('{"x":"DATA-EDIT"}');oracle={key:value.replace(b'>DATA<',b'>DATA-EDIT<') for key,value in oracle.items()};expected_rebuilt=n
    elif case=='generated':(d/'content/gen.html').write_text('<aside>GENERATED-EDIT</aside>\n');oracle={key:value.replace(b'GENERATED',b'GENERATED-EDIT') for key,value in oracle.items()};expected_rebuilt=n
    else:expected_rebuilt=0
    trace=d/'actions.trace';trace.unlink(missing_ok=True);old=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter_ns();r=subprocess.run([bins[label],'build'],cwd=d,capture_output=True,text=True);wall=(time.perf_counter_ns()-start)/1e6;new=resource.getrusage(resource.RUSAGE_CHILDREN);assert r.returncode==0,(n,case,label,r.stdout,r.stderr)
    mapping={f'{i}.html':(d/f'public/{i}.html').read_bytes() for i in range(n)};assert mapping==oracle,(n,case,label,'output mismatch');rebuilt=sum((d/f'.nift/public/{i}.info.json').stat().st_mtime_ns!=before[i] for i in range(n));assert rebuilt==expected_rebuilt,(n,case,label,rebuilt,expected_rebuilt);maps.append(mapping)
    rows.append(dict(size=n,case=case,round=k,warmup=case=='noop' and k<2,binary=label,wall_ms=wall,cpu_ms=1000*(new.ru_utime+new.ru_stime-old.ru_utime-old.ru_stime),rebuilt_pages=rebuilt,outputs_pass=True));(p/'websites.json').write_text(json.dumps(rows,indent=2))
   assert maps[0]==maps[1]
  print(n,case,[(label,round(statistics.median(x['wall_ms'] for x in rows if x['size']==n and x['case']==case and x['binary']==label and not x['warmup']),3)) for label in bins],flush=True)
 for case in ['sidecar-unchanged','sidecar-whitespace','sidecar-add','sidecar-remove','sidecar-replace','sidecar-malformed','sidecar-invalid-parent','sidecar-invalid-escape','sidecar-delete','sidecar-new']:
  observed=[]
  for label in ['e2','e3b']:
   d=p/'website-working';shutil.rmtree(d,ignore_errors=True);shutil.copytree(bases[label],d);side=d/'content/0.deps.json'
   for name in ['one','two']:(d/f'data/{name}.txt').write_text(name);os.utime(d/f'data/{name}.txt',ns=(1600000000000000000,)*2)
   if case!='sidecar-new':
    side.write_text('{"dependencies":["data/one.txt"]}');os.utime(side,ns=(1600000000000000000,)*2);r=subprocess.run([bins[label],'build','0'],cwd=d,capture_output=True,text=True);assert r.returncode==0,(case,label,r.stdout,r.stderr)
   before={i:(d/f'.nift/public/{i}.info.json').stat().st_mtime_ns for i in range(n)}
   if case=='sidecar-delete':side.unlink()
   elif case!='sidecar-unchanged':
    raw={'sidecar-whitespace':'{  "dependencies" : [ "data/one.txt" ] }', 'sidecar-add':'{"dependencies":["data/one.txt","data/two.txt"]}', 'sidecar-remove':'{"dependencies":[]}', 'sidecar-replace':'{"dependencies":["data/two.txt"]}', 'sidecar-malformed':'{broken', 'sidecar-invalid-parent':'{"dependencies":["../outside"]}', 'sidecar-invalid-escape':r'{"dependencies":["data/\q.txt"]}', 'sidecar-new':'{"dependencies":["data/two.txt"]}'}[case]
    side.write_text(raw);stamp=max(before.values())+1000000000;os.utime(side,ns=(stamp,stamp))
   old=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter_ns();r=subprocess.run([bins[label],'build'],cwd=d,capture_output=True,text=True);wall=(time.perf_counter_ns()-start)/1e6;new=resource.getrusage(resource.RUSAGE_CHILDREN)
   failed=case in ['sidecar-malformed','sidecar-invalid-parent','sidecar-invalid-escape'];assert (r.returncode!=0)==failed,(n,case,label,r.stdout,r.stderr)
   mapping={f'{i}.html':(d/f'public/{i}.html').read_bytes() for i in range(n)};assert mapping==expected
   rebuilt=sum((d/f'.nift/public/{i}.info.json').stat().st_mtime_ns!=before[i] for i in range(n));assert rebuilt==(0 if failed or case=='sidecar-unchanged' else 1),(case,label,rebuilt)
   observed.append((r.returncode,rebuilt,mapping));rows.append(dict(size=n,case=case,round=0,warmup=False,binary=label,wall_ms=wall,cpu_ms=1000*(new.ru_utime+new.ru_stime-old.ru_utime-old.ru_stime),rebuilt_pages=rebuilt,outputs_pass=True,error_pass=True,stdout=r.stdout,stderr=r.stderr))
  assert observed[0]==observed[1];(p/'websites.json').write_text(json.dumps(rows,indent=2));print(n,case,'PASS',flush=True)
 shutil.rmtree(base);shutil.rmtree(candidate);shutil.rmtree(p/'website-working',ignore_errors=True)
