; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; lofu32.asm -- LOF's 32-bit size -> ARGA as a PAGE-0 sub-ROM tenant
; (SUBROM_IDX_LOFU32, D-LOFU32 2026-09-10).
;
; Clean-room: own design. The observable it serves was measured black-box on
; the CF-3300 (scratchpad/putdomain_probe.py, scratchpad/loftype_probe.py):
; LOF(1) after PUT#1,300 prints 76800 and LOF(1)/7 prints 10971.428571429 --
; fourteen significant digits, a DOUBLE carrying the whole 32-bit size.
; Nothing here is derived from a disassembly or byte-copy of any reference
; ROM. Basis: basic/PROVENANCE.md.
;
; WHY A TENANT. The first cut of this fix lived in basic/expr.asm beside
; ev_ff_lof and cost 98 B of main page 1 (129 -> 31 B free, measured with
; `make basic-reloc` from a clean tree). Sub page 0 had 1184 B. The resident
; half that stays in main is the channel checks, the zero case, one
; subrom_call, arga_pack_fac and the FACTYP/DE tail -- the shape every other
; funding carve in this table has.
;
; CONTRACT. in: FAT_FILESIZE (4-byte LE, page-3 RAM, already selected to the
; channel by fch_select) is NON-ZERO -- the caller handles 0 itself, because
; the FPNUM zero form is `zero_fill 18` and that routine is main LOW REGION,
; which a page-0 tenant may not call (closure rule). out: ARGA = the unpacked
; FPNUM of the size: sign 0, DEXP = the digit count, dig[0..n-1] the decimal
; digits most-significant first, dig[n..14] zero (guard included). The caller
; packs it (arga_pack_fac). Clobbers everything (tenant convention).
;
; PAGE-0 CLEAN, transitively: RAM in, RAM out, no BIOS, no low region -- the
; digit array is cleared by its own loop for exactly that reason.
;
; HOW. Peel decimal digits, least significant first, into ARGA's digit array
; from its END: after n peels the n digits sit at dig[15-n..14] MOST-significant
; first, which is the order the FPNUM wants -- no five-byte WIDIG scratch (too
; small for ten digits) and no reversal loop, unlike basic/float-arith.asm's
; widen_uint_to. Then one LDIR slides them to dig[0..n-1] (dest below source,
; so the overlap is safe) and the tail is cleared.
lofu32_tenant:
                ld      hl,(FAT_FILESIZE)   ; DE:HL = the size, unsigned 32-bit
                ld      de,(FAT_FILESIZE+2)
                ld      bc,ARGA+FPNUM_DIG+14 ; BC = descending write pointer
lu32_peel:
                push    bc                  ; div10_32 counts in B
                call    div10_32
                pop     bc
                ld      (bc),a
                dec     bc
                ld      a,h
                or      l
                or      d
                or      e
                jr      nz,lu32_peel
                ld      hl,ARGA+FPNUM_DIG+14
                or      a
                sbc     hl,bc               ; HL = n, the digit count (1..10)
                ld      a,l
                ld      (ARGA+FPNUM_DEXP),a ; decimal exponent = integer digits,
                xor     a                   ;   as widen_uint_to sets it
                ld      (ARGA+FPNUM_DEXP+1),a
                ld      (ARGA+FPNUM_SIGN),a ; a size is never negative
                push    hl                  ; [n]
                inc     bc
                ld      h,b
                ld      l,c                 ; HL -> the most significant digit
                ld      de,ARGA+FPNUM_DIG
                pop     bc                  ; BC = n
                push    bc                  ; [n]
                ldir                        ; dig[0..n-1] := the digits; DE -> dig[n]
                pop     bc                  ; C = n
                ld      a,15
                sub     c
                ld      b,a                 ; B = 15 - n bytes: dig[n..14], guard included
                xor     a
lu32_clr:
                ld      (de),a
                inc     de
                djnz    lu32_clr
                ret

; --- div10_32: DE:HL (unsigned 32-bit) := DE:HL / 10, A := remainder. -------
; The 32-iteration form of basic/float-arith.asm's div10 (same restoring
; scheme, same register roles). Clobbers A, B.
div10_32:
                xor     a
                ld      b,32
d1032_lp:
                add     hl,hl               ; shift the dividend left, into the
                rl      e                   ;   quotient bit by bit ...
                rl      d
                rla                         ; A = running remainder<<1 | carry
                cp      10
                jr      c,d1032_skip
                sub     10
                inc     l                   ; set quotient bit
d1032_skip:
                djnz    d1032_lp
                ret
