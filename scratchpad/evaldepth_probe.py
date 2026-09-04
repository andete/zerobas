#!/usr/bin/env python3
r"""D-EVALDEPTH -- does the EVALUATOR's own nesting come out of the same pool?

WHY THIS DECIDES SOMETHING. D-CTLFRE (spec-basic-trapsvc.md §15) showed the
reference's GOSUB and FOR frames come out of the memory `FRE(0)` reports, 7 B and
25 B a level. But the reference keeps its frames on the GENERIC Z80 stack, and
that stack carries the interpreter's OWN recursion too -- nested function calls,
nested parentheses, a `DEF FN` calling a `DEF FN`. If those also come out of that
pool, then on the reference `CLEAR` bounds BOTH depths with one number.

🎯 AND THAT IS THE ARGUMENT THAT SEPARATES THE TWO CANDIDATE DESIGNS. A software
pointer running down from `varceil` moves only the CONTROL frames into the pool;
the Z80 `SP` stays where C-BIOS left it (`$F380`, ~870 B), so evaluator depth
keeps a SECOND, separate limit that `CLEAR` cannot move. Relocating `SP` --
the reference's actual mechanism -- would fix both with one change. Whether that
matters is exactly what these rows measure.

THE INSTRUMENT is a CHAIN OF `DEF FN`s, because it is the one evaluator recursion
whose depth is countable from BASIC: `FNE` calls `FND` calls ... calls `FNA`, and
`FNA`'s body is `FRE(0)`. Reading `FNA(0)` measures FRE at ONE level and
`FNE(0)` at FIVE, so the difference is four levels of evaluator nesting and
nothing else -- same program, same variables, same line.

⚠️ `FNA`'s body must be `FRE(0)` and NOT a variable, or the chain measures a
lookup rather than a depth. And every variable is created before the first read,
for the reason `basic_probe_clearpool.py` gives: `FRE(0)` falls when a new
variable is allocated, so an allocation between the two reads would be counted as
nesting.

⚠️ EVERY ROW ARMS `ON ERROR` AND REPORTS `E`. A machine that cannot build the
chain at all (no `DEF FN`, a formal-count ceiling, a nesting cap) must say WHICH,
not read `<NO OUTPUT>` -- the fault D-CTLFRE's first cut had
[[an-unnamed-outcome-reads-as-no-outcome]].
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

_LINK = {"B": "A", "C": "B", "D": "C", "E": "D"}


def defs_only(n):
    """🎯 THE SEPARATING CONTROL, and without it this probe cannot name what it
    found. `e.fn4` DEFINES five functions and NESTS four of them, so its ERR 7 on
    zerobas has TWO sufficient causes -- a nesting-depth cap and a
    definition-COUNT cap -- and they coincide on every row above. This defines
    the same five and calls only `FNA`, i.e. depth ONE. Still ERR 7 => the limit
    is on DEFINITIONS. Clean => it is on DEPTH.
    [[two-rules-that-coincide-on-every-row-you-have]]"""
    names = ["A", "B", "C", "D", "E"][:n]
    defs = ["20 DEFFNA(X)=FRE(0)"]
    for i, nm in enumerate(names[1:], start=3):
        defs.append(f"{i * 10} DEFFN{nm}(X)=FN{_LINK[nm]}(X)")
    return ["10 ONERRORGOTO900",
            "15 P=0:Q=0:E=0",
            *defs,
            "70 P=FNA(0)",
            "80 Q=FNA(0)",
            '90 CLS:PRINT"[";P-Q;E;"]":END',
            "900 E=ERR:RESUME90"]


def chain(deep):
    """FNA's body is FRE(0); FNB..FN<deep> each call the one below. P reads at
    ONE level and Q at `deep` levels, so P-Q is (levels-1) of evaluator nesting.
    ⚠️ Parameterised because zerobas raises ERR 7 somewhere in this chain and a
    single depth-5 row cannot say WHERE -- an outcome needs a number."""
    names = ["A", "B", "C", "D", "E"]
    top = names[names.index(deep)]
    defs = ["20 DEFFNA(X)=FRE(0)"]
    for i, n in enumerate(names[1:names.index(deep) + 1], start=3):
        defs.append(f"{i * 10} DEFFN{n}(X)=FN{_LINK[n]}(X)")
    return ["10 ONERRORGOTO900",
            "15 P=0:Q=0:E=0",
            *defs,
            "70 P=FNA(0)",
            f"80 Q=FN{top}(0)",
            '90 CLS:PRINT"[";P-Q;E;"]":END',
            "900 E=ERR:RESUME90"]

# The PARENTHESIS axis -- a different evaluator recursion, in case DEF FN has a
# mechanism of its own. `FRE(0)` read bare, then inside eight nested parens.
def parens(n):
    """🔴 THE FIRST CUT HAND-COUNTED THIS AND GOT IT WRONG -- eight closes where
    NINE are needed, because `FRE(0)` contributes one of its own. All three sides
    read ERR 2 and a huge delta (Q was never assigned, so P-Q is P: a large,
    entirely plausible wrong number). Built rather than typed now, and the ERR
    column is what caught it."""
    return ["10 ONERRORGOTO900",
            "15 P=0:Q=0:E=0",
            "20 P=FRE(0)",
            f"30 Q={'(' * n}FRE(0){')' * n}",
            '90 CLS:PRINT"[";P-Q;E;"]":END',
            "900 E=ERR:RESUME90"]

# 🎯 THE CONTROL THAT MAKES THE OTHER TWO READABLE. Same program shape, but the
# two reads are at the SAME depth -- so it must read 0 everywhere. A machine that
# reads non-zero here has some per-read drift and its other rows are not deltas.
CTL = ["10 ONERRORGOTO900",
       "15 P=0:Q=0:E=0",
       "20 DEFFNA(X)=FRE(0)",
       "30 P=FNA(0)",
       "40 Q=FNA(0)",
       '90 CLS:PRINT"[";P-Q;E;"]":END',
       "900 E=ERR:RESUME90"]

CASES = [
    ("e.ctl",    CTL,          "CONTROL: both reads at the SAME depth -- must be 0"),
    ("e.fn1",    chain("B"),   "ONE extra DEF FN level"),
    ("e.fn2",    chain("C"),   "two extra levels"),
    ("e.fn3",    chain("D"),   "three extra levels"),
    ("e.fn4",    chain("E"),   "four extra levels"),
    # 🎯 defines the SAME five functions as e.fn4 but calls only FNA (depth 1)
    ("e.def5",   defs_only(5), "SEPARATOR: 5 definitions, depth ONE"),
    ("e.paren8", parens(8),    "eight nested parentheses"),
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
    print(f"{lab:<{w}}  " + "  ".join(f"{v[s]:>12}" for s in sides) + f"   {why}{tag}")

print("\nreads `[FRE(0)@shallow - FRE(0)@deep   ERR]`")
print("  >0 -> the EVALUATOR's own nesting comes out of the FRE(0) pool too,")
print("        so on that machine CLEAR bounds evaluator depth as well")
print("  0  -> the evaluator recurses somewhere FRE(0) cannot see\n")

for s in sides:
    c = res["e.ctl"][s]
    ok = c.split()[:1] == ["0"]
    print(f"  {s:<8} control {c:>10}  "
          + ("ok" if ok else "🔴 NOT ZERO -- the other rows are not deltas"))

print("\nbytes per DEF FN level  (a row that raised is named, never averaged):")
for s in sides:
    bits = []
    for lab, lv in (("e.fn1", 1), ("e.fn2", 2), ("e.fn3", 3), ("e.fn4", 4)):
        v = res[lab][s].split()
        try:
            d, e = int(float(v[0])), int(float(v[1]))
        except (ValueError, IndexError):
            bits.append(f"{lab}=<unreadable>")
            continue
        bits.append(f"{lab}={d}" + (f" B ({d/lv:.1f}/level)" if e == 0
                                    else f" 🔴 ERR {e}"))
    print(f"  {s:<8} " + "   ".join(bits))

print("\nDEPTH cap or DEFINITION-COUNT cap?  e.def5 defines the same five")
print("functions as e.fn4 but nests only ONE:")
for s_ in sides:
    d5, f4 = res["e.def5"][s_], res["e.fn4"][s_]
    try:
        e5, e4 = int(float(d5.split()[1])), int(float(f4.split()[1]))
    except (ValueError, IndexError):
        print(f"  {s_:<8} <unreadable>")
        continue
    if e4 == 0:
        verd = "no cap reached at all"
    elif e5 == e4:
        verd = f"🔴 DEFINITION COUNT -- five definitions alone raise ERR {e5}"
    else:
        verd = f"🔴 NESTING DEPTH -- five definitions are fine (ERR {e5}), the DEPTH is not"
    print(f"  {s_:<8} e.def5 {d5:>10}   e.fn4 {f4:>10}   {verd}")
