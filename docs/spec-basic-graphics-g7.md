# Spec — graphics Slice G7: sprites (`SPRITE$`, `PUT SPRITE`, `SCREEN`'s size arg)

**Status: LANDED (2026-07-22)** — commits `444b24b` (both halves, resident gated
off), `f6a578a` + `8cc45d2` (the eviction, then switch-on). Gates green:
`graphics-acceptance` Phases N/O/P, floor gate + teeth, `unit-test` 51/51,
`diskbasic` 34/34, `bdos` 12/12, lean cart byte-identical. The eviction that
funded it is [spec-eviction-g7-space.md](spec-eviction-g7-space.md).
**Originally signed off (2026-07-22):** All of §9 approved as recommended, and
D-G7-4 settled on (a): `SPRITE ON/OFF/STOP` parse as accepted no-ops in G7. Slice G7 of the graphics arc
([spec-basic-graphics.md](spec-basic-graphics.md)) and its **last slice**: the
drawing statements G1–G6 have landed, and sprites are the remaining MSX1
graphics surface (`SCREEN 3` stays deferred, graphics `GET`/`PUT` do not exist
on MSX1 — arc spec §1).

Everything in §3–§6 is **measured** on the reference machine profile; the raw
findings and the probes behind them are the characterization notebook
[scratchpad/g7_sprite_notes.md](../scratchpad/g7_sprite_notes.md)
(probes `scratchpad/g7_sprite_char{1,2,3,4}.py`). Nothing here comes from a
disassembly.

---

## 1. What lands in G7 vs. what defers

**In:**
- `SPRITE$(n) = <string$>` — write a sprite pattern-generator entry.
- `A$ = SPRITE$(n)` — read one back (a string *factor*, both sides of `=`).
- `PUT SPRITE <plane>[,(x,y)|STEP(dx,dy)][,<colour>][,<pattern>]` — write a
  sprite attribute entry.
- **`SCREEN <mode>,<sprite-size>`** — the second argument, today *evaluated and
  discarded* ([basic/screen.asm:60](../basic/screen.asm:60)). G7 must make it
  real: it selects 8×8 vs 16×16, which changes the `SPRITE$` entry size **and**
  the `PUT SPRITE` pattern-number scaling, and it **persists** across later
  `SCREEN` statements (§5).
- The sprite table init that a mode set performs (§5).

**Out (deferred, by charter, to the interrupt-trap TODO item):** `SPRITE ON` /
`SPRITE OFF` / `SPRITE STOP` and `ON SPRITE GOSUB` — the collision-trap surface.
G7 owns the `SPRITE` **keyword** (which those forms share) and — per the
signed-off **D-G7-4** — parses all three statement forms as **accepted no-ops**,
so a program that arms a collision trap it never fires still runs. The trap
semantics themselves belong to the interrupt-trap slice.

## 2. Placement — DECISION D-G7-1

Sprites are **short, unconditional VRAM writes**: at most 32 bytes for a pattern
entry, exactly 4 for an attribute entry. There is no loop whose duration a
musician would hear, so the EI-between-pixels discipline that forced G3–G6 into
the page-0 tenant is not needed here for *timing*.

> **Recommended D-G7-1: join the existing page-0 graphics tenant**
> (`SUBROM_IDX_GRAPHICS`) as `GFX_OP = 7` (attribute write) and `GFX_OP = 8`
> (pattern write/read), reusing `gfx_vram_wr` / `gfx_rd_raw` verbatim.

Why not the alternatives:
- *Resident, via BIOS `WRTVRM`/`RDVRM`.* Byte-cheapest at the VRAM level, but
  page-1 resident space is the arc's standing wall (§7) — the bytes are exactly
  what we do not have. Rejected on space, not on correctness.
- *Its own tenant.* A second island duplicating the VDP primitives for ~60 B of
  logic; no benefit.

The tenant keeps the DI-guarded address-latch discipline unchanged
([memory: vdp-direct-port-read-fetch-window] — `gfx_rd_raw`'s settle NOPs stay
load-bearing for the `SPRITE$` read path, which reads VRAM back).

## 3. `SPRITE$(n)` — measured semantics

Sprite pattern generator table: **`$3800`** (arc spec §11 pin, re-confirmed).

| Fact | Measured |
|---|---|
| entry size | **8 bytes** in `SCREEN x,0` / `x,1`; **32 bytes** in `x,2` / `x,3` |
| entry address | `$3800 + size*n`, **`& $3FFF`** (no clamp: `SPRITE$(255)` in 16×16 lands at `$17E0`) |
| short string | **zero-padded** to the entry size |
| long string | **truncated** to the entry size |
| `""` | zeroes the whole entry |
| `n` domain | **0..255 in every size**; outside ⇒ `ERR 5` (read *and* write) |
| `n` type | numeric expression, **truncated toward zero** (`1.9` ⇒ 1) |
| read-back | always exactly the **entry size** (8 or 32), never the assigned length |
| RHS type | a numeric RHS ⇒ **`ERR 13`** |
| mode | **write** in `SCREEN 0` ⇒ `ERR 5`; `SCREEN 1` writes `$3800` normally.<br>**read is legal in every mode, including `SCREEN 0`** (asymmetric — measured) |
| `MID$(SPRITE$(0),…)="A"` | `ERR 2` (not an assignable target) |

## 4. `PUT SPRITE` — measured semantics

Sprite attribute table **`$1B00`**, 4 bytes per plane: **`y, x, pattern, colour`**,
entry at `$1B00 + 4*plane`.

- **plane** 0..31, else `ERR 5`.
- **x/y** are stored as the **low byte of the int16** — `256`→0, `300`→44,
  `32767`→255. **No clip, no error** (only `>int16` ⇒ `ERR 6`, the shared eval
  domain). This is unlike every other graphics statement in the arc.
- **Negative x ⇒ the early-clock rule:** `attr_x = (x+32) & 255` **and** bit 7
  (`$80`) is set in the colour byte. `x ≥ 0` clears that bit again — including
  when the colour argument is omitted (measured).
- **colour** 0..15 (`ERR 5` outside), stored in the colour byte's low nibble.
- **pattern number**: 8×8 ⇒ stored **as-is**, domain 0..255; 16×16 ⇒ stored as
  **`4n`**, domain **0..63** (`64` ⇒ `ERR 5`). The ×4 is the VDP's 32-byte-entry
  quantisation and is BASIC's job, not the hardware's.
- **Omitted argument = keep the byte already in the attribute entry.** Omitted
  colour keeps the entry's colour (then re-applies EC from the sign of `x`);
  omitted pattern keeps the entry's pattern byte; the whole coordinate group
  (`PUT SPRITE p,,c,n`) keeps **both** `y` and `x` — it does **not** consult
  `GRPAC`. Measured isolated (boot-per-case) after a round-2 batching artefact.
- **`STEP(dx,dy)`** is relative to `GRPAC`, as everywhere else in the arc.
- **Work area:** a coordinate-carrying `PUT SPRITE` sets `GRPACX/Y` *and*
  `GXPOS/GYPOS` to the **raw, unwrapped, possibly negative** coordinate. The
  omitted-coordinate form leaves all four alone.
- **Float/expression args truncate toward zero** — `(10.7,20.2),4.9,1.9` ⇒
  `10,20,4,1`; `-5.7` ⇒ −5 ⇒ attr x 27 with EC.
- **Modes:** `SCREEN 0` ⇒ `ERR 5`; `SCREEN 1` works (same `$1B00`).
- Needs **no `SPRITE ON`**.
- Syntax: `PUT SPRITE 0` (no coordinate group at all) ⇒ `ERR 2`; a half-empty
  coordinate `(,20)` / `(10,)` ⇒ `ERR 2`.

## 5. Mode set, init state, and the persistent size — measured

- `SCREEN 2` (and `SCREEN 1`) initialises **all 32 attribute entries** to
  `y = 209`, `pattern = plane index`, `colour = FORCLR` (measured: `COLOR 4,1,1:
  SCREEN2` ⇒ colour byte 4) — and **leaves the x byte untouched** (a stale x
  survives a mode set). `y = 209` is the "hide this and all following planes"
  value, i.e. the idle state.
- **`CLS` touches neither sprite table.** A re-`SCREEN 2` re-runs the attribute
  init but **leaves the pattern table intact**.
- The sprite-size argument lives in **`RG1SAV $F3E0` bits 1..0** (`,0`⇒`$F0`,
  `,1`⇒`$F1`, `,2`⇒`$F2`, `,3`⇒`$F3`; bit 1 = 16×16, bit 0 = magnify) and
  **persists across later `SCREEN` statements that omit it** — `SCREEN2,2:
  SCREEN2` stays `$F2`, and it survives `SCREEN 0`/`SCREEN 1`. Structurally the
  same "state that outlives the statement" shape as `DRAW`'s `S`/`A` (G6 §4).
- ⚠️ **Our runtime's mode set is C-BIOS `CHGMOD`, not the reference's.** Whether
  C-BIOS performs the same attribute init (and with `FORCLR`) is **the first
  thing to measure during impl** — if it differs, G7 owns the init explicitly in
  `ex_screen` rather than inheriting it. Do not assume; this is exactly the class
  of gap the arc's differential keeps catching.

## 6. Errors — the whole measured surface

| Case | Reference |
|---|---|
| `SPRITE$(n)` `n<0` or `n>255` (read or write) | `ERR 5` |
| `SPRITE$(n)=<numeric>` | `ERR 13` |
| `SPRITE$(n)=…` in `SCREEN 0` | `ERR 5` |
| `A$=SPRITE$(n)` in any mode incl. `SCREEN 0` | **accepted** |
| `PUT SPRITE` plane <0 or >31 | `ERR 5` |
| `PUT SPRITE` colour <0 or >15 | `ERR 5` |
| `PUT SPRITE` pattern >255 (8×8) / >63 (16×16) / <0 | `ERR 5` |
| `PUT SPRITE` coordinate `>int16` | `ERR 6` |
| `PUT SPRITE` coordinate off-screen but in int16 | **accepted**, stored mod 256 |
| `PUT SPRITE` in `SCREEN 0` | `ERR 5` |
| `PUT SPRITE 0` / `(,20)` / `(10,)` | `ERR 2` |

## 7. Space — the arc's standing wall

**MEASURED 2026-07-22 (both halves written, commit 444b24b):** the resident half
is **390 B** against **45 B** of free tail — a **388 B overrun**
(`__MEAS_PAGE1_END` $7FD3 → $8184). That is *after* the tenant-heavy split of §8
(the first cut, with the table arithmetic and the merge resident, measured 483 B).
The scout finds **no single clean carve** that size: on the clean build the
largest single-entry page-0-CLEAN carves are `read_one_value` 168 B (the
READ/DATA value scanner, 2 shared-utility entries), `fia_walked` 146 B (the ASCII
file-append tail, single entry), `ex_kill`/`do_kill` 124 B, `ds_lp` 125 B. So G7's
eviction is a **combination**, which is what D-G7-6 now has to decide.

G6 landed with **45 B free** on the page-1 tail
([spec-eviction-g6-space.md](spec-eviction-g6-space.md)). G7's resident half is
a parser + marshaller for two statements and one factor, plus the `SCREEN`
size-argument handling — a first estimate of **200–300 B**, so an **eviction is
expected again**. The procedure is now mechanical:

1. Write both halves, build, read the measured `__MEAS_PAGE1_END` overrun — the
   **measured** deficit, never an estimate (G5's estimate was off by ~2×).
2. Run `python3 scratchpad/g6_carve_scout.py <deficit>` and take a single-entry,
   page-0-CLEAN candidate. A scout run on today's tree already shows several in
   the 130–180 B band (`psv_fetch`/`psv_env` 130, `fia_walked` 146,
   `read_one_value` 168 with 2 extra entries), so the runway exists — but the
   shortlist must be re-run against the real deficit and human-read (the tool
   cannot see computed jumps).
3. DRY levers first where they are free: the `gfx_eval_int16` /
   `gfx_store_colour_checked` helpers G6 introduced already cover most of the
   coordinate/colour boilerplate `PUT SPRITE` needs.
4. Eviction spec → sign-off → carve → re-gate (`diskbasic`/`bdos`/lean-identical)
   **before** the G7 resident lands.

**Tenancy rule (automated, G6 §8):** a page-0 tenant sees page-1 residents but
neither BIOS nor the page-0 low region, judged **transitively** — anything whose
closure reaches `eval` (⇒ float pack) is barred.

## 8. Marshalling ABI (sketch)

Reuse the existing graphics block at `$E030` (`GFX_OP`, `GFX_C`, `GFX_RES`,
`GFX_REL`) plus the pinned `GXPOS/GYPOS` coordinate cells:

- **`GFX_OP = 7` — attribute write.** In: plane, y, x (already int16-truncated
  by the resident), colour + a "colour given" flag, pattern + a "pattern given"
  flag, EC bit. The tenant reads the existing entry for the omitted fields
  (`gfx_rd_raw`) and writes the 4 bytes.
- **`GFX_OP = 8` — pattern write / read.** In: entry index, entry size, a
  resident-side buffer address for the ≤32 bytes, direction. The string data
  itself is copied through a RAM buffer in the LINEBUF region the arc already
  uses (G3 §RAM home), never a page-1 pointer the tenant cannot follow.

The resident half does: `eval` for every argument, the int16/`ERR 6` domain, the
`ERR 5` range checks, the size lookup from `RG1SAV`, the ×4 pattern scaling, the
EC computation, the `GRPAC`/`GXPOS` work-area writes, and the string
descriptor/temp-pool handling for `SPRITE$` (both directions).

## 9. Decisions — SIGNED OFF 2026-07-22

- **D-G7-1 placement.** Join the graphics tenant as `GFX_OP = 7/8`
  (**recommended**, §2) vs. a resident BIOS-`WRTVRM` implementation (cheaper VRAM
  code, but spends the bytes we do not have).
- **D-G7-2 `SCREEN`'s sprite-size argument.** Implement it for real, including
  the `$F3E0` persistence (**recommended** — `SPRITE$`'s entry size and
  `PUT SPRITE`'s ×4 scaling are both derived from it, so without it the slice is
  half-faithful). Cost is small; it also removes an existing silent-discard.
- **D-G7-3 attribute init on mode set.** Measure C-BIOS `CHGMOD` first (§5); if
  it does not match, do the 32-entry init ourselves in `ex_screen`
  (`y=209`, `pattern=plane`, `colour=FORCLR`, **x untouched**). Faithful, ~25 B.
- **D-G7-4 `SPRITE ON/OFF/STOP` — settled on (a):** parse as accepted no-ops in
  G7 (~10–15 B) so the keyword surface is complete and programs that arm a trap
  they never fire still run. Trap semantics stay with the interrupt-trap slice.
- **D-G7-5 the `n`-wrap quirk.** `SPRITE$(255)` in 16×16 mode wraps within VRAM
  (`& $3FFF`). Reproduce the wrap (**recommended** — it is one `AND`) rather than
  raising an error, i.e. match the reference including its overrun.
- **D-G7-6 eviction target.** Deferred to the measured deficit (§7); it comes
  back as its own one-page spec for sign-off, like G5/G6.

## 10. Gates (Definition of Done)

1. `make graphics-acceptance` gains **Phase N** — a VG-8020 differential that
   reads the **attribute table and the pattern table back out of VRAM** for:
   pattern writes in both sizes (pad/truncate/empty/`n` wrap), read-back lengths
   and contents, attribute writes with every argument present, each omitted-arg
   form, the EC rule across a negative-x sweep, coordinate wrap `>255`, the ×4
   pattern scaling, `STEP`, and the work-area cells; **Phase O** — the §6 error
   table, both outcomes behind one tag (the G6 pattern, so an accepted↔raised
   flip cannot pass); **Phase P** — the §5 state behaviour: init values after a
   mode set (incl. `colour = FORCLR` and the untouched x), `CLS` leaving both
   tables alone, and the sprite-size **persistence** across a later bare `SCREEN`.
2. Host unit tests (`make unit-test`) for the pure leaves: entry-address
   computation with the `& $3FFF` wrap, the EC transform, and the ×4/size lookup.
3. `make diskbasic-acceptance` + `make bdos-acceptance` green after the eviction,
   and the **lean cart byte-identical** to its frozen baseline.
4. `make audit-citations` clean; paper-trail pass over the landed asm.

The recurring lesson stands: a green build that was never run against the
reference is not evidence. Sprites are VRAM-visible state, so the differential
can see everything that matters here — there is no excuse for a static-only pass.

## 11. Impl order — as it actually went

**Step 1 answered D-G7-3:** C-BIOS `CHGMOD` already reproduces the reference's
mode-set init (`y=209`, pattern = plane, colour = **FORCLR**) — and differs in
exactly one respect: it also **zeroes the x byte**, where the reference leaves it.
So G7 brackets its `CHGMOD` with tenant ops 10/11, which snapshot the 32 x bytes
and put them back (`scratchpad/g7_chgmod_init.py`).

**Two bugs survived to first run, both caught by the differential and invisible
to host tests** — the arc's recurring lesson, again:
1. `gfx_vram_rd` (the G1 di-guarded read) had **no fetch-window settle** — the G2
   lesson had only ever been applied to `gfx_rd_raw`. A 4-byte attribute read came
   back ROTATED and `SPRITE$` read zeros. Fixing it also showed that the G1 teeth
   check had really been detecting the missing settle all along (eviction spec §7).
2. Every malformed sprite statement used `jp stmt_error`, which PRINTS and aborts
   the RUN — so `ON ERROR GOTO` never saw it, while the reference raises a
   trappable `ERR 2`. Phase O puts both outcomes behind one tag, so the flip could
   not pass.

The original plan, for the record:

1. Measure C-BIOS `CHGMOD`'s sprite init (D-G7-3) — one probe, before any asm.
2. Tenant `GFX_OP = 7/8` + host-unit-tested leaves.
3. Resident `ex_put_sprite`, the `SPRITE$` statement + factor arms, `SCREEN`
   size argument; kwtable row for `SPRITE` + interp arms (repack-only, the
   `CIRCLE`/`DRAW` pattern).
4. Build → **measure** the overrun → eviction spec → sign-off → carve → re-gate.
5. Gates (Phases N/O/P, unit tests, diskbasic/bdos/lean).
6. Spec/PROVENANCE/TODO/memory writes; the graphics arc then **concludes**
   (bar the deferred `SCREEN 3` and the interrupt-trap slice).

## Appendix — sources

- Sprite *language* semantics (`SPRITE$`, `PUT SPRITE`, `SCREEN`'s size
  argument): public MSX-BASIC language reference.
- Sprite attribute/pattern table addresses, the early-clock bit, `RG1SAV`
  bits 1..0: TMS9918A datasheet + MSX2 Technical Handbook VDP chapter / MSX
  Assembly Page work-area appendix — published contracts, cross-checked
  black-box (§3–§5), never disassembled.
- Every numeric behaviour in §3–§6: this project's own black-box oracle
  observations, [scratchpad/g7_sprite_notes.md](../scratchpad/g7_sprite_notes.md),
  probes `scratchpad/g7_sprite_char{1,2,3,4}.py`.
- No MSX-BASIC / BIOS / reference-ROM disassembly was used
  ([PROVENANCE.md](../PROVENANCE.md)).
