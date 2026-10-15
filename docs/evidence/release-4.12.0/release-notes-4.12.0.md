# Nift v4.12.0

Nift v4.12 completes the transparent prepared-execution filesystem pipeline and
adds a Linux metadata fast path. Eligible filesystem traversal and build
workloads run faster with existing source code unchanged, on every platform.
C ABI remains **1.3**.

## Prepared filesystem pipeline (P4)

- Eligible filesystem traversal pipelines are now evaluated through a prepared
  entry pipeline: the walker is admitted once and the consumer executes against
  the prepared plan, dropping per-iteration parse and dispatch overhead.
- Real projects benefit automatically. Existing Nift source does not require
  modification, and public filesystem APIs are unchanged.
- Mechanisms remain transparent: when a program mutates selector or root
  bindings mid-run, the interpreter falls back to its normal path rather than
  using a stale prepared plan.

## Prepared execution improvements (P3C)

- Prepared numeric AST operator dispatch with canonical fallback reduces
  interpreter overhead for ordinary scripts.
- Restricted template loop bodies emit once with live value lookup.
- Representative measured walks/stats on the released fixtures are roughly
  2.5–3× faster than the pre-campaign baseline; per-workload results vary with
  fixture shape and are documented in the performance report.

## Linux metadata fast path

- On Linux, metadata acquisition now uses a single coherent `statx` snapshot
  (type and size together, following symlinks) instead of separate metadata
  calls, roughly halving metadata syscalls per file.
- Semantics are unchanged: each `stat` observes the current filesystem state,
  missing paths and permission failures classify as before, and on platforms or
  kernels without `statx` Nift uses its existing portable implementation, so
  behaviour does not vary by operating system.
- Measured on the released fixtures (walk 10k/100k, stat 10k/100k) the
  improvement over the previous pipelined build is roughly 6–9%; conditions and
  medians are in the benchmark report.

## Correctness and reliability

- Prepared and legacy iteration are protected against a use-after-free when the
  underlying collection shrinks during iteration: shrinking no longer invalidates
  the consumed iteration plan. Selector locations are preserved.
- Evaluated-operand expressions complete exactly once and readonly method
  entry/expression completion stays consistent.

## Compact sorting

- Single-selector `sort_by` uses compact Number keys, reducing build memory and
  instruction overhead for large ordinary sorts while preserving stable index
  order.

## Reliability and certification

- Native identity, sidecar and E3B certification now run against the ordinary
  native compilers and executables, including enforced Windows access-denial and
  readonly-oracle handling.
- Dependency status results are reused within dirty checks without duplicating
  path normalization, and returned subprocess results are exposed to integrity
  scans.
- Recursive captured callables share immutable lambda metadata across fresh
  instances.

## Experimental functionality cleanup

- The internal `__p4_oracle` debugging callable (scratch-only by design) was
  accidentally registered as a callable builtin. It is removed; Nift programs
  that reference it now report an undefined callable. No supported feature uses
  it.

## Compatibility

- Public filesystem APIs, fresh-observation semantics and project/root path
  authority are unchanged. The Linux optimisation carries portable fallbacks on
  other platforms.

## Deferred work

The following are **not** part of v4.12.0: generic prepared consumer lowering
(P5A), the `entries(path)` snapshot API (P5B2), and the native directory-FD
traversal backend. A historically published sorting benchmark does not
reproduce at its original magnitude on the current runtime; sorting performance
remains a separate future investigation.
