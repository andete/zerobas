<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `LPOS` — the printer head's column

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: a string as the dummy argument (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LPOS(0)` is the column the printer head is at: how many characters have been
sent to the printer since the last carriage return. It is to
[`LPRINT`](LPRINT.md) what [`POS`](POS.md) is to `PRINT`, with the same dummy
argument. zerobas behaves like the Philips VG-8020 in every case we have
measured except one: a string as the dummy argument.

## Syntax

```
LPOS(<dummy>)
```

The parentheses and one argument are required; the value is ignored.

## Details

All of these were measured on the VG-8020 and the National CF-3300 with a
printer attached, and agree on both:

- **0 on a fresh machine**, before anything has been printed.
- **It counts the characters actually sent.** `LPRINT "ABC";:PRINT LPOS(0)`
  gives 3; fourteen characters give 14. Padding counts too:
  `LPRINT TAB(10);:PRINT LPOS(0)` gives 10.
- **A completed line puts it back to 0.** `LPRINT "ABC":PRINT LPOS(0)` gives 0,
  because the `LPRINT` ended with a carriage return.
- **A half-finished printer line is ended when BASIC returns to the prompt.**
  Typed as two separate commands, `LPRINT "A";` and then `PRINT LPOS(0)` gives
  0, not 1: the line was finished in between. Read `LPOS` in the same line or
  program as the `LPRINT` it is about.
- **The argument is ignored, with no range check**: `LPOS(1)`, `LPOS(255)`,
  `LPOS(-1)` and `LPOS(300)` all give the same answer.
- **Errors**, the same on both machines: `LPOS` without parentheses,
  `LPOS()` and `LPOS(1,2)` are `Syntax error` (error 2). That is the whole
  error set. `LPOS("A")` differs — see below.
- What `LPOS` does when a line reaches the printer's right margin has not been
  measured.

## Example

This example sends nothing to the printer, so it runs without one; it shows
the resting value and the ignored argument. A program that prints first is
on the [`LPRINT`](LPRINT.md) page.

```
10 PRINT LPOS(0);LPOS(-1);LPOS(300)
20 ON ERROR GOTO 50
30 PRINT LPOS()
40 END
50 PRINT "Error";ERR:RESUME NEXT
RUN
 0  0  0
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_lpos.out`](../../scratchpad/kwdoc_lpos.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`LPOS("A")` is `Type mismatch` here and accepted on the VG-8020**
(D-POSDUMMY, found 2026-09-27, filed in [TODO.md](../../TODO.md) as a TIER 6
item, together with `POS("A")`). The reference does not check the dummy's
type. Because the reference raises nothing there, it does not hold back the
"every error" rung.

The other rung not yet proven is **RAM usage**, which has not been compared
for `LPOS` yet.

## What we found, and how

- **`LPOS` arrived on 2026-08-06** (D-LPTVERB), with `LPRINT`, after 38 rows
  were measured on both reference machines
  ([lptverb-msx1-characterization.md](../lptverb-msx1-characterization.md)).
  Before that it was not a keyword, and `PRINT LPOS(0)` quietly printed two
  numbers: a variable `L` and then `POS(0)`.
- **The two readings that looked contradictory.** `LPRINT "A";` left a
  carriage return in the printer's log, which suggested the `;` did nothing;
  `LPOS` read 3 after `LPRINT "ABC";` in the same line, which said it worked.
  A third reading, `LPOS` as a separate command, showed both were right: the
  line is ended later, on the way back to the prompt.
- **The counter must not be the screen's.** On a fresh machine the screen
  column and the printer column are both 0, so a `LPOS` that read the screen
  cursor would pass a test that only looks at rest; the tests print 3, 10 and
  14 characters first.
- **The counter started with garbage** in the first build (2026-08-06): it was
  never set at power-on, and the machine sent a stray carriage return to the
  printer at the first prompt. A control row that does not use `LPOS` at all
  caught it.
- **`LPOS(300)` was added on 2026-08-07** (D-DSKMSG), because the rule "no
  range check, not even outside 0..255" had been resting on 255, which is
  inside that range.

## Where it lives

`ev_ff_lpos` in [basic/expr.asm](../../basic/expr.asm) reads the counter
`LPTPOS`. The counter is kept by the printer sink `pch_lpt` in
[basic/print.asm](../../basic/print.asm), so every byte that reaches the
printer moves it, padding included. The return-to-prompt flush is in
[basic/repl.asm](../../basic/repl.asm).

## Tests that cover it

- `make lptverb-acceptance` — the `lps-` rows: at rest, after 3, 10 and 14
  characters, after a completed line, the flush, and the dummy values.
- `make kwsweep` — the everyday row (with a printer plugged in) and the error
  rows for {2}.
