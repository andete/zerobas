# D-CIRCMISS — predictions, written BEFORE the probe was run

Written 2026-08-23 on `81ae426`, ROMs `abfefa7f` / `34bb8554` / `a8173c25`,
walls from a clean `make basic-reloc`: page-1 free 4 B, low 10 B,
**sub p0 2563 B, sub p1 1624 B**.

Readout `[ERR R]`. `R = POINT(30,50)` — the left cardinal point of a radius-20
circle centred at (50,50), read BEFORE the exit line's `SCREEN0:CLS`.
SCREEN 2 background is `BAKCLR` = **4**; `FORCLR` = **15**. So

* `R=4`  nothing was drawn there
* `R=15` drawn in the DEFAULT colour (colour slot omitted / defaulted)
* `R=5`  drawn in the colour the statement named

Both arc boundaries used below (0.1 rad and 6.2 rad) sit near angle 0, so
angle pi — the point read — is deep INSIDE every arc and never on a boundary.

## Round 1 — the machine as it stands (no source has been edited)

| row | statement | pred refs | pred zb | why |
|---|---|---|---|---|
| `c.colour`  | `CIRCLE(50,50),20,`            | `24 4` | `0 15` | §16, ERR re-measured; R is new |
| `c.start`   | `CIRCLE(50,50),20,5,`          | `24 4` | `0 5`  | |
| `c.end`     | `CIRCLE(50,50),20,5,0.1,`      | `24 4` | `0 5`  | |
| `c.aspect`  | `CIRCLE(50,50),20,5,0.1,6.2,`  | `24 4` | `0 5`  | |
| `k.colour`  | `CIRCLE(50,50),20,:A=1`        | `24 4` | `0 15` | the `cp COLON` arm — UNMEASURED |
| `k.start`   | `CIRCLE(50,50),20,5,:A=1`      | `24 4` | `0 5`  | UNMEASURED |
| `k.end`     | `CIRCLE(50,50),20,5,0.1,:A=1`  | `24 4` | `0 5`  | UNMEASURED |
| `k.aspect`  | `CIRCLE(50,50),20,5,0.1,6.2,:A=1` | `24 4` | `0 5` | UNMEASURED |
| `o.none`    | `CIRCLE(50,50),20`             | `0 15` | `0 15` | 🔴 THE TRAP: no comma at all |
| `o.colour`  | `CIRCLE(50,50),20,,0.1,6.2`    | `0 15` | `0 15` | 🔴 THE TRAP: colour omitted BETWEEN commas |
| `o.start`   | `CIRCLE(50,50),20,5,,6.2`      | `0 5`  | `0 5`  | 🔴 THE TRAP: start omitted between commas |
| `o.end`     | `CIRCLE(50,50),20,5,0.1,,1`    | `0 5`  | `0 5`  | 🔴 THE TRAP: end omitted between commas |
| `x.extra`   | `CIRCLE(50,50),20,5,0.1,6.2,,` | `2 4`  | `2 4`  | a 7th slot; LOW CONFIDENCE, could be 24 |
| `x.extra2`  | `CIRCLE(50,50),20,5,0.1,6.2,1,`| `2 4`  | `2 4`  | dangling comma AFTER a complete list — the boundary between the two rules. LOW CONFIDENCE |
| `r.miss`    | `CIRCLE(50,50),`               | `24 4` | `24 4` | the MANDATORY radius; goes through the resident `eval`, so D-MISSOPFIX should ALREADY have closed it |
| `r.nocomma` | `CIRCLE(50,50)`                | `2 4`  | `2 4`  | no comma -> `cpt_err2` |
| `c.ok`      | `CIRCLE(50,50),20,5,0.1,6.2,1` | `0 5`  | `0 5`  | control: every slot present |

**Predicted DIFF count on round 1: 8** — the four `c.*` and the four `k.*`.

## The design this is meant to decide

`sub/circleparse.asm` has FOUR labels reached only AFTER a comma has been
consumed — `cpt_at_c` (:99), `cpt_at_start` (:130), `cpt_at_end` (:153),
`cpt_at_aspect` (:179) — not the three the filing named (`cpt_after_aspect`
carries no such pair; `cpt_at_end` and `cpt_at_aspect` do). Each carries

    or a      / jp z,cpt_finish     <- end of statement after a comma: DRAWS
    cp COLON  / jp z,cpt_finish     <- ':' after a comma: DRAWS

That is **8 jump instructions**, and they are 8 of the **14** that reach
`cpt_finish`. The other six (:97 :125 :151 :177 :230 :262) are the LEGITIMATE
"no more optional fields" exits and the `o.*` rows are what pins them.

⚠️ `cpt_finish` is a SHARED TAIL ([[a-shared-tail-is-not-a-decision]]). The fix
therefore gets its OWN label reached from the 8 sites that mean it, exactly as
D-MISSOPFIX's `ev_f_missop` did — not a change to `cpt_finish`.
