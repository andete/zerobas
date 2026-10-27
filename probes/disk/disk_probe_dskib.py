# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DSKIB (gate: dskib-acceptance): the single drive's A:/B: swap prompt.

One physical drive, two logical ones (Joost 2026-10-09: "yeah, we need to have the
prompt mechanism"). On the CF-3300, addressing the other logical drive prints, from a
fresh line, `Insert diskette for drive B:` / `and strike a key when ready`, waits for
one key and carries on with the same disk; the same drive again is silent; a name or
drive argument without B: is A: (scratchpad/dskib_run.out, _run2, _run3). Each case
boots a fresh copy of disk/test720.dsk; an empty typed line is the Enter that strikes
the key. NOT covered: COPY "A:X" TO "B:Y", which prompts per buffer there and once
here (filed in D-DSKIB).

Each row prints `ROW <name> CF=[...] ZB=[...] <verdict>`.
Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading.
Clean-room: typed BASIC in, the text screen out.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

CASES = {
    "dskf2":     ['PRINT DSKF(2)', ''],
    "dski2":     ['A$=DSKI$(2,0):PRINT LEN(A$)', ''],
    "dsko2":     ['DSKO$ 2,700', ''],
    "filesb":    ['FILES"B:"', ''],
    "b_then_a":  ['FILES"B:"', '', 'FILES"A:"', ''],
    "b_then_b":  ['FILES"B:"', '', 'FILES"B:"', ''],
    "b_then_none": ['FILES"B:"', '', 'FILES', ''],
    "b_then_dskf0": ['FILES"B:"', '', 'PRINT DSKF(0)', ''],
    "saveb":     ['NEW', '10 REM Q', 'SAVE"B:Q"', '', 'FILES"A:"', ''],
    "loadb":     ['LOAD"B:PROG.BAS"', '', 'LIST', ''],
    "midline":   ['PRINT "QQ";:PRINT DSKF(2)', ''],
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(CASES)
    bad, blind = [], []
    for name in only:
        got = {}
        for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"dskib_{name}_{side}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            got[side] = rows(omsx_repl.run_cases(m, [("direct", CASES[name])], batch=False,
                                                 diska=dsk, boot=14.0,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=4.0,
                                                 run_gap=8.0)[0])
        if got["CF"] is None:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["CF"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} CF=[{got['CF']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: the drive-B swap prompt ({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
