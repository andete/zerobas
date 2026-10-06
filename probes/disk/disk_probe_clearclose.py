#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CLEARCLOSE (gate: clearclose-acceptance): an ACCEPTED `CLEAR` closes every
open file, as on the CF-3300; a REJECTED one leaves them open.

Each case writes `ABCDEFGH` to a file open FOR OUTPUT, runs a CLEAR form, then
tries one more `PRINT#` under ON ERROR (`e <err>` when it raises), closes, and
reads the file back: `R< <lof> <first line> >#`. Fresh test720 copy per case,
on the CF-3300 and on ours.

  clear500   CLEAR 500           -> e 59, 11 B (the 10 written + Ctrl-Z)
  bare       CLEAR               -> the same
  himem      CLEAR 200,&HE000    -> the same
  rejneg     CLEAR -1            -> e 5, the file stays open: 16 B
  rejoom     CLEAR 30000         -> e 7, the same
  control    REM                 -> 16 B
  twochan    #1 and #2 open, #2 PARKED when CLEAR 1000 runs: #2's file must
             read back whole. The channels close under the OLD pool size --
             each channel's block is located from it -- so a close made after
             the new size is stored would read the parked channel from the
             wrong place.

Fixed 2026-10-06 (basic/clear.asm clr_h_fits / clr_files): ours kept every
channel open across CLEAR and the next PRINT# wrote to it.

Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading for a case.

    python3 -u probes/disk/disk_probe_clearclose.py
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

ONE = ['OPEN"CL.TXT"FOR OUTPUT AS#1', 'PRINT#1,"ABCDEFGH"']
AFTER = ["ON ERROR GOTO 900", 'PRINT#1,"XYZ"']
CASES = {
    "clear500": ("CL", ONE + ["CLEAR 500"] + AFTER),
    "bare":     ("CL", ONE + ["CLEAR"] + AFTER),
    "himem":    ("CL", ONE + ["CLEAR 200,&HE000"] + AFTER),
    "rejneg":   ("CL", ONE + ["CLEAR -1"] + AFTER),
    "rejoom":   ("CL", ONE + ["CLEAR 30000"] + AFTER),
    "control":  ("CL", ONE + ["REM"] + AFTER),
    "twochan":  ("C2", ["MAXFILES=2", 'OPEN"CL.TXT"FOR OUTPUT AS#1', 'OPEN"C2.TXT"FOR OUTPUT AS#2',
                        'PRINT#1,"ABCDEFGH"', 'PRINT#2,"QRSTUVWX"', 'PRINT#1,"IJKL"',
                        "CLEAR 1000", "ON ERROR GOTO 900", 'PRINT#2,"Z"']),
}


def prog(name, body):
    """The case body as lines 10.., then CLOSE and the read-back. The trap is
    armed at line 5 (a REJECTED CLEAR raises with it alive) and again after the
    CLEAR (an accepted one disarms it); it prints `e <err>` and resumes."""
    lines = ["NEW", "5 ON ERROR GOTO 900"]
    lines += [f"{10 + 10 * i} {s}" for i, s in enumerate(body)]
    lines += ["780 CLOSE",
              f'800 OPEN"{name}.TXT"FOR INPUT AS#1:LINE INPUT#1,A$:PRINT"R<";LOF(1);A$;">#":CLOSE:END',
              '900 PRINT"e";ERR;:RESUME NEXT', "RUN"]
    return lines


def main():
    out = {}
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        for case, (name, body) in CASES.items():
            dsk = probe_tmp.tmp(f"clearclose_{case}_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(machine, [("direct", prog(name, body))], batch=False,
                                      reset=("", "SCREEN 0"), boot=14.0, step=3.0,
                                      run_gap=30.0, diska=dsk)[0] or ""
            # quoted text is the echoed SOURCE, never output (the echo fence)
            scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
            m = re.findall(r"((?:e -?\d+ )*)R<([^>#]*)>#", scr)
            out[(tag, case)] = " ".join((m[-1][0] + "R<" + m[-1][1] + ">").split()) if m else None
            print(f"== {tag:8} {case:9} {out[(tag, case)]!r}", flush=True)
    print()
    bad = 0
    for case in CASES:
        a, b = out[("CF-3300", case)], out[("OURS", case)]
        if a is None:
            print(f"INSTRUMENT FAULT: the CF-3300 gave no reading for {case} -- no reference")
            return 2
        bad += a != b
        print(f"{'AGREE   ' if a == b else 'DIVERGES'} {case:9} CF-3300 {a!r}  ours {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: {len(CASES) - bad}/{len(CASES)} CLEAR forms close files as on the CF-3300")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
