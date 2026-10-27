#!/usr/bin/env python3
"""D-DSKIB step 1: the scope of the single-drive A/B swap, measured on the CF-3300.

One physical drive; the reference prompts `Insert diskette for drive B: and strike a
key when ready` when the other logical drive is addressed (Joost 2026-10-09: build the
prompt mechanism). Each case boots a fresh copy of disk/test720.dsk and types its
lines; an empty line is the Enter that strikes the key. The whole screen after the
first typed line is printed. Black box: keys in, screen out.

    python3 -u scratchpad/dskib_probe.py [CASE ...]
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "probes", "lib")]
import omsx_repl  # noqa: E402
import probe_tmp  # noqa: E402

CASES = {
    "dskf2":  ['PRINT DSKF(2)', ''],
    "dski2":  ['A$=DSKI$(2,0):PRINT LEN(A$)', ''],
    "filesb": ['FILES"B:"', ''],
    "b_then_a": ['FILES"B:"', '', 'FILES"A:"', ''],
    "b_then_b": ['FILES"B:"', '', 'FILES"B:"', ''],
    "saveb":  ['NEW', '10 REM Q', 'SAVE"B:Q"', '', 'FILES"A:"', ''],
}


def rows(scr, first):
    if scr is None:
        return "<NO READING>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    k = next((i for i, x in enumerate(r) if x.strip() == first[:40]), 0)
    return " | ".join(x.strip() for x in r[k:] if x.strip())


def main():
    for name in sys.argv[1:] or list(CASES):
        for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"dskib_{name}_{side}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            scr = omsx_repl.run_cases(m, [("direct", CASES[name])], batch=False, diska=dsk,
                                      boot=14.0, reset=("", "SCREEN 0:WIDTH 40"), step=4.0,
                                      run_gap=8.0)[0]
            print(f"{side} {name:9s} {rows(scr, CASES[name][0])}", flush=True)


if __name__ == "__main__":
    main()
