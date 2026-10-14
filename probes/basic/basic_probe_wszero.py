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
string concatenation. `ctl` loads below the window; `noclear` runs the same
program WITHOUT the `CLEAR`, as the loaders of D-TAPELOAD's RESET class do, so
the stack is wherever boot put it. The VG-8020 is the oracle.

KNOWN_DIVERGE pins the rows zerobas still fails: they must DIVERGE (a row that
starts agreeing is a pin that ROTTED -- remove it), every other row must be SAME.
As D-WSZERO's slices land the pins come off; slice 11 empties the set.

Each row prints `ROW <name> VG=[...] ZB=[...] <verdict>`. Exit 0 as pinned;
1 a divergence outside the pins or a rotted pin; 2 the VG-8020 gave no reading.
Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, re, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402

def sym(name):
    for ln in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        m = re.match(rf"^{name}\s+EQU\s+([0-9A-Fa-f]+)H", ln)
        if m:
            return int(m.group(1), 16)
    raise SystemExit(f"{name} is not in build/basic-reloc.sym -- build first")


# 🔁 SLICE 5 (2026-10-14) PACKED THE WORKSPACE against the top and raised the
# diskless ceiling (TXTMAX_NODISK $E98A -> the build's value), so the rows of
# slices 1-4 -- each the OLD HOME of a block that had just moved out -- stopped
# meaning anything: packed cells now sit in most of them. Their history, kept:
#   slice 0: ctl, w1-w5 (the window in five slices); first run w2 `Device I/O
#     error`, w3 nothing printed, w4 `Unprintable error in 10`, w5 stops after
#     [A][G] (scratchpad/wszero_gate_first.out).
#   slice 1: bl $EC20-$EC25, cas $F000-$F01F (BLOAD's loop cells, the tape
#     search's names); slice 2: trap $EDD1-$EE1F (the trap block, read by the
#     interrupt service every frame); slice 3: loop $EC26-$EC59 (PRGEND..SL_CEIL,
#     bisected: scratchpad/wszero_s3_bisect.out); slice 4: fperr $F03C-$F0A9 and
#     slot $F100-$F109 (scratchpad/wszero_w45_bisect.out), and `all` -- after
#     which no pin was left.
# The rows now come from the build: what is left of the window, in quarters and
# whole, and the RAM slice 5 handed back to programs.
NODISK = sym("TXTMAX_NODISK")
_q = (0xF380 - NODISK) // 4
RANGES = {
    "ctl": (0xC000, 0xC17F),
    # program RAM since slice 5: a load here must be harmless
    "freed": (0xE98A, NODISK - 1),
    "q1": (NODISK, NODISK + _q - 1),
    "q2": (NODISK + _q, NODISK + 2 * _q - 1),
    "q3": (NODISK + 2 * _q, NODISK + 3 * _q - 1),
    "q4": (NODISK + 3 * _q, 0xF37F),
    "all": (NODISK, 0xF37F),
    # D-TAPELOAD's RESET class (2026-10-14): a loader that does NOT `CLEAR` and
    # loads where the VG-8020 keeps free RAM below its stack ($F09E there). With
    # the ceiling at $E98A zerobas's SP was $E6A6, inside this block: the next
    # `ret` popped the loaded bytes.
    "noclear": (0xE000, 0xE7FF),
    # slice 6 (2026-10-14): the ceiling rose $EBCD -> $ECF8, so boot's stack moved
    # from ~$E8E9 to ~$EA14 -- this span held it before and must be free now.
    "noclear2": (0xE800, 0xE97F),
}
# Rows that run the program without `CLEAR` (the stack stays where boot put it).
NOCLEAR = {"noclear", "noclear2"}
KNOWN_DIVERGE = set()

PROGRAM_NOCLEAR = [
    "NEW",
    '10 BLOAD"CAS:",R',
    '20 PRINT"[A]";:GOSUB 100:FOR I=1 TO 2:PRINT I;:NEXT:A$="X"+"Y":PRINT A$;"]"',
    "30 END",
    '100 PRINT"[G]";:RETURN',
    "RUN",
]
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
            prog = PROGRAM_NOCLEAR if name in NOCLEAR else PROGRAM
            got[side] = rows(omsx_repl.run_cases(m, [("direct", prog)], batch=False,
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
