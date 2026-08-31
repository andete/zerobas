#!/usr/bin/env python3
r"""D-CVITM — `CVI(5)` is `Syntax error` here and `Type mismatch` on the reference.

Filed 2026-08-31 by D-NGRAM15 §6. `ev_ff_cvi` (basic/expr.asm) ends its argument
parse with `jp nc,ev_f_empty` -- a DEFERRED SYNTAX ERROR -- on every way
`str_eval` can decline. Two different causes share that one exit:

  (a) the argument is not a string at all   -- `CVI(5)`
  (b) a NESTED malformed string function    -- `CVI(LEFT$("AB"))`

The reference calls (a) `Type mismatch`. What it calls (b) is the question this
probe exists to answer, because THE ANSWER DECIDES THE FIX: if (b) is also Type
mismatch, one code change does it; if (b) is Syntax error, the two causes have to
be told apart and `str_eval`'s single NC return cannot do that on its own.

⚠️ ONE ORACLE ONLY. `CVI`/`MKI$` are DISK BASIC verbs: the cassette-only VG-8020
answers `Illegal function call` to every form, well-formed or not, so it cannot
arbitrate and is not a side here. Stated rather than silently dropped.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the two causes that share `jp nc,ev_f_empty` ---------------------------
add('a.num',     [], 'CVI(5)')                    # (a) a numeric literal
add('a.numvar',  ['A=5'], 'CVI(A)')               # (a) a numeric variable
add('b.nested',  [], 'CVI(LEFT$("AB"))')          # (b) nested malformed string fn
add('b.nested2', [], 'CVI(MID$("AB"))')           # (b) another one
# --- the other deferred exits from the same routine -------------------------
add('c.noparen', [], 'CVI"AB"')                   # missing '('
add('c.noclose', [], 'CVI("AB"')                  # missing ')'
add('c.empty',   [], 'CVI()')                     # nothing at all
# --- 🟢 the well-formed control, and the SIBLING verb ------------------------
add('g.ok',      [], 'CVI("AB")')
add('g.short',   [], 'CVI("A")')                  # 1-byte string: len < 2
add('m.ok',      [], 'ASC(MKI$(258))')            # MKI$ round-trips
add('m.str',     [], 'MKI$("A")')                 # the INVERSE type error
# --- 🟢 CONTROLS: the shared string-arg path, which is already correct -------
add('ctl.len',   [], 'LEN(5)')
add('ctl.instr', [], 'INSTR("ABCDE",5)')
add('ctl.num',   [], '1+1')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if refs and not same:
        diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs the CF-3300: {len(diff)}/{len(ORDER)}"
      + ("  " + " ".join(diff) if diff else ""))
raise SystemExit(1 if diff else 0)
