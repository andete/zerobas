# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FCBSHAPE FCB #0 (gate: fcb0-acceptance): channel #0 has an FCB at every
MAXFILES, and the channel blocks sit in the reference's order -- the FILTAB
pointer table, then #0, #1 .. #MAXFILES -- as on the VG-8020. Measured
2026-10-10 (scratchpad/fcb0_run.out): VARPTR(#0) is an address on both
references at MAXFILES 0..2, blocks are 265 apart, and the top block stays put
as MAXFILES grows (so VARPTR(#1) moves 265 a step); zerobas answered ERR 59 for
#0 and moved #1 by 267.

The machines' BASES differ (the address space is laid out differently), so
every row prints a RELATION, never an address:
  v0      MAXFILES=0: VARPTR(#0) answers (no error)
  stride  MAXFILES=2: VARPTR(#1)-VARPTR(#0), VARPTR(#2)-VARPTR(#1)
  geom    VARPTR(#1) at MAXFILES=1, then at MAXFILES=2: the delta
  fre     FRE(0) at MAXFILES=0, then at MAXFILES=1: the delta

Prints `ROW <name> VG=[...] ZB=[...] <SAME|DIVERGES>`; exit 0 all agree, 1 a
divergence, 2 the VG-8020 gave no reading.
Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

# MAXFILES clears the variables on BOTH references (measured: a value kept in a
# variable across it read back 0), so the two-step rows PRINT both readings and
# the DIFFERENCE is taken here, between the brackets.
CASES = {
    "v0": ["MAXFILES=0", 'A=VARPTR(#0):PRINT "[OK]"'],
    "stride": ["MAXFILES=2", 'PRINT "[";VARPTR(#1)-VARPTR(#0);VARPTR(#2)-VARPTR(#1);"]"'],
    "geom": ["MAXFILES=1", 'PRINT "[";VARPTR(#1);"]"', "MAXFILES=2", 'PRINT "[";VARPTR(#1);"]"'],
    "fre": ["MAXFILES=0", 'PRINT "[";FRE(0);"]"', "MAXFILES=1", 'PRINT "[";FRE(0);"]"'],
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    out = [x.strip() for x in r if x.strip().startswith("[") or "error" in x]
    if not out:
        return "<NOTHING PRINTED>"
    nums = [x.strip("[] ").split() for x in out if x.startswith("[") and x != "[OK]"]
    if len(nums) == 2 and all(len(n) == 1 for n in nums):   # a two-step row
        return f"delta {int(nums[1][0]) - int(nums[0][0])}"
    return " | ".join(out)


def main():
    only = sys.argv[1:] or list(CASES)
    bad, blind = [], []
    for name in only:
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = rows(omsx_repl.run_cases(m, [("direct", ["NEW"] + CASES[name])],
                                                 batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"),
                                                 step=3.0)[0])
        if got["VG"] is None:
            verdict = "NO-REFERENCE"
            blind.append(name)
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: FCB #0 and the channel geometry "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
