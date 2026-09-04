; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — printusing.asm  (PRINT USING format-scanner tenant)
; ===========================================================================
; The PRINT USING format literal-scanners (pu_to_field + pu_emit_tail), evicted
; from the repack main ROM's basic/printusing.asm into sub-ROM PAGE 0
; (docs/spec-evict-printusing.md), to free page-1 window space for the
; error-handling S2a slice.
;
; WHY SUB-SIDE. Both routines are PURE leaves over the PU_* RAM sysvars + pchar:
; they scan the copied format string (PU_FMT) and emit its literal characters,
; identifying the next #/!/&/\..\ field (pu_to_field) or stopping at it
; (pu_emit_tail). No eval, no pu_deref_body, no div10 — so they are a valid
; page-0 tenant run under DI, and the fragile value-render/deref paths
; (pu_do_number / pu_do_string / pu_fmt_int) stay RESIDENT and unchanged.
;
; The shared body lives in basic/pu-render.inc (the shared
; inline copy). Here it binds `pchar` to sub/detok.asm's sub-local DETOKBUF
; append (both are co-resident page-0 tenants — SUB_PARTS — so pchar is defined
; once, there, and shared). The two entry wrappers reset the DETOKBUF cursor,
; run the scanner, and 0-terminate the buffer; the resident stubs
; (basic/printusing.asm) drain DETOKBUF through the real
; print_string, honouring PRDEST — so the ONE scanner feeds both PRINT USING ->
; screen and PRINT# USING -> file (the 003ff70 file-form fix stays main-side).
;
; RAM: DETOKBUF ($BE00, 512 B) + DB_CUR ($F108) are shared sysvars.inc equates,
; byte-identical main/sub. PU_FMTMAX is 32, so a scanner's literal run is <= 32 B
; -- the 512 B buffer never overflows and needs no bound check.
;
; CLEAN-ROOM: original code (the scanners are copied verbatim from our own
; basic/printusing.asm via basic/pu-render.inc). No disassembly.
; ===========================================================================

BACKSLASH       equ     $5C                 ; '\' field char (pu-render.inc)

; --- pu_tofield_tenant: the SUBROM_IDX_PU_TOFIELD entry --------------------
; Reset the DETOKBUF cursor, run pu_to_field (emits leading literals via the
; sub-local pchar, sets PU_TYPE/PU_W/PU_POS, CF set if no field), 0-terminate the
; buffer, and return the no-field flag in A (0 = a field was found; 1 = none) —
; A is the CALSLT-safe result channel; the resident stub turns it back into CF.
pu_tofield_tenant:
                ld      de,DETOKBUF
                ld      (DB_CUR),de         ; reset the DETOKBUF write cursor
                call    pu_to_field         ; emit leading literals -> DETOKBUF; CF=no-field
                ld      hl,(DB_CUR)
                ld      (hl),0              ; 0-terminate (ld: no flag effect, CF survives)
                ld      a,0
                ret     nc                  ; field found -> A=0
                inc     a                   ; no field -> A=1
                ret

; --- pu_tail_tenant: the SUBROM_IDX_PU_TAIL entry -------------------------
; Reset the cursor, run pu_emit_tail (emits trailing literals up to the next
; field / format end), 0-terminate. No result flag.
pu_tail_tenant:
                ld      de,DETOKBUF
                ld      (DB_CUR),de
                call    pu_emit_tail
                ld      hl,(DB_CUR)
                ld      (hl),0
                ret

; --- pu_sign_tenant: PRINT USING's `+` / `-` sign placement (D-PUSIGN) ------
; docs/spec-basic-pufloat.md. Reached only when PU_FLAGS bit 3 says the field
; carried a sign specifier.
;
;   in   PU_NUM = "[-]digits",0 as pu_fmt_int left it
;        PU_FLAGS bit4 = TRAILING (else leading), bit5 = the char is `+`
;   out  PU_NUM rewritten; A = its new length. Clobbers AF, BC, DE, HL.
;
; Three transformations, and the measured contract is what picks them:
;     `+##` ·  5   ->  ` +5`   a `+` is PREPENDED
;     `+##` · -5   ->  ` -5`   the `-` pu_fmt_int already wrote is the sign
;     `##+` ·  5   ->  ` 5+`   a `+` is APPENDED
;     `##+` · -5   ->  ` 5-`   the `-` MOVES to the end -- and it is `-`, not `+`
;     `##-` ·  5   ->  ` 5 `   a SPACE is appended, not nothing
;     `##-` · -5   ->  ` 5-`
;
; ⚠️ SITED SUB-SIDE BECAUSE OF SPACE, NOT STRUCTURE. It is pure RAM work and could
; equally live in basic/printusing.asm -- but that is main page 1, which had 50 B
; free, and this is ~60. Page-0 closure holds trivially: no main-ROM call at all.
;
; PU_NUM is 8 bytes and the widest case fits: "-32768" is 6 + terminator, and the
; trailing form only MOVES that byte, while the leading form prepends to at most
; "32767" -> 6 + terminator.
pu_sign_tenant:
                ld      a,(PU_FLAGS)
                bit     4,a
                jr      nz,pst_trail
                ; --- LEADING: only a POSITIVE value changes ------------------
                ld      a,(PU_NUM)
                cp      '-'
                jr      z,pst_len           ; negative: the `-` already leads
                call    pst_end             ; HL -> terminator, B = length
                ld      d,h
                ld      e,l
                inc     de                  ; DE -> one past it
                ld      c,b
                inc     bc                  ; move length+1 bytes (with the 0)
                ld      b,0
                lddr                        ; shift right, backwards
                ld      a,'+'
                ld      (PU_NUM),a
                jr      pst_len
pst_trail:
                ld      a,(PU_NUM)
                cp      '-'
                jr      z,pst_tneg
                ; positive: append `+` (bit5) or a SPACE
                call    pst_end             ; HL -> terminator
                ld      a,(PU_FLAGS)
                bit     5,a
                ld      a,' '
                jr      z,pst_tput
                ld      a,'+'
pst_tput:
                ld      (hl),a
                inc     hl
                ld      (hl),0
                jr      pst_len
pst_tneg:
                ; negative: drop the leading `-`, then append one. Always `-`,
                ; even under `##+` -- measured.
                ld      hl,PU_NUM+1
                ld      de,PU_NUM
                call    pst_end_hl          ; BC = bytes remaining incl. terminator
                ldir
                call    pst_end
                ld      (hl),'-'
                inc     hl
                ld      (hl),0
pst_len:
                call    pst_end
                ld      a,b
                ret

; pst_end -- HL -> PU_NUM's 0 terminator, B = the length before it.
pst_end:
                ld      hl,PU_NUM
                ld      b,0
pse_lp:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                inc     b
                jr      pse_lp
; pst_end_hl -- BC = bytes from HL through the terminator INCLUSIVE.
pst_end_hl:
                push    hl
                ld      bc,1
psh_lp:
                ld      a,(hl)
                or      a
                jr      z,psh_done
                inc     hl
                inc     bc
                jr      psh_lp
psh_done:
                pop     hl
                ret

; --- pu_emit_tenant: PRINT USING's numeric PAD + EMIT (D-PUEMIT) ------------
; docs/spec-basic-pufloat.md. Builds the finished field into DETOKBUF; the
; resident stub drains it through the real print_string, honouring PRDEST -- so
; PRINT# USING's file form is untouched.
;
; ⚠️ WHY IT BUFFERS RATHER THAN PRINTING. A tenant cannot call the real `pchar`
; at all: `pchar` reaches CHPUT in the BIOS (PAGE 0) and lives in main PAGE 1, and
; whichever island a tenant runs on, one of those two is switched out. That is the
; same constraint pu_to_field already lives under, and the reason this file binds
; `pchar` to the sub-local DETOKBUF append instead.
;
;   in   PU_NUM holds the rendered digits; PU_W the field width; PU_FLAGS bit2
;        the asterisk fill
;   out  DETOKBUF = pad + digits (or `%` + digits on overflow), 0-terminated
pu_emit_tenant:
                ld      de,DETOKBUF
                ld      (DB_CUR),de         ; reset the append cursor
                ld      hl,PU_NUM           ; length, measured here rather than
                ld      b,0                 ; passed -- a marshalled byte would be
pet_len:                                    ; one more thing to keep in step
                ld      a,(hl)
                or      a
                jr      z,pet_have
                inc     hl
                inc     b
                jr      pet_len
pet_have:
                ld      a,(PU_W)
                sub     b                   ; pad = width - length
                jr      c,pet_over          ; longer than the field -> `%`
                jr      z,pet_body
                ld      b,a
                ld      a,(PU_FLAGS)
                bit     2,a                 ; D-PUSTAR: `**` pads with asterisks
                ld      a,' '
                jr      z,pet_pad
                ld      a,'*'
pet_pad:
                push    af
                call    pchar
                pop     af
                djnz    pet_pad
                jr      pet_body
pet_over:
                ld      a,'%'               ; field overflow marker (MSX)
                call    pchar
pet_body:
                ld      hl,PU_NUM
pet_cp:
                ld      a,(hl)
                or      a
                jr      z,pet_done
                push    hl
                call    pchar
                pop     hl
                inc     hl
                jr      pet_cp
pet_done:
                ld      hl,(DB_CUR)
                ld      (hl),0              ; 0-terminate for the drain
                ret

; The shared scanner body (pu_to_field/ptf_* + pu_emit_tail). Binds pchar to
; sub/detok.asm's sub-local DETOKBUF append (defined once, co-resident).
                include "basic/pu-render.inc"
