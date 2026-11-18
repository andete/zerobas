; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XINITIO7 -- docs/bios/INITIO.md round 7 (2026-11-18), after the ninth review: every recorded call in a window WITNESSED
; CLEAN ON BOTH MACHINES. Per case the probe seeds everything, reads the VDP status (no interrupt pending), reads JIFFY
; ($FC9E), enables interrupts if the case says so, calls INITIO, `di` at once, and reads JIFFY again; if it moved, it
; re-seeds and retries, up to 8 tries. Only then are the results read. Seeds, each per case:
;   - QUEUES ($F3F3) and its 28-byte table ($F959 or elsewhere), and $F959.. when the table is elsewhere;
;   - MUSICF; the PSG's 16 registers all one value ($00 or $FF);
;   - the voice control blocks $FB41-$FBAF: all $FF, or byte k := $CC - k (the complement of rounds 2-3's $33 + k).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xinitio7.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; per case a 237-byte record from CAP+1:
;   +0,1 JIFFY before (low, high) of the recorded try  +2,3 JIFFY after  +4 the tries it took (1 = first)
;   +5,6 QUEUES before  +7,8 QUEUES after  +9..36 QUEUES' table before  +37..64 after
;   +65..92 $F959.. before  +93..120 after  +121 MUSICF after  +122..124 R7 / R11 / R15 after
;   +125..235 the voice control blocks after   +236 sentinel $C3
;
; CLEAN-ROOM: 100% own code; a published BIOS entry, the PSG's / VDP's published ports, work-area RAM.
;
; @cap C000
; @caplen 0400
; @timeout 90

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
rec     equ     $EF04                   ; the record's start
cei     equ     $EF06                   ; the case's 8 bytes: ei, QUEUES (2), table seed, $F959 seed, MUSICF, PSG value,
cq      equ     $EF07                   ; VCB mode (0 none, 1 all $FF, 2 $CC - k)
cqs     equ     $EF09
cfs     equ     $EF0A
cmus    equ     $EF0B
cpsg    equ     $EF0C
cvcb    equ     $EF0D
tries   equ     $EF0E
jb      equ     $EF10
ja      equ     $EF12
qtab    equ     $EF14
SAVE    equ     $D000                   ; the BEFORE reads, kept here while the tries run (60 B)

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $03FF
                ld      (hl), 0
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      hl, cases
                ld      (tptr), hl
next:
                di
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, finish
                ld      de, cei
                ld      bc, 8
                ldir
                ld      (tptr), hl
                ld      hl, (ptr)
                ld      (rec), hl
                xor     a
                ld      (tries), a
try:
                di
                ld      a, (tries)
                inc     a
                ld      (tries), a
                call    seed
                ; the BEFORE reads into SAVE: QUEUES (2), its table (28), $F959.. (28)
                ld      hl, ($F3F3)
                ld      (qtab), hl
                ld      (SAVE), hl
                ld      de, SAVE+2
                ld      bc, 28
                ldir
                ld      hl, $F959
                ld      de, SAVE+30
                ld      bc, 28
                ldir
                ; the call: VDP status, JIFFY, ei per case, INITIO, di
                in      a, ($99)
                ld      hl, ($FC9E)
                ld      (jb), hl
                ld      a, (cei)
                or      a
                jr      z, c_di
                ei
c_di:
                call    $003B
                di
                ld      hl, ($FC9E)
                ld      (ja), hl
                ld      de, (jb)
                or      a
                sbc     hl, de
                jr      z, clean
                ld      a, (tries)
                cp      8
                jr      c, try                  ; an interrupt ran: seed and call again
clean:
                ; the record
                ld      hl, (rec)
                ld      (ptr), hl
                ld      a, (jb)
                call    emit
                ld      a, (jb+1)
                call    emit
                ld      a, (ja)
                call    emit
                ld      a, (ja+1)
                call    emit
                ld      a, (tries)
                call    emit
                ld      a, (SAVE)
                call    emit
                ld      a, (SAVE+1)
                call    emit
                ld      a, ($F3F3)
                call    emit
                ld      a, ($F3F4)
                call    emit
                ld      hl, SAVE+2
                call    emit28                  ; the table before
                ld      hl, (qtab)
                call    emit28                  ; after
                ld      hl, SAVE+30
                call    emit28                  ; $F959.. before
                ld      hl, $F959
                call    emit28                  ; after
                ld      a, ($FB3F)
                call    emit
                ld      a, 7
                call    rdpsg
                ld      a, 11
                call    rdpsg
                ld      a, 15
                call    rdpsg
                ld      hl, $FB41
                ld      b, 111
r_vcb:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    r_vcb
                ld      a, $C3
                call    emit
                jp      next

; seed -- the case's state: the PSG, QUEUES and its table, $F959.., MUSICF, the voice control blocks
seed:
                ld      b, 0
s_psg:
                ld      a, b
                out     ($A0), a
                ld      a, (cpsg)
                out     ($A1), a
                inc     b
                ld      a, b
                cp      16
                jr      c, s_psg
                ld      hl, $F959
                ld      a, (cfs)
                call    fill28
                ld      hl, (cq)
                ld      ($F3F3), hl
                ld      a, (cqs)
                call    fill28                  ; QUEUES' table (= $F959.. when QUEUES is $F959)
                ld      a, (cmus)
                ld      ($FB3F), a
                ld      a, (cvcb)
                or      a
                ret     z
                ld      hl, $FB41
                ld      b, 111
                ld      c, $CC
s_v:
                ld      a, (cvcb)
                cp      1
                ld      a, $FF
                jr      z, s_vput
                ld      a, c
s_vput:
                ld      (hl), a
                inc     hl
                dec     c
                djnz    s_v
                ret

fill28:
                ld      b, 28
f28:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    f28
                ret

rdpsg:
                out     ($A0), a
                in      a, ($A2)
                jp      emit

emit28:
                ld      b, 28
e28:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    e28
                ret

finish:
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret

; ---- cases: ei, QUEUES, table seed, $F959 seed, MUSICF, PSG value, VCB mode; $FF ends (ei is 0 / 1) ----
cases:
                db      1
                dw      $F959
                db      $60, $60, $FF, $FF, 2   ; 1  EI, QUEUES $F959, MUSICF $FF, PSG all $FF, VCB $CC - k
                db      1
                dw      $9EB7
                db      $40, $90, $5A, $00, 1   ; 2  EI, QUEUES $9EB7, MUSICF $5A, PSG all $00, VCB all $FF
                db      0
                dw      $F959
                db      $20, $20, $FF, $FF, 1   ; 3  DI, QUEUES $F959, MUSICF $FF, PSG all $FF, VCB all $FF
                db      0
                dw      $A123
                db      $C0, $10, $00, $FF, 2   ; 4  DI, QUEUES $A123, MUSICF 0, PSG all $FF, VCB $CC - k
                db      $FF
