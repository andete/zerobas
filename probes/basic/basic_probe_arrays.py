#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Differential arrays probe (docs/spec-basic-arrays.md §9.7) — prove zerobas's
numeric-array slice behaves byte-for-byte like the stock VG-8020 across the §4.1
characterization matrix.

Reference: stock Philips_VG_8020 (real MSX-BASIC 1.0). zerobas: the repack build
(C-BIOS_MSX1_EU_REPACK_DISK — arrays are repack-only). Drives both via the
KEYBUF-injection REPL harness (omsx_repl) and compares the printed value span OR
the error-message tail for each case. Observed outputs only, no ROM disassembly.

The VG-8020 reference machine is NOT in the default (homebrew) openMSX machine
path; point the harness at a build that has it, e.g.:
  OPENMSX=/Users/joost/projects/openmsx/derived/aarch64-darwin-opt/bin/openmsx \\
    python3 probes/basic/basic_probe_arrays.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl as R  # noqa: E402

REF = "Philips_VG_8020"
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
OMSX = os.environ.get("OPENMSX")  # None -> find_omsx default (must resolve REF)

# Each case: (label, mode, lines, kind). kind "value" compares the [..] span;
# "err" compares the error-message tail; "either" compares whichever the
# reference produced (some cases abort mid-line before the PRINT).
CASES = [
    ("autodim.bound10.ok",  "direct", ['A(10)=9:PRINT"[";A(10);"]"'],            "value"),
    ("autodim.11.oor",      "direct", ['A(11)=9:PRINT"[";A(11);"]"'],            "err"),
    ("autodim.touch.max",   "direct", ['A(5)=1:PRINT"[";A(10);"]"'],             "value"),
    ("dim.inclusive",       "direct", ['DIM B(5):B(5)=3:PRINT"[";B(5);"]"'],     "value"),
    ("dim.over.oor",        "direct", ['DIM B(5):B(6)=3:PRINT"[";B(6);"]"'],     "err"),
    ("base0",               "direct", ['DIM B(2):B(0)=7:PRINT"[";B(0);"]"'],     "value"),
    ("autoinit0",           "direct", ['DIM B(3):PRINT"[";B(2);"]"'],            "value"),
    ("redim",               "direct", ['DIM B(3):DIM B(3):PRINT"[ok]"'],         "err"),
    ("multidim.val",        "stored", ['DIM C(2,3):C(1,2)=5', 'PRINT"[";C(1,2);"]"'], "value"),
    ("multidim.init0",      "direct", ['DIM C(2,3):PRINT"[";C(2,3);"]"'],        "value"),
    ("multidim.wrongn.oor", "direct", ['DIM C(2,3):PRINT"[";C(1);"]"'],          "err"),
    ("typeindep",           "stored", ['A(1)=11:A%(1)=22', 'PRINT"[";A(1);",";A%(1);"]"'], "value"),
    ("neg.illegal",         "direct", ['DIM B(5):PRINT"[";B(-1);"]"'],           "err"),
    ("float.elem",          "direct", ['DIM D(3):D(1)=1.5:PRINT"[";D(1);"]"'],   "value"),
    ("multi.array.per.dim", "stored", ['DIM P(2),Q(3):P(2)=7:Q(3)=8', 'PRINT"[";P(2);Q(3);"]"'], "value"),
    ("ordering.2x2",        "stored",
        ['DIM C(1,1):C(0,0)=1:C(1,0)=2:C(0,1)=3:C(1,1)=4',
         'PRINT"[";C(0,0);C(1,0);C(0,1);C(1,1);"]"'], "value"),
    # --- variable-subscript regression class (slice-1 fix, 2026-07-15) -----
    # Root causes guarded forever: (1) fac_to_int_strict clobbers HL on the
    # float path only, so any VARIABLE (default double) subscript/bound
    # trashed ary_parse_subs's cursor -> phantom "syntax error" while literal
    # (int) subscripts sailed through; (2) the shared ARY_NIDX/ARY_IDX param
    # block was written incrementally per subscript, so a NESTED array rvalue
    # X(X(0)) re-entrantly clobbered the outer parse's partial count/values.
    ("var.subscript",       "stored", ['DIM X(3):I=1:X(I)=5', 'PRINT"[";X(I);"]"'], "value"),
    ("var.dim.bound",       "stored", ['N=4:DIM X(N):X(4)=7', 'PRINT"[";X(4);"]"'], "value"),
    ("nested.subscript",    "stored", ['DIM X(3):X(0)=2:X(2)=9', 'PRINT"[";X(X(0));"]"'], "value"),
    ("for.loop.fill",       "stored", ['DIM X(3):FOR I=0 TO 3:X(I)=I:NEXT', 'PRINT"[";X(3);"]"'], "value"),
    # DIM-then-use at MAXDIM guards the aeng_dim key-write path (a clobbered
    # ARY_KEY made every DIM'd descriptor invisible; small bounds silently
    # fell through to auto-dim, 4-dim exposed it as a phantom auto-dim OOM).
    ("dim.then.use.4d",     "stored", ['DIM C(1,1,1,1):C(1,1,1,1)=6', 'PRINT"[";C(1,1,1,1);"]"'], "value"),
    # error-surface casing: DIM OOM is reference-verbatim "Out of memory";
    # DIM with a negative bound is "Illegal function call" (tenant-side check)
    ("dim.oom.casing",      "direct", ['DIM X(5000):PRINT"[x]"'],  "err"),
    ("dim.neg.illegal",     "direct", ['DIM E(-1):PRINT"[x]"'],    "err"),
]


def _last_line(mode, lines):
    """The cmdline whose echo anchors the tail scrape."""
    return lines[-1] if mode == "direct" else lines[-1]


def compare(i, ref, zb):
    label, mode, lines, kind = CASES[i]
    cmd = _last_line(mode, lines)
    if kind == "value":
        rv = R.result_span(ref) if mode == "stored" else R.result_span_after_echo(ref, cmd)
        zv = R.result_span(zb) if mode == "stored" else R.result_span_after_echo(zb, cmd)
        return rv is not None and rv == zv
    if kind == "err":
        rt = R.screen_tail(ref, cmd)
        zt = R.screen_tail(zb, cmd)
        return bool(rt) and rt == zt
    # "either": compare value if ref printed one, else the tail
    rv = R.result_span_after_echo(ref, cmd)
    if rv is not None:
        return rv == R.result_span_after_echo(zb, cmd)
    return bool(R.screen_tail(ref, cmd)) and R.screen_tail(ref, cmd) == R.screen_tail(zb, cmd)


def main():
    specs = [(m, l) for _, m, l, _ in CASES]
    verdicts, refs, zbs = R.run_differential(
        REF, ZB, specs, compare, reset=("NEW", "CLS"), omsx=OMSX)
    npass = sum(verdicts)
    for i, (label, mode, lines, kind) in enumerate(CASES):
        cmd = _last_line(mode, lines)
        rv = (R.result_span(refs[i]) if mode == "stored"
              else R.result_span_after_echo(refs[i], cmd))
        zv = (R.result_span(zbs[i]) if mode == "stored"
              else R.result_span_after_echo(zbs[i], cmd))
        rt, zt = R.screen_tail(refs[i], cmd), R.screen_tail(zbs[i], cmd)
        tag = "PASS" if verdicts[i] else "FAIL"
        detail = f"ref={rv!r}/{rt!r}  zb={zv!r}/{zt!r}" if not verdicts[i] else ""
        print(f"  {tag}  {label:<22} {detail}")
    print(f"=== arrays: {npass}/{len(CASES)} {'ALL PASS' if npass == len(CASES) else 'SOME FAILED'} ===")
    return 0 if npass == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
