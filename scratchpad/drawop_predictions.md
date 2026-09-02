# D-DRAWOP — predictions, PINNED BEFORE THE PROBE RAN

2026-08-26, on `52f81fc`. Walls: main p0 low **39 B**, main p1 **89 B**.

## 0. The filed claims, which are what gets run first

`basic/graphics.asm`:876-886 justifies putting the mode gate FIRST at DRAW, in
prose, with two measured-sounding claims:

> *"`DRAW 5` in SCREEN 0 is ERR 5 on both references while the same statement in
> SCREEN 2 is ERR 13 (rows d.tm0/d.tm2), so the mode is refused BEFORE the
> string expression is evaluated."*

Both get a row. D-MISSOP3 separately measured `SCREEN2:DRAW` at **24 / 24 / 13**.

## 1. The site — the SAME shared tail for the THIRD time

```
    call    str_eval
    jp      nc,gfx_typeerr      ; DRAW 5 -> Type mismatch (measured)
```

`str_eval` declines both for *"there is nothing here"* and for *"there is
something and it is not a string"*. D-PUSING and D-MIDOP each split this exact
shape, and the references answered **24** and **13** both times.

🎯 **AND HERE THE RETARGET LOOKS FREE.** Nothing is pushed at this point
(`ex_draw` is a statement handler and every call so far is balanced), so
`jp nc,els_tc_common` is the same instruction with a different target — the case
`basic/files.asm`:732 describes as *"this caller has none to pop, so it enters at
the common label directly"*. **0 B, if the rows agree.**
⚠️ `gfx_typeerr` keeps four other callers (`:724`, `:936`, `:1065`, `:1370`), so
retargeting this one orphans nothing.

## 2. Row-by-row

| row | statement | refs | zb | what it asks |
|---|---|---|---|---|
| `d.none` | `SCREEN2:DRAW` | **24** | 13 🔴 | D-MISSOP3's row |
| `d.colon` | `SCREEN2:DRAW:PRINT1` | **24** | 13 🔴 | same site, `:` terminator |
| `d.plus` | `SCREEN2:DRAW+` | **24** | 13 🔴 | a stray operator — the row that broke D-PUSING's shape at MID$ |
| `d.num` | `SCREEN2:DRAW 5` | 13 | 13 ✅ | **the source's own claim** |
| `d.scr0` | `DRAW` *(SCREEN 0)* | 5 | 5 ✅ | the mode gate outranks the operand |
| `d.scr0num` | `DRAW 5` *(SCREEN 0)* | 5 | 5 ✅ | **the source's other claim** |
| `d.ok` | `SCREEN2:DRAW"R10"` | 0 | 0 ✅ | control |
| `d.var` | `SCREEN2:A$="R10":DRAW A$` | 0 | 0 ✅ | control — D-DRAWERR's own row |

**Predicted: 8 scored, 3 DIFF.**

## 3. The rule being predicted, and its third out-of-sample test

> **A required operand that ENDS where a value was needed is 24; one PRESENT but
> of the wrong type is 13 — and at DRAW the MODE outranks both.**

`d.plus` is again the row that decides the fix's SHAPE, exactly as at MID$: an
EOL/`:` peek would answer 13 for it. If it reads 24, the delegation is right; if
it reads 13, DRAW differs from MID$ and the peek is right here.

⚠️ **`d.scr0`/`d.scr0num` COULD MAKE THIS SLICE EMPTY.** If the mode gate really
runs first, then in SCREEN 0 nothing reaches the tail at all, and the three DIFF
rows only exist in a graphics mode — which is exactly why D-MISSOP3's original
`DRAW` row agreed at 5 on all three and hid the defect.
