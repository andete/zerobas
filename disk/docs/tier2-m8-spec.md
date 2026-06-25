<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 milestone M8 — implement the real CONOUT at `$5454`

**Status: APPROVED-equivalent (autonomous-span mode); implementing.** Root proven
in §8.67: our `$5454` `conout` is a first-cut no-op `ret`, and it is the COMPLETE
COMMAND.COM-load blocker (the §8.60-8.66 `$DA23`/`$607B`/`int_h`-storm symptoms were
all downstream of spinning in COMMAND.COM's banner loop). Evidence: aligned
`pctrace --arm 0x0100` diverges at exactly `$5454` (stock runs the real CONOUT, ours
`ret`s); ours visits 56 distinct PCs and never escapes, stock visits 482.

## 1. Contract (black-box, documented MSX BIOS ABI — no oracle bytes)

`$5454` CONOUT: **emit the character in `A` to the console, preserving
`BC/DE/HL/IX/IY`.** Stock reaches it via `$5454→$408F→$001C (CALSLT)→…→$00A2 CHPUT`
— a genuine inter-slot call to the main-ROM `CHPUT`. The visible effect (and the
work-area side effects CHPUT performs: cursor position `$F3DC/$F3DD`, screen state)
are what COMMAND.COM's banner loop depends on; a register-preserving no-op cannot
supply them.

## 2. Slot facts (measured live at `$0100`, `disk_probe_dosboot_slotcfg.py`)

`EXPTBL = 00 00 00 80` → on the CF-3300 the **main BIOS ROM (CHPUT `$00A2`) is in slot
0, primary, UNEXPANDED**; only slot 3 is expanded. During the banner phase `SP≈$8FFx`
(page 2), so the stack survives a page-0 switch; page 1 (our disk ROM, slot 3-1) is
selected by `$A8` bits[3:2] + `$FFFF` and is untouched by clearing only bits[1:0] — so
`conout_body` stays mapped and executes throughout.

**PORTABILITY (M8b, user-flagged):** the slot id is NOT hardcoded — `conout_body`
reads `EXPTBL[0]` at runtime (the standard work-area cell, present on all MSX) and
switches page 0 to *that* slot, handling the expanded case via the `$FFFF`/`SLTTBL`
secondary protocol (`conout_set_sub`). On the CF-3300 only the unexpanded primary path
runs (validated); the expanded sub-path is spec-derived (MSX2 TH §2.4) and unproven
here (see review queue).

## 3. Implementation

`$5454` site: `conout: jp conout_body` (3 B, was 1-B `ret`). The 2 extra bytes shift
the `$5456` relocated-bodies gap down by 2, absorbed by the existing
`ds $5FE5 - $, $00` slack pad — **net-zero, nothing past `$5FE5` moves**.

`conout_body` (free tail, after the wa_seg templates, ROM-resident, run in place):
```
conout_body:                  ; A = char to emit
        ld   (CONOUT_CHAR), a
        push af               ; preserve caller AF
        push bc
        push de
        push hl
        di                    ; mandatory: no interrupt during the page-0 switch
        in   a,($A8)
        ld   (CONOUT_A8), a   ; save primary-slot config
        and  $FC              ; page-0 primary -> slot 0 (main ROM, unexpanded)
        out  ($A8), a         ; main ROM now in page 0
        ld   a,(CONOUT_CHAR)
        call $00A2            ; CHPUT — emit A; documented to preserve all registers
        ld   a,(CONOUT_A8)
        out  ($A8), a         ; restore page-0 = RAM
        ei                    ; COMMAND.COM runs with interrupts enabled
        pop  hl
        pop  de
        pop  bc
        pop  af
        ld   a,(CONOUT_CHAR)  ; return A = the emitted char (CONOUT preserves it)
        ret
```
Scratch (2 B, page-3 RAM after the WA_SEG hook bodies, dead during the banner phase
since `SP` is in page 2): `CONOUT_CHAR`, `CONOUT_A8`.

Interrupts: unconditional `EI` on exit (COMMAND.COM runs with interrupts enabled;
the first frame interrupt was already shown handled cleanly, §8.66). If a regression
shows a DI caller, switch to `ld a,i`/`jp po` IFF preservation.

Return flags: stock returns `AF=0D3B` (F changed) vs our `0DA3`. CHPUT is documented
to preserve all registers, so the change is CALSLT-wrapper noise; we keep the caller's
AF. **Validation will show whether COMMAND.COM needs CHPUT's side effects (expected)
or the specific return flags (then revisit).**

## 4. Validation

1. `make unit-test` (18/18) + DSKIO/FILES == CF-3300 + BLOAD `,R`/plain — Tier-1 must
   stay green (CONOUT is on the DOS path only; the `$5454` site is `$FF`-gated DOS).
2. `pctrace --arm 0x0100` on ours: the banner loop must now **escape** (distinct-PC
   count climbs well past 56 toward stock's range) and execution proceed past `$0322`.
3. `progress`/`hang` probes: the `$DA23` loop / `int_h` storm should be GONE; look for
   the next blocker (if any) or the `A>` idle loop.
4. Visual: the COMMAND.COM sign-on banner should render (screenshot only on request).
