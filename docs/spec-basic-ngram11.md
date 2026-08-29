# D-NGRAM11 — one `str_eval_next` for the six "past the delimiter, evaluate a string" sites

*2026-08-29. `basic/interp.asm` (helper + 1 site), `arrays.asm`, `field.asm`,
`str-engine.asm` (×3). Probe `scratchpad/ngram11_probe.py`, arms
`scratchpad/ngram11_knives.py`.*

**Cost: −17 B** — page-0 low 118 → **134 B** free, page 1 348 → 349. Four of the
six sites are in the low region, which is where D-LEFTTM had just spent 16 B.
**Rows: 16, 2 DIFF (both pre-existing), 3 no-oracle.**

## 1. The carve

`inc hl / call skip_spaces / call str_eval` stood open-coded at six sites, all
saying the same sentence: *the byte at HL is a delimiter I have just matched, so
step over it, skip spaces, and evaluate the string expression that follows.*

| site | statement |
|---|---|
| `arrays.asm` | `LET A$(i) = …` |
| `field.asm` | `LSET` / `RSET` |
| `interp.asm` | `LET A$ = …` |
| `str-engine.asm` | the `MID$` statement |
| `str-engine.asm` ×2 | `INSTR`'s two string arguments |

7 B each, **42 B**; a 7 B body plus six 3 B calls is **25 B**.

Every caller keeps its **own** `jp/jr nc,<target>` — six different decline
destinations — which is exactly why this is a call and not a shared tail.
[[a-shared-tail-is-not-a-decision]]

## 2. The tail is a `jp`, and the arm says what that is worth

Ending `jp str_eval` rather than `call str_eval / ret` makes the stack depth at
`str_eval` **identical** to the open-coded form. That is the property D-NGRAM8
lost when it put `str_eval` behind a `call` whose `ret` landed one frame too
shallow and the decline stopped declining.

⚠️ **But K-N11B says that is a guarantee, not a measured hazard.** Turn the tail
into `call` + `ret` and **zero rows move**: `str_eval` returns normally, so at
these six sites the extra frame is popped before any caller sees it. The tail
jump's value here is *structural* — it cannot go wrong for the next caller anyone
adds — plus one saved byte. An arm that asserts its own zero beats a comment
asserting a danger that was never demonstrated.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

## 3. 🔴 One of the two "controls" was a subject row

`ctl.cat` was `['A$="AB":B$="CD"'], 'A$+B$'` — and its **setup is two `LET A$=`
statements**, one of the six sites. K-N11A moved it, which is how it was caught.

A control that runs the subject's own machinery is not a control; it is an
unlabelled subject row that reads as reassurance every time it stays green. It is
renamed `g.letcat`, and a real control (`ctl.lit`, `"AB"+"CD"` — literals only,
no `LET`) put in its place.

## 4. 🔴 I predicted seven rows for K-N11A and twelve moved

| | |
|---|---|
| predicted | the 7 success rows |
| measured | **12** |

Both surprises were real. The `b.*` rows for LET / LSET / MID$ move as well —
**13 (or 2) → 24**. With the delimiter unconsumed, `str_eval` is handed the `=`
itself, so the decline reason changes from *"there is a non-string here"* to
*"there is **nothing** here"*, which is `Missing operand`. **I had assumed a row
that is already declining cannot move; the code it declines *with* is part of the
reading.** And `g.letcat` moved for the reason in §3.

`b.instr` / `b.instrp` correctly do **not** move — their `ERR 2` comes from an
earlier stage this cut never reaches — and neither do `ctl.num` and `ctl.lit`.

## 5. Two pre-existing divergences, and three rows with no oracle

**DIFF (verified pre-existing by revert — HEAD gives the identical reading):**

| row | references | zerobas |
|---|---|---|
| `INSTR("ABCDE",5)` | ERR 13 | **ERR 2** |
| `INSTR(2,5,"CD")` | ERR 13 | **ERR 2** |

Same family as D-LEFTTM: a declined string operand reported as `Syntax error`
where the reference says `Type mismatch`. Filed.

**NO ORACLE — the two references disagree with each other:** `LSET`/`RSET` on a
variable that was never `FIELD`ed reads `Illegal function call` on the
cassette-only VG-8020 and pads in place on the disk-equipped CF-3300. zerobas
targets the disk machine and agrees with it. Scored **separately** rather than
counted as a divergence, and **named in the report** rather than dropped — an
unscored row that vanishes reads as coverage.
[[an-unnamed-outcome-reads-as-no-outcome]]

## 6. Falsification

| arm | requires | measured |
|---|---|---|
| **S1** | 0 open-coded runs, exactly 6 calls, **every pattern element alive** | ✅ |
| K-N11A | drop the `inc hl` → the delimiter is never consumed | **exactly 12** |
| K-N11B | tail jump → `call` + `ret` → asserted **0**, reason named | **0** |

S1 expects **zero**, so its matcher control is not optional: the helper's own
tail is a `jp`, so the body does not match the pattern and 0 is the honest
expectation — which is indistinguishable from a typo'd pattern without the
control. [[a-knife-can-be-inert-because-the-build-did-not-happen]]
