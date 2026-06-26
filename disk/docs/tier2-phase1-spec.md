<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 phase-1 spec — boot-time DOS work-area clear/default pass

**Status:** DRAFT for sign-off, 2026-06-26. No asm until signed off (spec-before-implementation).
**Milestone:** the first of the 4-phase DOS-work-area construction (`tier2-workarea-map.md` §5a).
Reproduce stock's boot-time clear/default of the DOS work area; this is the foundation the later
phases (DPB, resident code, FCB) build on. As a side effect it sets `$F338=00` — the cell
COMMAND.COM branches on.

## 1. What stock does (exact, black-box)

`disk_probe_dosboot_wabuild.py` (writes-by-PC) shows the phase-1 routines at t≈3.80:

| writer | operation |
|--------|-----------|
| `$57BE` | zero **`$F1C9-$F37F`** (439 B → `00`) — one contiguous memset |
| `$57D6` | `$C9`-fill **`$F24F-$F2B7`** (105 B → `C9`) — the BDOS/hook dispatch-stub table (RETs) |
| `$57E0/$57E3` | write **`$F365-$F367` = `DB A8 C9`** = `in a,($A8); ret` (a 3-byte resident routine) |

Net result, in order: zero `$F1C9-$F37F`; then `$C9`-fill `$F24F-$F2B7`; then place the
`in a,($A8);ret` routine at `$F365`.

## 2. Integration constraint (the delicate part)

The `$F1C9-$F37F` clear range OVERLAPS cells our boot already builds its own way. So — exactly as
stock does (clear first, fill second) — **the clear must run BEFORE all of ours' work-area fills**,
which then overwrite the cleared baseline. Cells ours writes inside the range:

| cells | ours' writer | must end up |
|-------|--------------|-------------|
| `$F37D-$F37F` SYSTEM = `C3 <bdos_entry>` | `init` (init.asm:126-128) | ours' value (intentional divergence) |
| `$F341-$F344` RAMAD | `init` → `set_ramad` (init.asm:140) | ours' value |
| `$F368-$F37C` segment-switch hook table | `build_wa_table` (init.asm:408) | ours' value (A-3/A-5 wa_seg; intentional divergence) |
| `$F34D-$F352` drive-DPB pointers | ours (→ DRV_TRAMP `$E8xx`) | ours' value (intentional divergence) |

If the clear runs AFTER any of these, it wipes them (e.g. wiping `$F37D` breaks the boot-sector's
`call $F37D`; wiping `$F368` breaks A-3/A-5). So the clear must be the **first** work-area touch.

## 3. Where to hook it — options

- **(A, recommended) First statement of `init`** (before the HPHYD/`$F37D`/`set_ramad` block).
  Simplest; guarantees the clear precedes every ours-fill. Runs for ALL boots (incl. BASIC), so it
  must be proven safe for Tier-1 (the clear only touches `$F1C9-$F37F`; if any BASIC/BIOS var there
  is needed pre-init, Tier-1 will catch it — fall back to (B)).
- **(B, fallback) DOS-boot-only**, at the top of `boot_disk`'s DOS path, with `init`'s `$F37D`/
  `set_ramad` MOVED to after the clear. More surgical (BASIC untouched) but reorders `init`.

Recommendation: try (A) first; it's minimal and Tier-1 is the safety net. If Tier-1 regresses,
switch to (B).

## 4. Implementation (net-zero)

A small routine `wa_clear` (≈20 bytes) in the free tail, called first thing in `init`:

```
wa_clear:  ld   hl, $F1C9
           ld   de, $F1CA
           ld   bc, 439-1
           ld   (hl), 0
           ldir                 ; zero $F1C9-$F37F
           ld   hl, $F24F
           ld   de, $F250
           ld   bc, 105-1
           ld   (hl), $C9
           ldir                 ; $C9-fill $F24F-$F2B7
           ld   a, $DB          ; in a,($A8) ; ret  -> $F365
           ld   ($F365), a
           ld   a, $A8
           ld   ($F366), a
           ld   a, $C9
           ld   ($F367), a
           ret
```

(Exact form TBD; may LDIR the `DB A8 C9` from a 3-byte ROM datum.) It needs no relocation template
itself — it runs from page-1 ROM at init time (page 1 = disk ROM during init), writing page-3 RAM.
Net-zero: it lives in the free tail; `disk.rom` stays 16384 B; no canonical address shifts. Constants
(`$F1C9`, `$F24F`, lengths) cited to the construction map (oracle observation), not stock bytes.

## 5. Validation (before commit)

- `disk_probe_dosboot_wadiff.py`: the **phase-1 regions now match stock** — `$F24F-$F2B7`=`C9`,
  `$F365-$F367`=`DB A8 C9`, and the phase-1 `00` cells (incl. **`$F338`=00**). (Phases 2-3 regions
  stay divergent — expected; they're later milestones.)
- A-3/A-5 intact: `$F368-$F37C` still holds ours' wa_seg hooks (clear ran before build_wa_table);
  `disk_derail_locate --preset sp-rompage` STUCK.
- Tier-1 green: `make unit-test` 18/18; DSKIO/BLOAD/FILES == CF-3300 (proves the clear didn't break
  BASIC — the option-(A) safety gate).
- Net-zero `disk.rom` == 16384 B; test disk md5 unchanged.

## 6. Open items for sign-off

1. Hook option (A vs B) — recommend (A), Tier-1 as the gate.
2. Is reproducing the `in a,($A8);ret` resident routine at `$F365` in scope for phase 1 (it's a
   tiny resident routine, technically "code" not "clear")? Recommend yes — it's part of the same
   `$57BE`-era pass and trivial.
3. Confirm clean-room basis: extents/values from the construction-map oracle observation; the
   `$F365` routine is `in a,($A8);ret` (a documented slot-register read), reimplemented, not copied.

## 7. Implementation attempt (2026-06-26) — option A built + validated for DOS, REVERTED (BASIC regression)

Built `wa_clear` (zero `$F1C9-$F37F`, `$C9`-fill `$F24F-$F2B7`, `$F365` routine) called first in `init`
(option A). Two integration hazards surfaced and were fixed during the build:
- **RAMAD gate (the spec §2 hazard, manifested).** Zeroing `$F341-$F344` defeats `set_ramad`'s
  `==$FF` host-detection, which **falls through to `build_wa_table` → `build_drvtbl` → resident
  routines**. So zeroing RAMAD skipped the entire DOS work-area build chain (`$F368` hooks stayed 0).
  Fixed by excluding `$F341-$F344` from the clear (two LDIRs around it).
- **Off-by-one** in the split memset (`bc` = bytes, not bytes-1) re-zeroed `$F341`; fixed.

**DOS-side validation PASSED** with the fixes: wadiff `$F338=00` ✓, `$F368=C3 95 E7` (A-3/A-5 hooks
built) ✓, `$F341-4=83` (RAMAD) ✓; diff 462→319 bytes (remainder = phases 2-3 + intentional
divergences); `disk_derail_locate sp-rompage` STUCK ✓; `make unit-test` 18/18 ✓; net-zero 16384 B.

**BUT option A REGRESSES Tier-1 BASIC `FILES`** (garbage listing; pre-change ROM byte-identical to
CF-3300, post-change empty). Root: `wa_clear` runs for ALL boots and wipes a `$F1C9-$F37F` cell our
disk-BASIC needs, not rebuilt on the BASIC path. **Reverted** to keep Tier-1 green.

**Option B (DOS-only) is required, and is NOT a one-line move.** Our DOS work-area build chain
(RES_PRINT `$F1C9`, RES_STUBS `$F24E`, DRVTBL `$F348`, WA_JMPTAB `$F368`, SYSTEM `$F37D`, the
`set_ramad→build_wa_table→build_drvtbl→resident-routines` fall-through) runs in `init` for ALL boots.
A `wa_clear` placed in the DOS path (`boot_sig_ok`) runs AFTER those builds and would wipe them with
no rebuild. So option B needs **reorganising that chain to run in the DOS-boot path, after
`wa_clear`** — while keeping whatever BASIC needs (DRVTBL? RES_PRINT?) built on the BASIC path. That
is a design task (next milestone): map which work-area builds BASIC actually depends on, then split
the construction into a DOS-only `wa_clear`+rebuild vs the BASIC-needed minimum. Needs its own spec.
