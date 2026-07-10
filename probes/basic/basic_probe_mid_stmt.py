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

The RANGE-ERROR case (`n > LEN(A$)`) is a documented **divergence**, asserted
per-machine rather than as equality: the reference raises `Illegal function call`,
zerobas raises `syntax error` (it has no "illegal function call" in its vocabulary,
spec D-3) -- but BOTH abort the line (the trailing PRINT never runs, A$ unchanged),
so the behaviour matches; only the wording differs. Asserting each machine's own
error string proves "both error" while documenting the wording gap, the same
convention the string-compare/functions slices used for their divergences.

Clean-room: this only *observes* black-box behaviour (type a line, read the screen).
The reference ROM is never read as code. See CONTRIBUTING.md.

    python3 probes/basic/basic_probe_mid_stmt.py
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OMSX_RUN = os.path.join(REPO, "probes", "lib", "omsx_run.py")

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


def run_prog(machine, lines, timeout=140):
    """Type each SHORT direct-mode line (line then a separately-timed Enter) and
    capture the SCREEN 0 name table as one raw row-major string of length NLEN
    (None on failure). Short lines are deliberate: a long single line lets the
    openMSX `type` Enter land mid-typing (the real-speed keyboard scan can't keep
    up), which silently drops the line; splitting setup/op/print into short lines
    (A$ persists across direct-mode lines) keeps each Enter after its line."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="midstmt_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine]
    t = 6.0
    for ln in lines:
        cmd += ["--type", ln, "--type-delay", f"{t}"]
        t += 2.0
        cmd += ["--type", "\r", "--type-delay", f"{t}"]
        t += 2.0
    cmd += ["--time", f"{t + 2.0}",
            "--mem", f"VRAM:0x0000:{NLEN}", "--out", out_path, "--timeout", str(timeout)]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    m = re.search(rf"mem\.VRAM:0x0000:{NLEN}=([0-9a-f]+)", cap)
    if not m:
        return None
    data = bytes.fromhex(m.group(1))
    return "".join(chr(b) if 32 <= b < 127 else " " for b in data)


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
    persists across the lines; short lines keep the Enter after each line."""
    a = c.a.decode("ascii")
    b = c.b.decode("ascii")
    return [f'A$="{a}"', f'MID$({c.args})="{b}"', 'PRINT"[";A$;"]"']


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help="reference machine (built-in BASIC oracle)")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine (string engine is repack-only)")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true", help="skip the zerobas side")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.only or args.only in c.label]
    want_err = not args.only or args.only in "range-err"
    if not cases and not want_err:
        print(f"no cases match --only {args.only!r}")
        return 1

    ok = True

    # --- overwrite cases: reference-lock then zerobas==reference ---
    if cases:
        print(f"--- reference oracle lock ({args.machine}, §2 contract) ---")
        ref_cap = {}
        for c in cases:
            want = mid_assign(c.a, c.n, c.b, c.m).decode("ascii")
            got = result(run_prog(args.machine, prog_for(c), timeout=180))
            ref_cap[c.label] = got
            good = got == want
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.label:9} got={got!r} want={want!r}")

        if not args.ref_only:
            print(f"\n--- zerobas == reference ({args.zb_machine}) ---")
            for c in cases:
                zb = result(run_prog(args.zb_machine, prog_for(c), timeout=140))
                ref = ref_cap.get(c.label)
                good = ref is not None and zb == ref
                ok = ok and good
                print(f"{'PASS' if good else 'FAIL':5} {c.label:9} zb={zb!r} ref={ref!r}")

    # --- range-error divergence: per-machine error string (D-3) ---
    if want_err:
        print("\n--- range error n>LEN(A$) [divergence: reference 'Illegal function "
              "call' vs zerobas 'syntax error'; both abort the line] ---")
        # short lines: seed A$, the out-of-range op (errors), then a would-be PRINT.
        errprog = ['A$="HI"', 'MID$(A$,5,1)="X"', 'PRINT"[";A$;"]"']
        ref_raw = run_prog(args.machine, errprog, timeout=180)
        ref_err = ref_raw is not None and "illegal function call" in ref_raw.lower()
        # the PRINT line still runs (direct mode), but A$ is unchanged -> [HI], never
        # [XI]; the key assertion is the error string appears + A$ was not mutated.
        ref_noresult = result(ref_raw) != "XI"
        good = ref_err and ref_noresult
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} range-err ref: 'Illegal function call'"
              f"={ref_err}, A$ unchanged={ref_noresult}")
        if not args.ref_only:
            zb_raw = run_prog(args.zb_machine, errprog, timeout=140)
            zb_err = zb_raw is not None and "syntax error" in zb_raw.lower()
            zb_noresult = result(zb_raw) != "XI"
            good = zb_err and zb_noresult
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} range-err zb:  'syntax error'"
                  f"={zb_err}, A$ unchanged={zb_noresult}")

    print("\nALL PASS -- reference matches §2, zerobas matches reference "
          "(range error: both abort, documented wording divergence)" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
