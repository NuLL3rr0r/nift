#!/usr/bin/env python3
"""v4.12 function-call semantic contract (self-contained).

Runs the 35 evaluated-operand cases against the candidate and compares against
the stored corrected-semantics oracle in tests/v412_call_expected.json — no
historical reference binary required.

Only `nested_effect_indices` differs from the historical reference: it stores the
corrected expectation (each index evaluated once; valid expression succeeds)
established by tests/v412_nested_index_oracle.py. All other expectations match
the historical reference.
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load_cases():
    ns = {"loop": lambda body: "while(true) { line := read(); if(line == null) { break }; " + body + " }\n"}
    exec((HERE / "v412_call_cases.py").read_text(), ns)
    return ns["cases"]

def run(binary, src, path):
    path.write_text(src)
    v = subprocess.run([str(Path(binary).resolve()), str(path)], input="one\n",
                       capture_output=True, text=True, timeout=30)
    tmp = str(path.parent)
    def norm(x):
        return x.replace(tmp, "<DIR>").replace("\\", "/")
    return {"stdout": norm(v.stdout), "stderr": norm(v.stderr), "exit": v.returncode}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    args = ap.parse_args()
    cases = load_cases()
    expected = json.loads((HERE / "v412_call_expected.json").read_text())
    assert set(cases) == set(expected), ("case/expectation mismatch",
        set(cases) ^ set(expected))
    failures = []
    with tempfile.TemporaryDirectory(prefix="v412-call-contract-") as t:
        d = Path(t)
        for name, src in cases.items():
            got = run(args.candidate, src, d / (name + ".f"))
            if got != expected[name]:
                failures.append({"case": name, "got": got, "expected": expected[name]})
    print(json.dumps({"total": len(cases), "failed": len(failures), "failures": failures}, indent=2))
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
