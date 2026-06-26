<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 A-5 spec — run the $0038 handler on the caller's stack (retire the A-2b private stack)

**Status:** IMPLEMENTED + validated 2026-06-26. Supersedes A-2b's private interrupt stack.
**Supersedes:** `tier2-a4-spec.md` (withdrawn — its premise was a misdiagnosis, see §2).

## 1. Symptom

After A-3 fixed the COMMAND.COM interrupt storm, the boot still hung short of `A>` in an
infinite loop `$DC03 → … → call $F368 → jp WA_SEG ($E795) → … → $0000: jp $DC03`, because the
`WA_SEG` segment-switch trampoline's tail (`$E7A8+`) was corrupted: instead of
`ld (SLTTBL3),a; ld ($FFFF),a; … ret` it ran off into `$0000: jp $DC03`. The page-1 swap the
kernel needs never happened.

## 2. Misdiagnosis (A-4) and the correction

A-4 read the corruptor as the MSX disk-boot stack roaming the `$E7xx` band, and relocated the
resident code into the reserved `$DDxx` zone. **That was wrong** — the corruption *reappeared
identically* at the new address (always at `WA_SEG+19`), because `WA_SEG` and the corruptor's
stack relocated *together*. The harness then showed the corruptor is **our own interrupt
handler**: the routine at `$0C82` (running on a stack inside our `INT_STK` region) is the
**main-ROM KEYINT** — a 3-iteration `rr c; call c,$113B` loop, the `dec ($F3F6)` JIFFY tick,
and the textbook MSX interrupt epilogue `pop ix; pop iy; pop af; pop bc; pop de; pop hl` at
`$0D02`. It is reached from our A-3 handler via `call $0038`.

**Root cause:** the A-2b *private interrupt stack* (`ld sp, INT_STK_TOP`, 48 bytes) is too
small for the main-ROM KEYINT (~60 bytes, and unbounded via the `H.TIMI`/`H.KEYI` hooks).
KEYINT overflows it **downward into the `WA_SEG` trampoline laid out directly below**
(`INT_STK_TOP = PG_SV_A8+1+48`, with `WA_SEG`/`CONOUT_CHAR`/`PG_SV_A8` immediately beneath),
corrupting it. (A-4 had already been reverted; the `$0C85` writes in its review-queue entry
are these KEYINT pushes, not a disk-boot stack.)

## 3. Fix

Run the handler on the **caller's (interrupted code's) stack** — the standard MSX interrupt
convention — by deleting the three stack-switch instructions from `int_h_hiram_tmpl`:

```
-   ld (INT_SP_SAVE), sp      ; A-2b: save caller SP
-   ld sp, INT_STK_TOP        ; switch to the 48-byte private stack
    push af / push bc / push de / push hl
    di ; …pg0_mainrom_in… ; call $0038 ; di ; …pg0_mainrom_out…
    pop hl / pop de / pop bc / pop af
-   ld sp, (INT_SP_SAVE)      ; restore caller SP
    ei
    ret
```

**Why this is safe now.** A-2b's private stack existed solely to be non-destructive if an
interrupt fired with a *corrupt caller SP* (the primary derail / storm). **A-3 fixed that
derail**, so the caller SP is always valid when `$0038` fires here — every caller stack we
measure is healthy and roomy (kernel `$DBFA`, COMMAND.COM `$F513`, …), with ample headroom for
KEYINT's ~60 bytes. Running on the caller stack also removes the unbounded-depth guesswork
that any fixed private-stack size would impose (KEYINT depth is not statically bounded).

The handler stays relocatable (straight-line, only a PC-relative `jr` + the fixed `call
$0038`). `INT_STK_TOP`/`INT_SP_SAVE` remain defined (still referenced by the dead-but-kept
`int_h_body`); they are simply no longer used by the live handler.

## 4. Validation (harness + regression, 2026-06-26)

- `WA_SEG` @`$E795` == the 27-byte template, **byte-identical at t=6 and t=14** (corruption
  gone — nothing overflows into it).
- Boot **breaks out of the loop**: `time_sweep` shows ours executing COMMAND.COM (`$0BA4`,
  `$0D0A`, `$120C`) + kernel veneers (`$50xx-$54xx`) + the working `$F36B → jp $E79B`
  segment switch, healthy SP `$DBxx` throughout — the same kind of varied progress stock makes
  (which it didn't before). CONOUT runs (`$790E ld (#e7b0),a`). A *new, looser* downstream
  blocker remains (screen still blank at t=90, PC churning around the `$54xx` CONOUT band) —
  the next milestone, not this one.
- A-3 intact: `disk_derail_locate --preset sp-rompage` = STUCK (no storm regression).
- Tier-1 green: `make unit-test` 18/18; DSKIO byte-identical to CF-3300; BLOAD loads (`,R`
  execs, plain does not); FILES byte-identical to CF-3300.
- Net-zero: `disk.rom` == 16384 B. The handler shrank 11 bytes, but it is LDIR-relocated from
  the free tail, so only the trailing `ds $8000-$` pad grows — no canonical address shifts.
- Test disk unmutated (md5 unchanged).

## 5. Undo

Re-insert the three stack-switch instructions in `int_h_hiram_tmpl`.
