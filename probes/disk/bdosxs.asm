; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; BDOSXS.COM -- D-DISKCONTRACT gap 7 (2026-11-17): a DISK SWAP, as a program that asks
; for another disk sees it. DSKENT / DSKCHG compare DSKCHG only while the disk stays put
; (B = 1 unchanged / 0 unknown); the "changed" path (B = $FF) was never reached.
;
; The program reads the directory (SFIRST, so the BDOS has the first disk), records
; DSKCHG (record 0), then waits on CONIN. The harness swaps drive A's image at --swap-at
; (`diska`) and types a key after it; the program then records DSKCHG again (record 1),
; and SFIRSTs "SWAPPED TXT" -- a file only the second disk holds (record 2: A, and the
; DTA's name): does the BDOS see the new disk? DSKCHG is called through CALSLT in the
; disk ROM's slot (DSKSLT), A = 0, B = 0, C = $F9, HL = a DPB buffer; the record keeps
; Cy and B (the contract), the DPB is captured after.
;
; CLEAN-ROOM: 100% own code; the published BDOS / disk-ROM entries. Nothing of the
; reference read.
;
; Build: pasmo --bin bdosxs.asm bdosxs.com bdosxs.sym

                org     $0100

BDOS            equ     $0005
CALSLT          equ     $001C
DSKSLT          equ     $FB22

start:
                jr      begin                   ; $0102 = $5C: a distinctive arm signature
                db      $5C
begin:
                ld      de, dta
                ld      c, $1A                  ; SETDTA
                call    BDOS
                ld      de, afcb
                ld      c, $11                  ; SFIRST *.* on the first disk
                call    BDOS
                ld      hl, regs+0
                call    chg                     ; record 0: before the swap
                ld      c, $01                  ; CONIN: the harness swaps, then types a key
                call    BDOS
                ld      hl, regs+4
                call    chg                     ; record 1: after the swap
                ld      de, sfcb
                ld      c, $11                  ; SFIRST SWAPPED.TXT: is the new disk seen?
                call    BDOS
                ld      (regs+8), a             ; record 2: SFIRST's A ($00 found / $FF)
                ld      a, $A5
                ld      (regs+9), a             ; the run finished
                jp      done

; chg -- DSKCHG drive A through CALSLT; Cy -> (HL+0), B -> (HL+1)
chg:
                ld      (recp), hl
                ld      a, (DSKSLT)
                ld      iyh, a
                ld      ix, $4013
                xor     a
                ld      b, 0
                ld      c, $F9
                ld      hl, dpb
                call    CALSLT
                ei
                ld      d, b
                push    af
                pop     bc
                ld      hl, (recp)
                ld      a, c
                and     1
                ld      (hl), a                 ; Cy
                inc     hl
                ld      (hl), d                 ; B: 1 unchanged / 0 unknown / $FF changed
                ret

recp:           dw      0
afcb:           db      0, "????????", "???"
                ds      37 - 12, 0
sfcb:           db      0, "SWAPPED ", "TXT"
                ds      37 - 12, 0

                ds      $0330 - $, $00
done:
                jr      done                    ; the capture anchor, pinned at $0330
                ds      $0340 - $, $00
regs:           ds      16, $EE                 ; rec 0 (Cy, B), rec 1 at +4, SFIRST A +8, $A5 +9
dpb:            ds      32
dta:            ds      33
