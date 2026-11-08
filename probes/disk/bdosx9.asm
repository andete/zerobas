; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX9.COM -- D-ENTRYTIERS step 2 (TODO.md): the BDOS functions the entry
; table (tools/entry_table.py) found NOT MEASURED, non-interactive half:
; CURDRV $19, SELDSK $0E, ALLOC $1B, SNEXT $12 (after SFIRST $11), CONOUT $02,
; WRZER $28 (after FMAKE $16, then FCLOSE $10), AUXOUT $04, and the seven
; numbers MSX-DOS 1 does not use ($1C-$20, $25, $29), LAST -- an unused number
; that misbehaves on one machine then cannot hide the rows before it. AUXIN $03
; (may wait for a device), BUFIN $0A (needs typed keys) and LSTOUT $05
; (lstoutx.asm) are other slices.
;
; Same shape as bdosx2.asm: each call's outward A/B/C/D/E/H/L into an 8-byte
; record (byte 0 = the function number), then a self-loop at `done` -- the
; disk_probe_diff.py `capture --at` anchor. Besides `regs`, the two search DTAs
; and the written file's FCB are captured: what SFIRST / SNEXT returned and what
; WRZER left in the FCB are the contract, not only the registers.
;
; CLEAN-ROOM: 100% own code. Function numbers and register contracts are the
; published MSX-DOS 1 function list (MSX2 Technical Handbook ch. 3; the
; map.grauw.nl MSX-DOS function spec, whose DOS-1 subset is the same). No
; kernel byte is read; the CF-3300 is a black box run side by side.
;
; Build: pasmo --bin bdosx9.asm bdosx9.com bdosx9.sym

                org     $0100

BDOS            equ     $0005

start:
                ; --- record 0: $19 CURDRV ---
                ld      c, $19
                call    BDOS
                ld      ix, regs+0*8
                ld      (ix+0), $19
                call    snap

                ; --- record 1: $0E SELDSK E = 0 (drive A:) ---
                ld      e, 0
                ld      c, $0E
                call    BDOS
                ld      ix, regs+1*8
                ld      (ix+0), $0E
                call    snap

                ; --- record 2: $19 CURDRV again (after the select) ---
                ld      c, $19
                call    BDOS
                ld      ix, regs+2*8
                ld      (ix+0), $19
                call    snap

                ; --- record 3: $1B ALLOC E = 0 (the default drive) ---
                ; A = sectors / cluster, BC = sector size, DE = clusters,
                ; HL = free clusters (IX / IY = addresses: not compared)
                ld      e, 0
                ld      c, $1B
                call    BDOS
                ld      ix, regs+3*8
                ld      (ix+0), $1B
                call    snap

                ; --- record 4: $11 SFIRST "????????.???" into DTA 1 ---
                ld      de, dta1
                ld      c, $1A
                call    BDOS
                ld      de, sfcb
                ld      c, $11
                call    BDOS
                ld      ix, regs+4*8
                ld      (ix+0), $11
                call    snap

                ; --- record 5: $12 SNEXT into DTA 2 ---
                ld      de, dta2
                ld      c, $1A
                call    BDOS
                ld      c, $12
                call    BDOS
                ld      ix, regs+5*8
                ld      (ix+0), $12
                call    snap

                ; --- record 6: $02 CONOUT E = '*' ---
                ld      e, '*'
                ld      c, $02
                call    BDOS
                ld      ix, regs+6*8
                ld      (ix+0), $02
                call    snap

                ; --- record 7: $16 FMAKE ZERO.DAT ---
                ld      de, dbuf
                ld      c, $1A
                call    BDOS
                ld      de, wfcb
                ld      c, $16
                call    BDOS
                ld      ix, regs+7*8
                ld      (ix+0), $16
                call    snap

                ; --- record 8: $28 WRZER, record 0 of 128 B (RS / RR set below) ---
                ld      hl, 128
                ld      (wfcb+14), hl
                xor     a
                ld      (wfcb+33), a
                ld      (wfcb+34), a
                ld      (wfcb+35), a
                ld      (wfcb+36), a
                ld      de, wfcb
                ld      c, $28
                call    BDOS
                ld      ix, regs+8*8
                ld      (ix+0), $28
                call    snap

                ; --- record 9: $10 FCLOSE ---
                ld      de, wfcb
                ld      c, $10
                call    BDOS
                ld      ix, regs+9*8
                ld      (ix+0), $10
                call    snap

                ; --- record 10: $04 AUXOUT E = 'A' ---
                ld      e, 'A'
                ld      c, $04
                call    BDOS
                ld      ix, regs+10*8
                ld      (ix+0), $04
                call    snap

                ; --- records 11-17: the unused numbers, DE = HL = 0 on entry ---
                ld      b, 0
                ld      hl, unused
                ld      ix, regs+11*8
un_loop:
                ld      a, (hl)
                or      a
                jr      z, done
                push    hl
                push    ix
                ld      c, a
                ld      (ix+0), a
                ld      de, 0
                ld      hl, 0
                call    BDOS
                pop     ix
                call    snap
                ld      de, 8
                add     ix, de
                pop     hl
                inc     hl
                jr      un_loop

done:
                jr      done                    ; the disk_probe_diff.py anchor (arm-gated
                                                ; on $0102 == this program's 3rd byte, as
                                                ; bdosx2.asm)

; snap -- A, B, C, D, E, H, L into (ix+1)..(ix+7); (ix+0) is the caller's.
snap:
                ld      (ix+1), a
                ld      (ix+2), b
                ld      (ix+3), c
                ld      (ix+4), d
                ld      (ix+5), e
                ld      (ix+6), h
                ld      (ix+7), l
                ret

unused:         db      $1C, $1D, $1E, $1F, $20, $25, $29, 0

; the search FCB: drive 0 (default), name and extension all '?'
sfcb:           db      0, "????????", "???"
                ds      37 - 12, 0

; ---------------------------------------------------------------------------
; captured block $0400-$0517: regs (18 x 8 = $90), the two DTAs ($30 each: drive
; byte + the 32-byte entry, rounded), the written FCB (37 B at $04F0)
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
regs:           ds      18*8                    ; $0400-$048F
                ds      $0490 - $, $00
dta1:           ds      $30                     ; $0490-$04BF
dta2:           ds      $30                     ; $04C0-$04EF
wfcb:           db      0, "ZERO    ", "DAT"   ; $04F0-$0514: the file WRZER writes
                ds      37 - 12, 0
                ds      $0580 - $, $00
dbuf:           ds      128, $55                ; WRZER's DTA, $55 so a zero-fill shows
