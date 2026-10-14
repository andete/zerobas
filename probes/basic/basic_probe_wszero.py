#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO (gate: wszero-acceptance): a program owns HIMEM..$F37F.

On a real diskless MSX1 a program that does `CLEAR n,&Hxxxx` owns the RAM from
HIMEM up to $F37F; BASIC keeps its state in the published work area ($F380 up)
and below HIMEM. Tape loaders do exactly that and then BLOAD up to $F000 / $F37F
(D-TAPELOAD's triage: 22 of ~43 failing titles). zerobas keeps ~2.5 KB of its own
state at $E98A-$F37F; a load over it crashes BASIC (Joost, 2026-10-14: shrink it
to zero, TIER 1 -- scratchpad/wszero_inventory.md).

Each row: OUR OWN synthetic tape (cas_encode) holding one binary that covers one
slice of the window -- a `ret` at its start, the rest $A5 -- loaded by a program
with `CLEAR 100,&HE000:BLOAD"CAS:",R`, which then runs PRINT, GOSUB, FOR and a
string concatenation. `ctl` loads below the window. The VG-8020 is the oracle.

KNOWN_DIVERGE pins the rows zerobas still fails: they must DIVERGE (a row that
starts agreeing is a pin that ROTTED -- remove it), every other row must be SAME.
As D-WSZERO's slices land the pins come off; slice 11 empties the set.

Each row prints `ROW <name> VG=[...] ZB=[...] <verdict>`. Exit 0 as pinned;
1 a divergence outside the pins or a rotted pin; 2 the VG-8020 gave no reading.
Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402

RANGES = {
    "ctl": (0xC000, 0xC17F),
    "w1": (0xE98A, 0xEAFF),     # graphics / DRAW scratch, the LIST window, holes
    "w2": (0xEB00, 0xEC7F),     # DEF FN frame, BLOAD's CURPTR..EXECPTR, run-loop, CSP
    "w3": (0xEC80, 0xEE7F),     # FOR copy, DATA, channel state, SAVSTK, the trap table
    "w4": (0xEE80, 0xF0FF),     # FIELD table, PRINT USING, tape search, float scratch
    "w5": (0xF100, 0xF37F),     # sub-ROM slots, the $0038 trampoline, math scratch
    # slice 1 (2026-10-14): the old homes of BLOAD's loop / flag cells and of the
    # tape search's names -- empty of anything a load needs since the move.
    "bl": (0xEC20, 0xEC25),
    "cas": (0xF000, 0xF01F),
    # slice 2 (2026-10-14): the trap block's old home -- the interrupt service read
    # it every frame, so a load over it armed garbage traps one frame later.
    "trap": (0xEDD1, 0xEE1F),
    # slice 3 (2026-10-14): PRGEND .. SL_CEIL's old home -- the run loop's control and
    # the control-pool anchors (CSP is loaded into SP at every line).
    "loop": (0xEC26, 0xEC59),
    # slice 4 (2026-10-14): FPERR's old home (read at every statement boundary) and
    # the sub-ROM slot cells' (read on every tenant call); then the whole window at
    # once, as a real tape loads it.
    "fperr": (0xF03C, 0xF0A9),
    "slot": (0xF100, 0xF109),
    "all": (0xE98A, 0xF37F),
}
# First run (2026-10-14, scratchpad/wszero_gate_first.out): w2 `Device I/O error`
# (BLOAD's loop cells), w3 nothing printed, w4 `Unprintable error in 10`, w5 stops
# after [A][G]. ctl and w1 agree.
# Slice 2 (2026-10-14) un-pinned w3: with the trap block out of $EDD1-$EE1F, a
# load over $EC80-$EE7F no longer stops BASIC (the FULL battery caught the rotted
# pin). w2 now prints nothing where it gave `Device I/O error` before slice 1.
# Slice 3 (2026-10-14) un-pinned w2: its fatal tenants were PRGEND..SL_CEIL
# ($EC26-$EC59, bisected: scratchpad/wszero_s3_bisect.out).
# Slice 4 (2026-10-14) un-pinned w4 and w5: their fatal tenants were FPERR and the
# sub-ROM slot cells (bisected: scratchpad/wszero_w45_bisect.out). No pins left.
KNOWN_DIVERGE = set()

PROGRAM = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 PRINT"[A]";:GOSUB 100:FOR I=1 TO 2:PRINT I;:NEXT:A$="X"+"Y":PRINT A$;"]"',
    "30 END",
    '100 PRINT"[G]";:RETURN',
    "RUN",
]


def tape(lo, hi):
    data = bytes([0xC9]) + bytes([0xA5]) * (hi - lo)
    return build_cas("W", lo, lo, data)


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    keep = [x.strip() for x in r if x.strip().startswith("[") or "rror" in x
            or "zerobas" in x or "Microsoft" in x]
    return " | ".join(keep)


def main():
    only = sys.argv[1:] or list(RANGES)
    tmp = tempfile.mkdtemp(prefix="wszero_")
    bad, rotted, blind = [], [], []
    for name in only:
        lo, hi = RANGES[name]
        path = os.path.join(tmp, f"{name}.cas")
        open(path, "wb").write(tape(lo, hi))
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = rows(omsx_repl.run_cases(m, [("direct", PROGRAM)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=40.0, cassette=path)[0])
        if not got["VG"]:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
            if name in KNOWN_DIVERGE:
                rotted.append(name)
                verdict = "SAME (PIN ROTTED)"
        else:
            verdict = "DIVERGES (pinned)" if name in KNOWN_DIVERGE else "DIVERGES"
            if name not in KNOWN_DIVERGE:
                bad.append(name)
        print(f"ROW {name} ${lo:04X}-${hi:04X} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}",
              flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    ok = not bad and not rotted
    print(f"\n{'PASS' if ok else 'FAIL'}: a load over the window, then BASIC "
          f"({len(only) - len(bad) - len(rotted)}/{len(only)} as pinned)"
          + (f"; unpinned divergence: {', '.join(bad)}" if bad else "")
          + (f"; ROTTED pins (now SAME, remove them): {', '.join(rotted)}" if rotted else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
