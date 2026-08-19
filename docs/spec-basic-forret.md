# `RETURN` discards the `FOR` frames opened since its `GOSUB`

D-FORRET, 2026-08-19, on `main`, based on `0f1a2a8` (D-REPRICE). Closes the
`TODO.md` residual *"`RETURN` DOES NOT DISCARD AN OPEN `FOR`, AND ON THE
REFERENCE IT DOES"*, filed 2026-08-02 by D-RETLN and re-measured still-live on
2026-08-09.

Two references (Philips VG-8020, National CF-3300) agreeing on **every** row.

---

## 1. The rule

MS-BASIC keeps `FOR` and `GOSUB` frames on the **same** (Z80) stack, so a
`RETURN` looking for a `GOSUB` frame walks past — and discards — every `FOR`
frame pushed since. zerobas keeps the two on **separate RAM stacks**
(`GOSUB_STK`/`GSP` and `FOR_STK`/`FSP`), so nothing is walked past and the loop
survives.

**Stated as a rule about depth rather than about a stack layout:**

> A `RETURN` truncates the `FOR` stack back to the depth it had when the
> matching `GOSUB` was taken. With no `GOSUB` frame at all, it discards **every**
> open `FOR` and then raises ERR 3.

That phrasing is what makes the fix possible with two stacks: the depth MS-BASIC
gets for free from the layout has to be **recorded** to be restored.

---

## 2. 🔴 The row that filed this could not have specified the fix

`lnrt-forret` is the row D-RETLN pinned, and it is the corner with **no `GOSUB`
frame at all**. It is consistent with the rule above *and* with a much narrower
one — *"a `RETURN` that finds no frame clears the `FOR` stack"* — and the two
prescribe **different code**: the narrow rule needs three bytes in
`ex_ret_under` and nothing else; the real rule needs a field in every `GOSUB`
frame. One row cannot separate two rules
([[one-row-cannot-separate-two-rules]]), which is the lesson `lnrt-forret` was
itself filed under, one level up.

So four rows with a real `GOSUB` frame underneath were measured **before** any
byte was designed.

---

## 3. The measurement

All six rows in the `lnrt` battery of
[`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
`make lnblank-say-acceptance ONLY=lnrt-for`, both references + zerobas:

| row | what it puts above the `GOSUB` frame | both references | zerobas before |
|---|---|---|---|
| `lnrt-forret` | *no frame at all* — one `FOR` open | ` 102  0  1 ` | ` 103  0  4 ` 🔴 |
| `lnrt-forgsb` | one `FOR`, opened in the subroutine | ` 1  0  7 ` | ` 1  0  8 ` 🔴 |
| `lnrt-forgdeep` | **two** `FOR`s, opened in the subroutine | ` 1  0  7  4 ` | ` 1  0  8  4 ` 🔴 |
| `lnrt-forgline` | one `FOR`, popped by `RETURN <line>` | ` 1  0  7 ` | ` 1  0  8 ` 🔴 |
| `lnrt-forgctl` | 🟢 **control** — `FOR` opened BEFORE the `GOSUB` | ` 0  0  3 ` | ` 0  0  3 ` ✅ |
| `lnrt-forerr` | 🟢 **control** — `ERROR 7` in place of `RETURN` | ` 103  0  4 ` | ` 103  0  4 ` ✅ |

🎯 **All four predictions were written into the probe before the run and all
four were EXACT** (§6).

🔴 **THE DISCRIMINATOR IS `I`, NOT THE ERROR COUNT.** Both sides trap exactly
once in `forgsb`/`forgdeep`/`forgline`, so both read `A=1`; what separates them
is whether the `NEXT` found a live frame (`I` steps to 8) or none (`I` stays at
the `FOR`'s initial 7). **A row scored on "did it error" would agree on both
sides and read green** — the same shape as `ex_let_arr_str`'s wrong-message trap
recorded in [`repricing-page1-2026-08-19.md`](repricing-page1-2026-08-19.md) §3.7.

### 3.1 The two controls carry different weight, and one of them corrects the item

* **`lnrt-forgctl`** pins the *other* half of the rule: a `FOR` opened **before**
  the `GOSUB` must SURVIVE. Without it, "clear the whole `FOR` stack on every
  `RETURN`" would score green on all four red rows and be wrong.
* **`lnrt-forerr`** is D-RETLN's own control and it **corrects the residual's
  prescription**. The item says closing this means teaching *"`RETURN` (and the
  error unwind)"* about the `FOR` stack. `lnrt-forerr` — the identical program
  with `ERROR 7` for `RETURN` — reads ` 103  0  4 ` on **all three sides**, so an
  ordinary trap does **not** unwind the `FOR` stack on the reference either.
  **The error-unwind half of the prescription is refuted by a control the item
  itself carries**, and this slice changes no error path.

---

## 4. The design

`GOSUB_FRAME` 4 → **6 bytes**: `[CURLINE:2][resume-ptr:2][FSP-at-push:2]`.

* **`gosub_push`** records `(FSP)` as it is at push time — 9 B.
* **`ret_frame`** reads it back and stores it to `FSP` before popping the rest —
  8 B. Sited here rather than in either arm **because both arms pop through it**,
  and `lnrt-forgline` measured that `RETURN <line>` discards the same entries.
* **`ex_ret_under`** (no frame at all) sets `FSP` to `FOR_STK` before raising
  ERR 3 — 6 B.

**+23 B main page 1 (64 → 41 free), +16 B RAM, 0 B low region, 0 B sub.**

The RAM comes from the window D-FORVAR freed when it relocated the `FOR` stack
to page 3: `$E070..$E0B8` was 72 B free, and `GOSUB_STK` now ends at `$E080`,
leaving **56 B**.

⚠️ **`gosub_push` IS SHARED WITH THE INTERRUPT-TRAP DISPATCHER**
(`basic/traps.asm`, its GOSUB-into-handler branch), so a trap handler's `RETURN`
now truncates the `FOR` stack too. That is the same rule and is believed
correct, but it is **not separately measured here**; all five trap gates are run
as regression (§5). `traps.asm` matches service records on the **value** of
`GSP`, not on a frame size, so widening the frame does not disturb it.

---

## 5. Gates

All green at the shipped tree:

| gate | result |
|---|---|
| `make lnblank-say-acceptance` | **208/208** gating rows agree across all three sides |
| `make unit-test` | **59/59** |
| `make deadcode` | 0 dead, both builds |
| `make basic-reloc` | 5 B low / **41 B** page 1 / 3295 B sub p0 / 1627 B sub p1 |
| `forvar` / `nxlist` / `nxary` | green — the `FOR` stack's own gates |
| `error-trap` / `onerr0` / `abort` | green — no error path changed (§3.1) |
| `stop` / `interval` / `key` / `sprite` / `strig` -trap | green — `gosub_push` is shared with the dispatcher |

`lnrt-forret`'s `KNOWN_DIVERGE` entry is **deleted**, so the probe's pin count
drops 3 → 2 and the row is scored ordinarily again.

🔴 **`make unit-test` WENT RED AND WAS RIGHT TO.** `tests/test_traps.py`
asserted *"GSP advanced by 4"* as a literal, and the dispatcher reaches
`gosub_push`. The assertion now reads `GOSUB_FRAME` from the symbol table and
gained a **new tooth** — that the frame's third field really holds the seeded
`FSP` — rather than being relaxed to the new number: a test that restates a
constant can only ever rot into agreement with whatever it was last edited to
match. A second site (`GSPV + 4`, "a nested GOSUB pushed higher") kept passing
throughout, because any non-equal value satisfies it — the number was never
load-bearing there, but the comment claiming it was a frame width now reads
from the symbol too.

---

## 7. Knives — 3 cuts, 3 EXACT

Runner: `scratchpad/forret_knives.py` (throwaway, per `dev-workflow.md`). The
probe is invoked **directly**, restore is from a scratchpad snapshot in a
`finally`, and every cut is **ROM-hash guarded** — a green row under a cut that
never reached the ROM is a claim about the runner, not about the tree.

| knife | cut | predicted red | measured | verdict |
|---|---|---|---|---|
| **K-FR1** | `ex_ret_under`'s `ld (FSP),hl` → a dead cell | `lnrt-forret` | `lnrt-forret` | ✅ EXACT |
| **K-FR2** | `ret_frame`'s `ld (FSP),de` → a dead cell | `forgsb`, `forgdeep`, `forgline` | the same three | ✅ EXACT |
| **K-FR3** | `gosub_push` records a CONSTANT `FOR_STK` | `lnrt-forgctl` | `lnrt-forgctl` | ✅ EXACT |

Baseline `5bab56b1`; the three cuts produced `811fbe22`, `e70de07a`, `199b2742`
— three distinct ROMs, so each was genuinely applied.

🎯 **K-FR3 IS THE ONE WORTH KEEPING.** It makes every `RETURN` clear the whole
`FOR` stack — which is *correct* for all four red rows and wrong only for the
control — so it reddens `lnrt-forgctl` **and nothing else**. That is the
control earning its place: without it, the cheap wrong design ("clear the stack
on every RETURN") scores a clean sweep and ships.

🎯 **AND THE THREE CUTS PARTITION THE ROWS.** Each site owns a disjoint set,
which is what says the rows are measuring three different things rather than
one thing three times.

---

## 6. Predictions, scored

| row | predicted | measured | verdict |
|---|---|---|---|
| `lnrt-forgsb` | refs ` 1  0  7 `, zb ` 1  0  8 ` | as predicted | ✅ **EXACT** |
| `lnrt-forgctl` | all three ` 0  0  3 ` | as predicted | ✅ **EXACT** |
| `lnrt-forgdeep` | refs ` 1  0  7  4 `, zb ` 1  0  8  4 ` | as predicted | ✅ **EXACT** |
| `lnrt-forgline` | refs ` 1  0  7 `, zb ` 1  0  8 ` | as predicted | ✅ **EXACT** |
| cost | ~23 B page 1 | 23 B (64 → 41) | ✅ **EXACT** |
