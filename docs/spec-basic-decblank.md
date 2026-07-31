# D-DECBLANK — blanks inside a decimal literal

*Status: **LANDED 2026-07-31 — 81/81 at `--repeat 2`, 39 B, all sub-ROM,
falsified on five knives.** Signed off with D-EXPBAD (§5.1) filed rather than
fixed.*

Split out of [D-LNBLANK](spec-basic-lnblank.md) on 2026-07-31, where it was the
*unfiled* half of the finding. The TODO had described a **line-number** scan that
skips blanks; measurement showed blank-transparency is a property of the
**decimal number scanner**, of which the line number is merely one customer
([`docs/lnblank-msx1-characterization.md`](lnblank-msx1-characterization.md)
§11 D).

Measurement: [`docs/decblank-msx1-characterization.md`](decblank-msx1-characterization.md).
Gate: `make lnblank-acceptance` (the `dec` battery is new; the five `lit-` rows
are already live as pinned `KNOWN_DIVERGE` entries and **retiring them is part of
this slice**).

---

## 0. The headline, in one row each

```
20 A=1 0     ref -> A <EF> <0F><0A>                 the single literal 10
20 A=1 .5    ref -> A <EF> <1D>A<15><00><00>        1.5, across the dot
20 A=1 E2    ref -> A <EF> <1D>C<10><00><00>        100, across the exponent marker
20 A=1 #     ref -> A <EF> <1F>A<10>…               a DOUBLE 1, across the suffix
20 A=. 5     ref -> A <EF> <1D>@P<00><00>           0.5 — and this one is not even in tk_float
20 A=1 +2    ref -> A <EF> <12> <F1><13>            ⚠️ THE BLANK SURVIVES
```

⚠️ **The last row is the one that sizes the fix, and no row filed with the item
could have produced it.** Every row the TODO carried puts the blank *between two
things that both belong to the number*. `dec-trail` puts it in front of something
that does not — and the blank stays. The scanner is **not** blank-blind; it looks
past blanks and keeps them unless it actually consumes what it finds.

---

## 1. The sites

All four are in the **sub-ROM**, page 0. `basic/tokenise.inc` is `include`d by
[`sub/sub.asm:209`](../sub/sub.asm:209) **and by nothing else** — the whole
tokeniser body was evicted there in subrom wave 2 — so this slice does not touch
the main ROM at all. See §6.1 for the assertion that makes that checkable rather
than asserted.

| # | site | file |
|---|---|---|
| S1 | the `'.'`-led entry (`.5`), which looks exactly one char past the dot | [`basic/tokenise.inc:68`](../basic/tokenise.inc:68) |
| S2 | `tkf_scan_digits` — the mantissa digit runs, integer and fractional | [`sub/tkfloat.asm:161`](../sub/tkfloat.asm:161) |
| S3 | the `'.'` test between the two digit runs | [`sub/tkfloat.asm:61`](../sub/tkfloat.asm:61) |
| S4 | `tkf_try_exponent` — the marker, the sign, and the exponent's own digits | [`sub/tkfloat.asm:229`](../sub/tkfloat.asm:229) |
| S5 | `tkf_try_suffix` — `!` / `#` / `%` | [`sub/tkfloat.asm:327`](../sub/tkfloat.asm:327) |

⚠️ **S1 is in the other file and a fix aimed at `tk_float` cannot reach it.**
`20 A=. 5` is 0.5 on both references; zerobas stores `.` verbatim, then a blank,
then the integer 5. The dispatch in `tk_loop` demands a digit *immediately* after
the dot, and no amount of blank-transparency inside `tk_float` changes a decision
taken before `tk_float` is entered. This cell exists only because the battery
asked about the entry as well as the scanner — the D-NOTOPEN2 lesson, where 3 of
7 rows gave a different answer than all 7.

`tk_hex` ([`basic/tokenise.inc:286`](../basic/tokenise.inc:286)) is **not** a
site: measured, it does not skip, for `&H` *and* for `&O` (§2, R-D5).

---

## 2. The rule — measured on two machines that agree on all 32 rows

Four oracle-lock rounds, VG-8020 and CF-3300, `--repeat 2`, every payload past
the echo guard first. Full tables in
[`docs/decblank-msx1-characterization.md`](decblank-msx1-characterization.md).

> **R-D1 — a blank run is transparent when the scan ACCEPTS what follows it.**
> `1 0` → 10, `1  0` → 10 (any run), and the same across every internal seam of
> the literal: the dot from either side (`1 .5`, `1. 5`), the exponent marker
> (`1 E2`, `1 E 2`), the exponent's sign (`1E -2`, `1E- 2`), the exponent's own
> digits (`1E 2 3` → 1E23), and a type suffix (`1 #`, `1 %`, `1 !`).

> **R-D2 — a blank run the scan does NOT accept past is left ALONE, all of it.**
> `1 +2` keeps its blank; `1  +2` keeps **both**. There is no separator blank
> eaten here. ⚠️ **This is where the decimal literal differs from the line
> number**, which eats exactly one ([D-LNBLANK](spec-basic-lnblank.md) R3) — so
> "copy `parse_lineno`" is the wrong instruction, and only `dec-trail2` says so.

> **R-D3 — equivalently, and this is the form to implement: the cursor the scan
> reports is one past the last character it actually CONSUMED.** Lookahead may
> cross any number of blanks; only consumption commits them.

> **R-D4 — the joined value flows through classification unchanged.**
> `3 2 7 6 7` → `<1C><FF><7F>` (a two-byte integer); `3 2 7 6 8` → a single. The
> int/float boundary is decided on the value the blanks produced, and the pair
> differs by one so neither row can agree for the wrong reason.

> **R-D5 — where it stops.** `&H1 F` → `&H1` then ` F`; `&O1 7` → `&O1` then
> ` ` then `7`; a string literal, a `REM` tail, a `DATA` body and a variable name
> all keep their blanks verbatim. **A fix written as "make the crunch's digit
> fetch blank-transparent" is wrong, and only the radix rows say so.**

### 2.1 What R-D3 buys that R-D1 does not

`1 EX` stores a **single 1.0 followed by `X`** on both references: the blank *and*
the `E` are consumed even though the exponent is malformed. Under R-D3 that is
one sentence — the scan consumed the `E`, so the blanks before it went with it —
and it tells the implementation exactly what a *rollback* has to undo. See §5.1:
zerobas' rollback is a separate defect, and R-D3 is what keeps this slice from
silently inheriting it.

---

## 3. What zerobas does today — 9/29 on the new battery

`make lnblank-characterize SIDES=vg8020,cf3300,zb ONLY=dec` (baseline captured
before any edit): **8/27** over rounds 1-3, plus round 4's two dot-led rows in
their own pass (`dec-dotlead0` agrees, `dec-dotlead` diverges) = **9/29**. The
five `lit-` rows already carried in `KNOWN_DIVERGE` are additional to these.

The eight rows that agree are the controls (`dec-ctl`, `dec-hexctl`,
`dec-dotlead0`), the two that must not move (`dec-trail`, `dec-trail2`), and the
three bounding cells (`dec-neg`, `dec-oct`, `dec-data`). ⚠️ **`dec-trail` and
`dec-trail2` agree today for a reason the fix must not remove**: zerobas stops at
the blank, which happens to be right when nothing follows it. They are the
sharpest must-not-move cells in the slice, and they are exactly the shape of cell
that caught the regression D-BADFNUM's signed-off design shipped.

Everything else diverges: `1  0`, `1 .5`, `1. 5`, `1 E2`, `1E- 2`, `1E -2`,
`1 #`, `1 %`, `3 2 7 6 7`, `3 2 7 6 8`, `1 0E 2`, `1 E 2`, `1E 2 3`, `1 !`,
`1 .X`, `. 5`.

---

## 4. The fix

A single helper plus a mechanical edit at each of the five sites.

```
; tkf_fetch: A = the first non-blank character at or after (HL); HL = its
; address. The caller PUSHes HL first and either POPs AF (accept: the blank run
; belonged to the number, R-D1) or POPs HL (reject: the run is not ours, R-D2).
tkf_fetch:      ld      a,(hl)
                cp      ' '
                ret     nz
tkf_f_lp:       inc     hl
                ld      a,(hl)
                cp      ' '
                jr      z,tkf_f_lp
                ret
```

* **S2 `tkf_scan_digits`** — `push hl` / `call tkf_fetch` at the loop head; the
  two range tests branch to a `pop hl` / `ret` tail instead of `ret c` / `ret nc`;
  the accept path `pop af`. `tksd_advance`'s `inc hl` is already relative to the
  digit's own address and stays correct.
* **S3 the dot test** — same shape; accept falls into the existing `inc hl`.
* **S4 `tkf_try_exponent`** — the `push hl` moves to the **top of the routine**,
  before the marker is fetched, so `tke_fail`'s existing `pop hl` rolls back to
  the cursor *before the blank run* and not to the marker. The sign and first
  exponent digit need no rollback of their own: one push covers the routine, which
  is what makes `1 E+X` come out right. `tke_dloop` gets its own push/fetch/pop
  pair, nested outside the multiply's existing `push hl`.
* **S5 `tkf_try_suffix`** — push/fetch at the top; the three arms converge on one
  `pop af` / `inc hl` / `ret` tail, which is **smaller** than the three `inc hl` /
  `ret` tails it replaces.
* **S1 the `'.'` entry** — the one-character lookahead becomes
  `inc hl` / `call tkf_fetch`, inside the existing `push hl` / `pop hl`. Two bytes.

### 4.0 🔴 The trap the first cut hit — `pop af` LOADS A

The discard on the accept path is `pop af`: the pushed HL has to come off the
stack, and AF is the register pair nothing else is using. **It is not a no-op —
it loads A from the stack**, i.e. with the source pointer's high byte. Written in
its natural place, immediately after the accept branch and *before* the digit is
extracted:

```
20 A=1      ->  A <EF> <0F><BB>       the integer 187
20 A=10     ->  A <EF> <1C><09><08>   the integer 2057
20 A=1E2    ->  REFUSED (empty program)
```

— every numeric literal in the language, wrong, and `1E2` overflowing the crunch
and refusing the line outright. The fix is one line of ordering: `sub '0'` and
`ld b,a` first, `pop af` after. Both accept paths (`tkf_scan_digits`, `tke_dloop`)
have it; the exponent commit (`pop de`) and the suffix tail were already safe
because A is reloaded or already stored there.

⚠️ **The build was green and the diff read correctly.** `make basic-reloc` passed,
the dead-code gate passed, the main ROM was byte-identical — and the ROM was
catastrophically broken. It took the first gate run to see it, which is the
standing lesson of this project stated once more:
[[gate-during-implementation]], and *the whole apparatus is part of the
measurement*.

### 4.1 Budget

**Landed at 39 B** (estimate was ≈ 55), all in sub-ROM page 0: its `$FF` tail went
**4057 → 4018 B free**. Main page 1 is unchanged at **8 B** and the low region at
**23 B** — `build/basic-reloc.rom` and `build/zerobas-main-eu.rom` came out
**byte-identical to HEAD** (`1d270536…`, `90403dbb…`), which is the whole space
argument of §4.1 checked rather than asserted. Part of the saving is §4's suffix
tail, which is *smaller* than the three it replaced.

**Estimate was ≈ 55 B, all in sub-ROM page 0, which had 4057 B free** (measured from
`build/sub.rom`'s `$FF` tail — the sub-ROM pads with `$FF`, so a trailing-zero
scan reports 0 and is wrong, [`docs/rom-region-structure-review.md:32`](rom-region-structure-review.md:32)).

⚠️ **The space warning in the handoff does not apply to this slice, and the check
that says so is free**: main page 1 is at 8 B and the low region at 23 B, but
neither file this slice edits is assembled into the main ROM. `build/basic-reloc.rom`
and `build/zerobas-main-eu.rom` must come out **byte-identical to HEAD**. That is
asserted in §6.1, not assumed.

---

## 5. Out of scope — measured here, filed, NOT fixed

Each of these was found *by this battery*, is pinned to its exact current value in
`KNOWN_DIVERGE`, and goes red the day it is fixed.

### 5.1 🔴 D-EXPBAD — a malformed exponent, with no blank anywhere near it

| row | typed | reference | zerobas |
|---|---|---|---|
| `dec-expbad0` | `20 A=1EX` | `<1D>A<10><00><00>X` (single 1, `E` **eaten**) | `<12>EX` (integer 1, `E` left) |
| `dec-expbadsg0` | `20 A=1E+X` | `<1D>A<10><00><00>X` | `<12>E<F1>X` |

The reference **consumes** a marker and sign that turn out not to introduce an
exponent, and the mere presence of the marker forces the literal to single
precision. zerobas rolls back and leaves the `E` for the ordinary tokeniser —
own-design, and its header
([`sub/tkfloat.asm:216`](../sub/tkfloat.asm:216)) says in as many words that it is
own-design rather than oracle-pinned. **Both rows carry no blank at all**, which
is what makes this a separate defect and not this one; attributing it here would
be the D-MFDOM trap of closing an item on a measurement belonging to another.

⚠️ It constrains this slice anyway. Under R-D3 the blanked forms (`1 EX`,
`1 E+X`) must keep reading **exactly what they read today** — `<12> EX` and
`<12> E<F1>X` — because a rollback that unwinds the marker has to unwind the
blanks in front of it too. Those two cells are pinned as must-not-move, and they
are the only witness that the fix rewinds the whole run rather than half of it.

### 5.2 `&B` is not a radix on either reference — and zerobas half-crunches it

`20 A=&B1 1` stores `&B1 1` **verbatim** on both references (so MSX1 BASIC has no
binary literal, and `B1` is just a variable name). zerobas stores `&B1 <12>` — it
crunches the trailing `1` to an integer token. Informational, non-gating, filed.

### 5.3 A trailing blank at end of line is NOT MEASURABLE with this instrument

`20 A=1 ` reads `A<EF><12>` on both references and `A<EF><12> ` on zerobas — but
the control `20 REMX `, whose tail is verbatim on every MSX, reads `<8F>X` on
**all three**. A blank that cannot survive a `REM` tail never reached the crunch,
so the two rows contradict each other and neither can ground a rule.

⚠️ **And the echo guard cannot referee it**: `echo_missing()` `rstrip`s every
screen row, so a trailing blank is invisible to the guard no matter what the
machine did with it. Both rows are informational **by construction** — a payload
whose delivery cannot be verified may not gate. Resolving the cell needs a
delivery path that bypasses the line editor (an ASCII `LOAD"CAS:`, the way
`basic_probe_floatlit.py` reaches literals). Filed as its own item.

### 5.4 Unchanged from D-LNBLANK

The missing `$0E` references for `LIST`/`DELETE`/`AUTO`/`RENUM`/`ELSE` (and the
three verbs that have no token at all) stay filed and untouched.

---

## 6. Falsification

Every knife keeps the code **reachable** — `make basic-reloc` runs a hard
dead-code gate (0 dead in both builds) and a knife that orphans a block fails the
build and measures nothing. So each knife changes a *constant* or *saturates to a
different value*, the shape D-LNBLANK's five knives ended up with.

| # | knife | prediction | witness |
|---|---|---|---|
| K1 | `tkf_fetch`'s `cp ' '` → `cp $00` (never a blank; the routine still runs and returns (HL)) | every `dec` and `lit` row falls back to today's baseline | `dec-run2`, `lit-assign` red; `dec-ctl`, `dec-trail` **stay green** |
| K2 | the accept path `pop af` → `pop hl` in `tkf_scan_digits` (commit becomes a rewind) | digits rejoin but the cursor rewinds each iteration | `lit-assign` red in a *different* way than K1 — the byte pattern separates "did not skip" from "skipped and did not commit" |
| K3 | S4's `push hl` moved back below the marker fetch (i.e. today's rollback target) | `1 EX` / `1 E+X` start eating the blank while still rolling the `E` back | `dec-expbad` / `dec-expbadsg` red — the two must-not-move cells of §5.1, which nothing else in the battery covers |
| K4 | S5's reject `pop hl` → `pop af` | a suffix that is not there still swallows the blank run | `dec-trail` red — **the green control turns red**, which is the only way to show that row is load-bearing |
| K5 | S1 reverted to the one-character lookahead | `. 5` regresses, everything entered on a digit stays green | `dec-dotlead` red alone — proves S1 is a second site and not a duplicate of S2 |

⚠️ **A knife must pair its red rows with a green control**, and K1/K4 are the two
that carry it explicitly. K4 is the important one: `dec-trail` agrees *today*, so
without a knife that turns it red there is no evidence the fix's reject path is
doing anything at all.

### 6.0 Result — five knives, five distinct witnesses

Each knife was built (`make basic-reloc` + `make repack-machine`, dead-code gate
0/0 every time) and measured against the VG-8020, then reverted.

| # | measured | control that stayed GREEN |
|---|---|---|
| K1 | **17/38** — every `lit-` and `dec-` transparency row fell back to the pre-fix baseline | `dec-ctl`, `dec-trail`, `dec-trail2`, `dec-hexctl`, `dec-oct`, `dec-data`, `dec-dotlead0`, `dec-dotx0`, `lit-ctl`, `lit-str`, `lit-rem` |
| K2 | `1 0` → **100** (`<0F>d`) and `1  0` → **1000** (`<1C><E8><03>`) — the digit re-consumed once per rewind, a *different* wrong answer than K1's `<12> <11>` | `dec-ctl`, `dec-trail`, `dec-trail2` |
| K3 | `1 EX` → `<12>EX` and `1 E+X` → `<12>E<F1>X`: the blank eaten, the marker still rolled back. **The allowlist fired by name** ("KNOWN_DIVERGE no longer describes zerobas") | `dec-exppre` (`1 E2`, the *well-formed* exponent) and **`dec-expbad0`/`dec-expbadsg0`, the no-blank rows** — the knife moved only the blanked pair, which is the pins doing exactly the job §5.1 claims |
| K4 | `1 +2` → `<12><F1><13>` and `1  +2` likewise — **the two rows that agree today went red** | `dec-ctl`, `dec-run2`, and all three suffix rows `dec-sfxh` / `dec-sfxp` / `dec-sfxb` |
| K5 | `dec-dotlead` red **alone** (`. 5` → `. <16>`) | `dec-dotlead0`, `dec-dotpre` (a blank before a dot *inside* a literal, which S2/S3 own) and `dec-run2` — so S1 is a genuinely separate site, not a duplicate of S2 |

⚠️ **K2 and K3 are byte-neutral** (`pop af`↔`pop hl`, two instructions swapped),
so neither has a symbol witness — the behavioural witness is the whole evidence,
which is why each was chosen to produce a reading *no other knife produces*.

---

## 6.1 Gates

| gate | expectation |
|---|---|
| `build/basic-reloc.rom`, `build/zerobas-main-eu.rom` | **byte-identical to HEAD** — this slice edits no main-ROM input |
| `make basic-reloc` dead-code gate | 0/0 both builds |
| `make lnblank-acceptance` | all `lit-` entries **retired from `KNOWN_DIVERGE`**; `dec` battery green except the §5.1 pins |
| `make linemax-acceptance` | 60/60 — ⚠️ **the one to watch**: its `tok`/`bnd` batteries measure crunch expansion byte-for-byte, and joining `1 0` shortens a body while `1 #` (integer→double) *lengthens* one. Its payload comment ([`basic_probe_linemax.py:139`](../probes/basic/basic_probe_linemax.py:139)) was already rewritten once by D-LNBLANK; re-read it before calling a red row a regression |
| `make unit-test` | 55/55 |
| the rest of the corpus | `badfnum` 93 · `lof` 45 · `chancost` 53 (allowlist empty) · `diskbasic` 34/34 · `bdos` 12/12 · `fat-error` 8/8+dir · `error-trap` · `abort` 49/49 · `stop-trap` · `arrdim` 73/73 · `clearpool` 52/52 · `array` 149/151 (the two standing rows confirmed **by name**: `ifc.instr.zero`, `ifc.instr.neg`) |

All met. Final gate run was `--repeat 2` on all three sides: **81/81, every row
stable across two independent boots**.

### 6.2 🔴 The apparatus finding — a DETERMINISTIC mangle is still a mangle

`make error-trap-acceptance` went red on `tc_next_nofor`, **4 runs out of 4**,
reading `";ERR;"`. HEAD was green. Every instinct says regression.

It was not. `read_R` returns the *last* `R<…>` on the screen, and `";ERR;"` is
what you get from the echo of the case's own `100 PRINT"R<";ERR;">"` when no
result row exists. Dumping the screen said why in four lines:

```
ZBN ERROR GOTO 100        <- `10 O` was EATEN by the injector
syntax error
ZB20 NEXT
next without for in 20    <- nothing armed, so nothing printed R<…>
```

The payload was never delivered. The row passes alone, passes with the whole
`tc_` family, and fails only in the full numeric-fact batch.

⚠️ **"It reproduces every time" is not evidence that a failure is semantic.**
openMSX is deterministic, so a race in the *harness* reproduces exactly — and a
39-byte ROM change perturbs the timeline enough to move which row loses it. The
one guard that would have caught this instantly is an echo guard, and the
numeric-fact family has none.

Fixed at the apparatus, not worked around: the family now uses
`omsx_repl.run_differential` with the same **self-heal** the probe's `onelin`
family already uses and documents for this exact class — any disagreeing row is
re-run **boot-per-case** and re-judged, so the verdicts equal a full
boot-per-case run. A delivery mangle costs one pair of boots; a real divergence
still fails. `make error-trap-acceptance`: **ALL PASS**.

---

## 7. Deliverables

1. This spec.
2. [`docs/decblank-msx1-characterization.md`](decblank-msx1-characterization.md) —
   the 32 oracle-locked rows, four rounds, both machines.
3. The `dec` battery in
   [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py)
   (already written; measurement is complete).
4. The fix at S1–S5.
5. `KNOWN_DIVERGE` shrunk to the §5.1 pins; the five `lit-` entries retired.
6. `TODO.md`: this item checked off; §5.1, §5.2 and §5.3 filed as new items.
7. The `error-trap` numeric-fact family switched to the self-healing differential
   (§6.2) — an apparatus repair this slice's own red row exposed.
