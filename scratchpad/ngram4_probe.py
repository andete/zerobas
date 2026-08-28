#!/usr/bin/env python3
r"""D-NGRAM4 — one `shx_tail` for the four sub-ROM string-op result tails.

`call call_strheap / call shx_finish / pop hl / jp str_eval_ok` ended SPACE$,
HEX$/OCT$/BIN$ and STRING$'s two forms. 49 B of sites -> a 13 B body plus four
3 B jumps: -24 B of the LOW region (70 -> 94 B free).

🔴 SAME HAZARD AS D-NGRAM2/3: the risk is a SITE THAT WAS NEVER REWIRED, which
behaves identically. One row per site, and the knife must move all of them.
Site 4 (STRING$'s two-arg form) is the one that guards its cursor with `push ix`
rather than `push hl` and pops it into HL -- byte-identical tail, different
prologue, so it gets its own row rather than being assumed equivalent.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- one row per SITE, on its SUCCESS path (that is what the tail publishes) --
# 🔴 CHR$ IS A SITE OF ITS OWN AND HAD NO ROW UNTIL THE KNIFE SAID SO. The
# sweep reports line numbers; naming the verb from nearby prose put `str_fn_chr`
# down as SPACE$, so one of the four sites went unwitnessed while the row set
# looked complete. Name a site from its ENCLOSING LABEL.
add('s.chr',      [], 'CHR$(65)')                # site str_fn_chr
add('s.chr.n',    [], 'ASC(CHR$(200))')          # same site, a high byte
add('s.space',    [], 'LEN(SPACE$(5))')          # site str_fn_space
# 🔴 NOT `"["+SPACE$(3)+"]"` -- the harness's face() reads the FIRST bracketed
# span, so a literal `[` in the row COLLIDES with its own result fence and the
# answer came back as `[` on all three sides. Consistent, and meaningless.
add('s.space.v',  [], 'ASC(SPACE$(1))')          # same site, the BYTE (32), not the length
add('s.hex',      [], 'HEX$(255)')               # site :1236 (op 6)
add('s.oct',      [], 'OCT$(8)')                 # site :1236 (op 7)
add('s.bin',      [], 'BIN$(5)')                 # site :1236 (op 14)
add('s.string.n', [], 'STRING$(4,65)')           # site :1293 / :1402
add('s.string.c', [], 'STRING$(4,"Z")')          # the char form
add('s.string.s', [], 'STRING$(3,"QRS")')        # first-char-of-string form

# --- 🟢 controls: the string engine at large, and a non-string path ----------
add('g.cat',      ['A$="AB":B$="CD"'], 'A$+B$')
add('g.mid',      ['A$="ABCDE"'],      'MID$(A$,2,3)')
add('ctl.num',    [],                  '1+1')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>20}" for s in sides) + "   verdict")
diff, blind = [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if not same: diff.append(l)
    if "<NO OUTPUT>" in zb or "<NO CAPTURE>" in zb or "SPACE$" in zb or "STRING$" in zb:
        blind.append(l)                     # a blank OR an echo is no reading
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>20}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND (no reading on zb): " + " ".join(blind))
    raise SystemExit(2)
