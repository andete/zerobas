#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Oracle + differential probe -- MID$ statement (MID$ slice S3).

MID$(A$,n[,m])=B$, per docs/spec-basic-mid-statement.md. The assignment form that
overwrites a substring of A$ in place (the MID$ function is basic_probe_str_fn.py's
sibling in the string engine). Two halves, modelled on basic_probe_str_fn.py:

1. REFERENCE ORACLE (black-box, no disassembly). Runs each overwrite on the real
   Philips VG-8020's built-in MSX-BASIC (no cartridge) and asserts its own screen
   output matches the §2 contract value, DERIVED in Python (never assumed).

2. ZEROBAS DIFFERENTIAL. Runs the IDENTICAL line on the repack machine
   (C-BIOS_MSX1_EU_REPACK_DISK -- the string engine is repack-only) and asserts
   zerobas's result equals the reference's.

Each overwrite is `A$="...":MID$(...)=B$:PRINT"[";A$;"]"`, so the mutated A$ prints
bracket-wrapped; the result is the LAST `[..]` pair (the echoed source has its own
`[`/`]`, printed earlier -- same disambiguation as basic_probe_str_fn.extract).

The RANGE-ERROR case (`n > LEN(A$)`) used to be a documented **divergence** --
the reference raising `Illegal function call` and zerobas `syntax error`, on the
premise that zerobas had no "Illegal function call" in its vocabulary (spec D-3).
That premise had been false for a long time, and it was the reason this path
funnelled seven distinct reference errors into one wrong one. D-MISS-2
(docs/spec-basic-str-domain.md §3) closed it; the row is now asserted as
AGREEMENT, and it earns its place by proving A$ is not mutated by the rejected
assignment. The rest of the domain (n<1, n>255, m<0, m>255, past int16 ->
`Overflow`) is gated by `make str-domain-acceptance`.

Clean-room: this only *observes* black-box behaviour (type a line, read the screen).
The reference ROM is never read as code. See CONTRIBUTING.md.

    python3 probes/basic/basic_probe_mid_stmt.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402  typing-free KEYBUF-injection REPL driver

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
COLS, ROWS = 40, 24
NLEN = COLS * ROWS


# --- §2 contract, computed in Python (never assumed) -----------------------

def mid_assign(a: bytes, n: int, b: bytes, m: int | None) -> bytes:
    """MID$(A$,n[,m])=B$: overwrite in place, LEN(A$) invariant.
    k = min(m if given else Lb, Lb, La-n+1); bytes outside [n,n+k) untouched."""
    la, lb = len(a), len(b)
    avail = la - (n - 1)
    k = min(lb if m is None else m, lb, avail)
    if k <= 0:
        return a
    return a[:n - 1] + b[:k] + a[n - 1 + k:]


def result(raw):
    """The LAST `[..]` bracket content (the mutated A$, printed after the echo)."""
    if raw is None:
        return None
    ms = re.findall(r"\[([^\[\]]*)\]", raw)
    return ms[-1] if ms else None


# (label, A$, mid-args-string, n, b, m) -- the op is MID$(A$,<args>)=<"b">
Case = namedtuple("Case", "label a args n b m")

CASES = [
    Case("basic",   b"HELLO", "A$,2,3", 2, b"XYZ",  3),
    Case("no-m",    b"HELLO", "A$,3",   3, b"XY",   None),
    Case("at-1",    b"HELLO", "A$,1",   1, b"XY",   None),
    Case("at-end",  b"HELLO", "A$,5,1", 5, b"Z",    1),
    Case("b-long",  b"HELLO", "A$,4",   4, b"WXYZ", None),
    Case("m-over",  b"HELLO", "A$,4,10",4, b"WXYZ", 10),
    Case("m-short", b"HELLO", "A$,1,2", 1, b"ABCD", 2),
    Case("b-empty", b"HELLO", "A$,2",   2, b"",     None),
    Case("m-zero",  b"HELLO", "A$,2,0", 2, b"XY",   0),
]


def prog_for(c: Case) -> list[str]:
    """Three short direct-mode lines: seed A$, do the overwrite, print it. A$
    persists across the lines within a case; a ("NEW","CLS") reset between cases
    clears it (and the screen) so a batched matrix shares one boot."""
    a = c.a.decode("ascii")
    b = c.b.decode("ascii")
    return [f'A$="{a}"', f'MID$({c.args})="{b}"', 'PRINT"[";A$;"]"']


# The range-error program (n>LEN(A$)): seed A$, the out-of-range op (errors),
# then a would-be PRINT. Its own spec, appended after the overwrite cases.
ERRPROG = ['A$="HI"', 'MID$(A$,5,1)="X"', 'PRINT"[";A$;"]"']


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help="reference machine (built-in BASIC oracle)")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine (string engine is repack-only)")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true", help="skip the zerobas side")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot instead of the default "
                         "single-boot batch (to rule out inter-case leakage)")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.only or args.only in c.label]
    want_err = not args.only or args.only in "range-err"
    if not cases and not want_err:
        print(f"no cases match --only {args.only!r}")
        return 1

    ok = True
    batch = not args.boot_per_case

    # Every case is a direct-mode 3-line program (seed A$, op, PRINT); the whole
    # matrix shares ONE boot per side with a ("NEW","CLS") reset between cases
    # (NEW clears the persisted A$, CLS the screen). The range-error program is
    # the final spec.
    specs = [("direct", prog_for(c)) for c in cases]
    if want_err:
        specs.append(("direct", ERRPROG))
    ref_raws = omsx_repl.run_cases(args.machine, specs, batch=batch, reset=("NEW", "CLS"))
    zb_raws = (omsx_repl.run_cases(args.zb_machine, specs, batch=batch, reset=("NEW", "CLS"))
               if not args.ref_only else [None] * len(specs))

    # --- overwrite cases: reference-lock then zerobas==reference ---
    if cases:
        print(f"--- reference oracle lock ({args.machine}, §2 contract) ---")
        ref_cap = {}
        for c, ref_raw in zip(cases, ref_raws):
            want = mid_assign(c.a, c.n, c.b, c.m).decode("ascii")
            got = result(ref_raw)
            ref_cap[c.label] = got
            good = got == want
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.label:9} got={got!r} want={want!r}")

        if not args.ref_only:
            print(f"\n--- zerobas == reference ({args.zb_machine}) ---")
            for c, zb_raw in zip(cases, zb_raws):
                zb = result(zb_raw)
                ref = ref_cap.get(c.label)
                good = ref is not None and zb == ref
                ok = ok and good
                print(f"{'PASS' if good else 'FAIL':5} {c.label:9} zb={zb!r} ref={ref!r}")

    # --- range-error divergence: per-machine error string (D-3) ---
    if want_err:
        # ⚠️ This block used to assert the DIVERGENCE -- reference 'Illegal
        # function call' vs zerobas 'syntax error' -- as the expected result.
        # D-MISS-2 (docs/spec-basic-str-domain.md §3) closed it: `ems_range` now
        # raises ERR 5 like the reference, so the assertion is AGREEMENT. The
        # gate went red the moment the divergence was fixed, which is a recorded
        # divergence doing its job; see the same event in basic_probe_missing.py.
        # The wider domain surface (n<1, n>255, m<0, m>255, past int16) is gated
        # by `make str-domain-acceptance`; this row stays because it is the one
        # that also proves A$ is NOT mutated by the rejected assignment.
        print("\n--- range error n>LEN(A$) [reference and zerobas both "
              "'Illegal function call'; A$ must be unmutated] ---")
        ref_raw = ref_raws[len(cases)]
        ref_err = ref_raw is not None and "illegal function call" in ref_raw.lower()
        # the PRINT line still runs (direct mode), but A$ is unchanged -> [HI], never
        # [XI]; the key assertion is the error string appears + A$ was not mutated.
        ref_noresult = result(ref_raw) != "XI"
        good = ref_err and ref_noresult
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} range-err ref: 'Illegal function call'"
              f"={ref_err}, A$ unchanged={ref_noresult}")
        if not args.ref_only:
            zb_raw = zb_raws[len(cases)]
            zb_err = zb_raw is not None and "illegal function call" in zb_raw.lower()
            zb_noresult = result(zb_raw) != "XI"
            good = zb_err and zb_noresult
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} range-err zb:  'Illegal function call'"
                  f"={zb_err}, A$ unchanged={zb_noresult}")

    print("\nALL PASS -- reference matches §2, zerobas matches reference "
          "(range error included: same message, both abort, A$ unmutated)" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
