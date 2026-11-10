; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; D7SORT.COM -- D-DOSLADDER rung D7 (TODO.md): what an editor / sort does to files.
; LINES.TXT: 20 records written by SEQWRITE in REVERSE order (record k holds 128 x
; (20 - k)), FCLOSEd, read back by SEQREAD into memory; the records sorted (by
; their byte, ascending) and written to SORTED.TXT by ONE WRBLK of 20 x 128; the
; file then TRUNCATED to 10 records by WRBLK of 0 records at RR = 10; FCLOSE. Then
; LINES.TXT re-opened and one record APPENDED past its end by WRRND (RR = 20);
; FCLOSE. Finally SORTED.TXT is FSIZE'd and its records 0 and 9 read by RDRND.
; Captured, the contract only: every call's A, the records read back, the sizes
; after each FCLOSE, FSIZE's RR and the two records' first bytes and sums.
; Self-loop at `done` -- the capture anchor.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 BDOS functions.
;
; Build: probes/disk/build_dosl_disk.py --prog d7sort

                org     $0100

BDOS            equ     $0005
NREC            equ     20

ARMSIG          equ     $D7
                jr      start
                db      $00                     ; $0102: the arm signature, written AT RUN
                                                ; TIME below -- D7 is big enough that MSX-DOS
                                                ; was still loading it when other code passed
                                                ; `done` with a static $D7 here (a false anchor)
start:
                ld      a, ARMSIG
                ld      ($0102), a
armpt:                                          ; the capture arms HERE (--arm-addr)
                ; --- LINES.TXT, 20 records in reverse order -------------------------
                ld      de, fl
                ld      c, $16
                call    BDOS
                ld      (cap+0), a
                ld      de, rec
                ld      c, $1A
                call    BDOS
                ld      b, NREC
wl_lp:
                push    bc
                ld      a, b                    ; 20 .. 1: reverse order
                call    fill
                ld      de, fl
                ld      c, $15                  ; SEQWRITE
                call    BDOS
                ld      hl, cap+1
                or      (hl)
                ld      (hl), a
                pop     bc
                djnz    wl_lp
                ld      de, fl
                ld      c, $10
                call    BDOS
                ld      (cap+2), a
                ld      hl, (fl+16)
                ld      (cap+3), hl             ; LINES.TXT's size after FCLOSE
                ; --- read it all back -----------------------------------------------
                ld      hl, fl0
                ld      de, fl
                ld      bc, 37
                ldir
                ld      de, fl
                ld      c, $0F
                call    BDOS
                ld      (cap+5), a
                ld      hl, mem
                ld      (memp), hl
rd_lp:
                ld      de, (memp)
                ld      c, $1A
                call    BDOS
                ld      de, fl
                ld      c, $14                  ; SEQREAD
                call    BDOS
                or      a
                jr      nz, rd_end
                ld      hl, cap+6
                inc     (hl)                    ; records read
                ld      hl, (memp)
                ld      de, 128
                add     hl, de
                ld      (memp), hl
                jr      rd_lp
rd_end:
                ld      (cap+7), a              ; the final SEQREAD's A
                ; --- sort the records (by their byte; a bubble pass per record) ------
                ld      b, NREC - 1
so_out:
                push    bc
                ld      hl, mem
                ld      b, NREC - 1
so_in:
                push    bc
                push    hl
                ld      de, 128
                add     hl, de
                ex      de, hl                  ; DE = the next record
                pop     hl
                ld      a, (de)
                cp      (hl)
                jr      nc, so_ok
                push    hl
                push    de
                ld      b, 128
so_sw:
                ld      a, (de)
                ld      c, (hl)
                ld      (hl), a
                ld      a, c
                ld      (de), a
                inc     hl
                inc     de
                djnz    so_sw
                pop     de
                pop     hl
so_ok:
                ex      de, hl                  ; HL = the next record
                pop     bc
                djnz    so_in
                pop     bc
                djnz    so_out
                ; --- SORTED.TXT: one WRBLK of 20 x 128, then truncate to 10 -----------
                ld      de, fs
                ld      c, $16
                call    BDOS
                ld      (cap+8), a
                ld      hl, 128
                ld      (fs+14), hl             ; RS := 128
                ld      de, mem
                ld      c, $1A
                call    BDOS
                ld      de, fs
                ld      hl, NREC
                ld      c, $26                  ; WRBLK 20 records
                call    BDOS
                ld      (cap+9), a
                ld      a, 10
                ld      (fs+33), a
                xor     a
                ld      (fs+34), a
                ld      (fs+35), a
                ld      de, fs
                ld      hl, 0
                ld      c, $26                  ; WRBLK 0 records at RR = 10: truncate
                call    BDOS
                ld      (cap+10), a
trunc:                                  ; (a second anchor: the disk between WRBLK 0 and FCLOSE)
                ld      de, fs
                ld      c, $10
                call    BDOS
                ld      (cap+11), a
                ld      hl, (fs+16)
                ld      (cap+12), hl            ; SORTED.TXT's size after FCLOSE
                ; --- LINES.TXT: append one record by WRRND --------------------------
                ld      hl, fl0
                ld      de, fl
                ld      bc, 37
                ldir
                ld      de, fl
                ld      c, $0F
                call    BDOS
                ld      (cap+14), a
                ld      de, rec
                ld      c, $1A
                call    BDOS
                ld      a, $77
                call    fill
                ld      a, NREC
                ld      (fl+33), a
                ld      de, fl
                ld      c, $22                  ; WRRND record 20
                call    BDOS
                ld      (cap+15), a
                ld      de, fl
                ld      c, $10
                call    BDOS
                ld      (cap+16), a
                ld      hl, (fl+16)
                ld      (cap+17), hl            ; LINES.TXT's size after the append
                ; --- SORTED.TXT: FSIZE, RDRND 0 and 9 ---------------------------------
                ld      hl, fs0
                ld      de, fs
                ld      bc, 37
                ldir
                ld      de, fs
                ld      c, $23
                call    BDOS
                ld      (cap+19), a
                ld      a, (fs+33)
                ld      (cap+20), a             ; FSIZE's record count (low byte)
                ld      de, fs
                ld      c, $0F
                call    BDOS
                ld      (cap+21), a
                xor     a
                call    rdone
                ld      (cap+22), a
                ld      a, (rec)
                ld      (cap+23), a             ; record 0's byte
                ld      a, 9
                call    rdone
                ld      (cap+24), a
                ld      a, (rec)
                ld      (cap+25), a             ; record 9's byte
                ld      a, 7
                call    rdone
                ld      (cap+26), a
                ld      a, (rec)
                ld      (cap+27), a             ; record 7's byte (the first cluster)
                ld      a, 8
                call    rdone
                ld      (cap+28), a
                ld      a, (rec)
                ld      (cap+29), a             ; record 8's byte (the second)
done:
                jr      done

; fill -- rec := 128 x A
fill:
                ld      hl, rec
                ld      b, 128
fi_lp:
                ld      (hl), a
                inc     hl
                djnz    fi_lp
                ret

; rdone -- RDRND record A of SORTED.TXT into rec (pre-filled $EE); A = its A
rdone:
                ld      (fs+33), a
                xor     a
                ld      (fs+34), a
                ld      (fs+35), a
                ld      a, $EE
                call    fill
                ld      de, rec
                ld      c, $1A
                call    BDOS
                ld      de, fs
                ld      c, $21
                jp      BDOS

memp:           dw      0
fl:             db      0, "LINES   TXT"
                ds      37 - 12, 0
fl0:            db      0, "LINES   TXT"
                ds      37 - 12, 0
fs:             db      0, "SORTED  TXT"
                ds      37 - 12, 0
fs0:            db      0, "SORTED  TXT"
                ds      37 - 12, 0
rec:            ds      128, 0

; ---------------------------------------------------------------------------
; captured block $0400-$041F, then the record memory
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
cap:            ds      32, $00
cap_end:
mem:            ds      NREC * 128, 0
