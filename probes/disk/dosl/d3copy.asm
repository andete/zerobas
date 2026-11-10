; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; D3COPY.COM -- D-DOSLADDER rung D3 (TODO.md): what COPY does. COMMAND.COM is
; copied record by record (SEQREAD / SEQWRITE) to C.COM, both FCLOSEd; C.COM is
; then re-opened and read to the end (records, byte sum), FSIZE'd, and found with
; SFIRST. Captured -- the CONTRACT only: every call's A, both record counts and
; sums, C.COM's size from its FCB after the copy and from its directory entry
; (SFIRST's DTA +28..31), and FSIZE's random record (+33..35).
; Self-loop at `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 BDOS functions. COMMAND.COM is
; data copied through them, never decoded.
;
; Build: probes/disk/build_dosl_disk.py --prog d3copy

                org     $0100

BDOS            equ     $0005

                jr      start
                db      $D3                     ; $0102: the capture's arm signature (unique;
                                                ; COMMAND.COM has $02 there -- D6's false anchor)
start:
                ld      de, buf
                ld      c, $1A                  ; SETDTA
                call    BDOS
                ld      de, sfcb
                ld      c, $0F                  ; FOPEN COMMAND.COM
                call    BDOS
                ld      (cap+0), a
                ld      de, dfcb
                ld      c, $13                  ; FDEL C.COM (none yet: $FF)
                call    BDOS
                ld      (cap+1), a
                ld      de, dfcb
                ld      c, $16                  ; FMAKE C.COM
                call    BDOS
                ld      (cap+2), a
cp_lp:
                ld      de, sfcb
                ld      c, $14                  ; SEQREAD
                call    BDOS
                ld      (cap+3), a
                or      a
                jr      nz, cp_end
                ld      de, dfcb
                ld      c, $15                  ; SEQWRITE
                call    BDOS
                ld      (cap+4), a
                or      a
                jr      nz, cp_end
                ld      hl, (cap+5)
                inc     hl
                ld      (cap+5), hl             ; records copied
                call    sum
                ld      (cap+7), de
                jr      cp_lp
cp_end:
                ld      de, sfcb
                ld      c, $10
                call    BDOS
                ld      (cap+9), a              ; FCLOSE source
                ld      de, dfcb
                ld      c, $10
                call    BDOS
                ld      (cap+10), a             ; FCLOSE copy
                ld      hl, (dfcb+16)
                ld      (cap+11), hl
                ld      hl, (dfcb+18)
                ld      (cap+13), hl            ; the copy's size, its FCB after close
                ; --- re-read the copy -----------------------------------------
                ld      hl, rfcb
                ld      de, dfcb
                ld      bc, 37
                ldir                            ; a fresh FCB for C.COM
                ld      hl, 0
                ld      (sumacc), hl
                ld      de, dfcb
                ld      c, $0F
                call    BDOS
                ld      (cap+15), a             ; FOPEN C.COM
rr_lp:
                ld      de, dfcb
                ld      c, $14
                call    BDOS
                or      a
                jr      nz, rr_end
                ld      hl, (cap+16)
                inc     hl
                ld      (cap+16), hl            ; records read back
                call    sum
                ld      (cap+18), de
                jr      rr_lp
rr_end:
                ld      (cap+20), a
                ld      de, dfcb
                ld      c, $23                  ; FSIZE
                call    BDOS
                ld      (cap+21), a
                ld      hl, (dfcb+33)
                ld      (cap+22), hl
                ld      a, (dfcb+35)
                ld      (cap+24), a             ; FSIZE's record count
                ld      de, dta2
                ld      c, $1A
                call    BDOS
                ld      de, rfcb
                ld      c, $11                  ; SFIRST C.COM
                call    BDOS
                ld      (cap+25), a
                ld      hl, (dta2+28)
                ld      (cap+26), hl
                ld      hl, (dta2+30)
                ld      (cap+28), hl            ; its directory entry's size
done:
                jr      done

; sum -- DE := (sumacc) + the 128 bytes at buf (16-bit); sumacc updated
sum:
                ld      hl, buf
                ld      de, (sumacc)
                ld      b, 128
sm_lp:
                ld      a, e
                add     a, (hl)
                ld      e, a
                jr      nc, sm_nc
                inc     d
sm_nc:
                inc     hl
                djnz    sm_lp
                ld      (sumacc), de
                ret

sumacc:         dw      0
sfcb:           db      0, "COMMAND COM"
                ds      37 - 12, 0
dfcb:           db      0, "C       COM"
                ds      37 - 12, 0
rfcb:           db      0, "C       COM"
                ds      37 - 12, 0
buf:            ds      128, 0
dta2:           ds      64, 0

; ---------------------------------------------------------------------------
; captured block $0400-$041F
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
cap:            ds      32, $00
cap_end:
