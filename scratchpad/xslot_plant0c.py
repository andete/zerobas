#!/usr/bin/env python3
"""D-XSLOTPRICE phases 0b+0c: PLANT the inter-slot probe (scaffold, reverted after).

0c adds a SPIN that burns time INSIDE the disk ROM without leaving it, so the
two arms differ in exactly one thing: which ROM is mapped at $4000 while the
time passes. $E771 spends it in MAIN page 1 (the call-back); $E772 spends it
in the disk ROM. htimi_guard should skip the second and not the first.

Anchored on TEXT. Refuses on a missing or non-unique anchor. Writes nothing
until every anchor has been resolved.
"""
import os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EDITS = []   # (path, anchor, replacement)

# ---- 1. main page 1: the call-back target (2 bytes of the 3 free) ----------
EDITS.append((
    "basic/main.asm",
    "; --- overflow guard: the image must not overrun the $8000 ceiling ----------",
    """; --- D-XSLOTPRICE phase-0b PROBE -- SCAFFOLD, NOT SHIPPED ------------------
; The whole point of the measurement: a main PAGE-1 routine whose only caller
; lives in disk.rom. Two bytes, so it fits the 3 B page-1 free measured today.
; HL arrives from the disk ROM pointing at a page-1 address whose byte DIFFERS
; between the two ROM images, so the value it returns names WHICH ROM was
; mapped at $4000 while this ran.
zb0b_calbak:
                ld      a,(hl)
                ret

; --- overflow guard: the image must not overrun the $8000 ceiling ----------""",
))

# ---- 2. declare it as a call-back import (phase 0a's machinery, first real use)
EDITS.append((
    "tools/gen_resident_abi.py",
    "REQUIRED_DISK_CALLBACK: list[str] = []",
    'REQUIRED_DISK_CALLBACK: list[str] = ["zb0b_calbak"]   # D-XSLOTPRICE 0b PROBE',
))

# ---- 3. disk side needs the BIOS CALSLT address ---------------------------
EDITS.append((
    "disk/equates.inc",
    "EXPTBL          equ     $FCC1   ; expanded-slot flags, 1 byte/primary, bit 7 = expanded",
    """EXPTBL          equ     $FCC1   ; expanded-slot flags, 1 byte/primary, bit 7 = expanded
CALSLT          equ     $001C   ; D-XSLOTPRICE 0b PROBE: BIOS inter-slot call (MSX2 TH)""",
))

# ---- 4. the probe body, in the free $607B-$75A5 corridor -------------------
EDITS.append((
    "disk/kernel.asm",
    "                ds      $75A5 - $, $00",
    """; --- D-XSLOTPRICE phase-0b PROBE -- SCAFFOLD, NOT SHIPPED ------------------
; One real inter-slot call, disk.rom -> main PAGE 1 -> back, in a loop whose
; length BASIC POKEs, so N=0 and N>0 are the SAME BUILD (no rebuild between the
; two readings -- the difference cannot be a different machine).
;   $E770 (RDBLK_DONE) <- the byte zb0b_calbak read at $4002. DOS-phase scratch,
;   $E771 (RDBLK_DONE+1) -> calls per hook entry, POKEd from BASIC.
; Both cells are BDOS $27 scratch, provably dead while BASIC runs.
ZB0B_RES        equ     $E770
ZB0B_CNT        equ     $E771
ZB0C_SPIN       equ     $E772           ; 0c: units of 65536 idle iterations spent
                                        ; in the disk ROM per hook entry, POKEd
ZB0C_EI         equ     $E773           ; 0c: nonzero -> EI for the spin. The hook
                                        ; arrives with interrupts OFF (the inter-slot
                                        ; CALLF leaves them so), which is itself the
                                        ; thing under test: with them off NOTHING can
                                        ; run, and htimi_guard never gets a turn.
ZB0B_WIT        equ     $4002           ; main=$10, disk=$34 -- a two-sided witness
zb0b_probe:
                push    bc
                push    de
                push    hl
                ld      a,(ZB0C_EI)
                or      a
                jr      z,zb0c_noei
                ei                      ; page 0 is main throughout, so $0038 is live
zb0c_noei:
                ld      a,(ZB0C_SPIN)
                or      a
                jr      z,zb0b_nospin
                ld      b,a
zb0c_outer:                             ; 0c: burn time INSIDE the disk ROM, so
                push    bc              ; page 1 is NOT main for the whole window
                ld      bc,0            ; 65536 iterations ~= 28 frames
zb0c_inner:
                dec     bc
                ld      a,b
                or      c
                jr      nz,zb0c_inner
                pop     bc
                djnz    zb0c_outer
zb0b_nospin:
                ld      a,(ZB0B_CNT)
                or      a
                jr      z,zb0b_end
                ld      b,a
zb0b_lp:
                push    bc
                ld      hl,ZB0B_WIT     ; ---- the per-call-site sequence starts
                ld      ix,zb0b_calbak
                ld      iy,(EXPTBL-1)   ; IYh = main-ROM slot id (MSX2 TH idiom)
                call    CALSLT
                ld      (ZB0B_RES),a    ; ---- and ends
                pop     bc
                djnz    zb0b_lp
zb0b_end:
                di                      ; hand back the interrupt state we were given
                pop     hl
                pop     de
                pop     bc
                scf
                ret

                ds      $75A5 - $, $00""",
))

# ---- 5. route the conversion hooks at the probe ----------------------------
EDITS.append((
    "disk/kernel.asm",
    """hk_present:
                scf
                ret""",
    """hk_present:
                jp      zb0b_probe      ; D-XSLOTPRICE 0b PROBE (was: scf / ret)""",
))


def main():
    # 🔴 Accumulate PER FILE. The first cut read every edit from the ORIGINAL
    # text and wrote them all at the end, so two edits to one file silently
    # discarded the first -- caught only because pasmo then refused an
    # undefined symbol. Edits to the same file must compose.
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
    print(f"OK: {len(staged)} file(s) planted, {len(EDITS)} edit(s)")


if __name__ == "__main__":
    main()
