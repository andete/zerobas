# Spec — Eviction slice: free main-ROM page-1 tail for G4 (and G5/G6)

**Status: SIGNED OFF (2026-07-21) — §7 decisions E-a/E-b/E-c/E-d/E-alt all resolved
as recommended.** A prerequisite slice for
[`spec-basic-graphics-g4.md`](spec-basic-graphics-g4.md) (CIRCLE, signed off but
**blocked on resident ROM space**). No asm is written until §7 is approved.

## 0. Why (measured)

The repacked main ROM is one contiguous slot-0 image `$2812–$8000`; `$8000` is the hard
program-RAM ceiling (`TXTTAB`), immovable without breaking the MSX memory map. We are
**already at the achievable repack boundary** `ROM_BASE=$2812` — the **Tier-A "relocate
above-font content" plan is confirmed impossible** ([cbios-repack-space-analysis.md:74](cbios-repack-space-analysis.md)
own 2026-07-10 correction; the pre-font gaps hold ≤~590 B fragmented, the keep-content is
1107 B). The only clean hole below `$2812` is gap2 = 245 B.

The graphics arc has **exhausted the page-1 tail**: resident `ex_circle` = 883 B, only
~110 B was free → the working tree **overruns `$8000` by 808 B** (measured
`__MEAS_PAGE1_END=$8328`). G5 PAINT and G6 DRAW will hit the same wall. The sanctioned
lever (user, 2026-07-21) is to **evict a self-contained resident feature into the
sub-ROM's page-1 region** (~7.3 KB free, DI tenants via `subrom_call`), freeing the tail.

## 1. Target selection (surveyed + verified)

A Fable survey ranked candidates by straddle (calls into main-ROM page-1 resident code a
sub tenant can't reach) and reclaim size. **No whole-file target is straddle-free at
≥900 B.** The winner is a **carve**:

**Primary — `fat_rand_*` random-access record engine** ([basic/field.asm](basic/field.asm),
`fat_rand_open`/`fat_rand_get`/`fat_rand_put` + private helpers `frnd_*`/`frl_*`/
`mul_reclen`/`load_reclen`/`fld_fill_record`, ~**582 B** of field.asm's 1188). **Why it's
the best target — VERIFIED, correcting the survey:**
- Its FAT calls (`read_sector`/`write_sector`/`fat_mount`/`fat_find`/`fat_alloc_cluster`/
  `fat_read_fat_sector`/`fat_write_fat_entry`/`fat_dir_create`/`fat_dir_update`) resolve
  to the fatprim **body labels that already exist sub-locally** (the shared
  `fat-prim-body.inc`, included in the sub-ROM), so co-located after fatprim they become
  **sub-local calls with no rewiring** — the exact mechanism the landed **`dirverb`**
  eviction already uses ([sub/sub.asm:482](sub/sub.asm): "a RAM+BIOS leaf whose bodies
  call the Phase-1 fatprim primitives sub-locally, placed AFTER fatprim").
- `fch_select` (the one true straddle the survey flagged) is called by the **resident
  driver** (`gp_common`/`ex_field`), which **stays resident** — it is on the resident side
  of the carve boundary, not inside the moved bodies. So there is **no straddle inside the
  carve**. (The impl must confirm the exact boundary keeps every `fch_select`/`eval`/
  `raise_error` call resident and that nothing jumps into the carve's middle — the
  verify-on-execute step.)
- Channel/record state is passed in **page-3 RAM** (`DISK_FCB_NAME`, `FWR_*`,
  `GP_RECNO`, `FSECTOR_BUF[0..256)`) — visible both sides; **nothing new to marshal**.
- Runs DI-fine (disk I/O, no music timing). **Net ≈ 582 − ~50 B resident stub ≈ +530 B.**

**Second carve — line editor** ([basic/program.asm](basic/program.asm) `store_line`/
`prog_find_del`/`delete_at`/`open_gap`/`relink`, ~305 B) → net ≈ **+250 B**. Pure-RAM
TXTTAB memmove; interactive path (DI-fine). Minor straddle-breaks: duplicate the tiny
`skip_to_eol` (~10 B) sub-locally; keep a resident `relink` shim (2 cload call sites);
`vars_reset`/`fre_abort_low` are LOWREG (slot-0 page-0, visible to a page-1 tenant — the
graphics resident-ABI-import precedent, confirm via `tools/check_tenant_closure.py`).

**Reserved (not this slice)** — tape scan/store bodies ([basic/cload.asm](basic/cload.asm))
net ~+300 B, held for G5/G6 (needs the real-time tape differential gate). Ruled out
(straddle-bound): SAVE/BSAVE, FILES/OPEN/INPUT#, expr/vars/strvar — the arc's prior
eviction stopped exactly here.

## 2. Budget

| Carve | Net freed | Cumulative |
|---|---:|---:|
| #1 `fat_rand_*` → sub | +530 B | 530 |
| #2 line editor → sub | +250 B | 780 |

G4 deficit ≈ **808 B**. **#1 + #2 = +780 B**; the last ~30 B is covered by a light DRY
pass on `ex_circle` (the G4 impl already identified ~250–350 B of DRY headroom — we need
only ~30). This lands **full G4** (no scope cut) with a small margin, and gives the arc
runway. (Alt if a second carve is unwanted: **#1 + a ~250 B `ex_circle` DRY pass** fits
G4 tightly at +530 — riskier, relies on the full DRY; **not recommended**.)

## 3. Design — #1 rand-io tenant (the `dirverb` clone)

- **Placement:** a new sub page-1 body `sub/randio.asm`, `include`d in [sub/sub.asm](sub/sub.asm)
  **after `fatprim.asm`** (so `call read_sector` etc. resolve to the sub-local bodies) and
  after `dirverb`. Add to Makefile `SUB_PARTS` (the [[makefile-subparts-stale-tenant]]
  trap) + `DEPS`.
- **ABI (cheapest, survey-endorsed):** extend fatprim's existing selector `fp_table`
  ([sub/fatprim.asm:79](sub/fatprim.asm)) with three new rows
  (`DISKOP_SEL_RAND_OPEN`/`_GET`/`_PUT` = 15/16/17) → `t_fat_rand_open`/`get`/`put`
  wrappers that `call` the moved bodies and stash `{HL,A,STATUS}` via the existing
  `fp_stash_ok`/`fp_stash_err` tails. Reuses `SUBROM_IDX_FATPRIM` (no new index), the
  `DISKOP_OP`/`DISKOP_*` RAM block, and the `subrom_call IX=SUBROM_ENTRY_BASE_P1+3*12`
  path. (Alternative: a fresh `SUBROM_IDX_RANDIO=14` + own tenant — more boilerplate;
  prefer the fp_table extension unless op-count or clobber rules forbid.)
- **Resident stubs** replace the 582 B with ~3 thin shims at the same labels
  (`fat_rand_open`/`get`/`put` → set `DISKOP_OP`, `subrom_call`, translate `DISKOP_STATUS`
  → CF), so `gp_common`/`ex_field` call sites and `jp c,load_error` dispositions stay
  **byte-unchanged**. `fch_select`/`eval`/`raise_error` remain resident.
- **Lean byte-identity:** the moved bodies are wrapped `IF ROM_BASE < $4000` on the
  resident side (become sub-only); the lean 16 KB build keeps the inline bodies via the
  `fat-prim-body.inc`-style idiom so the lean cart is byte-identical. Verify.

## 4. Design — #2 line-editor tenant

New `SUBROM_IDX` (14) + `sub/lineedit.asm` tenant. Resident `dispatch_line`/`store_line`
head marshals {tokenised-line buffer ptr, line number} into RAM (they're in registers
today), `subrom_call`, tenant runs `prog_find_del`/`delete_at`/`open_gap`/copy/`relink`
over TXTTAB RAM, returns an OOM status byte → resident head does the existing `err_mem`
raise. Duplicate `skip_to_eol` sub-locally; keep a resident `relink` shim for cload.

## 5. Gates (Definition of Done)

- **Random-access record differential** (`make diskbasic-acceptance` / the FIELD-GET-PUT
  cells) stays **green** on both lean and repack — the load-bearing proof the rand engine
  still works after the move. Run the FULL suite (the [[diskbasic-option-surface-audit]]
  lesson: a shared-parse edit surfaced only in the full run).
- **`bdos-acceptance` / disk gates** green (the fatprim tenant grows rows; must not
  regress ops 0–14).
- **Line-editor path** (store/delete/RUN, auto-number) green — `make diskbasic-acceptance`
  + program-mgmt cells; the host `program`/`list` tests.
- **Lean build byte-identical** (`build/basic.rom` sha unchanged) — every moved body is
  `IF ROM_BASE < $4000`; the lean cart keeps the inline bodies. This is the hard gate the
  whole eviction rides on.
- **Build wiring:** `sub/randio.asm` (+`lineedit.asm`) in `SUB_PARTS` **and** `DEPS`,
  force-rebuild sub.rom, rebuild+reinstall the IPS ([[ips-rebuild-after-basic-change]]).
- **Measured reclaim:** `__MEAS_PAGE1_END` drops by ≥780 B; confirm the **G4 working tree
  then assembles** (the real acceptance test of this slice).
- **`tools/check_tenant_closure.py`** passes for the new tenants (no un-imported straddle).

## 6. Order

#1 rand-io first (proven dirverb-clone, +530) → re-measure → #2 line-editor (+250) →
re-measure → confirm G4 assembles → hand back to the G4 slice (unblock, DRY ~30 B, gate,
commit). Each carve is its own commit; the eviction lands before G4 resumes.

## 7. Decisions — SIGN-OFF NEEDED

| # | Decision | Recommendation |
|---|---|---|
| **E-a** | Evict `fat_rand_*` (582 B) to a sub page-1 body co-located after fatprim, via 3 new `fp_table` rows | **Yes** — the proven `dirverb` pattern; bodies resolve sub-local; the one `fch_select` straddle stays resident |
| **E-b** | Also evict the line editor (~305 B) to a new `SUBROM_IDX=14` tenant to reach +780 B | **Yes** — needed to fund full G4 without a heavy/risky `ex_circle` DRY; builds G5/G6 runway |
| **E-c** | Close the last ~30 B with a light `ex_circle` DRY pass (headroom already identified) | **Yes** — cheap; keeps full G4 scope |
| **E-d** | Reserve the tape carve (+300 B) for G5/G6, not now | **Yes** — needs the real-time tape gate; not required for G4 |
| **E-alt** | Minimal variant: #1 only + a ~250 B `ex_circle` DRY | **No** — marginal fit, relies on the full DRY; #1+#2 is safer |

Clean-room: own code; the moved bodies are already ours; no reference-ROM disassembly.
Implementation (post-sign-off) by Sonnet per the model split, supervised + gated here.
