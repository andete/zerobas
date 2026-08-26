<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-KEYSTR scout — the gap is not the statement, it is the whole string area

Status: **📏 SCOUT. Measurement only — no source file changed, no ROM byte
moved** (`24d8e393` / `ae796ccb` / `5bf17dee`). 2026-08-26, on `53fe29e`.
`scratchpad/keystr_probe.py`, `keystr_scout2.out`.

`TODO.md` files `KEY n,"str"` / `KEY LIST` as unimplemented, on an **error-code**
reading: `KEY1,"X"` is 0 / 0 / 2. That says nothing about what the statement is
supposed to DO, which is the whole of what an implementation has to match.

---

## 1. The oracle, and why the address is measured rather than assumed

zerobas has **no `FNKSTR` equate at all** — the name occurs only in comments
(`basic/keytrap.asm`). So the probe **plants a distinctive string** and reads it
back: `KEY n,"ZQX"` writes three bytes (90, 81, 88) that do not occur together
by accident. Reading exactly those at a named address is a measurement of that
address; a guessed address that returns plausible bytes is the shape that gets
believed.

Both halves of the hypothesis — the **base** and the **stride** — get a row that
can refute them, plus a plant-nothing control.

| row | statement | read at | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|---|
| `k.slot1` | `KEY 1,"ZQX"` | `$F87F` | `90 81 88 0` | `90 81 88 0` | **`0 0 0 0`** 🔴 |
| `k.slot2` | `KEY 2,"ZQX"` | `$F88F` | `90 81 88 0` | `90 81 88 0` | **`0 0 0 0`** 🔴 |
| `k.slot10` | `KEY 10,"ZQX"` | `$F90F` | `90 81 88 0` | `90 81 88 0` | **`0 0 0 0`** 🔴 |
| `k.s1at2` | `KEY 1,"ZQX"` | `$F88F` | `97 117 116 111` | same | `0 0 0 0` |
| `k.none` | *(nothing planted)* | `$F87F` | `99 111 108 111` | same | `0 0 0 0` |
| `k.smoke` | *(no memory read)* | — | `0 1 2 3 4` | `0 1 2 3 4` | `0 1 2 3 4` ✅ |

**Base `$F87F`, stride 16, NUL-terminated** — all three measured, none assumed.
The two controls are what make that a reading rather than a coincidence:
`k.s1at2` plants slot 1 and reads slot 2's address, getting `97 117 116 111` =
**"auto"** (F2's default) rather than the plant, so the stride is not an
artifact; and `k.none` plants nothing and reads `99 111 108 111` = **"colo"**,
the head of F1's default `"color "`.

---

## 2. 🔴 THE FINDING IS BIGGER THAN THE FILED ITEM, AGAIN

zerobas reads **`0 0 0 0` at every slot, including with nothing planted.** The
references' *defaults* are there on a cold boot; zerobas's are not.

🎯 **So the gap is not "the assignment statement is missing" — the FUNCTION-KEY
STRING AREA IS UNPOPULATED.** `KEY ON` calls C-BIOS `DSPFNK`, which renders that
area; with it all zeros there is nothing to render. An implementation of
`KEY n,"str"` that only added the parse and the copy would leave nine slots
holding zeros where the reference holds `color `, `auto`, `goto`, `list`, …

⚠️ **This is the second time this item has been reframed by a control rather
than by its subject.** D-MISSOP3's `r.keyok` turned *"`KEY1,` has the wrong
error code"* into *"the statement form is absent"*; `k.none` here turns *"the
statement form is absent"* into *"the storage it writes to is empty too"*.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]] is about rows that agree;
this is its neighbour — **a row that DIFFERS can differ for a bigger reason than
the one you filed.**

---

## 3. 🔬 Three instrument faults, and the tally is what caught all three

The first three runs returned `<NO OUTPUT>` on **every row of every machine**,
with `0 on signal, N fell back to the scheduled budget`. That pair is the
harness saying *"the program never reached its END"* — not *"the machines
disagreed"* — and it is only legible because `probe_signal.Tally` prints it
([[a-probe-whose-answer-is-nothing-happened]]).

1. 🔴 **THE HANDLER'S `RESUME` TARGET WAS INSIDE THE CODE THAT COULD FAIL.** The
   statement under test aborts on zerobas *by design*, so the handler had to
   continue past it — at line 30, which was the top of the memory scan. Any
   error raised **inside** the scan resumed straight back into the scan.
   An infinite loop that reads exactly like a slow program.
2. ⚠️ **`&HF000` IS NEGATIVE AND `63488` IS A FLOAT.** MSX integers are signed,
   so `&HF000` is −4096; rewriting the bound in decimal to avoid that pushed it
   past 32767 and silently promoted the whole loop to single precision.
3. 🎯 **AND THE SCAN STILL DID NOT FINISH, SO THE STRATEGY WENT RATHER THAN THE
   DETAILS.** What separated *scaffold* from *search* was a no-loop smoke row
   (`k.smoke`) returning `0 1234 7` **captured on signal** while every scan row
   fell back. **Bisect the instrument with a row that does nothing** before
   changing the subject a third time. The shipped probe has no loop at all, and
   `k.smoke` is kept as its permanent control.

---

## 4. What a fix has to do, and what is still unpriced

* Parse `KEY <n>,<string>` with `n` in 1..10 — **the domain is unmeasured**;
  `KEY 0,` and `KEY 11,` were not run.
* Copy up to 15 bytes to `$F87F + 16*(n-1)`, NUL-terminated. **The truncation
  length is unmeasured** — a 20-character plant was not run, so "15" is read off
  the stride and not off a machine.
* **Populate the ten defaults at cold boot**, which is a table plus a copy and is
  probably the larger half.
* Refresh the display when the function-key line is on.
* `KEY LIST` is untouched by this scout.

💰 Main page 1 was **85 B** free on 2026-08-26 — read the wall, never this line.
The defaults table alone is ~160 B of *data*, so this needs a home outside main
page 1 before it needs a design.
