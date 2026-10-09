<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no answers="PRINT 1/0|PRINT ERR;ERL" -->

# Errors — codes, messages and `ON ERROR`

> **Status (2026-10-09):** every error code and every message is the
> reference's, letter for letter, and trapping, `ERR`, `ERL` and `RESUME` match
> the VG-8020 in every case measured. Open: a few rare failure paths still print
> zerobas's own `load error` instead of raising a trappable code (D-LOADERRRET,
> TIER 3); a malformed `ERROR` argument (D-ERRORARG, TIER 6); disk messages for
> 60–64 on the diskless build (D-NODISKERRTXT, TIER 6).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

Every error in MSX BASIC has a **number**, its code, and a **message**. When a
running program hits an error it stops and prints the message followed by
` in ` and the line number — `Division by zero in 20` — and returns to the
prompt. Typed at the prompt, the same error prints just the message.

A program can catch errors instead: `ON ERROR GOTO <line>` names a handler,
which reads the code in `ERR` and the line in `ERL` and leaves with `RESUME`.
`ERROR n` raises error `n` on purpose. zerobas uses the same codes, text and
trapping rules as the Philips VG-8020; on the disk build, the disk codes are
the National CF-3300's.

## How it works

### What an untrapped error does

The message starts on a fresh line and, in a program, ends with ` in <line>`,
the line of the failing statement. A graphics screen is left for the text
screen first, as `STOP` does; music still playing is silenced (a *trapped*
error leaves it playing); [`CONT`](../keywords/CONT.md) retries the failing
statement; and `LIST .` lists the failing line.

### The codes

The messages below were read off both reference machines by raising each code
with `ERROR n`; zerobas prints the same text, capitals included
([msgexact-msx1-characterization.md](../msgexact-msx1-characterization.md)).
Codes 1 to 25 belong to BASIC itself and read the same on both machines:

| code | message | code | message |
|---:|---|---:|---|
| 1 | `NEXT without FOR` | 14 | `Out of string space` |
| 2 | `Syntax error` | 15 | `String too long` |
| 3 | `RETURN without GOSUB` | 16 | `String formula too complex` |
| 4 | `Out of DATA` | 17 | `Can't CONTINUE` |
| 5 | `Illegal function call` | 18 | `Undefined user function` |
| 6 | `Overflow` | 19 | `Device I/O error` |
| 7 | `Out of memory` | 20 | `Verify error` |
| 8 | `Undefined line number` | 21 | `No RESUME` |
| 9 | `Subscript out of range` | 22 | `RESUME without error` |
| 10 | `Redimensioned array` | 23 | `Unprintable error` |
| 11 | `Division by zero` | 24 | `Missing operand` |
| 12 | `Illegal direct` | 25 | `Line buffer overflow` |
| 13 | `Type mismatch` | | |

Code 26 has no message on either machine; zerobas prints `Unprintable error`
for everything from 26 to 49. From 50 up are the file and disk codes, and the
measurement corrected an assumption: the diskless VG-8020 prints 50 to 59
itself, so only 60 and up belong to the disk ROM.

| code | message | code | message |
|---:|---|---:|---|
| 50 | `FIELD overflow` | 60 | `Bad FAT` |
| 51 | `Internal error` | 61 | `Bad file mode` |
| 52 | `Bad file number` | 62 | `Bad drive name` |
| 53 | `File not found` | 63 | `Bad sector number` |
| 54 | `File already open` | 64 | `File still open` |
| 55 | `Input past end` | 65 | `File already exists` |
| 56 | `Bad file name` | 66 | `Disk full` |
| 57 | `Direct statement in file` | 68 | `Disk write protected` |
| 58 | `Sequential I/O only` | 69 | `Disk I/O error` |
| 59 | `File not OPEN` | 70 | `Disk offline` |

50–59 print the same on both machines. 60–70 are the CF-3300's texts; the
VG-8020 prints `Unprintable error` for them (measured for 60–64 and 70; 65, 66,
68 and 69 not measured there), and so does the diskless zerobas build for 66
and 68–70. Codes 67, 71 and 72 have not been measured on the CF-3300; zerobas
prints `Unprintable error` for them.

**The `Unprintable error` rule.** `ERROR n` accepts any code from 1 to 255
(`ERROR 0` and `ERROR 256` are error 5). A code with no message of its own
still sets `ERR` to `n` and prints `Unprintable error`, which is also the
literal text of code 23.

### `ERR` and `ERL`

- **`ERR` is the code of the last error, `ERL` its line.** Both are 0 on a
  machine that has had no error yet, and both survive the program stopping, so
  `PRINT ERR;ERL` at the prompt shows what went wrong.
- **An error with no line** — typed at the prompt, or a line the editor refuses
  as you type it (`70 X=1E99` is `Overflow`, `70000 X=1` is `Syntax error`) —
  sets `ERL` to 65535.
- **`RESUME` sets `ERR` back to 0 and leaves `ERL` alone.**
- **zerobas keeps them in the documented work-area cells** `ERRFLG`
  (`&HF414`) and `ERRLIN` (`&HF6B3`); the handler is `ONELIN` and `ONEFLG`.

### `ON ERROR GOTO`, `RESUME` and `ERROR`

`ON ERROR GOTO 0` disarms the handler; inside an active handler it also hands
the error back, and BASIC stops with the original message and line. `RESUME`
retries the failing statement, `RESUME NEXT` continues after it, `RESUME
<line>` jumps; a handler that runs off the end of the program is `No RESUME`
(21). `RUN`, `NEW`, `CLEAR`, `MAXFILES` and editing a line disarm the handler.
The full rules are on the [`RESUME`](../keywords/RESUME.md) page.

### Which errors can be trapped

In every case measured, an error raised by a running program goes to an armed
handler — syntax, file and disk errors included. Two measured exceptions: an
error inside the handler, before its `RESUME`, stops the program with that
second message; and `ON ERROR GOTO A` (no line number) is a `Syntax error` the
current handler does not catch. A handler armed by a program also catches an
`ERROR 7` typed at the prompt after the program stopped (both references);
other errors typed at the prompt have not been measured.

### Errors at the prompt

A typed statement that fails prints the bare message and sets `ERL` to
65535. `Break` (from Ctrl-STOP or `STOP`), `?Redo from start` and
`?Extra ignored` are messages without an error code.

### The first fault in a statement is the one reported

When one statement goes wrong in two ways, you get the first:
`FOR I=0*(1/0) STEP 2` is `Division by zero`, not `Syntax error`, and
`SCREEN 0*(1/0)` is `Division by zero` without changing the mode. The
references stop at the first fault; zerobas records a fault found inside an
expression and raises it when the statement ends (*How zerobas does it*).

## Example

```
10 ON ERROR GOTO 90
20 A=1/0
30 ERROR 200
40 PRINT "ERR";ERR;"ERL";ERL
50 ON ERROR GOTO 0:X=SQR(-1)
90 PRINT "Error";ERR;"in";ERL
100 RESUME NEXT
RUN
Error 11 in 20
Error 200 in 30
ERR 0 ERL 30
Illegal function call in 50
PRINT 1/0
Division by zero
PRINT ERR;ERL
 11  65535
```

Code 200 has no message but `ERR` still reads 200; line 40 shows `RESUME`
clearing `ERR` and keeping `ERL`; line 50 disarms the handler, so its error
stops the program. The last two commands are typed at the prompt.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_errors.out`](../../scratchpad/kwdoc_errors.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **A few failure paths still print `load error` and carry on** (D-LOADERRRET,
  TIER 3): zerobas's own text, with no code and no trap. The ones left include
  a disk read failing inside `GET` and a failing tape header write; no test
  row reaches them yet.
- **A malformed `ERROR` argument** (D-ERRORARG, TIER 6): the VG-8020 gives
  13, 24, 6 or 2 depending on what is wrong; zerobas gives 5, and runs
  `ERROR 1,1` as `ERROR 1`. See [`ERROR`](../keywords/ERROR.md).
- **`ERROR 60` to `ERROR 64` on the diskless build** print the CF-3300's disk
  messages; the VG-8020 prints `Unprintable error` (D-NODISKERRTXT, TIER 6,
  [`errtext6064_run.out`](../../scratchpad/errtext6064_run.out)). Code 65 is
  held in the same table.

## What we found, and how

- **An untrapped error did not stop a program** (fixed 2026-07-18, with the
  ` in <line>` suffix: [spec-basic-error-handling.md](../spec-basic-error-handling.md));
  syntax errors became trappable on 2026-07-22.
- **Messages were in a lowercase house style**, and fourteen codes had none,
  until 2026-08-02 (D-MSGEXACT, D-MSGSUB). Measuring both machines showed that
  the published message table is wrong about code 17 (`Can't CONTINUE`, not
  `Can't continue`), and that the VG-8020 itself prints 50–59.
- **A fault could vanish at the end of a statement** (fixed 2026-08-09,
  D-STMTPEND): `SCREEN 0*(1/0)` and `FOR I=0*(1/0) TO 3` reported nothing
  ([spec-basic-stmtpend.md](../spec-basic-stmtpend.md)).
- **A line refused by the editor left `ERL` stale** (fixed 2026-08-30,
  D-ERLENTRY); both references read 65535.
- **"`Bad file number` is not trappable" was a confound**: the test typed
  `MAXFILES` between arming the handler and the error, and `MAXFILES` disarms
  it. Measured without that, codes 52 and 59 trap like any other.
- **The disk codes moved into the disk ROM** (2026-09-11, D-DISKERR): an empty
  drive is now `Disk offline` (70), trapped, where zerobas printed `load error`
  and ran on ([spec-basic-diskerr.md](../spec-basic-diskerr.md)).

## How zerobas does it

Every error goes through `raise_error` in
[basic/interp.asm](../../basic/interp.asm): it stores the code in `ERRFLG`,
`record_errline` writes `ERL` (65535 in direct mode), and then, if a handler
is armed and none is active, it resets the stack to the run loop's anchor
(`SAVSTK` — an error can come from any depth), saves the failing statement for
`RESUME` and jumps to the handler as `GOTO` would. Otherwise `fre_abort_low`
in [basic/arrays.asm](../../basic/arrays.asm) prints the message and
`print_in_lineno` the ` in <line>`.

Messages are looked up by code: `err_msgtab` in
[basic/islands.asm](../../basic/islands.asm) covers 1–25, and most of its
entries defer to the sub-ROM's table, `errmsg_tenant` in
[sub/errmsg.asm](../../sub/errmsg.asm), which also holds 50–65. A code it does
not hold is offered to the documented error-print hook `H.ERRP` (`&HFEFD`);
zerobas's disk ROM claims it and prints 66 and 68–70 (`hk_errp` in
[disk/kernel.asm](../../disk/kernel.asm)). Without a disk ROM the answer is
`Unprintable error`.

Faults found inside an expression (an overflow, a division by zero, a type
mismatch) do not unwind mid-expression. `penderr_set` in
[basic/str-engine.asm](../../basic/str-engine.asm) records a code only if none
is recorded yet — so the first fault wins — and the expression carries on with
a defined value. `exec_stmt`, where every statement starts, raises any code
still pending; `record_errline` consumes it, so a trapped error's handler does
not see it again. The end of the statement is too late for a statement with a
visible side effect, so such a statement checks its argument before acting:
`SCREEN` does (D-SCRERR, [spec-basic-screenerr.md](../spec-basic-screenerr.md)).

## Related pages

- Keywords: [`ERROR`](../keywords/ERROR.md), [`ERR`](../keywords/ERR.md),
  [`ERL`](../keywords/ERL.md), [`RESUME`](../keywords/RESUME.md) (with
  `ON ERROR GOTO`), [`ON`](../keywords/ON.md), [`STOP`](../keywords/STOP.md),
  [`CONT`](../keywords/CONT.md).
- Concepts: [interrupts-and-traps.md](interrupts-and-traps.md),
  [screen-editor.md](screen-editor.md), [files-and-devices.md](files-and-devices.md),
  [disk.md](disk.md), [program-text.md](program-text.md).

## Tests that cover it

- `make error-acceptance` — untrapped errors stop, with ` in <line>`.
- `make error-trap-acceptance` — trapping, `ERR`, `ERL`, `RESUME`, nesting.
- `make onerr0-acceptance` — `ON ERROR GOTO 0`, also in direct mode.
- `make msgexact-gate` — every message against both references.
- `make stmtpend-acceptance`, `make penderr-acceptance` — first fault wins.
- `make nodiskerr-acceptance` — `Disk offline` on an empty drive.
- `make unit-test` — includes the sub-ROM message-table bound check.
