#!/usr/bin/env python3
r"""D-CTLFRE -- does FRE(0) COUNT DOWN as you nest? The claim, finally run.

WHY. D-CTLSTACK (spec-basic-trapsvc.md §14) showed the references keep control
frames in the STKTOP..STREND gap -- the same gap FRE(0) reports the free space
of. So on the reference, nesting a GOSUB should visibly SHRINK FRE(0), at the
measured ~7 B per frame. zerobas keeps its frames in a fixed page-3 array and its
Z80 SP at C-BIOS's $F380, neither of which is in that gap, so its FRE(0) should
not move at all.

🔴 THIS HAS BEEN ASSERTED TWICE IN THIS ARC AND RUN ZERO TIMES.
`basic_probe_clearpool.py`'s docstring records the reference behaviour in
passing -- *"FRE(0) counts down to SP at ~6 bytes per nesting level"* -- and then
CANCELS IT OUT by reading every pair at equal depth, which is right for what that
probe measures and is exactly why the divergence has never been looked at. A
justification parenthesis is the part nobody ran
[[a-justification-parenthesis-is-an-unrun-claim]].

THE READING is `[A-B]`: FRE(0) at top level minus FRE(0) at depth N. A machine
whose control frames are in the FRE(0) gap reads ~7*N; a machine whose frames are
elsewhere reads 0.

⚠️ EVERY VARIABLE IS CREATED BEFORE THE FIRST READ. FRE(0) falls when a new
variable is allocated, so a row that creates one between its two reads is
measuring the allocation, not the nesting -- the equal-depth discipline
`basic_probe_clearpool.py` states for its own pairs, applied to the other axis.

⚠️ ONLY THE DEEPEST LEVEL MAY TAKE THE READING. `D` is never decremented, so the
obvious `IF D=N THEN B=FRE(0)` re-reads at EVERY level on the way out and the
last write is the SHALLOWEST one -- the reading would then be ~0 on all three
and would agree for the wrong reason. The recursion arm ends in `GOTO` past the
read instead.
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


# 🔴 EVERY ROW ARMS `ON ERROR` AND REPORTS `E`, AND THAT IS NOT DECORATION.
# Without it zerobas read `<NO OUTPUT>` on three of four rows -- it caps GOSUB at
# 8, so depth 10 raises ERR 7 UNTRAPPED, the program aborts and the fence is
# never printed. A non-reading and "the machine cannot reach this depth" are
# different facts and one of them is the finding
# [[an-unnamed-outcome-reads-as-no-outcome]]. ⚠️ There is no `CLEAR` anywhere in
# this file, so arming the handler on line 5 is safe (a CLEAR would reset it).
ERRTAIL = ["900 E=ERR:RESUME40"]


def gosub_prog(n):
    return ["5 ONERRORGOTO900",
            "10 A=0:B=0:D=0:E=0",
            "20 A=FRE(0)",
            "30 GOSUB100",
            '40 CLS:PRINT"[";A-B;E;"]":END',
            # ⚠️ the THEN arm carries BOTH statements, so only the deepest level
            # (where the IF is false) falls through to the read on line 110.
            f"100 D=D+1:IFD<{n}THENGOSUB100:GOTO120",
            "110 B=FRE(0)",
            "120 RETURN", *ERRTAIL]


def for_prog(n):
    """The FOR axis. A FOR frame is a different size from a GOSUB frame on every
    machine, so this is not a duplicate row -- it says whether BOTH kinds of
    control frame come out of the FRE(0) gap or only one."""
    return ["5 ONERRORGOTO900",
            "10 A=0:B=0:I=0:D=0:E=0",
            "20 A=FRE(0)",
            "30 GOSUB100",
            '40 CLS:PRINT"[";A-B;E;"]":END',
            f"100 D=D+1:FORI=1TO1:IFD<{n}THENGOSUB100:GOTO120",
            "110 B=FRE(0)",
            "120 NEXTI:RETURN", *ERRTAIL]


CASES = [
    ("f.g0",  gosub_prog(1),  "GOSUB depth 1 -- the floor"),
    ("f.g10", gosub_prog(10), "GOSUB depth 10"),
    ("f.g20", gosub_prog(20), "GOSUB depth 20 -- must be ~2x f.g10 if linear"),
    ("f.n10", for_prog(10),   "10 nested GOSUB+FOR pairs"),
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
                               batch=False, reset=(), boot=boot, step=20.0,
                               cap_gap=10.0, timeout=300.0)
    return face(caps[0])


sides = ["vg8020", "cf3300", "zb"]
res = {}
w = max(len(l) for l, _, _ in CASES)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides) + "   what it asks")
for lab, prog, why in CASES:
    v = {s: run(s, prog) for s in sides}
    res[lab] = v
    tag = "" if v["vg8020"] == v["cf3300"] else "   🔴 REFS SPLIT"
    print(f"{lab:<{w}}  " + "  ".join(f"{v[s]:>12}" for s in sides)
          + f"   {why}{tag}")

print("\nreads `[FRE(0)@top - FRE(0)@depth N   ERR]`  (ERR 0 = it got there)")
print("  ~7*N  -> the control frames come out of the SAME memory FRE(0) reports")
print("  0     -> they are somewhere else entirely\n")


def num(v):
    """The DELTA, or None when the row reports an ERR -- a machine that could not
    REACH the depth has not measured a delta, and `A-B` there is A (B was never
    written), which is a big plausible number and the worst kind of wrong."""
    try:
        d, e = (int(float(x)) for x in v.split())
    except ValueError:
        return None
    return d if e == 0 else None


def why_blank(v):
    try:
        return f"ERR {int(float(v.split()[1]))}"
    except (ValueError, IndexError):
        return "no reading"


print("bytes per GOSUB level, from FRE(0):")
for s in sides:
    a, b, c = (num(res[l][s]) for l in ("f.g0", "f.g10", "f.g20"))
    if None in (a, b, c):
        bad = [l for l in ("f.g0", "f.g10", "f.g20") if num(res[l][s]) is None]
        print(f"  {s:<8} COULD NOT REACH: " + ", ".join(
            f"{l} ({why_blank(res[l][s])})" for l in bad)
            + "  <- the depth cap IS the outcome, not a missing reading")
        continue
    # marginal, so the fixed cost of the outermost call cancels
    d1 = (b - a) / 9 if b != a else 0.0
    d2 = (c - b) / 10 if c != b else 0.0
    print(f"  {s:<8} depth 1/10/20 cost {a:>6} {b:>6} {c:>6} B   "
          f"marginal {d1:.1f} then {d2:.1f} B/level"
          + ("   <- FLAT: not in this pool" if a == b == c else ""))
