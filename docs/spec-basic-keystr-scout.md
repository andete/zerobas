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

## D-KEYSCOUT2 (2026-09-04) — the three unmeasured things, measured

The item is marked SCOUT-THEN-ASK and draws its own line: *"the decision is
yours; the measuring and pricing in front of it are not"*. It then names what was
missing — the `n` domain, the truncation length, and `KEY LIST` entirely.
`scratchpad/keylist_probe.py`, 11 rows × 3 machines.

### The `n` domain

| typed | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|
| `KEY 1,"X"` | accepted | accepted | **ERR 2** |
| `KEY 10,"X"` | accepted | accepted | **ERR 2** |
| `KEY 0,"X"` | **ERR 5** | **ERR 5** | ERR 2 |
| `KEY 11,"X"` | **ERR 5** | **ERR 5** | ERR 2 |
| `KEY -1,"X"` | **ERR 5** | **ERR 5** | ERR 2 |
| `KEY 1,""` | accepted | accepted | ERR 2 |
| `A=1` (control) | 0 | 0 | 0 |

So the domain is **1..10, out of range is Illegal function call**, and the empty
string is legal. The control is green on all three, which is what makes "ERR 2
everywhere" a reading about zerobas rather than about the program.

### The truncation length — read off a machine, not off the stride

    KEY 1,"ABCDEFGHIJKLMNOPQRST"   (20 characters)
    KEY LIST  ->  ABCDEFGHIJKLMNO  (15)

**15 confirmed**, on both references. The filed caveat was that 15 came from the
16-byte stride with a NUL, which is an inference from a memory map rather than a
measurement of a verb. It agrees — but it is now a reading.

### `KEY LIST` — and the defaults it hands over

`KEY LIST` works on both references and is `Syntax error` here. It also prints
the ten defaults, which is the cheapest way to read them: the item prices them as
*"~160 B of DATA … the larger half"*, and one row produces all ten as text
instead of forty PEEK rows over `FNKSTR`.

| slot | VG-8020 | CF-3300 |
|---|---|---|
| F1–F5 | `color` `auto` `goto` `list` `run` | identical |
| **F6** | **`color 15,4,4`** | **`color 15,4,7`** |
| F7–F10 | `cload"` `cont` `list.` `run` | identical |

🔴 **THE DEFAULTS ARE NOT UNIVERSAL, AND THE ITEM DID NOT KNOW THAT.** Slot 6
differs between the two references — they are different machines with different
default screen colours. zerobas has **two official build targets** with different
oracles (disk → CF-3300, diskless → VG-8020), so "the default for F6" is a
per-target answer, not a constant. That is a design input, and it is the one part
of this that is genuinely a decision.

⚠️ **`KEY LIST` CANNOT SHOW TRAILING SPACES OR A CR.** The real defaults end in
spaces (`color `) and several in a carriage return (which is what makes `run`
execute rather than just type). The first scout's PEEK read `"colo"` at F1, from
`"color "` — consistent. So the 60-byte packed figure above is a **lower bound**;
the exact bytes need a `PEEK` read of `FNKSTR`, and a straight 160-byte image
sidesteps the question entirely.

### The price

`ex_key` is at **`$5AB8` — main page 1**, which is the constrained region
(read `make basic-reloc`; it was 14 B when this was written). The sub ROM is not:
sub page 0 had 1416 B.

* **main page 1: ~7 B net** — the `jp stmt_error` at `basic/screen.asm:294` (3 B)
  becomes a tenant dispatch (`ld ix` / `call subrom_call` / `jp c,…`, ~10 B). A
  page-0 tenant may call main page 1, so the tenant can reach the expression
  evaluator, which is the D-PUSIGN / D-PUEMIT pattern.
* **sub page 0: ~160 B of data + ~120 B of code** — a straight `FNKSTR` image
  copied with `LDIR` at init (exact, no unpacking), plus the `KEY n,"str"` parse
  and store and the `KEY LIST` print.

Nothing here needs main-page-1 room beyond those ~7 B, which is what the filed
*"needs a home outside main page 1"* was waiting on.

### What is left for Joost

Only the decision, plus one question the measuring surfaced: **F6's default is
machine-specific**, so does zerobas ship the CF-3300 value on the disk build and
the VG-8020 value on the diskless one (faithful to each target's oracle, but two
different ROMs), or one value everywhere?


## D-KEYDEF (2026-09-10) — the exact 160 bytes, and the fix that ships them

§"`KEY LIST` cannot show trailing spaces or a CR" asked for a PEEK read of the
whole area. [`scratchpad/keydef_probe.py`](../scratchpad/keydef_probe.py)
([`.out`](../scratchpad/keydef_probe.out)) reads all 160 bytes at `$F87F` on both
references after a cold boot. **They agree on every byte except F6.**

| slot | VG-8020 bytes (stride 16, NUL-padded) | as text |
|---|---|---|
| F1 | `99 111 108 111 114 32 0…` | `color␠` |
| F2 | `97 117 116 111 32 0…` | `auto␠` |
| F3 | `103 111 116 111 32 0…` | `goto␠` |
| F4 | `108 105 115 116 32 0…` | `list␠` |
| F5 | `114 117 110 13 0…` | `run` CR |
| F6 | `99 111 108 111 114 32 49 53 44 52 44 52 13 0…` | `color 15,4,4` CR — **CF-3300: `…,7`** |
| F7 | `99 108 111 97 100 34 0…` | `cload"` |
| F8 | `99 111 110 116 13 0…` | `cont` CR |
| F9 | `108 105 115 116 46 13 30 30 0…` | `list.` CR `$1E` `$1E` |
| F10 | `12 114 117 110 13 0…` | `$0C` `run` CR |

The tails the LIST scout could not see: `run` and `cont` end in a CR (which is
what makes them execute), F9 carries two `$1E` (cursor-up) after its CR, F10
starts with a form feed. zerobas read `0` at all 160 bytes on the same boot.

**Shipped as D-KEYSTR**: this image is data in [`sub/keystr.asm`](../sub/keystr.asm)
(the VG-8020 bytes on both targets — the standing style ruling), copied to
`$F87F` once from `init` (cold boot only); `KEY n,"str"` stores the staged
string into slot n (cleared first, truncated to 15); `KEY LIST` prints the ten
slots up to their NUL. Gate: `make keystr-acceptance`. Cost, read from a clean
tree: main page 1 89 → 24 B, sub page 0 1100 → 839 B — never quote these,
run `make basic-reloc`.
