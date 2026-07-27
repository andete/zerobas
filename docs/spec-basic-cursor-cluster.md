<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — the cursor / `PRINT` cluster: `CSRLIN`, `POS`, `TAB(`, `SPC(`

**Status:** SPEC, 2026-07-27 — **awaiting sign-off** (D-CUR-A/B/C, §6). Nothing
implemented. Step 2 of [`decision-kwgaps-slicing.md`](decision-kwgaps-slicing.md)
§4.3. Behavioural contract comes entirely from
[`cursor-vg8020-characterization.md`](cursor-vg8020-characterization.md) —
`make cursor-characterize`.

## 1. Scope and what it buys

Four of the eight SILENT-GAP words in one slice, one spec, one gate. After this
the silent class is **down to two** (`FRE`, `BIN$`), and D-KW-3 named emptying
that class the arc's exit criterion.

Today all four parse as something else and compute a wrong answer with no error:
`CSRLIN` as the variable `CS`, and `POS`/`TAB`/`SPC` as *arrays*. `TAB(` is the
word that started the sweep — `PRINT TAB(99999)` raises ERR 6 on both sides for
structurally different reasons, so a differential agreed while it was absent.

**In scope:** the four words, their kwtable rows, and a standing gate.
**Also proposed, pending D-CUR-B:** the comma-zone rule (D-CUR-1), which is the
same routine `SPC(` shares its padding with.
**Out of scope:** D-CUR-2, the boot text width (§6, D-CUR-C).

## 2. The measured contract

Full tables in the characterization; the clauses an implementation must satisfy:

1. **`CSRLIN`** — bare pseudo-variable, no parentheses, no argument. 0-based
   cursor row. `CSRLIN(0)` is `CSRLIN` followed by a separate `(0)` item.
2. **`POS(n)`** — parentheses **required**; bare `POS` is a `Syntax error`. The
   argument is parsed and **discarded**. Returns the 0-based cursor column.
3. **`TAB(n)`** — `PRINT`-only, **absolute** 0-based column. If the cursor is
   already **at or past** `n`, do **nothing** — no move, no newline. Wraps
   modulo the text width.
4. **`SPC(n)`** — `PRINT`-only, **relative**: emit `n` spaces.
5. **Both:** float argument **truncates toward zero**; range **0..255**, outside
   → `Illegal function call`; `|n| > 32767` → `Overflow` (the int16 conversion
   fires first); a following separator behaves normally; a bare
   `PRINT TAB(10)` is legal; **used outside `PRINT` → `Syntax error`**, not a
   type error.
6. **Tokens** (from the sweep's own oracle-measured crunch capture):
   `CSRLIN` `$E8`, `POS` `$FF $91`, `SPC(` `$DF`, `TAB(` `$DB`.

Clause 3 is the one to be careful with — it is the behaviour a value-shaped test
cannot see, and the obvious implementation ("pad to column n") gets it wrong by
emitting a newline when already past.

Clause 5's truncation is **not new work**: it is the existing
`fac_to_int_strict` operand protocol, the same one the logical operators use.

## 3. Placement — where the bytes go

Per the [decision doc](decision-kwgaps-slicing.md) §2, the only scarce resource
is **main-ROM dispatch glue**; leaf compute is a sub-ROM tenant and kwtable rows
are sub-ROM. Current headroom: **page-1 498 B**, low region 7 B, `sub.rom` ~4 KB.

`TAB(` and `SPC(` are **`PRINT`-item dispatch**, not expression factors — they
hang off `exp_loop`, alongside the existing `cp '"'` / `cp PEEK_PREFIX` arms,
*not* off the `$FF` function table. `POS` is an ordinary `$FF` function and
`CSRLIN` a single-token factor, so both go through the existing factor paths.

Estimated main-ROM cost (from the decision doc, **not yet spiked**):
`CSRLIN` ~13 B, `POS` ~18 B, `SPC(` ~20 B, `TAB(` ~28 B ≈ **79 B**, plus ~12 B
of kwtable in sub.rom. Comfortable against 498 B — this slice needs no funding,
which is the first time that has been true in this arc.

⚠️ These are **estimates**, and this repo's estimates have run optimistic often
enough that the decision doc requires each slice to open with a **measured
spike**. That is the first implementation step, not an afterthought.

### 3.1 What the cursor position is read from

The reference maintains the cursor in the BIOS work area, and C-BIOS maintains
the same cells, so `CSRLIN`/`POS` are reads of `CSRY`/`CSRX` (`$F3DC`/`$F3DD`),
each minus 1 — the BIOS cells are 1-based, the BASIC values 0-based. This is a
published BIOS contract, not disassembly. `TAB(`/`SPC(` need the current column
(the same cell) and the text width (`LINLEN`).

## 4. Gating

New `make cursor-acceptance` — the characterization probe with `--gate`, which
promotes all four to "implemented" and turns every row into a two-sided
differential. The probe already exists and every row is already written and
measured; today they run reference-only.

**Falsification is required before the gate is believed** — for each of the four
independently, per the standing lesson that a green gate can be measuring
nothing. Clause 3 in particular gets its own falsification: break *only* the
already-past case and confirm the gate reddens.

Regression suites to re-run, because `exp_loop` and the `$FF` factor path are
shared: `string-acceptance`, `error-acceptance`, `printusing`, `direct-ctrl`,
plus `logicops-acceptance` (its battery 6 lives in `exp_loop`).

## 5. Risks

* **`exp_loop` is hot and already dense.** The `EQV`/`IMP` follow-on just added
  `exps_notrel` there; two more item-dispatch arms want care, and the lean cart
  must stay byte-frozen (all four are repack-only).
* **`TAB(`/`SPC(` are the first `PRINT`-only tokens.** Every other keyword is
  legal in an expression, so "syntax error anywhere else" is a *new* shape —
  and the natural implementation (a factor that errors unless a PRINT flag is
  set) is exactly the sort of hidden global the interrupt-trap arc kept getting
  bitten by. Prefer dispatch placement over a mode flag.
* **D-CUR-1 changes existing `PRINT` output.** Any gate that prints
  comma-separated items at the third zone may shift. That is a feature — it is
  a faithfulness fix — but it is why it is a separate decision.

## 6. Decisions — sign-off needed

**D-CUR-A — implement all four in one slice?** Recommend **yes**. They share one
probe, one gate and one measurement session, and together they take the
SILENT-GAP class from 6 to 2. Splitting them multiplies the fixed cost (spec,
gate, spike) without reducing risk.

**D-CUR-B — fix D-CUR-1 (the comma-zone rule) in this slice?** Recommend **yes**.
It is `print_comma_zone`, the routine `SPC(` shares `pcz_pad` with, so the code
is open on the bench anyway; the rule is precisely measured
(`zone_start + 14 <= width`, boundary confirmed at `WIDTH` 28 vs 27); and it is
a handful of bytes. The argument against is blast radius — it changes existing
`PRINT` output — which is why it is asked rather than assumed.

**D-CUR-C — what about D-CUR-2 (boot width 37 vs 39)?** Recommend **separate,
and not next**. It is console init, not a keyword or a `PRINT` routine, and
changing the boot width shifts the expected output of *every* screen-scraping
gate in the tree. It wants its own slice with its own re-pin of the affected
corpora, and it should not ride along inside a keyword slice.
