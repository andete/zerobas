# Spec — Eviction slice (G5 space): cassette name-match/skip → sub tenant

**Status: SIGNED OFF (2026-07-22).** Frees the main-ROM page-1 tail so resident
`ex_paint` (G5 PAINT, [spec-basic-graphics-g5.md](spec-basic-graphics-g5.md))
fits under `$8000`. The G5 tenant + resident + host tests are already written
(working tree); only space blocks the landing (`__MEAS_PAGE1_END=$807A`, 122 B
over). Follows the landed G4-eviction pattern
([spec-eviction-g4-space.md](spec-eviction-g4-space.md): `fat_rand_*`,
line-editor). Scout report + verification: this session's transcript;
`scratchpad/g5_paint_notes.md`.

## Target (verified)
Move the **Tier-3 cassette name-match / data-skip engine** — the contiguous block
`cas_open_match` … `cas_skip_data` in [basic/cload.asm:320](../basic/cload.asm),
**161 B measured** (`$67E8–$6889`, i.e. up to `do_tape_prog`) — into a **new sub
page-1 DI tenant, `SUBROM_IDX 16`** (15/LINEEDIT is last taken; watch the
spec-vs-impl index-drift lesson, commit 136aee8). Body shared via a new
`casmatch-body.inc` so the **lean 16 KB cart keeps inline bytes** (sha-identical —
the hard gate).

## Why it's clean (non-straddle) — VERIFIED
- **Single entry** `cas_open_match`. `cas_skip_data` (the block's other label) is
  called only from *inside* the block (`com_miss` skip branch, cload.asm:381). No
  external ref into any `com_*`/`csd_*` internal label (grep-confirmed).
- **3 call sites, all resident & unchanged:** `do_tape_prog` (cload.asm:475),
  `merge_cas` (files.asm:496), `oo_dev_cas` (files.asm:1530). They call a **resident
  stub** at the same `cas_open_match` label (~17–20 B, modeled on the landed
  `relink` shim): `ld ix,ENTRY / call subrom_call / jp c,<absent> / ld a,(STATUS) /
  or a / ret z / scf / ret`.
- Inside the carve: only **BIOS** (`TAPION`/`TAPIN`, page 0) + **`cal_refill`**
  (~30 B pure BIOS+RAM leaf) — `cal_refill` is **duplicated sub-locally** (resident
  `cal_getbyte`/`ascii_read_lines` still need the resident copy). No `eval`/`string`/
  `fat`/program-store calls. **No straddle.**
- **State: all page-3 RAM** (`CAS_WANT*`, `CAS_HDRNAME/ID`, `CLINK`, `CAL_BUF`/
  `CAL_CNT`/`CAL_NEEDFILL`), visible both sides. `cas_open_match` takes **no register
  inputs, returns only CF** → one status byte (reuse the `DISKOP_STATUS`/`LE_STATUS`
  alias cell, one-tenant-at-a-time). **Nothing new to marshal.**
- **DI-fine:** the whole tape window already runs DI (TAPION…TAPIOF); the
  subrom_call boundary is microseconds against a ~1 s leader tone. The fragile
  ASCII prompt-prime (`cas_ascii_setup`→`cal_refill`) stays **resident**, regime
  unchanged.

## Net bytes
161 moved − ~20 B resident stub = **~140 B net** (floor ~131 B) vs the 122 B
deficit → fits with margin. **No DRY retrofit** (G2–G4 code untouched).

## Verification
- `probes/basic/basic_probe_cas_match.py` exercises exactly this code (tokenised
  skip, ASCII multi-block skip through the `cal_refill` copy, mixed-format,
  bare-CLOAD regression, not-found, case-sensitivity). It hardcodes the lean cart —
  **add the `$ZEROBAS_BASIC_MACHINE` override** (the `diskbasic-acceptance-repack`
  mechanism) pointing at `C-BIOS_MSX1_EU_REPACK_DISK` so it hits the tenant (the
  constant is shared in `basic_probe_cas_verbs.py:67`).
- Lean-cart **sha byte-identity** + `check_reloc.py`; `check_tenant_closure.py
  --page1`; `make unit-test`; Makefile **`SUB_PARTS`+`DEPS`** wiring (the
  stale-tenant trap, [[makefile-subparts-stale-tenant]]).

## Landing
Commit the eviction FIRST (independently verified), then land G5 on top.
