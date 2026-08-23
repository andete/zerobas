# D-HIMDOM — predictions, written BEFORE the sweep returned

Baseline `649b548`, ROMs `f1e743c2` / `490ffc49` / `5293b7c7`, main page 1
**5 B free** (2026-08-23).

## The hypothesis I am testing, and why D-CLRFIX could not

D-CLRFIX justified `get_int16_checked` in the HIMEM slot with row `q.ovf`
(`CLEAR 200,70000` → ERR 6 on both references). **70000 is rejected under both
candidate rules**, so the row cannot separate them:

* **(a) SIGNED int16** — legal is −32768..32767; anything else ERR 6.
* **(b) ADDRESS domain** — legal is −32768..65535 (the MSX convention `POKE`
  uses, `eval_addr` / `fac_to_int_addr`), ERR 6 only past that; **plus** a RAM
  range check raising ERR 5 inside it.

`&HD000` passes under (a) only by accident: MSX BASIC reads a hex literal
≥ `&H8000` as NEGATIVE (−12288), so `|x| <= 32767` without the value ever being
"small". A **decimal** in [32768, 65535] is the discriminator and no shipped row
contains one.

## PREDICTION — I expect (b), which means **I shipped a regression**

`CLEAR 200,-1` is ERR **5** (Illegal function call), not ERR 6. Under (a) a
16-bit-overflow answer would be ERR 6; ERR 5 is a *domain* answer, which says
the value converted fine and was then refused for WHERE it points. That is only
coherent if the coercion is wider than int16.

| row | arg | PREDICTED refs | PREDICTED zb | |
|---|---|---|---|---|
| `d.50000` | `50000` | **`0 50000`** accepted | **`6 …`** | 🔴 **REGRESSION** |
| `d.40000` | `40000` | `0 40000` | `6 …` | 🔴 regression |
| `d.32768` | `32768` | `0 32768` | `6 …` | 🔴 regression |
| `d.32767` | `32767` | `0 32767` | `0 32767` | in-range twin, agrees |
| `d.65535` | `65535` | `5 …` (above RAM top) | `6 …` | both reject, DIFFERENT CODE |
| `d.65536` | `65536` | `6 …` | `6 …` | agrees |
| `d.70000` | `70000` | `6 …` | `6 …` | CONTROL, measured |
| `d.hffff` | `&HFFFF` | `5 …` — **same as `d.neg1`** | `0 65535` | the syntax discriminator |
| `d.neg1`  | `-1`     | `5 …` | `0 65535` | CONTROL, measured |
| `d.h8000` | `&H8000` | ? | ? | LOW CONFIDENCE |
| `d.hd000` | `&HD000` | `0 53248` | `0 53248` | CONTROL, accepted |
| `d.zero`  | `0` | ? | ? | LOW CONFIDENCE |
| `d.one`   | `1` | ? | ? | LOW CONFIDENCE |
| `d.h4000` | `&H4000` | ? (16384, inside ROM) | `0 16384` | LOW CONFIDENCE |
| `d.h8050` | `&H8050` | `0 32848` | `0 32848` | the array fixtures' ceiling |

🎯 **`d.hffff` vs `d.neg1` is the sharpest row.** Same sixteen bits, different
surface syntax. If both answer ERR 5 the rule is about the VALUE; if they differ
the rule is about the evaluated float's sign and my whole model is wrong.

⚠️ **THE REFERENCES MAY LEGITIMATELY DISAGREE** on the ERR-5 rows: HIMEM boots at
62336 on the VG-8020 and **56951** on the CF-3300 (its disk ROM takes RAM). If
the rule is "≤ this machine's RAM top", a value between those two is accepted on
one and refused on the other. The probe prints that as *"read the rule, not the
row"* rather than as an apparatus fault. **No row here sits in that window on
purpose** — 50000 is below both — but `d.hffff`/`d.neg1` at 65535 are above both.

## If the prediction holds, the fix is ALREADY IN THE TREE

`basic/poke.asm` uses `call eval_addr` — `eval` + `fac_to_int_addr`, exactly the
−32768..65535 rule — and then tests `FPERR` itself, because `eval_addr` DEFERS.
So `clr_himem` becomes:

    call eval_addr           ; 3 B   the ADDRESS domain, ERR 6 only past 65535
    call check_expr_errors   ; 3 B   raise BEFORE the store and the wipe
    ld   (HIMEM),de

**+3 B against 5 B free.** The ERR-5 range check is a SEPARATE question and is
not in that price.

## What I got wrong to get here, stated plainly

D-CLRFIX's `q.ovf` is a case where two candidate rules COINCIDE, and I built on
it without asking what else would make it green — the exact standing rule in
[[a-case-that-agrees-can-agree-for-the-wrong-reason]], applied to my own fix
within the hour of writing that reference into the slice report.
