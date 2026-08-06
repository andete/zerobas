<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-EDITVERB — `RENUM` / `AUTO` / `LLIST` measured on MSX1 hardware

Black-box characterization of the three editor verbs whose **statement half**
`TODO.md` still carries as open, taken at the prompt on a Philips **VG-8020**
and a National **CF-3300** through `probes/basic/basic_probe_editverb.py`.
Clean-room: typed inputs and observed outputs only, no reference-ROM
disassembly (`CONTRIBUTING.md`).

The fourth verb in the filed item, `DELETE`, is **not** measured here — it
shipped 2026-08-02 with D-DELETE and is characterized in
[`docs/delete-msx1-characterization.md`](delete-msx1-characterization.md). See
§0.

---

## 0. 🔴 The filed item's framing is wrong on its first clause

`TODO.md`'s residual reads *"`AUTO` / `RENUM` / `LLIST` / `DELETE` — the
STATEMENT half. Tokens are byte-exact (D-KWGAP4); **nothing executes them**."*

`DELETE` has executed since 2026-08-02. It has a `stmt_table` row
([`basic/interp.asm`](../basic/interp.asm)), a resident marshalling head
(`ex_delete`, [`basic/program.asm`](../basic/program.asm)), a whole-verb
sub-ROM implementation (`le_delrange`, [`sub/lineedit.asm`](../sub/lineedit.asm))
and 33 gated rows. The tree already said so in two places the index did not
follow — [`basic/sysvars.inc:2002`](../basic/sysvars.inc) (*"THREE OF THE FOUR
are still not dispatched"*) and `delete-range-slice`. The index line is stale,
not the code.

So the measured denominator of this slice is **three** verbs, not four.

⚠️ And the second clause of the same filed item — *"`AUTO` and `LLIST` cannot
be put to a reference in this harness (interactive / unplugged-`LSTOUT` hang)"*,
carried from D-KWGAP4 into `Makefile`'s `lnblank-say-acceptance` header and into
[`docs/kwsweep-msx1-coverage.md`](kwsweep-msx1-coverage.md) §"Not executed" — is
**also wrong**, in a way that costs the project four measured words. §1 is the
refutation.

---

## 1. The apparatus, and the two claims it refutes

### 1.1 `LLIST` — the readout is the PRINTER, not the screen

openMSX's `printerport` connector takes a `logger` pluggable whose
`getStatus()` returns *ready* unconditionally and which flushes **one byte per
strobe edge** to the file named by the `printerlogfilename` setting. So:

* the unplugged-`LSTOUT` hang the filed claim names is real *and irrelevant* —
  the harness plugs a printer, and a plugged printer never blocks;
* the reading is the **byte stream the program sent**, which is strictly better
  than a screen scrape: no 40-column wrap, no scroll-off, no cursor, and CR/LF
  visible as bytes.

Measured on the VG-8020, `LLIST` after `10 REM P / 20 REM Q / 30 REM R`:

```
'10 REM P\r\n20 REM Q\r\n30 REM R\r\n'
```

⇒ **`LLIST` is measurable against both references.** So are `LPRINT`, `LPOS`
and `LFILES`, which `kwsweep-msx1-coverage.md` lists as *"not executed —
printer-bound with the known unplugged-`LSTOUT` hang hazard"*. That reason no
longer holds for any of the four. (Only `LLIST` is in this slice's scope; the
other three are filed — see the spec §7.)

### 1.2 🔴 The zerobas side needs a GREEN CONTROL, and it is not `LPRINT`

`LPRINT` is a **`Syntax error` on zerobas too** — it has no `kwtable.inc` entry
at all. So an empty printer log on the zb side has **two** candidate causes: no
`LLIST`, or no working printer path ([[row-with-two-candidate-causes]]). The
row that separates them drives the sink through a path that already ships:

```
OPEN"LPT:" FOR OUTPUT AS #1 : PRINT#1,"CTL" : CLOSE#1
```

Measured on `C-BIOS_MSX1_EU_REPACK_DISK` at `0b31baa`, log reads `'CTL\r\n'`.

⇒ zerobas's `pchar`→`pch_lpt`→`LPTOUT` path **works today**; every empty
`llt-` reading is therefore attributable to `LLIST` alone. This control is row
`llt-ctl` and it is not decoration: without it the whole battery is
[[readout-blind-to-its-own-subject]] with the blindness on the *zerobas* side.

### 1.3 `AUTO` — the harness CAN drive it

Two independent questions, both answered yes:

* **line entry** — `AUTO`'s prompt loop reads through the ordinary BIOS
  `CHGET` path, which is exactly what the harness's KEYBUF injector feeds. An
  injected `REM A` at an `AUTO` prompt is stored.
* **termination** — Ctrl-STOP is not a character and cannot ride KEYBUF, but it
  *is* a key-matrix combination: row 6 bit 1 (CTRL) + row 7 bit 4 (STOP),
  driven with openMSX `keymatrixdown`/`keymatrixup` — the same primitive the
  input-devices arc's `holds` mechanism already uses. After the release,
  `PRINT 4+5` prints ` 9`, i.e. the machine is back in command mode.

⇒ **`AUTO` is drivable and readable.** The filed *"interactive, so `SIDE_LOCK`
refuses a reference"* is a statement about the KEYBUF injector's alphabet, not
about the harness.

⚠️ The one thing that must NOT be inherited from this: a Ctrl-STOP delivered by
the matrix is only visible to a routine that **scans the matrix**. See spec §3.3
— it is why `AUTO`'s read loop cannot simply block in `CHGET`.

---

## 2. `RENUM` — measured rules

Program used throughout unless stated (deliberately numbered 1..9, because
1..9 → 10..90 is **not** the identity; §2.9 records the round that used
10/20/30 and could not tell any rule from any other):

```
1 GOTO 3        2 PRINT"A"      3 GOSUB 5       4 END      5 RESTORE 6
6 DATA 1        7 ON 1 GOTO 2,4 8 IF 1 THEN 4 ELSE 2       9 RETURN
```

| # | rule | evidence |
|---|---|---|
| **R-RN1** | `RENUM` bare = start **10**, increment **10**, from the FIRST line. | → `10 20 30 40 50 60 70 80 90` |
| **R-RN2** | `RENUM n` sets the new start; increment stays 10. | `RENUM 100` → `100 110 …` |
| **R-RN3** | `RENUM n,m` renumbers **from the old line `m` onward**; lines below `m` keep their numbers. | `RENUM 100,3` → `1 2 100 110 120 130 140 150 160` |
| **R-RN4** | `RENUM n,m,i` sets the increment. | `RENUM 100,3,5` → `1 2 100 105 110 115 120 125 130` |
| **R-RN5** | An **absent new-start is 10**, not 0. | `RENUM ,,5` → `10 15`; `RENUM ,3` → `1 2 10` |
| **R-RN6** | **Every `$0E` line-number reference is rewritten**, wherever it stands — `GOTO`, `GOSUB`, `RESTORE`, `THEN`, `ELSE`, every element of an `ON…GOTO` list, `RUN <n>`, and an `ERL` comparison. | `7 ON 1 GOTO 2,4` → `70 ON 1 GOTO 20,40`; `2 RUN 1` → `20 RUN 10`; `1 ON ERROR GOTO 3` → `10 ON ERROR GOTO 30` |
| **R-RN7** | References in lines that are **not themselves renumbered** are rewritten too. | `RENUM 100,3`: `1 GOTO 3` → `1 GOTO 100` |
| **R-RN8** | A reference to a line that does not exist prints **`Undefined line <target> in <line>`**, using the **OLD** number of the containing line, and **the renumbering still happens**. | `1 GOTO 77` → `Undefined line 77 in 1`, then `LIST` reads `10 GOTO 77` |
| **R-RN9** | **One message per dangling reference**, in program order, including two in the same line. | `1 ON 1 GOTO 77,88` → `Undefined line 77 in 1` + `Undefined line 88 in 1` |
| **R-RN10** | 🔴 A dangling reference is **not an error**: `ERR` stays 0 and `ON ERROR` does not trap it. | `dang-err` → ` 0`; `dang-trap` never reaches its handler |
| **R-RN11** | Increment 0 is **`Illegal function call`** (ERR 5), and nothing is renumbered. | `RENUM 10,,0` |
| **R-RN12** | The new numbering must stay **strictly above** the last line left alone: equal is refused. | `RENUM 20,30` on `10 20 30` → ERR 5; `RENUM 21,30` → `10 20 21` |
| **R-RN13** | A **computed** number past 65529 is ERR 5, program untouched. | `RENUM 65520,,10` on 2 lines |
| **R-RN14** | 🔴 But a **literal** argument past 65529 is **`Syntax error`** (ERR 2), not ERR 5 — a different rule with a different message. | `RENUM 65530` → `Syntax error`; `RENUM 65529` → line becomes 65529 |
| **R-RN15** | More than three arguments is `Syntax error`, nothing renumbered. | `RENUM 10,1,10,7` |
| **R-RN16** | `RENUM` **ends the line and the program**; a `:` tail is accepted and abandoned. | `RENUM:B=9` → `B` reads 0, and the renumbering happened |
| **R-RN17** | 🔴 `RENUM` does **NOT** clear variables and does **NOT** invalidate `CONT`. | `1 A=7 / RUN / RENUM / PRINT A` → ` 7`; `1 STOP / 2 PRINT 5 / RUN / RENUM / CONT` → ` 5` |
| **R-RN18** | `RENUM` on an **empty** program is `Ok`. | |
| **R-RN19** | 🔴 The reference walk is **token-aware**: a `&H`/`&O` constant, a string literal, a `DATA` body and a `REM` body are never rewritten, even when their bytes contain `$0E`. | `1 A=&H0E0E` (stored `$0C $0E $0E`) survives `RENUM` intact and reports **no** undefined line — §2.9 |
| **R-RN20** | `RENUM` works as a **program statement**, not only at the prompt, and renumbers for real. | `1 RENUM / 2 REM B` + `RUN` → `10 RENUM / 20 REM B` |
| **R-RN21** | `.` is accepted as either line-number argument (the shared D-DOTLINE resolver). | `RENUM 100,.` → `Ok` |
| **R-RN22** | `GOTO 0` counts as a dangling reference (line 0 cannot exist). | `Undefined line 0 in 1` |
| **R-RN23** | A self-reference is rewritten to the line's own new number. | `1 GOTO 1` → `10 GOTO 10` |

### 2.9 🔴 Two rounds were measured on cases where the candidate rules COINCIDE

Recorded because both were nearly carried forward as settled — the
[[err21-no-resume-slice]] shape:

* **round 1 renumbered `10 20 30`.** `RENUM` maps that to `10 20 30`. The
  identity agrees with *every* rule anyone could propose, including "RENUM does
  nothing". Re-run at `1 2 3 …`, which separates them.
* **round 3's `CONT` and `renum-prog` rows had the same defect** — `10 STOP /
  20 PRINT 5` and `10 RENUM / 20 REM B` are already at the target numbering.
  R-RN17 and R-RN20 are stated from `1 STOP / 2 PRINT 5` and `1 RENUM /
  2 REM B`, where the lines actually move.
* **and the `&H0E0E` row needed reading twice.** After `RENUM` the listing is
  `10 A=&HE0E`, which *looks* mangled and is not: `&HE0E` is 3598 and so is
  `&H0E0E` — the detokeniser strips the leading zero. The rule is settled not
  by the listing but by the **absence** of an `Undefined line 14 in 1` message,
  which a byte-scanning walk must emit (it would read `$0E`, take the next two
  bytes `$0E $00` as the target 14, and find no line 14).

---

## 3. `AUTO` — measured rules

| # | rule | evidence |
|---|---|---|
| **R-AU1** | `AUTO` bare = start **10**, increment **10**. | prompt `10`, then `20` |
| **R-AU2** | `AUTO n` sets the start; increment stays 10. | `AUTO 55` → `55` |
| **R-AU3** | `AUTO n,i` sets both. | `AUTO 100,5` → `100`, `105`, `110` |
| **R-AU4** | 🔴 With the **comma form**, an absent start is **0**, not 10 — bare `AUTO`'s 10 is a whole-argument-absent rule, not a per-field default. | `AUTO ,7` → prompt `0`, then `7` |
| **R-AU5** | Increment 0 is `Illegal function call`. | `AUTO ,` (both fields absent after the comma) |
| **R-AU6** | The prompt is `<number>` followed by **`*` when a line with that number already exists**, and a space when it does not. The `*` is screen decoration only — the stored line has the ordinary space. | `10 REM OLD` present → `10*`; `LIST` afterwards reads `10 REM X` |
| **R-AU7** | An **empty** entry stores nothing and the prompt advances anyway. | prompt `20`, Enter → prompt `30`; `LIST` reads `10`,`30` |
| **R-AU8** | Ctrl-STOP leaves `AUTO` and returns to command mode, with **no `Ok`** printed. | `PRINT 4+5` next prints ` 9` |
| **R-AU9** | `AUTO` **ends the line and the program**; a `:` tail is accepted and abandoned. | `AUTO 10:B=9` → prompt `10`, `B` reads 0 |
| **R-AU10** | `AUTO` runs as a **program statement** too. | `10 AUTO / 20 REM B` + `RUN` → prompts `10*`, `20*` |

---

## 4. `LLIST` — measured rules

🎯 **The headline is that there is nothing new to measure.** Every shape
`LIST` was characterized on in
[`docs/listrange-msx1-characterization.md`](listrange-msx1-characterization.md)
answers **identically** under `LLIST`, with the output on the printer instead
of the screen.

| # | rule | evidence |
|---|---|---|
| **R-LL1** | `LLIST` = `LIST` to the printer; the whole program, one `<number> <body>CR LF` per line. | `'10 REM P\r\n20 REM Q\r\n30 REM R\r\n'` |
| **R-LL2** | The same range grammar and the same defaults: `LLIST n`, `LLIST n-`, `LLIST -m`, `LLIST n-m`. | `LLIST 20` → one line; `LLIST 20-` → to the end |
| **R-LL3** | No range error of any kind — a reversed range and a range above the program print nothing, ERR 0. | `LLIST 30-20`, `LLIST 99` → empty log, `Ok` |
| **R-LL4** | A comma after the range is `Syntax error` and prints nothing. | `LLIST 10,20` |
| **R-LL5** | `LLIST` ends the line and the program; a `:` tail is accepted and abandoned. | `LLIST:B=9` → log has the line, `B` reads 0 |
| **R-LL6** | 🔴 `LLIST` **restores the screen sink**: the next `PRINT` goes to the screen. | `PRINT "SCR"` after `LLIST` prints on screen and adds nothing to the log |
| **R-LL7** | Nothing of the listing appears on the screen. | screen shows only the echo and `Ok` |

---

## 5. Cross-reference agreement

Every rule above was taken on the **VG-8020**. §2's headline set, `AUTO`'s
prompt/`*`/Ctrl-STOP set and `LLIST`'s whole set were re-asked on the
**CF-3300**; agreement is recorded in the gate itself (`basic_probe_editverb.py`,
three sides) rather than restated here — a rule both references show is a
property of MSX-BASIC, one only the VG-8020 shows is a property of that machine.
