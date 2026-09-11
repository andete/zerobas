# `DEF FN` frames move into the control-frame pool (D-FNPOOL)

Ruled by Joost 2026-09-11: *"go for 2 control-frame pool"* — the string-`FN`
GC-root fix takes the pool, not a page-3 shadow area. The scout (D-FNGCNEST, same
day) measured the defect live on this tree: a string `FN` whose body calls another
string `FN` that collects returns **`qLMNO`** where both references return
`qABCD`; the control (same nesting, no collection) agrees everywhere.

## 1. Why the pool, mechanically

`fn_call` reserves its block **below `SP`** and `ldir`s the whole `FN_BASE`
prefix into it; `fn_leave` copies it back. `sg_walk_fnframe` (sub/strheap.asm)
walks `[FN_PAREA, FN_FEND)` — the LIVE frame — and can never address a block
under `SP`, so an outer call's string formal is reachable from nothing the GC
walks. Moving the saved prefix into the pool makes it addressable: the walk
follows a chain instead of stopping at the live frame.

The pool is already the right place by every other measure: it descends from
`CTLTOP` = `strheap_varceil()` (the reference's published `STKTOP`, §14.4 of
spec-basic-trapsvc), it is sized by `CLEAR`, and it already refuses on collision
with the variable region at `CTLLIM`. 🎯 And `ctl_alloc` is **pure main-ROM
arithmetic** — no tenant call, no slot crossing (measured: zero `call_strheap`
in its body) — so an FN call pays no CALSLT it did not pay before.

## 2. The change

* `FNSP` (2 B, `$E099` from the D-FORVAR band): the newest FN frame's address, or
  0 when no FN call is live.
* Frame: `[prevFNSP:2][prevCSP:2][size:1][the saved FN_BASE prefix]`. `prevCSP`
  is what makes the abort path reclaimable (§3); `size` is what `fn_leave`'s
  `ldir` needs and what the GC walk strides by.
* `fn_call`: compute the size as today, `ld hl,size+5` / `call ctl_alloc`,
  `jp c,gosub_stk_over` (ERR 7 — the same answer `fn_deep` gave, from the pool's
  own collision instead of a hand-rolled `FN_STK_FLOOR` compare), write the
  header, `ldir` the prefix in, `ld (FNSP),hl`.
* `fn_leave`: read `FNSP`, `ldir` the prefix back, restore `CSP` from `prevCSP`
  and `FNSP` from `prevFNSP`. The result and the cursor no longer ride the stack
  through the copy — they stay in DE/HL as today.
* `FN_STK_FLOOR` retires; so does `fn_call`'s `ld sp,hl`.
* `sg_walk_fnframe` gains a second half: after the live frame, walk the `FNSP`
  chain and run the same slot loop over each saved prefix's parameter area
  (`[base+5+FN_CELLS, base+5+size)`), which is exactly the live loop with a
  different base and end.

## 3. The abort path — the one real cost, and it is reclaimable

An error inside an FN body resets `SP` to `SAVSTK` and never runs `fn_leave`;
`raise_error` already resets `FN_FEND` to "no live frame". With the frames in the
pool, the same site must also empty the chain — and it can RECLAIM the space
rather than leak it: an `FN` body is an expression, so **no `GOSUB`/`FOR` frame
can ever be pushed above an FN frame**, which means the outermost live FN frame's
`prevCSP` is the pool frontier the abort should restore. Walk `FNSP` to its last
link, `CSP := that frame's prevCSP`, `FNSP := 0`. One loop, no new cell.

⚠️ NOT claimed: that the walk is free. A program with no live FN call pays one
`FNSP` load and a zero test — the same shape the live-frame walk's `FN_FEND`
test already had.

## 3b. 🔴 IT DOES NOT FIT IN MAIN PAGE 1 — AND THE ROUTE THAT WORKS IS A TENANT

Measured before writing a line of it (2026-09-11): main page 1 has **1 byte**
free and the low region 4. The pool version of `fn_call` is ~+8 B over the stack
version it replaces (the `ld hl,0 / add hl,sp / sbc / cp / ld sp,hl` dance goes,
the header write and `ctl_alloc` call come), `fn_leave` ~+4, and §3's abort
unwind is a ~26 B chain walk in `raise_error`. ~38 B against 1.

A fresh measured sequence scan offers at most ~16 B, all of it in the candidates
a previous slice already REJECTED on frame grounds (`push_lhs_frame` pops its own
return address; `evsp_close` discards a frame) — so the ordinary carve route is
shut for this one [[carve-routes-measured-shut]].

🎯 **The whole frame machinery is RAM arithmetic, which makes it page-0-tenant
legal.** It touches `FN_BASE`, `CSP`, `CTLLIM`, `FNSP` — page-3 RAM, no BIOS, no
main page 1 — and sub page 0 has **790 B** free. So the shape is
`fn_frame_tenant` (SUBROM_IDX_FNFRAME) with three ops: **save** (allocate from
the pool by the same `CSP`/`CTLLIM` arithmetic `ctl_alloc` does, write the
header, copy the prefix in), **restore** (copy back, pop the chain, restore
`CSP`), **unwind** (the abort walk). Main keeps three ~8 B stubs where ~88 B of
code stands today, so page 1 **GAINS ~60 B** — which is also what the SP
relocation will need for its own `CLEAR`-following re-anchor.

⚠️ The tenant must not call `ctl_alloc` itself (main's low region is unreachable
from a page-0 tenant): it does the two compares against `CSP` and `CTLLIM`
in-line, which is ~15 B of the 790 it has. And it runs under DI with main page 0
switched out, so it must touch nothing but RAM — which is all it touches.

## 4. Gates

* `deffn-strict`'s existing four GC rows, plus `n.outer` / `n.outer.ctl` from
  `scratchpad/deffn_gcnest_probe.py` promoted into it (the scout's rows become
  the gate: `qABCD` on all three sides).
* A depth row: nested `FN` beyond 3 (today's cap) now bounded by `CLEAR`, so the
  reachable depth must RESPOND to `CLEAR n` the way the GOSUB pool's does
  (D-CTLPOOL's own property, applied to FN).
* A `b.recurse` control: `DEF FNA(X)=FNA(X)` must still answer ERR 7, now from
  the pool's collision.
* An abort row: an error inside an FN body, then `PRINT FRE(0)` — the pool must
  be back where it started (§3's reclaim), which is the row that makes the
  reclaim a measurement rather than a comment.
