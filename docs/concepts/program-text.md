<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no run=LIST answers="RUN" -->

# Program text — how a typed line becomes a program line

> **Status (2026-10-09):** a typed line is crunched to the same bytes as on the
> VG-8020 and the CF-3300, stored in the same format at the same address, and
> listed back the same way, in every case measured. No TIER 1–3 item is open.
> How much program fits in memory is a RAM-usage question (TIER 4), covered on
> [`memory-map.md`](memory-map.md).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

When you press RETURN on a line that starts with a number, BASIC does not run
it: it **stores** it as a program line under that number. Lines are kept in
number order whatever order you type them in. Typing a line with a number that
already exists **replaces** that line; typing a number on its own **deletes**
it.

The line is not stored as the text you typed. It is first **crunched**
("tokenised"): every keyword becomes a one- or two-byte token, numbers become
binary constants, and letters outside strings and comments become upper case.
[`LIST`](../keywords/LIST.md) turns the tokens back into text, so what it shows
is the program's own spelling, not necessarily yours: `?` comes back as
`PRINT`, `goto 1 0` as `GOTO 10`.

## How it works

### Is it a program line?

After the [screen editor](screen-editor.md) has read the line, leading blanks are
skipped. If the first character is a digit, the line is a program line;
otherwise it is executed at once ("direct mode").

- **The line number** runs from 0 to **65529**. A larger number is
  `Syntax error` (error 2) and nothing is stored.
- **Blanks inside the number do not count**: `2 0 REM X` is line 20, and a
  bare `2 0` deletes line 20.
- **One blank after the number** separates it from the line; any further
  blanks are kept as part of the line. (After line number 0 no blank is taken.)
- **An empty rest deletes**: the number alone removes that line.
- **Storing or deleting prints no prompt**; only a command or an error does.

Every store, replacement or deletion is a **program edit**: all variables are
cleared, `CONT` can no longer continue, and `.` (the "current line" used by
`LIST .`, `DELETE .` and others) becomes the number just typed.

### Crunching

| typed | stored as |
|---|---|
| a statement keyword (`PRINT`, `GOTO`, `END`, …) | one byte, from `$81` up (`END` `$81`, `GOTO` `$89`, `PRINT` `$91`) |
| a function keyword (`PEEK`, `HEX$`, …) | two bytes: `$FF` and a second byte (`PEEK` = `$FF $97`) |
| an operator (`>` `=` `<` `+` `-` `*` `/` `^` `AND` `OR` … `\`) | one byte, `$EE` to `$FC` (`=` is `$EF`, `+` is `$F1`) |
| `?` | the `PRINT` token |
| `'` | `:` + `REM` + `$E6` |
| `ELSE` | `:` + `$A1` |
| a variable name | its letters, upper-cased |
| a string `"…"`, a `REM` or `'` comment, a `DATA` list, a `CALL` name | the characters as typed, case included |

Keywords are recognised **anywhere**, even inside a name: `SCORE` is stored as
`SC`, `OR`, `E`, so it cannot be used as a variable name the way it reads.

Numbers become constants, so `LIST` always shows them in one standard form:

| constant | stored as |
|---|---|
| 0 to 9 | one byte, `$11` to `$1A` |
| 10 to 255 | `$0F` + one byte |
| 256 to 32767 | `$1C` + two bytes, low byte first |
| a larger or fractional number | `$1D` + 4 bytes (single precision) or `$1F` + 8 bytes (double) |
| `&H…` / `&O…` | `$0C` / `$0B` + two bytes |
| `&B…` | kept as text, read when the line runs |

Blanks inside a decimal number are ignored here too: `A=1 0` stores the
constant 10 and `A=1 . 5` the constant 1.5. Inside an `&H` number they are not.

### Line numbers inside a line

After fourteen words — `GOTO`, `GOSUB`, `THEN`, `ELSE`, `RUN`, `RESTORE`,
`RESUME`, `RETURN`, `LIST`, `LLIST`, `DELETE`, `AUTO`, `RENUM` and `ERL` — a
number is stored as a **line reference**: `$0E` and the line number in two
bytes. That is what lets `RENUM` find and rewrite every reference. The list is
just a list: `IF`, `ERROR` and `ERR`, whose tokens sit right next to these, do
not do it. A reference larger than 65529 is split: `GOTO 99999` stores the
references 9999 and 9.

### The length limits

- **254 characters typed.** Anything past that is dropped without an error,
  and the shortened line is stored.
- **314 bytes crunched.** Crunching can make a line longer (a `#` constant
  takes nine bytes); past 314 the line is refused with `Line buffer overflow`
  (error 25), and nothing is stored or run.
- A number too large for a constant (`A=1E99`) is `Overflow` (error 6) at
  entry, again with nothing stored. After such an entry error `ERL` reads
  65535 (measured for errors 2 and 6).
- When the program would not fit in memory the line is refused with
  `Out of memory` (error 7).

### How it sits in memory

The program starts at the address in `TXTTAB` (`$F676`), which is `&H8001` on
the VG-8020 and on zerobas. Each line is

```
[address of the next line: 2 bytes] [line number: 2 bytes] [crunched text] [0]
```

with two-byte values low byte first, and a "next line" address of 0 ends the
program. The variables start right after that end marker; `VARTAB` (`$F6C2`)
holds the address. The MSX documentation also describes a second form of line
reference, `$0D` plus an address, that BASIC may use while a program runs;
zerobas never writes it, and whether the reference does so visibly has not
been measured.

### Back to text: LIST

`LIST` walks the lines in order and prints each one's number, a blank, and its
text: tokens become their keywords (in upper case), constants are printed in
decimal (`&H` and `&O` ones in their own base), `:` + `REM` + `$E6` comes back
as `'` and `:` + `$A1` as `ELSE`. Everything stored as text — names, strings,
comments, the blanks you typed — comes back as stored. `LLIST` and an ASCII
`SAVE "…",A` produce the same text. A line read from an ASCII file by `LOAD`
or `MERGE` goes through the same crunch and store as a typed one.

### AUTO, RENUM, DELETE

[`AUTO`](../keywords/AUTO.md) types the line numbers for you,
[`RENUM`](../keywords/RENUM.md) rewrites the numbers and every `$0E` reference,
[`DELETE`](../keywords/DELETE.md) removes a range and, unlike `RENUM`, counts as
a program edit.

## Example

Lines typed out of order, one replaced, one added and deleted again:

```
30 ?"C";PEEK(&H8003);PEEK(&H8004)
10 print "a";:rem lower
20 PRINT "B"
20 print "b":goto 3 0
25 X=1
25
LIST
10 PRINT "a";:REM lower
20 PRINT "b":GOTO 30
30 PRINT"C";PEEK(&H8003);PEEK(&H8004)
RUN
ab
C 10  0
```

The listing is in number order, keywords and the variable are upper case, the
string and the comment keep their lower case, `?` is `PRINT` and `3 0` is `30`.
`PEEK(&H8003)` and `PEEK(&H8004)` read the first line's number out of the
stored program: 10, low byte first. Run on the VG-8020 and on zerobas on
2026-10-09; both print exactly this
([`kwdoc_program-text.out`](../../scratchpad/kwdoc_program-text.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known in what is stored or listed. Not yet measured on the reference:
typing the number of a line that does not exist on its own (zerobas stores
nothing and reports nothing), and the `$0D` form above.

## What we found, and how

- **The keyword tokens were read off the reference, not copied from a table.**
  Each was found by crunching the keyword on a VG-8020 and reading the stored
  bytes; published token tables were only a cross-check (`AUTO`, `DELETE`,
  `RENUM` and `LLIST` last, D-KWGAP4, 2026-08-01).
- **A blank inside a line number used to end it**, so `20 0#` was line 20 here
  and line 200 on the reference — and an unguarded ceiling stored `99999 REM`
  as line 34463 without a word. Both fixed on 2026-07-31 (D-LNBLANK), after the
  two references were found to agree on all 54 measured shapes. The rule is the
  decimal-number scanner's, not the line number's: `A=1 0` is 10 too.
- **Crunching could overrun its buffer** (D-LINEMAX, 2026-07-29). A line of
  `0#0#0#…` only 27 characters long expanded past the old 96-byte buffer, and
  after a longer one zerobas could no longer run `B=7`. The reference refuses
  such a line with `Line buffer overflow`; zerobas now does the same, and the
  typed limit went from 95 characters to the reference's 254.
- **Line references were missing after eight words** (D-LNREF, 2026-08-01).
  Walking all 162 reserved words on both references found fourteen that store
  a `$0E` reference, not the six zerobas had. One was a live defect:
  `IF 0 THEN 20 ELSE 30` was `Syntax error` here.
- **zerobas printed its prompt after every stored line**, so typing a program
  scrolled the screen twice as fast. The reference prompts only after a command
  or an error (D-OKSTORE, 2026-09-24).

## How zerobas does it

`dispatch_line` in [basic/program.asm](../../basic/program.asm) decides what a
line is: `parse_lineno` reads the number (blanks inside it included) and the
65529 ceiling is checked there; then the line is crunched into `TOKBUF`. The
crunch itself, [basic/tokenise.inc](../../basic/tokenise.inc), runs in the
sub-ROM, once per line; its keyword list is
[basic/kwtable.inc](../../basic/kwtable.inc) and fractional and large numbers
go through [sub/tkfloat.asm](../../sub/tkfloat.asm); the 314-byte limit is
tested once, at the end of the line. The store is `le_store` in
[sub/lineedit.asm](../../sub/lineedit.asm): find the slot (deleting a line with
the same number), open a gap, copy the line in, recompute every "next line"
address, and clear the variables.

`LIST` is `ex_list` and `list_walk` in [basic/list.asm](../../basic/list.asm);
the text of each line is rebuilt by the shared detokeniser body
[basic/detok.inc](../../basic/detok.inc), run in the sub-ROM by
[sub/detok.asm](../../sub/detok.asm). It renders into a 96-byte window and
renders a longer line again for each further piece, so no large buffer is
taken out of program memory. The same table serves both directions, so a
keyword cannot crunch one way and list another.

The measurements behind this page are in
[lnblank-msx1-characterization.md](../lnblank-msx1-characterization.md),
[lnref-msx1-characterization.md](../lnref-msx1-characterization.md),
[linemax-vg8020-characterization.md](../linemax-vg8020-characterization.md) and
the token specs [spec-tokenise.md](../../basic/docs/spec-tokenise.md) and
[spec-tokens-statements.md](../../basic/docs/spec-tokens-statements.md).

## Related pages

- [`screen-editor.md`](screen-editor.md) — how the line is read first.
- [`LIST`](../keywords/LIST.md), [`LLIST`](../keywords/LLIST.md),
  [`AUTO`](../keywords/AUTO.md), [`RENUM`](../keywords/RENUM.md),
  [`DELETE`](../keywords/DELETE.md), [`NEW`](../keywords/NEW.md),
  [`REM`](../keywords/REM.md), [`DATA`](../keywords/DATA.md),
  [`CONT`](../keywords/CONT.md), [`SAVE`](../keywords/SAVE.md),
  [`LOAD`](../keywords/LOAD.md), [`MERGE`](../keywords/MERGE.md).
- [`numbers.md`](numbers.md), [`variables.md`](variables.md),
  [`memory-map.md`](memory-map.md), [`errors.md`](errors.md).
- More keywords: [`END`](../keywords/END.md), [`GOTO`](../keywords/GOTO.md).

## Tests that cover it

- `make lnblank-acceptance` — the stored bytes of each crunch shape: line
  numbers and blanks, the line-number ceiling, decimal and `.` constants,
  names, keywords after an exponent, and line references, walked over the
  reserved words; on the VG-8020, the CF-3300 and zerobas.
- `make lnblank-say-acceptance` — the effect on `LIST`, `.` and the error code.
- `make linemax-acceptance` — the 254-character and 314-byte limits.
- `make editverb-acceptance` — `RENUM`, `AUTO` and `LLIST`.
- `make txtceil-acceptance` — a program never outgrows its memory.
- `make kwsweep` — the crunched bytes of the keyword rows it carries.
