#!/usr/bin/env python3
"""D-DEFFN RAM HUNT — is $EA92..$EB00 ACTUALLY free? Ask the machine.

🔴 WHY THIS EXISTS. `make wall-assertion-check` polices ROM free-space claims and
**nothing polices RAM ones**, so they rot silently: `basic/sysvars.inc` advertised
*"376 B spare"* for three slices after the window had been spent, and what caught
it was the ASSEMBLER, not the reading. `scratchpad/rammap_sweep.py` says
$EA92..$EB00 carries no name in any component's map. **A map is still a reading.**

THE MEASUREMENT. Fill the window with a known pattern from BASIC, run one
subsystem hard, read every byte back, and print how many changed. A byte that
moves was written by something no map names.

⚠️ THIS IS A CLAIM ABOUT ZEROBAS'S OWN RAM LAYOUT, NOT ABOUT MSX-BASIC. The
references have an entirely different map, so there is no oracle here and the
probe runs `zb` only. That is stated rather than silently assumed.

⏱️ AND THE CAPTURE WINDOW IS PART OF THE MEASUREMENT, THREE TIMES OVER IN ONE
SESSION. A row that reads the ECHO of its own handler line, or `<NO OUTPUT>`,
has usually not finished: an 8-deep FOR nest re-executes ~2000 statements and a
real FAT write is slower still. **READ THE SCREEN before believing a red row** --
the raw capture for `n.for8` showed `RUN` with nothing after it, which is a
program still running and not a program that printed nothing.

🎯 THE NEIGHBOURS ARE THE POINT. The window is bounded BELOW by `FOR_STK`
($EA3A..$EA92, 8 x 11 B) and ABOVE by `LINEBUF` ($EB00, 256 B) with `TOKBUF`
($EC00, 576 B) beyond it. Those three are what a fill would most plausibly be
clobbered by, so each gets a row that drives it to its limit -- a full 8-deep FOR
nest, a maximal input line, and a line long enough to work the crunch.

⚠️ EVERY ROW NEEDS ITS OWN POSITIVE CONTROL, because "0 bytes changed" is exactly
what a probe that never ran also prints. `ctl.self` deliberately POKEs one byte
of the window and must report 1: it proves the fill, the read-back and the
counter all work.

🔴 AND THE SECOND CONTROL PASSED VACUOUSLY ON ITS FIRST RUN. `ctl.forstk` watches
the 8 bytes BELOW the window and requires a `FOR` workout to change them -- but
the first cut filled only the window, so those bytes were never pattern-keyed and
read "8 of 8 changed" whether or not the workout ran. It scored OK and proved
nothing. **A control is honest only about the cell it reads, and only if that
cell was SET.** The fill now covers FOR_STK and the window alike.
"""
from __future__ import annotations
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚠️ A DISK ROW NEEDS A DISK, AND THE PROBE MUST MOUNT ONE. Booting the machine
# bare made `OPEN"TS.TXT"FOR OUTPUT AS #1` answer ERR 59 -- which reads exactly
# like a channel-ceiling rule and is nothing of the kind. The shipped batteries
# pass `diska=` a WRITABLE COPY of this image (writing it mutates the fixture,
# so never mount the original).
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")

LO, N = 0xEA92, 110          # the candidate window, from rammap_sweep.py
FOR_STK = 0xEA3A             # the neighbour below -- ctl.forstk's subject

# label -> (workout lines, watch-base, watch-length, expected changed)
CASES: dict[str, tuple[list[str], int, int, str]] = {}


STEP: dict[str, float] = {}


ERRCONT: set[str] = set()
NEEDS_DISK: set[str] = set()


def case(label, lines, want, base=LO, n=N, step=None, errcont=False,
         disk=False):
    CASES[label] = (list(lines), base, n, want)
    if step:
        STEP[label] = step
    if errcont:
        ERRCONT.add(label)
    if disk:
        NEEDS_DISK.add(label)


# --- controls first: a battery whose subject is "nothing happened" must prove
#     it can see something happen at all -------------------------------------
case("ctl.self",   ["POKE &HEA92,255"],            "1")
case("ctl.forstk", ["FOR I=1 TO 3:NEXT"],          ">0", base=FOR_STK, n=8)
case("base.none",  ["A=1"],                        "0")

# --- the three neighbours, each driven to its limit -----------------------
# ⚠️ NOT `D` AND NOT `I`: those are the instrument's own counter and index. The
# first cut spelled the nest `...FOR D=1 TO 2 ... NEXT H,G,F,E,D,...`, which
# clobbered the counter, printed nothing, and let the scrape read the ECHO of
# `PRINT"[";D;"]"` back as a value -- a reading shaped like a result.
case("n.for8", ["FOR A=1 TO 2:FOR B=1 TO 2:FOR C=1 TO 2:FOR E=1 TO 2",
                "FOR F=1 TO 2:FOR G=1 TO 2:FOR H=1 TO 2:FOR J=1 TO 2",
                "NEXT J,H,G,F,E,C,B,A"],            "0", step=60.0)
# 🎯 THE BOUNDARY ROW. FOR_DEPTH is 8, so a NINTH frame is where a stack that
# does not bound itself would write past FOR_STK_END -- straight into the
# window. The workout is EXPECTED to fault; what is measured is that the window
# is untouched when it does.
case("n.for9", ["FOR A=1 TO 2:FOR B=1 TO 2:FOR C=1 TO 2:FOR E=1 TO 2",
                "FOR F=1 TO 2:FOR G=1 TO 2:FOR H=1 TO 2:FOR J=1 TO 2",
                "FOR K=1 TO 2"],                    "0", errcont=True)
case("n.gosub", ["GOSUB 1000"],                     "0")
# the CRUNCH buffer, worked by a long SOURCE LINE (TOKBUF's actual input), not
# by a long string -- the first cut used STRING$(200)+STRING$(200) and got
# ERR 14, this build's string ceiling being 255.
case("n.crunch", ["X=1:" + "X=X+1:" * 30 + "X=X+1"],  "0")

# --- the subsystems that own the biggest scratch windows nearby -----------
# ⚠️ a SCREEN-2 flood needs step≈90; at 12 it read <NO OUTPUT>, which is a
# missing measurement and not a result.
case("s.paint", ["SCREEN 2:LINE(0,40)-(255,40),7",
                 "PAINT(10,10),9,7", "SCREEN 0"],   "0", step=90.0)
case("s.draw",  ["SCREEN 2:DRAW\"R50D50L50U50\"", "SCREEN 0"],  "0")
case("s.play",  ['PLAY"CDEFG"'],                    "0")
case("s.str",   ['A$="":FOR J=1 TO 30:A$=A$+"xy":NEXT',
                 'B$=MID$(A$,3,10)'],               "0")
# ⚠️ THE FIXTURE, TWICE. `OPEN"A:T.T"...` gave ERR 59, so a `MAXFILES=1` was
# added -- and the SCREEN then showed `load error` / `File not OPEN in 60`,
# i.e. the OPEN still failed and the row exercised no disk write at all. The
# working form is the shipped batteries' own (`basic_probe_tgtspc.py` f.ctl):
# no drive prefix, a full 8.3 name. MAXFILES is not needed -- the default
# ceiling is already 1 (files.asm: "OPEN #1 works with no MAXFILES").
# 🔴 Neither failure was visible in the FACE; both needed the raw screen.
# 🔴 AND THE ROW VALIDATES ITSELF, because "0 bytes changed" has a SECOND CAUSE
# of green here: an OPEN that fails *without raising* -- which is exactly what
# this fixture did twice (it printed `load error` and carried on) -- still lets
# the program reach the print and still reports 0. So the row reads the file
# BACK and raises ERROR 99 if the round trip did not happen. A disk row that
# never touched the disk now reads `ERR 99`, not `0`.
case("s.disk",  ['OPEN"TS.TXT"FOR OUTPUT AS #1',
                 'PRINT#1,"HELLO"', 'CLOSE#1',
                 'OPEN"TS.TXT"FOR INPUT AS #1',
                 'LINE INPUT#1,Z$', 'CLOSE#1',
                 'IF Z$<>"HELLO" THEN ERROR 99'],  "0", step=120.0,
                disk=True)
case("s.files", ["FILES"],                          "0", disk=True)
# ...and the guard in s.disk is itself a claim, so it gets a control: the same
# round trip compared against the WRONG string must read ERR 99. If this reads
# `0`, s.disk's self-validation is decoration and its green means nothing.
case("ctl.diskfail", ['OPEN"TS.TXT"FOR OUTPUT AS #1',
                      'PRINT#1,"HELLO"', 'CLOSE#1',
                      'OPEN"TS.TXT"FOR INPUT AS #1',
                      'LINE INPUT#1,Z$', 'CLOSE#1',
                      'IF Z$<>"NOPE" THEN ERROR 99'], "ERR 99", step=120.0,
     disk=True)

# 🔴 GOTO LOOPS, NOT `FOR` LOOPS, AND THAT IS THE WHOLE INSTRUMENT DESIGN.
# A `FOR` loop WRITES FOR_STK ($EA3A..$EA92) -- the window's own lower
# neighbour. Filling or checking with one makes the instrument write the very
# region it is measuring, and it makes ctl.forstk unfalsifiable. A GOTO loop
# touches no stack, so the fill covers FOR_STK and the candidate window ALIKE
# and the control becomes real: fill both, run a FOR loop, and FOR_STK must
# change while the window must not.
FILL = ("I=0", "POKE {lo}+I,(I AND 255):I=I+1:IF I<{n} THEN {ln}")
CHECK = ("D=0:I=0",
         "IF PEEK({base}+I)<>((I+{off}) AND 255) THEN D=D+1",
         "I=I+1:IF I<{n} THEN {ln}")
BR = re.compile(r"\[([^\]]*)\]")


def face(cap):
    """🔴 THE **LAST** BRACKET, NEVER THE FIRST. `BR.search` finds the ECHO of the
    typed line `PRINT"[";D;"]"` -- which is itself a `[...]` -- and returns
    `";D;"`, an artifact shaped like a reading. It bit only the rows with enough
    program lines to keep that echo on screen, so it looked like a property of
    those workouts rather than of the readout. The program's own output is always
    the last bracket printed."""
    if cap is None:
        return "<NO CAPTURE>"
    ms = BR.findall(cap)
    if ms:
        return " ".join(ms[-1].split()) or "<empty>"
    return "<NO OUTPUT>"


def main() -> int:
    want = sys.argv[1:] or list(CASES)
    bad = [w for w in want if w not in CASES]
    if bad:
        print(f"unknown case(s): {bad}", file=sys.stderr)
        return 2
    dflt = float(os.environ.get("RAMFREE_STEP", "12.0"))
    fails = 0
    for label in want:
        lines, base, n, expect = CASES[label]
        step = STEP.get(label, dflt)
        # the fill covers FOR_STK *and* the window, so both are pattern-keyed
        span = LO + N - FOR_STK
        body = ["10 ON ERROR GOTO 900",
                "20 " + FILL[0],
                "30 " + FILL[1].format(lo=FOR_STK, n=span, ln=30)]
        body += [f"{40+10*k} {ln}" for k, ln in enumerate(lines)]
        t = 40 + 10 * len(lines)
        body += [f"{t} " + CHECK[0],
                 f"{t+10} " + CHECK[1].format(base=base, off=base - FOR_STK),
                 f"{t+20} " + CHECK[2].format(n=n, ln=t + 10),
                 f'{t+30} SCREEN 0:PRINT"[";D;"]":END',
                 # a row whose workout is MEANT to fault must still reach the
                 # check -- otherwise the handler answers instead of the
                 # measurement and the boundary is never read at all.
                 (f'900 RESUME {t}' if label in ERRCONT
                  else '900 SCREEN 0:PRINT"[ERR";ERR;"]":END'),
                 '1000 RETURN']
        kw = {}
        tmp = None
        if label in NEEDS_DISK:
            tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False)
            tmp.close()
            shutil.copy(TEST_DSK, tmp.name)   # never mount the original
            kw["diska"] = tmp.name
        try:
            caps = omsx_repl.run_cases(
                ZB_M, [("direct", ["NEW"] + body + ["RUN"])],
                batch=False, boot=8.0, step=step, cap_gap=10.0, timeout=400.0,
                **kw)
        finally:
            if tmp:
                os.unlink(tmp.name)
        got = face(caps[0])
        if expect == ">0":
            ok = got.isdigit() and int(got) > 0
        else:
            ok = got == expect
        fails += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {label:11s} "
              f"${base:04X}+{n:<3d} changed={got!r} want={expect}", flush=True)
        if os.environ.get("RAMFREE_RAW"):
            print("      RAW " + repr((caps[0] or "")[-400:]), flush=True)
    print(f"done — {len(want) - fails}/{len(want)} rows as expected", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
