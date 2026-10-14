#!/usr/bin/env python3
"""Independent semantic oracle for nested computed-index location chains.

Establishes the intended behaviour (not the historical evaluator's) for
`a.member[i()].nested[j()]`-style expressions:
  * every index expression executes exactly once, left to right;
  * a valid chain evaluates and mutates the intended aggregate;
  * an invalid index fails immediately, without executing later indices;
  * a scalar leaf yields a value, an aggregate leaf yields a location.
"""
import subprocess, sys, tempfile, os
from pathlib import Path

NIFT = str(Path(sys.argv[1]).resolve()) if len(sys.argv) > 1 else sys.exit("usage: <oracle> <nift-binary>")

def run(script):
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "case.f"; p.write_text(script)
        v = subprocess.run([NIFT, str(p)], input="x\n", capture_output=True, text=True, timeout=30)
    return v.returncode, v.stdout, v.stderr

LOOP = lambda body: "while(true) { line := read(); if(line == null) { break }; " + body + " }\n"
HEAD = 'a := {"member":[{"nested":[[1]]}]}\n'

checks = []
def check(name, script, want_out, want_err=None, expect_ok=True):
    rc, out, err = run(script)
    ok = (rc == 0) == expect_ok
    if want_out is not None and out != want_out: ok = False
    if want_err is not None and want_err not in err: ok = False
    checks.append((name, ok, rc, out, err))

# 1. valid nested chain: i and j exactly once, mutation of the original
check("valid_nested_exactly_once",
  HEAD + 'n:=0\nfn(index(tag)) { n+=1; print(tag); return 0 }\nfn(mutate(x)) { x.push(2); return 0 }\n'
  + LOOP('mutate(a.member[index("A")].nested[index("B")]); print(a.stringify()); print(n)'),
  'A\nB\n{"member":[{"nested":[[1,2]]}]}\n2\n')

# 2. valid nested chain, direct (non-prepared) context
check("valid_nested_direct",
  HEAD + 'n:=0\nfn(index(tag)) { n+=1; print(tag); return 0 }\n'
  + 'print(a.member[index("A")].nested[index("B")].stringify())\nprint(n)\n',
  'A\nB\n[1]\n2\n')

# 3. invalid first index (out of range): A once, B never
check("invalid_first_out_of_range",
  HEAD + 'fn(index(tag)) { print(tag); return 99 }\nfn(mutate(x)) { x.push(2); return 0 }\n'
  + LOOP('mutate(a.member[index("A")].nested[index("B")])'),
  None, want_err="out of range", expect_ok=False)

# 3b. assert B was never printed for case 3
rc,out,err = run(HEAD + 'fn(index(tag)) { print(tag); return 99 }\nfn(mutate(x)) { x.push(2); return 0 }\n'
  + LOOP('mutate(a.member[index("A")].nested[index("B")])'))
checks.append(("invalid_first_no_B", "B\n" not in out and out=="A\n", rc, out, err))

# 4. invalid first index (wrong type): A once, B never
check("invalid_first_type",
  HEAD + 'fn(index(tag)) { print(tag); return [] }\nfn(mutate(x)) { x.push(2); return 0 }\n'
  + LOOP('mutate(a.member[index("A")].nested[index("B")])'),
  None, want_err="non-negative integers", expect_ok=False)

# 5. valid first, invalid second (out of range): A and B once each
check("invalid_second_out_of_range",
  HEAD + 'seq:=0\nfn(index(tag)) { seq+=1; print(tag); return (tag=="A")?0:99 }\nfn(mutate(x)) { x.push(2); return 0 }\n'
  + LOOP('mutate(a.member[index("A")].nested[index("B")])'),
  None, want_err="out of range", expect_ok=False)

# 5b. verify exactly A,B once for case 5
rc,out,err = run(HEAD + 'seq:=0\nfn(index(tag)) { seq+=1; print(tag); return (tag=="A")?0:99 }\nfn(mutate(x)) { x.push(2); return 0 }\n'
  + LOOP('mutate(a.member[index("A")].nested[index("B")])'))
checks.append(("invalid_second_A_B_once", out=="A\nB\n", rc, out, err))

# 6. single computed index still works (regression)
check("single_index",
  'a := [[1]]\nn:=0\nfn(index()) { n+=1; print("I"); return 0 }\nfn(mutate(x)) { x.push(2); return 0 }\n'
  + LOOP('mutate(a[index()]); print(a.stringify()); print(n)'),
  'I\n[[1,2]]\n1\n')

# 7. object computed key, nested
check("object_computed_key",
  'a := {"m":{"k":[[1]]}}\nfn(k1()) { print("K1"); return "m" }\nfn(k2()) { print("K2"); return "k" }\nfn(mutate(x)) { x.push(2); return 0 }\n'
  + LOOP('mutate(a[k1()][k2()]); print(a.stringify())'),
  'K1\nK2\n{"m":{"k":[[1],2]}}\n')

# 8. scalar leaf yields value (no location), single evaluation
check("scalar_leaf",
  'a := {"x":[7]}\nn:=0\nfn(index()) { n+=1; print("I"); return 0 }\nfn(id(v)) { return v }\n'
  + LOOP('print(id(a.x[index()])); print(n)'),
  'I\n7\n1\n')

failed = [c for c in checks if not c[1]]
for name, ok, rc, out, err in checks:
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" rc={rc} out={out!r} err={err!r}"))
print(f"nested-index oracle: {len(checks)-len(failed)}/{len(checks)} passed")
sys.exit(1 if failed else 0)
