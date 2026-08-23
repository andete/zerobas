<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-PAINTMISS — PAINT's dangling comma fills the region and reports nothing

Status: **✅ SHIPPED. 3 B of main page 1** (free **4 → 1 B**, both read from a
clean `make basic-reloc` on 2026-08-23), on `5fe49d3`.
`basic-reloc.rom` `abfefa7f → 59f0a082`, merged `a8173c25 → 5ea13c71`,
`sub.rom` **unchanged** `490ffc49` — the right signature for a `basic/*.asm`
edit and the exact opposite of [D-CIRCMISS](spec-basic-circmiss.md)'s.

The second half of the pair [D-CLRTRAP](spec-basic-clrtrap.md) §2 measured and
could not afford. Mechanism **2** of the three that
[D-MISSOPFIX](spec-basic-missopfix.md) §11.1 separated: *the verb's own grammar
swallows the dangling comma before `eval` is ever reached*, so the resident
evaluator's deferred ERR 24 never sees it.

---

## 1. The defect, in one line of BASIC

    10 SCREEN2 : LINE(40,40)-(60,60),15,B
    20 PAINT(50,50),

**VG-8020 and CF-3300:** `Missing operand in 20`, and **nothing is filled.**
**zerobas before:** the statement completes, ERR 0, and **the box is full.**

Six shapes, one rule. Both optional slots, both terminators, and the B slot by
both of the two routes that reach it.

## 2. The site — a SHARED TAIL with six jumps, of which four mean this

`basic/graphics.asm`, `ex_paint`'s grammar walk. `ep_default_b` (*"no `,B` → B =
C"*) is reached by **six jump instructions**, enumerated as INSTRUCTIONS and not
by grepping the symbol ([[a-shared-tail-is-not-a-decision]]):

    grep -rnE '^[ \t]+(jp|jr|call)[ \t]+(z,|nz,|c,|nc,)?ep_default_b'

| line (pre-fix) | instruction | reached | verdict |
|---|---|---|---|
| `:701` | `jr nz,ep_default_b` | no comma at all | ✅ **LEGITIMATE** |
| `:707` | `jr z,ep_default_b` | after the C comma, end of line | 🔴 dangling |
| `:709` | `jr z,ep_default_b` | after the C comma, `:` | 🔴 dangling |
| `:718` | `jr nz,ep_default_b` | C given, no `,B` | ✅ **LEGITIMATE** |
| `:726` | `jr z,ep_default_b` | in `ep_parse_b`, end of line | 🔴 dangling |
| `:728` | `jr z,ep_default_b` | in `ep_parse_b`, `:` | 🔴 dangling |

**The property that separates them is not the slot and not the terminator — it
is whether a comma has already been consumed.** Four have; two have not. Putting
the raiser on `ep_default_b` itself would have served all six and broken
`PAINT(50,50)`.

⚠️ **And NOT the `cp ','` arm three lines below `:728`.** A *third* comma there
is a fourth argument and is **ERR 2**, measured by D-PAINTBORD's `od2.b16c` /
`od3.b15c`. Shape is not a verdict: D-LINERR measured LINE's colour slot as 24
and LINE's *box* slot — one field along in the same statement — as 2.

## 3. ✅ As built — 3 B, and the estimate was exact

    ep_missing:
                    jp      loc_missing         ; ERR 24 (Missing operand)   3 B
    ep_default_b:

plus **four `jr z,ep_default_b` retargeted to `jr z,ep_missing` — 0 B, same
instruction**, exactly as D-CIRCMISS retargeted eight `jp z,`.

💰 **A trampoline, not an inline raiser.** All four sites are `jr`s and
`loc_missing` is ~600 source lines away, far outside `jr` reach; an inline
`ld a,24 / jp raise_error` is **5 B**, and four `jp z,loc_missing` in place of
four `jr z,` is **+4 B**. The 3 B trampoline is the cheapest of the three, which
is what made this fit at all: **main page 1 had 4 B free.**

🎯 **`loc_missing` already existed and is exactly the label needed** — the same
one `wid_missing` (`basic/screen.asm`) forwards to. Nothing new was written.
Placement is immediately after `jr ep_draw`, an unconditional jump, so
`ep_missing` cannot be fallen into.

## 4. The measurement — 16 rows × 3 machines, boot-per-case

`scratchpad/circmiss_sib2.py`, unchanged from D-CLRTRAP so the reference columns
are a control on the instrument as well as a want. Readout `[ERR R]` with
`R = POINT(50,50)`, the paint seed: **4 = nothing filled, 15 = filled.**
Before: `scratchpad/circmiss_sib2.out`. After: `scratchpad/paintmiss_after.out`.

| row | statement | refs | zb BEFORE | zb AFTER | |
|---|---|---|---|---|---|
| `p.colour`  | `PAINT(50,50),`        | `24 4` | `0 15` | `24 4` | ✅ closed |
| `p.kcolour` | `PAINT(50,50),:A=1`    | `24 4` | `0 15` | `24 4` | ✅ closed |
| `p.b`       | `PAINT(50,50),15,`     | `24 4` | `0 15` | `24 4` | ✅ closed |
| `p.kb`      | `PAINT(50,50),15,:A=1` | `24 4` | `0 15` | `24 4` | ✅ closed |
| `p.cc`      | `PAINT(50,50),,`       | `24 4` | `0 15` | `24 4` | ✅ closed |
| `p.kcc`     | `PAINT(50,50),,:A=1`   | `24 4` | `0 15` | `24 4` | ✅ closed |
| `p.none`    | `PAINT(50,50)`         | `0 15` | `0 15` | `0 15` | ✅ trap, UNMOVED |
| `p.omit`    | `PAINT(50,50),,15`     | `0 15` | `0 15` | `0 15` | ✅ trap, UNMOVED |
| `p.plain`   | `PAINT(50,50),15`      | `0 15` | `0 15` | `0 15` | ✅ control |
| `p.ok`      | `PAINT(50,50),15,15`   | `0 15` | `0 15` | `0 15` | ✅ control |

**6 DIFF → 0. All ten PAINT rows unanimous on all three machines.** The three
remaining DIFFs in the 16-row set (`q.trail`, `q.kcolon`, `q.comma`) are CLEAR's,
in `basic/clear.asm`, untouched by this slice and still filed in `TODO.md`.

⚠️ **The instrument's own hazard, inherited and still load-bearing:** PAINT's
border defaults to the FILL colour, so a stop-box in 15 with a fill in 5 never
terminates — and it hangs only on the machine that HAS the defect, which reads
as apparatus debt on one side. Every row above fills with the SAME colour as its
box. See [D-CLRTRAP](spec-basic-clrtrap.md) §1.

## 5. 🔬 Knives — 6 of 6 EXACT, and three of them are the trap

`scratchpad/paintmiss_knives.py`, `scratchpad/paintmiss_knives.out`. Six
size-neutral cuts, each with a row set predicted before the run
(`scratchpad/paintmiss_predictions.md`). Every knife re-checks that
`basic-reloc.rom` **and** the merged image moved and that `sub.rom` did **not**.

| knife | cut | predicted | moved |
|---|---|---|---|
| K-PM1 | `:701` (no comma at all) → `ep_missing` | `p.none` → `24 4` | **1, exactly `p.none`** ✅ |
| K-PM2 | `:718` (no `,B`) → `ep_missing` | `p.plain` → `24 4` | **1, exactly `p.plain`** ✅ |
| K-PM3 | the C slot's end-of-line arm back to `ep_default_b` | `p.colour` → `0 15` | **1, exactly `p.colour`** ✅ |
| K-PM4 | the B slot's end-of-line arm back to `ep_default_b` | `p.b` **and** `p.cc` → `0 15` | **2, exactly `p.b` + `p.cc`** ✅ |
| K-PM5 | `ep_c_empty`'s `inc hl` → `nop` | `p.cc`/`p.kcc`/`p.omit` → `2 4` | **3, exactly those** ✅ |
| K-PM6 | `ep_missing`'s `jp loc_missing` → `jp gfx_err5` | all six → `5 4` | **6, all `5 4`** ✅ |

### 5.1 What each one establishes

* **K-PM1 / K-PM2 are the point of the slice.** The design question was never
  *"does ERR 24 come out"* — the differential answers that. It was *"does the
  fix leave the LEGITIMATE omission alone"*. Each of these points **one** of
  `ep_default_b`'s two surviving jumps at the new raiser and reddens **exactly
  one** green row. That is what makes `p.none` and `p.plain` detectors rather
  than decoration [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
* **K-PM4 measures the two-routes claim.** One instruction reverted, and **two**
  rows move — `p.b` arriving through the comma that ends a given C, `p.cc`
  through `ep_c_empty`'s shared comma. Static reachability said so; this is the
  dynamic proof.
* **K-PM5 is the only knife that reddens `p.omit`.** 🔴 **And its first draft
  could not have existed.** The obvious cut — point `jr z,ep_c_empty` at
  `ep_missing` — orphans the `ep_c_empty` label, which fails `make deadcode` and
  therefore **builds no ROM at all**: a knife that cannot be run. Cutting the
  *value* instead (`inc hl` → `nop`, both 1 B) leaves the shared comma
  unconsumed, so `ep_parse_b` reads it as a fourth argument and answers ERR 2.
  **Cut a VALUE, not a CALL** — and a jump whose removal orphans a label is a
  call for this purpose.
* **K-PM6** re-creates the fix with the WRONG CODE and predicts that the
  **picture is still protected**: `R` stays 4 on all six. The raiser's identity
  and the raiser's position are two separate claims, and only this one tests the
  first.
* **K-PM3** re-creates the defect at exactly one of its four sites and moves
  exactly one row — the narrowness of a single `jr`, not of the fix as a whole.

## 6. What this does NOT establish

* **`CLEAR` is untouched.** `CLEAR 200,` still raises the right error, loses the
  `ON ERROR` trap, and writes `HIMEM = 0`; `CLEAR ,200` still completes where
  both references answer ERR 2. Both stay filed.
* **The 4th-argument ordering is untouched.** `PAINT(10,10),9,15,` raises ERR 2
  on all three, but the references **fill first and raise after**; zerobas
  raises without filling. Both sides answer 2, so only a drawn-pixel column sees
  it — the same shape as CIRCLE's `x.extra2`. Pre-existing, still filed.
* **The scan that found this ranks candidates and does not judge them.**
  `basic/screen.asm`'s three `clr_apply` sites have the identical shape and are
  **correct** (`COLOR 15,` completes on all three references, D-MISSOP §5).
  No slot inherits a verdict; the six here were RUN.
* **`p.omit`'s route is pinned by one knife only.** K-PM5 reddens it through a
  *different* mechanism (ERR 2, not ERR 24); nothing points `ep_c_empty`'s own
  route at the raiser, because nothing size-neutral can.

## 7. Gates — 35 of 35 green

`scratchpad/paintmiss_gates.sh`, `scratchpad/paintmiss_gates.out`, from
`rm -rf build`. ⚠️ **`repack-machine` is FIRST on purpose**: `latch-check`
(Makefile:2498) is the one gate with no prerequisites and refuses on an empty
`build/`, which makes `make` exit 2.

    GATES: 35 green, 0 red -- 35 run
    build/basic-reloc.rom 59f0a082 / build/sub.rom 490ffc49
    build/zerobas-main-eu.rom 5ea13c71

The denominators were read, not assumed: `lineerr-acceptance` **210 printed,
210 scored, 0 diverge** — the gate that caught D-MISSOPFIX's shared-tail
regression, and the one with a structural sweep of *every slot that can END
where a value was required*; `deadcode` **0 dead spans in either build**, both
allowlist entries still verified dead; `graphics-acceptance` (which owns PAINT's
drawing corpus) PASS; `kwsweep` unchanged at DIVERGENT=1 (the pre-existing
`inputdol` blocking row).

`wall-assertion-check`, `rowshape-check` and `audit-citations` were re-run
AFTER this document and `TODO.md` were written, because the battery had passed
them before those edits landed. All three green; the wall gate reads
**page-1 free = 1 B** live and finds no undated free-space assertion among the
99 open items.
