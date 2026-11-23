; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XVA16 -- D-MSX2SPEC, docs/msx2/main/README.md "The shared VRAM address matrix", case VA-16: VA-1 (SCREEN 5, HL $1234,
; ACPAGE 0, DPPAGE 0, R#14 $06, $FFED $A1) with interrupts ON and the VDP's frame interrupt made to arrive while
; NSETRD ($016E), NSETWR ($0171), NRDVRM ($0174), NWRVRM ($0177) or BIGFIL ($016B, BC 1) runs: is the address still
; right, and does the call keep interrupts off across its port $99 writes?
; Timing, per step: interrupts off, the VBLANK flag polled from S#0 (the read clears it, so no interrupt is pending),
; then a delay loop calibrated to one frame minus 8 iterations, EI, k NOPs (k = 0..95, 5 T-states each on an MSX),
; the call. The sweep moves the next frame interrupt from after the call's return, through the call, to before it.
; The delay loop reads port $98 where the calibration reads $99: the same I/O timing (the FS-A1WSX adds wait states
; to VDP ports -- with a non-VDP port there, every interrupt of its sweep came after the step), and a $98 read never
; clears the flag. The calibration runs twice per call: on C-BIOS the first frame after CHGMOD measured short.
; H.TIMI ($FD9F) jumps to a RAM handler that records, for the first interrupt of the step: that it fired, whether the
; probe's INCALL flag was set (1 from just before the call to just after its return), and how many port $99 writes the
; port log had recorded at that moment ($FF = the log was not armed yet: the interrupt came before the call).
; Call 4 is the POSITIVE CONTROL: the probe's own four port $99 writes for the same address (R#14 := 0, then $34,
; $52) with interrupts on -- it shows the sweep can land an interrupt BETWEEN two port writes, and what that does.
; The capture (CAP = A001): +0 $A5 when finished, +1 the call count (6), +2 / +3 the calibration (loop iterations per
; frame, the last call's); from +4 a 16-byte record per call x step:
;   +0 k, +1 the call (0 NSETRD .. 3 NWRVRM, 4 control, 5 BIGFIL), +2 the handler's mark (bit 7 fired, bit 0 INCALL
;   at that moment), +3 the port $99 writes logged when it fired ($FF not armed), +4 the writes logged in all (to
;   the snapshot: the call's and an interrupt routine's), +5 R#14 after, +6 / +7 the VRAM pointer after (low, high),
;   +8 / +9 F from `ld a, i` twice right after the return (bit 2 = IFF2), +10..+13 the first four logged writes,
;   +14 / +15 this call's calibration (loop iterations per frame).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xva16.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, hooks and work-area cells, the VDP's published ports, the VDP's
; registers and pointer read by the debugger (hardware state, not a ROM byte).
;
; @cap A000
; @caplen 2500
; @vdpfull E8F0 E900
; @portlog 99 E902 E8F4
; @timeout 120

CHGMOD  equ     $005F
DPPAGE  equ     $FAF5
ACPAGE  equ     $FAF6
SV14    equ     $FFED
HTIMI   equ     $FD9F
DONE    equ     $A000
CAP     equ     $A001
SNAPFN  equ     $E8F0                   ; a `ret`: the debugger's snapshot point (@vdpfull)
ARMFN   equ     $E8F4                   ; a `ret`: the port log's arming point (@portlog)
SNAPP   equ     $E900                   ; @vdpfull's pointer word
LOGP    equ     $E902                   ; @portlog's pointer word (0 = not logging)
ptr     equ     $E904
kk      equ     $E906
cc      equ     $E907
sledp   equ     $E908
calN    equ     $E90A                   ; iterations per frame
dlyN    equ     $E90C                   ; calN - 8
incall  equ     $E90E
armed   equ     $E90F
h_mark  equ     $E910
h_lp    equ     $E911                   ; LOGP when the handler fired (2)
iff1    equ     $E913
iff2    equ     $E914
logend  equ     $E915                   ; (2)
HANDRAM equ     $E980                   ; the H.TIMI handler, copied to RAM
SNAPB   equ     $E000                   ; 114 bytes
LOGB    equ     $E080                   ; the port log, up to 96 bytes
NSTEP   equ     96

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $24FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      (ARMFN), a
                ld      hl, 0
                ld      (LOGP), hl
                call    ARMFN
                xor     a
                ld      (armed), a
                ld      (incall), a
                ; the handler into RAM, H.TIMI to it
                ld      hl, hand
                ld      de, HANDRAM
                ld      bc, hand_end - hand
                ldir
                ld      a, $C3
                ld      (HTIMI), a
                ld      hl, HANDRAM
                ld      (HTIMI+1), hl
                ld      hl, CAP+3
                ld      (ptr), hl
                xor     a
                ld      (cc), a
c_next:
                ld      a, 5
                call    CHGMOD
                di
                call    calib                   ; twice: on C-BIOS the first frame after CHGMOD measured 41 iterations
                call    calib                   ; short (1255 vs 1296 on the EU build), and its whole sweep missed
                xor     a
                ld      (kk), a
k_next:
                ; VA-1's state, by hand
                di
                xor     a
                ld      (ACPAGE), a
                ld      (DPPAGE), a
                ld      a, $A1
                ld      (SV14), a
                ld      a, $06
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ; the sled entry and the call's address
                ld      a, (kk)
                ld      e, a
                ld      d, 0
                ld      hl, sled_end
                or      a
                sbc     hl, de
                ld      (sledp), hl
                ld      a, (cc)
                add     a, a
                ld      e, a
                ld      d, 0
                ld      hl, targets
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                push    de
                pop     ix
                xor     a
                ld      (h_mark), a
                ld      hl, 0
                ld      (h_lp), hl
                ld      a, 1
                ld      (armed), a
                ; the frame: sync on the VBLANK flag, delay, EI, k NOPs, the call
                call    vsync
                ld      c, $98                  ; a VDP port (the same I/O waits as $99), whose read never sees the flag
                ld      h, 0
                ld      de, (dlyN)
                call    wloop
                ei
                ld      hl, (sledp)
                jp      (hl)
sled:
                ds      NSTEP + 8, 0            ; NOPs
sled_end:
                ld      hl, LOGB
                ld      (LOGP), hl              ; the log is armed
                ld      hl, incall
                ld      (hl), 1
                ld      hl, $1234
                ld      bc, $5AA5
                ld      de, $A55A
                ld      a, $C7
                call    callix
                ld      a, i
                push    af
                ld      a, i
                push    af
                xor     a
                ld      (incall), a
                di
                ld      (armed), a
                pop     hl
                ld      a, l
                ld      (iff2), a
                pop     hl
                ld      a, l
                ld      (iff1), a
                ld      hl, (LOGP)
                ld      (logend), hl
                ld      hl, 0
                ld      (LOGP), hl              ; disarm
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
                ; the record
                ld      de, (ptr)
                inc     de                      ; (ptr) points one before the record
                ld      a, (kk)
                ld      (de), a                 ; +0 k
                inc     de
                ld      a, (cc)
                ld      (de), a                 ; +1 the call
                inc     de
                ld      a, (h_mark)
                ld      (de), a                 ; +2 fired / INCALL
                inc     de
                ld      hl, (h_lp)
                ld      a, h
                or      l
                ld      a, $FF
                jr      z, r_na
                ld      bc, LOGB
                or      a
                sbc     hl, bc
                ld      a, l
r_na:
                ld      (de), a                 ; +3 writes at the interrupt
                inc     de
                ld      hl, (logend)
                ld      bc, LOGB
                or      a
                sbc     hl, bc
                ld      a, l
                ld      (de), a                 ; +4 writes in all
                inc     de
                ld      a, (SNAPB+14)
                ld      (de), a                 ; +5 R#14
                inc     de
                ld      a, (SNAPB+80)
                ld      (de), a                 ; +6 pointer low
                inc     de
                ld      a, (SNAPB+81)
                ld      (de), a                 ; +7 pointer high
                inc     de
                ld      a, (iff1)
                ld      (de), a                 ; +8
                inc     de
                ld      a, (iff2)
                ld      (de), a                 ; +9
                inc     de
                ld      hl, LOGB
                ld      bc, 4
                ldir                            ; +10..+13
                ld      hl, (calN)
                ex      de, hl
                ld      (hl), e                 ; +14 / +15 this call's calibration
                inc     hl
                ld      (hl), d
                ld      (ptr), hl
                ; clear the log buffer
                ld      hl, LOGB
                ld      de, LOGB+1
                ld      bc, 95
                ld      (hl), 0
                ldir
                ld      a, (kk)
                inc     a
                ld      (kk), a
                cp      NSTEP
                jp      nz, k_next
                ld      a, (cc)
                inc     a
                ld      (cc), a
                cp      6
                jp      nz, c_next
                ; done
                ld      hl, (calN)
                ld      (CAP+2), hl
                ld      a, 6
                ld      (CAP+1), a
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

callix:
                jp      (ix)

; the positive control: the same address by hand, interrupts left on
ctrl:
                ld      a, $00
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, $34
                out     ($99), a
                ld      a, $12 + $40
                out     ($99), a
                ret

targets:
                dw      $016E, $0171, $0174, $0177, ctrl, bigf1

; BIGFIL with BC 1: one byte, the pointer left at the address + 1
bigf1:
                ld      bc, 1
                jp      $016B

; interrupts off: wait for the start of a VBLANK (S#0 bit 7), clearing the flag
vsync:
                in      a, ($99)                ; clear a flag already set
vs1:
                in      a, ($99)
                and     a
                jp      p, vs1
                ret

; DE iterations, or until (in a, (c)) AND h is not zero; returns DE
wloop:
                in      a, (c)
                and     h
                ret     nz
                dec     de
                ld      a, d
                or      e
                jr      nz, wloop
                ret

; iterations from one VBLANK to the next, with the same loop body
calib:
                call    vsync
                ld      c, $99
                ld      h, $80
                ld      de, 0
                call    wloop
                ld      hl, 0
                or      a
                sbc     hl, de                  ; 65536 - DE
                ld      (calN), hl
                ld      de, 8
                or      a
                sbc     hl, de
                ld      (dlyN), hl
                ret

; H.TIMI (copied to HANDRAM): the first interrupt of a step records itself
hand:
                push    af
                push    hl
                ld      a, (armed)
                or      a
                jr      z, h_out
                xor     a
                ld      (armed), a
                ld      a, (incall)
                or      $80
                ld      (h_mark), a
                ld      hl, (LOGP)
                ld      (h_lp), hl
h_out:
                pop     hl
                pop     af
                ret
hand_end:

                ds      $8000 - $, $FF
