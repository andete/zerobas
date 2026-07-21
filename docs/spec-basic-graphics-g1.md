# Spec — graphics Slice G1: the VDP floor + interrupt-under-draw proof

**Status: DRAFT — SIGN-OFF NEEDED (2026-07-21).** Slice-design addendum to the
signed-off arc spec [`spec-basic-graphics.md`](spec-basic-graphics.md) (crux D1/D2/D4
approved; §11 characterization complete). G1 writes **no user-visible statement** —
it builds and *proves* the architectural floor every later slice rides on. That is
deliberate risk-staging: if the page-0 EI-trampoline + direct-VDP-port + DI-guarded
address-latch design has a flaw, it must surface here, cheaply, not inside `PAINT`.

Model precedent: the interrupt self-test tenant `SUBROM_IDX_INTTEST` +
[`spec-basic-subrom-trampoline.md`](spec-basic-subrom-trampoline.md) — G1 is the
same shape (a page-0 EI tenant, CALSLT-invoked by a probe, asserts a JIFFY delta),
extended to also drive VRAM under interrupts and verify the writes survived.

---

## 1. What lands in G1 vs. what defers

| Piece | G1 | Notes |
|---|---|---|
| Page-0 graphics tenant scaffold `sub/graphics.asm` (`SUBROM_IDX_GRAPHICS`, selector-dispatched `GFX_OP`) | ✅ | one entry, the `fatprim` pattern |
| VDP port + `SCREEN 2` base-table equates | ✅ | `VDP_DATA=$98` / `VDP_ADDR=$99`; bases from §11.2 |
| `gfx_calc_addr` — `(x,y)` → pattern VRAM byte addr + MSB-first mask | ✅ | pure leaf; host-unit-tested |
| `gfx_set_wrt` / `gfx_set_rd` — the **DI-guarded 2-byte address-latch** primitive | ✅ | the racy sequence (§3); the whole point of G1 |
| `gfx_vram_wr` / `gfx_vram_rd` — one byte via ports | ✅ | built on the latch primitive |
| `GFX_OP=0` **floor self-test** (EI, draw-under-interrupt, read-back-verify) | ✅ | the G1 gate |
| Work-area equates `GXPOS/GYPOS/GRPACX/GRPACY/CLOC/CMASK` + `GFX_*` scratch | ✅ | §5; addresses pinned §11.5 |
| Build wiring (`SUB_PARTS`, page-0 dispatch entry, IPS reinstall) | ✅ | the staleness traps ([memory: makefile-subparts-stale-tenant], [memory: ips-rebuild-after-basic-change]) |
| `PSET`/`PRESET`/`POINT`, any resident `basic/graphics.asm`, any kwtable token | ❌ G2+ | G1 needs **no scarce resident bytes** — the gate CALSLTs the tenant directly, exactly like `subrom-inttest` |
| `SCREEN 2` auto-init of the color table | ❌ | `CLS`/`CHGMOD` already bring the mode up; G1 writes the pattern plane the reference already cleared |

---

## 2. Placement + invocation (inherits arc D1/D2)

`sub/graphics.asm` is a **page-0** tenant (EI-capable via the existing RAM interrupt
trampoline — [basic/subromcall.asm:89](basic/subromcall.asm)). Index: page-0 indices
currently top out at `PU_TAIL=7`, so **`SUBROM_IDX_GRAPHICS = 8`** (append-only;
never renumber — [sub/equates.inc:17](sub/equates.inc)). Add one `jp graphics_tenant`
at index 8 of the page-0 dispatch table in [sub/sub.asm](sub/sub.asm). Invocation is
the standard `subrom_call` (`IX = SUBROM_ENTRY_BASE_P0 + 3*8 = $0028`), which runs it
under the trampoline so the tenant may `EI`.

The trampoline is already installed at boot when a sub-ROM is found (`sub_int_install`,
proven live by `subrom-inttest`), so G1 adds **no** new interrupt plumbing — it is a
new *client* of the proven mechanism.

**BIOS-agnostic note ([memory: cbios-target-cf3300-oracle]).** G1 touches only the
VRAM **address/data** ports (`$98`/`$99`) — the fixed MSX VDP hardware contract,
identical on every MSX1 — never a VDP **mode register**. So the BIOS register shadows
(`RG*SAV`) stay coherent; no BIOS coupling. (A later slice that writes a VDP register
directly would have to update the shadow too — flagged for then, not now.)

## 3. The DI-guarded address-latch — the crux primitive (D2)

To point the VDP at VRAM address `addr` for writing: `out ($99),<addr low>` then
`out ($99),<(addr>>8) | $40>`; then each `out ($98),data` stores and auto-increments.
Reading: same two `$99` writes but high byte **without** `$40`, then `in a,($98)`.

**The race (real TMS9918 behavior, published contract):** reading the VDP **status**
port (`in a,($99)`) — which the frame ISR does every VBLANK to ack the interrupt —
**resets the address read/write latch flip-flop**. If a VBLANK lands *between* our two
`$99` writes, the second write is taken as a *first* write → the address is corrupt
and the following data byte lands at the wrong VRAM address.

**Mitigation (standard MSX discipline):** wrap **only** the two `$99` writes in
`di … ei` (a handful of T-states), leaving the surrounding compute fully
interruptible. Valid because the tenant owns its EI region (§4): the guard restores
EI. `gfx_set_wrt`/`gfx_set_rd` are the *only* place `$99` is written; every VRAM
access funnels through them, so the guard is total.

```
gfx_set_wrt:            ; HL = VRAM addr; sets the write pointer
        di
        ld   a,l
        out  (VDP_ADDR),a
        ld   a,h
        or   $40
        out  (VDP_ADDR),a
        ei
        ret
```

## 4. `GFX_OP=0` — the floor self-test (the G1 gate body)

A tenant op that exercises §3 under live interrupts and proves both properties the
architecture needs. Pseudocode:

```
graphics_selftest:
        ld   hl,(JIFFY)          ; snapshot the frame counter
        ld   (GFX_J0),hl
        ei                       ; interrupts ON — the ISR now reads $99 every frame
        ; write a known, address-derived byte to a spread of VRAM addresses,
        ; looping long enough that MANY VBLANKs fire mid-run (raising the odds an
        ; unguarded latch would be hit). value(addr) = low byte of addr, say.
        <loop i = 0..N: HL = test_addr(i); gfx_vram_wr(HL, expected(i))>
        di                       ; leave EI region
        ; read every byte back (still DI-guarded per access) and compare
        <loop i = 0..N: gfx_vram_rd(test_addr(i)); if != expected(i): inc GFX_BAD>
        ld   hl,(JIFFY)
        <GFX_DJ = HL - GFX_J0>   ; frames elapsed (interrupts serviced iff > 0)
        ld   a,(GFX_BAD)
        ret                      ; A = mismatch count (0 = clean)
```

Result marshalling (RAM, read by the probe): `GFX_DJ` (JIFFY delta, 2 B), `GFX_BAD`
(mismatch count, 1 B), and `A` mirrors `GFX_BAD`. The write region is a scratch VRAM
window that no live display structure needs during the test (e.g. high pattern-gen
addresses); N and the loop length are tuned so ≥ several frames elapse (≥ ~3–4 VBLANKs)
— the same "spin past a frame" logic `subrom-inttest` already uses.

**Why this has teeth (the anti-green-build check, [memory: error-handling-arc]).** The
gate must be able to *fail*. A one-line build variant that omits the `di`/`ei` in
`gfx_set_wrt` (a `GFX_UNGUARDED` assembly switch) is run once during G1 bring-up to
confirm `GFX_BAD > 0` (corruption observed) — proving the guarded version's `GFX_BAD =
0` is a real result, not a test that can't fail. This variant is **not** shipped; it is
a bring-up assertion logged in the gate.

## 5. RAM / work-area contract

- **Reference-faithful cells** (declared now, populated by G2+; equates only in G1 so
  the addresses are pinned once): `GXPOS=$FCB3 GYPOS=$FCB5 GRPACX=$FCB7 GRPACY=$FCB9
  CLOC=$F92A CMASK=$F92C` (§11.5). G1 does not write them (no plot statement yet).
- **Own-design G1 scratch** — the `GFX_*` marshalling block in the repack-only free
  RAM window (allocate alongside the other tenant param blocks in
  [basic/sysvars.inc](basic/sysvars.inc), the `PLAY`/`SH_*`/`ARY_*` precedent; exact
  cell TBD at implementation from the live free-RAM map, not guessed): `GFX_OP` (1),
  `GFX_J0` (2), `GFX_DJ` (2), `GFX_BAD` (1). All dead outside a `GFX_OP` call.

## 6. `gfx_calc_addr` (pure leaf — host-unit-tested)

`addr = (y>>3)*256 + (x>>3)*8 + (y&7)`; `mask = $80 >> (x&7)` (§11.2). Color-plane
address is `addr + $2000` (G2 uses it; G1 defines the constant). Host unit test
(`tests/`, `make unit-test`, emulator-free — [memory: host-unit-test-harness]) locks
it against the §11 pinned landings:

| x | y | addr | mask |
|---|---|---|---|
| 0 | 0 | 0 | $80 |
| 8 | 0 | 8 | $80 |
| 0 | 8 | 256 | $80 |
| 3 | 0 | 0 | $10 |
| 255 | 191 | 6143 | $01 |

## 7. Gate (Definition of Done, G1)

- **New standing gate `make graphics-floor-acceptance`** → `probes/basic/
  basic_probe_graphics_floor.py`: CALSLT `GFX_OP=0` on the merged repack machine
  (model on the `subrom-inttest` probe), assert `GFX_DJ ≥ 1` (interrupts serviced
  mid-draw) **and** `GFX_BAD = 0` (no latch corruption). Runs on the zerobas build
  only — this is our own architectural proof, not a VG-8020 differential (the
  reference uses its own routines; §11.6 already confirmed interrupts stay live on
  real HW, which is the behavior we're matching).
- **`GFX_UNGUARDED` teeth check** (§4) — one bring-up run asserting the gate fails
  without the guard; logged, not shipped.
- **`make unit-test`** — `gfx_calc_addr` table (§6).
- **Build wiring:** `sub/graphics.asm` added to Makefile `SUB_PARTS`; page-0 dispatch
  entry added; **force-rebuild** the sub-ROM and **rebuild+reinstall the IPS** before
  the machine probe (both are silent-staleness traps — [memory:
  makefile-subparts-stale-tenant], [memory: ips-rebuild-after-basic-change]).
- **Lean build byte-identical** — G1 is repack-only (page-0 tenants exist only on the
  merged machine); the lean 16 KB cart must assemble unchanged.

## 8. Decisions — SIGN-OFF NEEDED

| # | Decision | Recommendation |
|---|---|---|
| **G1-a** | G1 ships the floor + gate only, **no** `PSET` / no resident code / no token | Yes — de-risk the architecture before any feature; keeps G1 off the exhausted resident budget |
| **G1-b** | `SUBROM_IDX_GRAPHICS = 8` (next page-0 index) | Yes |
| **G1-c** | Self-test writes a scratch VRAM window under EI, verifies read-back + JIFFY delta; `GFX_UNGUARDED` teeth check proves the gate can fail | Yes — the anti-green-build discipline |
| **G1-d** | Direct `$98`/`$99` only, no VDP register writes in G1 (BIOS shadows stay coherent) | Yes |

On sign-off I implement G1 in this order: equates → `gfx_calc_addr` + its unit test
(fast, emulator-free) → the latch primitives + self-test tenant → dispatch/`SUB_PARTS`
wiring → the floor gate (guarded pass + unguarded teeth check) → commit.

## Appendix — sources

Inherited from the arc spec §0/§Appendix: TMS9918A datasheet (VDP ports, the
status-read-resets-latch contract), MSX2 TH (work-area addresses, VDP port map), the
§11 VG-8020 black-box pins. Own-design: the tenant scaffold, the self-test, the
`gfx_calc_addr` implementation. No reference-ROM disassembly ([memory:
no-reference-rom-disasm]).
