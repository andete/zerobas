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
# slice 7 (2026-10-14): an ERROR after the load, over the whole window. The run
# loop anchors SP in SAVSTK once per RUN and the error trap reloads it -- a load
# over that cell and then any error jumped to a garbage stack (Formula 1
# Simulator's SP = $00F3). `abort` has no handler, `onerr` resumes from one.
ERRROWS = {"abort", "onerr"}
RANGES["abort"] = RANGES["all"]
RANGES["onerr"] = RANGES["all"]
# slice 7 (2026-10-14): the statements a BASIC loader typically runs AFTER the
# load, each a different tenant -- DEF FN, the string GC, READ / DATA, PRINT
# USING, graphics, PLAY, DIM -- over the whole window. A cell that only one of
# them reads is invisible to the core program.
RICH = {"rich", "rich2"}
RANGES["rich"] = RANGES["all"]
RANGES["rich2"] = RANGES["all"]
# D-WSZERO S8 (2026-10-15): state SET BEFORE the load and READ AFTER it --
# the persistent cells (DRAW's scale / angle, the disk-ROM-present flag that
# decides a `d:` name: 56 with no disk ROM, the disk arm with one -- FILES does
# not read it, knife K-WS13's first cut). Every other row sets its state after
# the load, so a persistent cell that a load garbles was invisible to them.
# ⏱ The scan is 17x17: a 41x41 one ran past the 40 s run gap on zerobas after a
# full-window load (the VG-8020 finished inside it) and read as an empty screen.
RANGES["persist"] = RANGES["all"]
# D-WSZERO S10 (2026-10-15): the persistent cells a loader's NEXT statements
# read, each set BEFORE the load (or by a load inside the statement that reads
# it) -- an open channel (FCH_MODES), INPUT's cursor (CSR_*), the direct-mode
# flag mid-line (DIRECTF), a RESUME after a load in the handler (ERRRESUME), CONT
# after a direct load (CONTVALID) and the `Ok` after RUN (PRMWANT -- only a $00
# fill can see it: $A5 is nonzero, which is what the cell wants).
for _r in ("chan", "input", "midline", "resume", "contdir", "prm"):
    RANGES[_r] = RANGES["all"]
FILL = {"prm": 0x00}
KNOWN_DIVERGE = set()

PROGRAM_NOCLEAR = [
    "NEW",
    '10 BLOAD"CAS:",R',
    '20 PRINT"[A]";:GOSUB 100:FOR I=1 TO 2:PRINT I;:NEXT:A$="X"+"Y":PRINT A$;"]"',
    "30 END",
    '100 PRINT"[G]";:RETURN',
    "RUN",
]
PROGRAM_RICH = [
    "NEW",
    '10 CLEAR 300,&HE000:DEFFNF(X)=X*2+1:READ P:BLOAD"CAS:",R',
    '20 SCREEN 2:CIRCLE(128,96),60,15:PAINT(128,96),4,15:C=POINT(128,96):SCREEN 0',
    '30 F=FNF(3):READ Q:FOR K=1 TO 40:B$=B$+"Z":NEXT:DIM Z(50):Z(50)=7:PLAY"T255L64C"',
    '40 PRINT"[";F;P;Q;LEN(B$);Z(50);C;:PRINT USING"##.##";3.14159;:PRINT"]"',
    "90 DATA 5,6",
    "RUN",
]
PROGRAM_RICH2 = [
    "NEW",
    '10 CLEAR 300,&HE000:A$="HELLO":DIM W(9):BLOAD"CAS:",R',
    '20 ON INTERVAL=2 GOSUB 100:INTERVAL ON:FOR K=1 TO 300:NEXT:INTERVAL OFF',
    '30 MID$(A$,2,2)="EY":I=INSTR(A$,"LO"):B$=STRING$(3,"Q"):SWAP A$,B$:ERASE W',
    '40 R=SQR(16)+INT(SIN(0))+INT(RND(1)):V=VAL(STR$(12)):VPOKE 6000,77:Q=VPEEK(6000)',
    '50 LOCATE 0,20:PRINT"[";-(T>0);A$;B$;I;R;V;Q;"]"',
    "60 END",
    "100 T=T+1:RETURN",
    "RUN",
]
PROGRAM_PERSIST = [
    "NEW",
    '10 CLEAR 100,&HE000:SCREEN 2:DRAW"S8A1":BLOAD"CAS:",R',
    '20 PSET(100,100),15:DRAW"C15R3U2"',
    '30 FOR Y=92 TO 108:FOR X=92 TO 108:IF POINT(X,Y)=15 THEN N=N+1:S=S+X*3+Y',
    '40 NEXT:NEXT:SCREEN 0:ON ERROR GOTO 100:OPEN"A:X"FOR INPUT AS#1',
    '50 PRINT"[";N;S;"]":END',
    '100 PRINT"[E";ERR;"]";:RESUME 50',
    "RUN",
]
PROGRAM_CHAN = [
    "NEW",
    '10 CLEAR 100,&HE000:ON ERROR GOTO 100:OPEN"CRT:"FOR OUTPUT AS#1:BLOAD"CAS:",R',
    '20 PRINT#1,"[C]"',
    '30 CLOSE#1:OPEN"CRT:"FOR OUTPUT AS#1:PRINT#1,"[D]":CLOSE',
    '40 FILES',
    '50 PRINT"[N]":END',
    '100 PRINT"[E";ERR;ERL;"]":RESUME NEXT',
    "RUN",
]
PROGRAM_INPUT = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 CLS:FOR R=0 TO 9:PRINT"[R";STRING$(34,"X");"]":NEXT:VPOKE &H25A5,7',
    '30 INPUT"[I";A:PRINT"[V";A;VPEEK(&H25A5);"]":END',
    "RUN",
    "@WAIT40",
    "42",
]
PROGRAM_MIDLINE = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R:DEFFNA(X)=X+1:PRINT"[A";FNA(1);"]";:ERROR 2',
    "RUN",
]
PROGRAM_RESUME = [
    "NEW",
    '10 CLEAR 100,&HE000:ON ERROR GOTO 100',
    '20 PRINT"[A]";:ERROR 2:PRINT"[B]"',
    '30 PRINT"[C]":END',
    '100 BLOAD"CAS:",R:RESUME NEXT',
    "RUN",
]
PROGRAM_CONTDIR = [
    "NEW",
    "CLEAR 100,&HE000",
    'BLOAD"CAS:",R',
    "@WAIT40",
    "CONT",
    'PRINT"[Z";ERR;"]"',
]
PROGRAM_PRM = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 CLS:PRINT"[P]"',
    "RUN",
    "@WAIT40",
    'PRINT"[Y";CSRLIN;"]"',
]
PROGRAM_ABORT = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 PRINT"[A]";:ERROR 2',
    "RUN",
]
PROGRAM_ONERR = [
    "NEW",
    '10 CLEAR 100,&HE000:ON ERROR GOTO 100:BLOAD"CAS:",R',
    '20 PRINT"[A]";:ERROR 2',
    '30 PRINT"[R]";:GOSUB 200:PRINT"]":END',
    '100 PRINT"[E";ERR;"]";:RESUME 30',
    '200 PRINT"[G]";:RETURN',
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


PROGRAMS = {**{n: PROGRAM_NOCLEAR for n in NOCLEAR}, "abort": PROGRAM_ABORT,
            "onerr": PROGRAM_ONERR, "rich": PROGRAM_RICH, "rich2": PROGRAM_RICH2,
            "persist": PROGRAM_PERSIST, "chan": PROGRAM_CHAN, "input": PROGRAM_INPUT,
            "midline": PROGRAM_MIDLINE, "resume": PROGRAM_RESUME,
            "contdir": PROGRAM_CONTDIR, "prm": PROGRAM_PRM}


def tape(lo, hi, fill=0xA5):
    data = bytes([0xC9]) + bytes([fill]) * (hi - lo)
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
        open(path, "wb").write(tape(lo, hi, FILL.get(name, 0xA5)))
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            prog = PROGRAMS.get(name, PROGRAM)
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
