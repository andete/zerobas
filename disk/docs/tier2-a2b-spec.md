<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 A-2b spec — a non-destructive ("storm-proof") int_h

**Status:** spec, awaiting sign-off (no asm yet).
**Genre:** diagnostic hardening. **This is NOT the boot fix.**

## Why (context, §8.74-8.75)

A pctrace armed on the first `$4251` proved the interrupt handler works end-to-end:
`$4251 → $792B` (int_h_body) → `pg0_mainrom_in` (paging ok) → `call $0038 → $0C3C`
(the real main-ROM KEYINT: H.KEYI `$FD9A` + H.TIMI `$FD9F` + keyboard scan) → clean
return through int_h_body cleanup → `RET` to the interrupted boot code at `$0320`,
SP recovering to `$8FF8`. ~700 steps stay healthy. **int_h / A-2 is correct.**

The `$0038⇄$4251`, SP-descending "storm" we keep catching is a **secondary symptom**:
a *primary* control-flow derail happens later in boot (fingerprint `AF=C28C BC=C51C↓
DE=C5E4 HL=09E4 IX=F1AA IY=0314 SP=$4250`), PC runs away, and interrupts pour into
int_h *during* the runaway. The handler then marches a bad/`$4250` stack down through
memory, **corrupting state and erasing the evidence of where the boot first derailed.**

## Goal / non-goal

- **Goal:** make int_h *non-destructive* — when it fires with a corrupt caller SP, it
  must not march that stack through memory. The failure should then present to the
  triage oracle as a clean, classifiable state (a SLIDE/SPIN with the derail intact),
  not a stack-marching storm. **This un-masks the real bug.**
- **Non-goal:** booting to `A>`. The primary derail remains after this change; that is
  the *next* milestone (hunt the first divergence from stock with the clean signal).

## Design — private interrupt stack

The canonical trampoline `int_h` (`$4251 = jp int_h_body`, + `ds 3,$00`) is **unchanged**
(net-zero). Only `int_h_body` (free-tail in `runtime.asm`, which has `ds $8000-$,$00`
slack) changes:

```
int_h_body:
        ld   (INT_SP_SAVE), sp     ; ED 73 nn nn — save caller SP without touching any stack
        ld   sp, INT_STK_TOP       ; switch to a private interrupt stack we own
        push af / push bc / push de / push hl
        di                         ; (defensive; accept already cleared IFF)
        call pg0_mainrom_in        ; UNCHANGED proven path
        call $0038                 ; main-ROM KEYINT — still does the single VDP S#0 ack
        di                         ; close KEYINT's internal EI before un-mapping
        call pg0_mainrom_out
        pop  hl / pop de / pop bc / pop af
        ld   sp, (INT_SP_SAVE)     ; ED 7B nn nn — restore caller SP
        ei                         ; single EI, last instruction before RET
        ret
```

New cells (place in disk-ROM-owned page-3 RAM, against the work-area map; ~34 B):
- `INT_SP_SAVE` (2 B) — saved caller SP.
- `INT_STK` … `INT_STK_TOP` (≈32 B) — the private interrupt stack (KEYINT's deepest
  nesting measured in the first-interrupt trace was ~10 words; 32 B is generous).

### Why this and not a pre-ack of the VDP

Reading VDP S#0 ourselves before KEYINT would clear bit 7, and KEYINT decides H.TIMI /
JIFFY off that bit — pre-acking would silently kill the timer tick. So we keep the ack
exactly where it works today (inside KEYINT) and gain non-destructiveness purely from
the private stack + guaranteed clean SP restore.

## Known residual (validate, don't pre-solve)

KEYINT ends `… ei ; ret`; there is a 1-instruction `IFF=1` seam before our `di`. In
normal operation the VDP is already acked, so nothing re-fires. If a re-entrant
interrupt *did* land in that seam it would re-enter int_h_body and clobber the single
`INT_SP_SAVE` cell. We deliberately **do not** add a re-entrancy guard flag yet — the
first-interrupt trace shows no re-entry, and the oracle will tell us if one appears
once int_h stops marching the stack. If it does, the follow-up is an `INT_BUSY` guard.

## Validation (all must hold)

1. **Triage oracle (ours):** verdict moves off "SLIDE [post-INTERRUPT-STORM, SP=$4250]"
   to a non-marching state — SP stable on the private stack, the derail/runaway PC
   exposed. (Success = *legible*, not OK.)
2. **First-interrupt pctrace (`--arm 0x4251`):** still shows int_h_body → KEYINT
   `$0C3C` → clean return to the interrupted PC, SP restored. Timer/keyboard intact.
3. **Host unit tests:** `make unit-test` 18/18.
4. **Regression vs CF-3300 oracle:** DSKIO / FILES byte-identical, BLOAD ok (int_h is
   not on those paths, but the build/relocation must stay sound).
5. **Clean-room / audit:** `make audit-citations TARGET=disk` clean; new cells carry
   the standard attestation; `ld (nn),sp`/`ld sp,(nn)` and the private stack are
   own-design, no oracle bytes.

## Success criterion

A derail no longer escalates into a memory-corrupting interrupt storm: the same boot
that today ends in a marching `$4251` storm instead ends in a clean, classifiable
state that points the oracle at the *primary* derail. That removes the mask that has
been costing us a fresh probe-hunt every time.
