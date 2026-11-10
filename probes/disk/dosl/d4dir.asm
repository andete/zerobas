; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; D4DIR.COM -- D-DOSLADDER rung D4 (TODO.md): what DIR does, on what the boot disk
; holds: "*.COM" through SFIRST / SNEXT -- each match's name (11 B) and size (its
; DTA's +29..32) in order, at most 3 recorded (a guard) --, the first match's DTA raw
; (33 B at cap+72), a count of "*.SYS" and of "*.*", and ALLOC ($1B: A = sectors per
; cluster, BC = sector size, DE = clusters, HL = free clusters). Self-loop at `done`.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 BDOS functions.
;
; Build: probes/disk/build_dosl_disk.py --prog d4dir

                org     $0100

BDOS            equ     $0005

start:
                ld      de, dta
                ld      c, $1A
                call    BDOS
                ; --- "*.TXT": names and sizes ---------------------------------------
                ld      hl, cap+4               ; (count at cap+3)
                ld      (outp), hl              ; NOT IX: BDOS does not keep it (the
                                                ; CF-3300 returns IX = its DPB; the first
                                                ; cut wrote names through it and hung)
                ld      de, scom
                ld      c, $11                  ; SFIRST
s1_lp:
                call    BDOS
                ld      (cap+60), a             ; the last search's A
                inc     a
                jr      z, s1_end               ; $FF: no (more) match
                ld      hl, cap+3
                inc     (hl)
                ld      a, (hl)
                cp      1
                jr      nz, s1_nraw
                push    hl
                ld      hl, dta
                ld      de, cap+72
                ld      bc, 33
                ldir                            ; the first match's DTA, raw (33 B)
                pop     hl
                ld      a, (hl)
s1_nraw:
                cp      4
                jr      nc, s1_end              ; at most 3 recorded (a guard, not a contract)
                ld      hl, dta+1               ; the name
                ld      de, (outp)
                ld      bc, 11
                ldir
                ld      hl, dta+29              ; the size (4 B)
                ld      bc, 4
                ldir
                ld      (outp), de
                ld      de, scom
                ld      c, $12                  ; SNEXT
                jr      s1_lp
s1_end:
                ld      de, sq
                call    count
                ld      (cap+61), a             ; "?.TXT"
                ld      de, sall
                call    count
                ld      (cap+62), a             ; "*.*"
                ld      e, 0
                ld      c, $1B                  ; ALLOC, the default drive
                call    BDOS
                ld      (cap+63), a
                ld      (cap+64), bc
                ld      (cap+66), de
                ld      (cap+68), hl
done:
                jr      done

; mkone -- FMAKE the FCB at HL, one SEQWRITE, FCLOSE; A = the three A's OR'd
mkone:
                ld      (mk_fcb), hl
                ex      de, hl
                ld      c, $16
                call    BDOS
                ld      b, a
                push    bc
                ld      de, (mk_fcb)
                ld      c, $15
                call    BDOS
                pop     bc
                or      b
                ld      b, a
                push    bc
                ld      de, (mk_fcb)
                ld      c, $10
                call    BDOS
                pop     bc
                or      b
                ret

; count -- matches of the FCB at DE through SFIRST / SNEXT; A = how many
count:
                ld      (ct_fcb), de
                ld      b, 0
                ld      c, $11
ct_lp:
                push    bc
                ld      de, (ct_fcb)
                call    BDOS
                pop     bc
                inc     a
                jr      z, ct_end
                inc     b
                ld      c, $12
                jr      ct_lp
ct_end:
                ld      a, b
                ret

outp:           dw      0
mk_fcb:         dw      0
ct_fcb:         dw      0
fa:             db      0, "A       TXT"
                ds      37 - 12, 0
fb:             db      0, "B       TXT"
                ds      37 - 12, 0
fc:             db      0, "AB      DAT"
                ds      37 - 12, 0
stxt:           db      0, "????????TXT"
                ds      37 - 12, 0
scom:           db      0, "????????COM"
                ds      37 - 12, 0
sq:             db      0, "????????SYS"
                ds      37 - 12, 0
sall:           db      0, "???????????"
                ds      37 - 12, 0
rec:            ds      128, $41
dta:            ds      64, 0

; ---------------------------------------------------------------------------
; captured block $0400-$046B
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
cap:            ds      108, $00
cap_end:
