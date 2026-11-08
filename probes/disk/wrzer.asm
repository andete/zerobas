; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; WRZER.COM -- D-WRZER (TODO.md): what BDOS $28 WRZER does to the records an
; extension adds, against $22 WRRND doing the same write.
;
; For each of two fresh files -- Z.DAT written by WRZER, R.DAT by WRRND --
; (after the clusters they will take are overwritten with $CC by WRABS)
; FMAKE, RS := 128, RR := 20, one 128-byte record of $55 from the DTA, FCLOSE;
; then FOPEN, RS := 128, and RDRND records 0, 8, 16, 20 into four 128-byte buffers.
; Records 0-19 are the ones the extension added: WRZER's published contract is
; that they are zero-filled; WRRND makes no promise. Every call's A is kept.
; Self-loop at `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code; the function numbers and register contracts are
; the published MSX-DOS 1 function list. No kernel byte is read.
;
; Build: pasmo --bin wrzer.asm wrzer.com wrzer.sym

                org     $0100

BDOS            equ     $0005

start:
                ; dirty the free space first: the clusters the two files will take
                ; ($155.. on this image -- the allocator moves forward, so a deleted
                ; file's clusters are NOT reused; measured) get $CC by WRABS, one
                ; sector a call, 32 sectors from sector 692 (= 14 + ($155-2)*2, the
                ; 720 KB geometry). What WRRND then leaves in the records an
                ; extension adds is visible; WRZER's contract says zeros.
                ld      de, gdata
                ld      c, $1A
                call    BDOS
                ld      hl, 692
                ld      (absec), hl
                ld      b, 32
dirty:
                push    bc
                ld      de, (absec)
                ld      h, 1                    ; one sector
                ld      l, 0                    ; drive A:
                ld      c, $30                  ; WRABS
                call    BDOS
                ld      hl, (absec)
                inc     hl
                ld      (absec), hl
                pop     bc
                djnz    dirty
                ld      hl, zfcb
                ld      a, $28
                ld      de, zbuf
                call    one_file
                ld      hl, rfcb
                ld      a, $22
                ld      de, rbuf
                call    one_file
done:
                jr      done

; one_file -- HL = the FCB, A = the write function, DE = 4 x 128 B read-back
; buffers. Appends each call's A to `codes` (codes_ptr).
one_file:
                ld      (wfn), a
                ld      (fcbp), hl
                ld      (rbp), de
                ld      de, wdata               ; the record to write
                ld      c, $1A
                call    BDOS
                ld      de, (fcbp)
                ld      c, $16                  ; FMAKE
                call    BDOS
                call    code
                call    set_rs
                ld      a, 20                   ; record 20: records 0-19 are ADDED (two
                call    set_rr                  ; whole clusters and part of a third)
                ld      de, (fcbp)
                ld      a, (wfn)
                ld      c, a                    ; WRZER or WRRND
                call    BDOS
                call    code
                ld      de, (fcbp)
                ld      c, $10                  ; FCLOSE
                call    BDOS
                call    code
                ld      de, (fcbp)
                ld      c, $0F                  ; FOPEN
                call    BDOS
                call    code
                call    set_rs
                ld      hl, rdrecs
rd_loop:
                ld      a, (hl)
                inc     hl
                push    hl
                call    set_rr
                ld      de, (rbp)
                ld      c, $1A
                call    BDOS
                ld      de, (fcbp)
                ld      c, $21                  ; RDRND
                call    BDOS
                call    code
                ld      hl, (rbp)
                ld      de, 128
                add     hl, de
                ld      (rbp), hl
                pop     hl
                ld      a, (hl)
                cp      $FF
                jr      nz, rd_loop
                ret
rdrecs:         db      0, 8, 16, 20, $FF       ; one record from each added cluster + the written one
absec:          dw      0

set_rs:                                         ; FCB +14..15 := 128
                ld      hl, (fcbp)
                ld      de, 14
                add     hl, de
                ld      (hl), 128
                inc     hl
                ld      (hl), 0
                ret
set_rr:                                         ; FCB +33..36 := A, 0, 0, 0
                ld      hl, (fcbp)
                ld      de, 33
                add     hl, de
                ld      (hl), a
                inc     hl
                ld      (hl), 0
                inc     hl
                ld      (hl), 0
                inc     hl
                ld      (hl), 0
                ret
code:                                           ; append A to codes
                ld      hl, (codes_ptr)
                ld      (hl), a
                inc     hl
                ld      (codes_ptr), hl
                ret

wfn:            db      0
fcbp:           dw      0
rbp:            dw      0
codes_ptr:      dw      codes
wdata:          ds      128, $55

; ---------------------------------------------------------------------------
; captured block $0400-$089F: codes (16 B), the three FCBs, both read-back areas
; (the read buffers are pre-filled $AA so an unread record shows)
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
codes:          ds      16, $EE                 ; $0400: A of each call, in order
zfcb:           db      0, "Z       ", "DAT"    ; $0410
                ds      37 - 12, 0
                ds      $0440 - $, $00
rfcb:           db      0, "R       ", "DAT"    ; $0440
                ds      37 - 12, 0
                ds      $04A0 - $, $00
zbuf:           ds      512, $AA                ; $04A0-$069F: Z.DAT records 0-3
rbuf:           ds      512, $AA                ; $06A0-$089F: R.DAT records 0-3
gdata:          ds      512, $CC                ; $08A0-$0A9F: the dirtying sector
