; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; circleparse.asm -- the CIRCLE grammar-walk + angle/aspect float math, evicted
; ===========================================================================
; from resident page-1 as an eval-bounce co-routine (docs/spec-circle-coroutine-
; space.md). PAGE-1 sub-ROM tenant (SUBROM_IDX_CIRCLEPARSE): main page 1 is
; switched out, so this tenant reads the program token stream from RAM, inlines
; skip_spaces, and REQUESTS each value from the resident `ex_circle` servicer
; (which owns eval/parse_coord/gfx_eval_int16 -- main page-1) via GFX_DREQ. The
; angle/aspect FLOAT math lives HERE (a page-1 tenant reaches the low-region
; float pack -- the fp_sqrt pattern), so it moved off page-1 with the grammar.
;
; PROTOCOL (mirrors DRAW's gfx_draw_op, docs §3):
;   GFX_DPTR    shared token cursor (RAM); resident seeds + advances it per eval.
;   GFX_DRESUME 0 = fresh parse, 1 = resuming after a resolved request.
;   GFX_CPHASE  which arg we last requested (P_*), so resume lands correctly.
;   GFX_DREQ    tenant->resident: 0 = done; 1 = parse centre; 2 = eval int16;
;               3 = eval float -> ARGA canonical.
;   GFX_DVAL    resident->tenant: the int16 value (DREQ 2). ARGA holds DREQ 3.
;   GFX_RES     tenant->resident: 0 = ok, else the ERR code to raise (2 / 5).
; Round trips: one subrom_call per PRESENT arg. The resident does the GFX_OP=4
; geometry draw once GFX_DREQ comes back 0.
;
; CLEAN-ROOM: the grammar + float glue are OUR code, moved verbatim from
; basic/graphics.asm (G4 slice); only the eval calls became DREQ bounces. No
; disassembly; the CIRCLE language is the public MSX-BASIC reference.

P_CENTER        equ     0
P_R             equ     1
P_C             equ     2
P_START         equ     3
P_END           equ     4
P_ASPECT        equ     5

; --- circleparse_tenant: the co-routine entry (sub_p1_table index 19) --------
circleparse_tenant:
                ld      a,(GFX_DRESUME)
                or      a
                jr      nz,cpt_resume
                ; fresh parse: clear the error slot, request the centre (x,y)
                xor     a
                ld      (GFX_RES),a
                ld      a,P_CENTER
                ld      (GFX_CPHASE),a
                ld      a,1                 ; DREQ 1 = parse_coord
                ld      (GFX_DREQ),a
                ret

cpt_resume:
                ld      a,(GFX_CPHASE)
                cp      P_CENTER
                jr      z,cpt_after_center
                cp      P_R
                jp      z,cpt_after_r
                cp      P_C
                jp      z,cpt_after_c
                cp      P_START
                jp      z,cpt_after_start
                cp      P_END
                jp      z,cpt_after_end
                jp      cpt_after_aspect    ; P_ASPECT

; --- after the centre: the mandatory ",r" then request r -------------------
cpt_after_center:
                call    cpt_skipsp
                cp      ','                 ; the ",r" comma is mandatory
                jp      nz,cpt_err2
                call    cpt_advance         ; consume ','
                ld      a,P_R
                ld      (GFX_CPHASE),a
                ld      a,2                 ; DREQ 2 = eval int16
                ld      (GFX_DREQ),a
                ret

; --- after r: r>=0 check, defaults, then the optional ",c" -----------------
cpt_after_r:
                ld      hl,(GFX_DVAL)       ; r
                ld      a,h
                or      a
                jp      m,cpt_err5          ; r<0 -> ERR 5 (G4-rneg deviation)
                ld      (GFX_R),hl
                call    cpt_defaults
                call    cpt_skipsp
                cp      ','
                jp      nz,cpt_finish       ; no optional fields -> draw
                call    cpt_advance         ; consume ','
cpt_at_c:
                call    cpt_skipsp
                cp      ','
                jp      z,cpt_start_intro   ; c omitted; this comma also intros start
                or      a
                jp      z,cpt_finish
                cp      COLON
                jp      z,cpt_finish
                ld      a,P_C
                ld      (GFX_CPHASE),a
                ld      a,2                 ; DREQ 2
                ld      (GFX_DREQ),a
                ret

; --- after c: 0..15 range check, then the optional ",start" ----------------
cpt_after_c:
                ld      hl,(GFX_DVAL)       ; c
                ld      a,h
                or      a
                jp      nz,cpt_err5         ; c<0 or >255 -> ERR 5
                ld      a,l
                cp      16
                jp      nc,cpt_err5         ; >15 -> ERR 5
                ld      (GFX_C),a
                call    cpt_skipsp
                cp      ','
                jp      nz,cpt_finish
                ; fall into start_intro (the comma that ends c intros start)
cpt_start_intro:
                call    cpt_advance         ; consume the comma introducing start
                call    cpt_angle_defaults
cpt_at_start:
                call    cpt_skipsp
                cp      ','
                jp      z,cpt_start_empty   ; start empty; comma intros end
                or      a
                jp      z,cpt_finish
                cp      COLON
                jp      z,cpt_finish
                ld      a,P_START
                ld      (GFX_CPHASE),a
                ld      a,3                 ; DREQ 3 = eval float -> ARGA
                ld      (GFX_DREQ),a
                ret

; --- after start angle: boundary prep, then the optional ",end" ------------
cpt_after_start:
                ld      bc,GFX_SNEG
                ld      de,GFX_SBRAD
                call    cpt_angle_from_arga
                call    cpt_skipsp
                cp      ','
                jp      nz,cpt_finish
                call    cpt_advance
cpt_at_end:
                call    cpt_skipsp
                cp      ','
                jp      z,cpt_end_empty     ; end empty; comma intros aspect
                or      a
                jp      z,cpt_finish
                cp      COLON
                jp      z,cpt_finish
                ld      a,P_END
                ld      (GFX_CPHASE),a
                ld      a,3
                ld      (GFX_DREQ),a
                ret
cpt_start_empty:
                call    cpt_advance         ; consume the comma, move into end
                jr      cpt_at_end

; --- after end angle: boundary prep, then the optional ",aspect" -----------
cpt_after_end:
                ld      bc,GFX_ENEG
                ld      de,GFX_EBRAD
                call    cpt_angle_from_arga
                call    cpt_skipsp
                cp      ','
                jp      nz,cpt_finish
                call    cpt_advance
cpt_at_aspect:
                call    cpt_skipsp
                cp      ','
                jp      z,cpt_err2          ; too many args -> Syntax error
                or      a
                jp      z,cpt_finish
                cp      COLON
                jp      z,cpt_finish
                ld      a,P_ASPECT
                ld      (GFX_CPHASE),a
                ld      a,3
                ld      (GFX_DREQ),a
                ret
cpt_end_empty:
                call    cpt_advance         ; consume the comma, move into aspect
                jr      cpt_at_aspect

; --- after aspect: the aspect float math, then finish ----------------------
cpt_after_aspect:
                ld      a,(ARGA+FPNUM_SIGN) ; ARGA = canonical(aspect) (resident widened)
                or      a
                jp      nz,cpt_err5         ; aspect < 0 -> ERR 5
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      a,h
                or      a
                jp      m,cpt_asp_le1       ; dexp<0 -> aspect<1
                ld      a,l
                or      a
                jp      z,cpt_asp_le1       ; dexp==0 -> aspect<1
                ; aspect>=1 (dexp>=1): y-major; minor_ratio = 1/aspect
                ld      a,1
                ld      (GFX_ASPMAJ),a
                ld      hl,ARGA
                ld      de,ARGB
                ld      bc,18
                ldir                        ; ARGB := aspect
                ld      hl,ARGA
                xor     a
                ld      de,1
                call    widen_uint_to       ; ARGA := 1.0
                call    fp_div              ; ARGA/FAC := 1/aspect
                call    cpt_asp_scale256
                jr      cpt_asp_done
cpt_asp_le1:
                xor     a
                ld      (GFX_ASPMAJ),a
                call    cpt_asp_scale256    ; ARGA still = aspect
cpt_asp_done:
                call    cpt_skipsp
                cp      ','
                jp      z,cpt_err2          ; too many args -> Syntax error
                jp      cpt_finish

; ===========================================================================
; helpers
; ===========================================================================

; cpt_skipsp: load HL from GFX_DPTR, skip spaces, store back, RETURN A = (HL).
; The cursor persists (skipping insignificant spaces is idempotent). Clobbers A,HL.
cpt_skipsp:
                ld      hl,(GFX_DPTR)
css_lp:
                ld      a,(hl)
                cp      ' '
                jr      nz,css_done
                inc     hl
                jr      css_lp
css_done:
                ld      (GFX_DPTR),hl
                ret

; cpt_advance: consume one token byte (HL=GFX_DPTR, inc, store). Clobbers HL.
cpt_advance:
                ld      hl,(GFX_DPTR)
                inc     hl
                ld      (GFX_DPTR),hl
                ret

; cpt_finish / cpt_err5 / cpt_err2: return control to the resident servicer.
; DREQ 0 = done; GFX_RES carries the ERR code (0 = ok). Clobbers A.
cpt_err5:
                ld      a,5
                ld      (GFX_RES),a
                jr      cpt_finish
cpt_err2:
                ld      a,2
                ld      (GFX_RES),a
cpt_finish:
                xor     a
                ld      (GFX_DREQ),a
                ret

; cpt_defaults: the pre-optional-field defaults (verbatim from ex_circle). ---
cpt_defaults:
                ld      a,(FORCLR)
                and     $0F
                ld      (GFX_C),a
                xor     a
                ld      (GFX_ASPMAJ),a
                ld      bc,256
                ld      (GFX_ASPS),bc
                xor     a
                ld      (GFX_ARCF),a
                ld      (GFX_SNEG),a
                ld      (GFX_ENEG),a
                ret

; cpt_angle_defaults: eager brad=0/signc=+1/signs=0 for BOTH boundaries -------
; (verbatim from circ_start_intro -- angle 0, the same vector an omitted end
; (2*pi) yields by periodicity, spec §5.2.1 REVISED).
cpt_angle_defaults:
                xor     a
                ld      (GFX_SBRAD),a
                ld      (GFX_SBRAD+1),a
                ld      (GFX_EBRAD),a
                ld      (GFX_EBRAD+1),a
                ld      (GFX_SSGNS),a
                ld      (GFX_ESGNS),a
                ld      a,1
                ld      (GFX_SSGNC),a
                ld      (GFX_ESGNC),a
                ret

; cpt_angle_from_arga: the tail of the old circ_parse_given_angle, from ARGA ---
; canonical (the resident already did eval+widen_rhs_operand). IN: BC=neg-flag
; cell (GFX_SNEG/ENEG), DE=dest record base (GFX_SBRAD/EBRAD), ARGA=canonical
; angle. Sets the neg flag, forces |angle|, fills the boundary record, ARCF:=1.
cpt_angle_from_arga:
                ld      (GFX_CS_AX),bc      ; stash neg-flag cell addr
                ld      (GFX_CS_AY),de      ; stash dest record base
                ld      a,(ARGA+FPNUM_SIGN)
                ld      hl,(GFX_CS_AX)
                ld      (hl),a              ; negative -> a spoke is drawn later
                xor     a
                ld      (ARGA+FPNUM_SIGN),a ; ARGA := |angle|
                call    cpt_boundary_prep   ; reads GFX_CS_AY for the dest base
                ld      a,1
                ld      (GFX_ARCF),a        ; actually GIVEN -> arc mode
                ret

; cpt_asp_scale256: S := round(minor_ratio*256) -> GFX_ASPS (verbatim). -------
cpt_asp_scale256:
                ld      hl,ARGB
                xor     a
                ld      de,256
                call    widen_uint_to       ; ARGB := 256.0
                call    fp_mul              ; ARGA/FAC := minor_ratio*256
                call    cpt_round
                ld      (GFX_ASPS),de
                ret

; cpt_boundary_prep: |angle| -> (brad, sign_c, sign_s) record at (GFX_CS_AY). --
; Verbatim from gfx_circ_boundary_prep (spec §5.2.1 REVISED, trig-free). Three
; bounded fp_cmp compares pin the quadrant signs; one fp_mul + round gives brad.
cpt_boundary_prep:
                ld      hl,GFX_HALF_PI
                ld      de,ARGB
                ld      bc,18
                ldir
                call    fp_cmp              ; A = 1(<half_pi) / 2(==) / 4(>)
                ld      (GFX_CS_T1),a       ; stash (the 2nd ldir clobbers B)
                ld      hl,GFX_THREE_HALF_PI
                ld      de,ARGB
                ld      bc,18
                ldir
                call    fp_cmp              ; A = cmp vs THREE_HALF_PI
                ld      c,a
                ld      a,(GFX_CS_T1)
                ld      b,a                 ; B = cmp vs HALF_PI (after both ldir)
                cp      2
                jr      z,cpt_signc_zero
                ld      a,c
                cp      2
                jr      z,cpt_signc_zero
                ld      a,b
                cp      1
                jr      z,cpt_signc_pos
                ld      a,c
                cp      4
                jr      z,cpt_signc_pos
                ld      a,$FF               ; HALF_PI < theta < THREE_HALF_PI
                jr      cpt_signc_store
cpt_signc_pos:
                ld      a,1
                jr      cpt_signc_store
cpt_signc_zero:
                xor     a
cpt_signc_store:
                ld      hl,(GFX_CS_AY)
                inc     hl
                inc     hl                  ; dest+2 = signc
                ld      (hl),a
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero        ; Z=1 iff theta is exactly 0
                jr      z,cpt_signs_zero
                ld      hl,GFX_PI_CONST
                ld      de,ARGB
                ld      bc,18
                ldir
                call    fp_cmp              ; A = theta vs PI
                cp      2
                jr      z,cpt_signs_zero
                cp      1
                jr      z,cpt_signs_pos
                ld      a,$FF               ; theta > PI
                jr      cpt_signs_store
cpt_signs_pos:
                ld      a,1
                jr      cpt_signs_store
cpt_signs_zero:
                xor     a
cpt_signs_store:
                ld      hl,(GFX_CS_AY)
                inc     hl
                inc     hl
                inc     hl                  ; dest+3 = signs
                ld      (hl),a
                ld      hl,GFX_K_128_PI
                ld      de,ARGB
                ld      bc,18
                ldir
                call    fp_mul              ; ARGA/FAC := theta * (128/pi)
                call    cpt_round           ; DE := round(...)
                ld      hl,(GFX_CS_AY)
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

; cpt_round: DE := round-half-away-from-zero(ARGA) as int16 (verbatim from ----
; gfx_round_arga_de: abs, +0.5, trunc, reapply sign).
cpt_round:
                ld      a,(ARGA+FPNUM_SIGN)
                push    af
                xor     a
                ld      (ARGA+FPNUM_SIGN),a ; ARGA := |value|
                ld      hl,ARGB
                call    cpt_build_half      ; ARGB := 0.5
                call    fp_add              ; ARGA/FAC := |value| + 0.5
                call    flt_to_int16        ; DE := trunc(|value|+0.5)
                pop     af
                or      a
                ret     z                   ; non-negative -> DE correct
                xor     a                   ; negate DE
                sub     e
                ld      e,a
                ld      a,0
                sbc     a,d
                ld      d,a
                ret

; cpt_build_half: write the 18-byte 0.5 FPNUM at HL (verbatim from gfx_build_half).
cpt_build_half:
                xor     a
                ld      (hl),a              ; sign
                inc     hl
                ld      (hl),a              ; dexp lo
                inc     hl
                ld      (hl),a              ; dexp hi
                inc     hl
                ld      (hl),5              ; dig[0] = 5
                inc     hl
                ld      b,14
cpt_gbh_lp:
                ld      (hl),0
                inc     hl
                djnz    cpt_gbh_lp
                ret

; --- FPNUM constants (18-byte records; moved verbatim from the resident) -----
GFX_HALF_PI:
                db      0, 1,0, 1,5,7,0,7,9,6,3,2,6,7,9,4,8,9
GFX_PI_CONST:
                db      0, 1,0, 3,1,4,1,5,9,2,6,5,3,5,8,9,7,9
GFX_THREE_HALF_PI:
                db      0, 1,0, 4,7,1,2,3,8,8,9,8,0,3,8,4,6,8
GFX_K_128_PI:
                db      0, 2,0, 4,0,7,4,3,6,6,5,4,3,1,5,2,5,2
