#!/usr/bin/env python3
r"""D-STACKPOOL — do the references put control frames on the GENERIC stack?

Joost's read of D-TRAPDEPTH: ~4000 frames, nothing reclaimed, and the two
references DISAGREEING WITH EACH OTHER (4071 vs 3302) smells like the Z80 machine
stack growing down from HIMEM rather than a fixed array.

🎯 `CLEAR` IS THE TEST. `CLEAR n` sets the string space and `CLEAR n,addr` sets
HIMEM outright. If control frames and string space come out of ONE pool, the
GOSUB depth must MOVE when that pool is resized -- and the size of the move gives
the bytes per frame. If the depth is unchanged, the frames live in a fixed array
and the hypothesis is refuted.

Reads `[D E]`: D = frames nested before the overflow, E = the ERR that stopped it.

⚠️ Every row re-runs the SAME recursion; only the CLEAR in front of it changes.
`c.base` has no CLEAR at all, so a row that fails to differ from it is telling us
the CLEAR did nothing -- not that the pool is separate.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}
CASES = [
    ("c.base",    "",                 "no CLEAR at all -- the baseline"),
    ("c.clr200",  "CLEAR 200",        "small string space"),
    ("c.clr2200", "CLEAR 2200",       "+2000 bytes of string space"),
    ("c.clr4200", "CLEAR 4200",       "+4000 -- the step must be LINEAR if shared"),
    ("c.himem",   "CLEAR 200,&HC000", "HIMEM lowered outright"),
]
NUM = re.compile(r"^[-0-9 ]+$")


def run(side, clr):
    machine, boot, reset = SIDES[side]
    # 🔴 THE CLEAR MUST COME BEFORE `ON ERROR`. With it after, every CLEAR row
    # read <NO OUTPUT> on ALL THREE machines: CLEAR resets the error vector, so
    # the overflow was untrapped, the program aborted and nothing printed. The
    # probe refused rather than reporting a value -- which is the only reason
    # that read as an instrument fault instead of "CLEAR breaks recursion".
    prog = ([f"5 {clr}"] if clr else []) + ["10 ONERRORGOTO800",
        "20 D=0:E=0",
        "30 GOSUB600",
        '90 CLS:PRINT"[";D;E;"]":END',
        "600 D=D+1:GOSUB600",
        "610 RETURN",
        "800 E=ERR:RESUME90", "RUN"]
    raw = "".join(omsx_repl.run_cases(machine, [("direct", list(reset) + prog)],
                                     batch=False, reset=(), boot=boot, step=45.0,
                                     cap_gap=15.0, timeout=420.0)[0] or "")
    # digits-only, per trapsvc_probe's guard: a run that never reaches its PRINT
    # leaves the ECHO of that line, and `[";D;E;"]` is not a reading.
    for m in re.finditer(r"\[([^\[\]]*)\]", raw):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split())
    return "<NO OUTPUT>"


w = max(len(l) for l, _, _ in CASES)
sides = ["vg8020", "cf3300", "zb"]
res = {}
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides) + "   statement")
for lab, clr, why in CASES:
    v = [run(s, clr) for s in sides]
    res[lab] = v
    print(f"{lab:<{w}}  " + "  ".join(f"{x:>12}" for x in v) + f"   {clr or '(none)':<18} {why}")


def depth(v):
    try:
        return int(v.split()[0])
    except Exception:
        return None


print("\nbytes per frame, if the pool is shared:")
for i, s in enumerate(sides):
    a, b, c = (depth(res[l][i]) for l in ("c.clr200", "c.clr2200", "c.clr4200"))
    if None in (a, b, c):
        print(f"  {s:<8} <not readable>")
        continue
    d1, d2 = a - b, b - c
    f1 = f"{2000/d1:.1f}" if d1 else "--"
    f2 = f"{2000/d2:.1f}" if d2 else "--"
    print(f"  {s:<8} +2000 B costs {d1:>5} frames ({f1} B/frame), "
          f"next +2000 costs {d2:>5} ({f2} B/frame)")
print("  a SHARED pool gives two similar B/frame figures; 0 frames lost = a fixed array")
