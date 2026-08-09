# D-EVALCHK — which of two PENDING errors an int-argument site reports

Measured 2026-08-09 against **two** references — a diskless Philips VG-8020 and
a National CF-3300 — with
[`basic_probe_width.py`](../probes/basic/basic_probe_width.py) at
`--sides vg8020,cf3300,zb`, zerobas at `65171d6` (`basic-reloc.rom f9d427e0…`).
Clean-room: observed screen output only; both reference ROMs are black boxes.

`make width-characterize` re-measures; `make width-acceptance` gates.

---

## 1. The question this battery exists to answer

D-WID (2026-07) characterised **which `n` `WIDTH` accepts**: 79 rows over four
screen modes, the coercion boundary, the syntax surface and the per-mode
default. It never asked what happens when the argument expression has
**already faulted** — and that turns out to be a different rule with its own
answer.

Two errors can be pending at once at any checked-coercion argument site:

* the one the **expression** left behind (`FPERR` from `1/0` or `SQR(-1)`,
  `TMISMATCH` from a string comparison) — deferred to the statement boundary by
  design (the error-handling arc's D-2/D-F2-1 pattern);
* the one the **coercion** raises (`fac_to_int_strict` sets `FPERR=1` when the
  magnitude leaves int16).

They are written to the **same byte**. Which one the reference reports is
therefore not deducible from either rule alone, and no row with a single fault
in it can say.

---

## 2. The rule, as measured

> 🎯 **THE EXPRESSION'S ERROR OUTRANKS THE COERCION'S.** When a deferred fault
> and an out-of-int16 value arrive together, both references report the
> **deferred** one — whichever class it is.

| # | program | VG-8020 | CF-3300 | zerobas | |
|---|---|---|---|---|---|
| 1 | `WIDTH 1/0` | ERR **11** | ERR **11** | ERR 11 | 🟢 |
| 2 | `WIDTH 1+0*(1/0)` | ERR **11** | ERR **11** | ERR 11 | 🟢 |
| 3 | `WIDTH SQR(-1)` | ERR **5** | ERR **5** | ERR 5 | 🟢 |
| 4 | `WIDTH 70000` | ERR **6** | ERR **6** | ERR 6 | 🟢 |
| 5 | **`WIDTH 70000+0*(1/0)`** | ERR **11** | ERR **11** | **ERR 6** | 🔴 |
| 6 | **`WIDTH 70000+0*SQR(-1)`** | ERR **5** | ERR **5** | **ERR 6** | 🔴 |
| 7 | `A$="X":WIDTH (A$<5)+0*(1/0)` | ERR **13** | ERR **13** | ERR 13 | 🟢 |
| 8 | **`CLEAR 70000+0*(1/0)`** | ERR **11** | ERR **11** | **ERR 6** | 🔴 |
| 9 | **`LOCATE 70000+0*(1/0),1`** | ERR **11** | ERR **11** | **ERR 6** | 🔴 |

ERR 5 `Illegal function call` · 6 `Overflow` · 11 `Division by zero` ·
13 `Type mismatch`.

**Rows 5 and 6 together are the rule.** Had only row 5 been measured, "division
by zero is special" would fit the data exactly as well; row 6 answers a
**different code** from the same shape, so the rule is *"the expression's
error"* and not *"ERR 11 wins"*. Row 7 adds the third class and fixes the order
**inside** the deferred pair: a pending `TMISMATCH` beats a pending `FPERR`.

**Rows 1–4 are what makes rows 5–6 legible.** Each is the same statement with
exactly one of the two clauses removed: rows 1–3 the fault with no overflow,
row 4 the overflow with no fault. Without them, `ERR 6` on row 5 has three
explanations rather than one.

⚠️ **EVERY VALUE LEAVES THE BOUND IT IS SUPPOSED TO LEAVE, CHECKED RATHER THAN
ASSUMED** ([[a-rule-can-claim-more-than-its-evidence]] — D-LPTVERB's R-LS4 was
filed with "out-of-byte" evidence that was *in* byte range): `70000 > 32767`
leaves int16, and `0*(1/0)` / `0*SQR(-1)` contribute a fault while contributing
**zero** to the value, so the two clauses are independently controlled. The
control for the *expression shape itself* is `WIDTH 30+0*1` → accepted at 30.

---

## 3. Where zerobas differs, and why

[`get_int16_checked`](../basic/interp.asm:1516) is `push hl` /
`call fac_to_int_strict` / `pop hl` / `jp check_fperr_only`.

* `fac_to_int_strict` **does not clear `FPERR`** on entry, so a deferred fault
  from `eval` survives the coercion and `check_fperr_only` surfaces it. That is
  why rows 1–3 already agree, at all three sites, with no post-`eval` check in
  the handler at all.
* `fac_to_int_strict` **does write `FPERR=1`** when the magnitude leaves int16 —
  **over the top of** the pending `FPERR=2`/`FPERR=3`. That is rows 5, 6, 8, 9:
  zerobas reports whichever fault was written **last**, the references report
  whichever happened **first**.

The three handlers that carry the divergence each test `TMISMATCH` inline and
then coerce; the fix is to run the shared
[`check_expr_errors`](../basic/interp.asm:1297) — which tests **both** flags —
**before** the coercion. `basic/field.asm`'s `exf_item` already does exactly
that (D-FLDWIDTH), which is why `FIELD` is the one site with no divergence here
and is this rule's positive control in the source.

---

## 4. The full matrix — 94 rows, three sides, `65171d6`

`91/94` agree. Nine positive controls green on **both** references, **zero rows
where the two references disagree**, seven rows with one reference only (the
`unt` battery, which reads the raw screen tail and so is VG-8020 + zb by
design).

The three divergences are rows 5, 6 and 8 above (`dfe-ovfdiv`, `dfe-ovfsqr`,
`cl-ovfdiv`). **Everything else in the matrix — the whole of D-WID's domain,
coercion, syntax and persistence surface, and the six other new rows — agrees on
all three machines.** That is the shape a *narrow* rule leaves behind, and it is
what makes the three red rows readable as one clause rather than as a verb being
generally wrong.

### 4.1 The batteries

| battery | rows | what it holds fixed |
|---|---|---|
| `ctl` | 9 | the apparatus: the pinned no-op readout in two modes, three trapped error codes, the restore, and 🔴 **the two deferred fault classes on their own** (`X=1/0` → 11, `X=SQR(-1)` → 5) — added by D-EVALCHK so that a reading of ERR 5 on row 6 cannot be blamed on the readout |
| `s0` `s1` `s2` | 35 | D-WID's domain matrix, unchanged |
| `co` | 15 | D-WID's coercion boundary, unchanged |
| `sx` | 8 | D-WID's syntax surface, unchanged |
| `pe` | 4 | D-WID's per-mode default, unchanged |
| **`dfe`** | **9** | **the rule** (rows 1–7) plus the two shape controls |
| **`cl`** | **7** | **the rule at its second site** — and `CLEAR`'s two coercion stages, so a fix that narrowed them would be caught |
| `unt` | 7 | the untrapped seam: what the user actually sees |

### 4.2 The readout

`[ ERR LINLEN LINL40 LINL32 ]` for every row except the `cl` battery, which
reads `[ ERR ]`.

🔴 **THE SYSVARS ARE PART OF THE READING, NOT DECORATION.** *"Did it raise?"* and
*"did it write the width anyway?"* are different questions, and an
implementation that gets the first right and the second wrong still destroys the
display. Reading them **before** the restore is what makes a reject's
side-effects visible; every row in §2 also asserts `40 40 32`, i.e. that the
rejected `WIDTH` scribbled on nothing.

🔴 **`CLEAR` CANNOT USE THAT FIXTURE.** A `CLEAR` that succeeds wipes every
variable, so the four captured numbers would read back as zeros and every
accepting row would report a fault that never happened. The `cl` rows use a
trapped-`ERR`-only program instead — sound precisely because `CLEAR` touches
none of the three width sysvars, so there is nothing else to read.

### 4.3 The instrument is pinned on every row

The machines boot at different text widths (VG-8020 37, zerobas 39), and
`WIDTH` is the one statement whose job is to change the stride the screen scrape
depends on. Lines 10–20 of every program set `SCREEN 1:WIDTH 32` then
`SCREEN 0:WIDTH 40`, so `LINL40`/`LINL32` are known constants on all three sides
and every reject row has a **known prior `LINLEN`**. D-WID's own §note records
that without the pin, three control rows executing no `WIDTH` at all diverged on
boot width alone while their `ERR` codes agreed.

---

## 5. The denominator

**(WHICH deferred fault:** a `1/0` → ERR 11, a `SQR(-1)` → ERR 5, a string
comparison → ERR 13, each carried into the expression by a `0*` term that
contributes the fault and **not** the value**) × (AGAINST WHAT:** nothing, an
int16 overflow, or another deferred fault**) × (AT WHICH SITE:** `WIDTH`'s
`get_byte_arg`, `CLEAR`'s `get_int16_checked`, and — measured, declined —
`LOCATE`'s written-out copy**) × (WITH WHICH CONTROL:** the same value with the
fault removed, the same expression *shape* with the fault removed, each
coercion's two stages, and the fault classes measured standing alone in a
non-argument position**)**, embedded in D-WID's existing 79-row domain matrix so
that a fix which moved the DOMAIN while fixing the ORDER cannot pass.

**NOT COVERED, named rather than implied:**

* `WIDTH LPRINT n` — the printer-channel form of `WIDTH`, not implemented and
  not measured.
* The **UNWIND** — whether the abort returns to the right depth. Owned by
  `make abort-acceptance`; this battery arms `ON ERROR` on purpose, which hides
  it, and the `unt` rows are the seam.
* `CLEAR`'s **pool semantics** — D-CLP, `basic_probe_clearpool.py`. Only the
  deferred-error ORDER is measured here.
* A `LEN=` record length — D-FLDWIDTH §6.5's residual.
* `LOCATE`'s own argument surface (row/column, omitted arguments, the
  `CON_LASTROW` clamp, `CSRLIN`/`POS` read-back) — which is exactly why row 9 is
  filed as a residual rather than fixed here.
* Message **WORDING** — D-MSGEXACT's surface; the readout is a numeric `ERR`.

---

## 6. Provenance

Statement semantics from the public MSX-BASIC language reference; `LINLEN`
`$F3B0`, `LINL40` `$F3AE`, `LINL32` `$F3AF` are published MSX system variables
(MSX2 Technical Handbook), already carried in
[`basic/sysvars.inc`](../basic/sysvars.inc). Every reading above is a screen
observation of a stock machine running a typed program. No disassembly.
