#!/usr/bin/env python3
"""v4.12 release-certification runner.

Runs the required Linux regression suites against the built candidate, records
passed/failed/skipped per suite, writes a machine-readable summary, and exits
non-zero if any required gate fails. Environmental skips (missing external
prerequisites) are reported and do not count as failures.
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

REQUIRED = [
    "test-call-semantics",
    "test-conformance", "test-control-flow", "test-prepared-method-parity",
    "test-v48-bytes-index-parity", "test-v48-comparison-parity",
    "test-v48-callable-parity", "test-v48-map-set-index",
    "test-cp17-bytes", "test-cp18-bytes", "test-cp19-bytes",
    "test-cp20-bytes", "test-cp21-bytes",
    "test-parser-hardening", "test-v42-language", "test-v43-language",
    "test-v49-selector-parity", "test-v49-json-preflight-guard",
    "test-v49-glob-key-guard", "test-v49-glob-order",
    "test-v410-filesystem-recipe-parity",
    "test-project-state", "test-project-host", "test-incremental-modified-immediate",
    "test-pagination-ordering", "test-contracts",
]

# Mandatory suites above: a failure fails certification.
# Intentionally EXCLUDED from this aggregate (documented, not silently omitted):
#   test-v44-packages            requires external package sources (nift-packages/)
#   test-release-cert            this runner itself
#   performance/networking suites, independent benchmark campaign
# Missing mandatory prerequisites therefore surface as failures, never silent skips.
SKIP_MARKERS = {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--make", default="make")
    ap.add_argument("--jobs", default=str(max(1, (os.cpu_count() or 4))))
    ap.add_argument("--summary", default="release-cert-summary.json")
    ap.add_argument("--include-optional", action="append", default=[])
    a = ap.parse_args()
    root = Path(a.root).resolve()
    targets = REQUIRED + a.include_optional
    results = []
    rc_total = 0
    for tgt in targets:
        t0 = time.time()
        p = subprocess.run([a.make, "-j" + a.jobs, tgt], cwd=root,
                           capture_output=True, text=True)
        dur = round(time.time() - t0, 2)
        status = "passed" if p.returncode == 0 else "failed"
        detail = ""
        if p.returncode != 0:
            marker = SKIP_MARKERS.get(tgt)
            if marker and marker in (p.stdout + p.stderr):
                status = "skipped"
                detail = f"missing prerequisite: {marker}"
            else:
                rc_total = 1
                detail = (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else ""
        results.append({"suite": tgt, "status": status, "seconds": dur, "detail": detail})
        print(f"[{status:7s}] {tgt} ({dur}s){(' - ' + detail) if detail else ''}", flush=True)
    summary = {
        "candidate": "7f7e487 + A13 + B1",
        "platform": os.uname().sysname,
        "passed": sum(1 for r in results if r["status"] == "passed"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "results": results,
    }
    (root / a.summary).write_text(json.dumps(summary, indent=2))
    print(f"release certification: passed={summary['passed']} failed={summary['failed']} skipped={summary['skipped']}")
    return rc_total

if __name__ == "__main__":
    raise SystemExit(main())
