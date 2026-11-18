; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XINITIO6 -- docs/bios/INITIO.md round 6 (2026-11-18), after the sixth review: QUEUES ($F3F3) and the table it points to,
; read BEFORE any interrupt can run. Every case: interrupts off, the VDP status read just before the call, `di` the first
; instruction after it, JIFFY ($FC9E) read before and after (the witness), and the reads made before any `ei`.
;   case 1: the first call after boot -- QUEUES as the boot left it, before and after; QUETAB ($F959, 28 B) before / after.
;   case 2: QUEUES := $9EB7, its 28-byte table seeded $40.. and $F959.. seeded $90..; both read before and after.
;   case 3: QUEUES := $A123, its table seeded $C0..; $F959.. seeded $10..; both read before and after.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xinitio6.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; per case a 125-byte record from CAP+1:
;   +0,1 JIFFY before (low, high)  +2,3 JIFFY after  +4,5 QUEUES before  +6,7 QUEUES after
;   +8..35 the table at QUEUES (as it was before the call) BEFORE   +36..63 the same 28 bytes AFTER
;   +64..91 $F959.. BEFORE   +92..119 $F959.. AFTER   +120 MUSICF after   +121..123 0   +124 sentinel $C3
;
; CLEAN-ROOM: 100% own code; a published BIOS entry, the VDP's published status port, work-area RAM.
;
; @cap C000
; @caplen 0180
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
cq      equ     $EF04                   ; the case: QUEUES value (0 = leave), table seed, $F959 seed
cqs     equ     $EF06
cfs     equ     $EF07
qtab    equ     $EF08                   ; the table address used for the reads
jb      equ     $EF0A

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $017F
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
                ld      de, cq
                ld      bc, 4
                ldir
                ld      (tptr), hl
                ; QUEUES: the case's value, or as found (0)
                ld      hl, (cq)
                ld      a, h
                or      l
                jr      z, q_keep
                ld      ($F3F3), hl
                ; its table: 28 bytes of garbage from the case's seed
                ld      a, (cqs)
                ld      b, 28
q_seed:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    q_seed
                ; $F959..: 28 bytes of garbage
                ld      hl, $F959
                ld      a, (cfs)
                ld      b, 28
f_seed:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    f_seed
q_keep:
                ld      hl, ($F3F3)
                ld      (qtab), hl
                ; the BEFORE reads (JIFFY comes last, just before the call)
                ld      hl, (ptr)
                ld      de, 4
                add     hl, de
                ld      (ptr), hl               ; +4: QUEUES before
                ld      a, (qtab)
                call    emit
                ld      a, (qtab+1)
                call    emit
                ld      hl, (ptr)
                inc     hl
                inc     hl
                ld      (ptr), hl               ; +8: skip QUEUES after for now
                ld      hl, (qtab)
                call    emit28                  ; +8..35
                ld      hl, (ptr)
                ld      de, 28
                add     hl, de
                ld      (ptr), hl               ; skip the AFTER copy for now
                ld      hl, $F959
                call    emit28                  ; +64..91
                ; the call, under the clean window
                xor     a
                ld      ($FB3F), a              ; MUSICF 0: nothing for an interrupt to play
                in      a, ($99)
                ld      hl, ($FC9E)
                ld      (jb), hl
                call    $003B
                di
                ; the AFTER reads: rewind ptr to the record's start
                ld      hl, (ptr)
                ld      de, -92
                add     hl, de
                ld      (ptr), hl               ; +0
                ld      a, (jb)
                call    emit
                ld      a, (jb+1)
                call    emit
                ld      a, ($FC9E)
                call    emit
                ld      a, ($FC9F)
                call    emit
                ld      hl, (ptr)
                inc     hl
                inc     hl
                ld      (ptr), hl               ; +6
                ld      a, ($F3F3)
                call    emit
                ld      a, ($F3F4)
                call    emit
                ld      hl, (ptr)
                ld      de, 28
                add     hl, de
                ld      (ptr), hl               ; +36
                ld      hl, (qtab)
                call    emit28                  ; +36..63
                ld      hl, (ptr)
                ld      de, 28
                add     hl, de
                ld      (ptr), hl               ; +92
                ld      hl, $F959
                call    emit28                  ; +92..119
                ld      a, ($FB3F)
                call    emit                    ; +120
                xor     a
                call    emit
                call    emit
                call    emit
                ld      a, $C3
                call    emit                    ; +124
                jp      next

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

; ---- cases: QUEUES (0 = as found), its table's seed, $F959's seed; $FF ends (the QUEUES low byte is never $FF) ----
cases:
                dw      $0000
                db      $00, $00                ; 1  the first call after boot
                dw      $9EB7
                db      $40, $90                ; 2  QUEUES $9EB7, both tables garbage
                dw      $A123
                db      $C0, $10                ; 3  QUEUES $A123, other garbage
                db      $FF
