# D-SCRERR — SCREEN's mode is a checked byte, and nothing is applied until it has passed

Settled contract. The measurement notebook is
[`screenerr-msx1-characterization.md`](screenerr-msx1-characterization.md); the
gate is `make screenerr-acceptance`.

## 1. The rule

> **`SCREEN`'s mode argument is an ordinary CHECKED BYTE ARGUMENT — the same
> two-stage coercion `WIDTH`, `ON n` and the string engine use — narrowed by one
> further test to 0..3, and every one of those rejects happens BEFORE `CHGMOD`.**

Three corollaries the denominator forced, none of them in the two filed items:

> **An argument list that ENDS where a value was required is `Missing operand`
> (ERR 24)**, at all four of `ex_screen`'s such slots.

> **Every trailing argument is a checked byte too**, and the FIRST of them — the
> sprite size — has its own domain `0..3`.

> **An OMITTED argument still occupies its slot.** `SCREEN 1,,99` sets the key
> click, not the sprite size.

## 2. What was measured

61 rows on three sides. **Both references agree on every row**; there is no row
without an oracle. Full tables in the characterisation note §2; the shape:

### 2.1 The mode domain

| statement | VG-8020 / CF-3300 | zerobas before |
|---|---|---|
| `SCREEN 0` … `SCREEN 3` | accepted | accepted |
| `SCREEN 4`, `5`, `255` | ERR 5 | **ERR 2** |
| `SCREEN -1`, `SCREEN (1<5)` | ERR 5 | **ERR 2** |
| `SCREEN 256`, `32767`, `-32768` | ERR 5 | **ERR 2** |
| `SCREEN 32768`, `-32769` | ERR 6 | **ERR 2** |
| `SCREEN 70000` | ERR 6 | **accepted — silently SCREEN 0** |
| `SCREEN 1.4` / `1.6` / `3.6` | modes 1 / 1 / 3 | same |
| `SCREEN "1"`, `SCREEN Q$` | ERR 13, mode unchanged | ERR 13, **mode 0 applied** |

`-32768` is ERR 5 and `-32769` is ERR 6: the int16 stage accepts the **range**
−32768..32767, not the magnitude |x| ≤ 32767. That is precisely the contract
[`basic/interp.asm`](../basic/interp.asm) already records for `get_byte_arg`,
pinned there at `CHR$(-32768)`/`CHR$(-32769)`. Meeting the same asymmetric
boundary again from an unrelated verb is the strongest available evidence that it
is one shared rule and not two coincidences — and it is why the fix is a
substitution rather than a new guard.

Truncation, not rounding: `1.6` → mode 1, and `3.6` → mode **3** where rounding
would give a mode 4 that is ERR 5 — a different CODE, not merely a different mode.

### 2.2 The argument list

| statement | both references | zerobas before |
|---|---|---|
| `SCREEN`, `SCREEN :` | ERR 24 | **silent no-op** |
| `SCREEN ,`, `SCREEN 2,`, `SCREEN 2,,`, `SCREEN 2,:` | ERR 24 | **silent no-op** |
| `SCREEN ,1`, `SCREEN ,,1`, `SCREEN ,,,1` | accepted | accepted |
| `SCREEN 1,3` | accepted, size applied | accepted |
| `SCREEN 1,99`, `SCREEN 1,-1` | ERR 5 | **accepted (`and $03`)** |
| `SCREEN 1,70000` | ERR 6 | **accepted** |
| `SCREEN 1,,99` | accepted | accepted *(but see §4)* |
| `SCREEN 1,,300` | ERR 5 | **accepted** |
| `SCREEN 1,,70000` | ERR 6 | **accepted** |

### 2.3 The ordering, measured as SCRMOD rather than scraped

| statement | refs: code, mode left behind | zerobas before |
|---|---|---|
| `SCREEN 0*(1/0)` | 11, mode **1** | 11, mode **0** |
| `SCREEN 2+0*(1/0)` | 11, mode **1** | 11, mode **2** |
| `SCREEN 2+0*SQR(-1)` | 5, mode 1 | 5, mode 2 |
| `SCREEN 2+0*(1E38*1E38)` | 6, mode 1 | 6, mode 2 |
| `SCREEN (Q$<5)` | 13, mode 1 | 13, mode 0 |
| `SCREEN 70000+0*(1/0)` | **11** (not 6) | — |
| `SCREEN 70000+0*SQR(-1)` | **5** (not 6) | — |
| `SCREEN 2,0*(1/0)` | 11, mode **2** | 11, mode 2 |
| `SCREEN 2,"A"` | 13, mode **2** | 13, mode 2 |

🎯 **THE LAST TWO ROWS ARE WHAT MAKE THIS A RULE ABOUT ONE ARGUMENT.** A fault in
a *trailing* argument is reported with the mode already legitimately applied, on
all three sides — so `SCREEN` does not validate everything and then act. It
validates the mode, applies it, and carries on. A "validate fully, then apply"
restructure would have been the wrong fix, and zerobas already agreed on those
two rows before the slice: the brief's warning not to assume the two filed items
share a mechanism was worth honouring. They share a routine and an ordering, but
the ordering is local to the mode argument.

The last two rows of the numeric block are what pick `eval_byte_checked` over the
cheaper `eval_byte_arg`, whose own coercion *also* aborts on a pending code — but
only after overwriting it. `70000+0*(1/0)` → 11 and `70000+0*SQR(-1)` → **5**, a
different code, says the rule is "a fault that already happened outranks the
coercion" and not "division by zero is special". Same rule as D-EVALCHK's at
`WIDTH`, re-measured independently here.

## 3. The design, and its price

**NET ZERO BYTES**, hand count EXACT at both intermediate builds.

| # | site | change | B |
|---|---|---|---|
| S1 | `ex_screen` mode | `call eval` + two hand-rolled `jp stmt_error` rejects → `call eval_byte_checked` / `cp 4` / `jp nc,gb_illegal` | **−6** |
| S2 | `ex_screen` ×4 | `jp z,exec_stmt` → `jp z,loc_missing` at all four empty-slot tests | **0** |
| S3 | `scr_extra` | `call eval` → `call eval_byte_checked` | **0** |
| S4 | `spr_extra_arg` | `and $03` → `cp 4` / `jp nc,gb_illegal` | **+3** |
| S5 | `scr_extra` | count the argument slot at the COMMA (§4) | **+7** |
| S6 | `spr_extra_arg` | its own increment, now redundant, deleted | **−4** |

`cp 4` cannot be folded into the coercion: **4 is a valid byte**, so the mode
domain needs a test of its own on top of `get_byte_arg`'s. That is the one place
the cheap hypothesis ("SCREEN should just call `get_byte_arg`") is incomplete,
and it was flagged in the brief before the first row was read.

## 4. 🔴 The defect the fix EXPOSED, which no row could previously see

`a.clk` (`SCREEN 1,,99`) went **red on zerobas and only on zerobas** after S3+S4
landed. The cause is older than the slice:

`ex_screen` counted the argument position in `spr_extra_arg`, i.e. **at the
value**. The `,,` arm loops back without evaluating anything, so an OMITTED
argument was never counted and every argument after one was off by one slot.
`SCREEN 1,,99` therefore applied 99 as the **sprite size**.

It had been wrong the whole time and was invisible, for two compounding reasons:
the old `and $03` quietly turned 99 into a legal size 3, and **a wrong sprite
size does not appear in `SCRMOD`** — the cell the whole probe reads. It became
visible only when the new domain check turned it into an error the reference does
not raise.

🔴 **AND THAT IS MEASURED ON THE BASE ROM, NOT INFERRED FROM THE FIX.** The
before-column was re-run on a reverted tree that reproduces `3dc1e7b`'s four ROM
hashes exactly, and `a.sprskip` — `SCREEN 2,,3 : IF LEN(SPRITE$(0))<>8 THEN
ERROR 99` — reads ` 99 , 2 ` there against ` 0 , 2 ` on both references. So the
claim is "the fix exposed a defect that was already shipping", with the shipping
defect in hand, and not "the fix broke a neighbour". ⚠️ **A tightened check is a detector for the code around it**, and
this is the second time in this arc that closing one divergence surfaced a
neighbour ([[knife-found-defect-in-own-fix]]).

Commas and argument slots are 1:1, so S5 counts at the comma — which is both
correct and *cheaper*, because it lets S6 delete the counting `spr_extra_arg` was
doing (+7/−4 rather than the +10 a `spr_skip_arg` helper would have cost).

🔴 **AND THE ERROR CODE WAS THE WRONG WITNESS FOR IT.** `a.clk` only detects the
position rule while the misplaced value has a domain to violate. Rows
`a.sprskip` / `a.sprslot1` were added to witness the **size itself**, through its
one reference-visible consequence — `LEN(SPRITE$(0))` is 8 for an 8×8 sprite and
32 for a 16×16 one — with `a.sprslot1` as the control that proves the witness
discriminates at all.

## 5. The instrument

🔴 **THE SUBJECT OF THIS SLICE IS THE SCREEN, AND THE OBVIOUS READING IS A SCREEN
SCRAPE.** That is why D-STMTPEND deferred `u.scr.dz` rather than scoring it: the
statement reinitialises the display before it reports, so the `RUN` echo the
reading anchors on is gone and the probe reads `<NO ECHO>` — not a wrong message,
*no* message. The same wall stopped its scouting from the other side (`SCREEN 1`
→ `<NO CAPTURE>` on **both** references).

So this probe does not scrape the mode, it **asks** for it: every trapped row
reads `[ ERR , PEEK(&HFCAF) ]` — code and resulting mode — captured in the
handler, over a `SCREEN 1` seed, with line 50 forcing `SCREEN 0` so the PRINT is
readable whatever mode the subject left behind. See the characterisation §1.

## 6. As-built

### 6.1 The walls — the hand count was EXACT at both stages

| wall | `3dc1e7b` | S1–S4 | as built | Δ |
|---|---|---|---|---|
| main low region | 14 B | 14 B | **14 B** | 0 |
| main page 1 | 48 B | 51 B | **48 B** | 0 |
| sub page 0 | 3604 B | 3604 B | **3604 B** | 0 |
| sub page 1 | 1483 B | 1483 B | **1483 B** | 0 |

### 6.2 The gate

`make screenerr-acceptance` — 61 rows × 3 sides.

| | before | after |
|---|---|---|
| rows agreeing | **22 / 61** | **61 / 61** |

(The row set grew from 49 to 61 while the slice ran: 10 `a.*` neighbours added
*before* the fix was written, because a `jp`-target change cannot tell them
apart and moving four unmeasured rows silently is a scope claim; 2 `o.*` rows
that pick the routine; 2 `a.spr*` position rows the exposed defect demanded.
🔴 **A ROW SET THAT GROWS INVALIDATES EVERY KNIFE PREDICTION WRITTEN AGAINST IT**
— D-NAMSPC's lesson; the knife predictions here were re-frozen after the last
row landed.)

`make stmtpend-acceptance` **57/57 scored + 1 deferred** (was 56/58 + 2):
**`u.scr.dz` is un-deferred and agreeing.**

### 6.3 Corpus

Sequentially from clean (`rm -rf build`, then `repack-machine` **first** — D-PENDERR
§10.4's lesson: `latch-check` has no such prerequisite and would otherwise boot a
machine config pointing at ROMs that do not exist). **43 targets**: D-STMTPEND's
40 plus `screenerr-acceptance` (new), `graphics-acceptance` and
`badfnum-acceptance` (both pulled in because this slice touches `graphics.asm`
and `ex_screen`'s argument loop). 24 min wall.

`unit-test` **59/59** (see below) · `audit-citations` CLEAN ·
`preflight-check` **95 guarded / 0 unguarded** · `injector-check` **354** files
(+1) · `rowshape-check` **25** probes (+1) · `latch-check` **16/16** ·
`screenerr-acceptance` **61/61 (new)** · `stmtpend-acceptance` **57/57 + 1
deferred** · `penderr-acceptance` **61/61** · `tmfp-acceptance` **50/50** ·
`width-acceptance` **94/94** · `locarg-acceptance` **45/45** ·
`namspc-acceptance` **58/58** · `fldwidth-acceptance` **40/40 (+2 deferred)** ·
`onerr0-acceptance` **24/24** · `missing-acceptance` **214/214** ·
`graphics-acceptance` PASS · `diskbasic-acceptance` **34/34 verbs** ·
`lnblank-acceptance` **539/539** · `lnblank-say-acceptance` **204/204** ·
`logicops-acceptance` **193/193** · `clearpool-acceptance` **52/52**, plus the
remaining 20 gates.

⚠️ `rowshape-check` and `injector-check` GROW with the corpus, so the previous
slice's figure is a prediction and not a baseline. Scored, not assumed.

### 6.4 🔴 `make unit-test` went RED, and it was right to

`tests/test_screen.py` asserted **"bare `SCREEN` → `CHGMOD` not called"** — the
old silent no-op — and was **the only thing in the tree that encoded that
contract**. Four of its rows (modes 0..3) still pass unchanged; the bare-`SCREEN`
row failed, and not with a clean assertion: the new `jp z,loc_missing` reaches
`raise_error`'s `ld sp,(SAVSTK)` funnel, `SAVSTK` is 0 in the host harness's
zeroed RAM, and the CPU **runs away** — `msxtest` raised `StackLost`.

The harness's own diagnostic said what to do (*"Fix the TEST, not the ROM: trap
the funnel and sample the state THERE"*), which is exactly the T-RUNAWAY
remedy `tests/test_poke.py`'s ERRMARK row already uses. The row now traps
`raise_error` and asserts **ERR 24 with `CHGMOD` never called**, and a second row
was added for the domain half — `SCREEN 4` → **ERR 5**, `CHGMOD` never called,
which is the *ordering* claim stated as a host-testable invariant rather than
only as an emulator row. 59/59, and the four ROM hashes are unchanged by it.

📏 The lesson is about the corpus, not the test: an emulator gate measured the
new behaviour on three sides and was completely green while a 20-line host test
still held the old contract. **The cheap emulator-free layer is where a
superseded contract survives**, because nothing about it looks stale.

## 7. Knives

Five cuts on the shipped tree, each run **twice**; both rounds agreed on every
row, so nothing here is a D-FEVERB-style round-to-round flake. All cuts
byte-neutral, all four ROMs hashed after every cut build, restore from a
scratchpad snapshot in a `finally`, rows parsed with `probe_report.parse()`.
A sixth knife (§8.3) cuts the **probe** instead.

| knife | cut | predicted RED | result |
|---|---|---|---|
| K-SE1 | the mode's `cp 4` reject → 3 `nop` | `d.4` `d.5` `d.255` `u.4` | **EXACT** ×2 |
| K-SE2 | `eval_byte_checked` → `eval_byte_arg` | `o.dzov` `o.5ov` | **MISS** ×2 (§8.1) |
| K-SE3 | the four `jp z,loc_missing` → `jp z,exec_stmt` | the six ERR-24 rows | **EXACT** ×2 |
| K-SE4 | the sprite domain's `jp nc,gb_illegal` → 3 `nop` | `a.sprbad` `a.sprneg` | **MISS** ×2 (§8.2) |
| K-SE5 | the comma-side slot counter → 7 `nop` | `a.sprbad` `a.sprneg` `a.sprslot1` | **MISS** ×2 (§8.2) |

Every predicted-GREEN set held exactly, in every knife, in both rounds.

K-SE1's degradations are worth reading rather than counting: `d.4`/`d.5`/`d.255`
become ` 0 , 1 ` — CHGMOD is *called* with the illegal mode and the statement
completes — and `u.4` becomes `[RANON]`, i.e. the untrapped program runs on to
its next line. The cut does not merely change a code, it removes a refusal.

## 8. 🔴 What the three misses actually found

### 8.1 K-SE2 refuted this slice's own justification

The source comment at the call site claimed `o.dzov` / `o.5ov` are what pick
`eval_byte_checked` over the cheaper `eval_byte_arg`, whose coercion aborts on a
pending code only *after* overwriting it. **Swapping the two moved nothing, in
both rounds, including those two rows.**

The reason is **D-PENDERR**: every writer into the pending-error cell is now
*set-if-empty*, so `fac_to_int_strict`'s ERR 6 can no longer overwrite a live
code at all. D-EVALCHK's stated justification for the checked leaf —
[`spec-basic-evalchk.md`](spec-basic-evalchk.md): *"it does WRITE FPERR=1 on an
out-of-int16 magnitude, OVER THE TOP of the pending FPERR=2"* — **was true when
it was written and was made false by D-PENDERR a few commits later, on the same
day.** Nothing regressed; a load-bearing reason quietly stopped being one.

The leaf is kept: same 3 bytes, same routine `WIDTH`/`FIELD`/`CLEAR` use, and it
states the ordering explicitly. What changed is the comment, which now says the
rows do **not** discriminate. `o.dzov`/`o.5ov` still earn their place — they pin
the **rule** (a fault that already happened outranks the coercion); they simply
do not pin the **routine**, and claiming they did was wrong.

### 8.2 `SCREEN 1,99` and `SCREEN 1,-1` are caught by DIFFERENT stages

Both K-SE4 and K-SE5 predicted `a.sprneg` red and both missed it, twice. Cutting
the sprite-size domain check moves `SCREEN 1,99` and **not** `SCREEN 1,-1`,
because a negative value never reaches the domain check: the caller's byte stage
rejects a set high byte first. The two rows read identically (` 5 , 1 `) and look
like one class; they are two. **Only `a.sprbad` tests the 0..3 domain** — a
partition no green run could have shown, and the reason both cuts are in the
record even though both "failed".

### 8.3 K-SE6 — the knife against the INSTRUMENT, run on the PRE-FIX tree

Cut: the `SCREEN 1` seed on line 20 of the trapped template. Run against the
reverted tree (base ROM hashes reproduced), so the defect is still live.

**Predicted**: the rows whose target mode is 0 stop discriminating and the probe
scores a live defect as AGREEING — `o.dz0`, `o.tm`, `d.str`, `d.strv`; the rows
whose target mode is 2 stay red — `o.dz`, `o.s5`, `o.ov`. **EXACT.** Four rows
flipped DIFF → ok with the tree still broken; three stayed red; both positive
controls held.

So the seed is load-bearing for exactly four of the 61 rows, and they are now
named. This is [[t.zero-is-blind-to-a-cut-that-also-disables-its-seed]] asked
*before* it could bite instead of after.

## 9. Filed, not folded in

* The **third** trailing argument's domain (`SCREEN 1,,,300`) is unmeasured. The
  first two are pinned; the loop treats 3+ identically to 2, so the risk is a
  reference that narrows a later slot. One row, no scouting done.
* `spr_extra_arg`'s `GFX_SFLAGS` sibling was not re-examined against the new slot
  numbering. It is written by `PUT SPRITE`, not by `SCREEN` — every reference to
  it is in the `ex_put_sprite` cluster and its sub-ROM tenant — so the counter
  this slice moved is not shared. Checked by walking the references, not assumed;
  not gated.
* `a.spr` (`SCREEN 1,3`) is **blind** to a cut that stops the sprite size being
  applied: K-SE5 reddened `a.sprslot1` and left `a.spr` untouched, because
  `a.spr` reads only the error code and a size that is never applied raises
  nothing. Recorded, not changed — `a.sprslot1` covers it, and `a.spr` is still
  the row that says an in-domain size is *accepted*.

## 10. 🔴 D-SCRSLOT — slot 3 is 1..2, and the arity stops at five

§2 pinned slot 1 (sprite size) to 0..3 and slot 2 (key click) to 0..255, and
left a filed risk: `scr_extra` treats **every** slot after the first exactly like
slot 2, so a reference that *narrows* a later one would be an unmeasured
divergence. Measured 2026-09-04, twelve rows, both references agreeing on all
twelve.

| row | statement | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `t.b1` | `SCREEN 1,,,1` | ok | ok | ok |
| `t.b2` | `SCREEN 1,,,2` | ok | ok | ok |
| `t.b0` | `SCREEN 1,,,0` | **ERR 5** | **ERR 5** | 🔴 ok |
| `t.b3` | `SCREEN 1,,,3` | **ERR 5** | **ERR 5** | 🔴 ok |
| `t.b300` | `SCREEN 1,,,300` | ERR 5 | ERR 5 | ERR 5 |
| `t.bneg` | `SCREEN 1,,,-1` | ERR 5 | ERR 5 | ERR 5 |
| `t.bbig` | `SCREEN 1,,,70000` | ERR 6 | ERR 6 | ERR 6 |
| `t.p0` / `t.p1` / `t.p2` | `SCREEN 1,,,,n` | ok | ok | ok |
| `t.p300` | `SCREEN 1,,,,300` | ERR 5 | ERR 5 | ERR 5 |
| `t.s6` | `SCREEN 1,,,,,1` | **ERR 2** | **ERR 2** | 🔴 ok |

**Slot 3 is the cassette baud rate and its domain is `1..2`** — not the 0..255
byte `scr_extra` applies. **Slot 4 (printer) really is byte-wide**, so the
narrowing is specific to slot 3 rather than general to "later slots", which is
the shape the filing could not have guessed. And the **argument list stops at
five**: a sixth slot is a *Syntax error*, i.e. the arity is bounded by the
parser, where `scr_extra`'s loop accepts commas indefinitely.

🎯 **`t.b1`/`t.b2` and `t.b300`/`t.bneg` are what make this a domain reading.**
Without the accepted pair, a row refusing `0` and `3` would be equally consistent
with "the slot rejects everything"; without the refused pair, with "the slot
checks nothing". Both pairs agree on all three machines, so the divergence is
precisely *"0 and 3 are accepted here and refused there"*.

### ⚠️ Measured and priced, NOT fixed

Both `scr_extra` (`basic/screen.asm`) and `spr_extra_arg`
(`basic/graphics.asm`) are in **main page 1**, which `make basic-reloc` reports
at **6 bytes free**. `spr_extra_arg` already dispatches on `GFX_SARGN`, so the
slot-3 arm is the natural home — `ld a,e / dec a / cp 2 / jp nc,gb_illegal`
behind a slot test, about **12 B**, with the arity bound another **8**. That does
not fit, and the three rows are `DEFERRED` in the gate with that price attached
rather than silently left out.

🔴 **Re-price before inheriting this.** A decline resting on a wall reading is a
decline resting on a figure that rots — the `CLEAR`/TRAPSTK item sat deferred on
*"2 B free"* and turned out to be a 3 B fix against 333 B
[[repricing-page1-slice]].
