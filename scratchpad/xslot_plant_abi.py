#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-XSLOTABI phase 1: PLANT the register-survival probe (scaffold, reverted after).

🎯 ZERO NEW MAIN-ROM BYTES, which matters because main page 1 has 3 B free. The
callee is a bare `ret` that ALREADY EXISTS in main page 1, at an address that
holds C9 in BOTH ROM images -- so if the slot switch ever failed to happen, the
disk ROM would execute its own C9 there and return harmlessly rather than run
garbage. Only disk/ is touched.

The disk side loads every register the ABI could carry with a distinct value,
calls through, and writes them all back to RAM for BASIC to PEEK. IX is not
among them: it is consumed by CALSLT as the target address.
"""
import os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) > 1:
    REPO = sys.argv[1]

EDITS = [
    # 🔴 NO CALSLT EDIT HERE ANY MORE. This probe predates D-DISKVERB, which
    # shipped `CALSLT equ $001C` into disk/equates.inc for real -- so re-adding
    # it now is a duplicate definition and pasmo refuses the build. A scaffold
    # that plants what the tree has since grown is stale, not broken; the fix is
    # to stop planting it, not to rename it.
    ("disk/kernel.asm",
     "                ds      $75A5 - $, $00",
     """; --- D-XSLOTABI phase-1 PROBE -- SCAFFOLD, NOT SHIPPED ---------------------
; What does a page-1 inter-slot call actually preserve? The ABI cannot be
; designed on "CALSLT is documented to affect most of them" -- that is the
; sentence hk_mkfloat already reasons from, and it is a reason to stage
; everything in RAM. If registers DO survive, staging is avoidable work.
ZBABI_BUF       equ     $E700           ; inside WBUF ($E560..$E75F), the FAT/dir
                                        ; write-back buffer -- dead unless a disk
                                        ; WRITE is in flight, and this test does none
ZBABI_INCHL     equ     $40A3           ; `inc hl / ret`, already in main page 1 --
                                        ; a callee that MODIFIES a register
ZBABI_SCF       equ     $408E           ; `scf / ret`  -- a callee that SETS carry
ZBABI_ORA       equ     $4091           ; `or a / ret` -- a callee that CLEARS it
ZBABI_RET       equ     $686A           ; a bare `ret` already in main page 1; the
                                        ; disk ROM holds C9 at the same address, so a
                                        ; switch that did not happen returns harmlessly
zbabi_probe:
                ; --- leg 1: what did the INBOUND hook (RST 30h / CALLF) preserve?
                ; Zero main-ROM bytes needed: expr.asm's ev_cv_hook demonstrably
                ; sets HL = the hook cell, DE = ev_cv_back, A = C = the width,
                ; so the values main sent are known and can simply be recorded.
                ld      (ZBABI_BUF+9),hl
                ld      (ZBABI_BUF+11),de
                ld      (ZBABI_BUF+13),bc
                ld      a,c
                ld      (ZBABI_BUF+15),a
                ; --- leg 2: what does the OUTBOUND call-back (CALSLT) preserve?
                ld      iy,(EXPTBL-1)   ; IYh = main-ROM slot id
                ld      ix,ZBABI_RET
                ld      hl,$1234
                ld      de,$5678
                ld      bc,$9ABC
                ld      a,$5A
                call    CALSLT
                ld      (ZBABI_BUF+0),hl
                ld      (ZBABI_BUF+2),de
                ld      (ZBABI_BUF+4),bc
                ld      (ZBABI_BUF+6),a
                push    iy
                pop     hl
                ld      (ZBABI_BUF+7),hl
                ; --- leg 3: does a callee's MODIFIED HL come back?
                ; $40A3 is `inc hl / ret`, already in main page 1. 0b put 12,800
                ; calls through this route with a two-sided witness, so the
                ; switch itself is no longer the thing in doubt -- but the
                ; witness is re-read below anyway rather than assumed.
                ld      iy,(EXPTBL-1)
                ld      ix,ZBABI_INCHL
                ld      hl,$1111
                call    CALSLT
                ld      (ZBABI_BUF+17),hl
                ; 🎯 LEG 3 IS ITS OWN WITNESS. `inc hl / ret` lives at $40A3 in
                ; MAIN; the disk ROM holds `ld a,(nn)` at that address, which does
                ; not return. So HL coming back $1112 can only mean main page 1
                ; was mapped and main's two bytes ran.
                ; (A first cut read the $4002 witness AFTER the call returned --
                ; by which time page 1 is the disk ROM again, so it could only
                ; ever have read $34. Removed rather than reported.)
                ; --- leg 4: does CARRY survive? Phase 1 left F unmeasured, and
                ; NAME's body needs CF back from fat_mount and fat_find. Both
                ; directions, because "always set" and "always clear" are each
                ; indistinguishable from "preserved" on a one-sided test.
                ld      iy,(EXPTBL-1)
                ld      ix,ZBABI_SCF        ; callee SETS carry
                or      a                   ; ...from CF=0
                call    CALSLT
                ld      a,0
                adc     a,a                 ; A = 1 if CF came back set
                ld      (ZBABI_BUF+19),a
                ld      iy,(EXPTBL-1)
                ld      ix,ZBABI_ORA        ; callee CLEARS carry
                scf                         ; ...from CF=1
                call    CALSLT
                ld      a,0
                adc     a,a
                ld      (ZBABI_BUF+20),a
                scf
                ret

                ds      $75A5 - $, $00"""),

    ("disk/kernel.asm",
     """hk_present:
                scf
                ret""",
     """hk_present:
                jp      zbabi_probe     ; D-XSLOTABI PROBE (was: scf / ret)"""),
]


def main():
    staged = {}
    for path, anchor, repl in EDITS:
        full = os.path.join(REPO, path)
        if not os.path.exists(full):
            sys.exit(f"REFUSE: no such file {path}")
        src = staged.get(full, open(full).read())
        n = src.count(anchor)
        if n != 1:
            sys.exit(f"REFUSE: anchor occurs {n} times in {path}:\n  {anchor[:70]!r}")
        staged[full] = src.replace(anchor, repl, 1)
    for full, out in staged.items():
        open(full, "w").write(out)
        print(f"patched {os.path.relpath(full, REPO)}")
    print(f"OK: {len(staged)} file(s), {len(EDITS)} edit(s)")


if __name__ == "__main__":
    main()
