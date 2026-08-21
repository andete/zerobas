<!-- Copyright (c) 2026 Joost Yervante Damad -- SPDX-License-Identifier: 0BSD -->

# D-FNARG2 — the four filename verbs D-FNARG's rule claimed and never drove

Measured 2026-08-20, two sides (National CF-3300, zerobas
`C-BIOS_MSX1_EU_REPACK_DISK`). A diskless VG-8020 cannot express the question
and is recorded `<NO DISK ON THIS SIDE>` rather than scored.

Apparatus: eight new `f.*` rows in
[`probes/basic/basic_probe_namspc.py`](../probes/basic/basic_probe_namspc.py),
DEFERRED like D-FNARG's fourteen. `make namspc-acceptance` unchanged at
**58/58**, deferred rows **14 → 22**. No ROM byte.

---

## 1. Why

[`fnarg-msx1-characterization.md`](fnarg-msx1-characterization.md) §4 concluded:

> 🎯 **THAT IS WHY ALL SEVEN VERBS DIVERGE IDENTICALLY.** They are not seven
> bugs; they are one mechanism reached from **11 call sites** of
> `parse_disk_fcb` […]

Its rows drove **three** verbs: `OPEN`, `KILL`, `NAME`. `SAVE`, `LOAD`, `BLOAD`,
`FILES` and `LFILES` were predicted by reading the source and never measured —
a rule claiming more than its evidence
[[a-rule-can-claim-more-than-its-evidence]]. This is the measurement.

---

## 2. The rows

| row | program | CF-3300 | zerobas |
|---|---|---|---|
| `f.savelit` 🟢 | `10 SAVE"FC1.DAT"` / `20 PRINT"[OK]"` | `OK` | `OK` |
| `f.savevar` | `10 A$="FC2.DAT"` / `20 SAVE A$` / … | `OK` | **`load error`** |
| `f.loadlit` 🔴 | `10 LOAD"FCZ.DAT"` (missing) / … | **`File not found in 20`** | **`load error`** |
| `f.loadvar` | `10 A$="FCZ.DAT"` / `20 LOAD A$` / … | `File not found in 20` | `load error` |
| `f.bloadlit` 🔴 | `10 BLOAD"FCY.BIN"` (missing) / … | **`File not found in 20`** | **`load error`** |
| `f.bloadvar` | `10 A$="FCY.BIN"` / `20 BLOAD A$` / … | `File not found in 20` | `load error` |
| `f.fileslit` 🟢 | `10 FILES"FC*.*"` (no match) / … | `File not found in 20` | `File not found in 20` |
| `f.filesvar` | `10 A$="FC*.*"` / `20 FILES A$` / … | `File not found in 20` | **`Syntax error in 20`** |

`LFILES` is **not measured and that is not an omission**: it writes to the
PRINTER, so no screen readout can see it. It is the 11th `parse_disk_fcb` site
and stays predicted.

---

## 3. 🔴 The instrument was blind first, and it read six rows wrong

Round 1 read `OK` for **six of the eight** zerobas rows. Every one was the
readout lying. The screen said:

```
ZBRUN
load error
[OK]
```

`bracket()` looks for `[` **before** it looks for an error, which is right for a
row whose subject is a VALUE and wrong for a row whose subject is a FAILURE —
and zerobas's failure path *prints and returns*, so the `[OK]` lands underneath
the message. This is the readout blind to its own subject that the probe's own
docstring warns about [[readout-blind-to-its-own-subject]], walked into anyway.

Fixed with a separate `errface()` — error-first, bracket second — rather than by
reordering `bracket()`, because 58 scored rows depend on that order and none of
them is under test here. `load error`, `File not found`, `Device I/O error`,
`Disk offline` and `Bad file name` were added to `ERRORS`; before that a real
error fell through to `<NO OUTPUT>`, i.e. read as a silence.

⚠️ **Adding a name to a classifier can change a SHIPPED row's reading**, so the
full gate was re-run rather than just the new rows: **58/58, unchanged.** That
is a measurement, not an assumption.

Round-2 predictions, written into the probe before the run: **8 of 8 exact.**

---

## 4. What the rows actually establish

### 4.1 ✅ The argument rule holds at all four verbs — on the REFERENCE side

`SAVE A$` is `OK` on the CF-3300; `LOAD A$` and `BLOAD A$` reach the file
system and answer `File not found`, the same as their literals; `FILES A$`
evaluates the pattern and answers `File not found`. So *wherever the reference
accepts a filename it accepts a string expression* extends cleanly from three
verbs to seven.

### 4.2 🔴 But "diverge IDENTICALLY" is wrong: one rule, THREE mechanisms

| verbs | non-literal argument reaches | face | raised? |
|---|---|---|---|
| `OPEN` `KILL` `NAME` | `cp '"'` → `stmt_error` | `Syntax error` | **yes** |
| `SAVE` `LOAD` `BLOAD` | `cp '"'` → `load_error` | **`load error`** | **no** |
| `FILES` | `cp '"'` → `df_nofilespec` | `Syntax error` | yes, but *later* |

`load_error` ([`basic/bload.asm:207`](../basic/bload.asm:207)) is `TAPIOF`, an
`ERRMARK` byte, `print_msg`, **`ret`**. It is not an error: no ERR code, no line
number, no `ON ERROR` trap, and **the program runs on** — `[OK]` prints
underneath it. That is the same class as the `ex_let_arr_str` swallow D-ARYOOS
closed the same day, in a different verb family.

🎯 **AND `FILES` AGREES WITH THE RULE BY COINCIDENCE OF FACE, NOT OF
MECHANISM.** A non-quote is not refused there — it is read as *"no filespec"*,
so zerobas **lists the entire directory** and only then derails on the
unconsumed `A$`:

```
ZB20 FILES A$
TEST    .BIN HI      .TXT PROG    .BIN
PROG    .BAS PROG2   .BAS
Syntax error in 20
```

where the CF-3300 prints nothing and answers `File not found in 20`. The error
matches; the side effect is a whole divergence of its own, and no row scores it.

### 4.3 🔴 The literal controls found a second defect — again

`f.loadlit` and `f.bloadlit` use a **literal** filename. Nothing to do with this
battery, and they diverge: `LOAD"FCZ.DAT"` / `BLOAD"FCY.BIN"` on a file that
does not exist is `File not found in 20` on the CF-3300 — raised, trappable,
execution stops — and `load error` + carry on here.

This is the second time a literal control in this probe has found a defect the
battery was not looking for; D-FNARG's `f.applit` was the first. 🎯 **A CONTROL
IS NOT OVERHEAD.**

⚠️ **THIS IS THE READING AN EARLIER SLICE SAID WAS MISSING.** D-DSKMSG §4.2 and
D-DKNAME §3.4/§6.5 both stop at the same place — *"changing what zerobas prints
there … needs a reading, and that reading opens the whole `load error` wording
divergence for `LOAD`/`RUN`/`BLOAD`/`OPEN`/`APPEND`/`MERGE` — six verbs nothing
has measured."* Two of those six now have one. 🔴 **And that sentence lives only
inside a `- [x]` item**, so the class had no open pickup entry at all; it now
does.

---

## 5. Status — ✅ ALL EIGHT ROWS CLOSED, 2026-08-21 (D-FNEXPR2)

[`spec-basic-fnexpr2.md`](spec-basic-fnexpr2.md). All eight are ordinary scored
rows now, and `f.filesvarl` (§4.2's side effect) with them:
`namspc-acceptance` **95/95**, deferred 5.

🔴 **AND §4.2's TITLE — "one rule, THREE mechanisms" — WAS TRUE WHEN WRITTEN AND
HAD STOPPED BEING TRUE BY THE TIME IT WAS PICKED UP.** Re-read at `cffb34d`
before any edit, `f.loadlit` and `f.bloadlit` BOTH answered `File not found` on
both sides: D-LOADERR-FIX (2026-08-20) and D-BLNF (2026-08-21) had retired the
PRINTED `load error` at `LOAD` and `BLOAD` as a side effect of other slices. So
the "different mechanism" half of the residual had already closed itself, and
what remained at all four verbs was the ARGUMENT SHAPE — D-FNARG's own rule.
**A deferred row is a denominator only while somebody re-reads it.**

🎯 **§4.2's OTHER CLAIM SURVIVED AND GOT SHARPER.** The three faces really were
three, and the reference has ONE: `OPEN 5` / `KILL 5` / `SAVE 5` / `LOAD 5` /
`BLOAD 5` / `FILES 5` are all `Type mismatch` on the CF-3300 (D-FNEXPR2 §2). The
convergence is a READING now, not the assumption it would have been had the fix
simply pointed all three gates at one label.

🔴 **AND §4.3's "the literal controls found a second defect — again" IS WHY THE
FIRST HALF CLOSED WITHOUT THIS DOC NOTICING.** `f.loadlit`/`f.bloadlit` were
that second defect; they were fixed elsewhere and nothing came back to score
them. *A control is not overhead* — and a control that has gone green is a
finding too.

**The original status, for the record:** all eight rows DEFERRED; two residuals
filed in `TODO.md` (the `load error` non-raise with the four remaining verbs
named, and the `FILES` full-listing side effect); not priced, with the note that
the argument-shape fix and the `load error` fix *"should not be assumed to share
a slice."* They did not: D-FNEXPR took the raising three, D-FNEXPR2 the rest —
and the second half turned out to be the same question as the first, plus a face
that had to be measured before it could be chosen.
