; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; D5RENDEL.COM -- D-DOSLADDER rung D5 (TODO.md): what REN and DEL do, wildcards and
; the error paths. X1.TMP, X2.TMP and Y.TMP are made (FMAKE / FCLOSE); then
;   FREN "X?.TMP" -> "Z?.TMP" (a wildcard rename), FREN of a missing file, FREN onto
;   a name that exists (Y.TMP -> Z1.TMP), the count of "Z?.TMP" and of "?.TMP",
;   FDEL "?.TMP" (Y.TMP), FDEL "Z?.TMP", FDEL of a missing file, the count of
;   "*.TMP" left.
; Captured, the contract only: every call's A and the counts. No pointer is kept in
; IX across a BDOS call (the CF-3300 returns IX = its DPB; D4's lesson).
; Self-loop at `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 BDOS functions.
;
; Build: probes/disk/build_dosl_disk.py --prog d5rendel

                org     $0100

BDOS            equ     $0005

start:
                ld      de, dta
                ld      c, $1A
                call    BDOS
                ld      hl, fx1
                call    mk
                ld      (cap+0), a
                ld      hl, fx2
                call    mk
                ld      (cap+1), a
                ld      hl, fy
                call    mk
                ld      (cap+2), a
                ld      de, renx
                ld      c, $17                  ; FREN X?.TMP -> Z?.TMP
                call    BDOS
                ld      (cap+3), a
                ld      de, renm
                ld      c, $17                  ; FREN of a missing file
                call    BDOS
                ld      (cap+4), a
                ld      de, reny
                ld      c, $17                  ; FREN Y.TMP -> Z1.TMP (exists)
                call    BDOS
                ld      (cap+5), a
                ld      de, sz
                call    count
                ld      (cap+6), a              ; "Z?.TMP"
                ld      de, sq
                call    count
                ld      (cap+7), a              ; "?.TMP"
                ld      de, sq
                ld      c, $13                  ; FDEL ?.TMP
                call    BDOS
                ld      (cap+8), a
                ld      de, sz
                ld      c, $13                  ; FDEL Z?.TMP
                call    BDOS
                ld      (cap+9), a
                ld      de, renm
                ld      c, $13                  ; FDEL a missing file
                call    BDOS
                ld      (cap+10), a
                ld      de, sall
                call    count
                ld      (cap+11), a             ; "*.TMP" left
done:
                jr      done

; mk -- FMAKE then FCLOSE the FCB at HL; A = both A's OR'd
mk:
                ld      (mk_fcb), hl
                ex      de, hl
                ld      c, $16
                call    BDOS
                ld      b, a
                push    bc
                ld      de, (mk_fcb)
                ld      c, $10
                call    BDOS
                pop     bc
                or      b
                ret

; count -- matches of the FCB at DE through SFIRST / SNEXT (at most 15); A = how many
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
                ld      a, b
                cp      15
                jr      nc, ct_end              ; a guard, not a contract
                ld      c, $12
                jr      ct_lp
ct_end:
                ld      a, b
                ret

mk_fcb:         dw      0
ct_fcb:         dw      0
fx1:            db      0, "X1      TMP"
                ds      37 - 12, 0
fx2:            db      0, "X2      TMP"
                ds      37 - 12, 0
fy:             db      0, "Y       TMP"
                ds      37 - 12, 0
renx:           db      0, "X?      TMP"            ; FREN: old at +1, new at +17
                ds      4, 0
                db      0, "Z?      TMP"
                ds      37 - 28, 0
renm:           db      0, "NOFILE  TMP"
                ds      4, 0
                db      0, "NEWNAME TMP"
                ds      37 - 28, 0
reny:           db      0, "Y       TMP"
                ds      4, 0
                db      0, "Z1      TMP"
                ds      37 - 28, 0
sz:             db      0, "Z?      TMP"
                ds      37 - 12, 0
sq:             db      0, "?       TMP"
                ds      37 - 12, 0
sall:           db      0, "????????TMP"
                ds      37 - 12, 0
dta:            ds      64, 0

; ---------------------------------------------------------------------------
; captured block $0400-$040F
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
cap:            ds      16, $EE
cap_end:
