#!/usr/bin/env python3
r"""D-CTLSTACK -- WHERE is the reference's control stack, asked of the ORACLE.

THE QUESTION, and it is Joost's: D-STACKPOOL (spec-basic-trapsvc.md §11)
concluded "the references use the GENERIC stack" from DEPTH alone -- ~4080
frames, 7.0 B/frame, linear in `CLEAR`, and the two machines agreeing exactly
once HIMEM is pinned. That is an inference from a behaviour. It never asked the
machine where the stack IS.

🎯 AND MSX PUBLISHES THE ANSWER, so the inference can be replaced by a reading.
The system variables are documented (MSX2 Technical Handbook / MSX Assembly Page
`map.grauw.nl`; this project already names them in basic/sysvars.inc:951 and
:1561), and BASIC can PEEK them:

    MEMSIZ  $F672   highest address BASIC may use          (what `CLEAR n,addr` sets)
    STKTOP  $F674   top of the STACK                       (the subject)
    STREND  $F6C6   end of the variable/array area         (the other side of the gap)
    FRETOP  $F69B   string-space allocation pointer

⚠️ THIS IS RAM READ THROUGH `PEEK`, NOT A DISASSEMBLY. The machines are used as
oracles exactly as everywhere else in this project: documented addresses in,
observed values out. No ROM code is decoded and no internal layout is lifted --
the rows below deliberately ask WHERE and HOW BIG, never "what does a frame look
like", because the answer to that would be an implementation to copy rather than
a contract to meet.

WHAT EACH ROW DECIDES

  o.base     the four pointers, no `CLEAR` -- the baseline the others move from
  o.clr2200  🎯 does `CLEAR 2200` LOWER STKTOP by 2000? If the stack top is
             bounded by the string space, it must. A stack somewhere else cannot
             move at all, and the +2000 B / -286 frames from §11 would then need
             some other explanation.
  o.clr4200  the same step again -- linear, or a coincidence
  o.himem    does `CLEAR 200,&HC000` set MEMSIZ to 49152, and pull STKTOP with it
  o.gap      🎯 THE ARITHMETIC ROW, and the one that closes it. Read STKTOP and
             STREND, THEN recurse to overflow. If control frames live in the gap
             between them, `(STKTOP - STREND) / depth` must come out at the SAME
             ~7 B/frame §11 measured from `CLEAR` alone -- two independent routes
             to one number. If it does not, the frames are somewhere else.

⚠️ NO ROW ARMS `ON ERROR` BEFORE ITS `CLEAR`. `CLEAR` resets the error vector, so
the overflow would go untrapped and the row would read `<NO OUTPUT>` -- the fault
that cost `stackpool_probe.py` a whole first draft.

⚠️ zerobas DEFINES NONE OF THESE CELLS (docs/sysvar-rehoming-decisions.md §3
rejected publishing FRETOP for exactly this reason: only the difference against
MEMSIZ/STKTOP means anything, and zerobas has neither). Its column is whatever
RAM happens to hold and is reported, never read as agreement.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

# The published MSX system variables (see the docstring for the sources).
MEMSIZ, STKTOP, STREND, FRETOP = 0xF672, 0xF674, 0xF6C6, 0xF69B

# A 16-bit read as a subroutine, so no line gets long enough to wrap its echo.
RD = ["100 V=PEEK(A)+256*PEEK(A+1):RETURN"]


def ptr_prog(clr):
    """The four pointers, after an optional CLEAR. `[MEMSIZ STKTOP STREND FRETOP]`."""
    return ([f"5 {clr}"] if clr else []) + [
        "10 CLS",
        f"20 A=&H{MEMSIZ:X}:GOSUB100:M=V",
        f"30 A=&H{STKTOP:X}:GOSUB100:S=V",
        f"40 A=&H{STREND:X}:GOSUB100:E=V",
        f"50 A=&H{FRETOP:X}:GOSUB100:F=V",
        '60 PRINT"[";M;S;E;F;"]":END',
        *RD]


# 🎯 THE ARITHMETIC ROW. STKTOP and STREND are read BEFORE the recursion (the
# recursion creates no variables, so STREND cannot move under it), then the
# machine is driven to control-stack overflow and the depth reported beside the
# gap. `G/D` is the bytes per frame, derived from ADDRESSES rather than from
# CLEAR -- an independent route to §11's 7.0.
GAP = [f"10 A=&H{STKTOP:X}:GOSUB100:S=V",
       f"20 A=&H{STREND:X}:GOSUB100:E=V",
       "30 ONERRORGOTO800",
       "40 D=0",
       "50 GOSUB600",
       '90 CLS:PRINT"[";D;S-E;"]":END',
       "600 D=D+1:GOSUB600",
       "610 RETURN",
       "800 RESUME90",
       *RD]

CASES = [
    ("o.base",    ptr_prog(""),                 "no CLEAR -- the baseline"),
    ("o.clr2200", ptr_prog("CLEAR 2200"),       "+2000 B of string space"),
    ("o.clr4200", ptr_prog("CLEAR 4200"),       "+4000 B -- linear?"),
    ("o.himem",   ptr_prog("CLEAR 200,&HC000"), "MEMSIZ set outright"),
    # 🔴 THE HIMEM ROW CAME BACK 536 B BELOW THE REQUESTED $C000, IDENTICALLY ON
    # BOTH REFERENCES -- so `CLEAR n,addr` does NOT set MEMSIZ to addr. These two
    # rows test the obvious candidate: the FILE BUFFERS are carved off the top
    # first, so MEMSIZ is `addr - MAXFILES*<buffer>`. If MAXFILES moves MEMSIZ by
    # one buffer per file, that is the whole of it -- and it also settles the
    # ⚠️ filed as "MAXFILES=n moves the pool top; measure it before assuming it
    # is benign" (TODO.md, the control-frame-pool arc).
    ("o.mxf2",    ptr_prog("MAXFILES=2:CLEAR 200,&HC000"),
     "one MORE file buffer off the top?"),
    ("o.mxf0",    ptr_prog("MAXFILES=0:CLEAR 200,&HC000"),
     "...and none at all?"),
    ("o.gap",     GAP,                          "depth reached, and STKTOP-STREND"),
]

NUM = re.compile(r"^[-0-9 .E+]+$")


def face(raw):
    for m in re.finditer(r"\[([^\[\]]*)\]", "".join(raw or "")):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split())
    return "<NO OUTPUT>"


def run(side, prog):
    machine, boot, reset = SIDES[side]
    caps = omsx_repl.run_cases(machine, [("r", list(reset) + prog + ["RUN"])],
                               batch=False, reset=(), boot=boot, step=45.0,
                               cap_gap=15.0, timeout=420.0)
    return face(caps[0])


sides = ["vg8020", "cf3300", "zb"]
res = {}
w = max(len(l) for l, _, _ in CASES)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>26}" for s in sides) + "   what it asks")
for lab, prog, why in CASES:
    v = {s: run(s, prog) for s in sides}
    res[lab] = v
    print(f"{lab:<{w}}  " + "  ".join(f"{v[s]:>26}" for s in sides) + f"   {why}")

print("\n  o.base/o.clr*/o.himem read `[MEMSIZ STKTOP STREND FRETOP]`")
print("  o.gap reads `[depth  STKTOP-STREND]`\n")


def nums(v):
    try:
        return [int(float(x)) for x in v.split()]
    except ValueError:
        return None


print("Does CLEAR move STKTOP?  (a stack bounded by the string space must)")
for s in sides:
    b, c2, c4 = (nums(res[l][s]) for l in ("o.base", "o.clr2200", "o.clr4200"))
    if None in (b, c2, c4):
        print(f"  {s:<8} <not readable>")
        continue
    print(f"  {s:<8} STKTOP {b[1]} -> {c2[1]} -> {c4[1]}   "
          f"steps {b[1]-c2[1]:+d} / {c2[1]-c4[1]:+d}")

print("\nDoes CLEAR n,&HC000 set MEMSIZ to 49152 ($C000)?  ...and what does")
print("MAXFILES do to it?  (`CLEAR n,addr` with MAXFILES 1 / 2 / 0)")
for s in sides:
    h, m2, m0 = (nums(res[l][s]) for l in ("o.himem", "o.mxf2", "o.mxf0"))
    if h is None:
        print(f"  {s:<8} <not readable>")
        continue
    line = (f"  {s:<8} MAXFILES 1 -> MEMSIZ {h[0]}  ({0xC000 - h[0]:+d} from $C000)")
    if m2 and m0:
        line += (f"   |  2 -> {m2[0]} ({m2[0]-h[0]:+d})"
                 f"   0 -> {m0[0]} ({m0[0]-h[0]:+d})")
    print(line)

print("\n🎯 Bytes per frame, from ADDRESSES -- does it agree with §11's 7.0?")
for s in sides:
    g = nums(res["o.gap"][s])
    if g is None or len(g) < 2 or g[0] == 0:
        print(f"  {s:<8} <not readable>")
        continue
    print(f"  {s:<8} depth {g[0]:>5}   STKTOP-STREND {g[1]:>6} B   "
          f"=> {g[1]/g[0]:.1f} B/frame")
print("  §11 measured 7.0 B/frame from the CLEAR ladder alone. Two independent")
print("  routes to one number = the frames are in the STKTOP..STREND gap.")
