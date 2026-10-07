#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Vleermuis side experiment (Joost 2026-10-07: "a tape for it ... a side
experiment"). NOT a gate. Vleermuis (egonw/vleermuis, MIT -- LICENSE beside the
.BAS) on an ASCII tape, loaded with LOAD"CAS:" on the diskless VG-8020 and on
ours, then compared:

  load   the TOKENISED program in RAM, TXTTAB ($F676) .. VARTAB ($F6C2): its
         length, a byte sum and a position-weighted sum (double precision, so
         exact) -- timing-free: both machines crunched the same ASCII text
  run    the as-is listing RUN: the retyped listing has `ON KEY GOSUC` in 1580,
         so a faithful machine is predicted to stop with `Syntax error in 1580`
         right after drawing the instruction screen

    python3 -u scratchpad/vleermuis/vleermuis_exp.py [load|run ...] [--tape=fixed]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REF, OURS = "Philips_VG_8020", os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
SUM = ('T=PEEK(&HF676)+256*PEEK(&HF677):V=PEEK(&HF6C2)+256*PEEK(&HF6C3):S#=0:W#=0:'
       'FOR I=T TO V-1:P=PEEK(I):S#=S#+P:W#=W#+P*(I-T+1):NEXT:PRINT"[S";V-T;S#;W#;"]"')
PTRS = 'T=PEEK(&HF676)+256*PEEK(&HF677):V=PEEK(&HF6C2)+256*PEEK(&HF6C3):PRINT"[T";T;V;"]"'
CASES = {
    "load": ['LOAD "CAS:"', "@WAIT240", PTRS, "@WAIT5", SUM, "@WAIT900"],
    "run": ['LOAD "CAS:"', "@WAIT240", "RUN", "@WAIT300"],
}


def tape(kind):
    src = os.path.join(HERE, "VLEERMUIS.BAS" if kind == "asis" else "VLEERMUIS-FIXED.BAS")
    out = os.path.join(HERE, f"vleermuis-{kind}.cas")
    open(out, "wb").write(cas_encode.build_cas_ascii("VLEER", open(src).read()))
    return out


def reading(machine, case, cas):
    raw = omsx_repl.run_cases(machine, [("direct", ["CLS"] + CASES[case])], batch=False,
                              reset=(), cassette=cas)[0] or ""
    return raw


def main():
    kind = "fixed" if "--tape=fixed" in sys.argv else "asis"
    cas = tape(kind)
    only = [a for a in sys.argv[1:] if not a.startswith("--")] or list(CASES)
    for case in only:
        for m in (REF, OURS):
            raw = reading(m, case, cas)
            scr = re.sub(r"\s+", " ", raw)
            hit = re.findall(r"\[S[^\]]*\]", scr) if case == "load" else \
                re.findall(r"[A-Z][a-z][a-z ]* in \d+", scr)   # any `<message> in <line>`:
            # "Out of string space in 1070" has no "error" in it, and the first
            # regex here missed it -- the run looked like a silent hang
            print(f"{case:5} {m[:22]:22} {hit[-3:] if hit else '<none>'}", flush=True)
            open(os.path.join(HERE, f"exp_{kind}_{case}_{m[:8]}.screen"), "w").write(raw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
