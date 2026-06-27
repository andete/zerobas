<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 spec — minimal DOS-only `$F338`=0 default (BDOS-loop blocker #1)

**Status:** DRAFT for sign-off, 2026-06-27. No asm until signed off (spec-before-implementation).
**Scope (deliberately narrow, per user 2026-06-27):** default the single cell `$F338` to `00`
on the DOS-boot path only — NOT the full phase-1 clear/default pass. Prove one cell advances a
real boot, then re-trace for blocker #2. Supersedes the parked phase-1 option-A (reverted).

## 1. Why (evidence)

`disk_probe_diff trace` (anchored on the FOPEN return `$C24E`) showed COMMAND.COM's n=3
STROUT-vs-SELDSK fork is a data-driven branch on `$F338`:

```
C26B  ld a,($F338)
C26E  and a
C26F  jr nz,$C274      ; $F338==0 -> STROUT/prompt (stock) ; !=0 -> SELDSK/loop (ours)
```

Poking `$F338`=0 into ours at the read advanced it **54 instrs** onto stock's exact path (to
`$D885 call $F368`). So `$F338`=0 is necessary and effective. Stock builds it during disk-ROM
boot (write from `$57BE` at t≈3.8, the [[msx-diskrom-shared-kernel]] clear pass); ours never does.

## 2. The dual-purpose hazard (why it must be DOS-only)

`$F338` is dual-purpose: on C-BIOS it is a `$C9` (RET) BASIC hook stub; for DOS it must be `00`
([tier2-phase1-spec.md](tier2-phase1-spec.md) §7a). A **data/BASIC disk also passes through
`boot_sig_ok`** (sig `$EB`, step-7 stub `D0 C9` returns — e.g. test720.dsk on
C-BIOS_MSX1_EU_BASIC_DISK). So an unconditional `$F338`=0 there would also fire for BASIC boots
and could break a BASIC disk-hook call (the phase-1 option-A blanket-zero regression, in miniature).

**Solution — save/restore around the step-7 handoff** so the `00` only PERSISTS for a real DOS
boot (which never returns from step 7), and a returning data disk gets its host value back:

- A real DOS disk: step-7 `scf; call BOOT_ENTRY` JPs into MSXDOS.SYS and never returns → the `00`
  stands → COMMAND.COM reads `$F338`=0.
- A data/BASIC disk: step-7 returns → we restore the saved host value → BASIC sees `$F338`
  exactly as the host left it (`$C9` on C-BIOS, `$FF` on CF-3300). FILES unaffected.

This is BIOS-agnostic: it saves whatever the host had and writes a fixed `00`, on any host.

## 3. Change (init.asm, `boot_sig_ok`, around the step-7 handoff at lines 293-303)

New scratch byte (mirrors `BOOT_SV_A8`/`BOOT_SV_SEC` at init.asm:156-157):

```
BOOT_SV_F338    equ     $E762   ; saved host $F338 (restored if a data disk returns)
```

Insert immediately before `scf` (step 7):

```
                ; --- DOS-only $F338 default (BDOS-loop blocker #1) -------------
                ; COMMAND.COM branches on $F338 (ld a,($F338);and a;jr nz @ $C26B):
                ; 0 = "no AUTOEXEC -> prompt", nonzero -> wrong path. Stock's disk
                ; ROM clears it at boot; we set it just before handoff. Saved/restored
                ; so a returning data disk keeps the host's BASIC stub ($F338 is
                ; dual-purpose). DOS disk never returns -> the 0 persists. (tier2-f338-default-spec.md)
                ld      a, ($F338)
                ld      (BOOT_SV_F338), a
                xor     a
                ld      ($F338), a
```

Insert on the data-disk return path (after step-7 call returns, before/after `page0_ram_out`):

```
                ld      a, (BOOT_SV_F338)
                ld      ($F338), a          ; data disk: restore host stub for BASIC
```

(~13 bytes; consumes ROM tail pad — net-zero, build-verified. No canonical address shifts: the
fixed entries are the `$4010` jump table + page-1 BDOS veneers, all ahead of / pinned by `ds`.)

## 4. Clean-room basis

`$F338`=`00` is the documented COMMAND.COM "no-AUTOEXEC → prompt" default state; the asm is our
own (`ld/xor/ld`, save-restore idiom mirroring our existing page-0 save/restore). No stock bytes
copied; the constant and the branch semantics come from the black-box trace, not disassembly.

## 5. Validation (before commit)

1. **DOS advance (the point):** `disk_probe_diff trace --anchor 0xC24E --diska <test.dsk>` —
   ours' first PC fork moves from **step 7 to ≈step 60** (the `$F368` hook), i.e. ours now takes
   the STROUT/prompt branch. `disk_probe_diff callseq` — ours n=3 = STROUT (not SELDSK). Compare to
   the poke result (must match: `$F338`=0 set at boot ≡ poked at read).
2. **Tier-1 green:** `make unit-test` 18/18; DSKIO/BLOAD/FILES == CF-3300; **and the C-BIOS
   BASIC-disk regression** — `disk_probe_files` on test720.dsk / C-BIOS_MSX1_EU_BASIC_DISK still
   matches (proves the data-disk restore path keeps `$F338`=`$C9` for BASIC).
3. **BIOS-agnostic:** run validation 1 on BOTH C-BIOS and CF-3300 hosts (§7b two-host rule).
4. **Net-zero:** `disk.rom` == 16384 B; test disk md5 unchanged (probes use tmp copies).

## 6. Open items for sign-off

1. **Restore-path placement** — before or after `page0_ram_out`? Either works (page0_ram_out
   touches slots, not `$F338`); recommend immediately after the step-7 call returns, symmetric
   with the save. Confirm.
2. **Scratch address `$E762`** — next free byte after `BOOT_SV_SEC` ($E761). Confirm it's unused
   (it's in our high-RAM scratch band; no canonical structure there).
3. **Expected residual** — after this, blocker #2 is the `$F368`→`$E795` relocated hook (a
   behavioral check, separate milestone). This spec does NOT claim `A>`; it claims "advances past
   the n=3 fork," verifiable by re-trace. Confirm that's the intended milestone boundary.
