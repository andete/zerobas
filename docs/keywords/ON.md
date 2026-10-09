<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no wait=12 -->

# `ON` — the start of eight different statements

> **Status (2026-10-09):** `ON` has no form of its own; it only ever starts one
> of the statements below, and each is tracked and documented as that
> statement. `ON INTERVAL GOSUB`, which has no other page, is covered in full
> here: every measured form agrees with the VG-8020.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ON` is never a statement by itself. It is the first word of eight
statements, which fall into two families:

- **a choice of line** — `ON n GOTO` and `ON n GOSUB` jump to the n-th line of
  a list;
- **a trap** — `ON ERROR GOTO` and the five `ON … GOSUB` interrupt traps name a
  line to run when something happens: an error, a function key, a joystick
  button, a sprite collision, Ctrl-STOP, or a timer.

## Where each `ON` statement is described

| statement | what it does | page |
|---|---|---|
| `ON n GOTO l1,l2,…` | jump to the n-th line of the list | [`GOTO`](GOTO.md) |
| `ON n GOSUB l1,l2,…` | call the n-th line of the list as a subroutine | [`GOSUB`](GOSUB.md) |
| `ON ERROR GOTO l` | run line l when an error happens | [`RESUME`](RESUME.md), section *`ON ERROR GOTO`*; also [`ERROR`](ERROR.md), [`ERR`](ERR.md), [`ERL`](ERL.md) |
| `ON KEY GOSUB l1,…,l10` | run a line when a function key is pressed | [`KEY`](KEY.md) (`KEY(n) ON`/`OFF`/`STOP`) |
| `ON STRIG GOSUB l1,…,l5` | run a line when the space bar or a joystick button is pressed | [`STRIG`](STRIG.md) |
| `ON SPRITE GOSUB l` | run a line when two sprites collide | [`SPRITE`](SPRITE.md), section *`SPRITE ON` / `OFF` / `STOP`* |
| `ON STOP GOSUB l` | run a line instead of stopping on Ctrl-STOP | [`STOP`](STOP.md) |
| `ON INTERVAL=n GOSUB l` | run a line every n frames | this page, below |

The five interrupt traps share one model: `ON … GOSUB` **arms** the trap, a
separate statement (`KEY(n) ON`, `STRIG(n) ON`, `SPRITE ON`, `STOP ON`,
`INTERVAL ON`) **enables** it; `… STOP` holds an event back until the trap is
enabled again, `… OFF` forgets it; the handler ends with `RETURN`. An `ON …
GOSUB` with no line number disarms the trap.

## `ON INTERVAL=n GOSUB` — a timer

```
ON INTERVAL=<numeric expression> GOSUB [<line number>]
INTERVAL ON | OFF | STOP
```

`INTERVAL` is not in the keyword table of either machine: it is typed as the
two keywords `INT` and `VAL` around the letters `ER`, and both machines
recognise the combination. Everything below was measured on the VG-8020 and
agrees on zerobas
([spec-traps-t5-interval.md](../spec-traps-t5-interval.md) §1).

- **The period is exactly n frames** (screen refreshes; the same counter
  `TIME` uses). `n=1` fires every frame.
- **n is converted like an address**: anything from −32768 to 65535 is
  accepted, a fraction is truncated toward zero (`2.7` gives 2), `0` is
  `Illegal function call` (error 5), and outside that range is `Overflow`
  (error 6). A variable works: `ON INTERVAL=Q GOSUB 800`.
- **Arming is not enabling.** Nothing fires until `INTERVAL ON`.
  `INTERVAL ON` with nothing armed is accepted and does nothing.
- **`INTERVAL STOP` remembers, `INTERVAL OFF` forgets.** While stopped the
  timer keeps running; at most one missed period is held back and fires
  straight after `INTERVAL ON`, however many periods went by.
- **The period counts from the moment the trap fires**, not from the
  handler's `RETURN`. So a handler that takes longer than the period runs
  again the moment it returns, and the main program never gets another turn —
  on both machines.
- **`ON INTERVAL=n GOSUB` again restarts the count**; `INTERVAL OFF` /
  `INTERVAL ON` do not.
- **No line number** (`ON INTERVAL=10 GOSUB`) is accepted and disarms the
  trap; arming it again later needs no second `INTERVAL ON`.

| you write | you get |
|---|---|
| `ON INTERVAL=10 GOSUB 777` (no line 777) | error 8, `Undefined line number`, when the statement runs |
| `ON INTERVAL=10 GOTO 800` | error 2, `Syntax error` |
| `ON INTERVAL GOSUB 800` (no `=n`) | error 2 |
| `INTERVAL` alone, `INTERVAL FOO` | error 2 |
| `ON INTERVAL=0 GOSUB 800` | error 5 |
| `ON INTERVAL=65536 GOSUB 800` | error 6 |

## Example

```
10 ON ERROR GOTO 120
20 ON INTERVAL=10 GOSUB 100
30 INTERVAL ON:T=TIME
40 IF TIME-T<100 THEN 40
50 INTERVAL OFF:PRINT C>=9 AND C<=10
60 ON INTERVAL=0 GOSUB 100
70 END
100 C=C+1:RETURN
120 PRINT "Error";ERR:RESUME NEXT
RUN
-1
Error 5
```

The handler counts its calls for 100 frames; with a 10-frame period that is 9
or 10 calls, depending on where the first frame falls, so the program prints
the test rather than the count. Run on the VG-8020 and on zerobas on
2026-10-09; both print exactly this
([`kwdoc_on.out`](../../scratchpad/kwdoc_on.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known for `ON INTERVAL GOSUB`. The other `ON` statements' differences, if
any, are on their pages.

## What we found, and how

- **`INTERVAL` was first recorded as an MSX2 feature, and that was wrong**
  (2026-07-24, corrected two days later). The test that looked for it searched
  the keyword table, where `INTERVAL` never is; it is built from `INT` and
  `VAL`, and it works on the VG-8020. Before it landed, every `ON INTERVAL`
  form was `Syntax error` here.
- **It landed on 2026-07-26** (traps slice T5), with a 149-case gate measured
  against the VG-8020 first: the period, the conversion of n, arming versus
  enabling, `STOP` versus `OFF`, where the count starts, and the starving
  handler.
- **That gate found one real defect before it shipped**: a period missed while
  the trap was stopped was remembered but never released. The other traps
  never showed it, because their events are re-checked every frame, while a
  timer's is a one-off.

## Where it lives

`ex_on_interval` in [basic/program.asm](../../basic/program.asm) arms the
trap; the shared trap machinery (`trap_line_link`, the per-frame poll) serves
all five interrupt traps.

## Tests that cover it

- `make interval-trap-acceptance` — the 149-case `ON INTERVAL` gate.
- `make kwsweep` — the everyday row (an armed, enabled timer fires) and the
  `INTERVAL OFF` row.
