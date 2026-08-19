# D-NXLIST — `NEXT` takes a LIST of loop variables

*Slice D-NXLIST, 2026-08-08, on `main`, based on `e966c0b` (D-FORVAR).*

D-FORVAR measured `NEXT B,A` on both references and **deferred** it, with
`n.multi1` as the proof that it is a different rule: the identical comma with
the single-letter names `ex_for` has always parsed is still `Syntax error`, so
no NAME fix can reach it ([[one-row-cannot-separate-two-rules]]). `nx_end` runs
`jp exec_stmt` once its frame is closed and the `,` arrives in statement
position.

🎯 **BOTH REFERENCES, EVERY ROW.** `FOR`/`NEXT` is core BASIC and a diskless
VG-8020 answers it, so every reading here has **two** independent oracles.

---

## 1. The rule — **measured before it was designed, in three rounds, two of which refuted a finished-looking design**

🔴 **TWO READINGS ARE NOT A RULE.** The filed residual carried `n.multi` and
`n.multi1`. They say a comma diverges. They do not say what the list *is*.

**28 rows, three sides, measured 2026-08-08 BEFORE a byte was written** —
[`nxlist-msx1-characterization.md`](nxlist-msx1-characterization.md) is the
table and **both references agree on all 28**. The rule that falls out:

> `NEXT` takes a **comma-separated list** of loop variables, and `NEXT B,A` is
> exactly `NEXT B : NEXT A`. Each element obeys `NEXT`'s own matching rule whole
> — both name characters **and** the resolved type — and closes any inner frames
> above the one it matches. The comma is read **only on the path where a frame
> CLOSES**. After a comma a variable is **required**: a comma followed by the end
> of the statement is **NEXT without FOR**, and a comma followed by anything else
> that is not a name is **Syntax error**.

🎯 **THE FOUR READINGS THAT DECIDED THE DESIGN ARE ONES THE FILED RESIDUAL COULD
NOT HAVE PREDICTED**, and each is a byte:

| row | reading | what it forces |
|---|---|---|
| `m.count` — inner-body executions under `NEXT B,A` | **` 6 `** | the comma test belongs on the loop-**ENDS** path only, and it is a NUMBER that says so, not an error face |
| `m.trail` — `NEXT B,` with an OUTER frame standing | **NEXT without FOR** | 🔴 a trailing comma is **not** a bare `NEXT`; §3 |
| `m.trailnum` — `NEXT B,1` | **Syntax error** | ...and not a blanket error either. The split is TERMINATOR vs not-a-name — which `ex_next` already makes |
| `m.ary9` — `NEXT A(99)` | **Subscript out of range** | 🔴 a `NEXT` operand is a full variable REFERENCE with its subscript EVALUATED — which prices `NEXT A(1)` out of this slice; §3.2 |

⚠️ **`m.trail` AND `m.trailnum` ARE THE ROWS THE DESIGN TURNS ON.** Together they
say the post-comma no-variable case must reach **ERR 1** while the post-comma
not-a-name case must reach **ERR 2** — and §4.2 buys exactly that for **one
byte**, because it is `ex_next`'s own existing split with a different sentinel
value.

---

## 2. What is wrong, in one sentence

* **`nx_end`** ([`basic/program.asm:1750`](../basic/program.asm)) — `pop hl` /
  `ld (FSP),hl` / `pop hl` / `jp exec_stmt`: the frame is closed and the cursor
  restored, and the statement dispatcher is handed a `,` it has no rule for.

---

## 3. Scope

**In:** the comma-separated `NEXT` list — two elements, three elements, elements
with two-character names and explicit type suffixes, an element that mismatches
by name and one that mismatches by TYPE, an element that closes inner frames on
its way, a negative STEP inside a list, spaces around the comma, a trailing comma
in four positions, a leading comma, a non-name after the comma, a `:`-separated
statement after the list, a `:` used INSTEAD of the comma, and the
loop-CONTINUES path measured as an inner-body COUNT. Plus — forced by §6.3's
carve, not chosen — **a `NEXT` with no `FOR` at all**, through both entries of
the frame-stack guard.

**Out, and named rather than implied:**

### 3.1 🔴 `NEXT A(1)` — DECLINED WITH A ROW, AND THE ROW IS `m.ary9`

The cheap fix is 8 bytes: after `for_name`, a `(` in the cursor makes the parsed
key unmatchable, so `nx_scan` walks the stack out and raises **NEXT without
FOR** — exactly D-FORVAR's `n.strnx` trick (§4.2 there), and exactly `m.ary`'s
measured answer.

**`m.ary9` refutes it.** `NEXT A(99)` reads **Subscript out of range** on both
references, so a `NEXT` operand is parsed as a *complete variable reference*
whose subscript is EVALUATED and range-checked before any match is attempted.
The 8-byte fix answers `NEXT without FOR` there, so it would **trade one red row
for another** ([[a-priced-decline-is-a-claim-about-a-design]]). `m.aryspc`
(`NEXT A (1)` → **NEXT without FOR**) adds that the `(` is not even lexically
contiguous, so the test would need `skip_spaces` too.

The faithful fix is an array-element reference parse in `ex_next` — the
D-ARYLV / lvalue family, not the LIST family, with its own price and its own
error-face questions. **Declined here, filed in `TODO.md` with all three
readings**, and all three rows stay MEASURED and PRINTED, scored in neither
direction.

### 3.2 Also out

* **A `$` element inside a list** (`NEXT B,A$`). D-FORVAR's `n.strnx` says a `$`
  `NEXT` name misses every frame, and this slice's design composes that
  unchanged — but composition is not a measurement and there is no row.
* **A list spanning a line boundary**, a list reached inside a `GOSUB` called
  from the loop body, and a list longer than three.
* **Nesting deeper than 8** — zerobas's fixed 8-frame stack and the references'
  stack-bounded limit are different mechanisms (D-FORVAR §9).

---

## 4. Design

### 4.1 🎯 THE COMMA IS TESTED WHERE THE FRAME CLOSES, AND NOWHERE ELSE

`m.count` is the reason this is a design constraint and not a placement
preference. `ex_next` has two exits:

* **`nx_again`** — the loop continues. It restores the frame's resume pointer,
  discards the post-`NEXT` cursor and `ret`s. It never reaches the terminator,
  so the rest of the list is *invisible* to it. **Unchanged by this slice.**
* **`nx_end`** — the frame closes. It restores the cursor and runs on.

So the whole fix is at `nx_end`:

```
nx_end:         pop     hl                  ; frame base -> pop the frame
                ld      (FSP),hl
                pop     hl                  ; the post-NEXT cursor
                call    skip_spaces         ; `NEXT B , A` -- row m.space
                cp      ','
                jp      z,nx_comma
                jp      exec_stmt           ; run on past NEXT
```

**8 → 16 bytes, +8.** `call skip_spaces` is 3 of those 8 and `m.space`
(`NEXT B , A` → ` 3  3 `) is the row that buys them.

### 4.2 🔴 THE BARE-`NEXT` SENTINEL *VALUE* CARRIES THE LIST STATE — ONE BYTE, NO FLAG, NO RAM

`nx_scan` reads `FOR_CUR+1` (name0) and treats **0** as *"match the top frame"*,
a value no real name0 can take because `is_letter` gated the parse. D-FORVAR
established that.

**Any other non-letter value there matches nothing**, walks the stack out and
raises `NEXT without FOR`. That is the whole of `m.trail`.

So the list entry differs from the ordinary entry by **the sentinel it parks**,
and by nothing else:

```
ex_next:        xor     a                   ; 0 = a bare NEXT matches the TOP frame
                jr      nx_head
nx_comma:       ld      a,1                 ; 🔴 1 = after a ',' a bare NEXT matches
                                            ;   NOTHING -- m.trail/m.trailc
nx_head:        ld      (FOR_CUR+1),a       ; parked; for_name overwrites it if a
                inc     hl                  ;   variable follows
                call    skip_spaces
                call    is_letter
                jr      nc,nx_notletter
nx_named:       call    for_name
                jr      nx_find
nx_notletter:   or      a                   ; `NEXT 1` and `NEXT B,1` are BOTH ERR 2
                jr      z,nx_find           ;   (n.num, m.trailnum) -- one test, and
                cp      COLON               ;   the parked sentinel decides whether a
                jp      nz,stmt_error       ;   TERMINATOR is ERR 1 or the top frame
                                            ; falls through to nx_find
```

🎯 **`nx_notletter` STOPS WRITING THE SENTINEL AND STARTS FALLING THROUGH**, and
that single change is what makes all four post-comma readings come out right at
once:

| program | path | answer |
|---|---|---|
| `NEXT` | sentinel 0, terminator | top frame ✓ `c.for` |
| `NEXT:PRINT` | sentinel 0, `:` | top frame ✓ `m.colon` |
| `NEXT 1` | sentinel 0, not a name | `stmt_error` ✓ `n.num` |
| `NEXT B,A` | sentinel 1, **overwritten** by `for_name` | matches `A` ✓ `m.two` |
| `NEXT B,` | sentinel 1, terminator | matches nothing → **ERR 1** ✓ `m.trail` |
| `NEXT B,:` | sentinel 1, `:` | matches nothing → **ERR 1** ✓ `m.trailc` |
| `NEXT B,1` | sentinel 1, not a name | `stmt_error` ✓ `m.trailnum` |
| `NEXT ,B` | sentinel 0, `,` is not a name | `stmt_error` ✓ `m.lead` |

**`ex_next` + `nx_comma` + `nx_head` + `nx_named` + `nx_notletter` = 30 bytes,
against 26 for `ex_next` + `nx_notletter` + `nx_top` today: +4.** The list entry
costs **two bytes** (`ld a,1`); the other two are the `xor a` / `jr` that turn
one head into two entries.

⚠️ **`nx_top` DIES**, and its `xor a` / `ld (FOR_CUR+1),a` become the two halves
of the shared head. Nothing outside `basic/program.asm` names it.

### 4.3 Funding carve A — the FOR stack has ONE bound test, not two

`nx_find` (*"is the stack empty?"*, 13 B) and `nx_miss` (*"did the walk run
out?"*, 15 B) end in the identical four instructions, and `nx_scan` then reloads
`(FSP)` to recompute the frame base. Merged, with the frame-base computation
folded into the test's own arithmetic:

```
nx_find:        push    hl                  ; save the post-NEXT cursor
                ld      hl,(FSP)
                jr      nx_bound
nx_miss:        pop     hl                  ; mismatch -> close this inner frame
                ld      (FSP),hl
nx_bound:       ld      de,-FOR_STK         ; HL = FSP - FOR_STK
                add     hl,de
                ld      a,h
                or      l
                jp      z,nx_nofor          ; ...zero -> no frame left at all
                ld      de,FOR_STK-FOR_FRAME
                add     hl,de               ; ...else HL = the top frame's base
nx_scan:        ld      a,(FOR_CUR+1)
                or      a
                jr      z,nx_have           ; a bare NEXT accepts the top frame
                push    hl
                ld      de,FOR_CUR
                ld      b,3                 ; name0, name1 AND the TYPE
nx_cmp:         ld      a,(de)
                cp      (hl)
                inc     hl
                inc     de
                jr      nz,nx_miss
                djnz    nx_cmp
                pop     hl                  ; falls through to nx_have
```

Three savings, each nameable: the two bound tests become one (`sbc hl,de` +
`or a` + a second `ld de` + a second `jp z`); the frame base is computed by
*continuing* the same subtraction instead of reloading `(FSP)` and adding
`-FOR_FRAME`; and `nx_cmp` **falls through** to `nx_have` instead of jumping,
because moving `nx_miss` above `nx_scan` turns its forward `jr` into a backward
one. **58 → 44, −14.**

### 4.4 Funding carve B — the limit comparison happens once, not twice

`nx_have` (positive step: end when `>` limit) and `nx_neg` (negative step: end
when `<` limit) each load the limit and call `cmp16_bits`. Only the wanted
verdict differs, and 🎯 **`cmp16_bits` touches A, HL, DE and the flags and
nothing else**, so the verdict can simply be carried in `B`:

```
                jr      nz,nx_neg
                ld      b,4                 ; step >= 0: end when value > limit
                jr      nx_limit
nx_neg:         ld      b,1                 ; step <  0: end when value < limit
nx_limit:       ld      de,(FOR_CUR+3)      ; limit
                call    cmp16_bits          ; 1 = < , 2 = = , 4 = >
                cp      b
                jr      z,nx_end            ; falls through to nx_again
```

**53 → 45, −8.** `m.step` (`FOR A=3 TO 1 STEP -1` inside a list → ` 0  3 `) is
the row this carve needs and the reason it is in *this* battery and not only in
D-FORVAR's.

### 4.5 RAM, and what does NOT change

**Nothing.** No cell is added, moved or retired; `FOR_CUR`, `FOR_STK`,
`FOR_FRAME` and `FSP` are all exactly as D-FORVAR left them. The list state lives
in a value the sentinel byte could already hold.

---

## 5. Forced constraints — each is a thing the design is NOT free to choose

### 5.1 🔴 THE COMMA TEST CANNOT MOVE EARLIER, AND `m.count` IS WHY

The tidy place for *"is there more list?"* is right after the match, before the
loop-continue fork — one test instead of one per exit. **`m.count` refutes it**:
` 6 ` is 3 × 2 inner-body executions, so the comma must be invisible while the
inner loop is still running. A design that tested early would read ` 3 ` there
and **`m.two` would still read ` 3  3 `** — the whole rest of the battery would
pass. This is the row that exists for the path a fix is most likely to break.

### 5.2 🔴 A TRAILING COMMA MUST *MISS*, NOT BE *BARE* — AND `m.trail1` CANNOT SAY SO

*"A comma with nothing after it is a bare `NEXT`"* costs zero bytes, re-uses
machinery that is already there, and predicts `m.trail1` **exactly right**
(`NEXT without FOR`, because that stack is empty anyway). `m.trail` is the same
program with an outer frame standing, and it reads `NEXT without FOR` where the
bare reading predicts ` 3  3 `. §4.2 spends **two bytes** (`ld a,1`) on the
difference.

### 5.3 🔴 AND IT MUST NOT BE A BLANKET ERROR EITHER

`NEXT B,1` is **Syntax error**, not `NEXT without FOR`. So the post-comma
no-variable case is not one disposition but two, split on *terminator vs not a
name* — which is `nx_notletter`'s existing split. Spending a guard here would
have cost bytes to produce the wrong message on one of the two rows.

### 5.4 The carve merges two guards into one, so the ROWS must carry the separation

§4.3 leaves a single `jp z,nx_nofor` where there were two. No cut can then
separate the `nx_find` entry from the `nx_miss` entry — so `n.nofor` /
`n.barenofor` (the `nx_find` entry) and `m.wrong` / `m.typex` (the `nx_miss`
entry) do it instead, and **no row in the D-FORVAR battery took the `nx_find`
entry at all**: every mismatching row there has one frame, so it errors from
`nx_miss`. The carve was unguarded until this battery existed.

---

## 6. The carve scout

All spans off `build/basic-reloc.sym` from a clean `rm -rf build && make
basic-reloc` at `e966c0b`; walls printed by that build (low **11 B**, page 1
**5 B**, sub p0 **3604 B**, sub p1 **1483 B**; `basic-reloc.rom cc7e3cbf…`,
`sub.rom accce5a1…`, `disk.rom 2c630d3d…`, `zerobas-main-eu.rom 0de562e4…`).

### 6.1 Which region each file lives in — asked before anything is priced

`python3 tools/carve_scout.py build/basic-reloc.sym --files <f>`:

| file | labels in page 1 | region | what this slice does there |
|---|---|---|---|
| `basic/program.asm` | **152 of 152** | **page 1** | every byte of this slice |
| `basic/vars.asm` | 59 of 59 | page 1 | untouched |
| `basic/interp.asm` | 79 of 79 | page 1 | untouched |
| `basic/arrays.asm` | 0 of 45 | LOW | untouched |
| `basic/input.asm` | 0 of 33 | LOW | untouched |
| `basic/str-engine.asm` | 0 of 103 | LOW | untouched |

🔴 **THIS SLICE WRITES TO EXACTLY ONE REGION, AND IT IS THE BINDING ONE.** Page 1
is at **5 B** and `basic/program.asm` is 152-of-152 in it. The low region's 11 B
is not reachable without moving a body across the boundary, which is legal
(page-1 → low always is) but buys nothing here: **the funding is inside the two
bodies being edited.**

### 6.2 The estimator, calibrated before it is used

Hand-counted from source and checked against the `.sym` **before** any number was
quoted for code that does not exist
([[calibrate-a-hand-counter-before-quoting-it]]):

| routine | hand-count | `.sym` span | |
|---|---|---|---|
| `for_name` | 14 | **14** | ✅ |
| `ex_for` | 63 | **63** | ✅ |
| `ef_step` | 4 | **4** | ✅ |
| `ef_havestep` | 48 | **48** | ✅ |
| `ef_over` | 10 | **10** | ✅ |
| `ex_next` | 16 → **14** | **14** | ✅ 🎯 *a body being edited* |
| `nx_notletter` | 8 | **8** | ✅ 🎯 *a body being edited* |
| `nx_top` | 4 | **4** | ✅ 🎯 *a body being deleted* |
| `nx_find` | 13 | **13** | ✅ 🎯 *a body being edited* |
| `nx_scan` | 19 | **19** | ✅ 🎯 |
| `nx_cmp` | 11 | **11** | ✅ 🎯 |
| `nx_miss` | 15 | **15** | ✅ 🎯 |
| `nx_have` | 42 | **42** | ✅ 🎯 |
| `nx_neg` | 11 | **11** | ✅ 🎯 |
| `nx_again` | 20 | **20** | ✅ |
| `nx_end` | 8 | **8** | ✅ 🎯 *the body the fix lands in* |
| `nx_nofor` | 11 | **11** | ✅ |

**17/17 exact**, and every one of the nine bodies this slice rewrites was counted
**instruction by instruction from the source**, not looked up. ⚠️ `LD (nn),DE` /
`LD DE,(nn)` are **4** bytes (`ED 53`/`ED 5B`), `LD (nn),BC` / `LD BC,(nn)` are
**4**, and `LD (nn),HL` / `LD HL,(nn)` are **3** — which is why `ld de,(FOR_CUR+3)`
is priced at 4 in §4.4 and `ld hl,(FSP)` at 3 in §4.3.

### 6.3 The cost — a BOUND, with the twin named for every part

| body | file | region | before | after | Δ |
|---|---|---|---|---|---|
| `ex_next` + **`nx_comma`** + `nx_head` + `nx_named` + `nx_notletter` (§4.2; `nx_top` folded in and deleted) | program.asm | p1 | 26 | **30** | **+4** |
| `nx_find` + `nx_miss` + **`nx_bound`** + `nx_scan` + `nx_cmp` (§4.3) | program.asm | p1 | 58 | **44** | **−14** |
| `nx_have` + `nx_neg` + **`nx_limit`** (§4.4) | program.asm | p1 | 53 | **45** | **−8** |
| `nx_end` (§4.1) | program.asm | p1 | 8 | **16** | **+8** |
| `nx_again`, `nx_nofor`, `for_name`, `ex_for`, `ef_*` | program.asm | p1 | 106 | **106** | **0** |
| `for_get` / `for_set` / `vnk_dollar` | vars.asm | p1 | — | — | **0** |
| low region / sub page 0 / sub page 1 / RAM | — | — | | | **0** |
| **main page-1 total** | | | **251** | **241** | **−10** |

### 6.4 The bottom line — **no carve is needed, and the wall ends RICHER**

| region | free at `e966c0b` | slice | free after |
|---|---|---|---|
| **main page 1** | **5 B** | **−10** | **≈ 15 B** |
| **main low** | 11 B | 0 | **11 B** |
| sub page 0 | 3604 B | 0 | **3604 B** |
| sub page 1 | 1483 B | 0 | **1483 B** |
| RAM | — | 0 | unchanged |

⚠️ **THE MEMORY INDEX SAID "NOTHING LANDS HERE WITHOUT A CARVE SCOUT" AND IT WAS
RIGHT — THE SCOUT IS WHAT FOUND THE FUNDING.** The filed sketch was *"≈+11 B at
`nx_end`, which does not fit"*, and the sketch is not wrong about `nx_end`: that
body really does grow by 8, and the design it sketched (re-enter the name parse
after a label) would have grown it by more, because it had no answer for
`m.trail` or `m.trailnum`. What the sketch never priced is the **other side of
the ledger**: the same 200 bytes of `ex_next` carry two guards that were written
twice and one comparison that was written twice, and this slice was going to be
reading all of them anyway. **22 bytes of duplication pay for 12 bytes of rule**
([[which-wall-binds-is-a-history-question]]).

⚠️ **A BOUND, not a measured cost.** The instrument is calibrated (§6.2, 17/17)
and every body is written out as the assembly that will be assembled, but the
real number comes from a build ([[filed-justification-is-a-claim]]).

⚠️ **Predicted ROM hashes**, all four, including which should HOLD
([[a-wall-is-a-size-a-hash-is-an-identity]]):
`basic-reloc.rom` **MOVES**; `zerobas-main-eu.rom` **MOVES**; `disk.rom`
**HOLDS at `2c630d3d…`** — no disk-side byte is written; and 🎯 **`sub.rom`
HOLDS at `accce5a1…`**. `sub/basic-resident-abi.inc` is generated from main's
`.sym` on every build and D-ARYLV recorded `sub.rom` moving while its walls
held — but all **11** exported addresses (`fp_add $34B7` … `vars_reset $3DAD`)
are in the **LOW** region, and this slice writes **no low-region byte at all**.
Page-1 addresses are not exported, so nothing the sub-ROM can see moves.

### 6.5 ✅ VERDICT: **GO, self-funded.** −10 B against a 5 B wall, zero low-region and zero sub-ROM bytes, zero RAM, and `NEXT A(1)` DECLINED with a row rather than with a budget.

---

## 7. Predicted GREEN — the reference column IS the prediction

`make nxlist-characterize` must read, on the VG-8020, the CF-3300 and zerobas
alike (⚠️ **two references per row**, so a row that agrees agrees three ways):

| row | prediction | |
|---|---|---|
| `c.for` / `c.next` / `c.nest` | ` 4 ` / ` 4 ` / ` 3  3 ` | 🟢 **controls** — green before **and** after |
| `m.two` `m.name` `m.three` | ` 3  3 ` / ` 3  3 ` / ` 3  3  3 ` | the list itself |
| `m.inner` | ` 4  3 ` | asymmetric bounds |
| `m.count` | ` 6 ` | 🎯 **§5.1 — the CONTINUES path, as a number** |
| `m.type` | ` 3  3 ` | a typed element |
| `m.typex` `m.wrong` | `NEXT without FOR` | an element obeys `NEXT`'s own match |
| `m.deep` | ` 3  3  1 ` | a list element closes inner frames on its way |
| `m.step` | ` 0  3 ` | 🎯 **§4.4's row** |
| `m.trail` | `NEXT without FOR` | 🎯 **§5.2 — a MISS, not a bare `NEXT`** |
| `m.trail1` `m.trail2` | `NEXT without FOR` | the same with an empty stack |
| `m.trailc` | `NEXT without FOR` | a `:` after the comma |
| `m.trailnum` | `Syntax error` | 🎯 **§5.3** — green before **and** after |
| `m.lead` | `Syntax error` | green before and after |
| `m.space` | ` 3  3 ` | the row that buys `nx_end`'s `skip_spaces` |
| `m.after` | ` 3  3 ` | a `:` statement after the list |
| `m.colon` | ` 3  3 ` | 🎯 green before **and** after — the row that separates "the comma" from "any separator" |
| `n.nofor` `n.barenofor` | `NEXT without FOR` | 🔴 **the CARVE's rows** — green before **and** after |
| `n.num` | `Syntax error` | 🔴 **NEGATIVE control** — green before **and** after |
| `m.ary` / `m.aryspc` | `NEXT without FOR` | ⏸ **DEFERRED**, printed, never scored (§3.1) |
| `m.ary9` | `Subscript out of range` | ⏸ **DEFERRED** — 🎯 the row that priced the decline |

⇒ **`make nxlist-acceptance` scores 25/25** (28 cases − 3 deferred), from
**9/25** at `e966c0b`.

⚠️ **25 is the SCOPE, not a row count** — §9 names what is left out
([[a-prediction-copied-into-the-result-column]]).

⚠️ **Classify a control failure by WHICH SIDE failed it** — red on a reference =
the fixture is broken (exit 2, score nothing); red on zerobas = an ordinary
divergence, scored ([[classify-a-control-failure-by-which-side-failed-it]]). All
three positive controls and the negative control are green on all three sides
**today**, so either side going red is the instrument.

And the document that has been counting this surface must move:

* `make forvar-acceptance` — **33/33** (up from 31/31): `n.multi` and `n.multi1`
  stop being DEFERRED there, because this is the slice they were deferred for.
  ⚠️ Its `f.ary` row must stay green — it is the same negative control.

Static counters, each predicted by reading its own check's definition rather than
by counting what this slice writes
([[a-count-is-predicted-by-reading-its-definition]]): `audit-citations` sweeps
**FILES** and this slice adds **three** (this document, the characterization
table and the probe), so 751 → **754** swept, basic provenance-bearing 196 →
**197** (+1 per real `probes/basic/*.py`); `injector-check` 343 → **344**;
`rowshape-check` 184/37/13/13/0 → **185/38/14/14/0**; `preflight-check`
**181/86/95/95/0 unchanged**; `latch-check` **16/16 unchanged**; `deadcode`
**0/0 (+1 allowlisted) unchanged** — ⚠️ *load-bearing here*: `nx_top` is deleted
rather than left reachable-by-fallthrough-only, and `nx_scan` survives only as
the fallthrough label inside `nx_bound`; sub page-0 closure **733 + 15, 14
tenants unchanged**; sub page-1 closure **585 + 43 unchanged**; resident ABI
closure **122 + 4 unchanged**; `unit-test` **59 unchanged** — no host test names
`nx_*`.

---

## 8. Knives — drafted BEFORE the row set was frozen

Runner discipline is **not** restated here: read
[`dev-workflow.md`](dev-workflow.md) §"Knives" first. `probe_report.parse()`
ships — do not hand-roll a row parser and never diff report LINES. Restore in a
`finally`; `rm -rf build` + full rebuild + repack before every run **including
each baseline**; **assert the ROM hashes MOVED after every cut build** (a
probe-only cut must NOT move them); run every cut TWICE. Cut a label's **BODY**,
not its reference. ⚠️ **A knife may only name symbols the side it edits can
SEE**, and ⚠️ **check that the invocation the runner makes can still REACH the
property being cut**.

The knife subject is the probe **`--sides zb`** for every cut except K-NL7: the
reference columns are constants and a cut in zerobas can only move zerobas.

Write `R` for the sixteen rows whose program contains a comma that reaches a
closed frame: `m.two m.name m.three m.inner m.count m.type m.typex m.wrong
m.deep m.step m.trail m.trail1 m.trailc m.trail2 m.space m.after`.

| # | cut (byte-neutral unless noted) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-NL1** | `nx_end`: `jp z,nx_comma` → 3 × `nop` — the comma is recognised and then ignored, i.e. the fix reverted at its last instruction | **`R`** (16) | the other 9. 🎯 **`m.trailnum` included** — its reference answer *is* `Syntax error`, so reverting the fix cannot move it |
| **K-NL2** | `nx_end`: `cp ','` → `cp COLON` — the separator is the colon | 🎯 **`R` ∪ {`m.colon`}** (17) — K-NL1's set plus exactly one row | the other 8 |
| **K-NL3** | `nx_end`: `call skip_spaces` → `ld a,(hl)` + 2 × `nop` | 🎯 **`m.space` ONLY** | the other 24 |
| **K-NL4** | `nx_comma`: `ld a,1` → `xor a` + `nop` — §4.2 reverted: a trailing comma becomes a BARE `NEXT` | 🎯 **`m.trail`, `m.trailc` ONLY** | the other 23 — 🔴 **`m.trail1` and `m.trail2` included, and that is the point**: their frame stack is empty at the comma, so a bare `NEXT` misses there anyway. This is §5.2's finding as a cut |
| **K-NL5** | `nx_bound`: `jp z,nx_nofor` → 3 × `nop` — the merged frame-stack guard | **`n.nofor`, `n.barenofor`** (the `nx_find` entry) **+ `m.typex`, `m.wrong`, `m.trail`, `m.trail1`, `m.trailc`, `m.trail2`** (the `nx_miss` entry). Reported as a SET; the shape may be a sentinel rather than an error string, because the scan then walks below `FOR_STK` | the controls and every matching row |
| **K-NL6** | `nx_neg`: `ld b,1` → `ld b,4` — a negative-step loop ends on the positive-step verdict | 🎯 **`m.step` ONLY** | the other 24 |
| **K-NL7** | `CONTROL_WANT["c.nest"]` made unmatchable (probe-only), against **`--sides vg8020,zb`** | exit **2**, 0 scored, `NOT MEASURED`, and the ROMs must **NOT** move | — (proves the probe fails closed) |

**Three cuts redden exactly the rows that exist for them, and two redden exactly
ONE row each** (K-NL3, K-NL6). All six red sets are **pairwise distinct** —
checked before the row set was frozen, which is what D-FORVAR §10.5(b) cost a
re-measurement to learn.

🔴 **K-NL4 IS THE KNIFE FOR THE ROUND-2 FINDING, AND IT NEEDS BOTH TRAILING-COMMA
FORMS.** `m.trail1` (`FOR B` / `NEXT B,`) was measured first and is **green under
its own knife**: with an empty frame stack a bare `NEXT` misses too, so it agrees
with the reference for the wrong reason. Only `m.trail`, which leaves an OUTER
frame standing, can tell. A battery containing just `m.trail1` would have scored a
clean sweep against a rule that is wrong ([[one-row-cannot-separate-two-rules]]).

⚠️ **`m.count` HAS NO CUT, AND THAT IS STATED RATHER THAN HIDDEN.** §5.1's defect
is an **addition** — testing the comma before the loop-continue fork — and knives
cut. The row is here because a *design* alternative needed refuting, not because
a byte of shipped code can be removed to expose it.

⚠️ **K-NL7 IS SITED AGAINST `--sides vg8020,zb`, NOT `--sides zb`.** The control
check skips a lone `zb` by construction — only a REFERENCE can say the apparatus
is broken — so the narrowed invocation the other six cuts use would make this
path structurally unreachable and score a false rc 0
([[a-shadowed-guard-has-no-knife]]).

---

## 9. Denominator

Scored by `nxlist-acceptance`: **(LIST LENGTH: 1 / 2 / 3) × (ELEMENT: matching
name / mismatching name / mismatching TYPE / two-char name) × (DEGENERATE:
trailing comma with an outer frame / with none / after a full list / before a
`:` / leading comma / a non-name after the comma / spaces around the comma)**,
plus the CONTINUES path as an inner-body COUNT, plus a list element that closes
inner frames on its way, plus a negative STEP inside a list, plus termination by
`:` after the list and by a `:` used INSTEAD of the comma, plus a `NEXT` with no
`FOR` at all through **both** entries of the frame-stack guard, plus three
positive controls and one negative control.

**Not covered, and named rather than implied:** `NEXT A(1)` and its subscript
evaluation (§3.1 — measured, divergent, DEFERRED with its own residual and its
own priced decline); a `$` element inside a list (`NEXT B,A$`); a list spanning a
line boundary; a list reached inside a `GOSUB` called from the loop body; a list
longer than three; and nesting deeper than 8, where zerobas's fixed 8-frame stack
and the references' stack-bounded limit are different mechanisms and neither is
measured against the other.

---

## 10. As-built

Implemented 2026-08-08 on `main`, based on `e966c0b`.

### 10.1 What landed

| file | change |
|---|---|
| [`basic/program.asm`](../basic/program.asm) | `nx_end` reads the `,` and jumps to the new `nx_comma`; `ex_next`/`nx_comma` become two entries to one head that differ only in the sentinel they park; `nx_notletter` stops writing the sentinel and falls through to `nx_find`; `nx_top` **deleted**; `nx_find`/`nx_miss` merged into `nx_bound` with the frame-base computation folded in; `nx_cmp` falls through to `nx_have`; `nx_have`/`nx_neg` merged into `nx_limit` |
| [`probes/basic/basic_probe_nxlist.py`](../probes/basic/basic_probe_nxlist.py) | **new**, 28 rows, 3 positive + 1 negative control, 3 deferred |
| [`probes/basic/basic_probe_forvar.py`](../probes/basic/basic_probe_forvar.py) | `DEFERRED` is now **empty** — `n.multi`/`n.multi1` were deferred *for this slice* |
| [`Makefile`](../Makefile) | `nxlist-characterize` + `nxlist-acceptance`, both `.PHONY` |

### 10.2 The walls, measured from clean — **all five exact**

| wall | at `e966c0b` | §6.4 predicted | as built | |
|---|---|---|---|---|
| **main page 1** | 5 B | ≈15 B (−10) | **15 B** | ✅ |
| **main low region** | 11 B | unchanged | **11 B** | ✅ |
| sub page 0 | 3604 B | unchanged | **3604 B** | ✅ |
| sub page 1 | 1483 B | unchanged | **1483 B** | ✅ |
| RAM | — | unchanged | **unchanged** | ✅ |

🎯 **AND ALL THIRTEEN PREDICTED SPANS LANDED TO THE BYTE** — `ex_next` 3,
`nx_comma` 2, `nx_head`(+`nx_named`) 17, `nx_notletter` 8, `nx_find` 6,
`nx_miss` 4, `nx_bound` 13, `nx_scan` 12, `nx_cmp` 9, `nx_have`+`nx_neg`+
`nx_limit` 45, `nx_again` 20, `nx_end` 16, `nx_nofor` 11. The four block totals
are **30 / 44 / 45 / 16** against the predicted 30 / 44 / 45 / 16. The reason is
§6.2: the counter was calibrated **17/17** against the `.sym` before it was
quoted for code that did not exist
([[calibrate-a-hand-counter-before-quoting-it]]). Fourth slice running.

### 10.3 The ROM hashes — **all four predicted before the build**

| ROM | at `e966c0b` | §6.4 predicted | as built |
|---|---|---|---|
| `basic-reloc.rom` | `cc7e3cbf…` | MOVES | **`2cce96c3…`** ✅ |
| `sub.rom` | `accce5a1…` | 🎯 **HOLDS** | **`accce5a1…`** ✅ |
| `disk.rom` | `2c630d3d…` | **HOLDS** | **`2c630d3d…`** ✅ |
| `zerobas-main-eu.rom` | `0de562e4…` | MOVES | **`38668085…`** ✅ |

`sub.rom` holds because all 11 resident-ABI addresses are LOW-region and this
slice writes no low-region byte — a stronger claim than D-FORVAR's, which
depended on *where* in the low region its one edit sat
([[a-wall-is-a-size-a-hash-is-an-identity]]).

### 10.4 The gates — every counter on its predicted value

| gate | before | predicted | measured |
|---|---|---|---|
| **`nxlist-acceptance`** | 9/25 | 25/25 | **25/25 agree, 0 diverge, 3 deferred** ✅ |
| **`forvar-acceptance`** | 31/31 + 2 def | **33/33** | **33/33, 0 deferred** ✅ |
| `unit-test` | 59 | 59 | **59** ✅ — no host test names `nx_*` |
| `audit-citations` swept / basic | 751 / 196 | 754 / 197 | **754 / 197** ✅ |
| `injector-check` | 343 | 344 | **344** ✅ |
| `rowshape-check` | 184/37/13/13/0 | 185/38/14/14/0 | **14 probes, ALL PASS** ✅ |
| `preflight-check` | 181/86/95/95/0 | unchanged | **181/86/95/95/0** ✅ |
| `latch-check` | 16/16 | unchanged | **16/16** ✅ |
| sub page-0 closure | 733 + 15, 14 tenants | unchanged | **733 + 15, 14** ✅ |
| sub page-1 closure | 585 + 43 | unchanged | **585 + 43** ✅ |
| resident ABI closure | 122 + 4 | unchanged | **122 + 4** ✅ |
| `deadcode` main / sub | 0 / 0 (+1) | unchanged | **0 / 0 (+1)** ✅ |

### 10.5 🔴 Three things went differently, and each is a finding

**(a) THE MEASUREMENT REFUTED THE DESIGN TWICE, AND BOTH REFUTATIONS CAME FROM
ROWS ADDED AFTER A ROUND WAS ALREADY "DONE".** Round 1 (21 rows) produced a
complete, self-consistent rule with a design that fit. `m.trail` — added in
round 2 only because the task asked what a trailing comma does — killed the
zero-byte *"a trailing comma is a bare `NEXT`"* reading, and `m.trailnum` then
killed its replacement (*"a comma demands a variable, else ERR 1"*). Round 3's
`m.ary9` killed the 8-byte `NEXT A(1)` fix. 🎯 **Each refuted design was cheaper
than the one that shipped**, which is the whole argument for measuring first:
the cheap designs were not wrong-looking, they were wrong.

**(b) AND THE FINAL DESIGN IS CHEAPER THAN ALL OF THEM.** Being forced onto
`nx_notletter`'s *existing* terminator/not-a-name split — because the two error
faces are both live — is what turned the list entry into **two bytes**
(`ld a,1`). The design that only had to satisfy round 1 needed a separate
post-comma parse head and cost **+13**. The measurement did not merely correct
the design; it found the one the code was already shaped for.

**(c) THE CARVE WAS UNGUARDED, AND THE ROW SET SAYS SO OUT LOUD.** §5.4:
merging `nx_find`'s and `nx_miss`'s frame-stack tests removes the possibility of
a cut that separates them, and **no row in the 33-row D-FORVAR battery enters
through `nx_find`'s** — every mismatching row there has exactly one frame, so it
errors from `nx_miss`. `n.nofor` / `n.barenofor` were added for the carve, not
for the fix, and they are green before **and** after. K-NL5 reddens both entries'
rows together, which is the honest shape once one test serves both.

### 10.6 Knives — 7 cuts × 2 rounds, **7 EXACT, both rounds identical**

Runner: throwaway in the scratchpad, never committed. Subject = the probe invoked
directly, `--sides zb` (the reference columns are constants). Snapshot restore in
a `finally`; `rm -rf build` + full rebuild + repack before every run including
each baseline; ROM-hash guard per cut; rows via `probe_report.parse()` compared as
`{label → zb value}` with a row-count refusal. **No flakiness on any cut.**

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-NL1** | `nx_end`: `jp z,nx_comma` → 3 × `nop` | the 16 comma rows | **exactly those 16**, all → `Syntax error` | ✅ ×2 |
| **K-NL2** | `nx_end`: `cp ','` → `cp COLON` | those 16 **+ `m.colon`** | **exactly 17** | ✅ ×2 |
| **K-NL3** | `nx_end`: `call skip_spaces` → `ld a,(hl)` + 2 × `nop` | 🎯 **`m.space` ONLY** | **`m.space` ONLY** | ✅ ×2 |
| **K-NL4** | `nx_comma`: `ld a,1` → `xor a` + `nop` | 🎯 **`m.trail`, `m.trailc` ONLY** | **exactly those two** — `m.trail` ` 3  3 `, `m.trailc` `OK` | ✅ ×2 |
| **K-NL5** | `nx_bound`: `jp z,nx_nofor` → 3 × `nop` | 8 rows, both guard entries | **exactly those 8** | ✅ ×2 |
| **K-NL6** | `nx_neg`: `ld b,1` → `ld b,4` | 🎯 **`m.step` ONLY** | **`m.step` ONLY**, ` 0  3 ` → ` 2  3 ` | ✅ ×2 |
| **K-NL7** | `CONTROL_WANT["c.nest"]` unmatchable, `--sides vg8020,zb` | rc **2**, `NOT MEASURED`, ROMs unmoved | **rc 2 + banner, ROMs held** | ✅ ×2 |

🎯 **K-NL4 IS §10.5(a) AS A CUT, AND IT NEEDED BOTH TRAILING-COMMA FORMS.** With
the sentinel reverted to `xor a`, `m.trail` reads ` 3  3 ` — the bare `NEXT`
closes the outer loop, exactly what the refuted design predicted — while
**`m.trail1` and `m.trail2` stay GREEN**, because their frame stack is already
empty at the comma and a bare `NEXT` misses there for the wrong reason. A battery
holding only `m.trail1` would have scored a clean sweep against a wrong rule
([[one-row-cannot-separate-two-rules]]).

⚠️ **K-NL5 REPORTED TWO DIFFERENT SHAPES, AND BOTH ARE RED.** The two `nx_find`
rows read `<Syntax error>` and the six `nx_miss` rows read `<NO OUTPUT>` — the
scan walks below `FOR_STK` and what it finds there differs by entry. The
prediction was written as a SET with the shape left open, which is why this
scored EXACT rather than "off".

🔴 **AND K-NL6 REDDENS WITH A WRONG NUMBER, NOT AN ERROR.** ` 0  3 ` → ` 2  3 `:
the negative-step loop ends two iterations early and the program runs on. That is
the shape a merged comparison fails in, and `m.step` exists in this battery
precisely because D-FORVAR's `f.step` is in a different one.

### 10.7 Corpus

Sequentially from clean (`rm -rf build`, **bash** — `zsh` does not word-split
`make $t`), **29 targets, all rc=0, 14 min 52 s wall**: `unit-test` 59 ·
`audit-citations` CLEAN (754 swept) · `preflight-check` 181/86/95/95/0 ·
`injector-check` 344 · `rowshape-check` 14 probes · `latch-check` 16/16 ·
`deadcode` 0/0 · `lnblank-acceptance REPEAT=2` · `lnblank-say-acceptance`
204/204 · `logicops-acceptance` · `float-acceptance` · `linemax-acceptance`
60/60 · `dexp5-pin` 16 · `editverb-acceptance` 61/61 · `lptverb-acceptance`
44/44 · `dskmsg-acceptance` 5/5 · `diskbasic-acceptance` 34/34 verbs ·
`fat-error-acceptance` · `runtail-acceptance` 9/9 · `castail-acceptance` ·
`cassave-acceptance` 20/20 · `readvar-acceptance` 24/24 ·
`arylv-acceptance` 18/18 · `inputary-acceptance` 7/7 · `lvfix-acceptance` ·
`fldary-acceptance` · `lrvar-acceptance` · **`forvar-acceptance` 33/33** ·
**`nxlist-acceptance` 25/25**.

⚠️ `latch-check` still has **no `repack-machine` prerequisite**, so the script
builds explicitly before the loop rather than letting the first target do it.

### 10.8 The fix, as a program

Both columns are readings from the runs above.

```basic
10 FOR A=1 TO 2
20 FOR B=1 TO 2
30 NEXT B,A
40 PRINT "[";A;B;"]"
```

| | screen after `RUN` |
|---|---|
| Philips VG-8020 / National CF-3300 | `[ 3  3 ]` |
| zerobas **before** | `Syntax error in 30` |
| zerobas **after** | `[ 3  3 ]` |

🎯 **The comma is invisible while the inner loop is still running**, and only a
COUNT can see it:

```basic
10 N=0
20 FOR A=1 TO 3
30 FOR B=1 TO 2
40 N=N+1
50 NEXT B,A
60 PRINT "[";N;"]"
```

| | screen after `RUN` |
|---|---|
| both references / zerobas **after** | `[ 6 ]` — 3 × 2 |
| zerobas **before** | `Syntax error in 50` |
| a design that tested the comma one fork earlier | `[ 3 ]` — and **every other row still green** |

And the row that refuted the cheap design, which needs an outer loop to say
anything at all:

```basic
10 FOR A=1 TO 2
20 FOR B=1 TO 2
30 NEXT B,
40 PRINT "[";A;B;"]"
```

| | screen after `RUN` |
|---|---|
| both references / zerobas **after** | `NEXT without FOR in 30` |
| under **K-NL4** (a trailing comma treated as a bare `NEXT`) | `[ 3  3 ]` — 🔴 the outer loop closed, and with `FOR B` alone this row is green either way |

Finally the pair that fixes the error FACE, one byte apart in the parser:

```basic
10 FOR A=1 TO 2
20 FOR B=1 TO 2
30 NEXT B,1
```

| | screen after `RUN` |
|---|---|
| both references / zerobas **before and after** | `Syntax error in 30` — 🟢 not `NEXT without FOR`, which is what `NEXT B,` answers |
