<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `LOCATE` / `SWAP` / `TRON` / `TROFF` / `MOTOR` (+ D-MISS-1) — implementation spec

**Status:** PROPOSAL, 2026-07-27. **Awaiting sign-off (S-MC-1 … S-MC-6, §9).**
No code has been written.

Inputs, all measured, none assumed:

- [`missing-vg8020-characterization.md`](missing-vg8020-characterization.md) —
  the surface, 175 cases + the 18-row `locrow` battery added for this spec.
- [`decision-missing-class-slicing.md`](decision-missing-class-slicing.md) —
  D-MC-1 ✅ (D-KW-2 first, then all five as one slice), D-MC-2 ✅ (fold D-MISS-1
  in, D-MISS-2 gets its own slice), D-MC-3 ✅ (`DEF FN` stays out), D-MC-4.
- Roadmap: [`TODO.md`](../TODO.md) "Keyword-completeness gaps", the MISSING
  bullet.

## 1. What this spec adds that the decision doc did not have

Four measurements were taken while writing it, because each one turns a design
choice from a guess into a fact. Three of them changed the design.

1. **O-1 is closed — and the obvious implementation is wrong.** The row clamps
   to **the console's own bottom row**, which moves with `KEY` (reference 22 at
   `KEY ON`, 23 at `KEY OFF`); zerobas is 23 in both states, having no
   function-key row. It is **not** a literal 23, and it is **not** `CRTCNT`
   (`$F3B1`), which measures **24** on both machines under every `WIDTH` and
   both `KEY` states. See the characterization §3.5.
2. **The argument domain has TWO error stages, not one.** `Overflow` beyond
   int16, `Illegal function call` outside `0..255` within it — on all three
   arguments. The first battery revision stopped at ±256, i.e. exactly the half
   of the domain where the one-error and two-error hypotheses agree. The tree's
   `get_byte_arg` already implements precisely this two-stage rule, so reusing
   it was going to be either exactly right or confidently wrong; it is exactly
   right, and now that is measured (characterization §3.3).
3. **The five tokens are pinned from the reference's own crunch**, not guessed:
   `LOCATE $D8`, `SWAP $A4`, `TRON $A2`, `TROFF $A3`, `MOTOR $CE`, with
   `MOTOR ON`/`OFF` crunching to the existing `ON_TOKEN $95` / `OFF_TOKEN $EB`
   (§3.1). ⚠️ `$A2`/`$A3`/`$A4` are **already** `equ`'d in `sysvars.inc` as
   `STICK`/`STRIG`/`PDL` — which are `$FF`-prefixed *function* tokens. Same byte
   value, different namespace; this is the existing `ASC_TOKEN $95` /
   `ON_TOKEN $95` situation, and it has a gate consequence (§7.5).
4. **The crunch-table entries are free, and the lean cart need not move.** In
   the repack build `kwtable` is **not resident** — it lives in `sub.rom`
   (subrom arc wave 3), where ~8 KB is free, so the ~39 B of new entries cost
   nothing in either tight region. The lean 16 KB cart includes `kwtable`
   inline in page 1 and is byte-full, which is why **this slice is proposed as
   repack-only**, `IF ROM_BASE < $4000`-guarded (§6.1) — so unlike D-KW-2 the
   lean cart stays **byte-identical** and `LEAN_SHA256` does not move.

## 2. Scope

**In:** `LOCATE`, `SWAP`, `TRON`, `TROFF`, `MOTOR`, and **D-MISS-1** (numeric →
string assignment must raise `Type mismatch`, not `syntax error`).

**Out:** `DEF FN`/`FN` (D-MC-3 — an arc). **D-MISS-2**, the absent string
argument-domain checks (D-MC-2 — its own slice; it is 4+ functions, a shared
domain check and a second error path, and bolting it on would blur two gates).

## 3. Normative surface

Everything here is measured. Section references are to the characterization.

### 3.1 Tokens (oracle-locked, VG-8020 crunch capture)

Read back with `("stored_line", TXTTAB)` — the tokeniser's own output, never ROM
code:

| source | stored bytes | token |
|---|---|---|
| `10 LOCATE 5,3` | `d8 20 16 2c 14 00` | `LOCATE = $D8` |
| `10 SWAP A,B` | `a4 20 41 2c 42 00` | `SWAP = $A4` |
| `10 TRON` | `a2 00` | `TRON = $A2` |
| `10 TROFF` | `a3 00` | `TROFF = $A3` |
| `10 MOTOR` | `ce 00` | `MOTOR = $CE` |
| `10 MOTOR ON` | `ce 20 95 00` | `ON = $95` (existing `ON_TOKEN`) |
| `10 MOTOR OFF` | `ce 20 eb 00` | `OFF = $EB` (existing `OFF_TOKEN`) |
| `10 TRON:TROFF:MOTOR` | `a2 3a a3 3a ce 00` | all three chain normally |

All five are **single-byte statement tokens**. Crunch-table entry cost:
`LOCATE` 9 B, `TROFF` 8 B, `MOTOR` 8 B, `SWAP` 7 B, `TRON` 7 B = **39 B**, all
into `sub.rom`.

### 3.2 `LOCATE [col][,[row][,cursor]]`

- **Order is column, row, cursor.** Arguments truncate (`5.7,3.2` → col 5 row 3;
  `4.5,2.5` → col 4 row 2, i.e. **no** round-half-up).
- **Each of the three is independently omittable**, and an omitted one **keeps**
  the current value: `LOCATE 7` sets the column only, `LOCATE ,4` the row only.
  `LOCATE 0` is a *value*, not an omission.
- **Bare `LOCATE` is `Missing operand`** — not a no-op. So are `LOCATE ,`,
  `LOCATE ,,` and `LOCATE 5,3,` (a trailing comma).
- **Domain, uniform across all three arguments, two stages:** beyond int16 →
  **`Overflow`**; outside `0..255` within int16 → **`Illegal function call`**;
  `0..255` → accepted, then clamped. `LOCATE "5",3` → `Type mismatch`.
- **Clamp:** column to `WIDTH-1` (measured 39 at `WIDTH 40`, 31 at `WIDTH 32`);
  row to **the console's bottom row** (§1 item 1). Both axes clamp
  independently — `LOCATE 255,255` lands at row 22, col 39 on the reference.
- **Maximum three arguments.** A fourth is `Syntax error` — and ⚠️ **the reject
  does not undo the accepted arguments**: `LOCATE 1,1,1,1` moves the cursor to
  (1,1) and prints `Syntax error` *there*.
- Accepted in graphics modes (`SCREEN 1`/`SCREEN 2`) without error.
- The third argument accepts `0..255` (not just 0/1). Its effect is O-3 (§8).

### 3.3 `SWAP a,b`

- Exchanges **scalars and array elements**, every type, including strings.
- **Strings move DESCRIPTORS, not bodies** — `LEN` follows the value across the
  swap and survives a later allocation, and aliased bodies (`B$=A$`) are
  undisturbed. **The implementation must not touch the string heap.**
- **The type rule is EXACT TYPE EQUALITY**, not numeric-vs-string: `%`≠`!`≠`#`
  all raise `Type mismatch`, as does `A%` vs a bare (`!`) name. `DEFINT`
  participates by changing what a bare name means, then the same rule applies.
- **The SECOND operand must already exist; the first may be created.**
  `B=1:SWAP A,B` creates `A`; `A=1:SWAP A,B` is **`Illegal function call`**. An
  **undimensioned array** on the right is auto-created without complaint, so the
  rule is specifically about *scalar* creation order. This is bug-for-bug
  behaviour to reproduce, not to fix ([`bug-for-bug-compat-over-accuracy`]).
- `SWAP A,A` is legal and a no-op; `SWAP` twice is an involution.
- **Shape rejects are `Syntax error`** (`SWAP`, `SWAP A`, `SWAP A,1`,
  `SWAP 1,A`, `SWAP A,B+0`, `SWAP A,LEN("x")`, `SWAP (A),B`, `SWAP A,B,`) —
  **except `SWAP A,B,C`, which is `Illegal function call`**. `SWAP A,Q(9)` on a
  `DIM Q(2)` is `Subscript out of range`.

### 3.4 `TRON` / `TROFF`

- The decoration is `[` + the **decimal** line number + `]`, no padding, emitted
  **before the line runs**, with **no newline of its own** (so it appears inline
  at the cursor).
- **Per LINE, not per statement.** `20 PRINT"A":PRINT"B"` traces once.
- **Jump targets are traced** (`GOTO`, `GOSUB` and every `FOR` loop re-entry);
  a **mid-line resume is not** (see §6.4, which is what makes this exactly
  implementable).
- **Direct-mode statements are NEVER traced**, but a `TRON` typed at the prompt
  **does** trace a subsequent `RUN`.
- **`RUN` does not reset it; `NEW` clears it.** `END` is traced and does not
  clear it. A line carrying `TROFF` is itself traced.
- **No arguments:** `TRON 1` / `TROFF 1` are `Syntax error`.

### 3.5 `MOTOR`

Exactly three forms — `MOTOR` (toggle), `MOTOR ON`, `MOTOR OFF`. **Everything
else is `Syntax error`**, including `MOTOR 1`, `MOTOR 0`, `MOTOR "ON"`,
`MOTOR A`, `MOTOR ON,OFF`, `MOTOR ON,` and — unlike `SPRITE`/`KEY`/`INTERVAL` —
**`MOTOR STOP`**.

### 3.6 D-MISS-1

Numeric → string assignment must raise **`Type mismatch`**, in every form:
`A$=A`, `A$=1`, `A$=1+1`, `A$=LEN("x")`, `LET A$=A`, `A$=A%`, and
`DIM Q$(3):Q$(0)=1`. The numeric-lvalue mirror is already correct and must stay
correct. Cause is localised: **the string-lvalue assignment path never
type-checks its RHS and fails in the parser instead.**

## 4. Design — `LOCATE`

Model it on `ex_color` ([`screen.asm:104`](../basic/screen.asm:104)), which is
the same three-optional-comma-separated-argument parse and measures 100 B with
*no* domain check and *no* clamp. Differences:

- Each argument goes through **`eval` + `get_byte_arg`** — which is already the
  measured two-stage rule (`ERR 6` beyond int16, `ERR 5` outside byte),
  `IF ROM_BASE < $4000`-guarded exactly as `ex_width` does it.
- **Omission keeps the current value**, so an omitted column/row reads back from
  `CSRX`/`CSRY` rather than defaulting to 0.
- **Bare `LOCATE` raises `Missing operand`**, which `ex_color` has no analogue
  for — `ex_color`'s bare form re-applies. This is a distinct error code and
  must be raised as such, not folded into `Syntax error`.
- **Apply as you parse, do not batch.** The measured "a rejected fourth argument
  does not undo the first two" behaviour falls out for free if each argument is
  applied when parsed, and has to be *engineered* if they are batched. This is
  the cheaper option *and* the faithful one.
- **The clamp target is read, never hard-coded** (§1 item 1): column against
  `LINLEN`, row against the console's bottom row.

⚠️ **`LINLEN` is `WIDTH`, and the bottom row has no equivalent sysvar in this
tree.** `CRTCNT` is 24 and is not it. zerobas's console bottoms out at row 23 in
every state measured, so the row clamp is `23` *for zerobas* — but it must be
written as "the console's last usable row" with the measurement cited, so that
if a function-key row is ever added the clamp moves with it instead of silently
becoming wrong. **S-MC-2 asks whether to introduce a named constant/sysvar for
this** rather than an unexplained `23`.

## 5. Design — `SWAP`

The one statement in the language that writes two lvalues, and the tree already
has the pieces:

- **`var_find_typed`** ([`vars.asm:320`](../basic/vars.asm:320)) returns
  `CF set, HL = entry address` and **does not allocate**.
- **`var_alloc_or_find`** ([`vars.asm:360`](../basic/vars.asm:360)) allocates.

So the measured asymmetry (§3.3) is reproduced *directly by choosing the right
routine per side*: **first operand → `var_alloc_or_find`, second operand →
`var_find_typed`, and `Illegal function call` when the second is absent.** The
reference's own mechanism (allocating the second can shift the variable table
and invalidate the pointer already taken for the first) is the likely cause, but
we reproduce the *behaviour*, not the mechanism.

Then: compare the two entries' **type bytes** first (exact equality, `Type
mismatch` otherwise), and exchange the value field's fixed width for that type
(2/4/8). For strings that width is the **descriptor**, which is exactly why
§3.3's "descriptors, not bodies" measurement matters — the heap is never
touched.

Array elements resolve through the existing array engine, which auto-`DIM`s —
matching the measured `SWAP A,Q(0)` acceptance.

Open design point, **S-MC-3**: whether to resolve an array-element lvalue via
the `VARPTR` array-element path already in the tree
([`varptr-array-element`](spec-basic-varptr-array-element.md)) or via a new
address-returning entry into the array engine. The first is reuse; the second
may be cheaper. Estimate range 90–130 B assumes the reuse route.

## 6. Design — `TRON`/`TROFF`, `MOTOR`, glue, D-MISS-1

### 6.1 Placement: repack-only

All five words, their `kwtable` entries and their `stmt_table` entries go behind
`IF ROM_BASE < $4000`. The lean cart stays **byte-identical**, so
`tools/check_reloc.py`'s `LEAN_SHA256` does **not** move — unlike D-KW-2, which
had to move it deliberately. Established precedent: `BEEP`/`SOUND`/`PLAY` are
already proven repack-only in the crunch probe.

### 6.2 `MOTOR` — a parse and a `call`

[`tape/tape.asm:175`](../tape/tape.asm:175) already implements **`STMOTR`
(`$00F3`)** with the MSX convention (`A=0` stop, `A=$FF` toggle, otherwise
start), and `tape/tape.asm` is a dependency of the merged repack ROM, so the
entry is present on the target machine. The three forms map 1:1:

| BASIC | `A` |
|---|---|
| `MOTOR` | `$FF` |
| `MOTOR ON` | `1` |
| `MOTOR OFF` | `0` |

Everything that is not end-of-statement, `ON_TOKEN` or `OFF_TOKEN` → `Syntax
error`. **`STOP` is explicitly not taken here**, which is worth a comment
because the other `ON`/`OFF` statements in this tree do take it.

### 6.3 The `ON`/`OFF` decode share

`MOTOR` would be the **7th** `ON`/`OFF`/`STOP` decode site (`program.asm` ×4,
`graphics.asm`, `screen.asm`), and the share was already flagged as deferred in
`spec-traps-t5-interval` §4.3. **S-MC-4** asks whether to take it in this slice
(it is a funding lever, but `MOTOR` needs a *2-way* decode where the others are
3-way) or leave it deferred.

### 6.4 The `TRON` hook — one line, and the tree is already shaped for it

The flag is a byte, cleared by `NEW`, untouched by `RUN`, `END` and `TROFF`-less
program end.

The hook goes in `run_program`'s loop ([`program.asm:293`](../basic/program.asm:293)),
on the **non-resume path only** — `rp_lp` reaches `rp_exec` two ways, and the
measured behaviour distinguishes them exactly:

- **fresh line entry** (`rp_lp` fall-through and `rp_goto`) → **traced**
- **mid-line resume** (`rp_resume`, i.e. `RETURN` and continuing `NEXT`) → **not
  traced**

That is not a guess — it is what makes the measured `FOR`/`NEXT` trace
`[20][30][30][40]` (line 20 entered once, resumed silently) and the `GOSUB`
trace `[40][20]` (the `RETURN` into line 10's remainder is silent, the
fall-through to line 20 is not) come out right.

Direct mode must not trace. `DIRECTF` is *derived* at `rp_exec` from
`CURLINE`'s high byte and is stale earlier in the loop, so the hook applies the
same `CURLINE+1` vs `dir_line >> 8` test — which is also exactly "is this a
stored line", the condition a line-number decoration needs anyway.

### 6.5 D-MISS-1

Add the RHS type check to the **string-lvalue** assignment path
(`ex_let_str`, [`interp.asm:485`](../basic/interp.asm:485), and the array-element
form `ex_let_arr_str`, [`arrays.asm:828`](../basic/arrays.asm:828)) so a numeric
RHS raises `Type mismatch` instead of falling through to the parser. The
numeric-lvalue mirror already does this correctly and is the model.

## 7. The gate

### 7.1 Teeth

`make missing-acceptance` (`--gate`) turns all 175 characterization rows plus
the 18 `locrow` rows two-sided. `BOOTPC=1` for the confirmation run — which on
this probe has already earned itself once (it is how the `LOCATE`-prints-above-
the-echo apparatus defect was found at all).

### 7.2 ⚠️ The row-clamp rows MUST be `KEY OFF`-pinned

Measured (characterization §3.5): the consoles bottom out at row **22
(reference) vs 23 (zerobas)** under the boot default, because the reference
reserves the function-key row and C-BIOS paints none — the same chrome
divergence §2 of the characterization already drops. Under **`KEY OFF` both are
23**. So `KEY OFF` pins the row axis exactly as `WIDTH 40` pins the column axis,
and an unpinned row-clamp case goes red for a reason that has nothing to do with
`LOCATE`. **Making the gate green by hard-coding 22 into zerobas would be the
wrong fix** — it would make zerobas's own last row unreachable by `LOCATE` while
`PRINT` still scrolls onto it.

### 7.3 ⚠️ The gate cannot reach green while D-MISS-2 is deferred

Re-run of the calibration battery on today's tree (`ONLY=cal`): **22/41 agree**,
and every one of the 19 red rows is a *documented* finding — 7 × D-MISS-1
(`cal-err-type` plus the 6 `d1-*` string-lvalue rows) and 12 × D-MISS-2. That is
the correct state of the world, but it means **`make missing-acceptance` will
still be red after this slice lands**, because D-MISS-2 is deliberately deferred
(D-MC-2). A gate that cannot go green is not a gate — it degrades into "read the
output and use your judgement", which is exactly what these gates exist to
replace.

So the slice must make the expectation **explicit and machine-checked**: mark
the D-MISS-2 rows as **known-divergent with a reason and a roadmap reference**,
so the gate is green when the world matches the recorded expectation and red the
moment anything *else* moves — including a D-MISS-2 row that starts *passing*
(which would mean the deferred slice landed and the marker is stale). The
D-MISS-1 rows get no such marker: this slice fixes them, and they must go from
red to green as its proof.

**S-MC-6** asks to confirm that shape (an expected-divergence marker carrying a
reason) rather than the alternatives — dropping the rows, which loses the
measurement, or leaving the gate permanently red.

### 7.4 Falsification — the standing rule

A green gate proves nothing until it has been shown to go red for the right
reason. Before landing, **delete each word's `stmt_table` entry in turn** and
confirm that word's rows — and only that word's rows — fail.
[`gate-can-be-green-while-measuring-nothing`](../MEMORY.md), and the D-KW-2 gate
that passed with `PRINT` deleted.

### 7.5 The `$A2`/`$A3`/`$A4` dual-namespace round-trip

`TRON`/`TROFF`/`SWAP` take byte values already `equ`'d for the `$FF`-prefixed
`STICK`/`STRIG`/`PDL` function tokens. The tokeniser and the **detokeniser**
must keep the two namespaces apart in both directions. Add `LIST` round-trip
cases (`10 TRON:A=STICK(0)` and friends) to the crunch/detok probe — this is
cheap and it is the one place where a silent wrong answer could hide in an
otherwise honest slice.

### 7.6 `tests/test_stmt_dispatch.py`

Extend the emulator-free dispatch gate with the five new entries, keeping its
independent-expectation discipline (the mapping is recovered from the source of
truth and compared *by name*, never read out of the artifact under test).

### 7.7 O-2 — close it, don't inherit it

`MOTOR`'s effect is the cassette relay, invisible to a screen scrape. We own
both sides now, so an **openMSX-level check of the motor line** settles whether
the relay actually closes, instead of shipping "accepted" as if it meant
"worked". Proposed as part of the acceptance work, not left open.

## 8. Deviations, stated up front

- **O-3, the `cursor` third argument, is accepted, domain-checked and
  ignored.** Nothing in the tree reads `CSRSW` (`$FCA9`) or any equivalent, so
  there is no mechanism for it to drive and storing it would be a write nobody
  reads. Acceptance is measured; behaviour is not. Documented as a deviation.
- **The row clamp lands one row lower than the reference at `KEY ON`** (23 vs
  22), because zerobas has no function-key row to reserve. This is the existing
  console-chrome divergence, not a new one, and it disappears under `KEY OFF`.

## 9. Cost, order, and the sign-off items

| item | estimate | region |
|---|---|---|
| `LOCATE` | 110–135 B | page 1 |
| `SWAP` | 90–130 B | page 1 |
| `TRON`/`TROFF` (flag + hook + decimal emit) | 50–75 B | page 1 |
| `MOTOR` | 25–40 B | page 1 |
| `stmt_table` glue, 5 × 3 B | 15 B | page 1 |
| D-MISS-1 | 10–25 B | page 1 |
| `kwtable` entries | 39 B | **`sub.rom`** (~8 KB free) |
| **page-1 total** | **300–420 B** | **against 420 B free** |

Measured from clean (`rm -rf build && make basic-reloc`): **page-1 420 B, low
region 11 B.** The low region is untouched by this slice.

**So the optimistic end lands with ~120 B to spare and the pessimistic end
consumes the budget exactly.** That is not a comfortable margin, so the proposed
order is **cheapest and most certain first, measuring free space after each**:
`MOTOR` → `TRON`/`TROFF` → D-MISS-1 → `LOCATE` → `SWAP`. `SWAP` is both the most
expensive and the most uncertain, so it goes last, where an overrun is
discovered against a *measured* remaining budget rather than an estimated one.
Reserve levers, in order of preference: the `ON`/`OFF`/`STOP` decode share
(§6.3), and the `fat_rand_*` clone collapse (~28 B, the last of that well).

### Sign-off

- **S-MC-1** — the slice as scoped in §2 and ordered in §9. Go / re-order / cut.
- **S-MC-2** — the row clamp: a named constant for "the console's last usable
  row" with the §3.5 measurement cited, or a bare `23` with a comment?
- **S-MC-3** — `SWAP`'s array-element lvalue: reuse the `VARPTR` array-element
  path, or a new address-returning entry into the array engine?
- **S-MC-4** — take the 7-site `ON`/`OFF`/`STOP` decode share now as funding, or
  leave it deferred?
- **S-MC-5** — repack-only (§6.1), keeping the lean cart byte-identical?
  Confirming, since it means these five words do not exist on the lean cart.
- **S-MC-6** — the deferred-D-MISS-2 gate shape (§7.3): an expected-divergence
  marker carrying a reason, so the gate can be green and still fail if anything
  moves?
