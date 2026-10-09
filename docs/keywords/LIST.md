<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no run=LIST answers="LIST 20-|LIST 10,30" -->

# `LIST` — show the program on the screen

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LIST` prints the stored program as text: each line's number, a space, and the
line itself, with every keyword spelled out again. With a line number or a
range it prints only that part. zerobas behaves like the Philips VG-8020 in
every case we have measured, errors included.

## Syntax

```
LIST
LIST <line>
LIST <from>-<to>
LIST <from>-
LIST -<to>
```

The line numbers are plain numbers (not expressions). `.` may stand for a line
number: it means the line the editor last touched.

## Details

- **`LIST n` lists line `n` only** — exactly like `LIST n-n`.
- **Neither end of a range has to exist.** `LIST 15-35` lists every stored line
  from 15 to 35. The listing starts at the first stored line at or above the
  low end.
- **An open end means "to the edge of the program".** `LIST 20-` lists from 20
  to the end; `LIST -30` from the start up to 30. (Under `DELETE` the same
  `20-` is an error — the two verbs share a grammar but not its rules; see
  [`DELETE`](DELETE.md).)
- **There is no range error.** A reversed range (`LIST 30-20`), a line that is
  not there (`LIST 25`), a range above the program and an empty program all
  list nothing and leave `ERR` at 0.
- **A comma is not a separator**: `LIST 10,30` is `Syntax error` (error 2).
- **`LIST` ends the line and the program.** `LIST 20:B=9` lists line 20 and
  never runs `B=9`; a `LIST` inside a running program lists and then the
  program stops, without an error.
- **`LIST` is not a program edit**: variables and the `CONT` point survive it
  (unlike `DELETE`, `NEW` or typing a line).
- **`.` after a `LIST` is the last line it printed**; a `LIST` that printed
  nothing leaves `.` alone.

| you type | you get |
|---|---|
| `LIST` | the whole program |
| `LIST 20` | line 20, if it exists; otherwise nothing |
| `LIST 15-35`, `LIST 20-35` | the stored lines from 15 (or 20) to 35 |
| `LIST 20-` / `LIST -30` | from 20 to the end / from the start to 30 |
| `LIST 30-20`, `LIST 25` (no such line) | nothing, no error |
| `LIST 10,30` | error 2, `Syntax error` |

The whole set of errors `LIST` can raise is {2}, the same on both machines.

## Example

```
10 REM ALPHA
20 PRINT "BETA"
30 GOTO 10
LIST
10 REM ALPHA
20 PRINT "BETA"
30 GOTO 10
LIST 20-
20 PRINT "BETA"
30 GOTO 10
LIST 10,30
Syntax error
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_list.out`](../../scratchpad/kwdoc_list.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **The line numbers used to be ignored** (fixed 2026-08-02, D-LSTRNG): every
  `LIST` printed the whole program. Twenty shapes were measured on both
  reference machines first, and the surprise was that `DELETE`'s range rules,
  measured a day earlier with the same grammar, do **not** carry over — five of
  the twenty would have come out wrong if they had been copied
  ([listrange-msx1-characterization.md](../listrange-msx1-characterization.md)).
- **Two predictions were wrong, and the measurement won.** It was expected that
  `LIST` would let the rest of the line run and would not stop a program,
  because it changes nothing. On both references it ends both. The same round
  showed that it keeps variables and `CONT`, so it must not copy `DELETE`'s
  reset.
- **`.` landed the same day** (D-DOTLINE, 2026-08-02), after measuring that it
  is the line the editor last touched — and that `LIST` itself sets it to the
  last line printed
  ([dotline-msx1-characterization.md](../dotline-msx1-characterization.md)).
- **The tests had a blind spot** (2026-09-14, D-KWLISTSEL): the only keyword
  sweep row was a bare `LIST`, which cannot see a `LIST` that ignores its
  argument. Rows for one line and for a range were added.

## Where it lives

- [basic/list.asm](../../basic/list.asm): `ex_list` is the statement;
  `list_walk` prints the selected lines; `ex_llist` (for
  [`LLIST`](LLIST.md)) shares all of it and only changes where the text goes.
- The argument parse is `le_lstrange` in
  [sub/lineedit.asm](../../sub/lineedit.asm), beside `DELETE`'s parse that it
  deliberately does not resemble.
- The design notes are in [spec-basic-listrange.md](../spec-basic-listrange.md).

## Tests that cover it

- `make lnblank-say-acceptance` — the `lst-` and `lse-` rows: every range
  shape, `ERR` after each, the `:` tail, `LIST` inside a program, and `.`.
- `make kwsweep` — the bare, single-line and range rows, and the error row
  for {2}.
- `make kwram` — the RAM-usage comparison.
