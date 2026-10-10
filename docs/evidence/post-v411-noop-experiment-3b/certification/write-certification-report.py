from pathlib import Path
import json,shutil,hashlib,ast,subprocess
repo=Path('/home/nick/Repositories/nift/nift');out=repo/'docs/evidence/post-v411-noop-experiment-3b/certification';scratch=Path('/tmp/nift-sidecar-experiment');sha='7d36fd91133bc41f8a01ad2f046835367f2cc901'
runs=json.loads((scratch/'hosted-current.json').read_text())
assert len(runs)==11 and all(r['headSha']==sha and r['status']=='completed' and r['conclusion']=='success' for r in runs),runs
native=json.loads((out/'native-summary.json').read_text());assert all(v['source_sha']==sha and v['crossover_passed'] for v in native.values())
for name in ['ProjectInfo.cpp','ProjectInfo.h']:
 assert subprocess.check_output(['git','show',sha+':src/'+name])==(repo/'docs/evidence/post-v411-noop-experiment-3b/data'/name).read_bytes()
assert ast.dump(ast.parse(subprocess.check_output(['git','show',sha+':tests/sidecar_state_contracts.py'])))==ast.dump(ast.parse((repo/'docs/evidence/post-v411-noop-experiment-3b/data/sidecar_state_contracts.py').read_text()))
for name in ['hosted-current.json','process-final-retry.json','process-final-attempt.json','process-final-first-failure.txt','hosted-c20124-checkpoint.json']:
 shutil.copy2(scratch/name,out/name)
identity=json.loads((out/'identity.json').read_text());identity.update(remote_candidate_sha_at_push=sha,metadata_representation_unchanged=True,performance_runtime_unchanged=True,certified=True,hosted_runs={r['workflowName']:r['databaseId'] for r in runs});(out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
text=f'''# E3B native and hosted certification

**CERTIFIED / READY FOR FINAL LANDING REVIEW. Next: NONE.** The retained candidate is `{sha}`. Its remote `origin/main` SHA matched exactly after the candidate push. The evidence is a separate normal commit containing this report and receipts; its SHA is returned with the handoff.

The reviewed E3B runtime was first committed as `56e9af7a290bef7ba24ba12cd6e03e4621461949`. Both runtime source files remain byte-identical to the measured archive. Metadata schema, `bytes-hex`, declaration indices, absent-state representation, reader pipeline and all performance runtime code are **unchanged**. No E3A, graph, packing, encoding change, version change, tag or release was included. Official Labs was untouched. All commits and pushes were normal; no history was amended or force-pushed.

## Source and binary identity

| File | SHA-256 |
|---|---|
| src/ProjectInfo.cpp | `44501382d6431bbe439c6981f4aa533d3ecc3d5ce4f415b27c7bceff3d40b23d` |
| src/ProjectInfo.h | `d68a320112c7b85fc17d7a6440549981bf718231e252a78bfec9f092fd66f0b6` |
| Final permanent sidecar test | `85b0f45cdcdb6974307e7a6a12b02ef66a0aaf29baeb452c9d67fc1ebb0e155d` |

The original permanent test differs only by a newline after its helper definition. Its complete Python AST and all assertions match the reviewed test; [test-ast-identity.json](test-ast-identity.json) records that verification. The untouched reviewed copy remains in the experiment data.

The normal local committed build reproduces the accepted Linux binary SHA-256:

`65719bd1a91dd901d3fec51a6c999fb83564d1ce207990f784daed0870a41b26`

Hosted builds record their own platform/toolchain hashes:

| Platform | Binary SHA-256 | Source SHA |
|---|---|---|
'''
for name,data in native.items():text+=f"| {name} | `{data['binary_sha256']}` | `{data['source_sha']}` |\n"
text+='''
[identity.json](identity.json), [native-summary.json](native-summary.json) and [final native receipts](final-native/) provide the complete identities.

## Native semantics and actual metadata transfer

Linux, macOS and Windows each passed the 40-case sidecar-state suite against an independently built immutable E2 baseline `c5f449c31cf93bd0155cae0332d6c4ffdd2aa161`. All three passed consumer snapshot contracts and 27 targeted/generated/hook cases. The sidecar suite covers authoritative parse-byte binding, hook provenance, exact CRLF/UTF-8/escaped-byte roundtrip, migration/fallback, malformed/corrupt cache state and missing-edge eligibility. Later hook changes suppress only the new certificate, preserving E2 behavior.

Linux/macOS each passed six native platform contracts; Windows passed seven, including native separator spelling and canonical declaration membership. Each explicitly replaced declarations while preserving the filesystem's actual native timestamp. Old E2 metadata remained readable and acquired state only after a successful candidate rebuild.

| Native randomized campaign | Scheduled operations | Builds | Fresh-build oracles | Explicit skips |
|---|---:|---:|---:|---|
| Linux | 288 | 645 | 288 | None |
| macOS | 288 | 645 | 288 | None |
| Windows | 288 | 540 | 243 | 30 native-symlink; 15 POSIX-interruption |

Those Windows skips are not claimed as covered operations. The separate checkpoint campaign passed all 18 native Windows path-identity cases, including aliases, Windows spelling and supported link/containment behavior. Its status suite records six unsupported POSIX permission fixtures on Windows; the other 24 pass.

Actual exported metadata was downloaded between native runners. Windows-certified state passed authoritative-fallback checks on Linux and macOS in modified/hash/hybrid modes (three cases per receiving platform). Both Linux- and macOS-certified state passed the corresponding Windows fallback checks (six cases). These use actual exported certificates; they are not just synthetic platform-marker tests. A malformed sidecar with matching certificate bytes and current historical sidecar hash makes improper reuse observable, so incompatible provenance must reach the authoritative parser. The added platform-check-bypass mutant is detected by this test. Local synthetic-provenance controls are separately labeled.

The checkpoint comparison passed all 18 portable cases with no mismatches and passed platform-specific contracts. All three corpus source receipts identify the final SHA. See [checkpoint receipts](checkpoint-final/) and [native transfer receipts](final-native/).

## Local committed and retained correctness evidence

NRS **94/94** passed on Linux at suite SHA `6da99128a5ea053551fe952a4994a390a38d0258`, using the committed CLI and rebuilt candidate embedding prefix. PRS **12/12** passed on Linux at suite SHA `1da43659da269c96af21aea7234799d2ad56b2df`. Native macOS/Windows NRS/PRS are not claimed.

The committed local binary reproduces the measured candidate exactly. Its 40 sidecar contracts and 18-case checkpoint corpus passed. The corrected existing mutation harness caught all nine mutants. Together with seven E3B-specific and two extra provenance/eligibility mutants, the reviewed campaign detects **18/18 unique mutants**. The added platform-transfer suite also detects the already-known platform-check-bypass mutation; this is an additional detection, not a nineteenth unique mutation.

The byte-identical runtime retains the full local make-test, bindings, 30 status-adversarial, 15 path-identity, 27 targeted snapshot, 18 preserved-exact-mtime and 21 sidecar-behavior controls. The extended randomized campaign passed 36 mode/seed cases, **3,456 operations**, **7,425 builds** and **3,456 fresh-build oracles**. Both ASan/UBSan/leak campaigns passed with leak detection enabled. Native-process/ptrace and LeakSanitizer sandbox limitations were rerun without weakening assertions and are preserved in the historical report. No current-input status cache or historical-snapshot authority was added.

## Exact-SHA hosted walls

All eleven workflows have successful final conclusions and are bound to `'''+sha+'''`:

| Workflow | Run ID | Final status |
|---|---:|---|
'''
for r in sorted(runs,key=lambda r:r['workflowName']):
 suffix=' (attempt 2)' if r['workflowName']=='Process hardening contracts' else ''
 text+=f"| [{r['workflowName']}](https://github.com/nift-dev/nift/actions/runs/{r['databaseId']}) | {r['databaseId']} | PASS{suffix} |\n"
text+='''
No publication workflow was dispatched. Raw exact-SHA status is in [hosted-current.json](hosted-current.json).

## Preserved failures and normal integration fixes

The initial runtime checkpoint remains intact. Required certification integration was corrected through later normal commits:

| Commit | Change |
|---|---|
| `125df927903df0b62afc122afa62b4110f090fba` | Update the existing late-hash mutant anchor to the reviewed new call signature; all nine controls caught |
| `5bdbe715915f2adb7e78146d423761df3fc93b96` | Request the native Windows `nift.exe` make target |
| `c20124abf4ad3b389acce63d746c5240cb1fccec` | Include hidden build receipts in artifact upload; retry deletion of readonly temporary oracle metadata on Windows |
| `7d36fd91133bc41f8a01ad2f046835367f2cc901` | Put the existing returned subprocess call on a separate line for scanner recognition; verified identical test AST |

Native run `38079956697` failed on the Windows make target before compilation, while Linux/macOS contracts passed but artifact upload excluded hidden receipts. Run `38080154328` passed Windows sidecar, platform, snapshot and targeted cases, then failed deleting readonly oracle metadata. The cleanup fix retries the same operation after clearing the Windows readonly attribute; other errors still propagate. Local 288-operation rerun and controlled cleanup/error-propagation checks passed. The complete native and actual-transfer campaign passed at c20124ab and again at the final SHA. Its earlier receipts are in [historical-c20124](historical-c20124/).

The c20124ab static integrity scan reported the inline returned call as discarded. Its callers already assert subprocess results; the scanner supports a standalone returned call. The newline-only fix changed no AST, assertion or scanner rule. The unchanged scanner then found zero issues and the final hosted static, deterministic, aggregate and binding gates passed.

The final process wall's first Windows attempt failed the standalone sentinel assertion (`unrelated inheritable handle leaked`). This unit compiles only unchanged Process/JobControl sources and does not link E3B. Its probe checks numeric handle validity without proving object identity, so handle-value reuse is a possible false-positive cause, **not proven here**. One unchanged failed-job retry passed (attempt 2). No assertion, threshold or source was changed for that retry. The first red log, analysis and successful exact-SHA attempt metadata are retained in [process failure log](process-final-first-failure.txt), [retry analysis](process-retry-analysis.json) and [final attempt](process-final-attempt.json). This transient failure remains visible for review; it is not represented as a diagnosed process fix.

Older incomplete workflows were marked superseded/cancelled when the certification integration SHA changed. Their IDs/status snapshots remain in this directory. Failures and prior commits were not hidden or rewritten.

## Performance and accepted costs

The measured runtime is unchanged: native 10k no-op **775.564 -> 586.396 ms**, **24.39% faster**, with gains across all fixture sizes and worker counts. The 10k workflow removes 10,015 sidecar parses, 60,031 declaration validations, 70,046 duplicate comparisons and 3.63 million allocator requests while retaining sidecar byte reads and all 90,076 saved-edge checks.

The costs remain explicit: persisted page-info metadata **8,070,235 -> 13,933,996 bytes (+72.66%)**; the certificate alone adds roughly 5.56 MB. Four-worker RSS rises 420 KiB; eight-worker RSS rises 796 KiB. Ordinary 5k website no-op is **3.21% slower** and generated rebuild **3.78% slower**. This is not a universal website throughput win. Representation and ordinary website performance were not tuned during certification.

Architectural lesson: E3A removed 100,038 repeated status observations for about **2.7%** gain; E3B removes a redundant declaration workflow for about **24.4%**. Future work should favor eliminating repeated workflows over micro-optimizing individual filesystem primitives. Compaction, certified-absence representation, other encodings and no-sidecar website tuning are separate future investigations requiring review; none is implemented here.

See the [historical experiment report](../report.md) for all benchmark samples, operation attribution, metadata accounting, assumptions and limits. Exact-byte state assumes stable inputs within a consumer check; this campaign does not prove arbitrary concurrent external-writer equivalence or authenticate coherently forged metadata.

Recommendation: **CERTIFIED**. Metadata representation unchanged: **YES**. Performance runtime unchanged: **YES**. Next: **NONE — STOP FOR REVIEW**.
'''
(out/'report.md').write_text(text)
print('Final certification report written')
