<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-LPTVERB — `LPRINT` / `LPOS` / `LFILES` measured on MSX1 hardware

Black-box characterization of the three words that remain of the printer
surface, taken at the prompt on a Philips **VG-8020** and a National
**CF-3300** through
[`probes/basic/basic_probe_lptverb.py`](../probes/basic/basic_probe_lptverb.py).
Clean-room: typed inputs and observed outputs only, no reference-ROM
disassembly (`CONTRIBUTING.md`).

Predecessor: [`editverb-msx1-characterization.md`](editverb-msx1-characterization.md)
(D-EDITVERB), whose apparatus this reuses wholesale — the `printerport logger`
readout, the `screen_printer` capture and the boot-per-case discipline.

---

## 0. 🔴 The filed reason covered FOUR words and fell for only THREE

`TODO.md`'s residual, and `kwsweep-msx1-coverage.md` §"Not executed", carried all
four printer words under one reason: *"printer-bound with the known unplugged-
`LSTOUT` hang hazard"*. D-EDITVERB refuted it and implemented `LLIST`. The
residual it filed then said the same refutation covers the remaining three.

**It does not cover `LFILES`.** In
[`probes/basic/basic_probe_kwsweep.py`](../probes/basic/basic_probe_kwsweep.py)
`lfiles` is not in the printer group at all — it sits among the **Disk-BASIC**
words carrying **two** reasons, `NEEDS-DISK` *and* printer-bound. Only the
second one fell. The VG-8020 has no disk ROM, so asking it `LFILES` measures the
absence of a disk interface rather than of a language feature — the identical
trap this project already records for the `MKS$`/`MKD$`/`CVS`/`CVD` family.

⇒ **the side sets are not uniform, and the probe says so out loud** rather than
letting a reader infer it from a silent absence:

| battery | words | sides |
|---|---|---|
| `lpr-`, `scr-` | `LPRINT` | vg8020 + cf3300 + zb |
| `lps-` | `LPOS` | vg8020 + cf3300 + zb |
| `lfl-` | `LFILES` | **cf3300 + zb only** |

⚠️ And `LPOS` is not the same *kind* of change as the other two. `LPRINT` and
`LFILES` re-point an existing sink; `LPOS` reports a **printer column counter
that does not exist anywhere in this tree** — `pch_lpt` calls `LPTOUT` and tracks
nothing. §3.9 is what that counter has to do.

---

## 1. The apparatus, and the four rows that exist only to keep it honest

### 1.1 The readouts

`LPRINT` and `LFILES` are read from the **printer log** (`plug printerport
logger`, whose status is READY unconditionally so nothing can block). The framing
is part of the answer, so CR and LF are rendered visibly and never stripped:
`X\r\n` is the rule and `X` is not.

`LPOS` returns a number, so it is read from the **screen**.

### 1.2 🔴 Four controls, because every battery here has a way to read empty

zerobas lacks all three `kwtable.inc` entries at the baseline, so the subject
rows are *expected* to come back empty. An empty reading has more than one
candidate cause, and each is closed by a row that exercises only shipping code:

| control | reads | what it makes attributable |
|---|---|---|
| `lpr-ctl` | `'CTL\r\n'` on all three sides | the **printer path** works, so an empty log elsewhere is the VERB |
| `lps-ctl` | `'0'` on all three sides | the `PRINT <fn>(0)` **readout** works, so a uniform `Syntax error` is not a dead instrument |
| `lfl-ctlf` | the directory, all sides that have a disk | the **disk fixture** is readable before any `LFILES` row is believed |
| `lfl-ctlp` | `'CTL\r\n'` | the printer path still works **with a disk mounted** |

All four pass on all three sides. Without them the batteries would be
[[readout-blind-to-its-own-subject]] with the blindness on *our* side.

### 1.3 🔴 A printer-log row is structurally blind to half its own rule

D-EDITVERB paid for this: knife K3 scored MISS against `llt-tail` because that
row reads the log, which is byte-identical whether or not the verb ends the line.
"Does the statement continue", "did an error message appear" and "did the output
reach the screen instead" are **screen** facts.

So every printer row whose rule has a screen half has a partner in the `scr-`
battery, named for the row it completes — `scr-lprtail`, `scr-lprsink`,
`scr-lprhash`, and `lfl-noneb`. Three of the four changed what the log alone
would have concluded (§2.9).

### 1.4 The `lps-` battery boots per case, and it is not caution

The printer column is machine state that **survives a case**. Batched,
`lps-init` — "a fresh printer head is at column 0" — would read whatever column
the previous case's `LPRINT` left behind, and would read it identically on every
repeat, because openMSX is deterministic. That is exactly the shape D-EDITVERB
found on `AUTO`: a batched case measuring the one before it, producing a
plausible reading of the wrong thing that `--repeat` cannot catch.

⚠️ `run_cases(batch=False)` **ignores `reset`** (its own docstring says so), so
every boot-per-case battery carries the side's reset inside the case. The
CF-3300's is not cosmetic: the leading `""` answers its boot date prompt and
`SCREEN 0` selects the 40-column mode this scrape reads.

---

## 2. `LPRINT` — measured rules

Both references answered **identically on all 16 rows**.

| # | rule | evidence |
|---|---|---|
| **R-LP1** | `LPRINT` sends its output to the printer, CR/LF terminated. | `LPRINT"X"` → `X\r\n` |
| **R-LP2** | The number format is `PRINT`'s exactly: leading sign space, trailing space. | `LPRINT 5` → `' 5 \r\n'` |
| **R-LP3** | Negative numbers take `-` in the sign position, trailing space kept. | `LPRINT -5` → `'-5 \r\n'` |
| **R-LP4** | `;` joins items with no spacing. | `LPRINT"A";"B"` → `AB\r\n` |
| **R-LP5** | `,` advances to the next **14-column** zone — the same zones `PRINT` uses. | `LPRINT"A","B"` → `'A' + 13 spaces + 'B'` |
| **R-LP6** | A trailing `;` suppresses the statement's newline — but see **R-LP16**, which is why the log still ends `\r\n`. | `LPRINT"A";` → `A\r\n` in the log, and `LPOS` reads 3 mid-line |
| **R-LP7** | A bare `LPRINT` prints an empty line. | `LPRINT` → `\r\n` |
| **R-LP8** | Two `LPRINT`s in one line both reach the printer. | `LPRINT"A":LPRINT"B"` → `A\r\nB\r\n` |
| **R-LP9** | 🔴 `LPRINT` does **NOT** end the line or the program — unlike `LLIST`. The statement after it runs. | `LPRINT"A":B=9` → log `A\r\n`, and `PRINT B` reads **9** (`scr-lprtail`) |
| **R-LP10** | 🔴 The **screen** sink is restored for the next statement. | `LPRINT"A":PRINT"SCR"` → log holds only `A\r\n`, and `SCR` is on the **screen** (`scr-lprsink`) |
| **R-LP11** | `LPRINT USING` works and formats as `PRINT USING` does. | `LPRINT USING"##";5` → `' 5\r\n'` |
| **R-LP12** | `TAB(n)` pads to column n. | `LPRINT TAB(5);"A"` → 5 spaces then `A` |
| **R-LP13** | `SPC(n)` emits n spaces. | `LPRINT SPC(3);"A"` → 3 spaces then `A` |
| **R-LP14** | 🔴 `LPRINT` takes **no `#channel`** — that is a `Syntax error`, and nothing is printed. | `LPRINT#1,"A"` → empty log **and** `Syntax error` on screen (`scr-lprhash`) |
| **R-LP15** | `LPRINT` runs as a program statement. | `10 LPRINT"P"` + `RUN` → `P\r\n` |
| **R-LP16** | 🎯 **A partial printer line is FLUSHED on the return to command level.** Within the line the head stays put; by the time control reaches the prompt, a CR/LF has been sent. | §2.9 |

### 2.9 🔴 Two readings looked contradictory, and the row that settled it was a THIRD one

`lpr-trsemi` (`LPRINT"A";`) came back with a **trailing `\r\n`** in the log, which
says the newline was not suppressed. `lps-after`
(`LPRINT"ABC";:PRINT LPOS(0)`) read **3**, which says it *was* — no CR/LF had been
sent at that point in the same line.

Both readings are real, so the CR/LF must arrive **later than the statement**.
The row that separates the two candidate explanations asks `LPOS` from a
**separate command**:

* `lps-after` — `LPRINT"ABC";` and `PRINT LPOS(0)` **on one line** → **3**
* `scr-lposflush` — `LPRINT"A";` then `PRINT LPOS(0)` **as the next command** → **0**

⇒ **R-LP16**: BASIC flushes a partial printer line when it returns to command
level. Neither of the first two rows could have established that, and read alone
either one implies a false rule about `;`.

---

## 3. `LPOS` — measured rules

Both references answered **identically on all 10 rows**, and every row is guarded
with `L=7` for the reason in §6.

| # | rule | evidence |
|---|---|---|
| **R-LS1** | `LPOS(n)` is the printer head's **column**, and it is **0** on a fresh head. | `lps-init` → `0` |
| **R-LS2** | It advances by the characters actually sent. | `LPRINT"ABC";:PRINT LPOS(0)` → **3** |
| **R-LS3** | A completed `LPRINT` (one that sent CR/LF) leaves it at **0**. | `LPRINT"ABC":PRINT LPOS(0)` → **0** |
| **R-LS4** | 🔴 The argument is a **DUMMY**: every value answers the same, and there is **no domain check** — not even for a negative or an out-of-byte value. | `LPOS(1)`, `LPOS(255)`, `LPOS(-1)`, `LPOS(300)` → `0`, `0`, `0`, `0` |
| **R-LS5** | 🔴 The parentheses are **required**; `LPOS` bare is a `Syntax error`. | `PRINT LPOS` → `Syntax error` |
| **R-LS6** | `TAB(n)` moves the counter, so it tracks padding and not just literal bytes. | `LPRINT TAB(10);:PRINT LPOS(0)` → **10** |
| **R-LS7** | It tracks a multi-character write into two digits. | `LPRINT"01234567890123";:PRINT LPOS(0)` → **14** |

### 3.4 ➕ R-LS4's fourth value, added 2026-08-07 by D-DSKMSG

🔴 **THE RULE CLAIMED MORE THAN ITS EVIDENCE COVERED, FOR A DAY.** R-LS4 says
"not even for a negative or an **out-of-byte** value", and its three values were
`1`, `255`, `-1`. **255 is IN byte range.** So the out-of-byte half of the claim
rested on a case that cannot separate it from a byte-legal one, and the only row
that could have caught a byte-domain check was `lps-argneg` — one row, whose
`$FFFF` a `ld a,d / or a` test trips for the *negative* reason.

`lps-argover` (`LPOS(300)`: int16, positive, outside 0..255) closes it. Measured
**before** the knives, on both references, and both answer **`0`** — R-LS4 stands
as written, now with evidence for each clause. See
[`spec-basic-dskmsg.md`](spec-basic-dskmsg.md) §2; the pair
`lps-argneg`+`lps-argover` is what knife K-LS4b reddens while `lps-arg1`/
`lps-argbig` survive, which is the falsification D-LPTVERB §6.7.3 could not run.

⚠️ **R-LS2 and R-LS3 are only readable on ONE line.** Asked as a separate
command, every one of them reads `0` — the command-level flush of **R-LP16** has
already reset the counter. §3.9 is what that cost.

### 3.9 🔴 A row that fixed its own apparatus bug and silently changed subject

`lps-multi` took three attempts, and the middle one is the instructive failure:

1. one line with a 40-character payload → 43 characters typed, the prompt echo
   **wraps** at 40 columns, the anchor is never found, and both references read
   `<NO ECHO>` (the echo-wrap trap, [[clearpool-slice]] — visible only because
   that sentinel is kept distinct from `<nothing>`);
2. split into **separate commands** → the wrap was fixed and the measurement
   broke. Both references then read **0**, because a separate command is a return
   to command level and R-LP16 flushes there. **The row still looked healthy** — a
   number, agreed on both references — while measuring the flush that
   `scr-lposflush` already measures, not the counter it is named for;
3. one line, 14-character payload → 37 characters, nothing wraps, and the counter
   is read before any flush.

⇒ the same shape as [[correct-claim-can-be-the-wrong-question]]: step 2 produced a
true, reproducible, cross-reference-agreeing reading **of the wrong thing**. It
was caught only because the expected value (20, then 14) was written down before
the run and the row answered 0.

### 3.10 What the counter has to do, for the implementation

R-LS1..R-LS7 and R-LP16 together specify state that **does not exist in this
tree**: `pch_lpt` calls `LPTOUT` and tracks nothing. A counter has to be

* **incremented per byte actually sent to the printer sink** (R-LS2), including
  bytes emitted by `TAB`/`SPC` padding (R-LS6) — i.e. in `pch_lpt`, not in the
  `LPRINT` statement head;
* **zeroed when a CR/LF is sent** (R-LS3);
* **zeroed on the return to command level when it is non-zero** (R-LP16) — and
  that flush must emit the CR/LF too, since the log shows it;
* readable by a **function** entry with a parsed-and-discarded argument (R-LS4)
  that still requires its parentheses (R-LS5).

---

## 4. `LFILES` — measured rules

Measured on the **CF-3300 only** (§0), against `disk/test720.dsk`, whose
directory is `TEST.BIN`, `HI.TXT`, `PROG.BIN`, `PROG.BAS`, `PROG2.BAS`.
**Eight rows** — R-LF1..R-LF5 taken by D-LPTVERB (2026-08-06), R-LF6 added by
D-LFILES (§4.1).

| # | rule | evidence |
|---|---|---|
| **R-LF1** | 🎯 `LFILES` is **not** `FILES` with the sink moved. The screen form packs **three entries per row**; the printer form is **one entry per line**, each `NAME    .EXT ` followed by CR/LF. | `FILES` → `'TEST    .BIN HI      .TXT PROG    .BIN / PROG    .BAS PROG2   .BAS'`; `LFILES` → `'TEST    .BIN \r\nHI      .TXT \r\n…'` |
| **R-LF2** | The entry itself keeps the 8.3 layout and a **trailing space** after the extension. 🔴 **WIDENED 2026-09-12 (D-DFEND): the trailing space is on the SCREEN too**, where this tree had it as a separator emitted BEFORE the next field. Row by row the two are identical; they differ only in where the cursor RESTS, which is the one place a 40-column scrape reads them apart. | `'PROG    .BAS \r\n'`; screen `POS(0)` = 19 after `FILES"PROG.BIN"`, 31 after a bare listing, on both machines |
| **R-LF3** | A filespec argument filters, with wildcards. | `LFILES"*.BAS"` → `PROG.BAS` and `PROG2.BAS` only |
| **R-LF4** | 🔴 No match prints **nothing to the printer** and `File not found` **to the screen**. | `LFILES"NOSUCH.XXX"` → empty log (`lfl-none`) + `File not found` (`lfl-noneb`) |
| **R-LF5** | The screen sink is restored for the next statement. | `LFILES:PRINT"SCR"` → the log holds the listing only |
| **R-LF6** | 🔴 **`FILES` says `File not found` too**, so the message belongs to the shared directory walk and not to the printer verb. | `FILES"NOSUCH.XXX"` → `File not found` (`lfl-nonef`) |
| **R-LF7** | 🔴 **An EMPTY directory is the SAME disposition as a filespec that matched nothing** — a *bare* `FILES`/`LFILES` over a mounted, writable volume holding no files raises `File not found`, on the screen, with the printer log empty. | `FILES` → `File not found` (`lfl-emptyf`); `LFILES` → empty log (`lfl-emptyp`) + `File not found` (`lfl-emptypb`); control `lfl-emptyctl` → `CTL     .BAS` |

### 4.1 R-LF6 was added by D-LFILES, and it was added BEFORE the design chose

R-LF6 is the only rule in this document taken after the implementing slice
started, and the reason is worth keeping: R-LF4 is a rule about `LFILES`, but the
cheapest place to implement it is the directory walk **`FILES` also runs** — so
the change would land on a verb this battery did not measure. A change to an
unmeasured verb is a change made blind.

So `lfl-nonef` was written as a **fork with two named dispositions** before the
reading was taken ([`spec-basic-lfiles.md`](spec-basic-lfiles.md) §2.2): a
`File not found` answer puts the message in the shared walk; a silent answer puts
it behind the `LFILES` op alone and leaves `FILES` silent. The reference answered
**`File not found`**, and zerobas answered **nothing at all** — so this is not
only a design input but a previously unmeasured divergence in a verb that has
shipped since Phase 2.

⚠️ It also puts a caveat on `lfl-none`, the one `LFILES` row that **already
agreed** at the D-LPTVERB baseline: an empty printer log is what a machine with no
`LFILES` prints for every input. It agreed for the wrong reason, exactly the class
[[kwsweep-msx1-denominator]] records, and only `lfl-noneb`/`lfl-nonef` separate the
two readings.

### 4.2 ➕ R-LF7 was added 2026-08-07 by D-DSKMSG, and it needed a SECOND fixture

R-LF4 and R-LF6 were both taken **with a pattern**, so neither says anything
about a disk with no files on it at all. [`spec-basic-lfiles.md`](spec-basic-lfiles.md)
§2.4 said so and left that arm alone; its knife K7 then predicted the miss
**before** the run. This is the arm, and closing it needed
`tools/make_test_dsk.py --empty` — the same geometry with an empty root
directory.

🔴 **THE ROW IS IN THE CLASS THAT PASSES A DEAD SUBJECT.** "The listing printed
nothing" is what an unmounted drive, an all-$00 disk ROM and an empty directory
all produce ([[gate-whose-answer-is-an-error-passes-a-dead-subject]] — 8/8 on a
dead disk ROM), and `lfl-ctlf` does **not** close it because it mounts the other
image. `lfl-emptyctl` is the control on *this* image: it `SAVE`s a program to the
empty volume and lists the result, so the row asserts the positive text
`CTL     .BAS` and a machine that could not mount or write cannot satisfy it. It
passes on **both** sides, which is what licenses reading the other three rows.

⚠️ And `lfl-emptyp` is the second instance of the blindness §4.1 records for
`lfl-none`: the printer log is empty on the reference **and** on the pre-fix
zerobas, because R-LF4's message resolves through `raise_error` to the SCREEN and
not through the listing's sink. `lfl-emptypb` is the row that can see it.

🔴 **R-LF1 is the rule that costs bytes.** `ex_files`
([`basic/files.asm`](../basic/files.asm)) is main-ROM and packs three columns; a
sink re-point alone would produce the screen layout on the printer and pass every
row of a battery that only checked *which device* received the bytes. This
battery reads the bytes, so it cannot.

---

## 5. Cross-reference agreement

Every `LPRINT`, `LPOS` and `scr-` rule above was taken on **both** references and
agreed on every row. `LFILES` was taken on the CF-3300 alone, for the structural
reason in §0 — a one-sided reading, stated as one-sided in the probe's own
output.

## 6. The zerobas baseline, before any implementation

All four controls pass; every subject row is absent. Two absences are **not**
plain errors and both matter:

* 🔴 **`LPOS(0)` does not fail on zerobas — it answers.** `POS` is a keyword, so
  with no `LPOS` entry the sequence crunches as the **variable `L`** followed by
  the **function `POS(0)`**, and `PRINT LPOS(0)` prints two numbers (`0  3`
  measured). `PRINT LPOS` prints one and then raises. This is the D-KWGAP4
  accidental-parse class: a word with no token still parses as *something*.
* ⚠️ **And the default value of `L` is 0, which is what the references print.**
  The unguarded `lps-init` row therefore had a reference answer of `0` and an
  accidental-parse answer whose *leading* number was also `0` — so any
  normalisation that dropped the second number would have scored AGREE on a
  machine with no `LPOS` at all. Every `lps-` row is now guarded with `L=7`,
  which makes the two parses disjoint by construction. Same family as the `TAB(`
  row `kwsweep-msx1-coverage.md` keeps deliberately weak, and
  [[kwsweep-msx1-denominator]]'s rule that a case which agrees can agree for the
  wrong reason.

## 7. Measured NOT to be measured

* **The printer's own width wrap.** `lps-wide` writes 20 characters and reads
  20. A payload long enough to reach a printer's right margin cannot be typed
  into a 40-column echo readout (the first two attempts read `<NO ECHO>` on both
  references — the echo-wrap trap). What `LPOS` does at the margin is **not
  claimed**.
* **`WIDTH LPRINT`** — untouched here; no row asks it.
* **`LPOS`'s number FORMAT.** The screen scrape strips the left margin, which
  discards the sign space, so this battery states LPOS's **value** and not its
  rendering.
* **`LFILES` on a second reference.** Structural (§0), not an omission.
