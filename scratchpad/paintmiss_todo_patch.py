#!/usr/bin/env python3
"""D-PAINTMISS: close the PAINT dangling-comma item in TODO.md."""
import os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
p = "TODO.md"
s = open(p).read()

OLD_PTR = """        proving those rows can go red. **PAINT is the same defect and is OPEN
        below.**
"""
NEW_PTR = """        proving those rows can go red. ✅ **PAINT WAS THE SAME DEFECT AND IS
        CLOSED 2026-08-23 (D-PAINTMISS, 3 B, below).**
"""
assert s.count(OLD_PTR) == 1, "pointer anchor"
s = s.replace(OLD_PTR, NEW_PTR)

OLD = """- [ ] 🔴 **PAINT HAS CIRCLE'S DANGLING-COMMA DEFECT, MEASURED — AND UNLIKE
      CIRCLE IT IS BYTE-BLOCKED.** Filed 2026-08-23 by D-CIRCMISS §7
      (`scratchpad/circmiss_siblings.py`, 9 rows x 3 machines). `PAINT(50,50),`
      and `PAINT(50,50),:A=1` are **`24` and no fill on both references** and
      **`0` + a filled region here** — the same mechanism, at
      [`basic/graphics.asm`](basic/graphics.asm)'s `ep_default_b`, reached from
      **two** slots (:708 the colour field, :727 the B field) on two terminators
      each = **4 jumps**. ✅ **ALL SIX ROWS NOW MEASURED (D-CLRTRAP,
      [`docs/spec-basic-clrtrap.md`](docs/spec-basic-clrtrap.md) §2,
      `scratchpad/circmiss_sib2.py`): 6 DIFF, and the 4 trap rows are
      unanimous.** `p.cc` / `p.kcc` (`PAINT(50,50),,`) prove the B slot is
      reached by BOTH its routes. 💰 **PAINT's grammar is MAIN page 1, 4 B free
      on 2026-08-23** — a `cpt_err24`-shaped raiser needs a carve or a
      promotion, which CIRCLE's sub page 1 (1617 B free on 2026-08-23) did not.
      ⚠️ Shape is not a verdict, which is why all six were RUN: D-LINERR measured
      LINE's box slot as ERR **2** one field past a slot that is 24, and `p.cc`
      was predicted LOW CONFIDENCE for exactly that reason before it came back
      `24`.
"""

NEW = """- [x] ✅ **CLOSED 2026-08-23 — PAINT'S DANGLING COMMA RAISES ERR 24 AND NO
      LONGER FILLS** (D-PAINTMISS,
      [`docs/spec-basic-paintmiss.md`](docs/spec-basic-paintmiss.md)). Filed
      2026-08-23 by D-CIRCMISS §7, measured in full by D-CLRTRAP §2, fixed here.
      💰 **3 B of MAIN page 1 — free 4 B → 1 B**, both read from a clean
      `make basic-reloc` on 2026-08-23. `basic-reloc.rom` `abfefa7f → 59f0a082`
      and the merged image `a8173c25 → 5ea13c71`; **`sub.rom` unchanged at
      `490ffc49`** — the right signature for a `basic/*.asm` edit and the exact
      OPPOSITE of D-CIRCMISS's.
      🎯 **THE FIX IS ONE NEW LABEL AND FOUR RETARGETED `jr`s.**
      [`basic/graphics.asm`](basic/graphics.asm) `ep_missing: jp loc_missing`
      (3 B — `loc_missing` ALREADY EXISTED, the same label `wid_missing`
      forwards to), plus four `jr z,ep_default_b` → `jr z,ep_missing` at **0 B,
      same instruction**. A trampoline beats both alternatives *because* the
      sites are `jr`s: an inline `ld a,24 / jp raise_error` is 5 B and four
      `jp z,loc_missing` is +4 B.
      🔴 **`ep_default_b` IS A SHARED TAIL WITH SIX JUMPS AND ONLY FOUR MEAN
      THIS** — the property is *a comma has already been consumed*, not the slot
      and not the terminator. The other two (`PAINT(x,y)` with no comma at all,
      `PAINT(x,y),15` with no `,B`) are the LEGITIMATE omissions and must keep
      painting. Enumerated as INSTRUCTIONS, never by grepping the symbol.
      📏 **16 rows × 3 machines, 6 DIFF → 0** (`scratchpad/paintmiss_after.out`);
      all ten PAINT rows unanimous. **6/6 knives EXACT**
      (`scratchpad/paintmiss_knives.out`): K-PM1/K-PM2 each point ONE legitimate
      exit at the new raiser and redden exactly one green row — that is what
      makes the trap rows detectors; K-PM4 reverts ONE instruction and moves TWO
      rows, which is the dynamic proof that the B slot is reached by both of its
      routes; K-PM5 is the only knife that reddens `p.omit`, and 🔴 **its
      obvious first draft could not have been run at all** — pointing
      `jr z,ep_c_empty` at the raiser orphans that label, fails `make deadcode`
      and builds no ROM, so the cut had to be a VALUE (`inc hl` → `nop`).
      ⚠️ **NOT extended by analogy to anything unrun.** The `cp ','` arm three
      lines below is a FOURTH argument and is ERR 2 (D-PAINTBORD `od2.b16c`);
      `basic/screen.asm`'s three `clr_apply` sites have the identical shape and
      are CORRECT. All six PAINT slots were RUN.
      💰 **AND IT LEAVES MAIN PAGE 1 AT 1 B FREE (2026-08-23).** The next main
      page-1 slice needs a carve or a promotion into the page-0 low region
      (10 B free, 2026-08-23) BEFORE it writes a byte — see the D-MISSOPFIX
      promotion of `basic/title.asm` for the shape. **Read the wall, never this
      line: `make basic-reloc` prints all four.**
"""
assert s.count(OLD) == 1, "PAINT item anchor"
s = s.replace(OLD, NEW)
open(p, "w").write(s)
print("TODO.md patched")
