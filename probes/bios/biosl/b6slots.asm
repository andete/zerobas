; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; B6SLOTS -- D-BIOSLADDER rung B6 (TODO.md): the inter-slot entries a ROM uses to
; find RAM for page 2 and to read its own slot. A 16 KB "AB" cartridge; INIT runs it.
; The machines' slot MAPS differ (hardware, not BIOS), so the rung records what a
; program can rely on -- outcomes and published register contracts -- never a raw
; slot number:
;   1. this cartridge's own slot (page 1, from port $A8 and EXPTBL / SLTTBL, built
;      into the published slot-ID form F000SSPP); RDSLT of its "AB" header (CAP+0, +1);
;   2. page 3's RAM slot, the same way; ENASLT it into page 2 (H = $80); then a
;      byte written and read back at $8000 and $BFFF (CAP+2, +3: $5A / $A5 = it is
;      RAM); whether interrupts are on after ENASLT (CAP+4: P/V of `ld a,i`);
;   3. WRSLT $C3 to that RAM slot at $8001, RDSLT it back (CAP+5), and RDSLT's
;      register contract around it: A, and whether HL / DE / BC came back as passed
;      (CAP+6..8: 1 = kept);
;   4. EXPTBL's bit 7 for slot 0 and slot 3 (CAP+9, +10: expanded or not -- recorded,
;      excused if the hardware differs).
; CLEAN-ROOM: 100% own code; only published BIOS entries, work-area cells and port $A8.
;
; @timeout 40

RDSLT   equ     $000C
WRSLT   equ     $0014
ENASLT  equ     $0024
EXPTBL  equ     $FCC1
SLTTBL  equ     $FCC5

DONE    equ     $E000
CAP     equ     $E001
SLOT1   equ     $E200           ; this cartridge's slot ID
SLOT3   equ     $E201           ; page 3's RAM slot ID

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                ; --- 1: our own slot -----------------------------------------------------
                in      a, ($A8)
                rrca
                rrca                        ; page 1's primary slot in bits 0-1
                call    slot_id             ; B = the page (1)
                ld      (SLOT1), a
                ld      hl, $4000
                call    RDSLT
                ld      (CAP+0), a          ; 'A'
                ld      a, (SLOT1)
                ld      hl, $4001
                call    RDSLT
                ld      (CAP+1), a          ; 'B'
                ; --- 2: page 3's RAM into page 2 ------------------------------------------
                in      a, ($A8)
                rlca
                rlca                        ; page 3's primary slot in bits 0-1
                ld      b, 3
                call    slot_id_b
                ld      (SLOT3), a
                ld      h, $80
                call    ENASLT
                ld      a, i
                push    af
                ld      a, $5A
                ld      ($8000), a
                ld      a, $A5
                ld      ($BFFF), a
                ld      a, ($8000)
                ld      (CAP+2), a
                ld      a, ($BFFF)
                ld      (CAP+3), a
                pop     hl
                ld      a, l
                and     4
                ld      (CAP+4), a
                ei
                ; --- 3: WRSLT / RDSLT -----------------------------------------------------
                ld      a, (SLOT3)
                ld      hl, $8001
                ld      e, $C3
                call    WRSLT
                ld      a, (SLOT3)
                ld      hl, $8001
                ld      de, $1234
                ld      bc, $5678
                call    RDSLT
                ld      (CAP+5), a
                ld      a, h
                cp      $80
                jr      nz, hl_bad
                ld      a, l
                cp      $01
                jr      nz, hl_bad
                ld      a, 1
                ld      (CAP+6), a
hl_bad:
                ld      a, d
                cp      $12
                jr      nz, de_bad
                ld      a, e
                cp      $34
                jr      nz, de_bad
                ld      a, 1
                ld      (CAP+7), a
de_bad:
                ld      a, b
                cp      $56
                jr      nz, bc_bad
                ld      a, c
                cp      $78
                jr      nz, bc_bad
                ld      a, 1
                ld      (CAP+8), a
bc_bad:
                ; --- 4: expanded? ---------------------------------------------------------
                ld      a, (EXPTBL+0)
                and     $80
                ld      (CAP+9), a
                ld      a, (EXPTBL+3)
                and     $80
                ld      (CAP+10), a
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; slot_id -- A bits 0-1 = a primary slot, page 1 (B := 1); slot_id_b: page in B.
; -> A = the slot ID: primary in bits 0-1; if EXPTBL says it is expanded, bit 7 set
; and the secondary slot for page B (from SLTTBL) in bits 2-3.
slot_id:
                ld      b, 1
slot_id_b:
                and     3
                ld      c, a
                ld      hl, EXPTBL
                add     a, l
                ld      l, a                ; HL = EXPTBL + primary (no carry: $C1..$C4)
                ld      a, (hl)
                and     $80
                jr      z, sid_plain
                inc     hl
                inc     hl
                inc     hl
                inc     hl                  ; SLTTBL + primary
                ld      a, (hl)
sid_shift:
                rrca
                rrca
                djnz    sid_shift           ; the page's secondary now in bits 0-1
                and     3
                rlca
                rlca                        ; -> bits 2-3
                or      c
                or      $80
                ret
sid_plain:
                ld      a, c
                ret
