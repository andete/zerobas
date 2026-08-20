# A filename is an EXPRESSION on the reference and a LITERAL here

D-FNARG, 2026-08-19, on `main`, based on `ec840cf` (D-WALLDATE). Measurement
only — **no ROM change and nothing priced into the tree.** Builds the
denominator the `TODO.md` residual *"`OPEN A$ AS #1` is `Syntax error` here and
`OK` on the CF-3300"* asked for, and scouts the mechanism.

⚠️ **ONE REFERENCE.** Every row is Disk BASIC. A diskless Philips VG-8020 answers
`Syntax error` to all of it and **cannot express the question**; recording that
would manufacture an agreement out of an absent disk controller. Every row rests
on the National CF-3300 alone, and the probe prints
`<NO DISK ON THIS SIDE>` rather than a reading for the VG-8020.

---

## 1. The rule

> **Wherever the reference accepts a filename it accepts a string EXPRESSION.
> zerobas accepts a STRING LITERAL and nothing else.**

The residual had **one row**. It now has fourteen, and the rule is not about
`OPEN`: it holds across every filename-taking verb measured, in every mode.

| row | statement | CF-3300 | zerobas |
|---|---|---|---|
| `f.lit` 🟢 | `OPEN"FA1.DAT"AS #1` | `OK` | `OK` |
| `f.var` | `A$="FA2.DAT"` / `OPEN A$ AS #1` | `OK` | **Syntax error** 🔴 |
| `f.expr` | `OPEN A$+".DAT" AS #1` | `OK` | **Syntax error** 🔴 |
| `f.paren` | `OPEN(A$)AS #1` | `OK` | **Syntax error** 🔴 |
| `f.inlit` 🟢 | `OPEN"FA5.DAT"FOR INPUT AS #1` | `OK` | `OK` |
| `f.invar` | `OPEN A$ FOR INPUT AS #1` | `OK` | **Syntax error** 🔴 |
| `f.outvar` | `OPEN A$ FOR OUTPUT AS #1` | `OK` | **Syntax error** 🔴 |
| `f.appvarx` | `OPEN A$ FOR APPEND AS #1` (file exists) | `OK` | **Syntax error** 🔴 |
| `f.killlit` 🟢 | `KILL"FA9.DAT"` | `OK` | `OK` |
| `f.killvar` | `KILL A$` | `OK` | **Syntax error** 🔴 |
| `f.namelit` 🟢 | `NAME"FAB.DAT"AS"FAC.DAT"` | `OK` | `OK` |
| `f.namevar` | `NAME A$ AS B$` | `OK` | **Syntax error** 🔴 |

**Eight divergent rows, four green controls.** The controls are load-bearing:
without them "zerobas cannot do disk I-O at all" is an equally good reading of
the red column.

🎯 **AND THE EXPRESSION FORMS MATTER MORE THAN THE VARIABLE ONE.** `f.expr`
(`A$+".DAT"`) and `f.paren` (`(A$)`) rule out the cheap fix of "accept a bare
string variable as well as a literal": the reference is evaluating an
expression, not widening a token match.

---

## 2. Predictions, scored

Written into the probe before the run: every `*lit` control `OK` on the CF-3300,
every variable/expression form `OK` there and `Syntax error` here.

**11 of 12 exact.** The miss was `f.appvar`, and it is §3.

---

## 3. 🔴 The miss: `<NO OUTPUT>` is not a value, and it had two candidate causes

`f.appvar` (`OPEN A$ FOR APPEND AS #1`, file **not** created) read
`<NO OUTPUT>` on the CF-3300 — the machine printed nothing at all. That is a
readout anomaly wearing the shape of a reading, and **two things could cause
it**: the variable filename (this battery's subject) or `FOR APPEND` against a
file that does not exist. One row cannot separate them, so two more changed one
variable each:

| row | mode | argument | file | CF-3300 | zerobas |
|---|---|---|---|---|---|
| `f.appvar` | APPEND | variable | missing | `<NO OUTPUT>` | Syntax error |
| **`f.applit`** | APPEND | **literal** | missing | `<NO OUTPUT>` | **`OK`** 🔴 |
| **`f.appvarx`** | APPEND | **variable** | **exists** | `OK` | Syntax error |

✅ **THE MODE IS THE CAUSE, NOT THE ARGUMENT.** `f.applit` uses a literal and
still reads `<NO OUTPUT>`; `f.appvarx` uses a variable and reads `OK`. The §1
rule is intact and `f.appvarx` joins it as an eighth divergent row.

🔴 **AND THE CONTROL FOUND A SECOND DEFECT.** `f.applit` is a **literal**
filename — nothing to do with this battery — and zerobas answers **`OK`** where
the CF-3300 produces no output at all. `OPEN "X" FOR APPEND AS #1` on a
non-existent file diverges, and it is filed separately.

⚠️ **WHAT THE REFERENCE ACTUALLY DOES THERE IS UNMEASURED.** `<NO OUTPUT>` means
this row's readout could not capture it — an error that did not print, a hang, a
prompt that never returned. It is **not** evidence that the reference "errors",
and the residual says so: characterising it needs a screen-tail readout, not a
bracket span ([[read-the-artifact-when-the-screen-cannot-witness]]).

---

## 4. The scout — one mechanism, eleven sites

Not priced, but no longer unexplained. `do_open`
([`basic/files.asm:184`](../basic/files.asm)) opens with:

```
do_open:        call    skip_spaces
                cp      '"'
                jr      nz,oo_synerr        ; filename string required
                inc     hl                  ; HL -> first filename char
                ...
                call    parse_disk_fcb      ; build DISK_FCB_NAME; HL -> closing '"'
```

The filename is never evaluated. It is read **straight out of the program text**
by `parse_disk_fcb`, which walks the characters between the quotes with the
interpreter's own cursor. A literal is not a special case of the reference's
behaviour here — it is the *only* case the parser can express.

🎯 **THAT IS WHY ALL SEVEN VERBS DIVERGE IDENTICALLY.** They are not seven bugs;
they are one mechanism reached from **11 call sites** of `parse_disk_fcb`, each
behind its own `cp '"'` gate, across five files —
`files.asm` (×6: `FILES`, `OPEN`, `KILL`, `NAME` old + new, `LFILES`),
`save.asm` (×2), `cload.asm` (×2), `bload-body.inc` (×1).

🔴 **"IDENTICALLY" WAS REFINED BY MEASUREMENT ON 2026-08-20 — SEE
[`fnarg2-msx1-characterization.md`](fnarg2-msx1-characterization.md).** The
sentence above was written from the source with rows for **three** verbs
(`OPEN`, `KILL`, `NAME`); the other four were predicted. They were then driven,
and the *rule* holds at all seven while the *face* does not: only OPEN/KILL/NAME
RAISE `Syntax error`. `SAVE`/`LOAD`/`BLOAD` reach `load_error`
([`basic/bload.asm:160`](../basic/bload.asm)), which PRINTS a lowercase
`load error` and **returns** — no ERR code, no line number, no trap, and the
program runs on. `FILES` does not refuse a non-quote at all: it reads it as *no
filespec*, lists the whole directory, and derails later on the unconsumed
argument. One rule, three mechanisms
[[a-rule-can-claim-more-than-its-evidence]].

💰 **AND THAT SIZES THE SLICE WITHOUT PRICING IT.** The fix is not "also accept a
variable": it is to evaluate a string expression and hand `parse_disk_fcb` a
*string body* instead of a *text cursor*. That is a second source for a shared
parser plus a staging buffer, at 11 sites — a design question, not an edit.
**Not scouted further and not priced**, and with main page 1 at 22 B it is not
opened here.

---

## 5. Status

Both findings are **DEFERRED in the probe** — measured, printed, never scored —
so `make namspc-acceptance` is unchanged at its shipped tally. A deferred row
that started AGREEING would itself be a finding.
