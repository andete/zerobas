# zerobas BASIC — graphics slice G8: `VDP(n)` and `BASE(n)`

Status: **LANDED 2026-07-22.** Signed off the same day (D8-1 reproduce the quirk;
D8-2..D8-5 as recommended); §6 and §7 are as-built. Arc spec:
[`spec-basic-graphics.md`](spec-basic-graphics.md). Predecessor slices G1–G7 all
landed; this is the VDP-register / table-base access pair, the last non-deferred
graphics item in [`../TODO.md`](../TODO.md).

Every `[PIN]` below is a measured black-box fact from the Philips VG-8020, with
the raw record and the probe scripts in
[`../scratchpad/g8_vdp_notes.md`](../scratchpad/g8_vdp_notes.md)
(`g8_vdp_char1.py` … `g8_vdp_char8.py`). No ROM disassembly
([memory: no-reference-rom-disasm]).

---

## 1. Scope

**In:** the `VDP(n)` pseudo-array (read and write) and the `BASE(n)` pseudo-array
(read and write). Four surfaces:

| surface | before this slice |
|---|---|
| `A=VDP(n)` | did not exist (`VDP` was not a keyword) |
| `VDP(n)=v` | did not exist |
| `A=BASE(n)` | **descoped stub** — [`basic/expr.asm:1721`](../basic/expr.asm:1721) parses the argument, returns 0 and sets ERRMARK |
| `BASE(n)=v` | did not exist |

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
| `FOR VDP(0)=0 TO 1`, `SWAP VDP(0),A` | ERR 2 (**not reproduced** -- `G8-trapclass`, §7) |
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
  bit and watching the frame counter freeze (delta 0 against a control that
  advanced 62). This is the gate's teeth check -- see §7.
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

4. **How wide is the reprogram? All of R0..R6** `[PIN]` — not just the written
   slot's register. Rounds 4/7 could not tell, because every other register
   already held the value its table word implies. Round 8 desyncs first
   (`VDP(2)=5:VDP(6)=5`) and then writes an unrelated slot: both poked registers
   **snap back to their table values**, in SCREEN 0 as much as in SCREEN 1/2. So
   there is ONE uniform code path, and the mode's only role is choosing the
   source group:

   ```
   group_used = [0, 2, 3, 3] [SCRMOD]      ; the off-by-one lives entirely here
   ```

   `R7` is untouched, and `R0`/`R1`'s non-mode bits are **preserved** — a
   `SCREEN 2,1` sprite size survives (`R1 $e1 -> $e9`: only M2 changes), as does a
   poked `R1=$a0` (`-> $a8`) and a poked `R7=$4f`.

   With `g = group_used` and `b(k) = BASE(g*5 + k)`:

   ```
   R0 = (R0 & $FD) | ($02 if g==2 else $00)          ; M3
   R1 = (R1 & $E7) | ($10 if g==0 else $08 if g==3 else $00)   ; M1 / M2
   R2 = b(0) / $400
   R3 = b(1) / $40      | $7F  if g==2                ; GRAPHIC-2 mask
   R4 = b(2) / $800     | $03  if g==2                ; GRAPHIC-2 mask
   R5 = b(3) / $80
   R6 = b(4) / $800
   ```

   Every value in §4.4's tables and in rounds 4/7/8 falls out of this: `g=2`
   colour `$2000` → `$80|$7F = $ff`, `g=0` colour `$2000` → `$80`, `g=2` pattern
   `$0000` → `$03`, `g=3` name `$0800` → `$02`, satr `$1F00` → `$3E`.

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

## 6. Space — as built

The resident half measured **112 B over** the ceiling on first assembly, and
**85 B over** after a DRY pass (one shared paren parser for `VDP(n)`/`BASE(n)`/
`SPRITE$(n)`, one body for both function reads). The `BASE` stub's retirement
paid for the rest.

The deficit was NOT funded by evicting an unrelated feature. The carve scout's
shortlist did not survive a human read -- its top single-entry candidate,
`psv_fetch` (130 B), is the PLAY servicer that runs from the frame ISR, and a
`subrom_call` per VBLANK is exactly the wrong thing to add there. So the bytes
came from inside the graphics arc instead, by moving two pieces of PURE
MARSHALLING out of page 1 and into the tenant that was already doing the work:

| moved | freed |
|---|---|
| `circ_draw`'s tail -- the deferred start/end spokes and the work-area writes. Each spoke was a resident `subrom_call` back into the SAME island; inside the tenant it is a plain `call gfx_line_op`. | ~120 B |
| `elg_draw`'s work-area writes (`GXPOS`/`GYPOS`/`GRPACX`/`GRPACY` = p2) -- the tenant already holds those coordinates in `GFX_X2`/`GFX_Y2`. | 24 B |

Final: `__MEAS_PAGE1_END = $7FEE`, i.e. **18 B of page-1 tail still free**, with
the lean cart byte-identical (`9e723a02…`, unchanged).

Order is load-bearing after the move: `gfx_line_op` now stamps the work area
with its own endpoint, and the CIRCLE op calls it for spokes -- so `gco_done`
draws the spokes FIRST and writes the circle's own work-area values AFTER, or a
spoke endpoint would survive as the last-referenced point.

## 7. Gate — as built

`make graphics-acceptance` gained **Phase Q**, three parts, all differential
against the VG-8020 and all green:

* **Q1 (20 cases)** -- state: the 20-word table AND `R0..R6`, read from memory
  with the case holding its screen mode in a `GOTO`-self loop. Covers the plain
  reprogram, the SCREEN-1/2 off-by-one, the poison cases that prove the source
  group, the desync cases that prove the reprogram is wide, `R1`'s surviving
  sprite-size bits, and the cross-group store-only rule.
* **Q2 (55 cases)** -- reads, domains, value grain per slot kind, and the whole
  grammar table of §3, each case reporting both outcomes behind one tag so an
  accepted↔raised flip cannot pass.
* **Q3 (4 cases)** -- **the teeth**: everything else passes on an implementation
  that only updates the RAM mirrors, since the reads come back from the very
  cells the write filled. So clear `R1`'s interrupt-enable bit and watch the
  frame counter: frozen means the chip saw it. Measured `JIFFY` delta 0 for
  `ie_off` against 206 for the control on our machine (62 on the reference).
  Note it reads `JIFFY` directly, not BASIC's `TIME` -- zerobas has no `TIME`,
  so the first cut of this check sat at 0 for BOTH cases and proved nothing on
  the machine it most needs to bite.

Host unit tests were not extended: unlike G3/G4's rasterisers, every G8 leaf is
a table lookup or a shift whose only interesting behaviour is the VDP write the
host harness cannot model -- Q1/Q3 are where the teeth are.

**Excluded from assertion, documented:**

* **`G8-regdelta`** -- C-BIOS programs `R7` differently from the reference BIOS
  (`$f4` vs `$04` in SCREEN 1/2), and `R3`/`R5`/`R6` differently in SCREEN 0, so
  `VDP(3)`/`VDP(5)`/`VDP(7)` read back different values there. This sits BELOW
  the BASIC statement. Q1 therefore asserts `R0..R6` only where G8 reprograms
  (there all seven are written from the identical table, so they DO match
  exactly) and the table alone elsewhere. (An earlier draft of this spec claimed
  SCREEN 2 agreed exactly; it does not -- `R7` differs there too.)
* **`G8-trapclass`** -- `FOR VDP(0)=0 TO 1` and `SWAP VDP(0),A` are a trappable
  ERR 2 on the reference and are silently ACCEPTED here. NOT a G8 property:
  `FOR 1=0 TO 1` and `SWAP 1,A` behave the same way, so it is a general
  FOR/SWAP lvalue-validation gap, and gating it would only lock in the wrong
  behaviour.

**Bug the differential caught** (the arc's recurring lesson, again): the first
cut parked the function's index limit in `C` across the argument evaluation.
`eval` clobbers `BC` on its FLOAT path only -- so every integer index worked and
every fractional one (`VDP(1.7)`, and even `VDP(1.0)`) became a bogus ERR 5.
Static reading said the register was fine; Q2 said otherwise. The limit now
lives in RAM.

## 8. Decisions — SIGNED OFF 2026-07-22

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
