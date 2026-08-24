<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-CIRCTC — CIRCLE's trailing comma was NOT a restructure; it is the same delete-and-delegate

**Date:** 2026-08-24, from `14fd9a5`. **Fix:** delete CIRCLE's bespoke
trailing-comma check at `cpt_asp_done` in
[`sub/circleparse.asm`](../sub/circleparse.asm) and let the resident's `cp_done`
draw and `jp exec_stmt` reject the leftover comma. **Cost: −5 B of sub page 1 —
a carve.** References: Philips VG-8020, National CF-3300. The **fourth and last**
member of the generic error-layer seam (after D-SWAP3, D-PAINT4, D-SPRITE5).

## 0. The headline: the filed characterization was wrong

Every prior filing — D-CIRCMISS §6, D-DUPSPAN §6.1, and the one-pass classifier
(`scratchpad/seam_classify.py`) that ended *"CIRCLE trailing comma → RESTRUCTURE,
confirmed … a second flag, NOT a delete"* — said this case could not be a clean
delete because the parse lives in a sub-ROM tenant that reports through `GFX_RES`,
and the resident's `cp_done` tests that result **before** the `GFX_OP=4` draw, so
"draw, then fail" would need a second signal across the tenant/resident ABI.

🔴 **That verdict was assigned by STATIC REASONING, not measured** — the classic
"a justification parenthesis is an unrun claim". The error: it assumed the
trailing comma must be signalled *as a CIRCLE error by the tenant*. It is not a
CIRCLE-grammar error at all — it is a leftover **statement** token, which is
`exec_stmt`'s job, and `cp_done` **already ends in `jp exec_stmt`** after the
draw:

    cp_done:
                ld      a,(GFX_RES)
                or      a
                jp      nz,raise_error      ; a real parse error -> raise, no draw
                ld      a,4                 ; else GFX_OP=4 -> draw the circle
                ...
                call    subrom_call
                ld      hl,(GFX_DPTR)       ; <-- the cursor, preserved across the draw
                jp      exec_stmt           ; <-- ALREADY delegates the leftover

So the tenant does **not** need a second flag. It needs to do LESS: at
`cpt_asp_done`, report success (`GFX_RES` stays 0) and leave the cursor on the
trailing comma. The draw happens, and the `jp exec_stmt` the resident already
runs rejects the comma via `es_noentry` → `stmt_error` → **ERR 2, trappable,
after the draw** — exactly what SWAP/PAINT/SPRITE delegate to. `GFX_DPTR` is a RAM
sysvar untouched by `gfx_circle_op` (GFX_OP=4), so the cursor survives the draw
round-trip.

**This is a DELETE, like the other three. The "restructure" never existed.**

## 1. The divergence, re-measured on both references from a clean build

`scratchpad/circmiss_probe.py` (reused verbatim — it already carries the row).
Readout `[ERR R]`, `R = POINT(30,50)`, the left cardinal of a radius-20 circle at
(50,50): SCREEN 2 `BAKCLR`=4, so **4 = nothing drawn**, **5 = drawn in the named
colour 5**.

| row | statement | refs | zb before | zb after |
|---|---|---|---|---|
| `x.extra2` | `CIRCLE(50,50),20,5,0.1,6.2,1,` | **`2 5`** | `2 4` 🔴 | **`2 5`** ✅ |

Both references DRAW the circle (R=5) and then raise `Syntax error`; zerobas
raised ERR 2 without drawing (R=4). Full 17-row set: **1 DIFF → 0**
(`circtc_before.out` / `circtc_after.out`). Every other row is byte-identical
across the fix, and in particular:

* `x.extra` (`CIRCLE(50,50),20,5,0.1,6.2,,`) stays `2 4` on all three — the
  aspect slot is itself EMPTY, so the reference raises BEFORE drawing. This is the
  neighbouring `cpt_at_aspect` site and it is CORRECTLY LEFT ALONE.
* `c.ok`, the four `o.*` legitimate-omission rows, and D-CIRCMISS's eight
  dangling-comma rows are all unchanged.

## 2. The two sites are different, and only one moved

CIRCLE's aspect terminator has **two** `cp ','` boundary sites; the per-site
oracle split is the whole design, and it is the same empty-slot-vs-complete-list
rule the four `cpt_at_*` labels already carry (D-CIRCMISS), extended to the end
of the list:

| site | shape | reference | fix |
|---|---|---|---|
| `cpt_at_aspect` | `…,6.2,,` — aspect slot EMPTY | raise BEFORE draw (`2 4`) | **KEEP** its `cpt_err2` |
| `cpt_asp_done` | `…,6.2,1,` — list COMPLETE, trailing comma | DRAW then raise (`2 5`) | **DELETE** its `cpt_err2` → delegate |

The reference draws at the moment its argument list is SATISFIED and checks the
terminator afterwards; when a slot is itself empty it errors first. One rule,
both rows.

## 3. As built — −5 B, sub.rom only

    cpt_asp_done:
                call    cpt_skipsp
    -           cp      ','
    -           jp      z,cpt_err2          ; too many args -> Syntax error
                jp      cpt_finish

Two instructions deleted (`cp ','` 2 B + `jp z,cpt_err2` 3 B) = **−5 B of sub
page 1**. `cpt_err2` keeps its other two edges (`cpt_after_center`,
`cpt_at_aspect`), so nothing is orphaned and `deadcode` is satisfied. A
`sub/*.asm` edit moves **`sub.rom` only**:

    before  sub.rom dd8f417b  basic-reloc.rom 41b8c4ed  merged 53124034
    after   sub.rom 1922eaa0  basic-reloc.rom 41b8c4ed  merged 53124034

— the OPPOSITE signature of the three resident-side seam fixes, and the same as
D-CIRCMISS.

## 4. Knives — 2 of 2 EXACT

`scratchpad/circtc_knives.py`. Each cut is a size-neutral jp-retarget to a label
that keeps other incoming edges, preceded by `rm -rf build`, restored by writing
the bytes, and asserts `sub.rom` moved while `basic-reloc.rom` + merged did not.

| knife | the cut | predicted | moved | |
|---|---|---|---|---|
| **K-CT1** | `cpt_asp_done` `jp cpt_finish` → `jp cpt_err2` (re-impose raise-first) | `x.extra2`, `c.ok`, `o.end` → `2 4` | 3 | EXACT |
| **K-CT2** | `cpt_at_aspect` `jp z,cpt_err2` → `jp z,cpt_finish` (empty slot to delegate) | `x.extra` → `2 5` | 1 | EXACT |

🎯 **K-CT1 IS ITSELF THE REFUTATION OF "RESTRUCTURE".** Only THREE rows reach
`cpt_asp_done` — every row whose aspect is fully parsed (`c.ok`, `x.extra2`,
`o.end`) — and K-CT1 moves **all three together**. After the fix the tenant no
longer distinguishes a trailing comma from a clean end-of-list: both flow through
the one `jp cpt_finish`. So no circleparse.asm knife *can* target `x.extra2`
alone — the trailing-comma decision now lives in the resident's `exec_stmt`,
which is precisely the point. A "second flag" would have kept the decision in the
tenant; there is no flag, and there is no tenant-side decision to knife.

🔬 **K-CT2 is the trap guard** (the K-CM3/K-CM4 analogue): it sends the EMPTY
aspect slot down the delegate path and `x.extra` wrongly draws-then-raises
(`2 5`), proving the empty-slot case must raise BEFORE drawing and that the fix
correctly left `cpt_at_aspect` in place.

## 5. Gates

`scratchpad/circtc_gates.out` + `circtc_gates/*.log`, the 38-gate battery from
`rm -rf build`, `repack-machine` first. `graphics-acceptance` and the
D-CIRCMISS / D-PAINTBORD rows inside `lineerr-acceptance` are the load-bearing
ones — a fix inside a grammar walk is exactly the shape whose blast radius a
purpose-built probe's denominator does not describe.

## 6. The seam is closed

Four members, all measured, all shipped: SWAP (−23 B), PAINT `:798` (−8 B),
SPRITE `:1250` (−8 B), CIRCLE `cpt_asp_done` (−5 B). Every one was a delete of a
bespoke trailing-token check whose job the statement boundary already does; every
one also fixed an ordering bug (side-effect-then-raise). The classifier's KEEP
verdicts (PAINT `:748`, SPRITE `:1203`/`:1210`, PLAY `:73`) stand — those raise
before their effect and agree on both references. The one RESTRUCTURE verdict was
the only one it got wrong, and it got it wrong by reasoning instead of measuring.
