#!/usr/bin/env python3
"""D-DUPSPAN — one row per COLLAPSED ERROR TAIL SITE.

The carve replaced 13 byte-identical `ld a,N / jp raise_error` tails with `equ`
aliases onto two canonical ones (interp.asm's `gb_illegal` for ERR 5,
play.asm's `pl_syntax` for ERR 2), on `gfx_absent equ gfx_err5`'s precedent.

🎯 WHAT THESE ROWS ARE FOR. The batteries already say the collapse changed no
observable; they cannot say the collapse was OBSERVABLE AT ALL. A tail nothing
exercises would stay green through any mistake made to it. Every row below
reaches ONE named site, and the knife runner cuts the CANONICAL value: a site
whose row does not redden is a site the battery cannot see, which is the finding
either way.

⚠️ READOUT. `ON ERROR GOTO 900` + `PRINT ERR` is not decoration: `raise_error`
is TRAPPABLE and `stmt_error` is not, so a row that read ERR 2 from the wrong
mechanism would abort the RUN and read `<NO OUTPUT>` here. The trappability is
part of what each tail claims (see pl_syntax's and gfx_syntax's own headers).

⚠️ `pl_absent` HAS NO ROW AND CANNOT HAVE ONE. It is the defensive
"subrom_call reported the tenant missing" tail, unreachable on the merged build
-- exactly like `gfx_absent`, the D-PAINTBORD carve's own subject. Its collapse
is unfalsifiable by a probe and is claimed on the assembler alone. 8 sites, 7
rows.
"""
from __future__ import annotations
import os, re, sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}
_only = os.environ.get("DUPSPAN_SIDES")
if _only:
    SIDES = {k: v for k, v in SIDES.items() if k in _only.split(",")}

# label -> (program lines, the SITE it reaches)
CASES: dict[str, list[str]] = {}
SITE: dict[str, str] = {}


HANDLER: dict[str, str] = {}


def case(label, site, *lines, handler=None):
    CASES[label] = list(lines)
    SITE[label] = site
    if handler:
        HANDLER[label] = handler


# ===========================================================================
# THE ERR-5 FAMILY -- eight tails, now `equ gb_illegal`.
# ===========================================================================
# gb_illegal itself, through all THREE of its own local entries: the bare `jr`
# (get_vram_arg), a `jp` (eval_pos_arg) and a `jr nz` (gba_byte). The first two
# are the only `jr`s in the family that did NOT have to widen, which is the
# whole reason gb_illegal and not gfx_err5 is the canonical.
case("e5.vpoke",  "gb_illegal/jr",    "VPOKE 16384,0")
case("e5.mid0",   "gb_illegal/jp",    'A$=MID$("abc",0)')
case("e5.chr",    "gb_illegal/jr nz", "A$=CHR$(256)")
# the seven aliases
case("e5.sound",  "snd_illegal",      "SOUND 14,0")
case("e5.pset0",  "gfx_err5",         "SCREEN 0", "PSET(10,10)")
case("e5.eof300", "fchk_ifc",         "A=EOF(300)")
case("e5.interv", "eoi_err5",         "ON INTERVAL=0 GOSUB 800")
case("e5.strig",  "strig_illegal",    "STRIG(5) ON")
case("e5.key",    "strig_illegal",    "KEY(0) ON")
case("e5.swap3",  "sw_illegal",       "A=1:B=2:C=3", "SWAP A,B,C")
# 🔴 THE ROW THIS SLICE MOST NEEDS. sw_illegal was a FALLTHROUGH target, so the
# alias could not stand alone -- `sw_absent` now reaches ERR 5 through a `jp`
# that did not exist before. Nothing else in the tree exercises that `jp`.
case("e5.swapnew", "sw_absent->jp",   "A=1", "SWAP A,B")

# ===========================================================================
# THE ERR-2 FAMILY -- six tails, now `equ pl_syntax`.
# ===========================================================================
case("e2.play",   "pl_syntax",        "PLAY")
case("e2.line",   "elg_syntax",       "SCREEN 2", "LINE(1,1)(5,5)")
case("e2.pset",   "pc_syntax",        "SCREEN 2", "PSET 10,10")
case("e2.paint4", "ep_syntax",        "SCREEN 2", "PAINT(10,10),9,15,")
case("e2.putspr", "gfx_syntax",       "SCREEN 2", "PUT SPRITE 0")
case("e2.letvdp", "gfx_syntax",       "LET VDP(0)=2")
case("e2.oninterv", "trap_syntax",    "ON INTERVAL GOSUB 800")

# ===========================================================================
# 🔴 FOLLOW-UP ROWS. These are NOT part of the carve's claim -- they are three
# divergences the carve's own row set turned up, and they are here so each is
# separated from MY FIXTURE before anything is filed.
# ===========================================================================
# (a) e2.paint4 read `<NO OUTPUT>` on both references at step=4 and `ERR 2` at
#     step=90, while zerobas read ERR 2 at BOTH. 🔴 A <NO OUTPUT> IS NOT A
#     DIVERGENCE, IT IS A MISSING MEASUREMENT -- but the ASYMMETRY is one, and
#     the only plausible consumer of those seconds is the flood. A TIMING
#     INFERENCE IS NOT A MEASUREMENT EITHER: trap the ERR 2, then read a pixel
#     the fill must have covered. Painted -> the reference raises the 4th-argument
#     Syntax error AFTER painting; unpainted -> it raises before, like zerobas,
#     and the seconds went somewhere else.
case("x.paint4pt", "ep_syntax/order",
     "SCREEN 2", "PAINT(10,10),9,15,",
     "V=POINT(10,0):SCREEN 0:PRINT\"[\";V;\"]\":END")
case("x.paint3pt", "ep_syntax/order-ctl",   # the SAME program with no 4th arg:
     "SCREEN 2", "PAINT(10,10),9,15",       # the fill's own positive control
     "V=POINT(10,0):SCREEN 0:PRINT\"[\";V;\"]\":END")
# (b) `SWAP A,B,C` read ERR 2 on both references where
#     docs/missing-vg8020-characterization.md §4.5 records `Illegal function call`
#     -- singled out there as *the kind of detail that only a measurement
#     produces*. MY fixture pre-defines A, B and C; the doc's shape may not have.
#     Separate the two before believing either.
case("x.swap.pre",  "sw_illegal/defined",   "A=1:B=2:C=3", "SWAP A,B,C")
case("x.swap.bare", "sw_illegal/undefined", "SWAP A,B,C")
case("x.swap.two",  "sw_illegal/ctl",       "A=1:B=2", "SWAP A,B", "PRINT A")
# (c) bare `PLAY` read ERR 24 (Missing operand) on both references where zerobas
#     raises ERR 2 from pl_syntax -- whose own header cites the VG-8020. That tail
#     has FOUR call sites and only one is an end-of-statement; if the reference
#     splits "missing" from "malformed", the divergence is one site, not four.
case("x.play.eol",  "pl_syntax/EOL",        "PLAY")
case("x.play.colon","pl_syntax/COLON",      "PLAY:PRINT 1")
case("x.play.comma","pl_syntax/comma",      'PLAY ,"E"')
case("x.play.ok",   "pl_syntax/ctl",        'PLAY "E"', "PRINT 1")

# 🔴 x.paint4pt AS FIRST WRITTEN COULD NOT REACH ITS OWN CASE. The POINT read sat
#    on a line AFTER the PAINT, and a TRAPPED error jumps straight to the handler
#    -- so that line never runs and every side printed the trapped ERR instead of
#    a pixel. The read has to happen IN THE HANDLER, which is exactly how
#    basic_probe_lineerr.py captures GRPACX/GRPACY. Same fixture, handler moved.
case("x.pt4.ord", "ep_syntax/order",
     "SCREEN 2", "PAINT(10,10),9,15,",
     handler='900 V=POINT(10,0):SCREEN 0:PRINT"[";ERR;V;"]":END')
case("x.pt4.ctl", "ep_syntax/order-ctl",   # an ERR 2 from the SAME tail whose
     "SCREEN 2", "PUT SPRITE 0",           # statement paints nothing: V must be 4
     handler='900 V=POINT(10,0):SCREEN 0:PRINT"[";ERR;V;"]":END')

# 🎯 THE SWAP SEPARATOR. `SWAP A,B,C` is ERR 5 with all three UNDEFINED and ERR 2
#    with all three DEFINED, so the doc's row agrees for a reason that is not the
#    third operand at all. Which name decides it -- the SECOND (whose absence has
#    its own measured ERR 5, `A=1:SWAP A,B`) or the THIRD?
case("x.swap.bdef", "sw_illegal/B-defined", "A=1:B=2", "SWAP A,B,C")   # C undefined
case("x.swap.cdef", "sw_illegal/C-defined", "A=1:C=3", "SWAP A,B,C")   # B undefined

BR = re.compile(r"\[([^\]]*)\]")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = BR.search(cap)
    if m:
        return " ".join(m.group(1).split()) or "<empty>"
    return "<NO OUTPUT>"


def main() -> int:
    want = sys.argv[1:] or list(CASES)
    bad = [w for w in want if w not in CASES]
    if bad:
        print(f"unknown case(s): {bad}", file=sys.stderr)
        return 2
    step = float(os.environ.get("DUPSPAN_STEP", "4.0"))
    for label in want:
        body = ["10 ON ERROR GOTO 900"]
        body += [f"{20+10*k} {ln}" for k, ln in enumerate(CASES[label])]
        body += ['890 SCREEN 0:PRINT"[NONE]":END',
                 HANDLER.get(label, '900 SCREEN 0:PRINT"[ERR";ERR;"]":END')]
        row = {}
        for side, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=step, cap_gap=10.0,
                timeout=300.0)
            row[side] = face(caps[0])
            print(f"  {side:7s} {label:11s} -> {row[side]!r}   [{SITE[label]}]",
                  flush=True)
            if os.environ.get("DUPSPAN_RAW"):
                print("      RAW " + repr((caps[0] or "")[-400:]), flush=True)
        if "vg8020" in row and "cf3300" in row:
            agree = "refs-agree" if row["vg8020"] == row["cf3300"] else "REFS DIFFER"
        else:
            agree = "one-ref-only" if len(row) > 1 or "zb" not in row else "zb-only"
        ref = row.get("vg8020", row.get("cf3300"))
        if "zb" not in row:
            zbm = "zb=<not run>"
        elif ref is None:
            zbm = "zb=<no ref this round>"
        else:
            zbm = "zb=" + ("same" if row["zb"] == ref else "DIFF")
        print(f"  ROW {label:11s} {agree:12s} {zbm}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
