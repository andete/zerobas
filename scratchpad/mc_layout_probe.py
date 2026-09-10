#!/usr/bin/env python3
"""SCREEN 3 MULTICOLOUR VRAM LAYOUT — black-box derivation (scout §6, item 1).

Plot ONE cell in a distinctive colour, then find which VRAM byte and which NIBBLE
changed. That is a measurement of OUR OWN observable machine state through VPEEK;
no reference ROM is decoded. It is how the rest of this project's VDP knowledge
was obtained.

⚠️ Same fixture rule as the scout: capture into variables, force SCREEN 0, THEN
print -- a screen scrape cannot read PRINT while the VDP is in a graphics mode.
ON ERROR so a refusal is a readable value, never silence.
"""
from __future__ import annotations
import os, re, sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, step=2.5, reset=("NEW",)),
}

# (label, [program lines without numbers]) -- line 10 is always ON ERROR
CASES = {
 # --- RECON: what is the fill byte, and does a 6144-VPEEK loop finish here? ---
 "mc.fill":  ['SCREEN 3', 'V=VPEEK(0):W=VPEEK(&H1800):U=VPEEK(&H1801)',
              'SCREEN 0:PRINT"[";V;",";W;",";U;"]":END'],
 "mc.speed": ['SCREEN 3', 'T=0:FOR I=0 TO 6143:T=T+VPEEK(I):NEXT',
              'SCREEN 0:PRINT"[";T;"]":END'],
 # ⚠️ ASK THE MACHINE FOR THE TABLE ADDRESSES rather than guessing them. BASE(n)
 # is the published MSX-BASIC function for exactly this.
 # 🔴 DRAFT 1 USED THE WRONG GROUP AND ITS CONTROL AGREED WITH IT. The groups are
 # 0-4 SCREEN 0, 5-9 SCREEN 1, 10-14 SCREEN 2, 15-19 SCREEN 3 -- so BASE(10..12)
 # read SCREEN 2, and the "control" BASE(5..7) read SCREEN 1, whose nominal bases
 # are the SAME ($1800/$2000/$0000). Two readings agreeing said the indices were
 # wrong, not that the answer was right. The SCREEN-0 group is the control now,
 # because its layout DIFFERS ($0000 name, $0800 pattern) and so can discriminate.
 "mc.base":  ['SCREEN 3', 'A=BASE(15):B=BASE(16):C=BASE(17)',
              'SCREEN 0:PRINT"[";A;",";B;",";C;"]":END'],
 "mc.base2": ['SCREEN 3', 'A=BASE(18):B=BASE(19)',
              'SCREEN 0:PRINT"[";A;",";B;"]":END'],
 "ctl.s2base":['SCREEN 2', 'A=BASE(10):B=BASE(11):C=BASE(12)',
              'SCREEN 0:PRINT"[";A;",";B;",";C;"]":END'],
 "ctl.s0base":['SCREEN 0', 'A=BASE(0):B=BASE(2)',
              'SCREEN 0:PRINT"[";A;",";B;"]":END'],
}

# --- the address sweep -------------------------------------------------------
# Plot ONE cell in colour 7 and find the byte in the pattern generator ($0000,
# measured above) that stopped being the $44 background fill. The MC generator is
# 1536 B (6 blocks of 256), so the scan is short enough to run in BASIC.
# Prints [addr, value]: the value's NIBBLE says which half of the byte the cell is.
PLOT = ['SCREEN 3', 'PSET({x},{y}),7', 'A=-1:B=0',
        'FOR I=0 TO 1535:IF VPEEK(I)<>68 THEN A=I:B=VPEEK(I):I=1535',
        'NEXT',
        'SCREEN 0:PRINT"[";A;",";B;"]":END']

# logical (x,y) -> hardware cell (x>>2, y>>2), established by the scout's §2
SWEEP = [("p.0.0",   0,   0), ("p.4.0",   4,   0), ("p.8.0",   8,   0),
         ("p.0.4",   0,   4), ("p.0.8",   0,   8), ("p.0.32",  0,  32),
         ("p.252.188", 252, 188)]
for _lab, _x, _y in SWEEP:
    CASES[_lab] = [ln.format(x=_x, y=_y) for ln in PLOT]

# --- VERIFY: predictions written BEFORE the run (see the derivation) ---------
# ⚠️ p.252.188's SCAN returned <NO OUTPUT> on BOTH references -- an APPARATUS
# TIMEOUT, not a reading: cell (63,47) lands at 1535, the LAST byte, so that scan
# ran all 1536 iterations where every other case exited within a few. A direct
# VPEEK at the PREDICTED address costs nothing and is a stronger row anyway.
VERIFY = ['SCREEN 3', 'PSET({x},{y}),7', 'V=VPEEK({a})',
          'SCREEN 0:PRINT"[";V;"]":END']
for _lab, _x, _y, _a in [("v.252.188", 252, 188, 1535),   # want 71  ($47, low)
                         ("v.128.64",  128,  64,  640),   # want 116 ($74, high)
                         ("v.5.5",       5,   5,    1)]:  # want 71  ($47, low)
    CASES[_lab] = [ln.format(x=_x, y=_y, a=_a) for ln in VERIFY]

# 🔴 zerobas runs on C-BIOS, NOT the reference BIOS. CHGMOD is what lays down the
# SCREEN-3 NAME TABLE at $0800, so if C-BIOS's mode-3 setup differs, an
# implementation that writes only the pattern generator inherits a wrong table.
# This is the row that decides whether the generator is enough. zb is a SIDE here.
CASES["nt.s3"] = ['SCREEN 3',
                  'A=VPEEK(&H800):B=VPEEK(&H801):C=VPEEK(&H81F)',
                  'D=VPEEK(&H820):E1=VPEEK(&H900):F=VPEEK(&HA00)',
                  'SCREEN 0:PRINT"[";A;B;C;D;E1;F;"]":END']
CASES["nt.s2"] = ['SCREEN 2',
                  'A=VPEEK(&H1800):B=VPEEK(&H1801):C=VPEEK(&H181F)',
                  'D=VPEEK(&H1820):E1=VPEEK(&H1900):F=VPEEK(&H1A00)',
                  'SCREEN 0:PRINT"[";A;B;C;D;E1;F;"]":END']

# --- PAINT semantics in MC: there is NO pattern bit, so "drawn vs never-drawn"
# (the distinction gfx_paint_read's border test is built on, and the one the
# VG-8020 differential forced in SCREEN 2) has no counterpart. Measure what the
# references actually do before implementing anything.
_PT = ['SCREEN 3', 'LINE(0,40)-(255,40),7', '{paint}', 'V={read}',
       'SCREEN 0:PRINT"[";V;"]":END']
for _lab, _p, _r in [
        # flood from above the line: does it spread, and where does it stop?
        ("pt.flood",  "PAINT(10,10),9",   "POINT(10,0)"),
        ("pt.stop",   "PAINT(10,10),9",   "POINT(10,60)"),
        ("pt.online", "PAINT(10,10),9",   "POINT(10,40)"),
        # explicit border argument
        ("pt.bord7",  "PAINT(10,10),9,7", "POINT(10,0)"),
        # border == the BACKGROUND colour (4): the SCREEN-2 bug case
        ("pt.bord4",  "PAINT(10,10),9,4", "POINT(10,0)"),
]:
    CASES[_lab] = [ln.format(paint=_p, read=_r) for ln in _PT]

# round 2: pt.stop showed the DEFAULT border does not stop at colour 7. These two
# discriminate whether an EXPLICIT border does, and whether the default floods the
# whole surface -- pt.bord7 could not tell, because its read point was on the
# SEED's own side of the line.
for _lab, _p, _r in [
        ("pt.b7stop", "PAINT(10,10),9,7", "POINT(10,60)"),   # border 7: crossed?
        ("pt.far",    "PAINT(10,10),9",   "POINT(200,150)"), # default: whole screen?
]:
    CASES[_lab] = [ln.format(paint=_p, read=_r) for ln in _PT]

CASES["d.seed"]  = ['SCREEN 3', 'PAINT(10,10),9', 'V=POINT(10,10)',
                    'SCREEN 0:PRINT"[";V;"]":END']
CASES["d.line"]  = ['SCREEN 3', 'LINE(0,40)-(255,40),7', 'V=POINT(100,40)',
                    'SCREEN 0:PRINT"[";V;"]":END']
CASES["d.circ"]  = ['SCREEN 3', 'CIRCLE(100,100),20,7', 'V=POINT(120,100)',
                    'SCREEN 0:PRINT"[";V;"]":END']
CASES["d.box"]   = ['SCREEN 3', 'LINE(10,10)-(50,50),7,BF', 'V=POINT(30,30)',
                    'SCREEN 0:PRINT"[";V;"]":END']

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


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = _last_bracket(BR, cap)
    if m:
        return " ".join(m.group(1).split()) or "<empty>"
    e = ERR.search(cap)
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def main() -> int:
    want = sys.argv[1:] or list(CASES)
    for label in want:
        lines = CASES[label]
        body = ["10 ON ERROR GOTO 900"]
        body += [f"{20+10*k} {ln}" for k, ln in enumerate(lines)]
        body += ['900 SCREEN 0:PRINT"[ERR";ERR;"]":END']
        for side, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=cfg["step"])
            print(f"  {side:7s} {label:10s} -> {face(caps[0])!r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
