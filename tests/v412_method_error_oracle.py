#!/usr/bin/env python3
"""Adversarial exactly-once oracle for native replace/split error paths.

Verifies that declining a native method on a validation error does not cause the
canonical fallback to re-evaluate the receiver or arguments. Each probe prints a
marker; the marker counts must be exactly one per evaluated expression.
"""
import subprocess, sys, tempfile
from pathlib import Path

_argv = [x for x in sys.argv[1:] if x != "--negative-control"]
_neg = "--negative-control" in sys.argv
NIFT = str(Path(_argv[0]).resolve()) if _argv else sys.exit("usage: <oracle> <nift-binary>")

def run(script):
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "case.f"; p.write_text(script)
        v = subprocess.run([NIFT, str(p)], input="x\n", capture_output=True, text=True, timeout=30)
    return v.returncode, v.stdout, v.stderr

LOOP = lambda body: "while(true) { line := read(); if(line == null) { break }; " + body + " }\n"
HDR = ('fn(mk()) { print("R"); return "abc" }\n'
       'fn(empty()) { print("E"); return "" }\n'
       'fn(one()) { print("O"); return 1 }\n'
       'fn(a()) { print("A"); return "a" }\n'
       'fn(b()) { print("B"); return "b" }\n'
       'fn(c()) { print("C"); return "c" }\n')

cases = []
def case(name, body, direct=False):
    script = HDR + (body + "\n" if direct else LOOP(body))
    cases.append((name, script, direct))

# valid baseline: R,A,B once, result r
case("valid_effect_all", 'out := mk().replace(a(), b()); print(out)', direct=True)
case("valid_effect_all_prep", 'out := mk().replace(a(), b()); print(out)')
# empty old produced by effectful arg -> error; R,E once
case("empty_old_effect", 'mk().replace(empty(), "y")')
case("empty_old_effect_direct", 'mk().replace(empty(), "y")', direct=True)
# non-string arg produced by effectful fn -> error; R,O once
case("nonstring_arg_effect", 'mk().replace(one(), "y")')
# wrong arity with effectful args -> error; R,A,B,C once
case("arity_effect", 'mk().replace(a(), b(), c())')
# split non-string delimiter from effectful fn -> R,O once
case("split_nonstring_effect", 'mk().split(one())')
# effectful receiver, pure args -> R once
case("effect_receiver_empty_old", 'mk().replace("", "y")')
# nested chain: mk() once, empty() once
case("nested_chain", 'mk().to_upper().replace(empty(), "y")')
# invalid op not followed by later arg evaluation: b() must not run if a() fails? language: args evaluated left-to-right before the call; both run.
case("second_arg_after_first", 'mk().replace(one(), b())')

import collections as _c
if _neg:
    # A deliberately replaying script (two mk() calls, one in the expression):
    # the harness must DETECT that the probe ran more than once.
    script = HDR + 'a := mk()\nb := mk()\nprint(a.replace("", "y"))\n'
    rc, out, err = run(script)
    counts = _c.Counter(ch for ch in out if ch in "REOABC")
    detected = counts["R"] != 1
    print(f"negative control: R_count={counts['R']} detected_replay={detected}")
    sys.exit(0 if detected else 1)

fails = 0
for name, script, direct in cases:
    rc, out, err = run(script)
    import collections
    counts = collections.Counter(ch for ch in out if ch in "REOABC")
    print(f"{name}: rc={rc} counts={dict(counts)} out={out.strip()!r} err={err.strip().splitlines()[-1] if err.strip() else ''!r}")
    # exactly-once assertions
    ok = True
    for marker in counts:
        if counts[marker] != 1:
            ok = False
    if not ok:
        fails += 1
        print(f"   FAIL exactly-once: {name}")
print(f"method-error oracle: {len(cases)-fails}/{len(cases)} exactly-once")
sys.exit(1 if fails else 0)
