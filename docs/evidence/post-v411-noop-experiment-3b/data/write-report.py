from pathlib import Path
import json,csv,statistics
p=Path('/tmp/nift-sidecar-experiment');out=Path('/home/nick/Repositories/nift/nift/docs/evidence/post-v411-noop-experiment-3b');d=out/'data';s=json.loads((d/'summary.json').read_text())
fmt=lambda v:f'{v:,.3f}'
def timing_table(family,keys):
 text='| Size / workers | E2 median [min–max], ms | E3B median [min–max], ms | Improvement | Child CPU E2 → E3B, ms |\n|---:|---:|---:|---:|---:|\n'
 for key in keys:
  group=s[family][str(key)];a=group['e2'];b=group['e3b']
  cell=lambda x:fmt(x['wall_ms']['median'])+' ['+fmt(x['wall_ms']['minimum'])+'–'+fmt(x['wall_ms']['maximum'])+']'
  text+=f'| {key:,} | {cell(a)} | {cell(b)} | {group["improvement_percent"]:.2f}% | {fmt(a["child_cpu_ms"]["median"])} → {fmt(b["child_cpu_ms"]["median"])} |\n'
 return text
web='| Pages | Scenario | E2 median, ms | E3B median, ms | Improvement |\n|---:|---|---:|---:|---:|\n'
for n in [100,1000,5000]:
 for case in ['noop','page','template','partial','data','generated']:
  g=s['websites'][f'{n}/{case}'];web+=f'| {n:,} | {case} | {fmt(g["e2"]["wall_ms"]["median"])} | {fmt(g["e3b"]["wall_ms"]["median"])} | {g["improvement_percent"]:.2f}% |\n'
rss='| Workers | E2 peak RSS median, KiB | E3B peak RSS median, KiB | Delta, KiB |\n|---:|---:|---:|---:|\n'
for t in [1,2,4,8]:
 g=s['rss'][str(t)];rss+=f'| {t} | {g["e2"]:,} | {g["e3b"]:,} | {g["e3b"]-g["e2"]:+,} |\n'
a=json.loads((p/'alloc-e2.json').read_text());b=json.loads((p/'alloc-e3b.json').read_text());alloca=sum(a[k] for k in ['malloc','calloc','realloc','aligned']);allocb=sum(b[k] for k in ['malloc','calloc','realloc','aligned'])
ops='| Operation | E2 | E3B | Removed |\n|---|---:|---:|---:|\n'
for label,x,y in [('Current sidecar logical reads',10015,10015),('Current sidecar bytes read',2121273,2121273),('Sidecar JSON decodes',10015,0),('Authored declaration validations',60031,0),('Reconstructed current-set edges',70046,0),('Duplicate current comparisons',70046,0),('All dependency comparisons',160122,90076),('Following dependency status observations',170137,100091),('No-follow safety checks',90076,90076),('path_exists calls',110112,40066),('relative_of calls',90076,30045),('Checked reads, all roles',20032,20032),('JSON load/parse-helper calls',20031,10016),('Native newfstatat',410422,270330),('Native openat',40077,40077),('Native read',20038,20038),('Native lseek',60096,60096),('Allocator requests',alloca,allocb)]:ops+=f'| {label} | {x:,} | {y:,} | {x-y:,} |\n'
report=f'''# EXPERIMENT 3B — BYTE-BOUND DECLARATION REUSE

Recommendation: **RETAIN the bounded prototype for review and native certification. Do not land yet.** The fresh 10k paired median improves **24.39%**, from **775.564 to 586.396 ms**. This clears the fixed ≥15% retention target without combining E3A, another reader, hashing changes or metadata packing. The largest ordinary website no-op regresses **3.21%**, and persisted metadata grows **72.66%**. Those costs are part of the recommendation.

**Production remains E2 `64d68993a981fdb6aaf6a52e37c666b035073b3e`, with evidence HEAD `c5f449c31cf93bd0155cae0332d6c4ffdd2aa161`. Nothing committed or pushed. Implementation authorization: NONE FURTHER. STOP FOR REVIEW.** Native macOS and Windows certification is outstanding; this is not a production-certified candidate.

## Candidate and representation

Runtime changes exist only in scratch `/tmp/nift-sidecar-experiment`: `ProjectInfo.cpp` and `ProjectInfo.h`. The reviewable [patch](data/candidate.patch), exact sources and [identity receipt](data/identity.json) are retained. The header adds private helper declarations and a nested observation type, with no new ProjectInfo data members or class-layout change. A scratch rebuild produced exactly the measured binary SHA-256, `65719bd1a91dd901d3fec51a6c999fb83564d1ce207990f784daed0870a41b26`. Frozen E2 SHA-256 is `9d7e1438531c5f476c4603fb0a2d79d614b49d98ffbea3787edeb1842c7c92e5`.

The permanent candidate test is [tests/sidecar_state_contracts.py](../../../tests/sidecar_state_contracts.py), presently uncommitted. Its copy is in [data](data/sidecar_state_contracts.py). Other harnesses and raw receipts are preserved alongside it. Production tracked sources, versions, tags, releases, authored dependency formats, official Labs evidence and Jsonic++ are unchanged.

Each successful consumer may append this Nift-owned derived state to its existing `.info.json`:

```json
{{"sidecar-state":{{"version":1,"platform":"posix-lexical-v1","present":true,"bytes-hex":"7b22646570656e64656e63696573223a5b22646174612f6f6e652e747874225d7d","declaration-indices":[2]}}}}
```

Bytes use reversible lowercase hex, including whitespace, escaping, newline spelling and arbitrary accepted byte values. The example represents `{{"dependencies":["data/one.txt"]}}`; index 2 refers to that path in the consumer's existing saved dependency array. Indices are sorted and unique; paths are not duplicated in the certificate. An absent observation writes `present:false`, empty bytes and empty membership.

Provenance records the lexical normalization policy and path-syntax family: POSIX or Windows. The current `relative_of` implementation uses lexical normalization/relative conversion without case or Unicode folding. A future declaration-validation/normalization policy change must invalidate this version/provenance before reuse.

## Provenance and publication

The loader captures the exact buffer passed to the successful parse and the normalized declaration set validated from that buffer. The **second declaration parse, after rendering**, supplies the authoritative observation. The first parse and existing generic dependency hashes retain E2 behavior.

After file post-hooks, existing dependency/hash/post-output validation and stale pagination cleanup, the candidate freshly checks the sidecar again. It publishes the captured bytes and membership only when presence and literal bytes still match that authoritative observation. This final read verifies the observation; its bytes are never substituted for the bytes that produced membership. A later change or failed read suppresses the certificate while retaining E2's successful-build behavior. Publication uses the existing atomic readonly metadata writer.

A→B→A, B→A→B and multiple hook changes all suppress the certificate. Stable B→B→B certifies B. A→B→B succeeds in modified mode with B's certificate; E2 rejects it in hash/hybrid mode as a dependency changed during the build, and the candidate likewise fails without publishing new metadata. Follow-up tests delete a path named only by the restored final sidecar and require normal loader failure on the next invocation.

## Reuse, migration and fallback

Every ordinary saved dependency still receives E2's safety, no-follow, containment, status and mode-specific historical-snapshot checks. The implementation uses a conservative whole-consumer clean gate: **any dirty, missing, erroneous or unsafe saved edge, or either known value-fingerprint role, forces the ordinary loader**. Requirement checks run before the reuse decision. There is no per-edge status table, E3A cache or cross-consumer reuse.

For a present certificate, the candidate validates version, provenance, field types, integer/range/unique indices and eligible saved roles; freshly runs the existing presence/readability and checked byte pipeline; decodes prior bytes; compares literal bytes; and requires the expected sidecar's own saved edge. All referenced ordinary edges were already checked clean. It then skips the current declaration parser, path/set reconstruction, declaration validation and duplicate comparison loop. No FNV or other digest authorizes declaration reuse.

Absent state still requires a fresh existence observation. Newly created/deleted/unreadable sidecars are detected. Modified/hybrid `>=` decisions remain in the saved-edge checks; equal bytes do not turn a dirty timestamp clean. Generic hash snapshots remain independently authoritative for ordinary hash/hybrid dirty decisions.

Old E2 metadata is accepted and takes the normal loader path. A clean old consumer is not rewritten merely to populate a certificate; a subsequent successful build adds it. Missing/unsupported/malformed cache state also falls back. Changed bytes with old timestamps can require both the certificate read and a fallback loader read. The optimization is deliberately scoped to a consumer check with stable inputs; it does not promise equivalence to E2's additional later observations of arbitrary concurrent external edits. The corruption evidence covers the listed structural cases, not every coherent edit to derived metadata.

## Operations at certified 10k clean modified

{ops}

All **10,015** consumers hit reuse. The 60,031 validations and 70,046 current-set/comparison edges disappear, while all 90,076 saved edges remain checked. Their current-workflow join sites are not executed; no separate machine-level path-append count is claimed. [Fresh E2 counters](data/counts-e2-fresh.csv) and [E3B counters](data/counts-e3b.csv) bind counts; detailed path fanout is gzip-compressed.

`relative_of` reaches 30,045 rather than the proposed ~20,030 because validating the sidecar's own membership retains one relative conversion per consumer. `path_exists` removes 70,046 calls: 60,031 authored declaration checks plus 10,015 redundant initial sidecar existence probes. The retained readability/checked-read pipeline still opens each sidecar normally; native opens/reads/seeks are identical. This extra existence-probe removal explains 270,330 native stats rather than the original ~280,345 estimate. Unique following-status paths remain 70,099; the removed observations were duplicates.

Scope timings are inclusive and overlap; they are not added into a wall-time prediction. Earlier E2 counter receipts are retained, but the table uses the freshly rebuilt instrumented E2 control. Diagnostic instrumentation, allocation interception and strace were outside all ordinary timing series.

## Metadata, parse inputs and allocations

| Quantity | E2 | E3B | Delta |
|---|---:|---:|---:|
| `.info.json` files | 10,015 | 10,015 | 0 |
| `.info.json` bytes | 8,070,235 | 13,933,996 | +5,863,761 / +72.66% |
| Info/config/sidecar decoder-input bytes | 10,191,751 | 13,934,239 | +3,742,488 / +36.72% |
| All JSON parser-input bytes, including tracking | 12,565,017 | 16,307,505 | +3,742,488 / +29.78% |
| All checked-read bytes | 12,565,017 | 18,428,778 | +5,863,761 / +46.67% |
| Allocator requests | {alloca:,} | {allocb:,} | {allocb-alloca:+,} / {100*(allocb/alloca-1):+.2f}% |
| Cumulative requested allocation bytes | {a['requested_bytes']:,} | {b['requested_bytes']:,} | {b['requested_bytes']-a['requested_bytes']:+,} |

The original accepted E2 fixture omits `dependency-hashes`; today's writer emits an empty object in modified mode. That accounts for **300,450 bytes** of the actual size delta. The certificate itself adds **5,563,311 bytes**; the equivalent current E2 writer format would total 8,370,685 bytes. This attribution is calculated by removing only the certificate text from actual candidate metadata; it is not a separate timing control or a newly rebuilt E2 fixture.

The 2,121,273 raw sidecar bytes occupy 4,242,546 hex characters. Indices and certificate fields add another 1,320,765 bytes. This exceeds the earlier ~3.53 MB raw-string model, as expected for an unoptimized explicit encoding. No encoding optimization was attempted.

The decoder counter excludes the separate unchanged streaming tracking parser. Its actual source is 2,373,266 bytes and is read/parsed once in both controls; the all-parser row includes it. Thus the earlier progress update's ~37% figure applies to the instrumented decoder subset, while complete JSON input grows ~30%.

Allocation counts use the same owned glibc-entry interceptor in both binaries: malloc, calloc, realloc and aligned requests, excluding the interceptor's final report I/O. They are cumulative requests, not peak/live heap bytes. They are not added to operator-new events. [Allocator source](data/alloc.c) and receipts are retained.

## Native paired timings

{timing_table('native',[100,1000,5000,10000])}

Two warmup pairs and **20 alternating measured pairs at every size**, with four workers and affinity CPUs 0–3 (two physical cores with SMT). No owned compilation/test/profile overlapped an ordinary timing series. Worker/RSS and website campaigns were separate. Linux 7.0.0-29-generic; GCC 15.2.0. Raw samples, Q1/Q3, ranges and child CPU are in [summary](data/summary.json) and [native samples](data/native.json).

Candidate metadata came from actual successful forced candidate builds, not fabricated certificates. Initial compilation/setup is excluded from no-op timings. The harness swaps two `.nift` state directories at the **same fixture path**: original E2 state versus newly certified candidate state, with identical authored inputs and output paths. Forced setup advances output timestamps, so after verifying identical output bytes the harness restores all original output-file timestamps. The initial 100-unit attempt before this correction was rejected and excluded; its failure is retained in the work history, not as a successful measurement.

Every measured invocation succeeds with zero traced native actions. Every action-output SHA-256 remains identical and the executable's stdout matches its manifest oracle. The original E2 state is restored after each campaign. These are accepted disposable `/tmp` fixtures; official Labs remains untouched.

## Workers and RSS

{timing_table('workers',[1,2,4,8])}

Two warmups and ten alternating measured pairs per worker count, same affinity. Three independent GNU-time peak-RSS observations per binary/worker count, outside ordinary pairs:

{rss}

There is no retained graph or status cache. The four-worker RSS delta is **420 KiB**; the largest eight-worker delta is **796 KiB**. RSS values are medians of three peaks and fluctuate with scheduling/allocator behavior.

## Website campaign

{web}

The established shared-template/partial/JSON/generated-output fixture was freshly built separately with each binary, so E3B uses real absence certificates. Each size has two no-op warmups plus ten measured alternating pairs, and three alternating pairs for each changed-input scenario. Every complete output map and expected page-rebuild count matches E2. Small changed-case timing deltas have only three pairs and should not be treated as precise wins.

All **222** website observations pass their output/rebuild/error oracles: 162 established observations plus 60 sidecar observations. At 100/1,000/5,000 pages, the sidecar cases are unchanged, whitespace, add, remove, replace, malformed JSON, parent escape, invalid escape, delete and newly added. Valid changes rebuild exactly one page; unchanged rebuilds zero; malformed/escaping cases fail and do not publish new page metadata. Outputs match frozen E2. The added cases use modified mode; the separate 18+21 controls cover all three modes. Full sidecar-case timings/errors are in [website receipts](data/websites.json).

The ordinary 5k no-op is 181.422→187.237 ms (**3.21% slower**), page timing is essentially equal, and generated rebuilds regress 3.78%. The native result is consequently a gain for sidecar-heavy consumers, not a universal website improvement.

## Correctness and certification

| Gate | E3B result |
|---|---|
| Preserved exact-mtime A–F, all modes | **18 PASS**, normalized observable stdout/stderr/exit match E2 |
| Existing sidecar appearance/removal/equal-time/read-error controls | **21 PASS**, observable E2 match |
| Permanent new sidecar/provenance/cache-state contracts | **40 PASS**, including 15 hook/mode cases, 3 missing-edge equivalence cases, byte round-trips, structural corruption and migration |
| Status adversarial | **30 PASS / 0 skips** |
| Alias/path/symlink/containment identity | **15 PASS**, paired E2 control |
| Consumed-byte/historical snapshot contracts | **PASS**, including generated variants, conflicting reads, native/external/interrupt barriers |
| Targeted shared-dependency matrix | **27 PASS / 0 failures** |
| Extended randomized differential | **36 mode/seed cases; 3,456 operations; 7,425 builds; 3,456 full-build oracles PASS** |
| Full ordinary CLI regression (`make -j2 test`) | **PASS** |
| Embedding and Go/C#/Node/Python regression surfaces | **PASS** |
| Independent NRS | **94/94 PASS**, pinned `6da99128a5ea053551fe952a4994a390a38d0258`, candidate embedding prefix enabled |
| Independent PRS | **12/12 PASS**, pinned `1da43659da269c96af21aea7234799d2ad56b2df` |
| Existing incremental source mutants | **9/9 detected** |
| New byte/state/publication/eligibility source mutants | **9/9 detected**; total **18/18** |
| ASan/UBSan + leak checks, both normal and lifetime configurations | **PASS**, status/snapshot/40 new-contract suites in each rebuilt configuration |
| Linux checkpoint corpus | **18 portable cases PASS** |
| Clean candidate reduced-CLI build boundary | **PASS**, unchanged assertions; E2 archive plus the two uncommitted candidate files |
| Native macOS | **NOT RUN** |
| Native Windows | **NOT RUN** |

Corruption covers old/no state; missing version/presence/bytes/membership/platform; non-object state and invalid field types; unsupported version; bad encoding; invalid/fractional/negative/out-of-range/duplicate indices; incompatible fingerprint membership; and provenance mismatch. These tests use matching forged byte identity with malformed current input where possible, requiring fallback parsing and its existing diagnostic. They do not count arbitrary process failures as successful oracle matches.

The mutation controls detect bypassed byte equality, version/platform/index guards, stale publication, publication identity reread from a different buffer, and reuse of a missing saved edge. The missing-edge mutant demonstrably loses E2's “user dependency metadata is invalid” status reason and is caught. Existing consumed-byte, output deletion and hook-dependency mutants remain live.

Two environment-related first attempts are preserved: pagination strace and LeakSanitizer failed under sandbox ptrace restrictions, then passed with native process access and unchanged assertions/leak detection. Go's first scratch build could not obtain VCS status; the binding retry uses `-buildvcs=false` only for this uncommitted scratch tree. No runtime code or correctness threshold was weakened. The clean-boundary harness changes only source preparation, because the production gate otherwise archives committed HEAD; its assertions are unchanged. No candidate commit was created to run it.

The hosted workflow checks out a remote ref, and only the local host is available. Publishing the candidate is outside the current no-commit/no-push instruction. Therefore native macOS/Windows and exact-SHA hosted certification remain outstanding; prior green E2 workflows are not counted as E3B certification.

## Recommendation and handoff

**RETAIN for review and further certification; keep production on E2.** The complete workflow removal gives a 24.39% 10k improvement, removes ~3.63 million allocator requests and retains low peak RSS. It meets the predeclared bar. The tradeoff is 5.86 MB more persisted state, ~30% more total JSON parser input and a slight ordinary-website no-op regression. Review must accept those costs and the derived-state/provenance policy before production adoption.

No status cache, graph rewrite, packed state, new digest, reader redesign or encoding rescue is added. Sources, test harnesses, raw samples, compiler/test receipts and [SHA256SUMS](data/SHA256SUMS) are preserved. Scratch remains available for native certification after a separate review decision.

**Implementation authorization: NONE FURTHER. STOP FOR REVIEW.**
'''
(out/'report.md').write_text(report);print(out/'report.md')
