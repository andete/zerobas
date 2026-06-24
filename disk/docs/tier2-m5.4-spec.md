<!--
SPDX-License-Identifier: 0BSD
Copyright (c) 2026 Joost Yervante Damad
-->
# M5.4 implementation spec — first COMMAND.COM progress (for review)

Status: **APPROVED 2026-06-24** — fork = **(P) pragmatic diagnostic first cut**;
loader-first reorder accepted (M5.4 = first-cut `k_47B2`). Rationale: gaps in
*contracts* fill cleanly later via the veneer/stub design; only the loader's
control-flow *shape* (the return-to-`$D824` handoff) might need rework, which the
diagnostic framing surfaces early. Parent: [`tier2-kernel-plan.md`](tier2-kernel-plan.md).
Sources: scans §8.48-8.53.

## A dependency-chain finding that reshapes M5.4

The plan had M5.4 = "build the trampoline table + page-0 vectors, validate
standalone." That ordering is **not validatable**: the `$F2xx` CALSLT trampolines
are only ever exercised *by `$47B2`'s logic* (scan §8.49: `$4919←$F27C←$4916`,
etc.), and `k_47B2` is currently a `ret` stub — so with the loader stubbed, a
trampoline table fires *never* and proves nothing. The chain forces **loader-first**:
nothing downstream runs until `k_47B2` does something.

So M5.4 is redefined: **a first-cut `k_47B2` that gets COMMAND.COM running at
`$0100`**, measured by a new progress probe. The trampoline table + sub-entries are
then filled *as COMMAND.COM/the loader demand them* (M5.6…N), each validated by the
same probe — the incremental loop, not a big-bang foundation.

## What `$47B2` actually is (from the scans)

- Reached **directly** by `CALL $47B2` from the kernel loader at `$D821` (not via a
  trampoline). Runs the whole COMMAND.COM load + COMMAND.COM's early init, then
  returns to `$D824` after ~371 k instrs (§8.41); COMMAND.COM continues *after*
  `$D824` to reach `A>` (§8.51).
- Entry contract (§8.50, == spec §5.1): `AF=0044 BC=FFFA DE=DC5B HL=D500 IX=F195
  IY=EC55`; returns `AF=0142 HL=1A00 IY=DC5B`.
- The essential I/O it performs: locate COMMAND.COM, **read it with one DSKIO call,
  B=13 sectors → `$0100`** (§8.50, `$4010` IN `BC=0DF9 HL=0100`), lay the `$0100`
  page-0 env (spec §5.2), transfer in.

## The fork (needs sign-off) — how faithful should `k_47B2` be?

- **(P) Pragmatic loader (recommended for the first cut).** Don't replicate the
  stock's internal sub-entry choreography. Use our **own validated file layer**:
  open `COMMAND.COM` via `bdos_entry` (FCB), DMA = `$0100`, read all records to
  `$0100`; then lay the §5.2 page-0 env, set the register contract, and transfer to
  `$0100`. Reuses `bdos_entry`/`fat_mount`/`SECTOR_BUF` — all oracle-validated.
  Fast, and it produces the observable result COMMAND.COM cares about (its image at
  `$0100` + the env).
- **(F) Faithful loader.** Replicate `$47B2`'s exact sub-entry sequence (drive
  `$4558/$4919/…` through the `$F2xx` trampolines), reproducing every work-area
  side-effect. Maximal fidelity, much more work, and most of it is the C-class
  characterisation still ahead.

**Recommendation: start with (P) as a diagnostic first cut** — get COMMAND.COM
*executing* (first proprietary COMMAND.COM code on zerobas), then let the progress
probe tell us which side-effects/sub-entries COMMAND.COM actually needs, and add
only those (drifting toward F only where the probe proves it necessary). This is the
black-box-driven, minimal-divergence path; it also respects that §8.53 showed the
"faithful kernel" is loaded MSXDOS.SYS, not something we hand-build.

**Known risk of (P):** the stock `$47B2` *returns to `$D824`* mid-COMMAND.COM-init,
whereas a plain "load + `jp $0100`" would not. The first cut is therefore a
**diagnostic** to measure how far COMMAND.COM gets and what it calls back into — not
necessarily the final control-flow. Expect to revisit the return-to-`$D824` handoff
once we see COMMAND.COM's first callbacks.

## Reuse inventory (grounded, not guessed)

`bdos_entry` (FCB BDOS, oracle-validated) · `fat_mount` (BPB parse) · DSKIO `$4010`
(done) · `SECTOR_BUF` `$E2A0` · the `$F24E-$F2FD` stub table (`RES_STUBS`, today
`RET`-filled §8.29 — becomes the `$F2xx` trampolines later) · `lay_page0_env` +
the §5.2 page-0 layout.

## Concrete steps (first cut)

1. **`k_47B2` body:** build an FCB for `"COMMAND COM"`; `bdos_entry` Open; set DMA =
   `$0100`; read its records into `$0100` (reuse the seq/RDBLK read path). Cite the
   COMMAND.COM size/sector contract to §8.50.
2. **Lay the `$0100` page-0 env** per spec §5.2 (the 6-vector table + the inter-slot
   slot helper written from the public slot-select spec — *our* bytes; the FCB/DMA
   left `$00`).
3. **Set the register contract** the env hands COMMAND.COM (§5.2) and transfer to
   `$0100`.
4. **Clean-room:** every address/constant cited to the scan finding or a public
   source; COMMAND.COM/MSXDOS.SYS stay pure oracles.

## Validation

- **New progress probe** `disk_probe_dosboot_progress.py`: boot the Tier-1 machine
  (`National_CF-3300_ZEROBASDISK`) on the oracle disk; report COMMAND.COM's
  PC high-water in `$0100-$1FFF` and the screen state. Success for the first cut =
  **COMMAND.COM executes at `$0200`** (its real entry past the `jp` at `$0100`) —
  the first proprietary COMMAND.COM code running on zerobas.
- **Regression gates stay green:** `make unit-test`, DSKIO == CF-3300, file diffs.
- Oracle on a `/tmp` copy; `git status` + hash check after.

## Ledger impact (when done)

`$47B0-47DF` (48 B, `k_47B2`) flips ✅, and — if the first cut also exercises the
read path — the read-related reuse may validate too. Re-render the ledger + show the
summary on completion.

## Open questions (resolve during M5.4)

- Does `bdos_entry` Open/Read work at this boot point as-is, or need the work area
  more complete first? (If it stalls, that's the first probe finding.)
- The return-to-`$D824` handoff (the (P) risk above) — characterise once COMMAND.COM
  is running.
