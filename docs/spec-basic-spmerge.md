# `SP` moves into the pool's region — the MERGE (D-SPMERGE)

Ruled by Joost 2026-09-11: *"for the SP, the only real option is MERGE, it is the
most compatible one"*, and **first in the queue**: *"the stack fix we decided on
earlier should be the first thing to actually fix next"*. The defect it closes is
TIER 1 — a legal 16-deep parenthesised formula WRECKS the machine (D-PARENNEST:
screen garbage at depth 16, `ERR 50` from a path that raises no 50, crash at
string depth 12) where both references print the value to depth 32.

## 1. The measurement that makes the size of the problem plain (2026-09-11)

Read from the running machine (`PEEK` of the published cells):

| | address | |
|---|---|---|
| `CTLTOP` / `CSP` (empty pool) | **$D906** | = `strheap_varceil()` = the reference's `STKTOP` (§14.4) |
| after `CLEAR 2000` | **$D1FE** | the top moves with `CLEAR`, exactly as the reference's does |
| `CTLLIM` (= ARYEND+2) | **$80CB** | the variable/array region's first free byte |
| the Z80 stack | ~**$F2EA**, floor $F200 | **234 B** of headroom — and `basic/` sets `SP` nowhere |

**~22 KB of free RAM sits between `CTLLIM` and `CTLTOP`**, and the evaluator
recurses in 234 bytes above it. That is the whole defect in two numbers.

## 2. What MERGE has to mean here

The reference's observable contract (§11, measured three ways): control frames
and the machine stack come from ONE region bounded by HIMEM; depth responds to
`CLEAR` and to HIMEM; ~7 B per frame; nothing is ever "reclaimed" because `SP`
simply moves. So the invariant is

    at every statement boundary:   SP == CSP
    control frames occupy          [CSP, CTLTOP)
    the machine stack descends     [CTLLIM, CSP)

A `GOSUB` frame therefore costs the evaluator exactly its own size, and a deep
expression is bounded by `CSP − CTLLIM` — which is what "the same pool" means
observably, and what `stackpool-acceptance`'s rows already pin for the reference.

## 3. Where `SP` may move — the part that is not free

🔴 **`exec` is CALLED, not jumped to** (`basic/program.asm:597`: `call exec` per
line), so `SP` at `exec_stmt`'s top carries a live return address and a
per-statement `ld sp,(CSP)` would discard the line loop's return. The safe points
are the two that already anchor `SAVSTK` — the direct-mode anchor
(`program.asm:64`) and the run anchor (`:429`) — because the trap path
(`ld sp,(SAVSTK)`) already treats those as places the machine JUMPS back to
rather than returns to.

Consequences to design against, each of them a way to get this wrong:
1. **`ctl_alloc` must keep `SP` and `CSP` together.** At a `GOSUB`, `SP` is a few
   return addresses below `CSP`; lowering `SP` to the new `CSP` is safe only when
   the frame is larger than that delta, which is not guaranteed. The frame push
   therefore happens at the statement boundary's known depth, or `ctl_alloc`
   performs the pop-return-address / allocate / re-push dance `fn_call` already
   does today.
2. **Freeing raises `SP`**, which discards live return addresses by construction —
   legal only where the code path afterwards JUMPS (`jp exec_stmt`) instead of
   returning. `RETURN` and `NEXT` already end that way; every free site must be
   re-read against that rule, not assumed.
3. **`SAVSTK` is re-anchored whenever `SP` moves**, or the trap unwinds to an
   address that is no longer in the region.
4. **`CLEAR n,addr` moves `CTLTOP`**, so the relocation must re-read `CSP` after
   every `clear_vars`, never cache a boot value — the `$D000` accident of §17 is
   exactly the cached form of this.

## 4. Order of work

1. **The subject gets a gate first.** `D-PARENNEST`'s ramp is a scratchpad scout;
   it becomes `parennest-acceptance` with the diverging depths PINNED to today's
   faces, so the defect has a standing row and the fix flips pins in the same
   commit as the code (the tree's rule for a measured divergence).
2. Then the relocation, against that gate plus the pool's existing contract
   (`stackpool`, `ctlpool`, `ctlcross`, `ctllim`, `trapdepth`, `trapsvc`).
3. Then `DEF FN`'s frames move to the same region (D-FNPOOL, ruled the same day),
   which is where the GC-root fix lives; §19's "how much of the ~78 B/level is
   evaluator recursion vs FN machinery" is re-measured after that, not before.

⚠️ Not claimed: that the 22 KB is all usable — `CTLLIM` rises with every `DIM`,
which is the point of the collision check. Only that the evaluator's 234 B is not
the size of the free gap and never was.

## 5. The relocation's own byte budget — measured 2026-09-11, after D-FNPOOL

`repl:` is the one safe site (entered `jp repl`, "read/eval loop (never
returns)"), and `basic/repl.asm` is INCLUDED AFTER `__MEAS_LOW_END`, so it is
main page 1 — which has **3 bytes** free with D-FNPOOL landed.

The site needs ~8:

        ld      hl,(CSP)        ; 3   the pool's live frontier, re-read every line
        ld      a,h             ; 1   ...so CLEAR / RUN / NEW are followed for free
        or      l               ; 1
        jr      z,rp_nosp       ; 2   pool not live yet (cold boot, before ctl_reset)
        ld      sp,hl           ; 1

🔴 **AND IT CANNOT BE HIDDEN IN A `call`.** A helper in the low region (5 B free)
would have its return address on the OLD stack and `ret` would pop from the NEW
one; the pop-into-HL / `jp (hl)` dance that fixes it costs ~12 B there. Both
regions are short, and they share one budget.

➡️ So the next slice in this arc is **a carve, not the relocation** — the same
route that has funded three slices tonight (measured sequence scan, then Route D,
which renews after every insertion). ~10 B of main page 1 buys the relocation
AND its `CLEAR`-following re-anchor.

## 6. 🔴 THE FIRST CUT FLIPPED ALL NINE PINS AND WAS STILL WRONG (2026-09-11)

`ld sp,(CSP)` at `repl:` — four bytes, the site §3 argues for — made every
wrecked depth answer the reference's value (`p32` = 33, `f32` = 1, `s16` = 1)
**and took thirty-two other suites down with it**: `stackpool`, `ctlcross`,
`trapdepth`, `trapsvc`, `ctllim`, `forvar`, `nxary`, `nxlist`, the trap suites,
`float`, `array`, `graphics`… Reverted; all three of the worst-hit are green
again and the nine pins are back.

**The cause is in §2's own arithmetic, and I had it backwards.** `ctl_alloc`
allocates **downward from `CSP`**:

        HL = CSP − size ; refuse if HL < CTLLIM ; CSP = HL

With the stack BASED at `CSP`, the interpreter is already some tens of bytes
below it by the time a statement runs — so the first `GOSUB`/`FOR`/trap frame is
handed out **inside live stack**, and the two consumers write over each other on
the very first push. The spec's own sentence "frames the pool already holds sit
above `CSP`" is true of frames ALREADY allocated and says nothing about the next
one, which is the only one that matters.

**So MERGE has one frontier, and it must be `SP` itself.** The shape that works:

* `ctl_alloc` allocates from `SP`, not from a separate `CSP` the stack has
  already run past: pop its own return address, `HL = SP − size`, refuse on
  `CTLLIM`, `ld sp,hl`, push the return address back, `ret`.
* `CSP` becomes a mirror of `SP` for the existing readers (`GSP`/`FSP`/`TSP`
  comparisons, `strheap_varceil`'s ceiling test, `FRE`).
* Every free site (`RETURN`, a named `NEXT`, the trap pop, `fn_leave`) raises
  `SP` as well as `CSP` — legal only where the path afterwards JUMPS
  (`jp exec_stmt`), which §3 already required and which those sites already do.

That is a multi-site slice against the pool's whole contract, not a four-byte
patch, and it is what the next attempt implements. The nine pins stay pinned
until it lands: **rows going green is necessary and nowhere near sufficient**,
which is why the battery runs before a pin is flipped.

## 7. What cut 2 actually costs — the constraint that decides it (2026-09-11)

§6 named the shape: one frontier, and it must be `SP`. Reading every site that
would have to change turns that into a concrete constraint, and it is not about
`ctl_alloc` at all.

**A frame allocated by lowering `SP` cannot be crossed by a `ret`.** The moment
`ctl_alloc` does `ld sp,hl`, every return address already on the stack sits ABOVE
the new frontier, and the next `ret` pops the frame's bytes instead. The
allocation dance (pop the return address, allocate, push it back) fixes
`ctl_alloc`'s OWN return — it cannot fix its callers'. And the callers are:

| site | shape today | crossable? |
|---|---|---|
| `gosub_push` (`ex_gosub`) | `call gosub_push` → `jr c` → `jp goto_take_bc` | no — but it tail-calls cleanly: `jp gosub_push`, ending `jp goto_take_bc` / `jp gosub_stk_over` |
| the `FOR` push | `call ctl_alloc` → `ldir` → `jp pop_exec` | already jump-tailed |
| the trap record (`traps.asm`) | `call ctl_alloc` → … | reachable from the ISR seam; needs its own reading |
| 🔴 **`exec`** | **`rp_run: call exec`** (`basic/program.asm:597`) | **no.** The run loop CALLS the line executor, so `exec`'s return address is on the stack for the whole line — and any frame a statement allocates lands below it. `exec`'s `ret` at end of line then pops across the frame. |

So the merge's real precondition is that **the run loop stops returning across a
statement's frame**. Three ways out, and the choice is a design decision, not a
detail:

1. **Make the run loop a jump loop** — `exec` reached by `jp`, END/STOP/CONT and
   the error paths re-entering through `SAVSTK` as the traps already do. Faithful
   to how the reference is structured, and the reason its GOSUB depth is bounded
   by RAM rather than by an array. Touches the run loop, END/STOP, CONT, RESUME.
2. **Allocate by SHIFTING the live stack down** — `ctl_alloc` `ldir`s the live
   block down by `size` and places the frame in the vacated top, so every pending
   return address stays contiguous below it and no `ret` ever crosses anything.
   Costs one short `ldir` per `GOSUB`/`FOR`/trap push (tens of bytes) and requires
   adjusting every ABSOLUTE saved `SP` — `SAVSTK` at least — by the same `size`.
   Localised to `ctl_alloc` plus the free sites; the interpreter is untouched.
3. **A dynamic reserve** — keep the pool where it is and base the stack a
   computed distance below `CTLTOP`, sized from `CLEAR`. This is partition wearing
   merge's clothes: depth would respond to `CLEAR` and HIMEM, which is the
   measured property, but the two consumers would not actually share.

⚠️ Not started. (1) and (2) are both real; (2) looks cheaper and is reversible,
(1) is what the reference does. This is the point where the arc needs a decision
rather than another cut.
