<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-DRAWOP — the same shared tail for the THIRD time, and this one is free

Status: **✅ SHIPPED.** 2026-08-26, on `52f81fc`. **8 rows × 3 machines,
references unanimous on all 8, 3 DIFF → 0, at ZERO BYTES.**
`scratchpad/drawop_probe.py` (`drawop_base.out`, `drawop_after.out`).
Predictions pinned in `drawop_predictions.md` before the probe ran once —
**8 of 8 exact.**

The last of the roots D-MISSOP3 found.

---

## 1. 🔴 D-MISSOP3's OWN `DRAW` ROW AGREED AT 5 AND HID THIS

D-MISSOP3 ran `DRAW` and got **5 on all three machines**, which read as *"DRAW
breaks the missing-operand rule"*. It does not: in **SCREEN 0** the mode gate
refuses before the operand is looked at, so the row could not reach the tail
under test at all. `SCREEN2:DRAW` is **24 on both references and was 13 here**.

That was already recorded as a case that agreed for the wrong reason. This slice
is what it opened, and **every row here that must reach the tail says `SCREEN2`
first.**

---

## 2. The site — the same shape D-PUSING and D-MIDOP each split

```
    call    str_eval
    jp      nc,gfx_typeerr      ; DRAW 5 -> Type mismatch (measured)
```

`str_eval` declines both for *"there is nothing here"* and for *"there is
something and it is not a string"*.

⚠️ **THE OLD COMMENT'S `(measured)` WAS TRUE AND NARROW.** `DRAW 5` really is 13
— re-run here as `d.num` and green. What it did not say is that the label it sat
on serves three more shapes, none of which had ever been measured:

| row | statement | refs | before | after |
|---|---|---|---|---|
| `d.none` | `SCREEN2:DRAW` | **24** | 13 | 24 ✅ |
| `d.colon` | `SCREEN2:DRAW:PRINT1` | **24** | 13 | 24 ✅ |
| `d.plus` | `SCREEN2:DRAW+` | **24** | 13 | 24 ✅ |
| `d.num` | `SCREEN2:DRAW 5` | 13 | 13 | 13 ✅ |

🎯 **A `(measured)` ANNOTATION IS A CLAIM ABOUT ONE ROW, NOT ABOUT THE LABEL IT
IS WRITTEN NEXT TO.**

---

## 3. The source's own justification, re-run

`graphics.asm`:876-886 argues in prose that DRAW's mode gate belongs FIRST —
unlike PSET/PRESET/LINE/CIRCLE/PAINT, where D-LINERR moved it DOWN — citing:

> *"`DRAW 5` in SCREEN 0 is ERR 5 on both references while the same statement in
> SCREEN 2 is ERR 13 (rows d.tm0/d.tm2), so the mode is refused BEFORE the
> string expression is evaluated."*

**Both halves re-run and both hold**: `d.scr0num` is **5** in SCREEN 0 and
`d.num` is **13** in SCREEN 2. The prose was right, and it is now right *and*
re-checkable from this slice's own row set rather than from a doc two arcs back.

---

## 4. The fix — 0 B, and `d.plus` is why it is a DELEGATION

```
    jp nc,gfx_typeerr   ->   jp nc,els_tc_common
```

Both walls unchanged (**low 39 B, page 1 89 B**); `basic-reloc.rom`
`a19e1637` → `350db281`; **`sub.rom` UNMOVED** at `33ba143a`.

🎯 **THAT IS THE FIRST INDEPENDENT CONFIRMATION OF D-MIDOP §5.1's RULE** — *a
main low-region edit moves `sub.rom` iff it changes SIZE*. This edit is
size-neutral and the generated resident ABI did not move.

⚠️ **AN EOL/`:` PEEK WOULD HAVE BEEN WRONG HERE, EXACTLY AS AT MID$.**
`SCREEN2:DRAW+` is **24**, and `+` is neither end-of-line nor `:`. The question
is *"can a FACTOR start here"*, which is `ev_f`'s — so ask `els_tc_common`, which
evaluates the operand numerically and lets `check_expr_errors` decide. Nothing is
pushed at this point, so this is the case `basic/files.asm`:732 calls *"this
caller has none to pop, so it enters at the common label directly"*, and
`gfx_typeerr` keeps its four other callers (`:724`, `:936`, `:1065`, `:1370`).

**Three verbs, one rule, three different fix costs** — D-PUSING −6 B (a carve),
D-MIDOP +6 B (a fourth pop-and-enter), D-DRAWOP 0 B. The rule is shared; the
price is a property of each site's stack and neighbourhood.

---

## 5. 🔬 Knives

`scratchpad/drawop_knives.py` / `drawop_knives.out`. K-DR1 reverts the
delegation. **K-DR2 deletes the mode gate**, to show §3's ordering is
LOAD-BEARING rather than incidental: with no gate the SCREEN-0 rows reach the
operand check and stop being ERR 5.

---

## 6. What this does NOT establish

* `d.plus` uses `+`. **Other bytes that cannot start a factor are not swept** —
  the claim is that `els_tc_common` answers for all of them, and it is tested by
  one.
* `DRAW` inside a `DRAW` sub-command string (the `X` command's recursion,
  `GFX_DRESUME`) is untouched.
* The four other `gfx_typeerr` callers were **counted, not measured**. Each may
  have the same two-meanings problem; none has rows here.
