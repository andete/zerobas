<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `LOCATE` / `SWAP` / `TRON` / `TROFF` / `MOTOR`, characterised against the VG-8020

**Status:** MEASUREMENT RECORD, 2026-07-27. Input to the MISSING-class slice of
[`decision-kwgaps-slicing.md`](decision-kwgaps-slicing.md) — the five statements
left in the keyword arc that are a *slice* rather than an arc. Produced by
[`probes/basic/basic_probe_missing.py`](../probes/basic/basic_probe_missing.py)
(`make missing-characterize`, `BOOTPC=1` for the confirmation run). Reference:
`Philips_VG_8020`.

`DEF FN`/`FN` is the sixth MISSING word and is **deliberately out of scope**: a
definition table, argument binding and re-entrant evaluation is an arc, not a
slice.

## 1. Why this class is the inverse measurement problem

The eight SILENT-GAP words were dangerous because zerobas *answered* and the
answer was wrong. These five raise an honest `syntax error`, so nothing is
silently broken — which means the risk is not "is zerobas wrong" but **"what
exactly does the reference do"**. Four of the five have surfaces that are easy
to guess wrong, and every one of those guesses turned out to matter:

| word | the thing you would have guessed wrong |
|---|---|
| `LOCATE` | the column bound is **`WIDTH`-relative**, not a fixed 40 — and out-of-range **clamps** instead of erroring |
| `SWAP` | the type rule is **exact type equality** (`%`≠`!`≠`#`), not numeric-vs-string |
| `TRON` | the decoration is per **LINE**, not per statement, and direct-mode statements are **never** traced |
| `MOTOR` | the whole surface is three forms; **everything else is `Syntax error`**, including `MOTOR 1` |

## 2. Two readouts had to be refused, and one instrument had to be fixed

**The bracket convention is unusable for the trace battery.** Every other probe
in this tree reads its answer out of `PRINT "[";X;"]"`. The reference's own
`TRON` decoration is *itself* bracketed (`[20]`), so `result_span` would happily
return a slice of the trace and call it the answer. Trace rows use a
whole-screen readout and never touch `result_span`.

**`CSRLIN`/`POS` cannot be the instrument for `LOCATE`.** They landed in
`99c0f6d` and are gated 67/67, so they are legitimate calibration — but they are
the READ side of exactly the state `LOCATE` WRITES, and a wrong pair could
cancel and read as correct. `LOCATE` is measured by where a marker LANDS on the
40×24 grid; `CSRLIN`/`POS` appear only in the declared `xchk` cross-check (§3.4).

**The instrument was wrong on the first run, and the calibration battery caught
it.** `cal-trace-null` compared `A/B` against `A/B/color auto goto list run`:
the reference paints its **function-key labels** on the bottom screen row and
`CLS` does not wipe them, while C-BIOS paints nothing there. Every trace row
would have failed for a reason with nothing to do with `TRON`. The readout now
drops the last row — as console chrome, the same class of already-known
divergence as the different boot `WIDTH`.

### 2.1 A wrapped echo makes a row AGREE while measuring nothing

Three rows in the first revision read `<no result>` on **both** machines and
therefore PASSED, while one side raised `Illegal function call` and the other
did not. The cause: `Z=99:PRINT "[";LEN(CHR$(256));"]":Z=1` is 37 source
characters, which with zerobas's then-3-character `zb>` echo prefix was exactly one column too
wide for a 40-column row. `screen_tail` anchors **strictly** on the echo, so a
wrapped echo kills the readout silently.

This is the [`kwsweep`](kwsweep-msx1-coverage.md) apparatus scar #1 in a new
costume, and it is now impossible rather than unlikely: **`MAX_ECHO = 33`, and
the probe REFUSES TO RUN** if any echo-anchored row exceeds it.

The first fix was an over-correction worth recording, because it would have
thrown away good data: the guard was applied to `value` rows too, condemning 36
rows that demonstrably read correctly (`cal-xchg-num` is 37 chars and reported
`2 1` on both machines). `value` rows survive a wrapped echo because
`result_span` **falls back** to the last `[...]` anywhere on screen, which is
the printed answer. Only `tail` is anchored, so only `tail` is guarded.

The split this forced is the better design anyway, and the batteries below are
built on it: **a `tail` row measures the ERROR MESSAGE and stays short; a
`value`/`marker` row measures the EFFECT and may be as long as it needs.** The
original rows tried to do both at once, which is why they were all 37–55 chars.

### 2.2 …and for `LOCATE` the echo anchor is not fixable, only replaceable

Shortening the rows was still not enough, and the reason is specific to the word
under test. **`LOCATE` moves the cursor before it rejects** (§3.3): given
`LOCATE 1,1,1,1` the reference applies the first two arguments, jumps to (1,1),
and prints `Syntax error` **above** the echo. `screen_tail` looks only *after*
the echo, so it found nothing and reported `<no result>` — "no error" — for a
row that errors.

This was caught only because the batched and boot-per-case runs **disagreed**:
the batched run's `NEW:CLS` reset happened to leave the echo high enough that
the message landed below it, and read `Syntax error` correctly by luck. A
disagreement between two runs of the same case is the signal; without the
confirmation run this would have gone into the spec as fact.

Every error battery (`locerr`, `swaperr`, `motor`, and the `trd-*` rows) is
therefore **`CLS`-led with the whole-screen readout**, which finds the message
wherever it lands: a rejecting row reads as its message, an accepting row reads
`<blank>`. Two unambiguous readings that do not depend on where the cursor ends
up — and no echo anchor means no `MAX_ECHO` budget either.

### 2.3 The `value` readout classifies its fallback rather than dropping it

`result_span_after_echo` cannot anchor when the echo wraps, and five `xchk` rows
are 51–63 chars. The bare `result_span` fallback rescues them, because it takes
the **last** `[` on screen — which is the printed answer whenever one exists.

What the fallback cannot do is notice when *nothing* was printed: every value
row's echo contains `[` and `]` inside its own `PRINT "[";…` text, so an aborted
statement yields a slice of the typed command (`";A%;B!;"`, `";C;D;"`). Removing
the fallback was the wrong fix — it made the whole `xchk` battery read
`<aborted>` after it had been reading correct values. The fallback is kept and
its output is **classified**: printed answers here are numbers and short literals
and never contain `"` or `;`, while an echo slice always contains both. A span
carrying either reads `<aborted>`, which is what it means.

## 3. `LOCATE [col][,[row][,cursor]]`

### 3.1 Position — column first, row second, truncating

| case | ROM |
|---|---|
| `LOCATE 5,3` | marker at row 3, col 5 |
| `LOCATE 0,0` | 0,0 |
| `LOCATE 2+3,1+2` | 3,5 — expressions |
| `LOCATE X,Y` | 3,5 — variables |
| `LOCATE 5.7,3.2` | 3,5 — **truncates** |
| `LOCATE 4.5,2.5` | 2,4 — truncates, does **not** round half up |
| `LOCATE 20,5:LOCATE 3,1` | 1,3 — not one-shot state |
| `LOCATE 5,3:PRINT "AB";#` | 3,7 — ordinary cursor, printing continues from it |
| `LOCATE 38,3:PRINT "AB";#` | 4,0 — and wraps normally |

### 3.2 Omitted arguments — and a bare `LOCATE` is an ERROR

| case | ROM |
|---|---|
| `PRINT "AAA":LOCATE 7` | 1,7 — column set, **row preserved** |
| `PRINT "AAA";:LOCATE ,4` | 4,3 — row set, **column preserved** |
| `PRINT "AAA";:LOCATE 0` | 0,0 — column 0 is a value, not an omission |
| `LOCATE` | **`Missing operand`** — *not* a no-op |
| `LOCATE ,` | `Missing operand` |
| `LOCATE ,,` | `Missing operand` |
| `LOCATE 5,3,` | `Missing operand` |

`Missing operand` is a distinct error from `Syntax error` and the implementation
must raise that one.

### 3.3 Bounds — a BYTE domain check, then a CLAMP

The two are separate, and the distinction is the whole of the bound behaviour.
**The rule is uniform across all three arguments**, and it has **two** error
stages, not one: `0..255` is accepted and then clamped, outside that but within
int16 is `Illegal function call`, and beyond int16 it is **`Overflow`** —
raised by the argument coercion before the domain check ever runs.

| case | ROM |
|---|---|
| `LOCATE 32768,0` / `99999,0` / `-32769,0` | **`Overflow`** |
| `LOCATE 0,32768` | **`Overflow`** |
| `LOCATE 5,3,32768` | **`Overflow`** |

⚠️ This half of the domain was **not** in the first revision of the battery,
which stopped at ±256 — i.e. exactly the half where "one error" and "two errors"
agree. It was added (2026-07-27) because D-MISS-2 found the same two-stage shape
in `CHR$`, and because the tree's `get_byte_arg` already implements two stages,
which would have made reusing it either exactly right or confidently wrong with
nothing measured in between. It is exactly right.

| case | ROM |
|---|---|
| `LOCATE 255,0` | accepted |
| `LOCATE 256,0` | **`Illegal function call`** |
| `LOCATE -1,0` | `Illegal function call` |
| `LOCATE 0,23` / `0,24` / `0,255` | accepted |
| `LOCATE 0,256` | **`Illegal function call`** |
| `LOCATE 0,-1` | `Illegal function call` |
| `LOCATE 5,3,2` / `5,3,255` | accepted — the cursor argument is **not** restricted to 0/1 |
| `LOCATE 5,3,256` | **`Illegal function call`** |
| `LOCATE 5,3,-1` | `Illegal function call` |
| `LOCATE "5",3` | `Type mismatch` |

Argument **count**: three is the maximum.

| case | ROM |
|---|---|
| `LOCATE 1,1,1` | accepted |
| `LOCATE 1,1,1,1` | `Syntax error` |
| `LOCATE 1,1,1,1,1` | `Syntax error` |

⚠️ **A rejected excess argument does not undo the accepted ones.**
`LOCATE 1,1,1,1` applies its first two arguments, moves the cursor to (1,1), and
prints `Syntax error` *there*. This is measured, not inferred: on a raw screen
the message lands at row 2 while the echo is at row 4, overwriting the boot
banner. It is also what broke the first version of this battery — see §2.2.

Inside the byte domain, the value is **clamped to the screen**:

| case | marker |
|---|---|
| `WIDTH 40` · `LOCATE 40,3` / `41,3` / `255,3` | all land at **col 39** |
| `WIDTH 32` · `LOCATE 32,3` / `39,3` | both land at logical col **31** (physical 35) |
| `WIDTH 32` · `LOCATE 31,3` | logical 31 = physical 35 |
| `WIDTH 32` · `LOCATE 0,3` | logical 0 = physical 4 |

**The column limit is `WIDTH`-relative, not a fixed 40** — settled by the two
`WIDTH 32` rows, which are the only ones that can tell the two hypotheses apart.
(`SCREEN 0` centres the text area, so at `WIDTH 32` the margin is 4 and every
logical column reads 4 higher on the VRAM grid. That offset is the reason every
positional row pins `WIDTH 40`; see
[`cursor-vg8020-characterization.md`](cursor-vg8020-characterization.md) §1.1.)

**Row bounds are not directly readable** and the record says so rather than
guessing: `LOCATE 5,22`, `5,23` and `5,24` all report the marker at row **20**,
because printing on the bottom rows scrolls the screen before the scrape runs.
What is measured is that none of them ERRORS. The clamp target for the row is
therefore an **open question for the spec** (§7 O-1), to be settled by a
scroll-free readout rather than by assumption.

`LOCATE` in a graphics mode is accepted: `SCREEN 2:LOCATE 5,3` and
`SCREEN 1:LOCATE 5,3` both raise nothing.

### 3.5 O-1 CLOSED — the row clamps to the CONSOLE'S OWN BOTTOM ROW, not to 23

Added 2026-07-27, battery `locrow`
(`make missing-characterize ONLY=locrow`), 18 rows, batched **and**
boot-per-case, identical both times.

The grid could not answer this because printing near the bottom scrolls before
the scrape runs (§3.3). The scroll-free readout is to capture the cursor into
**variables** on the line that moves it and print them from a *separate later
line*: scrolling after the capture cannot change a number already in a variable,
and the printing line starts from wherever the prompt left the cursor. `CSRLIN`/
`POS` are legitimate here where §2 refused them — this battery is
**reference-only**, so it asks what the reference does with the reference's own
gated instrument, and the cancellation risk §2 refused them for needs *two*
implementations to cancel. Every in-range row reproduces the grid battery's
answer, which is what earns the out-of-range ones.

| case | `CSRLIN` `POS(0)` |
|---|---|
| `LOCATE 5,3` / `5,21` / `5,22` | `3 5` / `21 5` / `22 5` — in-range controls |
| `LOCATE 5,23` / `5,24` / `5,25` / `5,255` | **all `22 5`** |
| `KEY OFF` · `LOCATE 5,22` | `22 5` |
| `KEY OFF` · `LOCATE 5,23` / `5,24` / `5,255` | **all `23 5`** |
| `LOCATE 39,3` / `40,3` / `255,3` | all `3 39` |
| `WIDTH 32` · `LOCATE 31,3` / `32,3` / `255,3` | all `3 31` |
| `LOCATE 255,255` | `22 39` — **both axes clamp, independently** |

So it **is** a clamp (the cursor is at row 0 after `CLS`; an ignored argument
would have left it there, not at 22), and **the target moves with `KEY`**.

**And the obvious mechanism is the wrong one.** `CRTCNT` (`$F3B1`) is the
sysvar that looks like the answer, and it reads **24 on both machines, under
every `WIDTH` and under both `KEY` states** — so it is the panel height and not
the clamp source. What the clamp actually tracks is the console's own last
usable text row, measured directly as where ordinary scrolling stops
(`CLS:FOR I=1 TO 30:PRINT:NEXT:Y=CSRLIN`):

| | reference | zerobas |
|---|---|---|
| `KEY ON` (boot default) | **22** | **23** |
| `KEY OFF` | **23** | **23** |
| `KEY OFF` · `WIDTH 32` | 23 | 23 |

The reference reserves the bottom row for the function-key labels and C-BIOS
paints none — the *same* console divergence §2 already drops as chrome, showing
up on the row axis. The clamp target equals that bottom row in every state
measured.

**Two consequences the spec turns on:**

1. **The implementation must clamp to its own console's bottom row, not to a
   literal.** Hard-coding the reference's 22 would make zerobas's last row
   unreachable by `LOCATE` while `PRINT` still scrolls onto it.
2. **`KEY OFF` pins the row axis exactly as `WIDTH 40` pins the column axis.**
   Under `KEY OFF` both consoles bottom out at row 23, so a differential
   row-clamp case is comparable; under the boot default it would read 22 vs 23
   and go red for a reason that has nothing to do with `LOCATE`. That pinning is
   measured above, not assumed — zerobas ignores `KEY ON`/`OFF` for the row
   count (it has no function-key row to reclaim), which is *why* the two agree
   there.

### 3.4 The declared `CSRLIN`/`POS` cross-check

Recorded as a consistency check between two independently-measured instruments,
never as the gate's teeth (§2).

| case | ROM | consistent with the grid? |
|---|---|---|
| `LOCATE 5,3:PRINT "[";CSRLIN;POS(0);"]"` | `3 9` | ✅ |
| `LOCATE 0,0:…` | `0 4` | ✅ |
| `PRINT "AAA":LOCATE 7:…` | `1 11` | ✅ |
| `PRINT "AAA";:LOCATE ,4:…` | `4 7` | ✅ |
| `LOCATE 39,22:…` | `22 4` | ✅ (printing at col 39 wrapped) |

⚠️ **`POS` here is confounded by the row's own printing** and is not a reading of
where `LOCATE` left the cursor: `[` and then ` 3 ` are emitted *before* `POS(0)`
is evaluated, so `POS` reads 4 columns to the right of the `LOCATE` column
(5 → 9, 0 → 4, 7 → 11, 3 → 7). Every row is consistent once that offset is
applied, which is what makes this a corroboration; it is **not** an independent
measurement of `POS`.

## 4. `SWAP a,b` — exact type equality, and the second operand must EXIST

### 4.1 It exchanges, for every type

| case | ROM |
|---|---|
| `A=1:B=2:SWAP A,B` | `2 1` |
| `A=1.5:B=2.25:SWAP A,B` | `2.25 1.5` |
| `A%=1:B%=2` / `A!=…` / `A#=…` | all exchange |
| `A$="P":B$="QQ"` | `QQP` |
| `A=7:SWAP A,A` | `7` — self-swap is legal and a no-op |
| `SWAP A,B:SWAP A,B` | `1 2` — involution |
| `DIM Q(3):SWAP Q(0),Q(1)` | `9 7` — array elements |
| `SWAP A,Q(0)` | `5 1` — scalar with an array element |
| `DIM Q$(3):SWAP Q$(0),Q$(1)` | `QQP` — string array elements |

### 4.2 Strings move DESCRIPTORS, not bodies

This is the question that decides whether the implementation may touch the
string heap at all, and the answer is that it must not:

| case | ROM |
|---|---|
| `A$="XY":B$=STRING$(20,66):SWAP A$,B$` → `LEN(A$);LEN(B$)` | `20 2` |
| …then `C$=STRING$(30,67)` and re-read | `20 2` — survives a later allocation |
| `A$="P":B$=A$:SWAP A$,B$` | `PP` — aliased bodies, both still `"P"` |

### 4.3 The type rule is EXACT TYPE EQUALITY

The single most load-bearing unknown in the surface, and the answer is *not*
"numeric vs string":

| case | ROM |
|---|---|
| `A=1:B$="x":SWAP A,B$` (either order) | `Type mismatch` |
| `A%=1:B!=2.5:SWAP A%,B!` | **`Type mismatch`** |
| `A%=1:B#=2.5:SWAP A%,B#` | **`Type mismatch`** |
| `A!=1.5:B#=2.5:SWAP A!,B#` | **`Type mismatch`** |
| `A%=1:B=2.5:SWAP A%,B` | **`Type mismatch`** |
| `DEFINT C:C=1:D=2.5:SWAP C,D` | `Type mismatch` |
| `DEFINT C,D:C=1:D=2:SWAP C,D` | accepted |

So the implementation must compare the two variables' **types** before moving
anything, and may then move a fixed width for that type. `DEFINT` participates
exactly as expected — it changes what a bare name means, and the rule then
applies to the resulting types.

### 4.4 The SECOND operand must already exist — the first may be created

Measured boot-per-case, because the batched run's asymmetry had no plausible
mechanism and needed settling:

| case | ROM |
|---|---|
| `B=1:SWAP A,B` (first undefined) | `1 0` — **A is created** |
| `A=1:SWAP A,B` (second undefined) | **`Illegal function call`** |
| `SWAP A,B` (both undefined) | `Illegal function call` |
| `A$="P":SWAP A$,B$` | `Illegal function call` |
| `A=1:SWAP A,Q(0)` (second is an undimensioned ARRAY) | accepted → `0 1` |

The asymmetry is real and consistent. It has an obvious mechanism — creating the
second variable can move the variable table and invalidate the pointer already
taken for the first — and an **undimensioned array** on the right is auto-created
without complaint, so the rule is specifically about scalar creation order.
This is a bug-for-bug behaviour to reproduce, not to fix; see
[`bug-for-bug-compat-over-accuracy`](../MEMORY.md).

### 4.5 Shape rejects

| case | ROM |
|---|---|
| `SWAP` / `A=1:SWAP A` | `Syntax error` |
| `SWAP A,B,C` | **`Illegal function call`** — not `Syntax error` |
| `SWAP A,1` / `SWAP 1,A` | `Syntax error` |
| `SWAP A,B+0` / `SWAP A,LEN("x")` | `Syntax error` |
| `SWAP (A),B` | `Syntax error` |
| `SWAP A,B,` | `Syntax error` |
| `DIM Q(2):SWAP A,Q(9)` | `Subscript out of range` |

`SWAP A,B,C` raising `Illegal function call` where every other malformed shape
raises `Syntax error` is the kind of detail that only a measurement produces.

## 5. `TRON` / `TROFF` — per LINE, and never in direct mode

### 5.1 The decoration

| program | screen |
|---|---|
| `10 CLS:TRON` `20 PRINT"A"` `30 PRINT"B"` | `[20]A` / `[30]B` |
| `20 PRINT"A":PRINT"B"` `30 PRINT"C"` | `[20]A` / `B` / `[30]C` — **per LINE, not per statement** |
| `20 GOTO 40` `30 PRINT"SKIP"` `40 PRINT"D"` | `[20][40]D` — the jump TARGET is traced |
| `20 FOR I=1 TO 2` `30 NEXT` `40 TROFF` | `[20][30][30][40]` — every loop re-entry |
| `10 CLS:TRON:GOSUB 40` `20 TROFF` … `40 RETURN` | `[40][20]` |
| `20 PRINT"A";` `30 PRINT"B";` `40 TROFF` | `[20]A[30]B[40]` — inline, it is just printed at the cursor |
| `1 CLS:TRON` `30000 PRINT"A"` `32767 TROFF` | `[30000]A` / `[32767]` — no padding |

The decoration is `[` + the decimal line number + `]`, emitted **before** the
line runs, with no newline of its own. A line carrying `TROFF` is itself traced,
because the decoration precedes execution.

### 5.2 Scope — and it survives RUN but not NEW

| case | ROM |
|---|---|
| `CLS:TRON:PRINT "A":TROFF` typed at the prompt | `A` — **direct-mode statements are NOT traced** |
| direct `TRON`, then `RUN` | `[20]A` — a prompt `TRON` **does** trace the program |
| `20 TRON` … `RUN` `RUN` | `[20][30]A` — **`RUN` does not reset it** |
| `10 CLS:TRON` `20 PRINT"A"` `30 END` `RUN` | `[20]A` / `[30]` — `END` is traced, and does not clear it |
| … `RUN` `NEW` `10 CLS` `20 PRINT"B"` `RUN` | `B` — **`NEW` clears it** |
| `TRON:TROFF` | accepted |
| `TRON 1` / `TROFF 1` | `Syntax error` — **no arguments** |

## 6. `MOTOR` — three forms, and nothing else

⚠️ **This battery measures the LANGUAGE SURFACE only.** `MOTOR`'s whole effect is
the cassette relay, and a SCREEN 0 name-table scrape cannot see it. A row below
reading "accepted" means *accepted*, never *the motor turned*. Confirming the
relay is an open item (§7 O-2).

| case | ROM |
|---|---|
| `MOTOR` | accepted (toggle) |
| `MOTOR ON` | accepted |
| `MOTOR OFF` | accepted |
| `MOTOR ON:MOTOR OFF` / `MOTOR:MOTOR` | accepted |
| `MOTOR STOP` | `Syntax error` — **`STOP` is not taken here**, unlike `SPRITE`/`KEY`/`INTERVAL` |
| `MOTOR 1` / `MOTOR 0` | `Syntax error` — **no numeric argument** |
| `MOTOR "ON"` / `A=1:MOTOR A` | `Syntax error` |
| `MOTOR ON,OFF` / `MOTOR ON,` | `Syntax error` |

The surface is exactly `MOTOR` | `MOTOR ON` | `MOTOR OFF`.

## 7. Open questions this run did NOT settle

Listed rather than silently dropped.

- ~~**O-1 — `LOCATE`'s ROW clamp target.**~~ ✅ **CLOSED, see §3.5.** The clamp
  target is the console's own bottom row (reference 22 at `KEY ON`, 23 at
  `KEY OFF`; zerobas 23 always), **not** a literal 23 and **not** `CRTCNT`,
  which is 24 everywhere. Settled by capturing the cursor into variables and
  printing them from a later line, so scrolling cannot destroy the reading.
- **O-2 — whether `MOTOR` closes the relay.** Out of reach of a screen scrape
  (§6). This is a tape-component question; an openMSX-level readout of the
  cassette motor line would settle it.
- **O-3 — the `cursor` argument's effect.** `LOCATE 5,3,0` / `,1` / `,2` are all
  accepted and none disturbs the position, but a blinking cursor is invisible to
  a name-table scrape. Only the *acceptance* is measured.

## 8. What the calibration battery turned up — pre-existing, nobody was looking

This is the fourth slice running whose calibration battery found live defects in
code that was not under test. Two here, both confirmed boot-per-case, **neither
in the MISSING class and neither caused by it**.

### D-MISS-1 — numeric → string assignment raises `syntax error`, not `Type mismatch`

Every form, on the string-lvalue side only:

| case | reference | zerobas |
|---|---|---|
| `A=1:A$=A` | `Type mismatch` | **`syntax error`** |
| `A$=1` | `Type mismatch` | **`syntax error`** |
| `A$=1+1` | `Type mismatch` | **`syntax error`** |
| `A$=LEN("x")` | `Type mismatch` | **`syntax error`** |
| `A=1:LET A$=A` | `Type mismatch` | **`syntax error`** |
| `A%=1:A$=A%` | `Type mismatch` | **`syntax error`** |
| `DIM Q$(3):Q$(0)=1` | `Type mismatch` | **`syntax error`** |
| `A$="x":A=A$` (mirror) | `Type mismatch` | `type mismatch` ✅ |
| `A="x"` / `A=CHR$(65)` / `DIM Q(3):Q(0)="x"` | `Type mismatch` | correct ✅ |

The rule is clean: **the string-lvalue assignment path never type-checks its
right-hand side and fails in the parser instead.** The numeric-lvalue mirror is
already correct, including for array elements. Diagnosable rather than dangerous
— but it is the wrong error, and `ON ERROR` sees the wrong code.

### D-MISS-2 — the string engine's argument-domain checks are largely absent

| case | reference | zerobas |
|---|---|---|
| `LEN(CHR$(-1))` | `Illegal function call` | **`1`** |
| `LEN(CHR$(256))` | `Illegal function call` | **`1`** |
| `LEN(CHR$(32768))` | **`Overflow`** | **`1`** |
| `LEN(CHR$(99999))` | **`Overflow`** | **`1`** |
| `LEN(LEFT$("abc",-1))` | `Illegal function call` | **`3`** |
| `LEN(RIGHT$("abc",-1))` | `Illegal function call` | **`3`** |
| `LEN(MID$("abc",-1))` | `Illegal function call` | **`0`** |
| `LEN(MID$("abc",0))` | `Illegal function call` | **`3`** |
| `LEN(STRING$(-1,65))` | `Illegal function call` | `Illegal function call` ✅ |
| `LEN(STRING$(256,65))` | `Illegal function call` | `Illegal function call` ✅ |
| `LEN(SPACE$(-1))` | `Illegal function call` | `Illegal function call` ✅ |
| `ASC("")` | `Illegal function call` | `illegal function call` ✅ |

Three findings in one table:

1. **The family is inconsistent with itself.** `STRING$`/`SPACE$`/`ASC` check
   their domain; `CHR$`/`LEFT$`/`RIGHT$`/`MID$` do not. So this is missing
   checks, not a missing mechanism — the mechanism exists and is reachable
   (`cal-err-fc` is in the battery to prove exactly that before any row here is
   read as "zerobas cannot raise it").
2. **There are TWO reference errors, not one.** Out-of-*byte*-range is `Illegal
   function call`; beyond int16 (`32768`, `99999`) it is **`Overflow`**, raised
   by the argument coercion before the domain check ever runs. An implementation
   that raises `Illegal function call` for everything would be wrong on half the
   domain. This is the same two-stage shape as `LOCATE`'s bounds (§3.3).
3. **In-domain behaviour already agrees**, including the coercion rule:
   `CHR$(65.7)` → `A` and `CHR$(64.5)` → `@`, i.e. truncation, matching on both
   machines. So the fix is a domain check bolted onto correct code.

These are silent wrong answers in words the string engine already ships and
gates. That is a **different animal** from the now-empty SILENT-GAP *class*,
which is about absent reserved words — which is precisely why it survived it.

### Not a finding — two spellings of one error message

`ASC("")` reports lowercase `illegal function call` while `STRING$(-1,65)`
reports capitalised `Illegal function call`. This is **deliberate and already
documented** at [`basic/arrays.asm:44`](../basic/arrays.asm:44): the arrays path
uses the reference-verbatim capitalised text rather than the lowercase house
style. Recorded because it looks like a defect in a diff and is not.

### Also observed — D-CUR-3, already known, reported not gated

`STRING$(-1,65)` prints `Illegal function call` *and then* `syntax error`;
`SPACE$(-1)` prints the error *and then* ` 0`. That is the documented
mid-statement-abort defect from the cursor slice (an error raised inside a
`PRINT` item loop sets `ENDFLAG` and returns, so the loop carries on and the
unwind only happens at the next statement boundary). It is pre-existing, it is
not new here, and these rows are not a second sighting of a new bug.

## 9. Apparatus notes

Four defects in the probe itself, three of which had already produced a wrong
reading before they were caught. Recorded because each is reusable.

1. **The reference's function-key row survives `CLS`** and C-BIOS paints none,
   so every trace row would have failed for a console reason (§2). Caught by
   `cal-trace-null`, which exists for that.
2. **A wrapped echo makes a row AGREE while measuring nothing** (§2.1) — three
   rows read `<no result>` on both machines while one side errored.
3. **`LOCATE` prints its error ABOVE the echo**, because it moves the cursor
   before rejecting (§2.2). Caught only by a disagreement between the batched
   and boot-per-case runs.
4. **Removing the `result_span` fallback** to stop it reporting echo garbage
   silently killed the whole `xchk` battery (§2.3). The fix was to classify the
   fallback's output, not to delete it.
5. **A machine whose ROM is missing reads as a machine that answers nothing.**
   The §3.5 follow-up measurement returned `<no capture>` on *every* zerobas
   row, which spells "zerobas does not keep `CRTCNT`" convincingly and was
   actually `build/` having been cleaned: the installed machine config embeds
   **absolute paths** into `build/`, so a `rm -rf build` leaves a config that
   still resolves, still boots, and produces nothing. The tell is that the
   failure was *total* — a trivial `PRINT 1+1` failed too. `make repack-machine`
   (not `make install`, which does not build the merged repack ROM) restores it.
   Same family as [`stale-machine-reads-as-unimplemented`](../MEMORY.md), one
   step worse: there the machine answered from stale code, here it did not
   answer at all. **A baseline that cannot produce a known-good answer is not a
   baseline** — check the control before reading the subject.

Standing guards:

- **`MAX_ECHO = 33`, enforced at startup** — the probe refuses to run rather than
  report rows that would agree while measuring nothing (§2.1).
- **The marker search covers the WHOLE screen**, not the first six rows as in the
  cursor probe: this battery's cases reach row 22, and a search window shorter
  than the cases can reach would report `none` for a marker that landed perfectly
  — the T2 capture-window trap.
- **`CHR$(35)` is the marker, never a literal `#`**, so the grid search cannot
  find it inside an echoed command and report a confident, wrong column.
- **Every number above was confirmed with `BOOTPC=1`, and the confirmation was
  not a formality.** `run_differential` self-heals a disagreeing two-sided row by
  re-running it boot-per-case, so calibration verdicts already equal a
  boot-per-case run — but reference-only rows are delivered batched and nothing
  re-checks them, and they are what the spec is built on. The confirmation run
  disagreed with the batched run on `le-four`, and that disagreement is the only
  reason apparatus defect #3 was found.
- **`SCREEN 0` is restored on the same line** by the `le-scr1`/`le-scr2` rows: a
  case that leaves a graphics screen behind poisons every following case in the
  shared boot, whose scrape then reads a graphics name table.
