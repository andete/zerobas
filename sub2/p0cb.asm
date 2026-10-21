; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; p0cb.asm -- zerobas-sub2 PAGE 0: the call back into main (D-P0CB,
; docs/spec-sub2-p0cb.md). Included in page 0 of sub2/sub2.asm.
;
; While a page-0 tenant of this ROM runs, slot-0 page 0 -- the BIOS, main's low
; region, the $0038 entry -- is switched OUT; only main page 1 stays mapped. A
; statement moved here still needs main's CHRGTR, its evaluator, its raise and its
; print path, all of which reach page 0. p0cb maps main's page 0 back for one call.
;
; 🏗️ NO NEW RAM (Joost, 2026-10-21: "Yes, but no new RAM"): it goes through the
; BIOS's own RAM inter-slot primitive CLPRIM ($F38C), the one C-BIOS's CALSLT
; jumps to (C-BIOS src/slot.asm m_clprim). Its contract, from that source:
;   in   A = the new primary-slot value (out to $A8); IX = the address to call;
;        the stack holds [the old $A8 value, pushed as AF] above [a return
;        address]; AF' = what the callee receives as AF
;   it   out ($A8),A / ex af,af' / call (IX) / ex af,af' / pop af /
;        out ($A8),A / ex af,af' / ret
; so the CALLER's own return address is the one CLPRIM's `ret` uses: p0cb only
; parks AF in AF', pushes the live $A8 and jumps. Main is slot 0, unexpanded on
; both repack machines (their XML), so "page 0 := main" is clearing bits 0-1.
;
;   in   IX = a main address (any page: the low region and the BIOS are mapped
;        for the duration); A, F, BC, DE, HL = the callee's inputs
;   out  the callee's A, F, BC, DE, HL; IX = whatever the callee left; AF'
;        clobbered. A callee that RAISES never returns (raise_error resets SP and
;        runs main's error path with main's page 0 already mapped).
p0cb:
                ex      af,af'              ; the caller's AF -> AF' (the callee gets it)
                in      a,($A8)
                push    af                  ; the live primary slots: CLPRIM restores them
                and     $FC                 ; page 0 := slot 0, main
                jp      CLPRIM              ; ...whose `ret` returns to OUR caller

; s2_chrgtr / s2_outdo -- this ROM's RST 10h / RST 18h ($0010 / $0018 jump
; here): main's CHRGTR and OUTDO through p0cb, so code moved here keeps its
; `rst $10` / `rst $18` byte for byte. IX is SAVED: a caller may hold the
; evaluator's cursor in it, and p0cb consumes IX.
s2_chrgtr:
                push    ix
                ld      ix,p0_chrgtr
                jr      s2_rst
s2_outdo:
                push    ix
                ld      ix,p0_outdo
s2_rst:
                call    p0cb
                pop     ix
                ret

; --- p0cb_selftest: page-0 index 2 (SUB2_IDX_P0TEST), the mechanism proven ---
; Called by the probe's injected stub (probes/basic/basic_probe_sub2_p0cb.py)
; under CALSLT 3-3, never by BASIC. in: HL = a RAM work area W, with W+16 =
; "  XY",0 and W+15 = any byte. Writes, then returns with interrupts OFF:
;   W+0  A after `rst $10` from W+15 ('X')       W+1  L after it (low byte of W+18)
;   W+2..W+9  A, F, B, C, D, E, H, L after a p0cb to main's `bp_ret` (a bare `ret`)
;             entered with A=$5A, CF=1, BC=$1234, DE=$5678, HL=$9ABC
;   W+10 A, W+11 L after a p0cb to main's page-1 skip_spaces from W+16
;   W+12 the low byte of IX after the `rst $10`, entered with IX=$5AA5 ($A5)
;   W+13 1 if JIFFY moved under EI inside this page-0 tenant (D-SUB2EI's twin), else 0
p0cb_selftest:
                push    hl
                pop     iy                  ; IY = W (p0cb leaves IY alone)
                ; (1) RST 10h -> main's CHRGTR, from W+15: past the blanks to 'X'
                push    iy
                pop     hl
                ld      de,15
                add     hl,de
                ld      ix,$5AA5            ; must survive the RST (s2_chrgtr saves it)
                rst     $10
                ld      (iy+0),a
                ld      (iy+1),l
                push    ix
                pop     de
                ld      (iy+12),e           ; $A5 iff IX came back
                ; (2) every register both ways, through a bare `ret` in main page 1
                ld      bc,$1234
                ld      de,$5678
                ld      hl,$9ABC
                ld      a,$5A
                scf
                ld      ix,p0_bp_ret
                call    p0cb
                ld      (iy+4),b            ; stores touch no register, so A and F
                ld      (iy+5),c            ; are still the callee's when pushed
                ld      (iy+6),d
                ld      (iy+7),e
                ld      (iy+8),h
                ld      (iy+9),l
                push    af
                pop     hl
                ld      (iy+2),h            ; A
                ld      (iy+3),l            ; F
                ; (3) a page-1 routine with a contract: skip_spaces from W+16
                push    iy
                pop     hl
                ld      de,16
                add     hl,de
                ld      ix,p0_skip_spaces
                call    p0cb
                ld      (iy+10),a
                ld      (iy+11),l
                ; (4) EI inside this page-0 tenant: the interrupt lands on THIS ROM's
                ; $0038 -> SUB_INT_RAM, which must come back here (D-SUB2EI)
                ld      (iy+13),0
                ld      hl,(JIFFY)
                ld      bc,0                ; a bounded spin: ~65536 x the loop
                ei
p0st_spin:
                ld      de,(JIFFY)
                ld      a,e
                cp      l
                jr      nz,p0st_moved
                ld      a,d
                cp      h
                jr      nz,p0st_moved
                dec     bc
                ld      a,b
                or      c
                jr      nz,p0st_spin
                jr      p0st_done
p0st_moved:
                ld      (iy+13),1
p0st_done:
                di
                ret
