<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-CASSAVE — what FORMAT each cassette SAVE verb writes

Measured 2026-08-07 on the **Philips VG-8020** *and* the **National CF-3300**
against zerobas at `21d7538`, by
[`probes/basic/basic_probe_cassave.py`](../probes/basic/basic_probe_cassave.py)
(`make cassave-characterize`). Spec: [spec-basic-cassave.md](spec-basic-cassave.md).

This is the reading the
[dotgaps-msx1-characterization.md](dotgaps-msx1-characterization.md) §3.2
residual was blocked on. That slice **found** the divergence — while measuring
which SAVE forms write `.`, the row that looked like a cassette-specific `.`
defect turned out to be a **format** divergence — recorded one WAV, decoded it,
pinned the `.` half as `csv-tok` and filed the rest.

## 0. 🔴 What the filed reading could NOT support, and why each gap matters

§3.2 rests on **one machine** and **two rows**, and it decoded the tape for the
subject only. Three things a fix must know were open:

| # | question the filed reading could not answer | why it decides the fix |
|---|---|---|
| 1 | Does the **CF-3300** write `$EA` too? | A one-machine reading is *"what a VG-8020 does"*. Re-specifying a **shipped save format** on one machine's word is the mistake the two-reference rule exists to prevent. |
| 2 | Are `SAVE"CAS:x"` and `SAVE"CAS:x",A` **the same thing**, or merely both ASCII? | The cheap fix routes the no-flag form into the `,A` path, making them **one code path**. If the references distinguish them anywhere — id, name, body — that fix is wrong, and a 0-byte diff is exactly the shape that hides it ([[a-filed-zero-byte-fix-can-hide-a-conflation]]). |
| 3 | What does **`CSAVE`** actually write? | §3.2 infers "tokenised" from a `.` row — a *screen* reading, not the tape. If `CSAVE` were ASCII too, the rule would be "every cassette save is ASCII" and the fix would be sited somewhere else entirely. |

Answers: **1 — yes, identical**; **2 — the same, on every reading this battery
can take**; **3 — `$D3`, on all three sides, and zerobas is already right there.**

## 1. The reading, all three sides

Program `10 REM ZQ8` / `20 REM ZQ9`. Each row is one boot on a fresh recording
tape (`cassetteplayer new`), decoded by
[`cas_decode.py`](../probes/lib/cas_decode.py).

| row | typed | VG-8020 | CF-3300 | zerobas @ `21d7538` |
|---|---|---|---|---|
| `sav-cas` | `SAVE"CAS:PA"` | `<nothing>` | `<nothing>` | `<nothing>` |
| `sav-cas:id` | *(file-type id)* | `EA` | `EA` | **`D3`** 🔴 |
| `sav-cas:name` | *(name field)* | `'PA    '` | `'PA    '` | `'PA    '` |
| `sav-cas:text` 🟢 | *(printable runs)* | `10 REM ZQ8 / 20 REM ZQ9` | *(same)* | **` ZQ8 /  ZQ9`** 🔴 |
| `sav-cas-a:id` | `SAVE"CAS:PB",A` | `EA` | `EA` | `EA` |
| `sav-cas-a:text` 🟢 | | `10 REM ZQ8 / 20 REM ZQ9` | *(same)* | *(same)* |
| `csave:id` 🟢 | `CSAVE"PC"` | `D3` | `D3` | `D3` |
| `csave:text` 🟢 | | ` ZQ8 /  ZQ9` | *(same)* | *(same)* |
| `sav-cas-bare:id` | `SAVE"CAS:"` | `EA` | `EA` | **`D3`** 🔴 |
| `sav-cas-bare:name` | | `'      '` | `'      '` | `'      '` |
| `sav-cas-bare:text` 🟢 | | `10 REM ZQ8 / 20 REM ZQ9` | *(same)* | **` ZQ8 /  ZQ9`** 🔴 |

🟢 = a **positive control**. **16 of 20 readings agree; the 4 that do not are one
defect wearing two rows.** The two references agree on every one of the twenty.

## 2. R-CV1 — `SAVE"CAS:name"` is an ASCII save on an MSX1, on BOTH references

`$EA` and the full listing — line numbers included — on the VG-8020 *and* the
CF-3300. That promotes §3.2's reading from one machine's behaviour to the MSX1
rule, which is the bar a change to a **shipped save format** has to clear.

zerobas writes `$D3` and its own [`basic/save.asm:12`](../basic/save.asm:12)
documents that as intended (*"SAVE "CAS:F" -> tape tokenised"*). The document is
wrong, not merely the code.

## 3. R-CV2 — `,A` is not a different verb, and this is what refutes the conflation

`sav-cas` and `sav-cas-a` return the **same** `:id` (`EA`), the same shape of
`:name`, and the **identical** `:text`. Every reading this battery can take says
they are one behaviour with two spellings, so routing the no-flag form into the
`,A` path is a faithful fix and not a collapse of two things into one.

🔴 **This is the reading that makes a 0-byte fix safe to believe.** The whole
change is one `jp` target, so the diff cannot tell you whether it merged two
behaviours that should stay apart. Only a measurement of both forms, on both
references, can — and `,A` was never decoded before this battery.

⚠️ **What it does NOT claim**: that no observable anywhere distinguishes them.
It claims that the file-type id, the name field and the printable content of the
data block do not, on either reference.

## 4. R-CV3 — `CSAVE` is the tokenised one, and it is the reason the claim stays narrow

`$D3` on all three sides, with the REM arguments present verbatim (` ZQ8 /  ZQ9`)
and **no line numbers as text** — the signature of a stored image rather than a
listing.

🟢 **This is the control that keeps the fix from over-reaching.** "SAVE"CAS:" is
ASCII" and "every cassette save is ASCII" differ by exactly this row, and
zerobas already agrees with both references here — so `CSAVE` must come out of the
fix **unchanged**, which is a claim knife K-CS3 exists to test.

## 5. R-CV4 — the bare form diverges the same way, and its NAME field already agrees

`SAVE"CAS:"` with no name writes six spaces in the name field on all three sides,
and `$EA` on both references against zerobas's `$D3`. So the bare form is the same
defect, not a second one, and nothing about the name handling is in scope.

## 6. Why the tape, and not the screen

Every verb here prints **nothing at all**, whatever it writes — `sav-cas`,
`sav-cas-a`, `csave` and `sav-cas-bare` all read `<nothing>` on all three sides.
D-DOTGAPS found the divergence only because the format leaks into a **`.`**
reading, and then had to decode a WAV to learn that the `.` row was a symptom.
This battery reads the format directly.

🔴 **`:text` is what lets a tokenised row and an ASCII row be scored the same
way.** A tokenised image cannot be compared byte-for-byte across machines — its
line links are absolute addresses and `TXTTAB` differs between a VG-8020, a
CF-3300 booting Disk BASIC, and zerobas. The **printable runs** do not: `REM`
keeps its argument verbatim after the `$8F` token. So a tokenised save yields the
text without the line numbers and an ASCII save yields the whole listing, both
stable cross-side, and the difference between them *is* the format question. The
≥3-character run threshold keeps stray printable link bytes out — links and line
numbers are 2-byte binary and cannot reach it.

## 7. What is NOT claimed here

* **What `LOAD"CAS:"` / `CLOAD` accept** — unchanged and out of scope. A separate
  filed residual covers `LOAD"CAS:"` accepting a tokenised tape where the
  reference does not return (`TODO.md`); nothing here touches the read side.
* **`BSAVE"CAS:"`** — `$D0`, not measured here, not touched.
* **The `,speed` clause** — `CSAVE"name",2` is parsed by a different path and no
  row asks.
* **Whether a name longer than six characters is truncated or refused** — the
  shared capture truncates on every verb; no row asks.
* **The block framing of the ASCII file** (256-byte blocks, Ctrl-Z padding) is
  not compared byte-for-byte; `:text` reads the printable content, which is what
  the format question needs.
