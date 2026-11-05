; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; var_find_typed's fast walk (D-TRAPCOST, 2026-11-05). The contract is the one in
; basic/vars.asm's header: BC = key (name0, name1), A = type -> CF set + HL = the
; entry, CF clear = not found (HL undefined). Clobbers A, D, E, H, L.
; LAST in the low region, after every low-region pin (basic/main.asm), so no
; existing label moves.
; CLEAN-ROOM: own-design (basic/PROVENANCE.md) -- a read-only copy of zerobas's own
; scalar-chain walk (sub/arrays.asm scv_find); no reference byte read.

; 🐌 D-TRAPCOST (2026-11-05): THE WALK RUNS HERE WHEN NO FN CALL IS LIVE. A
; scalar read went through the sub ROM for a ~370 T walk and paid ~1500 T of
; crossing around it -- three of them in `GOSUB 100` / `H(M)=H(M)+1:RETURN`
; (scratchpad/trapcost_prof4.out). Read-only, so the copy cannot disagree with
; the tenant's: the same region [PRGEND+2, ARYTAB), the same key (name0, name1,
; type) and stride (3 + elsize_from_type: a string's is 3). While an FN call is
; live (FN_FEND past FN_PAREA's low byte, fn_shadow_find's own fast test) a
; formal may shadow the name, so that case still takes the tenant.
var_find_typed:
                ld      d,a                 ; D = the type
                ld      a,(FN_FEND)
                cp      low FN_PAREA
                ld      a,d
                jp      nz,vft_engine       ; an FN call is live: the tenant (vars.asm)
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; HL = the scalar region's base
vft_lp:
                ld      a,(ARYTAB+1)
                cp      h
                jr      nz,vft_go
                ld      a,(ARYTAB)
                cp      l
                ret     z                   ; HL == ARYTAB: not found, CF clear
vft_go:
                ld      a,(hl)              ; name0
                inc     hl
                cp      b
                ld      a,(hl)              ; name1 (`ld` keeps the flags)
                inc     hl
                ld      e,(hl)              ; type
                jr      nz,vft_skip
                cp      c
                jr      nz,vft_skip
                ld      a,e
                cp      d
                jr      nz,vft_skip
                dec     hl
                dec     hl                  ; HL = the entry
                scf
                ret
vft_skip:
                ld      a,e
                cp      1
                jr      nz,vft_num
                ld      a,3                 ; a string's [len][ptr]
vft_num:
                inc     a                   ; HL is at +2: elsize + 1 more
                add     a,l
                ld      l,a
                jr      nc,vft_lp
                inc     h
                jr      vft_lp
