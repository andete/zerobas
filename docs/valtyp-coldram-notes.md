<!-- Copyright (c) 2026 Joost Yervante Damad -- SPDX-License-Identifier: 0BSD -->

# D-VALTYP — `VALTYP` reads `$FF` cold because RAM does, and three comments say otherwise

Measured 2026-08-21 at `840599e`. **Zero ROM bytes**: what this slice changes is
three comments, two dated records and one filed price.

---

## 1. The filed item asked about one byte; the window answered a different question

`VALTYP $E0C8` has been read three times (2026-08-01 D-REHOME, 08-09, 08-20) and
each time as **one byte**, each time `$FF` — neither of its two documented values
(`0` numeric / `1` string). The obvious next question is *what writes it*, and
`grep` says only one site does (`basic/strvar.asm`'s `str_eval_ok`, which writes
`1`). So it was read as a **window** instead, on a machine whose only program
line is `REM`, `capture=("mem_abs", …)`:

```
$E0C0  zeros= 3/32  ff=18/32      $F000  zeros= 1/32  ff=30/32
$E080  zeros= 0/32  ff=32/32      $F040  zeros= 0/32  ff=32/32
$E100  zeros= 0/32  ff=31/32      $F060  zeros= 1/32  ff=31/32
$E180  zeros= 0/32  ff=32/32      $F400  zeros=32/32  ff= 0/32
$E300  zeros= 0/32  ff=31/32      $F500  zeros=32/32  ff= 0/32
$E800  zeros= 0/32  ff=31/32      $F6A0  zeros=31/32  ff= 0/32
$D000  zeros= 0/32  ff=31/32      $F700  zeros=32/32  ff= 0/32
```

Byte for byte across `$E0C0`: `NUMBUF` (`$E0C0..C7`) `ff`×8 — nothing has printed
a number yet. `VALTYP` `ff`. `STRPTR` `ff ff`. And then `PRDEST 00`, `PRDEV 00`,
`CONTVALID 00` — **every cell an init writes reads 0; every cell nothing writes
reads `$FF`.**

🎯 **So `$FF` AT `VALTYP` IS NOT A WRITE. IT IS POWER-ON RAM**, and power-on RAM
on this machine is `$FF`. The item's implicit hypothesis — *something is writing
a third value* — is refuted, which retires the interesting half of it.

---

## 2. 🔴 And that refutes a sentence standing in three places

`basic/interp.asm`'s cold-only hook justifies three of its stores like this:

> *"On real hardware power-on RAM is garbage, so this explicit zero is
> load-bearing (**openMSX zero-fills RAM**, hiding the omission)."* — ERRFLG
>
> *"**openMSX zero-fills RAM**, so — exactly like `ld (DOT),hl` below — NO
> emulator row can see this store: knife K-SP4 predicts ZERO red rows."* — FPERR
>
> *"**openMSX zero-fills RAM**, so no emulator row can see this store; spec §7 K6
> predicts ZERO red rows."* — DOT

§1 shows RAM that nothing zero-filled. The three cells are not in one
neighbourhood, and reading their addresses is what separates the true half from
the false one:

| cell | address | its window | so the cold store is… |
|---|---|---|---|
| `ERRFLG` | `$F414` | **all 00** | genuinely invisible here |
| `DOT` | `$F6B5` | **31/32 00** | genuinely invisible here |
| `FPERR` | **`$F069`** | **31/32 `$FF` — and `$F069` is the ONE zero** | **the only reason that byte is 0** |
| `VALTYP` | `$E0C8` | 18/32 `$FF`, and it is one of them | never written at all |

`$F400`+ is the **standard MSX system-variable area**, which the BIOS clears
before BASIC runs. `$F069` and everything below it is not. **The mechanism is not
the emulator; it is C-BIOS's own workspace init, and it does not reach either
`FPERR` or zerobas's private `$E0xx` block.**

⚠️ ONE MEASUREMENT REFUTES THE SENTENCE, NOT THE VERDICTS. A window reading is
evidence about the cells it read. Whether a particular store is *observable* is a
claim about a **gate**, so it was knifed.

---

## 3. K-VT1 — the store IS observable, and a 62-row battery cannot see it

Cut: `ld (FPERR),a` in the cold hook → `ld (ONEFLG),a`, a duplicate of the store
four lines below (same `A`, same value). A **value** cut: the instruction still
exists, `make deadcode` still builds, and `FPERR` is left as power-on RAM.

| | baseline | K-VT1 | restored |
|---|---|---|---|
| ROM id (main) | `670b8d4a` | `34c7e24f` | `670b8d4a` |
| `$F060..$F06F` | `…ff **00** ff…` | **all `ff`** | `…ff **00** ff…` |
| `10 PRINT"[OK]" : 20 PRINT"[TWO]" : RUN` | `[OK] \| [TWO]` | **`Unprintable error in 10`** | `[OK] \| [TWO]` |
| `clearpool-acceptance` | 62/62 ALL PASS | **62/62 ALL PASS** | 62/62 ALL PASS |

🔴 **THE MACHINE CANNOT RUN A TWO-LINE PROGRAM AND THE BATTERY IS FULLY GREEN.**
`FPERR = $FF` is an error code no message table has, so `exec_stmt` — which reads
the pending cell first since D-STMTPEND — raises `Unprintable error` out of the
program's very first statement.

⚠️ **THE FIRST DRAFT OF THIS KNIFE MATCHED TWO SITES AND THE RUNNER REFUSED IT**
rather than cutting whichever came first (`ld (FPERR),a` is also at
`interp.asm:1051`). Same assertion that split D-LOADERR's K-LE2; it has now
earned its keep twice.

---

## 4. 🔴 K-SP4's recorded "predicted miss" is a green for a reason nobody wrote down

`docs/stmtpend-msx1-characterization.md` records K-SP4 — *the cold-boot zero* —
as **"0 — a PREDICTED MISS, 0 moved, hashes confirmed changed"**, and explains it
with the sentence §2 just refuted. The cut is real (§3 moved the ROM and broke
the machine). So the 0 is not evidence that the store is unobservable; it is
evidence about **what the batteries type before their first scored row**.

Re-run under K-VT1, `stmtpend-acceptance` — **K-SP4's own battery** — is
**58/58, all agree**, on the very build whose `10 PRINT"[OK]"` answers
`Unprintable error in 10`. The zero is real and it reproduces. What it measures
is the harness, and pass 3 says exactly which statement:

| typed before the program (K-VT1 build) | result |
|---|---|
| (nothing) | `Unprintable error in 10` |
| `NEW` | `Unprintable error in 10` |
| `NEW` `CLS` | `[OK] \| [TWO]` |
| `CLS` | `[OK] \| [TWO]` |

🎯 **THE BOGUS ERROR FIRES EXACTLY ONCE, AND `CLS` IS WHAT SPENDS IT.** The
first-direct-statement row proves the once (`Unprintable error`, then `[TWO]`
prints normally). `NEW` does not reach the consuming path; `CLS` does. And every
battery in this tree resets through `CLS` — `stmtpend` types `("NEW","CLS")` on
vg8020/zb and `("","SCREEN 0","NEW","CLS")` on cf3300, `clearpool` types
`("NEW","CLS")` — so the one bogus statement is always spent on the reset before
the first scored row. **Measured in a fourth run rather than inferred from the
third**, because a mechanism written into a document on a plausible inference is
the exact defect this slice is about.

🎯 **A PREDICTION AND ITS REASON ARE TWO CLAIMS, AND A GREEN RUN CONFIRMS AT MOST
ONE.** K-SP4's number stands. Its *"openMSX zero-fills RAM"* does not, and the
number was read as confirming it — which is exactly the shape
[[a-predicted-miss-is-a-claim-too]] and
[[gate-can-be-green-while-measuring-nothing]] both describe.

---

## 5. 💰 The `VALTYP` fix itself: priced, and DECLINED

`ld (VALTYP),a` in the same cold hook, where `A` is already 0: **3 bytes of main
page 1**. Main page 1 measured **2 B free** on 2026-08-21 (`make basic-reloc`).
**It does not fit.**

* No cheaper encoding exists: `ld (nn),a` and `ld (nn),hl` are both 3 bytes, and
  no adjacent pair is already being zeroed (`STRPTR` at `$E0C9..CA` is not
  written either, so widening a store would need the same 3 bytes).
* No free home exists: `basic/main.asm`'s include order puts `interp.asm`,
  `vars.asm` (`clear_vars`) and `files.asm` (`init_filechan`) all **after**
  `__MEAS_LOW_END` — every cold-init routine in the tree is in page 1.
* The low region has 22 B and `basic/main.asm` states the two walls are
  **coupled**, so a promotion could fund it — but a promotion is its own slice
  with its own closure check, and this one is hygiene.

**Declined with the number.** `VALTYP` is written before it is read at every
`eval`, it is zerobas's own private cell with no reference column, and no gate in
the tree reads it — so nothing observable changes today. The residual stays open
with the price attached, and the reason to reopen it is a **new caller that reads
before writing**, not a spare byte.

---

## 6. ✅ THE APPARATUS HALF — CLOSED 2026-08-21 as D-COLDROW, **0 ROM bytes**

§4 ends by filing the hole rather than closing it: *"no battery boots and runs a
program without a `CLS`-bearing reset, so the cold stores for FPERR/ERRFLG/DOT
are gated by nothing."* This is that row, and it is two rows.

### 6.1 The shape — one variable, and it is the reset

`probes/basic/basic_probe_stmtpend.py` gains a fourth family, `b.*`, and a third
template that takes **no statement at all**:

```
COLD_PROG = ['10 PRINT"[OK]"', '20 PRINT"[TWO]"']
```

Two `PRINT`s, not one, so a machine that dies on the first statement and one that
dies on the second read differently.

| row | reset typed before the program | reading, all three sides |
|---|---|---|
| `b.cold` | `NEW` (vg8020/zb) · `""`,`SCREEN 0`,`NEW` (cf3300) | `[OK]\|[TWO]` |
| `b.warm` 🟢 | the side's normal reset, i.e. **with `CLS`** | `[OK]\|[TWO]` |

`b.warm` is a **positive control** and is pinned to that **LITERAL**, not to
cross-side agreement — see §6.3.

### 6.2 The machinery question, and the cheaper answer

The reset is per-SIDE (`SIDES[...]["reset"]`), not per-row. Widening the case
tuple to carry a reset would touch three unpack sites and all 58 shipped rows.
What landed instead is a label set consulted inside `run_side`:

```python
NO_CLS_RESET = {"b.cold"}
...
reset = (tuple(r for r in cfg["reset"] if r != "CLS")
         if label in NO_CLS_RESET else cfg["reset"])
```

Four lines, and **the 58 shipped rows build exactly the line list they built
before** — measured, not argued: `stmtpend-acceptance` reads **60/60** where it
read 58/58, with every pre-existing row's value unchanged.

Deriving the cold reset by REMOVING `CLS` from the side's own reset rather than
writing a literal one is what keeps the cf3300 arm honest: that side needs its
leading blank line and its `SCREEN 0`, and a hand-written override would have
had to know that.

### 6.3 🔴 The blindness this row would have had, and the pin against it

`b.cold` and `b.warm` share a template, a readout **and a reset builder**. If the
override ever stops firing — a renamed label, a side whose reset no longer says
`CLS`, a `CLS` that creeps into the template — `b.cold` silently becomes a second
copy of `b.warm`, **agrees on three sides, and measures nothing**. No differential
can catch that: there is no column in which the override differs
([[fileside-slice]]).

So it is pinned **statically**, by `reset_selftest()`, in **both senses** — the
override must REMOVE a `CLS` from every side, and the un-overridden twin must
still HAVE one. Calibrated against four known positives **before** the green run
was believed:

| mutation | complaints |
|---|---|
| baseline (shipped tree) | **0** |
| the label renamed (`b.colld`) | 1 — *"names 'b.colld', which is not a case"* |
| a side's reset loses its `CLS` | 2 — the side, **and** its control twin |
| `CLS` creeps into the template | 3 — one per side |
| the control twin deleted | 1 — *"no un-overridden b.\* row is left"* |

And `b.warm` carries a LITERAL want for the same reason `f.filesbare` does.

### 6.4 Knives — 2/2 EXACT, and the exit codes are again the point

| knife | cut | predicted | measured |
|---|---|---|---|
| **K-CR1** | the cold `ld (FPERR),a` (K-VT1's cut, anchored on the comment above it — it matches **twice** in the file) | `b.cold` reddens **alone**, at `Unprintable error in 10`; `b.warm` and all 58 shipped rows stay green | ✅ **EXACT**, rc **1** |
| **K-CR2** | probe-side: `NO_CLS_RESET = {"b.colld"}` | `reset_selftest` refuses; **rc 2**, nothing scored | ✅ **EXACT**, rc **2** |

`b.cold` under K-CR1: `vg8020='[OK]|[TWO]' cf3300='[OK]|[TWO]'
zb='Unprintable error in 10'`. That is the store made observable by a row, which
is the whole of the filed item.

⚠️ **K-CR2 is rc 2 and K-CR1 is rc 1, and a runner shelling out to `make
<gate>` could not tell them apart** — `make` exits 2 for any failed recipe
([[injjudge-slice]]). The runner invokes the probe.

⚠️ **A LOG THAT IS OVERWRITTEN IS A LOG THAT WAS NEVER READ.** The first knife
driver ran both rounds with the same `{knife}.r{n}` tag, so the narrow round
clobbered the full battery's report and left a `rc=1` with no red set behind it.
The return code was true and the evidence was gone. Re-run with a distinct tag —
[[zerobas-gate-operating-rules]]'s *"`ls` the log before believing a return
code"*, one layer up.

### 6.5 What this row does NOT cover

`ERRFLG $F414` and `DOT $F6B5` sit **inside** the C-BIOS-cleared system-variable
area (§2), so cutting *their* cold stores is genuinely invisible on this
emulator. Only `FPERR $F069` is below it. **A row claiming to cover all three
would be over-claiming**; `b.cold` covers one cell, and that is what it says.

### 6.6 ⚠️ A fixture dependency, and a justification from the day before that was wrong

`stmtpend-characterize`/`-acceptance` had **no `$(DISK_TEST_DSK)` dependency** —
the third instance in three slices, after `inputary` ([[arysite-slice]]) and
`namspc` ([[fileside-slice]]). Added.

🔴 **AND THE REASON D-FILESIDE GAVE FOR `namspc`'s IS FALSE.** It says the rows
*"would read `<NO OUTPUT>` on both disk sides and AGREE"*. They would not: that
probe **copies** the image per case, so a missing image raises `FileNotFoundError`
before openMSX is launched. Measured, not reasoned — the file was moved aside and
one row run on each probe: **rc 1, a traceback, no boot**. The dependency is right;
only the consequence claimed for its absence was wrong.

The silent-agreement failure is real, but it belongs to the **other** kind of
probe — the kind that hands the path straight to openMSX, which then boots with
no disk in the drive and says nothing. `inputary`'s note is accurate for exactly
that reason.

⚠️ **THE SPLIT BELOW IS A STATIC CLASSIFICATION, NOT 35 MEASUREMENTS.** Two of
the rows were measured (`namspc` and `stmtpend`, by moving the image aside); the
rest are `grep`, and the enumerator is in `TODO.md` so the next reader can re-run
it rather than trust it. **35** probes name `disk/test720.dsk`:

| kind, by `shutil.copy*(TEST_DSK` | probes | targets whose make rule lacks the dep |
|---|---|---|
| **copies** it per case → `FileNotFoundError`, **LOUD** | 19 | 24 |
| hands the path over → **SILENT** no-disk boot | 16 | 24 |

Five of the sixteen do not set `diska` at all and reach the drive some other way,
so the silent half is an **upper bound** on the dangerous class, not a roster.
Filed in `TODO.md` as a residual: it is a 48-target sweep with a per-probe
question in it, which is a slice, not a line in this one.
