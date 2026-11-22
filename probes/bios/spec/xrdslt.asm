; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XRDSLT -- docs/bios/RDSLT.md / WRSLT.md round 5 (2026-11-18): RDSLT ($000C) and WRSLT ($0014) on the machine's RAM
; slot and on the probe's own cartridge slot. The probe runs from RAM ($EA00, page 3). It first works out, from the
; slot register ($A8), EXPTBL ($FCC1..) and the secondary register ($FFFF, read complemented, only when the slot is
; expanded), the slot ID of page 3's RAM (the RAM slot) and of page 1 at boot (the cartridge), in the published form
; E000SSPP. Each case then calls the entry with A = that slot ID, HL = the address, E = the value (WRSLT), entry A's
; other bits as the slot ID, entry F from the case, interrupts on or off per case. A WITNESS then reads the same
; address through the probe's own switching (out ($A8), and $FFFF when expanded; interrupts off), independent of the
; BIOS: after WRSLT it shows the byte landed, after RDSLT the byte RDSLT should have read.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xrdslt.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; CAP+1..16 the header: $A8 at boot, EXPTBL (4), SLTTBL (4), the secondary
; register complemented (or 0 if slot 3 is not expanded), the RAM slot ID, the cartridge slot ID, 4 x 0; then per case
; 12 bytes: A after, F after, IFF after (1 = interrupts on, from LD A,I), $A8 after, the secondary register after
; (complemented; 0 if not expanded), moved (a bit per register that changed: bit 0 B, 1 C, 2 D, 3 E, 4 HL, 5 IX, 6 IY),
; the witness byte, B, C, D, E after, the PRE-witness (the byte the same hand read found BEFORE the call); then $C3.
; Round 4 adds, after the third review: (1) cases that first set slot 3's SECONDARY selection for page 0 or 1 to 3-1
; by hand (only where slot 3 is expanded; pages 0 / 1 are not slot 3 then, so the probe keeps running), so a call
; naming 3-0 must switch the secondary and put 3-1 back -- the record's secondary byte shows it; (2) an RDSLT with the
; cartridge's ID at a page-2 address, where page 2 is RAM (slot 3): ORing the slot into the page's field would read
; slot 3 again, replacing it reads the cartridge's slot. The rules read this table (`cases:`) from this file.
; Round 5, after the fourth reviews: (3) a second write / read pair under each secondary preset, with new values, so
; RDSLT's reads of 3-0 cannot be a fixed 3-1 byte; (4) cases that first set page 1's PRIMARY slot to 0 by hand ($A8
; $F4 -> $F0, $F8 -> $F0 ... on every machine), a second slot-register value everywhere, put back after each case;
; (5) a CONTROL record (op 2): interrupts on and no call, so the IFF readout is seen to report 1. The variables live at
; $E900.. (below $EF00).
; IFF is read twice (LD A,I can read 0 when an interrupt is accepted during it) and the two ORed. The witness treats ID
; bit 7 as "slot 3, expanded": correct here (the only expanded slot ever named is zerobas's RAM, 3-0), not general. Entry markers: B $13, C $57, D $9B, IX $4321, IY $8765; E is the
; value; HL the address. The slot ID passed is the RAM / cartridge ID OR the case's extra bits.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the published slot register and work-area cells. RDSLT reads only
; RAM and the probe's own cartridge bytes.
;
; @cap C000
; @caplen 0200
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E900
tp      equ     $E902
ramid   equ     $E904
cartid  equ     $E905
sid     equ     $E906                   ; the case: op (0 WRSLT, 1 RDSLT), which (0 RAM, 1 cart), addr (2), value,
cop     equ     $E907                   ; entry F, ei
cwh     equ     $E908
cad     equ     $E909
cva     equ     $E90B
cef     equ     $E90C
cei     equ     $E90D
ra      equ     $E90E                   ; results
rf      equ     $E90F
riff    equ     $E910
rkept   equ     $E911
rbc     equ     $E918
rde     equ     $E91A
cxb     equ     $E91C
rhl     equ     $E912
rpre    equ     $E920
cps     equ     $E91D                   ; the case's secondary preset: 0 none, 1 page 0 := 3-1, 2 page 1 := 3-1
c8p     equ     $E91E                   ; the case's slot-register preset: 0 none, 1 page 1 := slot 0
secb    equ     $E921                   ; slot 3's secondary selection at boot (when expanded)
wpri    equ     $E914
wsec    equ     $E915
wsav    equ     $E916
a8boot  equ     $E917
RAMB    equ     $EA00

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $01FF
                ld      (hl), 0
                ldir
                ld      hl, blk
                ld      de, RAMB
                ld      bc, blk_end - blk
                ldir
                jp      RAMB

blk:
                di
                ld      hl, CAP+1
                ld      (ptr), hl
                ; the header
                in      a, ($A8)
                ld      (a8boot), a
                call    RAMB + emit - blk
                ld      hl, $FCC1
                ld      c, 8
h_lp:
                ld      a, (hl)
                call    RAMB + emit - blk
                inc     hl
                dec     c
                jr      nz, h_lp
                call    RAMB + rdsec - blk
                ld      (secb), a
                call    RAMB + emit - blk
                ; the RAM slot: page 3's primary
                ld      a, (a8boot)
                rlca
                rlca
                and     3
                call    RAMB + slotid - blk     ; A = primary, page 3 -> the ID
                ld      (ramid), a
                call    RAMB + emit - blk
                ; the cartridge: page 1's primary at boot
                ld      a, (a8boot)
                rrca
                rrca
                and     3
                ld      c, 1
                call    RAMB + slotid_pg - blk
                ld      (cartid), a
                call    RAMB + emit - blk
                xor     a
                call    RAMB + emit - blk
                call    RAMB + emit - blk
                call    RAMB + emit - blk
                call    RAMB + emit - blk
                ld      hl, RAMB + cases - blk
                ld      (tp), hl
next:
                di
                ld      hl, (tp)
                ld      a, (hl)
                cp      $FF
                jp      z, RAMB + finish - blk
                ld      de, cop
                ld      bc, 7
                ldir
                ld      de, cxb
                ld      bc, 3
                ldir
                ld      (tp), hl
                ld      a, (cwh)
                or      a
                ld      a, (ramid)
                jr      z, c_id
                ld      a, (cartid)
c_id:
                ld      hl, cxb
                or      (hl)
                ld      (sid), a
                call    RAMB + preset - blk     ; the case's secondary preset, if any
                ld      a, (c8p)                ; the case's slot-register preset: page 1 := slot 0
                or      a
                jr      z, c_no8p
                in      a, ($A8)
                and     $F3
                out     ($A8), a
c_no8p:
                call    RAMB + witness - blk    ; the byte before the call
                ld      (rpre), a
                ld      hl, $0014               ; the entry: WRSLT, RDSLT or (the control) none, into the `jp` at c_jp
                ld      a, (cop)
                or      a
                jr      z, c_tgt
                ld      hl, $000C
                dec     a
                jr      z, c_tgt
                ld      hl, RAMB + c_nop - blk
c_tgt:
                ld      (RAMB + c_jp + 1 - blk), hl
                ld      a, (sid)
                ; the call: A = slot ID, F = (cef), HL = addr, E = value, D / BC / IX / IY markers
                ld      b, a
                ld      a, (cef)
                ld      c, a
                push    bc
                ld      bc, $1357
                ld      ix, $4321
                ld      iy, $8765
                ld      d, $9B
                ld      a, (cva)
                ld      e, a
                ld      hl, (cad)
                ld      a, (cei)
                or      a
                jr      z, c_noei
                ei
c_noei:
                pop     af
                call    RAMB + c_jp - blk
                jr      c_ret
c_jp:
                jp      0                       ; WRSLT / RDSLT, written per case
c_nop:
                ret
c_ret:
                ld      (rhl), hl
                ld      (rbc), bc
                ld      (rde), de
                push    af
                ld      a, i                    ; P/V := IFF2
                push    af
                ld      a, i                    ; again: an interrupt accepted during the first reads 0
                di
                push    af
                pop     hl                      ; L bit 2 = IFF, second read
                pop     de                      ; E bit 2 = IFF, first read
                ld      a, l
                or      e
                rrca
                rrca
                and     1
                ld      (riff), a
                pop     hl                      ; H = A, L = F
                ld      a, h
                ld      (ra), a
                ld      a, l
                ld      (rf), a
                ; moved: a bit per register
                ld      c, 0
                ld      a, (rbc+1)
                cp      $13
                jr      z, m1
                set     0, c
m1:
                ld      a, (rbc)
                cp      $57
                jr      z, m2
                set     1, c
m2:
                ld      a, (rde+1)
                cp      $9B
                jr      z, m3
                set     2, c
m3:
                ld      a, (rde)
                ld      hl, cva
                cp      (hl)
                jr      z, m4
                set     3, c
m4:
                ld      hl, (rhl)
                ld      de, (cad)
                or      a
                sbc     hl, de
                jr      z, m5
                set     4, c
m5:
                push    ix
                pop     hl
                ld      de, $4321
                or      a
                sbc     hl, de
                jr      z, m6
                set     5, c
m6:
                push    iy
                pop     hl
                ld      de, $8765
                or      a
                sbc     hl, de
                jr      z, m7
                set     6, c
m7:
                ld      a, c
                ld      (rkept), a
                ; the record
                ld      a, (ra)
                call    RAMB + emit - blk
                ld      a, (rf)
                call    RAMB + emit - blk
                ld      a, (riff)
                call    RAMB + emit - blk
                in      a, ($A8)
                call    RAMB + emit - blk
                call    RAMB + rdsec - blk
                call    RAMB + emit - blk
                ld      a, (rkept)
                call    RAMB + emit - blk
                call    RAMB + witness - blk
                call    RAMB + emit - blk
                ld      a, (rbc+1)
                call    RAMB + emit - blk
                ld      a, (rbc)
                call    RAMB + emit - blk
                ld      a, (rde+1)
                call    RAMB + emit - blk
                ld      a, (rde)
                call    RAMB + emit - blk
                ld      a, (rpre)
                call    RAMB + emit - blk
                ld      a, (a8boot)             ; the slot register back to its boot value
                out     ($A8), a
                ld      a, ($FCC4)              ; slot 3's secondary back to its boot selection
                or      a
                jp      p, RAMB + next - blk
                ld      a, (secb)
                ld      ($FFFF), a
                jp      RAMB + next - blk

; preset -- slot 3 expanded and (cps) = 1 / 2: set its secondary selection for page 0 / 1 to 1 (3-1), others kept
preset:
                ld      a, ($FCC4)
                or      a
                ret     p
                ld      a, (cps)
                or      a
                ret     z
                ld      b, $FC                  ; page 0: keep bits 2-7, set 01
                ld      c, $01
                cp      1
                jr      z, ps_go
                ld      b, $F3                  ; page 1
                ld      c, $04
ps_go:
                ld      a, ($FFFF)
                cpl
                and     b
                or      c
                ld      ($FFFF), a
                ret

; rdsec -- A := the secondary register of slot 3 complemented when EXPTBL+3 says expanded (page 3 is slot 3), else 0
rdsec:
                ld      a, ($FCC4)
                or      a
                ret     p
                ld      a, ($FFFF)
                cpl
                ret

; slotid -- A = a primary slot, page 3: the ID (E000SSPP), the secondary from SLTTBL when expanded (as slotid_pg)
slotid:
                ld      c, 3
; slotid_pg -- A = a primary slot, C = the page: the ID. The secondary comes from SLTTBL (the BIOS's copy), for every
; page (the header records $FFFF too).
slotid_pg:
                push    hl
                push    de
                ld      e, a
                ld      d, 0
                ld      hl, $FCC1
                add     hl, de
                bit     7, (hl)
                jr      z, s_plain
                ld      hl, $FCC5
                add     hl, de
                ld      a, (hl)                 ; SLTTBL: the secondary selections, 2 bits per page
                ld      b, c
s_shift:
                dec     b
                jp      m, RAMB + s_got - blk
                rrca
                rrca
                jr      s_shift
s_got:
                and     3
                rlca
                rlca
                or      e
                or      $80
                jr      s_done
s_plain:
                ld      a, e
s_done:
                pop     de
                pop     hl
                ret

; witness -- read (cad) in the case's slot by own switching (interrupts are off); A := the byte
witness:
                ld      a, (cad+1)
                rlca
                rlca
                and     3
                ld      c, a                    ; C = the page
                ld      a, (sid)
                ld      e, a                    ; E = the slot ID
                and     3
                ld      (wpri), a
                ld      a, e
                rrca
                rrca
                and     3
                ld      (wsec), a
                in      a, ($A8)
                ld      d, a                    ; D = $A8 to restore
                ld      a, ($FFFF)
                cpl
                ld      (wsav), a               ; slot 3's secondary selection (used only when expanded)
                ld      h, 3                    ; H = the page's 2-bit mask, shifted
                ld      b, c
w_sh:
                dec     b
                jp      m, RAMB + w_shd - blk
                sla     h
                sla     h
                ld      a, (wpri)
                rlca
                rlca
                ld      (wpri), a
                ld      a, (wsec)
                rlca
                rlca
                ld      (wsec), a
                jr      w_sh
w_shd:
                bit     7, e
                jr      z, w_prim
                ld      a, h                    ; expanded (slot 3 here): its secondary for the page
                cpl
                ld      l, a
                ld      a, (wsav)
                and     l
                ld      l, a
                ld      a, (wsec)
                or      l
                ld      ($FFFF), a
w_prim:
                ld      a, h
                cpl
                and     d
                ld      l, a
                ld      a, (wpri)
                or      l
                out     ($A8), a
                ld      hl, (cad)
                ld      b, (hl)
                ld      a, d
                out     ($A8), a
                bit     7, e
                jr      z, w_done
                ld      a, (wsav)
                ld      ($FFFF), a
w_done:
                ld      a, b
                ret

finish:
                ld      a, $C3
                call    RAMB + emit - blk
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

; ---- cases: op (0 WRSLT, 1 RDSLT, 2 control), which (0 RAM, 1 cart), addr, value, entry F, ei, extra slot-ID bits,
; secondary preset, slot-register preset; $FF ends ----
cases:
                db      0, 0
                dw      $8ABC
                db      $5A, $00, 0, $00, 0, 0  ;  0 WRSLT RAM page 2
                db      1, 0
                dw      $8ABC
                db      $00, $FF, 0, $00, 0, 0  ;  1 RDSLT RAM page 2
                db      0, 0
                dw      $4567
                db      $A5, $FF, 1, $00, 0, 0  ;  2 WRSLT RAM page 1, ei
                db      1, 0
                dw      $4567
                db      $00, $00, 1, $00, 0, 0  ;  3 RDSLT RAM page 1, ei
                db      0, 0
                dw      $0123
                db      $3C, $00, 0, $00, 0, 0  ;  4 WRSLT RAM page 0
                db      1, 0
                dw      $0123
                db      $00, $FF, 1, $00, 0, 0  ;  5 RDSLT RAM page 0, ei
                db      0, 0
                dw      $3FFF
                db      $C3, $FF, 1, $00, 0, 0  ;  6 WRSLT RAM page 0's last byte, ei
                db      1, 0
                dw      $3FFF
                db      $00, $00, 0, $00, 0, 0  ;  7 RDSLT
                db      1, 1
                dw      $4000
                db      $00, $00, 0, $00, 0, 0  ;  8 RDSLT the cartridge: 'A'
                db      1, 1
                dw      $4001
                db      $00, $FF, 1, $00, 0, 0  ;  9 RDSLT the cartridge: 'B', ei
                db      0, 0
                dw      $8ABC
                db      $00, $00, 0, $00, 0, 0  ; 10 WRSLT RAM page 2: value 0
                db      1, 0
                dw      $8ABC
                db      $00, $00, 1, $00, 0, 0  ; 11 RDSLT
                db      0, 0
                dw      $0000
                db      $81, $00, 0, $00, 0, 0  ; 12 WRSLT RAM $0000
                db      1, 0
                dw      $0000
                db      $00, $FF, 0, $70, 0, 0  ; 13 RDSLT RAM $0000, slot ID | $70 (bits 4-6)
                db      0, 0
                dw      $4000
                db      $18, $FF, 0, $70, 0, 0  ; 14 WRSLT RAM $4000, slot ID | $70
                db      1, 0
                dw      $4000
                db      $00, $00, 0, $00, 0, 0  ; 15 RDSLT RAM $4000
                db      0, 0
                dw      $BFFF
                db      $E7, $00, 1, $00, 0, 0  ; 16 WRSLT RAM $BFFF, ei
                db      1, 0
                dw      $BFFF
                db      $00, $FF, 0, $00, 0, 0  ; 17 RDSLT
                db      0, 0
                dw      $EE40
                db      $66, $00, 0, $00, 0, 0  ; 18 WRSLT RAM page 3 ($EE40)
                db      1, 0
                dw      $EE40
                db      $00, $FF, 1, $00, 0, 0  ; 19 RDSLT RAM page 3, ei
                db      1, 1
                dw      $4002
                db      $00, $00, 0, $00, 0, 0  ; 20 RDSLT the cartridge: init's low byte
                db      0, 0
                dw      $0456
                db      $2D, $00, 0, $00, 1, 0  ; 21 WRSLT RAM $0456, page 0's secondary preset to 3-1
                db      1, 0
                dw      $0456
                db      $00, $FF, 1, $00, 1, 0  ; 22 RDSLT, the same preset, ei
                db      0, 0
                dw      $5678
                db      $D2, $FF, 0, $00, 2, 0  ; 23 WRSLT RAM $5678, page 1's secondary preset to 3-1
                db      1, 0
                dw      $5678
                db      $00, $00, 0, $00, 2, 0  ; 24 RDSLT, the same preset
                db      0, 0
                dw      $8002
                db      $C6, $00, 0, $00, 0, 0  ; 25 WRSLT RAM $8002 := $C6: page 2's RAM byte there differs from the cartridge's
                db      1, 1
                dw      $8002
                db      $00, $00, 0, $00, 0, 0  ; 26 RDSLT the cartridge's ID at $8002 (page 2 is RAM, $C6 there)
                db      0, 0
                dw      $0456
                db      $B4, $00, 0, $00, 1, 0  ; 27 WRSLT RAM $0456 := $B4, page 0's secondary preset to 3-1 (second value)
                db      1, 0
                dw      $0456
                db      $00, $00, 0, $00, 1, 0  ; 28 RDSLT, the same preset
                db      0, 0
                dw      $5678
                db      $4B, $00, 1, $00, 2, 0  ; 29 WRSLT RAM $5678 := $4B, page 1's secondary preset to 3-1 (second value), ei
                db      1, 0
                dw      $5678
                db      $00, $FF, 0, $00, 2, 0  ; 30 RDSLT, the same preset
                db      0, 0
                dw      $0789
                db      $3E, $00, 0, $00, 0, 1  ; 31 WRSLT RAM $0789, page 1's primary preset to slot 0
                db      1, 0
                dw      $0789
                db      $00, $FF, 1, $00, 0, 1  ; 32 RDSLT, the same preset, ei
                db      1, 1
                dw      $4001
                db      $00, $00, 0, $00, 0, 1  ; 33 RDSLT the cartridge: 'B', page 1 preset to slot 0 (the call must switch it)
                db      0, 0
                dw      $9ABC
                db      $81, $FF, 0, $00, 0, 1  ; 34 WRSLT RAM page 2, page 1 preset to slot 0
                db      1, 0
                dw      $9ABC
                db      $00, $00, 0, $00, 0, 1  ; 35 RDSLT, the same preset
                db      2, 0
                dw      $8ABC
                db      $00, $00, 1, $00, 0, 0  ; 36 CONTROL: interrupts on, no call (the IFF readout must read 1)
                db      $FF
blk_end:
