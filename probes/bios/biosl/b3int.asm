; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; B3INT -- D-BIOSLADDER rung B3 (TODO.md): the interrupt as a ROM program uses it.
; A 16 KB "AB" cartridge; INIT runs it (page 1 stays this cartridge throughout, so
; the hooks may jump straight into it, as cartridge games do).
;   1. EI; 50 x HALT: JIFFY's advance (CAP+0, word);
;   2. H.TIMI := jp timi (counts its calls, keeps the A it is entered with -- the
;      VDP status, by the published contract -- and its bit 7 OR'd over all calls)
;      and H.KEYI := jp keyi (counts every interrupt); 50 x HALT: JIFFY's advance
;      (CAP+2), the H.TIMI count (CAP+4), the H.KEYI count (CAP+6), the first A
;      (CAP+8) and the OR (CAP+9);
;   3. DI; a busy loop of ~1.4 s (~70 frames); then what JIFFY and the two counts did
;      during it, read BEFORE the EI (CAP+10, +12, +14 -- words);
;   4. both hooks back to RET; 10 x HALT: the counts after it (CAP+16, +18) and
;      JIFFY's advance (CAP+20);
;   5. a frame-synced loop: 20 x (HALT, then the VDP status read through the BIOS
;      cell STATFL): STATFL's bit 7 OR'd (CAP+22).
; CLEAN-ROOM: 100% own code; only published BIOS cells and hooks.
;
; @timeout 40

JIFFY   equ     $FC9E
STATFL  equ     $F3E7
H_KEYI  equ     $FD9A
H_TIMI  equ     $FD9F

DONE    equ     $E000
CAP     equ     $E001
TCNT    equ     $E200           ; word: H.TIMI calls
KCNT    equ     $E202           ; word: H.KEYI calls
TFIRST  equ     $E204           ; the first A seen by H.TIMI (0 until then)
TSEEN   equ     $E205           ; 1 once H.TIMI ran
TOR     equ     $E206           ; A's bits OR'd over the H.TIMI calls
J0      equ     $E208           ; JIFFY at a step's start

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
                ld      hl, TCNT
                ld      de, TCNT+1
                ld      bc, 15
                ld      (hl), 0
                ldir
                ; --- 1 ------------------------------------------------------------------
                ei
                call    mark
                ld      b, 50
                call    halts
                ld      de, CAP+0
                call    since
                ; --- 2 ------------------------------------------------------------------
                di
                ld      a, $C3
                ld      (H_TIMI), a
                ld      (H_KEYI), a
                ld      hl, timi
                ld      (H_TIMI+1), hl
                ld      hl, keyi
                ld      (H_KEYI+1), hl
                ei
                call    mark
                ld      b, 50
                call    halts
                ld      de, CAP+2
                call    since
                ld      hl, (TCNT)
                ld      (CAP+4), hl
                ld      hl, (KCNT)
                ld      (CAP+6), hl
                ld      a, (TFIRST)
                ld      (CAP+8), a
                ld      a, (TOR)
                ld      (CAP+9), a
                ; --- 3 ------------------------------------------------------------------
                ld      hl, (TCNT)
                ld      (CAP+12), hl        ; the counts before ...
                ld      hl, (KCNT)
                ld      (CAP+14), hl
                di
                ld      hl, (JIFFY)
                ld      (J0), hl
                ld      bc, 0               ; 3 x 65536 x 26 T (dec bc / ld a,b / or c /
                ld      d, 3                ; jr nz) = ~5.1 M T, ~1.4 s
busy:
                dec     bc
                ld      a, b
                or      c
                jr      nz, busy
                dec     d
                jr      nz, busy
                ld      de, CAP+10
                call    since               ; JIFFY's advance under DI
                ld      hl, (TCNT)          ; ... and after, as a difference
                ld      de, (CAP+12)
                or      a
                sbc     hl, de
                ld      (CAP+12), hl
                ld      hl, (KCNT)
                ld      de, (CAP+14)
                or      a
                sbc     hl, de
                ld      (CAP+14), hl
                ei
                ; --- 4 ------------------------------------------------------------------
                di
                ld      a, $C9
                ld      (H_TIMI), a
                ld      (H_KEYI), a
                ld      hl, (TCNT)
                ld      (CAP+16), hl
                ld      hl, (KCNT)
                ld      (CAP+18), hl
                ei
                call    mark
                ld      b, 10
                call    halts
                ld      de, CAP+20
                call    since
                ld      hl, (TCNT)          ; the counts must not have moved
                ld      de, (CAP+16)
                or      a
                sbc     hl, de
                ld      (CAP+16), hl
                ld      hl, (KCNT)
                ld      de, (CAP+18)
                or      a
                sbc     hl, de
                ld      (CAP+18), hl
                ; --- 5 ------------------------------------------------------------------
                ld      b, 20
                ld      c, 0
sync:
                halt
                ld      a, (STATFL)
                and     $80
                or      c
                ld      c, a
                djnz    sync
                ld      a, c
                ld      (CAP+22), a
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; mark -- J0 := JIFFY
mark:
                ld      hl, (JIFFY)
                ld      (J0), hl
                ret

; since -- (DE) := JIFFY - J0 (word)
since:
                ld      hl, (JIFFY)
                push    de
                ld      de, (J0)
                or      a
                sbc     hl, de
                pop     de
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ret

; halts -- B x HALT (interrupts on)
halts:
                halt
                djnz    halts
                ret

; timi -- the H.TIMI handler: count, keep the first A, OR A's bits
timi:
                push    af
                push    hl
                ld      hl, (TCNT)
                inc     hl
                ld      (TCNT), hl
                ld      hl, TSEEN
                bit     0, (hl)
                jr      nz, timi_seen
                ld      (hl), 1
                ld      (TFIRST), a
timi_seen:
                ld      hl, TOR
                or      (hl)
                ld      (hl), a
                pop     hl
                pop     af
                ret

; keyi -- the H.KEYI handler: count
keyi:
                push    hl
                ld      hl, (KCNT)
                inc     hl
                ld      (KCNT), hl
                pop     hl
                ret
