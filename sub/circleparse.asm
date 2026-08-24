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
;   GFX_RES     tenant->resident: 0 = ok, else the ERR code to raise (2/5/24).
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
; 🔴 THIS IS THE RADIUS DOMAIN, AND IT IS 0..32767 -- NOT 0..255 (D-CIRCDOM).
; Five `$8000` verdicts in docs/fixpoint8000-msx1-sweep.md §4.2 and four
; headers in sub/graphics.asm used to cite a "blessed r<=255 domain" that is
; enforced NOWHERE. The actual enforcement is exactly two tests, in two files:
;
;   UPPER  basic/graphics.asm cp_req_int -> gfx_eval_int16   ERR 6 for |r|>=32768
;   LOWER  the `jp m,cpt_err5` three lines below              ERR 5 for r<0
;
; so GFX_R is any value in 0..32767 and `CIRCLE(128,96),1000` is accepted (K on
; BOTH references, measured -- circdom §4 phase S). Cite THIS pair, not "r<=255",
; anywhere a graphics routine needs the radius domain.
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
; 🔴 D-CIRCMISS: THE FOUR `cpt_at_*` LABELS ARE REACHED ONLY AFTER A COMMA
; HAS BEEN CONSUMED, so a statement that ENDS at one of them is a DANGLING
; comma, not an omitted argument -- `Missing operand` (ERR 24) on both
; references, at all four slots and on both the end-of-line and the `:` arm
; (8 rows, docs/spec-basic-circmiss.md §3). They used to jp cpt_finish, so
; `CIRCLE(50,50),20,` DREW THE CIRCLE and reported nothing at all.
; ⚠️ AN OMITTED SLOT BETWEEN COMMAS IS A DIFFERENT THING AND STILL LEGAL:
; the `cp ','` arm one line below each of these is what carries it, and
; `CIRCLE(50,50),20,,0.1,6.2` must keep drawing (rows o.colour / o.start /
; o.end / o.none, unanimous 0 on all three machines before AND after).
; ⚠️ AND THE RULE STOPS AT THE END OF THE LIST: a comma after a COMPLETE
; argument list is Syntax error (ERR 2), not 24 (rows x.extra / x.extra2), the
; same way D-LINERR measured LINE's box slot as ERR 2 one field past a slot
; that is 24. But WHERE the ERR 2 is raised splits the two boundary sites
; (D-CIRCTC):
;   cpt_at_aspect (x.extra `...,6.2,,`): the aspect slot is itself EMPTY, so the
;     reference raises BEFORE drawing (`2 4`). Its cpt_err2 STAYS -- raise-first.
;   cpt_asp_done  (x.extra2 `...,6.2,1,`): the list is COMPLETE (aspect present),
;     so the reference DRAWS then raises (`2 5`). Its bespoke cpt_err2 is DELETED
;     and the leftover comma is delegated to the resident's cp_done boundary --
;     draw-then-raise, matching SWAP/PAINT/SPRITE (docs/spec-basic-circle-
;     restructure.md). The empty-slot-vs-complete-list split is the SAME rule
;     the four cpt_at_* labels carry above (omitted slot draws; dangling comma
;     is 24) -- extended to the terminator.
cpt_at_c:
                call    cpt_skipsp
                cp      ','
                jp      z,cpt_start_intro   ; c omitted; this comma also intros start
                or      a
                jp      z,cpt_err24         ; a comma was CONSUMED: end of
                cp      COLON               ; statement here is a DANGLING
                jp      z,cpt_err24         ; comma -> Missing operand
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
                jp      z,cpt_err24         ; a comma was CONSUMED: end of
                cp      COLON               ; statement here is a DANGLING
                jp      z,cpt_err24         ; comma -> Missing operand
                ld      a,P_START
                ld      (GFX_CPHASE),a
                ld      a,3                 ; DREQ 3 = eval float -> ARGA
                ld      (GFX_DREQ),a
                ret

; --- after start angle: boundary prep, then the optional ",end" ------------
cpt_after_start:
                ld      bc,GFX_SNEG
                ld      de,GFX_SOCT
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
                jp      z,cpt_err24         ; a comma was CONSUMED: end of
                cp      COLON               ; statement here is a DANGLING
                jp      z,cpt_err24         ; comma -> Missing operand
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
                ld      de,GFX_EOCT
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
                jp      z,cpt_err24         ; a comma was CONSUMED: end of
                cp      COLON               ; statement here is a DANGLING
                jp      z,cpt_err24         ; comma -> Missing operand
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
                ; 🔴 D-CIRCTC: a trailing comma after a COMPLETE argument list
                ; (aspect PRESENT) is NOT a tenant error. The reference DRAWS the
                ; circle and THEN raises Syntax error (x.extra2 `2 5`); zerobas
                ; raised ERR 2 here BEFORE the draw (`2 4`). This is the seam the
                ; three resident-side verbs already delegate (SWAP/PAINT/SPRITE):
                ; report SUCCESS (GFX_RES stays 0), leave GFX_DPTR ON the leftover
                ; comma, and let the resident's cp_done do its GFX_OP=4 draw and
                ; the `jp exec_stmt` it ALREADY ends in -- es_noentry / stmt_error
                ; raises ERR 2 (trappable, after the draw). The tenant needn't
                ; signal the leftover: the resident's own statement boundary is
                ; the second signal, so this is a DELETE, not the "second flag"
                ; restructure the seam classifier assumed (docs/spec-basic-circle-
                ; restructure.md). Non-comma trailing junk ALREADY fell to
                ; cpt_finish here; the comma now joins it.
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

; cpt_finish / cpt_err24 / cpt_err5 / cpt_err2: return control to the resident
; servicer. DREQ 0 = done; GFX_RES carries the ERR code (0 = ok) and the
; resident's cp_done raises it BEFORE the GFX_OP=4 draw, so a raising exit
; never draws -- which is what the references do too (D-CIRCMISS: R=4, no
; pixel, on all eight dangling-comma rows on BOTH machines). Clobbers A.
cpt_err24:
                ld      a,24
                ld      (GFX_RES),a
                jr      cpt_finish
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

; cpt_angle_defaults: eager (oct,u14)=(0,0) for BOTH boundaries -------------
; (angle 0, the same boundary an omitted end (2*pi) yields by periodicity --
; D-ARCMASK: the all-zero record IS angle 0's marshalling, no special case).
cpt_angle_defaults:
                xor     a
                ld      hl,GFX_SOCT
                ld      b,8                 ; SOCT..EU14, two 4-byte records
cad_lp:
                ld      (hl),a
                inc     hl
                djnz    cad_lp
                ret

; cpt_angle_from_arga: the tail of the old circ_parse_given_angle, from ARGA ---
; canonical (the resident already did eval+widen_rhs_operand). IN: BC=neg-flag
; cell (GFX_SNEG/ENEG), DE=dest record base (GFX_SOCT/EOCT), ARGA=canonical
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

; cpt_asp_scale256: S := TRUNC(minor_ratio*256) -> GFX_ASPS. -----------------
; 🔴 D-CIRCDOM: this used to say "round(...)" and to `call cpt_round`, and the
; reference TRUNCATES. Measured (docs/circdom-msx1-characterization.md §5), all
; at CIRCLE(128,96),r -- whole-pattern-plane differential, minor half-axis read
; off the bounding box:
;
;   aspect  aspect*256  floor  round  VG-8020  zerobas-before
;     .3       76.80      76     77     76         77          <- DIFF
;     .55     140.80     140    141    140        141          <- DIFF
;     .1       25.60      25     26     25         26          <- DIFF (r=255)
;     .7      179.20     179    179    179        179          control, byte-identical
;     .25      64.00      64     64     64         64          control, byte-identical
;
; 3/3 discriminating aspects say TRUNCATE; 2/2 controls (where floor==round, so
; both models predict the SAME picture) came back byte-identical, which is what
; makes the 3 DIFFs attributable to the rounding and not to the rig.
;
; ⚠️ WHY THIS TRUNCATES DIRECTLY: D-CIRCDOM measured the reference truncating
; here while the boundary marshalling rounded, so the two callers split; the
; shared `cpt_round` that forced the choice was retired by D-ARCMASK when the
; boundary marshalling moved to trunc as well (both its trunc sites are
; flt_to_int16). Safe unsigned because cpt_after_aspect has already refused
; aspect<0 and 1/aspect is positive.
;
; ⚠️ THE CORPUS COULD NOT SEE THIS: every aspect the tree had ever drawn
; (.25 -> 64, .5 -> 128, 2 -> 128, 3 -> 85.33, .01/1/100 via dexp5-pin) has
; floor == round. .3 is the first literal in the tree's history where the two
; models come apart -- and it needs r >= 128 for the 1/256 to reach a whole
; pixel, while the gate's largest drawn radius was 20.
cpt_asp_scale256:
                ld      hl,ARGB
                xor     a
                ld      de,256
                call    widen_uint_to       ; ARGB := 256.0
                call    fp_mul              ; ARGA/FAC := minor_ratio*256
                call    flt_to_int16        ; DE := TRUNC(...) -- not cpt_round
                ld      (GFX_ASPS),de
                ret

; cpt_boundary_prep: |angle| -> (oct_raw, u14) record at (GFX_CS_AY). ---------
; D-ARCMASK (2026-08-17, docs/arcmask-msx1-characterization.md §5.5): the
; reference's arc boundary is the octant loop's STEP INDEX distributed
; LINEARLY over the in-octant angle, evaluated in SINGLE precision. Measured:
; 53/54 whole reference planes (arcmask_refmodel2.py), the exact-ray rule this
; replaces scores 2-4/54. The marshalling:
;   P1  round ARGA to 6 significant digits, half-up. ⚠️ LOAD-BEARING: without
;       it the 1.5707963-vs-pi/2 row diverges (53->52, arcmask_asmsim2.py) --
;       the reference keeps the axis point because to 6 digits 1.5707963 IS
;       pi/2. Digits 6..14 (incl. the guard) are zeroed either way.
;   P2  q = theta6 * (4/pi)              one bounded fp_mul -- no series
;   P3  oct_raw = trunc(q)               flt_to_int16 is silent out of domain,
;                                        same contract as the brad it replaces
;   P4  f = q - oct_raw                  ARGB := -oct_raw via widen_uint_to's
;                                        sign argument; ARGA survives P3
;                                        (domain_convert_core unpacks FAC into
;                                        CVT, not ARGA)
;   P5  u14 = trunc(f * 16384)           0..16383
; Replaces the (brad, sign_c, sign_s) marshal, its three quadrant fp_cmp
; compares and their three 18-byte constants, cpt_round and cpt_build_half --
; the quadrant signs are implicit in the octant index.
cpt_boundary_prep:
                ; --- P1: 6-significant-digit round, half-up, in place -------
                ld      hl,ARGA+FPNUM_DIG+6
                ld      a,(hl)
                cp      5
                push    af                  ; CF=1 -> digit 6 < 5, no carry
                ld      b,9                 ; zero digits 6..14 (guard incl.)
cbp_zlp:
                ld      (hl),0
                inc     hl
                djnz    cbp_zlp
                pop     af
                jr      c,cbp_mul           ; truncation WAS the rounding
                ld      hl,ARGA+FPNUM_DIG+5
                ld      b,6
cbp_carry:
                ld      a,(hl)
                inc     a
                cp      10
                jr      c,cbp_cst           ; no overflow -> store, done
                ld      (hl),0
                dec     hl
                djnz    cbp_carry
                ; 0.999999 -> 1.000000: dig0=1 (rest already 0), dexp+1
                ld      hl,ARGA+FPNUM_DIG
                ld      (hl),1
                ld      hl,(ARGA+FPNUM_DEXP)
                inc     hl
                ld      (ARGA+FPNUM_DEXP),hl
                jr      cbp_mul
cbp_cst:
                ld      (hl),a
cbp_mul:
                ; --- P2: q := theta6 * (4/pi) -------------------------------
                ld      hl,GFX_K_4PI
                ld      de,ARGB
                ld      bc,18
                ldir
                call    fp_mul              ; ARGA/FAC := theta6 * 4/pi
                ; --- P3: oct_raw -> record +0/+1 ----------------------------
                call    flt_to_int16        ; DE := trunc(q), silent
                ld      hl,(GFX_CS_AY)
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ; --- P4: f := q - oct_raw -----------------------------------
                ld      hl,ARGB
                ld      a,$80               ; sign: ARGB := -oct_raw
                call    widen_uint_to
                call    fp_add              ; ARGA/FAC := q - oct_raw
                ; --- P5: u14 -> record +2/+3 --------------------------------
                ld      hl,ARGB
                xor     a
                ld      de,16384
                call    widen_uint_to       ; ARGB := 16384.0
                call    fp_mul              ; ARGA/FAC := f * 16384
                call    flt_to_int16        ; DE := trunc, 0..16383
                ld      hl,(GFX_CS_AY)
                inc     hl
                inc     hl
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

; --- FPNUM constant (18-byte record) -----------------------------------------
; 4/pi = 1.2732395447351|6...: 14 significant digits + the guard digit, the
; same layout as the retired K_128_PI it replaces.
GFX_K_4PI:
                db      0, 1,0, 1,2,7,3,2,3,9,5,4,4,7,3,5,1,6
