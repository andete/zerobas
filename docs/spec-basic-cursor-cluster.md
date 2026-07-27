<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — the cursor / `PRINT` cluster: `CSRLIN`, `POS`, `TAB(`, `SPC(`

**Status:** ✅ **LANDED 2026-07-27** — D-CUR-A/B/C all signed off (§6).
`make cursor-acceptance` **67/67**. Step 2 of [`decision-kwgaps-slicing.md`](decision-kwgaps-slicing.md)
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

Estimated main-ROM cost (decision doc): `CSRLIN` ~13 B, `POS` ~18 B, `SPC(`
~20 B, `TAB(` ~28 B ≈ **79 B**.

⚠️ **Measured: 109 B.** The estimate was optimistic by 38%, which is exactly why
the decision doc requires a spike. Page-1 free **498 B → 389 B** from clean; low
region unchanged at 7 B; sub.rom kwtable 925 → 955 B; lean cart byte-identical.
Still comfortable — this remains the first slice in the arc that needed no
funding — but the estimate was not the number.

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

**Falsified, five ways, each independently.** The first three rows were measured
against the 63-row gate, the last two against the 67-row gate after it was
strengthened — see below for why it needed strengthening.

| break | gate | intact |
|---|---|---|
| `CSRLIN` loses its 1-based→0-based `dec` | 57 | /63 |
| `POS` loses its `dec` | 55 | /63 |
| comma-zone fit test removed (pad always) | 56 | /63 |
| `TAB(` emits a newline when already past | 62 → **64** | /63 → /67 |
| `SPC(` treated as absolute like `TAB(` | 62 → **64** | /63 → /67 |

The last two are the point of doing this at all. At **62/63** they each moved
exactly *one* row: both clauses only become visible when the cursor is somewhere
other than column 0, and almost every row in the battery starts at column 0.
Four rows were added that put the cursor elsewhere first, and each clause now has
three guards. **A clause guarded by one row is one edit away from being
unguarded** — and falsification is what surfaced that, not review.

Regression suites, all green — chosen because `exp_loop` and the `$FF` factor
path are shared: `logicops-acceptance` **193/193** (its battery 6 lives in
`exp_loop`), `direct-ctrl-acceptance` **40/40**, `string-acceptance` PASS,
`error-acceptance` ALL PASS, `intarg-acceptance` ALL PASS,
`basic_probe_printusing` PASS.

## 4.1 D-CUR-3 — found during the gate, pre-existing, NOT fixed here

`PRINT TAB(-1)` gives the right error and then a spurious second one. The cause
is not in this slice: **an error raised mid-statement does not abort the
statement.** `fre_abort_low` sets `ENDFLAG` and *returns*; the unwind only
happens at the next statement boundary, so the `PRINT` item loop carries on.

The controls prove it is pre-existing — they use functions this slice never
touched:

| | reference | zerobas |
|---|---|---|
| `PRINT VPEEK(-1);"Z"` | `Illegal function call` | `Illegal function call` then ` 32 Z` |
| `PRINT STICK(9);"Z"` | `Illegal function call` | `Illegal function call` then ` 0 Z` |
| `PRINT TAB(-1);"Z"` | `Illegal function call` | `Illegal function call` then `syntax error` |

One defect, three symptoms — they differ only in where the cursor is left. It
belongs to the error-handling arc (the abort mechanism), not to a keyword slice,
and it wants its own decision. The rows are **reported and never gated**, with
the two `ctl-*` controls beside them so the record cannot be misread as a
`TAB(`/`SPC(` problem.

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

## 6. Decisions — all signed off 2026-07-27

**D-CUR-A — implement all four in one slice?** ✅ **yes.** Done; the SILENT-GAP
class is now **2** (`FRE`, `BIN$`).

**D-CUR-B — fix D-CUR-1 (the comma-zone rule) here?** ✅ **yes.** Done, repack-
gated: `next_zone + 14 <= width` or wrap.

**D-CUR-C — D-CUR-2 (boot width 37 vs 39)?** ✅ **separate, and not next.**

**D-CUR-D (new) — D-CUR-3, the mid-statement abort?** Its own slice, in the
error-handling arc. See §4.1; it is a general abort-mechanism defect that this
slice merely surfaced, and its controls are already in the probe.

## 7. Implementation notes worth keeping

* **`TAB(`/`SPC(` are `PRINT`-item dispatch, and `ev_f` never learns about
  them.** That is what makes `X=TAB(5)` and `IF TAB(5)=0` a `Syntax error` — the
  token falls off the end of `ev_f`'s chain into `ev_f_err` — with *no code at
  all*. The alternative (a "PRINT mode" flag consulted by a factor) buys the
  same behaviour and a hidden global with it.
* **`POS` cost one table byte.** The `$FF` one-numeric-argument set is already
  `cpir`-driven, so joining it is `db POS_TOKEN`; and because the argument is
  discarded, it deliberately stays *out* of the `ev_ff_ck*` domain-check chain —
  `POS(-1)` must not raise.
* **The overrun that stopped the first build was in the LEAN cart**, from a
  single ungated `ld c,a` added above the repack gate in `print_comma_zone`.
  Everything else was correctly gated; one byte in a byte-frozen image is still
  a failure. `make build/basic.rom` on its own is the quickest way to tell which
  of the two images overran.
