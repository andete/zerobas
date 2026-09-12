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

## 8. Cut 2 is RULED (1), and here is what (1) actually costs (2026-09-11)

Joost, asked which way out of §7: **the jump loop**, over the `ldir` shift. So
`exec` must never be returned from — at a statement boundary the stack has to hold
frames and nothing else.

### 8.1 `ret` cannot survive, and the reason is one sentence

A `ret` needs a stack word. At the statement boundary we need ZERO stack words
above the frontier. So every path that leaves `exec` becomes a jump. Four ways
around it were tried on paper and all fail on the same wall:

* **Stash the return address in RAM at `exec`'s entry.** The exits still execute
  `ret`, which now pops a frame.
* **Push a sentinel for the exits to `ret` to.** That sentinel IS the two bytes the
  frame lands under. Identical to today.
* **Defer the frame push to the boundary** (the §3.1 "known depth" option). The
  LINE boundary is too late — `FOR I=1 TO 3:NEXT` needs `NEXT` to see the frame the
  same line pushed — and the STATEMENT boundary is inside `exec`, where the return
  address is still live. Same wall.
* **Re-base `SP := CSP` per line and allocate from `SP`.** The frame lands below
  `exec`'s return address, and the end-of-line `ret` pops the frame. This is cut
  1's bug wearing a different hat.

### 8.2 The site list is MEASURED, not guessed

[`scratchpad/execexit_scout.py`](../scratchpad/execexit_scout.py) walks the source
from all 90 `stmt_table` handlers, following jumps, not descending into calls, and
reports every `ret` reachable at the handler's own depth.

🔴 **Its first cut said 38 sites and was wrong**, in this tree's most familiar way:
it counted `pch_done` — the tail of a CALLED helper — as an `exec` exit with
TWENTY-FIVE origins, because it had jumped into a label that is also a `call`
target. Hardened with a taint rule (any chain through a `call` target is
AMBIGUOUS, reported separately and not counted) and a bar on crossing into `sub/`
(a main-ROM `jp` cannot land there; a same-named label is a collision):

| | count | note |
|---|---|---|
| **confirmed exits** | **25** | each `ret`/`ret cc` is 1 B and becomes a 3 B jump: **+50 B** |
| ambiguous | 12 | reached only through a `call` target; each needs reading. The five read so far (`load_commit_prog`, `verify_error`, `cont_record`, `sv_tenant`, `load_handoff`) are ordinary subroutines whose `ret` serves their caller — false positives |

Against **12 B free** (page 1 10, low region 2, one budget).

### 8.3 What makes it affordable: the exits are mostly a repeated idiom

Eight of the confirmed sites are literally `ld a,1` / `ld (FLAG),a` / `ret` — 6 B —
and become a 3 B `jp` to one shared tail per flag: **−3 B each**, not +2. The
already-existing `set_resumeflag_ret` is the same idiom spotted once before. So
the conversion is a CONSOLIDATION that partly funds itself, and the carve to find
is the remainder, not the full +50.

### 8.3a 🔴 THE HARD CASE: A SHARED TAIL THAT IS BOTH CALLED AND TAIL-JUMPED

`goto_resolve` (`basic/interp.asm:2036`) is the GOTO/RESUME/IF tail — `find_line_bc`,
the undefined-line check, then `ld (GOTOTGT),hl` / `ld a,1` / `ld (GOTOFLAG),a` /
`ret`. It appears in BOTH scout lists, confirmed and ambiguous, and that is not a
bug in the scout: `ex_goto` reaches it by `jr`, so its `ret` leaves `exec` — and
`basic/cload.asm:299` does `call goto_resolve`, so the same `ret` also returns to
a caller. Converting it to a jump breaks the call; leaving it breaks the merge.

This is [[a-shared-tail-is-not-a-decision]] in its exact form, and it decides the
shape of the conversion: a tail with both kinds of user needs SPLITTING — the
arming body, then two entries, one ending `ret` for callers and one ending
`jp rp_after` for the statement paths. **Every one of the 25 confirmed sites must
be checked for a `call` on the same label before it is converted**, not just the
12 the taint rule already flagged.

🟢 **AND THAT CHECK IS DONE: `goto_resolve` IS THE ONLY ONE.** Cross-referencing
each confirmed site's enclosing label against all 670 `call` targets in the tree:
24 of 25 sit in labels nothing ever calls (`ex_end`, `ex_rem`, `exd_lp`,
`if_false`, `exl_walk`, `exp_stmt_end`, `pu_skipnl`, `rp_run`, `ex_delete`,
`exr_done`, `exa_stop`, `set_resumeflag_ret`, `nx_again`, `goto_take_bc`,
`dl_cas_close`, `dl_is_disk`, `do_run`, `dr_cas_close`, `cas_ascii_save`,
`sv_tenant`, `disk_write_end`), so their `ret` has exactly one meaning and becomes
a jump with no reasoning required. `goto_take_bc` is NOT a second hard case — it
is jump-only despite sharing the idiom. **One split, not a class of them.**

### 8.4 Order, and the knife

1. Shared exit tails (`end_line_end` / `_goto` / `_resume`), which is a carve.
2. Convert the 25 confirmed sites.
3. Read the 12 ambiguous ones.
4. 🔬 **KNIFE**: build once with `rp_run` pushing a POISON address before
   `jp exec`. Any exit nobody converted lands on it and is named by the suite that
   trips it, instead of popping a frame and corrupting the machine silently. The
   battery is the denominator; a green battery with the poison in place is the
   evidence that the site list is complete.
5. Only then stage B — `ctl_alloc` from `SP`, `CSP` as the mirror, the free sites.

⚠️ Stage A changes NO stack behaviour: `SP` still never moves. Its whole content
is "the run loop stops returning across a statement", so it must land with the
battery at 128/128 and the nine `parennest` pins UNMOVED. A pin that flips during
stage A means something other than the conversion happened.

## 9. Cut 2, RE-RULED: `ctl_alloc` relocates the live block (2026-09-11)

§8's jump loop was ruled on an estimate of ~50 B. **Building it measured ~93 B and
the ruling changed.**

### 9.1 What the jump loop actually cost, and what §8 missed

39 B bought the 19 confirmed `ret` exits (applied, builds, saved as
[`scratchpad/d-jumploop-stageA-v2.patch`](../scratchpad/d-jumploop-stageA-v2.patch)).
The remaining ~54 B is nine wrappers, because **41 statement paths leave `exec` by
TAIL-JUMPING into a shared helper** rather than by `ret`:

| helper | `call` sites | tail-jumps |
|---|---|---|
| `load_error` | 1 | **29** |
| `print_crlf` | 6 | 5 |
| `print_msg` | 4 | 5 |
| six others | 1–2 each | 1–2 each |

Each helper's `ret` serves real callers, so it cannot be converted; the fix has to
sit at the jump (`call helper` + `jp rp_after`), one 6 B wrapper per helper.

🔴 **§8.3a's "one split, not a class" WAS WRONG, and the audit that produced it was
blind by construction.** It checked every confirmed `ret` site's enclosing label
against the tree's 670 `call` targets — a sound test for `ret` sites, and it says
nothing about JUMP sites. `exp_nl_ret: jp print_crlf` is how PRINT ends a line and
never appeared in it.

🔴 **AND THE FAILURE MODE IS SILENT.** With `jp exec` nothing is pushed, so a
missed exit's `ret` pops the REPL's own return address and lands at the prompt.
The program looks like it worked. `CONT` merely stopped recording its resume
point: 12 suites red, no crash anywhere, and the trace showed the run loop simply
never regaining control after a `PRINT`.

### 9.2 The shape ruled instead

Keep `call exec`. `ctl_alloc` moves the live block out of the frame's way:

    the live block is [SP, CSP)      -- and CSP - SP is SMALL
    1. base := CSP - size ; refuse if base < CTLLIM
    2. copy [SP, CSP) down by `size`   (forward copy; dest < src, no overlap hazard)
    3. SP := SP - size ; CSP := base
    4. the frame occupies [base, oldCSP), and HL := base

No `ret` ever crosses a frame, because everything that could `ret` moved down with
it. Zero exit conversions; one routine changes.

### 9.3 🔴 I ARGUED AGAINST THIS ON A COST MODEL THAT WAS WRONG

§7 rejected option (2) as *"an `ldir` of the WHOLE live stack on every
`GOSUB`/`FOR`/trap push — O(depth), in the hot path, inside the one fix whose
entire purpose is to let the evaluator recurse deeply"*, and I repeated it when
the fork was put to Joost.

**It is not the whole live stack.** Frames are only ever pushed at a STATEMENT
BOUNDARY, where the expression evaluator has already unwound — so the block
between `SP` and the frontier is the statement handler's own chain and nothing
else. Read at the two main-ROM callers: `gosub_push` holds `push bc` + `push hl` +
its own return + `ctl_alloc`'s return above the continuation, about ten bytes. The
copy is bounded by the handler's depth, not by the recursion depth the merge
exists to enable, and it does not grow as expressions get deeper.

The "adjust every absolute saved `SP`" objection also shrinks: `SAVSTK` is
captured at the loop/REPL anchor, ABOVE the frontier, so a block moving below it
does not touch it.

⚠️ So ~10 B was optimistic in the other direction — the room check plus the copy is
nearer 25–30 B. Still one routine against ~93 B over sixty sites.

### 9.4 Order of work

1. `ctl_alloc` as §9.2, with `CSP` still the frontier and `SP` still C-BIOS's —
   behaviour-identical, because the copy is a no-op until `SP` lives in the region.
   The battery must stay 128/128 and the nine pins UNMOVED.
2. Then move `SP` into the region at the safe point (§3), which is the cut that
   flips the pins.
3. The trap record (`basic/traps.asm:372`) is the third `ctl_alloc` caller and
   fires from the ISR seam; its stack shape needs its own reading before step 2.

## 10. 🔴 THE MERGE AS BUILT IS ASYMMETRIC, AND IT BREAKS THE HAPPY PATH

§9 shipped as step 3 and seven of nine affected suites went green. **That reading
was wrong, and the two red trap suites were never the real defect.** A fable
subagent was dispatched to investigate them deeply (Joost, 2026-09-12); it named
two independent causes, and BOTH re-verified here before anything was built on
them.

### 10.1 The relocation is ONE-WAY — proved by reading, then measured

`ctl_alloc` is the only path that relocates: it lowers `CSP` and tail-jumps to
`ctl_reloc`, which slides the live block `[SP, CSP)` down by the frame's size.
But the frontier is RAISED — a frame freed — at **six other sites that do not
move the stack at all**:

| site | what frees there |
|---|---|
| [`basic/program.asm:1623`](basic/program.asm:1623), [`:1653`](basic/program.asm:1653) | `RETURN`, the GOSUB frame |
| [`basic/program.asm:1949`](basic/program.asm:1949), [`:2034`](basic/program.asm:2034) | `NEXT` closing inner frames |
| [`sub/deffn.asm:512`](sub/deffn.asm:512), [`:551`](sub/deffn.asm:551), [`:574`](sub/deffn.asm:574) | the `DEF FN` frame |
| [`sub/strheap.asm:1844`](sub/strheap.asm:1844) | the string-heap frame |

So every alloc/free CYCLE lowers `SP` by the frame's size and never raises it
back. The gap `CSP - SP` grows monotonically for the life of the program, and
`ctl_alloc`'s 256-byte reserve cannot see it, because the reserve is measured at
the FRONTIER, which returns to the same address every time.

🎯 **MEASURED, and it is not a trap corner — it is `FOR`/`GOSUB`/`RETURN`/`NEXT`**
([`scratchpad/spmerge_gosubdrain.py`](scratchpad/spmerge_gosubdrain.py),
[readings](scratchpad/spmerge_gosubdrain.out)). No traps, no errors, no `FN`:

| iterations | zb + step3k patch | VG-8020 |
|---|---|---|
| 50 | `[51]` | `[51]` |
| 200 | `[201]` | `[201]` |
| 400 | `[401]` | `[401]` |
| **800** | **`NO OUTPUT`** | `[801]` |

🔴 **THE 400 ROW IS A CORRECTION, AND THE ERROR WAS MINE.** The first run of this
table reported 400 blank as well, at the suite's own `step=5.0, cap_gap=45.0`. Re-run
at `step=20.0, cap_gap=180.0` it prints `[401]` on the SAME build: 400 was the
CAPTURE BUDGET, not the drain — this program is about five times the work of the
`FOR`/`NEXT` control, on a machine already 2.5–3.8× slower than the reference, and a
row that runs out of budget prints exactly like a row that died
[[an-unnamed-outcome-reads-as-no-outcome]]. The defect is unchanged and 800 still
dies with the window wide open; only the threshold moves.

The subagent's independent run of the same class put the death at GOSUB #360 with
`Syntax error in 63784` and 8 B drained per `RETURN`, which lands inside the
200–400 window measured here. **The merge as built is a TIER 1 regression, worse
than the defect it fixes.** The copy also grows with the gap, so the cost is
O(n²) in the number of frames, not the O(1) §9.3 argued for.

### 10.2 `fnf_save` does `ctl_alloc`'s arithmetic and skips `ctl_reloc`'s half

[`sub/deffn.asm:492`](sub/deffn.asm:492) hand-rolls the allocation — its own header
says so, *"`ctl_alloc`'s arithmetic done here, because main's low region is
unreachable from a page-0 tenant"* — and then `ldir`s the FN prefix into the
region it just claimed ([`sub/deffn.asm:524`](sub/deffn.asm:524)). Under the merge
that region IS the live stack block `[SP, CSP)`, so the copy lands on top of the
newest pushed words, including `run_prog`'s return word at the `SAVSTK` anchor.

The subagent's watchpoint caught the write with the writer named: `PC=$3753`, the
byte after the `ED B0` in the SUB ROM's `fnf_save`, `HL=EA9A` = `FN_BASE+8`,
`DE=D8F9` = the anchor. The BIOS-ISR-at-`$18E6` reading recorded in earlier ticks
was **post-mortem**: `ret nz` popped the FN cell `FFFF`, the machine took `RST 38`,
and the ISR pushes logged there are the crash, not its cause.

### 10.3 🔴 AND `deffn-acceptance` WAS GREEN THROUGH ALL OF IT

The reason §10.2 survived five ticks undetected is that its own gate cannot see
it. Same target, same `rc=0`, same headline
([clean](scratchpad/spmerge_deffn_clean.out) vs
[patched](scratchpad/spmerge_deffn_patched.out)):

| | rows SCORED | `NOT MEASURED` | verdict printed |
|---|---|---|---|
| clean tree | **86** | 1 | `0 of 73 DEF FN rows still divergent` |
| step3k patch | **33** | **55** | `0 of 73 DEF FN rows still divergent` |

54 rows stopped answering and the suite reported the same green line, because a
blank reading is excluded from scoring rather than counted against it. **The
scored DENOMINATOR is the signal and nothing watches it**
[[an-unnamed-outcome-reads-as-no-outcome]] [[gateblind-slice]]. `deffn-acceptance`
was also not among the nine suites this arc was re-running, so even its collapsed
denominator went unread.

### 10.4 What the design has to become

The re-based frontier is the free operation, and the fix is to stop trying to make
alloc and free symmetric one site at a time:

**At the statement loop `rp_lp`, where the live block is exactly ONE WORD, re-base
the stack to the frontier every statement:**

    pop     de
    ld      sp,(CSP)
    push    de
    ld      (SAVSTK),sp

All six entries to `rp_lp` ([`basic/program.asm:606`](basic/program.asm:606),
`:614`, `:624`, `:630`, `:1123`,
[`basic/interp.asm:1508`](basic/interp.asm:1508)) arrive with `SP == SAVSTK`, so
the invariant holds on every path in. This removes the drain (a freed frame is
reclaimed at the next statement, wherever it was freed and by whom), bounds the
copy at the statement handler's own depth instead of the program's, and makes
`raise_error_hl`'s `(SAVSTK)`-vs-`(CSP)` question moot because the two coincide by
construction.

### 10.4a 🟢 BUILT AND VERIFIED ON A SCAFFOLD (2026-09-12)

The re-base is written and measured. It sits at the TOP of `rp_lp`, above the
`RESUMEFLAG` test, so all four entries — `rp_run`'s fallthrough, `rp_goto`, the
trap-fired branch and `rp_resume` — pass through it.

⚠️ **IT WAS MEASURED ON A SCAFFOLDED BUILD, WHICH IS A DIFFERENT MACHINE**
[[a-scaffolded-build-is-a-different-machine]]: `SWAP_RESIDENT equ 0` evicts SWAP to
the sub ROM and frees 154 B of page 1, which is where the 10 B came from. The switch
is back at 1 and the real build OVERRUNS by exactly those 10 B — the assembler
refuses with `BASIC_IMAGE_OVERRAN_8000_CEILING`, so nothing ran on a stale machine.

📏 **THE DRAIN IS GONE, on the same program and the same wide window**
([before](scratchpad/spmerge_drain_before.out) vs
[after](scratchpad/spmerge_drain_after.out)):

| iterations | before | after | VG-8020 |
|---|---|---|---|
| 50 / 200 / 400 | `[51]` `[201]` `[401]` | same | same |
| **800** | **`NO OUTPUT`** | **`[801]`** | `[801]` |

🎯 **AND THE MECHANISM IS WITNESSED DIRECTLY, not inferred from the output.** A
breakpoint at `rp_lp` logging every 25th pass
([`scratchpad/spmerge_rplp_trace.out`](scratchpad/spmerge_rplp_trace.out)) reads
`SP=D8F9 CSP=D8FB SAVSTK=D8F9 gap=2` at hit 25 and the IDENTICAL triple at hit 4000
— the gap never moves across the whole run, where before it fell by the frame size
on every cycle.

💰 **WHAT IS LEFT IS ONLY THE CARVE: 10 B of main page 1, at 0 B free.** The two
halves that fit:
  * `repl:`'s own re-base is **8 B** (`ld hl,(CSP)` + the zero test + `ld sp,hl`) and
    is now mostly redundant — typed lines route through this same loop, so `rp_lp`
    re-bases them too. 🔴 **DO NOT DELETE IT OUTRIGHT**: `repl` is entered by `jp`
    and never returns, so its discard is what reclaims a line that FAILS before ever
    reaching the loop (a syntax error at the prompt). Shrinking it to a bare
    `ld sp,(CSP)` keeps the discard and drops only the cold-boot zero guard — **4 B**,
    and whether that guard is dead is a measurement (does `CSP` read non-zero at the
    first prompt?), not a judgement.
  * `jr_mapper.py` finds **2 B** on 2026-09-12: `$4F5E jp z -> ev_ff_lof`
    ([`basic/expr.asm:1121`](basic/expr.asm:1121)) and `$65BF jp -> bl_load_error`
    (`basic/pdfcb-body.inc:53` — ⚠️ a `*-body.inc`, so check whether `sub/` includes
    it before touching it).
  * The remainder from the pair scout, whose best live candidates on 2026-09-12 are
    `jp nz,stmt_error | inc hl` (11 sites, net 6 B) and
    `inc hl | ld e,(hl) | inc hl | ld d,(hl)` (10 sites, net 5 B).
### 10.4b THE CARVE, AS SHIPPED — AND THE ONE ROW THAT STOPS IT (2026-09-12)

**The 10 B came out of code the re-base itself made dead**, so no pair conversion
was needed:

| carve | B | how it was settled |
|---|---|---|
| `repl:`'s whole re-base | **8** | MEASURED: a breakpoint at `repl` over 23 prompt entries, 20 of them deliberately-failing lines (`FOR`, `NEXT X`, `PRINT )`, `GOTO`), reads `SP=D906=CSP gap=0` EVERY time — the error unwind self-levels through `SAVSTK`, so the prompt needs no re-base of its own. Hit #1 is the cold-boot C-BIOS `SP=F2EC`, before anything has re-based. |
| the RUN anchor, `basic/program.asm:429` | **4** | `rp_lp` rewrites `SAVSTK` on every pass before anything can read it |
| the direct-mode anchor, `basic/program.asm:64` | **KEPT** | 🔴 I was WRONG that this one was redundant. Deleting it moved `deffn`'s `d.def`/`d.defrun` from `Undefined user function` to `Illegal direct`; restoring it alone took the suite back to 0 of 73. A direct-mode error unwinds back to the REPL, and `rp_lp`'s re-based anchor points into the LOOP. |

12 B carved against 10 B spent: **page-1 2 B free, low 0 B, sub page 0 527 B** with
the `fnf_save` arm in. Whole slice:
[`scratchpad/d-spmerge-step5.patch`](scratchpad/d-spmerge-step5.patch).

⚠️ **ROUTE D UN-RENEWS EXACTLY AS IT RENEWS.** `jr_mapper.py` proposed
`basic/expr.asm:1121` and the ASSEMBLER REFUSED IT — *relative jump out of range* —
because the proposal was measured before this slice moved the layout. Re-run after
the carve it proposes the SAME site again, so its range model and the assembler
disagree; that is an instrument bug worth its own item. `basic/pdfcb-body.inc:53`
converted, then went out of range the moment another 4 B was freed.

🟢 **GREEN ON THE REAL BUILD (no scaffold):** `parennest` 16 rows, `WRECKED` empty,
0 divergence, 0 drift — **the TIER 1 defect is fixed**; `trapsvc` PASS 7/7 including
`int.resnext`/`int.resume`/`int.six`; `deffn` 0 of 73 divergent with **86 rows SCORED
and 1 NOT MEASURED**, matching the clean baseline exactly; the GOSUB sweep
`[51]/[201]/[401]/[801]`, equal to the VG-8020 at every depth. Battery **126/128**.

### 10.4c 🟢 STEP 6: THE ARRAY CEILING HAD TO RESERVE THE STACK — AND WHERE

One row held the slice back, and it was right to. The history below is kept because
the FIRST reading of it was wrong twice.

🔴 **THE DEFECT.** `strheap_varceil` clamps the variable/array ceiling to `CSP`, the
pool's live frontier — correct before the merge, and catastrophic after it, because
since the merge **the machine stack lives BELOW `CSP`**. A ceiling AT the frontier
lets the array region grow straight through the live stack. The routine's own note
had already named the gap: the pool's `ctl_alloc` check "is only one side of it".

📏 **CLEAN AND MERGED, SAME INPUTS** (`MAXFILES=0` / `CLEAR 200,47872` / `DIM Z(N)`
then 26 scalar assignments,
[readings](scratchpad/spmerge_squeeze_bisect.out)):

| N | clean | merged, before the fix |
|---|---|---|
| 1845 | 123 B, `Out of memory` | 123 B, **no OOM** |
| 1855 | 43 B, `Out of memory` | **2526 B**, no OOM |
| 1857 | 27 B, `Out of memory` | **no reading at all** |
| 1859 | 11 B, `Out of memory` | **no reading at all** |
| 1861 | the `DIM` fails | the `DIM` fails |

Clean is monotonic and raises the error at every step; merged went non-monotonic and
**died**. So this was a regression the merge introduced, not a row whose geometry had
rotted — and re-sizing it to a passing value would have been fixing the test to match
a defect. 🔴 **MY FIRST READING SAID THE OPPOSITE** ("under the merge the geometry
leaves 123 B instead of ~26, so it needs a re-size"): both builds read 123 B at
N=1845, the probe's own "~27 B" comment had rotted, and clean's real 27 B point is
N=1857. Walking the CLEAN boundary is what separated the two.

🔴 **AND THE FIX'S LOCATION IS THE WHOLE LESSON.** The reserve went into
`strheap_varceil` first — one byte, `dec d`, exactly the right idea. It turned
`txtceil`'s **POSITIVE control** red with `stored=0`: the bound refused every
program, which is precisely what that control exists to catch, and it took
`loc-acceptance` with it. `strheap_varceil()` is **also** the pool's top (`CTLTOP`)
and the source of the program-text store ceiling `SL_CEIL`, so a reserve taken there
moves the whole map [[a-mechanical-fix-can-break-a-different-invariant]]. The same
instruction two sites over — `dec h` after each `call strheap_varceil` in
[`sub/arrays.asm`](sub/arrays.asm) — bounds only the array growth it is about.
**2 B of sub page 0**, `txtceil` and `loc` green, `array` 146/146.

📏 **AFTER THE FIX THE MERGED BUILD REPRODUCES CLEAN EXACTLY, shifted by 32 elements
— 256 B at 8 B per double, the reserve itself**: 1813 → 123 B of margin, 1821 → 59,
1825 → 27, 1827 → 11, 1829 the `DIM` fails. Both `DIM Z(1845)` sites in
[`probes/basic/basic_probe_arrays.py`](probes/basic/basic_probe_arrays.py) re-size to
**1813** on that mechanism. ⚠️ `FRE(0)` reads **256 high** — the reserve sits at the
check, not in the ceiling — so merged N=1813 reports 379, which is clean's 123 plus
the margin. Read the margin, never `FRE`.

🟢 **LANDED: battery 128/128**, the five battery-excluded targets green by hand,
`parennest` 16 rows with `WRECKED` empty and 0 drift, `trapsvc` PASS 7/7, `deffn`
0 of 73 with **86 rows SCORED**, `array` 146/146, the GOSUB sweep
`[51]/[201]/[401]/[801]` equal to the VG-8020. Page-1 2 B free, low 0 B, sub page 0
525 B, all measured 2026-09-12.

### 10.4d (historical) the row as it blocked the slice

🔴 **AND IT WAS NOT COMMITTED, BECAUSE OF ONE ROW.** `array-acceptance`'s
`scalar.str.chain.oom` is a byte-precise squeeze — `MAXFILES=0` / `CLEAR 200,47872` /
`DIM Z(1845)` sized to leave ~26 B, then 26 string assignments to force the OOM. Under
the merge the same geometry leaves **123 B** and the chain completes with no OOM at
all, so at first reading this is only the row's own
[[a-coverage-row-whose-geometry-cannot-reach-the-case]] class, needing a re-size.
**It is not.** Walking N toward the new boundary
([`scratchpad/spmerge_squeeze_bisect.out`](scratchpad/spmerge_squeeze_bisect.out)):

| `DIM Z(N)` | `FRE(0)` after it | the 26-assignment chain |
|---|---|---|
| 1845 | 123 | completes, no OOM |
| 1855 | 2526 | completes, no OOM |
| **1857** | **no reading at all** | **no reading at all** |
| **1859** | **no reading at all** | **no reading at all** |
| 1861 | 14899 (the `DIM` itself failed) | completes |

`FRE` is not monotonic in N, and two values in the middle of the range produce NO
OUTPUT — the machine dies rather than raising ERR 7. That is the very failure this
row exists to catch, so re-sizing it to a value that happens to pass would be fixing
the test to match a defect.
⚠️ **WHAT IS NOT YET MEASURED, and is the first thing to do next:** whether the CLEAN
tree also dies at ITS OWN boundary. The row passes on clean at N=1845 because that
value leaves ~26 B there, which is nowhere near clean's boundary — so these two are
NOT the same experiment, and until the clean boundary is walked the same way, "the
merge introduced this" is unproven.

The whole slice is preserved at
[`scratchpad/d-spmerge-step4.patch`](scratchpad/d-spmerge-step4.patch) — the merge
plus the re-base, which SUPERSEDES `d-spmerge-step3k.patch` as the baseline.
🔴 **AND `fnf_save` STILL NEEDS §10.2's HALF** regardless: it allocates from a
page-0 tenant that never reaches `ctl_reloc`. The subagent implemented and verified
that arm — `trapsvc-acceptance` PASS on all seven rows, `deffn-acceptance` 0/73
with the denominator restored — at **63 B of sub page 0** (590 → 527 free), 0 B of
main. It is **preserved as a patch, not applied** —
[`scratchpad/d-spmerge-fnfsave.patch`](scratchpad/d-spmerge-fnfsave.patch), which
`git apply --check`s clean against the tree at `55450e28` — because it is only
correct WITH the merge: without `SP` in the region it would relocate an unrelated
block. It also tests the reserve where **SP would land**, not at the frontier,
because `FN` recursion grows the stack about 4× faster than it grows the pool.

### 10.5 Side finding, not part of this arc

An oversized `CLEAR n` (one that puts `CTLTOP` below `CTLLIM`; ERR 7 on the
reference) is accepted here, and the patch's CLEAR arm
([`basic/clear.asm:207`](basic/clear.asm:207)) then relocates the stack below the
floor — `CTLLIM=8027` with the block moved to `$68B0`, a dead machine. The
acceptance of the oversized `CLEAR` is a pre-existing gap the merge only makes
louder.
