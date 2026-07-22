# zerobas BASIC — graphics slice G8: `VDP(n)` and `BASE(n)`

Status: **SPEC — SIGN-OFF NEEDED** (2026-07-22). Arc spec:
[`spec-basic-graphics.md`](spec-basic-graphics.md). Predecessor slices G1–G7 all
landed; this is the VDP-register / table-base access pair, the last non-deferred
graphics item in [`../TODO.md`](../TODO.md).

Every `[PIN]` below is a measured black-box fact from the Philips VG-8020, with
the raw record and the probe scripts in
[`../scratchpad/g8_vdp_notes.md`](../scratchpad/g8_vdp_notes.md)
(`g8_vdp_char1.py` … `g8_vdp_char7.py`). No ROM disassembly
([memory: no-reference-rom-disasm]).

---

## 1. Scope

**In:** the `VDP(n)` pseudo-array (read and write) and the `BASE(n)` pseudo-array
(read and write). Four surfaces:

| surface | today |
|---|---|
| `A=VDP(n)` | does not exist (`VDP` is not a keyword) |
| `VDP(n)=v` | does not exist |
| `A=BASE(n)` | **descoped stub** — [`basic/expr.asm:1721`](../basic/expr.asm:1721) parses the argument, returns 0 and sets ERRMARK |
| `BASE(n)=v` | does not exist |

So G8 both adds three surfaces and **retires a documented divergence**: the
`BASE` stub was written when zerobas had no per-mode VDP table map. The graphics
arc has since pinned that map, and — the finding that makes this slice cheap —
**our runtime's work-area table already matches the reference byte for byte in
every mode** (§4.1), so `BASE(n)` becomes an honest word fetch rather than a
fabricated table.

**Out:** `SCREEN 3` (still deferred, arc-spec D4) and the sprite-collision trap
`ON SPRITE GOSUB` (belongs to the interrupt-trap item). G8 touches SCREEN 3 only
where the reference's own behaviour drags it in (§4.4, decision **D8-1**).

## 2. Tokens `[PIN]`

`VDP` = **$C8**, `BASE` = **$C9**, both single-byte function tokens — `BASE` is
already in the keyword table, `VDP` is a new row (repack-only, the PSET/CIRCLE
pattern). The assignment form has **no statement token of its own**: a statement
whose first token is `$C8`/`$C9` is an assignment.

```
A=VDP(0)        41 EF C8 28 11 29
VDP(1)=2        C8 28 12 29 EF 13
BASE(0)=&H1800  C9 28 11 29 EF 0C 00 18
```

That is the one structural demand G8 makes of the interpreter: `exec`'s
statement dispatch must recognise these two function tokens as the head of an
assignment, alongside the existing variable-assignment path.

## 3. Grammar and errors `[PIN]`

```
    VDP ( <numeric-expr> )                    -- function
    VDP ( <numeric-expr> ) = <numeric-expr>   -- statement
    BASE ( <numeric-expr> )                   -- function
    BASE ( <numeric-expr> ) = <numeric-expr>  -- statement
```

| form | result |
|---|---|
| `VDP(0)=VDP(0)`, `BASE(0)=BASE(0)` | OK (self-assignment is legal) |
| `A=1:VDP(0)=2:B=3`, `IF 1 THEN VDP(0)=2` | OK — an ordinary statement in any position |
| **`LET VDP(0)=2`**, `LET BASE(0)=…` | **ERR 2** — the `LET` form is rejected |
| `VDP(0)` as a statement, `VDP=1`, `BASE=1`, `VDP 0=1`, `A=VDP`, `A=VDP 0` | ERR 2 |
| `VDP(0,1)=2`, `VDP(0)=1,2` | ERR 2 |
| `FOR VDP(0)=0 TO 1`, `SWAP VDP(0),A` | ERR 2 |
| `VDP(0)=` | **ERR 24** (Missing operand) |
| `VDP(0)="A"`, `VDP("A")=1`, `BASE(0)="A"` | ERR 13 |

**Coercion `[PIN]`:** index and value both **truncate** toward zero, and the
domain check runs **after** truncation — `VDP(-0.4)` is index 0 (not ERR 5),
`VDP(0)=255.6` sets 255, `VDP(3.9)` reads register 3 — no rounding anywhere, and
a fractional value that truncates *into* the domain is accepted rather than
rejected. G8 must therefore call the truncating float→int conversion and
range-check afterwards; check which of the D-F2-2 helpers
([`spec-basic-df2-2-intarg-coercion.md`](spec-basic-df2-2-intarg-coercion.md))
already has that exact shape before adding another one.

## 4. Semantics

### 4.1 `BASE(n)` read `[PIN]`

`n` ∈ 0..19, else ERR 5. The result is the work-area word at `$F3B3 + 2n`, and
it is **mode-independent** — the whole table is readable from any screen mode.
Slot kind is `n mod 5`: 0 name, 1 colour, 2 pattern generator, 3 sprite
attribute, 4 sprite pattern generator; group `n \ 5` is the screen mode the slot
describes.

Power-on table, **identical on the VG-8020 and on our own
`C-BIOS_MSX1_EU_REPACK_DISK` build in SCREEN 0/1/2**:

```
BASE(0..4)    0000 0000 0800 0000 0000     group 0 -> SCREEN 0
BASE(5..9)    1800 2000 0000 1B00 3800     group 1 -> SCREEN 1
BASE(10..14)  1800 2000 0000 1B00 3800     group 2 -> SCREEN 2
BASE(15..19)  0800 0000 0000 1B00 3800     group 3 -> SCREEN 3
```

### 4.2 `VDP(n)` read `[PIN]`

* `n` ∈ 0..8, else ERR 5.
* `n` 0..7 → the RAM write-shadow at `$F3DF + n` (the TMS9918's registers are
  write-only; the shadow is what every MSX reads back).
* `n` = 8 → `STATFL` at `$F3E7`, the ISR's status copy — **not** a live port
  read.

### 4.3 `VDP(n)=v` write `[PIN]`

* `n` ∈ 0..7 (**`VDP(8)=` is ERR 5** — the status register is read-only),
  `v` ∈ 0..255 after truncation, else ERR 5.
* Updates the shadow **and the chip**: proven by clearing R1's interrupt-enable
  bit and watching `TIME` freeze (delta 0 against a control that advanced 62).
* Nothing else moves — no mode variable, no table.

### 4.4 `BASE(n)=v` write `[PIN]` — including the reference's off-by-one

1. Validate `n` ∈ 0..19 (else ERR 5), then validate `v`: `0 <= v < $4000` **and**
   `v` a multiple of the slot's grain, else ERR 5.

   | slot kind | grain | exception |
   |---|---|---|
   | name | $400 | — |
   | colour | $80 | **group 2: $2000** |
   | pattern generator | $800 | **group 2: $2000** |
   | sprite attribute | $80 | — |
   | sprite pattern generator | $800 | — |

   The check follows the **slot's group, not the current mode**: `BASE(11)=&H0400`
   fails even when issued from SCREEN 0.

2. Store the word at `$F3B3 + 2n`.

3. Reprogram the VDP **only if the slot's group equals `SCRMOD`** (a cross-group
   write stores and stops — no register moves). And the reprogram itself is the
   crux pin:

   | current mode | measured effect |
   |---|---|
   | SCREEN 0 | writes exactly the register the slot owns, `= v / grain` (`BASE(3)=&H1F00` → R5=$3E) |
   | SCREEN 3 | same — correct single-register update |
   | **SCREEN 1** | ignores the written slot's register; programs the chip from **group 2's** five table words + SCREEN 2's mode bits |
   | **SCREEN 2** | ignores it likewise; programs the chip from **group 3's** words + SCREEN 3's (multicolor) mode bits |

   `SCRMOD` does **not** change: the mode variable stays put while the chip is
   left configured one mode along. A subsequent plain `SCREEN` puts everything
   right, so only this immediate-reprogram path is off by one group.

   This is not inferred from defaults that happen to coincide — it is
   poison-tested: with `BASE(13)` pre-set to `&H0400` from SCREEN 0, a
   `BASE(8)=&H1F00` write in SCREEN 1 leaves `R5=$08`, the poisoned **group-2**
   value, not `$3E` from the value just written. Same shape for SCREEN 2 reading
   group 3.

   Mode bits needed to reproduce it (measured): mode 2 → `R0=$02, R1=$E0`;
   mode 3 → `R0=$00, R1=$E8`.

## 5. Placement

Follow the arc's established split (arc-spec D1/D5): **the engine joins the
page-0 graphics tenant, the resident half stays thin.**

* **Tenant** ([`sub/graphics.asm`](../sub/graphics.asm)), two new selectors —
  `GFX_OP=13` (VDP read/write) and `GFX_OP=14` (BASE read/write): the grain
  table, the validation, the work-area store, and the register programming
  (direct VDP port I/O, which the tenant already owns and the resident does not).
  Work-area RAM is page 3, visible to a page-0 tenant, so no marshalling of the
  table itself is needed.
* **Resident** ([`basic/graphics.asm`](../basic/graphics.asm)): parse `(n)`,
  optionally `= v`, truncate-coerce both, marshal through the existing
  `GFX_*` block, one `subrom_call`. Plus the `exec` dispatch arm for a statement
  beginning with `$C8`/`$C9`, and the `ev_f_vdp` / rewritten `ev_f_base` arms in
  `ev_f`'s function-token chain.

Rationale: the resident page-1 tail has **9 bytes** free
(`__MEAS_PAGE1_END = $7FF7`), so every byte kept out of page 1 is a byte the
eviction does not have to find.

## 6. Space

Estimate (to be **measured, not assumed** — the arc's standing lesson — by
assembling the resident half before the tenant is wired):

| part | est. |
|---|---|
| `ev_f_vdp` + rewritten `ev_f_base` | +60 B, −55 B reclaimed from the descoped stub |
| assignment dispatch arm (two tokens) | +25 B |
| `ex_vdpassign` / `ex_baseassign` parse + marshal | +110 B |
| `VDP` keyword-table row | +6 B |
| **resident net** | **≈ +145 B** |
| tenant `GFX_OP` 13/14 | ≈ +180 B (sub-ROM, not scarce) |

Against 9 B free that needs a carve of ~140 B. The
[`g7_carve_scout.py`](../scratchpad/g7_carve_scout.py) shortlist (the automated
tenancy rule from G6 §8) currently offers, page-0 tenant CLEAN and single-entry:
`psv_fetch` 130 B, `ev_ff_lof` 151 B, `ev_ff_eof` 162 B, `exec` 362 B — the
first three all being small, self-contained leaves. Pick at implementation time
against the freshly measured deficit; if the measured resident half lands under
~100 B after DRY, a single leaf carve covers it.

## 7. Gate

Extend `make graphics-acceptance` with **Phase Q** (`VDP`/`BASE`), a VG-8020
differential over: the `BASE(n)` table in each mode; `VDP(n)` reads;
`VDP(n)=` shadow + chip effect (the `TIME`-freeze probe is the chip half, and it
is the teeth check — a shadow-only implementation passes every read assertion and
fails this one); the `BASE(n)=` value domain per slot kind; the cross-group
store-only rule; and the errors of §3. Host unit tests in
[`../tests/test_graphics.py`](../tests/test_graphics.py) for the pure leaves
(grain lookup, validation, register/divisor mapping).

**Known-divergent, excluded from assertion (`G8-regdelta`, documented):** C-BIOS
programs R3/R5 differently in SCREEN 0 and R7 differently in SCREEN 1, so
`VDP(3)`, `VDP(5)`, `VDP(7)` read back different values there. This is a
BIOS-level difference below the BASIC statement; SCREEN 2 agrees exactly. The
gate asserts the registers G8 itself writes, plus all of SCREEN 2.

## 8. Open decisions — SIGN-OFF NEEDED

| # | Decision | Recommendation |
|---|---|---|
| **D8-1** | Reproduce the SCREEN-1/2 off-by-one reprogram (§4.4)? | **Yes — reproduce it.** It is measured, it is cheap (a uniform "program 7 registers from group g+1" loop is *simpler* than a per-slot special case), and it is exactly the kind of quirk a period program could depend on. The alternative — correct single-register update in all four modes — would be a third documented deviation of the [[bug-for-bug-compat-over-accuracy]] class, taken for no space saving. |
| **D8-2** | The group-3 (SCREEN 3) slots, with no SCREEN 3 on our side | **Accept as measured**: validate and store `BASE(15..19)=`. `SCRMOD` is never 3 on our runtime, so the reprogram arm is simply unreachable — except as the *source* group when a SCREEN-2 write triggers D8-1, which is why the group-3 words must be maintained faithfully. |
| **D8-3** | `BASE(n)` stub retirement | **Retire it**: implement the real read, drop the ERRMARK path, and strike the divergence from `PROVENANCE.md`. Our table already matches the reference (§4.1). |
| **D8-4** | `G8-regdelta` (§7) | **Document, do not chase.** Fixing it means changing C-BIOS's mode setup, which is out of this slice and risks the whole graphics gate. |
| **D8-5** | Placement + funding (§5/§6) | **Tenant engine + thin resident**, funded by one leaf carve chosen against the measured deficit. |

## 9. Implementation order

1. `VDP` keyword row + the two `ev_f` function arms (`ev_f_vdp`, real
   `ev_f_base`) — read-only surfaces first, gated before any write lands.
2. Tenant `GFX_OP=13/14` with the grain/validation/register tables + host unit
   tests for the pure leaves.
3. Resident assignment dispatch (`$C8`/`$C9`) + the parse/marshal half.
4. Measure the deficit; run the carve scout; land the carve; re-gate
   (`unit-test`, `graphics-acceptance`, `diskbasic-acceptance`, lean-build
   byte-identity).
5. Phase Q differential, including the `TIME`-freeze teeth check.
6. TODO/arc-spec/memory close-out.

Per [memory: opus-vs-sonnet-model-split], steps 1–5 are Sonnet-5 work once this
spec is signed off.
