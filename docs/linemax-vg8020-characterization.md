<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-LINEMAX — how long a line each machine takes (VG-8020 characterization)

Measurement behind [`spec-basic-linemax.md`](spec-basic-linemax.md). Probe
[`probes/basic/basic_probe_linemax.py`](../probes/basic/basic_probe_linemax.py),
`make linemax-characterize ONLY=rem|tok|tokx|bnd|corrupt` (+ `--cas`),
boot-per-case, both machines. Split out of D-ARR-C, which measured the divergence
([`arrdim-c-vg8020-characterization.md`](arrdim-c-vg8020-characterization.md) §4)
and could not reach it.

Six batteries, measured **2026-07-29**. Two of them exist because the item as
filed was the wrong size: the input line is the smaller half of what is wrong
here.

---

## 0. The instrument: the stored line's own bytes

Every length battery reads `("stored_line", TXTTAB)` — omsx_repl dereferences the
BASIC text base and returns the first stored line's **exact bytes**. `REM` keeps
the rest of its line verbatim on both machines
([`basic/tokenise.inc:99`](../basic/tokenise.inc:99)/[`:181`](../basic/tokenise.inc:181)),
so `20 REM` + filler stores one token plus the surviving filler and the
truncation point is **counted**, not inferred from a proxy variable.

This is what lets §1 separate two dispositions the arrdim `line` battery folds
together. That battery reads `20` + padding + `A=7`: a line truncated *anywhere*
in its tail loses the assignment, so "the tail was dropped and the rest kept" and
"the whole line was refused" both read 0. They are different behaviours and a
faithful implementation has to copy the right one.

**Calibration.** `rem-100` must read exactly **+89 filler** on zerobas — 95
characters minus `20 REM`, the number `LINEMAX = 96` predicts. It does. `rem-40`
is the two-sided control.

---

## 1. 🔴 The reference's line ends at 254 — and the apparatus said 250

| source chars | 40 | 90 | 94 | 95 | 96 | 97 | 100 | 200 | 248 | 250 | 252 | 253 | **254** | 255 | 256 | 257 | 260 | 300 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| reference (filler stored) | 34 | 84 | 88 | 89 | 90 | 91 | 94 | 194 | 242 | 244 | 246 | 247 | **248** | 248 | 248 | 248 | 248 | 248 |
| zerobas | 34 | 84 | 88 | **89** | 89 | 89 | 89 | 89 | 89 | 89 | 89 | 89 | 89 | 89 | 89 | 89 | 89 | 89 |

**The reference's last intact line is 254 characters; zerobas's is 95.** Past its
ceiling each machine **saturates**: the reading is flat at 248 filler from 255 all
the way to 300, and flat at 89 from 96 up.

**Both machines DROP the tail and KEEP the line.** Neither refuses it, neither
raises an error, and the truncated line is stored. So the disposition already
agrees — only the ceiling differs, and this half of the item is a single constant.

⚠️ **THE APPARATUS HAD THE ANSWER HARD-CODED, AND IT WAS A GUESS.**
`omsx_repl.MAX_BUF` was **250**, commented "MSX line-input buffer (BUF/LINBUF)
holds ~255 chars incl CR", and it *refused to inject a longer line*. The arrdim
`line` battery's top row is 250. So §4's "the reference's is 250" was the
**harness's ceiling reported as the machine's**: every length past it was
unreachable, not accepted-and-tested. Nothing was measured wrong — something
unmeasured was written down as measured, which is the same failure the arrays
arc's §4 target #9 hid for a year. The constant is now **254, measured**, with the
plateau above it as its own evidence.

---

## 2. 🔴 The crunched line is the real defect, and it is live TODAY

The tokeniser **expands**. A double literal is `DBL_TOKEN` + 8 value bytes
([`basic/sysvars.inc:288`](../basic/sysvars.inc:288),
[`sub/tkfloat.asm`](../sub/tkfloat.asm) `tkf_double`), so the two characters `0#`
become **nine bytes** — 4.5×. zerobas's `TOKBUF` is **96 bytes** (`$E160..$E1BF`)
and [`basic/tokenise.inc`](../basic/tokenise.inc) bounds its writes **nowhere**.

`20 A=` + `0#`×k, both machines, crunched body bytes stored:

| k | 5 | 10 | 11 | 12 | 20 | 30 | 34 | 35 | 36 | 40 | 45 | 124 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| source chars | 15 | 25 | 27 | 29 | 45 | 65 | 73 | 75 | 77 | 85 | 95 | 253 |
| reference | 47 | 92 | 101 | 110 | 182 | 272 | 308 | **refused** | refused | refused | refused | refused |
| zerobas | 47 | 92 | **101** | 110 | 182 | 272 | 308 | 317 | 326 | 362 | **407** | 407 |

The two agree byte-for-byte to 308. Then they part:

* **The reference REFUSES and says so.** From 315 body bytes it prints
  **`Line buffer overflow`** and stores nothing (the `tokx` battery reads the
  screen; the `bnd` battery walks the boundary a byte at a time with a trailing
  filler run, and puts it at **314 accepted / 315 refused**).
* **zerobas has no bound at all.** It writes 407 bytes into a 96-byte buffer —
  **311 bytes past the end** — silently, and stores the result as a program line.

**The onset is a 27-character line.** `k = 11` already crunches to 101 bytes.
This needs no long line, no array and no `LINEMAX` change: it is reachable at
today's 95-character ceiling, and raising `LINEMAX` only widens the window.

zerobas's worst case is **407 bytes**, pinned by its own input truncation (95
characters = 45 literals) — which is why `tok-45` and `tok-124` read the same.
That write runs from `$E160` to `$E2FE`, over `ARYTAB` (`$E1C0`, the scalar/array
boundary and the *first* cell past the buffer), the whole error-trap block
(`DIRECTF`/`SAVSTK`/`ERRCODE`/`ERRLINE`/`ONELIN`/`ONEFLG`/`ERRRESUME`/`SAVTXT`),
the 54-byte `ZTRAP` table, `TRAPENA`/`TRAPSTK`/`TRAPPEND`, `POOLSIZE` (`$E232`)
and into `STRTAB` (`$E240`).

### 2.1 It is fatal, not cosmetic

⚠️ **"It wrote past the buffer" is not a defect until something reads the damage.**
The `corrupt` battery types the overrunning line **direct**, then a plain
statement, then a short readout:

| | after the overrun, `B=7 : PRINT B` | after the overrun, `B$="HI" : PRINT B$` | control (5 literals, no overrun) |
|---|---|---|---|
| reference | ` 7 ` | `HI` | ` 7 ` |
| zerobas | **`<none>`** | **`<none>`** | ` 7 ` |

After the overrun zerobas cannot execute a numeric assignment or a string
assignment — the readout never prints at all. The control is the same shape at a
length that does not overrun and reads ` 7 ` on both, so the red rows are the
overrun and not the direct line, the payload or the readout.

These are also the rows that can **falsify a fix**: bound the crunch and they go
green; leave `TOKBUF` where it is and no amount of `LINEMAX` work can move them.

### 2.2 🔴 The LEAN cart has it too, by a different route

The obvious reading is that this is a repack-only defect: the lean 16 KB cart has
**no float pack**, its integer crunch `tk_number`
([`tokenise.inc:279`](../basic/tokenise.inc:279)) emits at most 3 bytes from 3
characters, and measured directly it crunches `0#` as `11 23` — two characters,
two bytes, no expansion at all.

**That reading is wrong, and it is reasoning rather than measurement.** The float
literal is the *widest* expansion, not the only one. A line-number reference is
`$0E` + a 16-bit word — **three bytes from one source character** (`branch_lineno`,
MSX2 TH Figure 2.12) — so in an `ON..GOTO` list every `,1` is two characters and
four bytes:

| `20 ONAGOTO1` + `,1`×k | k=5 | 20 | 22 | **23** | 30 | 42 |
|---|---|---|---|---|---|---|
| source chars | 21 | 51 | 55 | **57** | 71 | 95 |
| crunched body (both builds) | 26 | 86 | 94 | **98** | 126 | **174** |

**A 57-character line already exceeds the 96-byte `TOKBUF` in the lean build**,
and 95 characters reach 174 — 78 bytes past it. In the lean build `TOKBUF+96` is
`VARTAB`, the **live** variable table (the repack build relocated scalars out;
lean did not).

And it is observable there too. A variable set **before** the over-long line:

| `B=7` : `ONAGOTO1,1,…` (42) : `PRINT B` | reference | lean cart |
|---|---|---|
| | ` 7 ` | **` 0 `** |

⚠️ **THE `tok` BATTERY'S OWN VERDICT CANNOT SEE THIS.** Every `lnum` row *passes*
— both machines crunch the identical 174 bytes, so the stored bytes agree
perfectly. The reference has a 315-byte buffer and is fine; the lean cart has 96
and is not. **Agreement on what was produced is not agreement on whether it fit.**
Only the `corrupt`-shaped rows, which read the damage, separate them.

---

## 3. The third consumer agrees — measured, not assumed

`ascii_read_lines` ([`basic/files.asm:1461`](../basic/files.asm:1461)) bounds an
ASCII-LOADed line with the same idiom and the same constant as the keyboard
reader. That is a reason to *expect* agreement, not a measurement of it, and the
reference's ASCII loader is not obliged to share its editor's ceiling. The
VG-8020 has no disk, so the battery carries the line in on an `$EA` cassette tape
and reads the same stored-line bytes back after `LOAD"CAS:"`:

| tape line | 40 | 100 | 250 |
|---|---|---|---|
| reference | 34 filler | 94 | **244** |
| zerobas | 34 filler | **89** | **89** |

Identical to §1 on both machines: the ASCII path shares each machine's typed
ceiling, and zerobas's `ascii_read_lines` truncates at the same 95 characters.
One constant governs both paths on both machines.

---

## 4. Two dispositions, and the one that is not this item

The battery matrix also caught a divergence that has nothing to do with buffers,
found as a **failing two-sided control**. The first `tok` payload was `20 ` +
literals, and `tok-5` — a length nothing truncates — diverged:

```
typed:      20 0#0#0#0#0#
VG-8020 ->  line 200, body = 0x23 ('#') + four double literals
zerobas ->  line 20,  body = five double literals
```

The reference's **line-number scan skips the blank and keeps accumulating
digits** (`20` + ` ` + `0` = 200) where zerobas stops at the space. Same source,
different line number *and* different body. It is filed as its own item; here it
was purely a confound, removed by putting a letter after the space (`20 A=`).

Two causes, two dispositions:

* **§1 (the input line)** is one constant and its RAM home. Both machines already
  agree on *what truncation means*.
* **§2 (the crunch)** is a missing bound and a missing error, it is a live
  memory-corruption defect at today's `LINEMAX`, and it is what actually sizes
  the buffers this slice has to re-home.
