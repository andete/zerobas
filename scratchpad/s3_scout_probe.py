#!/usr/bin/env python3
"""SCREEN 3 SCOUT — what is the coordinate space, and where does it clamp?

Not a gate. One question, asked of both references: zerobas raises ERR 5 for every
SCREEN-3 pixel op, so the DESIGN cannot be priced until the surface is known.
Everything else about SCREEN 3 (the rasteriser, the address model) is downstream
of "how big is it and what happens at the edge".

Each case prints [<POINT>] so a refusal, a plot and an off-screen read are all
distinguishable in one span. `pset3` reproduces the already-filed m.s3/v.pset3
reading as this probe's OWN positive control -- without it, an agreeing row could
be agreeing because the fixture never ran.
"""
from __future__ import annotations
import os, re, sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB, boot=8.0, step=2.5, reset=("NEW",)),
}

# 🔴 DRAFT 1 OF THIS PROBE READ `<NO OUTPUT>` ON ALL 21 ROWS, INCLUDING THE
# SCREEN-2 CONTROL. A screen scrape cannot read PRINT output while the VDP is in
# a graphics mode -- "the screen was blank" and "the machine is still in SCREEN 3"
# are the same reading. The control is what caught it. The shape below is
# basic_probe_lineerr.py's TRAP_PROG: capture into variables, force SCREEN 0, THEN
# print; and ON ERROR so a refusal is a readable VALUE instead of silence.
PROG = [
    "10 ON ERROR GOTO 100",
    "20 {setup}",
    "30 {stmt}",
    "40 E=0:V={read}",
    '50 SCREEN 0:PRINT"[";E;",";V;"]":END',
    "100 E=ERR:V=-1:RESUME 50",
]

CASES = [
    # 🟢 the control: SCREEN 2 PSET works on all three sides. If this reads
    # <NO OUTPUT> or -1 the fixture is broken and nothing below is a reading.
    ("ctl.s2",     "SCREEN 2", "PSET(20,21)",        "POINT(20,21)"),
    ("pset3",      "SCREEN 3", "PSET(20,21)",        "POINT(20,21)"),
    # THE QUESTION: is the SCREEN-3 surface 64x48, or still 256x192?
    ("s3.63x47",   "SCREEN 3", "PSET(63,47)",        "POINT(63,47)"),
    ("s3.64x48",   "SCREEN 3", "PSET(64,48)",        "POINT(64,48)"),
    ("s3.255x191", "SCREEN 3", "PSET(255,191)",      "POINT(255,191)"),
    # the EDGE rule: D-SPOKELINE proved LINE CLAMPS in SCREEN 2 -- does it here?
    ("s3.clamp",   "SCREEN 3", "LINE(0,0)-(300,300)", "POINT(63,47)"),
    # is the surface really 16-colour per pixel (no clash)?
    ("s3.col",     "SCREEN 3", "PSET(10,10),7",      "POINT(10,10)"),
    # 🟢 second control: does POINT read back 0 on an UNTOUCHED SCREEN-3 pixel?
    ("ctl.s3rd",   "SCREEN 3", "REM no plot",        "POINT(30,30)"),

    # 🔴 ROUND 2 -- THE DISCRIMINATOR. Round 1 showed PSET(255,191) "works", but a
    # PSET and a POINT that BOTH wrap to the same cell agree whatever the model is.
    # These separate "256x192 logical, 4x4 hardware cells" from "the coordinate is
    # used raw": plot ONE point in a distinctive colour, then read a DIFFERENT
    # logical coordinate that shares its 4x4 cell, and one that does not.
    ("s3.same",    "SCREEN 3", "PSET(0,0),7",        "POINT(3,3)"),
    ("s3.next",    "SCREEN 3", "PSET(0,0),7",        "POINT(4,4)"),
    ("s3.aliashi", "SCREEN 3", "PSET(255,191),7",    "POINT(252,188)"),
    # and the domain edge: is 256/192 refused as it is in SCREEN 2?
    ("s3.256",     "SCREEN 3", "PSET(256,192),7",    "POINT(255,191)"),

    # 🔴 SEPARATION ROWS -- added 2026-08-22 because the rows above CANNOT see a
    # broken address model. PSET and POINT both go through gfx_calc_addr_mc, so a
    # write/read ROUND TRIP through one address function is invariant under ANY
    # consistent bijection: knife the formula and the read follows the write.
    # K-S1 proved it, reddening nothing with the row term cut to zero. Each row
    # below writes at ONE coordinate and reads at ANOTHER that is a DIFFERENT cell
    # by exactly ONE term of the formula, so each term becomes falsifiable.
    ("s3.rowsep",  "SCREEN 3", "PSET(0,0),7",        "POINT(0,4)"),   # (cy&7)
    ("s3.blksep",  "SCREEN 3", "PSET(0,0),7",        "POINT(0,32)"),  # (cy>>3)*256
    ("s3.colsep",  "SCREEN 3", "PSET(0,0),7",        "POINT(8,0)"),   # x & $F8
]

BR = re.compile(r"\[([^\]]*)\]")

def _last_bracket(rx, text):
    """🔴 THE **LAST** `[...]`, NEVER THE FIRST (D-BRLAST, 2026-09-10).

    `rx.search` returns the FIRST bracket on screen, and that is the ECHO of the
    typed line `PRINT"[";V;"]"` -- itself a `[...]` -- so it yields `";V;"`, an
    artifact shaped like a reading. This family was protected only by accident:
    every fixture here enters a graphics mode, and the closing `SCREEN 0` clears
    the echo away. A fixture that never leaves SCREEN 0 has no defence at all,
    which is exactly how `ramfree_probe`'s rows failed -- and it looked like a
    property of those workouts rather than of the readout.

    The program's own output is always the LAST bracket printed. Returns a match
    object so `.group(1)` keeps working at the call sites.
    """
    m = None
    for m in rx.finditer(text):
        pass
    return m

ERR = re.compile(r"^\s*([A-Z][A-Za-z' ]+ error|Illegal function call|Overflow|"
                 r"Out of memory|Type mismatch|Subscript out of range)", re.M)


def face(cap: str | None) -> str:
    if cap is None:
        return "<NO CAPTURE>"
    m = _last_bracket(BR, cap)
    if m:
        return m.group(1).strip() or "<empty>"
    e = ERR.search(cap)
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def main() -> int:
    only = sys.argv[1:] or None
    rows = {}
    for side, cfg in SIDES.items():
        for label, setup, stmt, read in CASES:
            if only and label not in only:
                continue
            body = [ln.format(setup=setup, stmt=stmt, read=read) for ln in PROG]
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=cfg["step"])
            rows.setdefault(label, {})[side] = face(caps[0])
            print(f"  {side:7s} {label:12s} -> {rows[label][side]!r}", flush=True)
    print("\n=== SCREEN 3 SCOUT ===")
    for label, *_ in CASES:
        if label not in rows:
            continue
        r = rows[label]
        agree = "refs agree" if r.get("vg8020") == r.get("cf3300") else "🔴 REFS DIFFER"
        print(f"  {label:12s} vg8020={r.get('vg8020')!r:26s} "
              f"cf3300={r.get('cf3300')!r:26s} zb={r.get('zb')!r:20s} [{agree}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
