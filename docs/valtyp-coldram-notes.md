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
