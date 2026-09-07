#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RAMFREE -- is a declared FREE-RAM window ACTUALLY free? Ask the machine.

WHY THIS EXISTS. `make ram-claim-check` (D-RAMCLAIM) polices the NAME level: no
`equ` may resolve inside a `; FREE-RAM $A..$B` span. It refuses to claim more,
and says so on every run -- **an address is where a cell STARTS, never how long
it is**, so a cell below a claim can extend up into it (`TOKBUF`'s 612-byte
delta to the next name is 36 bytes free; `LINEBUF`'s 256-byte delta is 0). Only
the machine can settle extent, and this is the half that asks it.

THE MEASUREMENT. Fill every declared window with an address-keyed pattern, run
one subsystem hard, read every byte back, and report how many changed PER
WINDOW. A byte that moves was written by something no map names, and the claim
that window carries is false.

🎯 THE SPANS COME FROM `sysvars.inc`, NOT FROM A LIST HERE. They are parsed by
`tools/check_ram_claims.py`'s own resolver, so the two halves cannot drift: a
span declared and name-checked but never extent-checked would otherwise be
exactly the gap this pair exists to close.

🔴 GOTO LOOPS, NOT `FOR` LOOPS, AND THAT IS THE INSTRUMENT'S DESIGN. A `FOR`
loop writes a control frame; filling or checking with one would make the
instrument write regions it is measuring. A `GOTO` loop touches no control
stack, so the fill and the check are inert with respect to every subject.

⚠️ EVERY RUN CARRIES A POSITIVE CONTROL, because "0 bytes changed" is exactly
what a probe that never ran also prints. `ctl.poke` writes ONE byte into EACH
window and must report 1 for every one of them -- it proves the fill, the
read-back and each per-window counter independently.

🔴 AND A SECOND CONTROL, BECAUSE THE FIRST ONE'S ANCESTOR WENT STALE. The probe
this generalises (`scratchpad/ramfree_probe.py`) had `ctl.forstk`: fill
`$EA3A` and require a `FOR` workout to change it. D-CTLPOOL moved control frames
out of that array into the pool, and the control now reads 0 -- correctly RED,
its subject having moved out from under it. `ctl.pool` replaces it against the
subject that exists TODAY: a GOSUB nest must move the control pool's frontier,
which proves the machinery is live and that the pool is where the map says.

⚠️ THIS IS A CLAIM ABOUT ZEROBAS'S OWN RAM LAYOUT, NOT ABOUT MSX-BASIC. The
references have an entirely different map, so there is no oracle here and this
runs `zb` only -- stated rather than silently assumed.

⏱️ AND THE CAPTURE WINDOW IS PART OF THE MEASUREMENT. The fill and check walk
~2 x the total declared span in interpreted GOTO iterations; at the ancestor's
12 s default the rows read `<NO OUTPUT>` and the reader returned the ECHO of the
error line, which looks like a result. 90 s by default, per row where needed.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                    # noqa: E402,F401 [[one-temp-root]]

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
SYSVARS = os.path.join(ROOT, "basic", "sysvars.inc")

# 🎯 THE CONTROL POOL'S OWN WINDOW, for ctl.pool. The pool descends from
# `strheap_varceil()` (~$D9xx with the default CLEAR 200), so bytes just under
# that ceiling are the FIRST a GOSUB frame takes. Read from the machine would be
# better; a fixed probe address a few frames down is enough for a control whose
# only job is "something happened".
# \U0001f534 DERIVED FROM THE MACHINE, NOT HARDCODED -- and the comment above used to
# say a fixed address was "enough". It was, until the ceiling moved: D-FIELDFIX
# grew the per-channel block by 256 B, `strheap_varceil()` dropped with it, and
# $D980 ended up ABOVE the pool top ($D906) instead of a few frames below it.
# The row then read "the GOSUB nest did NOT move the control pool" -- a true
# statement about a window that was no longer in the pool.
# CTLTOP ($E052) caches `strheap_varceil()` on the machine, so the workload can
# compute its own window and no constant can go stale again.
CTLTOP_ADDR = 0xE052    # the pool's TOP, cached in RAM (sysvars.inc)
POOL_BACKOFF = 24       # a few frames below the top, where a GOSUB writes first
POOL_N = 16
POOL_BASE = "PB"        # the BASIC variable the workload computes it into
MAX_SPANS = 8           # Q0..Q7 counters; more would need a second letter


def declared_spans():
    """The `; FREE-RAM $A..$B` spans, parsed by the name-level gate's OWN
    regex so the two halves cannot drift apart."""
    import check_ram_claims as C
    text = open(SYSVARS).read()
    out = [(int(m.group(1), 16), int(m.group(2), 16))
           for m in C.CLAIM.finditer(text)]
    return sorted(set(out))


# label -> (workout lines, step, needs_disk, errcont, expect)
# `expect` is "0" for every real row: a declared-free window must not move.
CASES = [
    ("ctl.poke",  None,                                    90.0, 0, 0, "POKE"),
    ("ctl.pool",  ["Q9=0", "GOSUB 1010"],                  150.0, 0, 1, "POOL"),
    ("base.none", ["A=1"],                                 90.0, 0, 0, "0"),
    ("n.for8",    ["FOR A=1 TO 2:FOR B=1 TO 2:FOR C=1 TO 2:FOR E=1 TO 2",
                   "FOR F=1 TO 2:FOR G=1 TO 2:FOR H=1 TO 2:FOR J=1 TO 2",
                   "NEXT J,H,G,F,E,C,B,A"],               120.0, 0, 0, "0"),
    # 🎯 THE DEPTH ROW. The control pool is thousands of frames deep now, so
    # this drives it hard rather than to its old 8-frame ceiling: whatever the
    # pool walks over on its way down must not be a declared-free window.
    ("n.deep",    ["ON ERROR GOTO 900", "Q9=0", "GOSUB 1010"],
                                                          150.0, 0, 1, "0"),
    ("n.crunch",  ["X=1:" + "X=X+1:" * 30 + "X=X+1"],      90.0, 0, 0, "0"),
    ("s.paint",   ["SCREEN 2:LINE(0,40)-(255,40),7",
                   "PAINT(10,10),9,7", "SCREEN 0"],       150.0, 0, 0, "0"),
    ("s.draw",    ["SCREEN 2:DRAW\"R50D50L50U50\"", "SCREEN 0"],
                                                          120.0, 0, 0, "0"),
    ("s.play",    ['PLAY"CDEFG"'],                         90.0, 0, 0, "0"),
    # ⚠️ A `GOTO`-SHAPED LOOP, NOT `FOR` -- see the header: a FOR here would make
    # the workout push a control frame and muddy what the row attributes to the
    # string engine.
    ("s.str",     ['A$=""', 'A$=A$+"xy":Q8=Q8+1:IF Q8<30 THEN {SELF}',
                   'B$=MID$(A$,3,10)'],                    90.0, 0, 0, "0"),
    ("s.files",   ["FILES"],                              120.0, 1, 0, "0"),
]

BR = re.compile(r"\[([^\]]*)\]")


def face(cap):
    """🔴 THE **LAST** bracket, never the first: the ECHO of the typed readout
    line is itself a `[...]`, and returning it gives an artifact shaped like a
    reading. ⚠️ And the error line's echo is a bracket too, which is what a row
    that timed out returns -- hence the digits-only test at the call site."""
    if cap is None:
        return "<NO CAPTURE>"
    ms = BR.findall(cap)
    return (" ".join(ms[-1].split()) or "<empty>") if ms else "<NO OUTPUT>"


def build(spans, lines, poke, errcont, pool_span=False):
    """The BASIC program: fill every span, run the workout, count per span.
    ⚠️ Index `P`, counters `Q0..`; the workouts use A-K, X, Z$ and A$/B$, and
    the ancestor was bitten by a nest that clobbered the instrument's own
    counter and then read the echo of its PRINT back as a value."""
    # 🔴 THE PATTERN IS KEYED ON THE OFFSET, NOT THE ADDRESS, AND THAT IS
    # FORCED BY THE LANGUAGE. MSX `AND` is a 16-bit SIGNED integer operator, so
    # `(($E058+P) AND 255)` overflows for every address above $7FFF -- the first
    # cut used the address and every row read `ERR 6`. `(P+k) AND 255` keeps both
    # operands small; `k` is the span's index, so two spans never carry the same
    # bytes at the same offset and a mix-up cannot read as clean.
    # 🔴 EVERY INSTRUMENT VARIABLE IS CREATED **BEFORE** THE WORKOUT, AND A
    # DEEP-RECURSION ROW HANGS WITHOUT IT. After D-CTLPOOL the variable/array
    # allocator's ceiling is `min(varceil, CSP)`, so with the control pool driven
    # to its floor there is NO ROOM FOR A NEW VARIABLE -- the check's first
    # `Q0=0` raises Out of memory, the handler RESUMEs to the check, and it
    # raises again, forever. The row read `<NO OUTPUT>` and looked like a slow
    # workout. Pre-creating them costs nothing and is the same discipline
    # basic_probe_ctllim.py needs for its own tally.
    names = " ".join(f"Q{i}=0:" for i in range(len(spans)))
    body, ln = ["10 ON ERROR GOTO 900", f"15 P=0:Q9=0:Q8=0:{names}P=0"], 20
    # base EXPRESSION per span: a literal for the declared windows, and the
    # machine's own CTLTOP for the pool probe (see POOL_BASE above)
    bases = [f"&H{lo:04X}" for lo, _hi in spans]
    if pool_span:
        bases[-1] = POOL_BASE
        body.append(f"17 {POOL_BASE}=PEEK(&H{CTLTOP_ADDR:04X})"
                    f"+256*PEEK(&H{CTLTOP_ADDR+1:04X})-{POOL_BACKOFF}")
    for i, ((lo, hi), base) in enumerate(zip(spans, bases)):   # fill
        body.append(f"{ln} P=0")
        body.append(f"{ln+10} POKE {base}+P,((P+{i}) AND 255):P=P+1"
                    f":IF P<{hi-lo} THEN {ln+10}")
        ln += 20
    if poke:                                                   # the control
        for base in bases:
            body.append(f"{ln} POKE {base},PEEK({base}) XOR 255")
            ln += 10
    for line in lines or []:
        # `{SELF}` is this line's own number -- a workout that loops cannot know
        # it at definition time, and the first cut wrote a literal `0` there and
        # read ERR 8 (Undefined line number) instead of a tally.
        body.append(f"{ln} " + line.replace("{SELF}", str(ln)))
        ln += 10
    check = ln
    for i, ((lo, hi), base) in enumerate(zip(spans, bases)):   # count
        body.append(f"{ln} Q{i}=0:P=0")
        body.append(f"{ln+10} IF PEEK({base}+P)<>((P+{i}) AND 255) "
                    f"THEN Q{i}=Q{i}+1")
        body.append(f"{ln+20} P=P+1:IF P<{hi-lo} THEN {ln+10}")
        ln += 30
    tally = ";".join(f"Q{i}" for i in range(len(spans)))
    body.append(f'{ln} SCREEN 0:PRINT"[";{tally};"]":END')
    body.append(f'900 {"RESUME " + str(check) if errcont else "SCREEN 0:PRINT" + chr(34) + "[E" + chr(34) + ";ERR;" + chr(34) + "]" + chr(34) + ":END"}')
    body.append("1000 RETURN")
    # the deep-recursion helper for n.deep: a GOTO-free self-call that the pool
    # bounds, reached only by that row (ERRCONT catches its Out of memory).
    body.append("1010 Q9=Q9+1:GOSUB1010")
    body.append("1020 RETURN")
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--gate", action="store_true")
    args = ap.parse_args()

    spans = declared_spans()
    if not spans:
        print("INSTRUMENT FAULT: no `; FREE-RAM` span declared in "
              "basic/sysvars.inc -- nothing to measure, and a clean run here "
              "would mean the check had stopped looking.")
        return 2
    if len(spans) > MAX_SPANS:
        print(f"INSTRUMENT FAULT: {len(spans)} spans but only {MAX_SPANS} "
              f"counters (Q0..Q{MAX_SPANS-1}) -- widen the naming first.")
        return 2

    print(f"\nwatching {len(spans)} declared FREE-RAM span(s):")
    for lo, hi in spans:
        print(f"    ${lo:04X}..${hi:04X}   {hi-lo:4d} B")
    print()

    sel = [c for c in CASES if not args.only or args.only in c[0]]
    if not any(c[0].startswith("ctl.") for c in sel):
        sel = [c for c in CASES if c[0].startswith("ctl.")] + sel

    fails, w = [], max(len(c[0]) for c in CASES)
    for label, lines, step, disk, errcont, expect in sel:
        # the pool window's ADDRESSES are placeholders -- only its LENGTH is
        # used, because build() computes the base from CTLTOP on the machine
        watch = spans + ([(0, POOL_N)] if expect == "POOL" else [])
        body = build(watch, lines, expect == "POKE", errcont,
                     pool_span=(expect == "POOL"))
        kw = {}
        tmp = None
        if disk:
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False)
            tmp.close()
            shutil.copy(TEST_DSK, tmp.name)      # never mount the original
            kw["diska"] = tmp.name
        try:
            caps = omsx_repl.run_cases(ZB_M, [("d", ["NEW"] + body + ["RUN"])],
                                       batch=False, boot=8.0, step=step,
                                       cap_gap=12.0, timeout=500.0, **kw)
        finally:
            if tmp:
                os.unlink(tmp.name)
        got = face(caps[0])
        vals = got.split()
        readable = len(vals) == len(watch) and all(v.isdigit() for v in vals)
        if not readable:
            ok, note = False, "🔴 NOT MEASURED (the row never printed its tally)"
        elif expect == "POKE":
            ok = all(int(v) == 1 for v in vals)
            note = "every span saw its one poked byte" if ok else \
                   "🔴 a span did NOT see its poked byte -- that counter is blind"
        elif expect == "POOL":
            # 🔴 THE FIRST CUT SCORED THIS `ok = True` WITH A COMMENT SAYING
            # "scored separately below", AND THERE WAS NO BELOW -- a control
            # that asserts nothing, which is the exact shape of the stale
            # ctl.forstk it was written to replace. It watches ONE EXTRA span
            # inside the control pool and requires THAT to move while every
            # declared span stays still: proof the workouts reach the machine,
            # and that the pool is where the map says it is.
            ok = int(vals[-1]) > 0 and all(int(v) == 0 for v in vals[:-1])
            note = (f"the pool moved ({vals[-1]} B) and no declared span did"
                    if ok else
                    "🔴 the GOSUB nest did NOT move the control pool -- either "
                    "the workout never ran or the pool is not at "
                    f"CTLTOP-{POOL_BACKOFF}")
        else:
            ok = all(int(v) == 0 for v in vals)
            note = "clean" if ok else "🔴 A DECLARED-FREE WINDOW WAS WRITTEN"
        if not ok:
            fails.append(label)
        print(f"  {'OK  ' if ok else 'FAIL'} {label:{w}s} {got:24s} {note}")

    print(f"\nrows {len(sel)}  red {len(fails)}")
    if fails:
        print("  A declared-free window that MOVES is a false claim: the span is "
              "in use by something no name covers, or a cell below it extends "
              "up into it -- which is exactly what ram-claim-check cannot see.")
    print("RAMFREE: PASS" if not fails else f"RAMFREE: RED ({len(fails)})")
    return 1 if (fails and args.gate) else 0


if __name__ == "__main__":
    sys.exit(main())
