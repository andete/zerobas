<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Error-message TEXT — MSX1 characterization

Measured 2026-08-02 by [`probes/basic/basic_probe_msgexact.py`](../probes/basic/basic_probe_msgexact.py)
on **both** references (`Philips_VG_8020`, `National_CF-3300`) plus the zerobas
repack machine at `4d43294`. Instrument: `ERROR n` in direct mode, read through
`omsx_repl.screen_tail`.

This is a **denominator**, not a gate. It answers "what exactly does an MSX1
print", per machine, verbatim. It does not assert anything about zerobas.

## Why it did not exist before

The tree had a standing policy against comparing message text to the reference.
[`probes/basic/error_acceptance.py:24`](../probes/basic/error_acceptance.py:24)
states it outright:

> Wording stays house-style (we don't copy MSX's verbatim text — so we DON'T
> compare the message string to the reference)

So **the corpus was structurally blind to message wording**. Every error class it
covers agrees *numerically* (`PRINT ERR`); the text was never an observable on
any side. That is the same failure shape as
[[readout-blind-to-its-own-subject]], at corpus scale — and it is why a wrong
message could sit in the tree indefinitely without a single red row.

## 1. The dense range, 1..26

Both references agree on **every** code in this range. `26` is the control: it
must read differently from `25`, or the walk is not tracking the table's end.

| ERR | both references | zerobas @ `4d43294` | |
|----:|---|---|---|
| 1 | `NEXT without FOR` | `next without for` | case |
| 2 | `Syntax error` | `syntax error` | case |
| 3 | `RETURN without GOSUB` | `return without gosub` | case |
| 4 | `Out of DATA` | `out of data` | case |
| 5 | `Illegal function call` | `Illegal function call` | ✅ exact |
| 6 | `Overflow` | `overflow` | case ⚠️ |
| 7 | `Out of memory` | `out of memory` | case |
| 8 | `Undefined line number` | `undefined line` | 🔴 **wording** |
| 9 | `Subscript out of range` | `Subscript out of range` | ✅ exact |
| 10 | `Redimensioned array` | `Redimensioned array` | ✅ exact |
| 11 | `Division by zero` | `division by zero` | case |
| 12 | `Illegal direct` | `unprintable error` | hole |
| 13 | `Type mismatch` | `type mismatch` | case |
| 14 | `Out of string space` | `out of string space` | case |
| 15 | `String too long` | `unprintable error` | hole |
| 16 | `String formula too complex` | `String formula too complex` | ✅ exact |
| 17 | `Can't CONTINUE` | `can't continue` | case 🔴 |
| 18 | `Undefined user function` | `unprintable error` | hole |
| 19 | `Device I/O error` | `unprintable error` | hole |
| 20 | `Verify error` | `unprintable error` | 🎯 hole, but the string EXISTS |
| 21 | `No RESUME` | `no resume` | case |
| 22 | `RESUME without error` | `resume without error` | case |
| 23 | `Unprintable error` | `unprintable error` | case |
| 24 | `Missing operand` | `missing operand` | case |
| 25 | `Line buffer overflow` | `Line buffer overflow` | ✅ exact |
| 26 | `Unprintable error` | `unprintable error` | control — differs from 25 ✅ |

🔴 **ERR 17 is `Can't CONTINUE`, not `Can't continue`.** The table in
[`docs/spec-basic-error-handling.md:199`](spec-basic-error-handling.md:199) —
sourced from the *published* MSX-BASIC language reference, grade B — says
`Can't continue`. It is wrong about the case. **This is the whole argument for
measuring rather than transcribing**: a grade-B source got the one thing wrong
that a capitalisation policy depends on. Four codes carry interior ALL-CAPS
words (`FOR`, `GOSUB`, `DATA`, `CONTINUE`, `RESUME`) and no case rule predicts
which; they have to be read off the machine one at a time.

## 2. The sparse disk range, 50..64

⚠️ **A written-down prediction that the measurement falsified.** The probe was
written expecting the diskless VG-8020 to answer `Unprintable error` across
50..64. It does not: it carries **50..59 in main BASIC** and only falls through
at 60. So the disk-ROM boundary is at **60**, not 50.

| ERR | VG-8020 | CF-3300 | zerobas |
|----:|---|---|---|
| 50 | `FIELD overflow` | `FIELD overflow` | `unprintable error` |
| 51 | `Internal error` | `Internal error` | `unprintable error` |
| 52 | `Bad file number` | `Bad file number` | `bad file number` |
| 53 | `File not found` | `File not found` | `unprintable error` |
| 54 | `File already open` | `File already open` | `unprintable error` |
| 55 | `Input past end` | `Input past end` | `input past end` |
| 56 | `Bad file name` | `Bad file name` | `unprintable error` |
| 57 | `Direct statement in file` | `Direct statement in file` | `unprintable error` |
| 58 | `Sequential I/O only` | `Sequential I/O only` | `sequential i/o only` |
| 59 | `File not OPEN` | `File not OPEN` | `file not open` |
| 60 | `Unprintable error` | `Bad FAT` | `unprintable error` |
| 61 | `Unprintable error` | `Bad file mode` | `bad file mode` |
| 62 | `Unprintable error` | `Bad drive name` | `unprintable error` |
| 63 | `Unprintable error` | `Bad sector number` | `unprintable error` |
| 64 | `Unprintable error` | `File still open` | `unprintable error` |

The 60..64 disagreement is **the reading that proves each machine is being read
on its own terms** — a row where both refs agreed there would be the suspicious
one. `Sequential I/O only` and `File not OPEN` carry interior caps, again
unpredictable from any rule.

## 3. The messages `ERROR n` cannot reach

Not ERR codes, so a code walk is structurally blind to them. Boot-per-case.

| case | both references | zerobas |
|---|---|---|
| `STOP` direct | `Break` | `break` |
| `10 STOP : RUN` | `Break in 10` | `break in 10` |
| `INPUT` bad data | `?Redo from start` | `?redo from start` |
| `INPUT` surplus data | `?Extra ignored` | `?extra ignored` |
| `CLOAD?` mismatch | **`Verify error`** (VG-8020 only) | `Verify error` ✅ exact |

**`Verify error` measured 2026-08-02** on a real `CLOAD?` mismatch (memory holds
`POKE …,&H98`, tape holds `&H99`). zerobas's `err_verify` is **already exact** —
confirmed, not inferred from the string looking right.

⚠️ **VG-8020 only, and the reason is the tape image.** The tokenised CAS carries
absolute line links for `TXTBASE $8001`, the VG-8020's BASIC text base. The
CF-3300 boots Disk BASIC with a higher `TXTTAB`, so the same image does not
describe its memory — running it there would measure the tape format, not the
message. This is the one **single-reference** row in the denominator, and it is
labelled rather than quietly presented as a two-reference lock.

⚠️ **The existing `basic_probe_cas_verify.py` could never have measured this.**
It hardcodes `-machine ZB_MACHINE` (so it only ever reads zerobas) and asserts
`"verify error" in scr.lower()` — **case-insensitively**. The one probe in the
tree that already prints this message is structurally blind to its case. That is
the corpus-wide blindness of §"Why it did not exist before", found inside the
probe that looked most likely to have covered it.

Two rig facts the first two runs got wrong, kept because they are reusable:

* **Type timings are per-machine.** `basic_probe_cas_verify.py` types at 6.0 s on
  the repack machine; on the VG-8020 that is *before the prompt* (`boot=8.0`).
  The program line never appeared and the readout returned a boot banner.
* **`autoruncassettes` must be off, and off BEFORE `-cassetteplayer`.** openMSX
  types `CLOAD`+`RUN` itself on cassette insertion, so the tape was consumed at
  boot and the probe's own `CLOAD?` met a tape at its end. Setting it inside the
  `-script` is **too late** — openMSX processes command-line options in sequence,
  so it has to be a `-command` ahead of the insertion.

The `?Redo from start` reading carries trailing screen junk (INPUT's re-prompt
`?` and the function-key row) — the message is the head of the row, and the
comparison is on that head.

## 4. Region map (from `build/basic-reloc.sym`, clean build at `4d43294`)

Low region `$2812–$3FFF`, page 1 `$4000–$7FFF`. **Almost every message string is
page 1** — which is where the wall is, and also where the carve is.

| low `$2812–$3FFF` | page 1 `$4000–$7FFF` |
|---|---|
| `err_too_complex` `$283C` · `err_out_of_str` `$2857` · `msg_redo` `$307F` · `msg_extra` `$3090` · `err_subscript` `$3D05` · `err_redim` `$3D17` · `err_illegal_fn_arr` `$3D2B` · `err_mem_arr` `$3D2E` · `err_syntax` `$3D37` · `err_no_resume` `$3D93` | `err_type_mismatch` `$425D` · `err_fp_divzero` `$42A6` · `err_illegal_fn` `$42B7` · `err_resume_noerr` `$42BA` · `err_unprintable` `$4377` · `err_line` `$4452` · `err_verify` `$6697` · `brk_msg` `$76BB` · `msg_phrase_tab` `$771D` · `err_cont` `$779C` · `err_mem` `$77F3` · `err_noret` `$7A0E` · `err_nofor` `$7A1C` · `err_data` `$7A5C` · `err_missing_operand` `$7D9F` · `err_input_pastend` `$7F75` · `err_seq_only` `$7F84` · `err_bad_filemode` `$7F98` · `err_linebuf_overflow` `$7FA2` · `err_overflow` `$7FAE` · `err_bad_filenum` `$7FDC` · `err_file_notopen` `$7FE8` |

⚠️ **Doc debt found in passing:** [`basic/main.asm:385`](../basic/main.asm:385)
claims `err_bad_filenum`/`err_file_notopen` are "LOW REGION". The symbol table
says `$7FDC`/`$7FE8` — **page 1**. The comment describes the placement at the
time it was written; the R1 rebalance moved them. Not corrected here (that is a
`basic/` edit), filed.

## 5. What the phrase encoder does and does not constrain

The escapes ([`basic/sysvars.inc:3435`](../basic/sysvars.inc:3435)) deliberately
**exclude the leading letter**, precisely so `"Illegal"`/`"illegal"` and
`"Out of"`/`"out of"` could share a phrase while each message kept its own case:

| esc | phrase |
|---|---|
| `MSGESC_ERROR` | `" error"` |
| `MSGESC_UTOF` | `"ut of "` |
| `MSGESC_ILLFN` | `"llegal function call"` |
| `MSGESC_WITHOUT` | `" without"` |
| `MSGESC_FILE` | `"file "` |

So a leading-letter capitalisation is **byte-neutral**, and the phrase bodies
already carry exactly the case the references use — `" error"` stays lowercase
in `Syntax error`, `" without"` stays lowercase in `RESUME without error`.

Three places where that does **not** hold, i.e. the only text costs:

1. **`MSGESC_FILE` is `"file "`, lowercase.** `Bad file number` / `Bad file mode`
   keep it (the escape is mid-string). `File not OPEN` needs it **leading**, so
   that message loses the escape.
2. **`err_linebuf_overflow` FALLS THROUGH into `err_overflow`** —
   `"Line buffer "` at `$7FA2` followed by `"overflow",0` at `$7FAE`, one 21-byte
   blob serving ERR 25 *and* ERR 6. Exact wants `Overflow` (capital) for 6 and
   `…buffer overflow` (lowercase) for 25. **The shared tail cannot be both.**
3. **ERR 8 is a wording gap, not a case gap** — `undefined line` vs
   `Undefined line number`.

## 6. The ABORT-PATH shapes a direct-mode code walk cannot see

Measured 2026-08-02 for [D-MSGSUB](spec-basic-msgsub.md) §5.2, `--walk subx`,
boot-per-case. §1–§3 are **all direct mode**, so they exercise exactly one of
`fre_abort_low`'s two arms and never the `" in <line>"` suffix, and they never
put a message on screen with `PRDEST` non-zero. These four rows do both.

| row | program | VG-8020 | CF-3300 | zerobas @ `3ffd390` |
|---|---|---|---|---|
| `hole-run` | `10 ERROR 12` : `RUN` | `Illegal direct in 10` | `Illegal direct in 10` | `Unprintable error in 10` |
| `ifc-run` | `10 ERROR 5` : `RUN` | `Illegal function call in 10` | `Illegal function call in 10` | `Illegal function call in 10` ✅ |
| `prd-hole` | `OPEN` a disk file, `PRINT#1,"[";`, then `ERROR 12` | *(no disk ROM)* | `Illegal direct in 30` | `Unprintable error in 30` |
| `prd-ifc` | same with `ERROR 5` | *(no disk ROM)* | `Illegal function call in 30` | `Illegal function call in 30` ✅ |
| `mid-ifc` | `20 PRINT#1,"[";ASC("")` — the error is raised **inside** the `PRINT#` | *(no disk ROM)* | `Illegal function call in 20` | `Illegal function call in 20` ✅ |

🔴 **THIS SECTION FIRST CLAIMED THE `prd-*` PAIR "SETTLES `CHPUT`". IT DOES NOT,
AND D-MSGSUB'S KNIFE K3 IS WHAT SAID SO.** The claim was that those rows raise
their error with `PRDEST` non-zero, so the message reaching the screen proves
`fre_abort_low`'s `ld (PRDEST),a` is what makes `pchar` and `CHPUT` agree. K3
deleted that instruction and **neither row moved**. The reason is that
`PRINT#1,"[";` **restores `PRDEST` when the statement ends**, so the `ERROR n` on
the *next* statement never sees it set. Both rows were green, and green for a
reason unrelated to the one written down — a row that cannot go red is not a
measurement ([[gate-can-be-green-while-measuring-nothing]]).

🎯 **`mid-ifc` is the rig that actually sets `PRDEST`**, and K3 measured it both
ways: with the zero, `Illegal function call in 20` on the screen; **without it,
the screen is EMPTY and the message went into the file.** So the PRDEST zero is
load-bearing and now has a row holding it down — which the corpus did not have
before this slice.

⚠️ **There is no `mid-hole` row, and that is a fact about the language.** The
fourteen sub-hosted codes are reachable only through the `ERROR n` *statement*,
which cannot appear inside a `PRINT#` argument list — so a sub-hosted message
can never be raised with `PRDEST` set at all. For that path the CHPUT question is
**bounded away, not measured**. That is a weaker claim than the one this section
originally made, and the correct one. `prd-hole` is kept because it does measure
something real (an open print channel does not divert a sub-hosted message
either), just not that.

⚠️ The VG-8020 rows are **skipped**, not empty. The probe prints
`<skipped:no-disk>` — a third sentinel beside `<none>` and `<empty>`, because a
row that never ran and a machine that declined to answer are different facts
([[readout-blind-to-its-own-subject]]).
