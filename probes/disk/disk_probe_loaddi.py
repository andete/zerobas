# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOADDI (gate: loaddi-acceptance): the clock keeps running while a
tokenised LOAD reads the disk, as on the National CF-3300.

Measured 2026-10-10 (scratchpad/loadclock_probe.py -> loadclock_run.out, an
emulated-time stamp outside the guest): a 14 KB `LOAD"x",R` took 6.9 s here and
`TIME` advanced 3 jiffies, against 2.7 s and 83 jiffies on the CF-3300. disk.rom's
LOAD hook arrives through CALSLT, which returns DI, and the FDC driver keeps the
caller's state per sector, so the whole load ran masked: TIME stood still, and
the keyboard was not scanned. One `ei` on the load path (disk/kernel.asm,
hk_dpload) -- after it TIME ran for 43 % of the load, the CF-3300's 50 %
(scratchpad/loadclock_after.out).

The row: a ~2 KB program whose first line prints TIME is SAVEd, then
`TIME=0:LOAD"T.BAS",R`. `RUNS` when TIME advanced >= 8 jiffies during the load
(the reference reads ~50, the masked load ~2), else `STOPPED`; `ctl` is the
same read with no LOAD in between (a few jiffies on both: the program's own
start, which the threshold sits above).

Prints `ROW <name> CF=[...] ZB=[...] <SAME|DIVERGES>`; exit 0 all agree, 1 a
divergence, 2 the CF-3300 gave no reading.
Clean-room: typed BASIC in, the text screen out. CF-3300 vs zerobas DISK.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

SIDES = [("CF", "National_CF-3300", ("", "SCREEN 0", "CLOSE", "NEW", "CLS")),
         ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK", ("CLOSE", "NEW", "CLS"))]
PAD = ["%d REM %s" % (n, "X" * 200) for n in range(2, 12)]      # ~2 KB
PROG = ['1 PRINT"@K";TIME:END'] + PAD
THRESHOLD = 8


def reading(raw):
    m = re.findall(r"@K\s*(-?\d+)", (raw or "").replace("\n", ""))
    return int(m[-1]) if m else None


def verdict(j):
    return None if j is None else ("RUNS" if j >= THRESHOLD else "STOPPED")


def main():
    got = {}
    for side, machine, reset in SIDES:
        dsk = probe_tmp.tmp(f"loaddi_{side}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        cases = [("direct", ["NEW"] + PROG + ['SAVE"T.BAS"', "NEW", 'TIME=0:LOAD"T.BAS",R']),
                 ("direct", ["NEW"] + PROG[:1] + ["TIME=0:RUN"])]
        out = omsx_repl.run_cases(machine, cases, batch=False, reset=reset, boot=10.0,
                                  step=3.0, diska=dsk, capture="screen")
        got[side] = [reading(o) for o in out]
    bad, blind = [], []
    for i, name in enumerate(("load", "ctl")):
        cf, zb = got["CF"][i], got["ZB"][i]
        if name == "load":
            vcf, vzb = verdict(cf), verdict(zb)
        else:                                # the control: both well under the bar
            vcf = None if cf is None else ("UNDER" if cf < THRESHOLD else "OVER")
            vzb = None if zb is None else ("UNDER" if zb < THRESHOLD else "OVER")
        if vcf is None:
            v = "NO-REFERENCE"
            blind.append(name)
        elif vcf == vzb:
            v = "SAME"
        else:
            v = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} CF=[{vcf}] ZB=[{vzb}] {v}   (jiffies: CF {cf}, ZB {zb})",
              flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: the clock runs during LOAD "
          f"({2 - len(bad)}/2)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
