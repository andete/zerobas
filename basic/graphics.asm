; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; graphics.asm — the SCREEN-2 pixel statements' RESIDENT stubs (graphics arc,
; Slice G2). docs/spec-basic-graphics-g2.md.
;
;   PSET (x,y)[,c]      plot one pixel (colour-clash read-modify-write)
;   PRESET (x,y)[,c]    = PSET whose default colour is BAKCLR (not FORCLR)
;   POINT(x,y)          function -> the pixel's colour (off-screen -> -1)
;
; SPLIT (arc D2/D5): the pixel READ-MODIFY-WRITE itself is a page-0 sub-ROM tenant
; (sub/graphics.asm, GFX_OP=1/2) because it needs direct VDP port I/O with the BIOS
; paged out. These resident stubs do only what must stay resident: evaluate the
; coordinate/colour expressions (eval is resident), the SCREEN-2 mode precheck, the
; STEP/clip policy, and the work-area updates, then marshal a tiny param block and
; hand off with one subrom_call. Repack-only (the page-0 tenant is reachable only in
; the merged build); the lean cart ships no graphics -> byte-identical.
;
; Coordinates are int16 (a coordinate may legally be off-screen, e.g. 300 or -1 —
; a SILENT no-op, NOT clipped; §11.4). Only a coordinate OUTSIDE int16 raises
; (Overflow, ERR 6, inside get_int16_checked). SCREEN 0/1 -> Illegal function call
; (ERR 5). The last-referenced point (GRPACX/GRPACY) AND the pending-target cells
; (GXPOS/GYPOS) move to the resolved (unclipped) coordinate on EVERY PSET/PRESET,
; drawn or not — MEASURED on the VG-8020 (G2-d): PSET(10,20):PSET(300,100) leaves
; GRPAC = (300,100). Only the pixel plot is gated by the on-screen range test.
;
; Clean-room: own-design. PSET/PRESET/POINT + STEP semantics are the public
; MSX-BASIC language reference; the colour-clash rule, the clip/last-point behaviour
; and the tokens are black-box VG-8020 pins (spec §11.3/§11.4/§11.8/§11.9); the
; parser + marshalling are zerobas's own. No disassembly. See basic/PROVENANCE.md.
    IF ROM_BASE < $4000

; --- ex_pset / ex_preset: the pixel-plot statements -------------------------
; Entry: HL on the PSET/PRESET token. The two differ ONLY in the default colour
; used when `,c` is omitted (FORCLR vs BAKCLR); both marshal GFX_OP=1.
ex_pset:
                inc     hl                  ; past the PSET token
                ld      a,(FORCLR)          ; PSET default colour = foreground
                jr      gfx_plot_stmt
ex_preset:
                inc     hl                  ; past the PRESET token
                ld      a,(BAKCLR)          ; PRESET default colour = background
gfx_plot_stmt:
                and     $0F                 ; colour is a 4-bit nibble
                ld      (GFX_C),a           ; provisional default (overridden by ,c below)
                ld      a,(SCRMOD)
                cp      2                   ; SCREEN 2 only (arc D4)
                jp      nz,gfx_err5         ; SCREEN 0/1 -> Illegal function call (ERR 5)
                call    parse_coord         ; BC = x, DE = y (int16, STEP resolved); HL past ')'
                ; --- optional ",c" colour override ---
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,gfx_plot_go      ; no ",c" -> keep the default colour
                inc     hl                  ; consume the ','
                push    bc                  ; save x across the colour eval (eval clobbers all)
                push    de                  ; save y
                call    eval                ; DE = colour (silent int16)
                call    get_int16_checked   ; DE = colour, ERR 6 if > int16
                ld      a,e
                and     $0F                 ; use the low nibble (0..15); see G2 gate note
                ld      (GFX_C),a
                pop     de                  ; restore y
                pop     bc                  ; restore x
gfx_plot_go:
                ; --- work area: unconditional (drawn OR no-op) -- G2-d ---
                ld      (GXPOS),bc          ; pending-target X = resolved x
                ld      (GRPACX),bc         ; last-referenced point X = resolved x
                ld      (GYPOS),de          ; pending-target Y
                ld      (GRPACY),de         ; last-referenced point Y
                ; --- range test decides plot vs silent no-op ---
                call    gfx_in_range        ; CF = 1 iff 0<=x<=255 and 0<=y<=191
                jp      nc,exec_stmt        ; off-screen -> no plot (work area already moved)
                ld      a,1                 ; GFX_OP = 1 -> tenant plot (PSET/PRESET)
                ld      (GFX_OP),a
                push    hl                  ; guard the token cursor -- CALSLT clobbers HL
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS   ; page-0 index 8 = $0028
                call    subrom_call         ; CF=1 iff the sub-ROM is absent (no call made)
                pop     hl
                jp      c,gfx_absent        ; defensive: merged ROM always ships the tenant
                jp      exec_stmt           ; chain the next ':'-separated statement

; --- ev_f_point: POINT(x,y) function -> the pixel's colour ------------------
; Reached from expr.asm's function dispatch (IX = cursor). POINT has NO SCREEN-mode
; precheck (works in any mode; only "no error" is pinned for SCREEN 0/1 -- §11.8/
; G2-e). Off-screen -> -1. POINT is READ-ONLY: it resolves STEP against the last
; point but does NOT move it. Returns DE = value with FACTYP int (the ERR/ERL
; single-token pattern, expr.asm ev_f_errfn).
ev_f_point:
                inc     ix                  ; past the POINT token
                push    ix
                pop     hl                  ; HL = cursor (parse_coord's HL convention)
                call    parse_coord         ; BC = x, DE = y (int16, STEP resolved); HL past ')'
                push    hl                  ; save the advanced cursor across the call
                call    gfx_in_range        ; CF = 1 iff on-screen
                jr      nc,pt_offscreen
                ld      (GXPOS),bc          ; marshal target (POINT does NOT touch GRPAC)
                ld      (GYPOS),de
                ld      a,2                 ; GFX_OP = 2 -> tenant point read
                ld      (GFX_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                call    subrom_call         ; CF=1 iff absent
                jr      c,pt_offscreen      ; defensive: treat an absent tenant as off-screen
                ld      a,(GFX_RES)         ; tenant result: pixel colour 0..15
                ld      e,a
                ld      d,0                 ; DE = colour (positive)
                jr      pt_return
pt_offscreen:
                ld      de,$FFFF            ; off-screen POINT -> -1 (signed int16)
pt_return:
                ld      a,2
                ld      (FACTYP),a          ; result is an int16 (§9.4 domain)
                pop     hl                  ; HL = advanced cursor
                push    hl
                pop     ix                  ; restore IX = cursor for the expr evaluator
                ret

; --- ex_line_gfx: graphics LINE (+ ,B / ,BF box) --- G3 -----------------------
; Entry (from ex_line, files.asm): HL at the first non-space char after the LINE
; token — one of '(' / STEP / '-' . docs/spec-basic-graphics-g3.md.
;   LINE [[STEP](x1,y1)] - [STEP](x2,y2) [, [c] [, B|BF]]
; The first coordinate is optional ('-' -> continue from the last point GRPAC); the
; '-' and second coordinate are mandatory. STEP CHAINS (§3.3, measured): the 2nd
; coordinate's STEP is relative to the FIRST resolved endpoint, so we stage
; GRPACX/GRPACY = p1 before parsing p2 (parse_coord resolves STEP against GRPAC),
; then set GRPAC = p2 at the end. Off-screen endpoints are legal (the tenant clips
; per pixel, §3.4); only |coord| > int16 (in parse_coord) or SCREEN 0/1 raises.
ex_line_gfx:
                ld      a,(SCRMOD)
                cp      2                   ; SCREEN 2 only (arc D4)
                jp      nz,gfx_err5         ; SCREEN 0/1 -> Illegal function call
                ld      a,(FORCLR)
                and     $0F
                ld      (GFX_C),a           ; default colour = foreground (overridden by ,c)
                ld      a,(hl)
                cp      MINUS_TOKEN         ; '-' -> continuation (p1 = last point)
                jr      z,elg_from_grpac
                ; --- explicit first endpoint ---
                call    parse_coord         ; BC = x1, DE = y1 (STEP rel current GRPAC)
                ld      (GFX_X1),bc
                ld      (GFX_Y1),de
                ld      (GRPACX),bc         ; stage running ref = p1 (STEP chain, §3.3)
                ld      (GRPACY),de
                call    skip_spaces
                ld      a,(hl)
                cp      MINUS_TOKEN         ; '-' between the two coordinates is mandatory
                jp      nz,elg_syntax
                inc     hl                  ; consume '-'
                jr      elg_second
elg_from_grpac:
                inc     hl                  ; consume '-'
                ld      bc,(GRPACX)         ; p1 = last-referenced point
                ld      (GFX_X1),bc
                ld      bc,(GRPACY)
                ld      (GFX_Y1),bc         ; GRPAC already = p1 -> p2's STEP resolves vs it
elg_second:
                call    parse_coord         ; BC = x2, DE = y2 (STEP rel GRPAC = p1)
                ld      (GFX_X2),bc
                ld      (GFX_Y2),de
                ; --- optional ",[c][,B|BF]" ---
                xor     a
                ld      (GFX_MODE),a        ; default: segment
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,elg_draw         ; no options
                inc     hl                  ; consume the 1st comma
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; ",," -> colour omitted, straight to box field
                jr      z,elg_box_comma
                call    is_box_kw           ; single-comma box (",B"/",BF") ?
                jr      z,elg_box_read
                ; --- colour expression ---
                call    eval                ; DE = colour (silent int16)
                call    get_int16_checked   ; ERR 6 if > int16
                ld      a,e
                and     $0F
                ld      (GFX_C),a
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,elg_draw         ; ",c" only
elg_box_comma:
                inc     hl                  ; consume the box-introducing comma
                call    skip_spaces
elg_box_read:
                ld      a,(hl)
                cp      'B'                 ; box keyword
                jp      nz,elg_syntax
                inc     hl
                ld      c,1                 ; ,B -> outline
                ld      a,(hl)
                cp      'F'
                jr      nz,elg_box_set
                inc     hl
                ld      c,2                 ; ,BF -> fill
elg_box_set:
                ld      a,c
                ld      (GFX_MODE),a
elg_draw:
                ; --- work area: GXPOS/GYPOS + GRPACX/GRPACY = p2 (endpoint, §11.5) ---
                ld      bc,(GFX_X2)
                ld      (GXPOS),bc
                ld      (GRPACX),bc
                ld      bc,(GFX_Y2)
                ld      (GYPOS),bc
                ld      (GRPACY),bc
                ld      a,3                 ; GFX_OP = 3 -> tenant LINE/box
                ld      (GFX_OP),a
                push    hl                  ; guard the token cursor -- CALSLT clobbers HL
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                call    subrom_call         ; CF=1 iff the sub-ROM is absent
                pop     hl
                jp      c,gfx_absent        ; defensive: merged ROM always ships the tenant
                jp      exec_stmt           ; chain the next ':'-separated statement
elg_syntax:
                ld      a,2                 ; Syntax error (bad LINE form)
                jp      raise_error

; --- is_box_kw: is HL at a "B"/"BF" box suffix? (does NOT advance HL) ----------
; ZF=1 iff HL points at 'B' or 'BF' terminating the statement (next char after it is
; the line/statement terminator 0 or ':'), i.e. a genuine box flag rather than a
; colour expression that merely starts with the variable B (e.g. "B*2"). Clobbers A.
is_box_kw:
                ld      a,(hl)
                cp      'B'
                ret     nz                  ; not 'B' -> NZ (not a box suffix)
                push    hl
                inc     hl
                ld      a,(hl)              ; char after 'B'
                cp      'F'
                jr      nz,ibk_term
                inc     hl
                ld      a,(hl)              ; "BF" -> char after 'F'
ibk_term:
                pop     hl                  ; restore HL (non-destructive peek)
                or      a
                ret     z                   ; 0 (end of line) -> box (ZF=1)
                cp      ':'                 ; ':' (next statement) -> box; else NZ
                ret

; --- parse_coord: parse "[STEP] (x,y)" at HL -------------------------------
; in:  HL = cursor at the coordinate (after the verb/function token).
; out: BC = x, DE = y (int16; STEP already added to GRPACX/GRPACY); HL past ')'.
; A coordinate > int16 aborts ERR 6 (get_int16_checked); a missing '(' / ',' / ')'
; or operand aborts Syntax error (ERR 2) via raise_error, which resets SP to SAVSTK
; -- so the pushed x need not be balanced on the error path. Own-design.
parse_coord:
                call    skip_spaces
                ld      a,(hl)
                cp      STEP_TOKEN          ; $DC -> relative coordinate
                jr      nz,pc_absolute
                inc     hl                  ; consume STEP
                ld      a,1
                jr      pc_flag
pc_absolute:
                xor     a
pc_flag:
                ld      (GFX_REL),a
                call    skip_spaces
                ld      a,(hl)
                cp      '('
                jr      nz,pc_syntax
                inc     hl
                call    eval                ; DE = x (silent int16)
                call    get_int16_checked   ; DE = x, ERR 6 if > int16 (HL guarded)
                push    de                  ; save x across the y eval
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,pc_syntax
                inc     hl
                call    eval                ; DE = y
                call    get_int16_checked
                call    skip_spaces
                ld      a,(hl)
                cp      ')'
                jr      nz,pc_syntax
                inc     hl
                pop     bc                  ; BC = x ; DE = y
                ld      a,(GFX_REL)
                or      a
                ret     z                   ; absolute -> done
                ; --- STEP: add the last-referenced point (HL is the cursor, untouched) ---
                ld      a,(GRPACX)
                add     a,c
                ld      c,a
                ld      a,(GRPACX+1)
                adc     a,b
                ld      b,a                 ; BC = x + GRPACX
                ld      a,(GRPACY)
                add     a,e
                ld      e,a
                ld      a,(GRPACY+1)
                adc     a,d
                ld      d,a                 ; DE = y + GRPACY
                ret
pc_syntax:
                ld      a,2                 ; Syntax error (bad coordinate form)
                jp      raise_error         ; aborts (SP reset) -> the pushed x is discarded

; --- gfx_in_range: is (x,y) on the SCREEN-2 surface? -----------------------
; in: BC = x (int16), DE = y (int16). out: CF = 1 iff 0<=x<=255 and 0<=y<=191,
; else CF = 0 (off-screen -- silent no-op / POINT -1). A negative or >255 coord has
; a non-zero high byte; a y in 0..255 must additionally be < 192. Pure leaf,
; host-unit-tested (tests/test_graphics.py). Clobbers A.
gfx_in_range:
                ld      a,b
                or      a                   ; x high byte -> x < 0 or x > 255
                jr      nz,gir_off
                ld      a,d
                or      a                   ; y high byte -> y < 0 or y > 255
                jr      nz,gir_off
                ld      a,e
                cp      192                 ; y <= 191 ?
                jr      nc,gir_off          ; y >= 192 -> off-screen
                scf                         ; on-screen
                ret
gir_off:
                or      a                   ; CF = 0
                ret

; --- shared error tails -----------------------------------------------------
gfx_err5:
                ld      a,5                 ; Illegal function call (PSET/PRESET in SCREEN 0/1)
                jp      raise_error
gfx_absent:
                ld      a,5                 ; defensive: sub-ROM missing (never on merged build)
                jp      raise_error
gfx_typeerr:
                ld      a,13                ; Type mismatch (G5 PAINT's MSX2 tile$ form, §5)
                jp      raise_error

; --- gfx_eval_int16: "evaluate + strict-int16-check" pair -------------------
; (spec-basic-graphics-g5.md §8 D4 DRY lever). IN: HL = cursor at the
; expression. OUT: DE = value, HL advanced past the expression (ERR 6 aborts
; if the magnitude exceeds int16 -- get_int16_checked's own contract). A
; mechanical fold of the `call eval / call get_int16_checked` pair used at
; ex_paint's C/B sites below. NOTE (space hard-stop, see the G5 slice
; report): this was ALSO applied at PSET/LINE/CIRCLE/parse_coord's own
; pre-existing eval+check sites during the DRY pass (~18 B saved) but was
; REVERTED there once the image still overran $8000 by ~93 B even with it --
; the resident build is currently blocked (see basic/main.asm's own $8000
; gate), so those already-landed, differentially-tested sites could not be
; re-verified before landing; reapplying that broader DRY is safe to retry
; once the space question is resolved. Clobbers A (+ whatever eval/
; get_int16_checked already clobber).
gfx_eval_int16:
                call    eval
                jp      get_int16_checked   ; tail call: ret serves both

; --- gfx_store_colour_checked: "C" RANGE-CHECK+STORE tail -------------------
; (spec-basic-graphics-g5.md §8 D4 DRY lever). IN: DE = an already-eval'd +
; get_int16_checked'd colour value. Range-checks 0..15 (ERR 5 if outside --
; the stricter CIRCLE/PAINT rule, unlike PSET's silent `and $0F` mask) and
; stores to GFX_C. Used by ex_paint's colour parse below. (Was ALSO factored
; into ex_circle/circ_c during the DRY pass, ~10 B saved -- reverted for the
; same reason as gfx_eval_int16 above: unverifiable while the resident build
; is blocked.) Clobbers A.
gfx_store_colour_checked:
                ld      a,d
                or      a
                jr      nz,gfx_err5         ; negative -> ERR 5
                ld      a,e
                cp      16
                jp      nc,gfx_err5         ; > 15 -> ERR 5
                ld      (GFX_C),a
                ret

; =============================================================================
; G4 -- CIRCLE (+ ellipse aspect + start/end-angle arcs + negative-angle
; spokes). docs/spec-basic-graphics-g4.md. Entry: HL just past the CIRCLE
; token. Grammar (§3): CIRCLE [STEP](x,y),r[,[c][,[start][,[end][,aspect]]]].
;
; SPLIT (as G2/G3): the tenant (sub/graphics.asm, GFX_OP=4) owns only the
; midpoint-circle octant generator, the 8.8 minor scale, and the integer
; cross-product arc mask; this resident stub owns the grammar walk, the
; SCREEN-2 precheck, every ERR raise, the math-pack SIN/COS calls (the
; tenant has no float), and the work-area writes.
;
; ARC/ASPECT DEFAULTS (§9 fork not pinned by a captured case, own choice —
; the public MSX-BASIC language reference default: an omitted start defaults
; to 0 radians, an omitted end to a full turn (2*pi, i.e. the SAME boundary
; vector as 0 by periodicity — no separate math-pack call needed for that
; default). Flagged in the G4 slice report as an assumption beyond the
; pinned battery (which never exercises a single-sided start/end omission).
;
; BOTH boundary vectors are computed EAGERLY the moment the "start,end,..."
; zone is entered (circ_start_intro) so every exit path has a valid GFX_SVX/
; SVY/EVX/EVY regardless of which of start/end end up given vs. omitted —
; the given-value paths simply overwrite the default afterward. GFX_ARCF is
; set to 1 only by an ACTUALLY GIVEN start or end (never by entering the
; zone alone), so "CIRCLE(x,y),r,c,,,aspect" (both omitted) still yields the
; full ellipse (ARCF=0), matching the ell_a025-style captured cases.
;
; SPOKES (§5.3) are drawn AFTER the arc/circle op (§9 G4-spoke default), via
; the landed G3 GFX_OP=3 line op reusing GFX_SVX/SVY or GFX_EVX/EVY directly
; as the endpoint offset -- the SAME r-scaled (+ minor-scaled) vector used
; for the arc mask boundary test, unifying the two needs (an implementation
; choice: the spec leaves the S/E vector's exact scale unspecified beyond
; "small integers"; the combined ellipse+arc+spoke case is untested).
; =============================================================================
ex_circle:
                inc     hl                  ; past the CIRCLE token
                ld      a,(SCRMOD)
                cp      2                   ; SCREEN 2 only (arc D4)
                jr      nz,gfx_err5
                call    parse_coord         ; BC=cx, DE=cy (int16, STEP resolved)
                ld      (GFX_CXC),bc
                ld      (GFX_CYC),de
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; the ",r" comma is mandatory
                jp      nz,elg_syntax
                inc     hl
                call    eval                ; DE = radius (silent int16)
                call    get_int16_checked   ; ERR 6 if > int16
                ld      a,d
                or      a
                jp      m,gfx_err5          ; r<0 -> ERR 5 (signed-off G4-rneg deviation)
                ld      (GFX_R),de
                ; --- defaults before the optional fields ---
                ld      a,(FORCLR)
                and     $0F
                ld      (GFX_C),a
                xor     a
                ld      (GFX_ASPMAJ),a
                ld      bc,256              ; NOT hl -- hl is the live token cursor here
                ld      (GFX_ASPS),bc
                xor     a
                ld      (GFX_ARCF),a
                ld      (GFX_SNEG),a
                ld      (GFX_ENEG),a
                ; --- optional ",c" ---
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,circ_draw
                inc     hl
circ_c:
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      z,circ_start_intro  ; c omitted; this comma also intros "start"
                or      a
                jp      z,circ_draw
                cp      COLON
                jp      z,circ_draw
                call    eval
                call    get_int16_checked   ; ERR 6 if > int16
                ld      a,d
                or      a
                jp      nz,gfx_err5         ; negative -> ERR 5 (jp: jr went out of
                                            ; range once this slice's new G5 code
                                            ; earlier in the file lengthened it)
                ld      a,e
                cp      16
                jp      nc,gfx_err5         ; > 15 -> ERR 5
                ld      (GFX_C),a
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,circ_draw
circ_start_intro:
                inc     hl                  ; consume the comma introducing "start"
                ; --- eager defaults: brad=0, sign_c=+1, sign_s=0 (angle 0 -- the
                ; SAME vector an omitted end (2*pi) yields by periodicity, spec
                ; §5.2.1 REVISED trig-free design). Matches the OLD gfx_circ_
                ; default_vec's (r,0) result exactly (verified: gfx_circ_bvec at
                ; brad=0/signc=1/signs=0 folds to cos=+max/sin=0 -> (r,0)), now
                ; expressed as the record the tenant's gfx_circ_bvec reads. No
                ; math-pack call, no float, no HL clobber -- the push/pop guard
                ; the old code needed is gone too.
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
circ_start:
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      z,circ_start_empty  ; empty; this comma also intros "end"
                or      a
                jp      z,circ_draw
                cp      COLON
                jp      z,circ_draw
                ld      bc,GFX_SNEG
                ld      de,GFX_SBRAD
                call    circ_parse_given_angle ; HL := cursor advanced past the expr
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,circ_draw
                inc     hl
                jr      circ_end
circ_start_empty:
                inc     hl                  ; consume the comma, move into "end"
circ_end:
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      z,circ_end_empty    ; empty; this comma also intros "aspect"
                or      a
                jp      z,circ_draw
                cp      COLON
                jp      z,circ_draw
                ld      bc,GFX_ENEG
                ld      de,GFX_EBRAD
                call    circ_parse_given_angle ; HL := cursor advanced past the expr
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,circ_draw
                inc     hl
                jr      circ_aspect
circ_end_empty:
                inc     hl                  ; consume the comma, move into "aspect"
circ_aspect:
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      z,elg_syntax        ; too many args -> Syntax error
                or      a
                jp      z,circ_draw
                cp      COLON
                jp      z,circ_draw
                call    eval                ; HL := cursor advanced past the expr
                push    hl                  ; guard it -- everything below clobbers HL
                ld      hl,ARGA
                call    widen_rhs_operand   ; ARGA := canonical(aspect)
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jp      nz,gfx_err5         ; aspect < 0 -> ERR 5
                ; --- major axis + minor scale S (spec §4.2) ---
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      a,h
                or      a
                jp      m,circ_asp_le1      ; dexp<0 -> aspect<1
                ld      a,l
                or      a
                jp      z,circ_asp_le1      ; dexp==0 -> aspect<1
                ; --- aspect>=1 (dexp>=1): y-major; minor_ratio = 1/aspect ---
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
                call    circ_asp_scale256
                jr      circ_asp_done
circ_asp_le1:
                xor     a
                ld      (GFX_ASPMAJ),a
                call    circ_asp_scale256   ; ARGA still = aspect
circ_asp_done:
                pop     hl
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      z,elg_syntax        ; too many args -> Syntax error
                jp      circ_draw           ; NORMAL exit -- MUST jump, else fall
                                            ; through into circ_asp_scale256 and
                                            ; scale ARGA by 256 a SECOND time
                                            ; (round leaves ARGA=|v|+0.5, so the
                                            ; 2nd fp_mul gives 64.5*256=16512 for
                                            ; aspect .25 -- the ellipse bug)

; --- circ_asp_scale256: ARGA already = the desired minor_ratio (canonical). --
; S := round(minor_ratio*256) -> GFX_ASPS (spec §4.2). Shared tail of the
; aspect<=1 / aspect>1 branches (DRY per the G4 slice byte-budget pass).
; Clobbers everything.
circ_asp_scale256:
                ld      hl,ARGB
                xor     a
                ld      de,256
                call    widen_uint_to       ; ARGB := 256.0
                call    fp_mul              ; ARGA/FAC := minor_ratio*256
                call    gfx_round_arga_de
                ld      (GFX_ASPS),de
                ret

; --- circ_draw: draw (GFX_OP=4), deferred spokes, work area -----------------
; ARCBIG (and S/E themselves) are now TENANT-computed from GFX_SBRAD/EBRAD
; (spec §5.2.1 REVISED, gfx_circ_bvec_prep/gfx_circ_arcbig_calc, sub/graphics.
; asm) -- no resident call needed here any more.
circ_draw:
                ld      a,4                 ; GFX_OP = 4 -> tenant CIRCLE
                ld      (GFX_OP),a
                push    hl                  ; guard the token cursor -- CALSLT clobbers HL
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                call    subrom_call         ; CF=1 iff the sub-ROM is absent
                pop     hl
                jp      c,gfx_absent
                ; --- deferred spokes (spoke-AFTER-arc default, §9 G4-spoke) ---
                ld      a,(GFX_SNEG)
                or      a
                jr      z,circ_no_sspoke
                push    hl
                ld      hl,GFX_SVX
                call    gfx_circ_spoke
                pop     hl
circ_no_sspoke:
                ld      a,(GFX_ENEG)
                or      a
                jr      z,circ_no_espoke
                push    hl
                ld      hl,GFX_EVX
                call    gfx_circ_spoke
                pop     hl
circ_no_espoke:
                ; --- work area (resident writes; §6, §9 G4-work signed-off quirk) ---
                ; BC, NOT HL -- HL is the live token cursor here (the G3 elg_draw
                ; lesson: work-area scratch must not clobber it before exec_stmt).
                ld      bc,(GFX_CXC)
                ld      (GRPACX),bc
                ld      bc,(GFX_CYC)
                ld      (GRPACY),bc
                ld      bc,(GFX_R)
                ld      (GXPOS),bc          ; quirk: GXPOS = r
                ld      bc,(GFX_CYC)
                ld      (GYPOS),bc          ; quirk: GYPOS = cy
                jp      exec_stmt

; --- gfx_circ_spoke: IN HL=vector base (GFX_SVX or GFX_EVX; Y=base+2). ------
; Marshals a GFX_OP=3 segment centre->(centre+vector), the shared body of the
; two former gfx_circ_spoke_s/_e (DRY per the G4 slice byte-budget pass, spec
; §5.3). Clobbers everything.
gfx_circ_spoke:
                push    hl                  ; stash the vector base
                ld      hl,(GFX_CXC)
                ld      (GFX_X1),hl
                ld      hl,(GFX_CYC)
                ld      (GFX_Y1),hl
                pop     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = vector X
                inc     hl
                push    hl                  ; stash the Y-cell address
                ld      hl,(GFX_CXC)
                add     hl,de
                ld      (GFX_X2),hl
                pop     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = vector Y
                ld      hl,(GFX_CYC)
                add     hl,de
                ld      (GFX_Y2),hl
                xor     a
                ld      (GFX_MODE),a        ; segment
                ld      a,3                 ; GFX_OP = 3 -> tenant LINE
                ld      (GFX_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                call    subrom_call
                jp      c,gfx_absent
                ret

; --- circ_parse_given_angle: the shared body of circ_start/circ_end's -------
; GIVEN-value path (DRY per the G4 slice byte-budget pass). IN: HL=cursor at
; the angle expression (caller already confirmed non-empty/non-terminator).
; BC = address of the neg-flag cell (GFX_SNEG or GFX_ENEG); DE = dest
; boundary-RECORD base (GFX_SBRAD or GFX_EBRAD -- §5.2.1 REVISED trig-free
; design; NOT a vector any more). OUT: HL = cursor advanced past the
; expression; the neg-flag cell and the 4-byte record (brad/signc/signs) at
; (dest) are set; GFX_ARCF := 1. Stashes BC/DE in the tenant's own (not-yet-
; live) GFX_CS_AX/AY cells -- safe, the tenant only reads them after the
; LATER GFX_OP=4 call. Clobbers everything + ARGA/ARGB/FAC.
circ_parse_given_angle:
                ld      (GFX_CS_AX),bc      ; stash the neg-flag cell address
                ld      (GFX_CS_AY),de      ; stash the dest record base
                call    eval                ; HL := cursor advanced past the expr
                push    hl                  ; guard it -- everything below clobbers HL
                ld      hl,ARGA
                call    widen_rhs_operand   ; ARGA := canonical(angle)
                ld      a,(ARGA+FPNUM_SIGN)
                ld      hl,(GFX_CS_AX)
                ld      (hl),a              ; negative -> a spoke is drawn later
                xor     a
                ld      (ARGA+FPNUM_SIGN),a ; ARGA := |angle| = a0/a1
                call    gfx_circ_boundary_prep ; reads GFX_CS_AY for the dest base
                ld      a,1
                ld      (GFX_ARCF),a        ; actually GIVEN -> arc mode
                pop     hl                  ; HL := the advanced cursor (see above)
                ret

; =============================================================================
; gfx_circ_boundary_prep -- REVISED 2026-07-21 (spec §5.2.1): TRIG-FREE
; replacement for the old float SIN/COS pipeline (gfx_circ_default_vec/
; gfx_circ_endpoint_vec/gfx_circ_axis_val/gfx_round_nonzero, all removed).
; The original design fed |angle| through the sub-ROM math-pack SIN/COS,
; whose series fp_mul INFINITE-LOOPED in the CIRCLE call context (root-caused
; via scratchpad/g4_hang_probe.py: PC stuck in the sub-ROM's own fp_mul inner
; loop, tenant never entered). This resident half now does only TWO kinds of
; bounded, non-iterative float op -- neither is the series that hung:
;   * THREE fp_cmp compares (theta vs HALF_PI/THREE_HALF_PI/PI_CONST) to
;     pin the quadrant SIGN of the cos/sin components. This must be a
;     CONTINUOUS float compare, not derived from the rounded brad below: at
;     a0=1.57 and a0=1.58 BOTH round to the identical brad=64 (the exact
;     quadrant boundary), so a brad-derived sign would collapse the very
;     near-cardinal distinction the reference is shown to preserve (spec
;     §5.4) -- found by host-fit validation against every captured arc +
;     boundary re-capture BEFORE writing this code
;     (scratchpad/g4_trigfree_final_model.py: ALL MATCH only with the
;     continuous compare; a brad>>6-derived sign regresses arc_0_hpi/
;     arc_hpi_pi). fp_cmp is a pure digit compare (float-arith.asm) -- reads
;     ARGA/ARGB, never mutates ARGA, so all three compares run BEFORE the
;     angle-scaling fp_mul below touches ARGA.
;   * ONE fp_mul (theta * 128/pi, the K_128_PI constant) + gfx_round_arga_de
;     (itself just fp_add-half + flt_to_int16 -- no series) for the
;     magnitude table INDEX (brad), left UNMASKED/un-reduced (mod 2*pi is
;     the tenant's job, done together with the ARCBIG wrap fix -- see
;     sub/graphics.asm gfx_circ_arcbig_calc).
; The tenant (sub/graphics.asm gfx_circ_bvec) turns (brad, sign_c, sign_s)
; into the actual boundary vector via an integer quarter-wave table --
; genuinely no float in the tenant, per the arc's own rule (spec §5.2/§9
; G4-e). IN: ARGA = |angle| (canonical, sign already forced 0); GFX_CS_AY =
; dest record base (GFX_SBRAD or GFX_EBRAD; +2=signc, +3=signs). OUT: the
; 4-byte record at (GFX_CS_AY) is filled. Clobbers everything + ARGA/ARGB/FAC.
; =============================================================================
gfx_circ_boundary_prep:
                ; --- sign_c: +1 if theta<HALF_PI or theta>THREE_HALF_PI; -1 if
                ; strictly between; 0 at either exact boundary (never hit by a
                ; literal user angle in practice; matters only for byte-exact
                ; parity with the continuous reference model, harmless either
                ; way since the paired magnitude is 0 there too) ---
                ld      hl,GFX_HALF_PI
                ld      de,ARGB
                ld      bc,18
                ldir
                call    fp_cmp              ; A = 1(theta<half_pi) / 2(==) / 4(>)
                ld      (GFX_CS_T1),a       ; stash cmp-vs-HALF_PI -- NOT a register:
                                            ; the second ldir's `ld bc,18` clobbers B
                                            ; (found live: this is what flipped every
                                            ; sign_c below THREE_HALF_PI).
                ld      hl,GFX_THREE_HALF_PI
                ld      de,ARGB
                ld      bc,18
                ldir
                call    fp_cmp              ; A = cmp vs THREE_HALF_PI
                ld      c,a                 ; C = cmp vs THREE_HALF_PI
                ld      a,(GFX_CS_T1)
                ld      b,a                 ; B = cmp vs HALF_PI (reloaded AFTER
                                            ; both ldir's are done)
                cp      2
                jr      z,gcbp_signc_zero
                ld      a,c
                cp      2
                jr      z,gcbp_signc_zero
                ld      a,b
                cp      1
                jr      z,gcbp_signc_pos
                ld      a,c
                cp      4
                jr      z,gcbp_signc_pos
                ld      a,$FF               ; HALF_PI < theta < THREE_HALF_PI
                jr      gcbp_signc_store
gcbp_signc_pos:
                ld      a,1
                jr      gcbp_signc_store
gcbp_signc_zero:
                xor     a
gcbp_signc_store:
                ld      hl,(GFX_CS_AY)
                inc     hl
                inc     hl                  ; dest+2 = signc cell
                ld      (hl),a
                ; --- sign_s: +1 if 0<theta<PI; -1 if theta>PI; 0 if theta==0 or PI ---
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero        ; Z=1 iff theta is an exact 0
                jr      z,gcbp_signs_zero
                ld      hl,GFX_PI_CONST
                ld      de,ARGB
                ld      bc,18
                ldir
                call    fp_cmp              ; A = theta vs PI
                cp      2
                jr      z,gcbp_signs_zero
                cp      1
                jr      z,gcbp_signs_pos
                ld      a,$FF               ; theta > PI
                jr      gcbp_signs_store
gcbp_signs_pos:
                ld      a,1
                jr      gcbp_signs_store
gcbp_signs_zero:
                xor     a
gcbp_signs_store:
                ld      hl,(GFX_CS_AY)
                inc     hl
                inc     hl
                inc     hl                  ; dest+3 = signs cell
                ld      (hl),a
                ; --- brad = round(theta * 128/pi) -- ONE bounded fp_mul (not a
                ; series -- safe), left UNMASKED (the tenant reduces mod 256 for
                ; the table lookup and handles the wrap specially for ARCBIG) ---
                ld      hl,GFX_K_128_PI
                ld      de,ARGB
                ld      bc,18
                ldir
                call    fp_mul              ; ARGA/FAC := theta * (128/pi)
                call    gfx_round_arga_de   ; DE := round(...)
                ld      hl,(GFX_CS_AY)
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

; --- FPNUM constants (18-byte records: sign/dexp(2)/dig[15], sysvars.inc's ---
; FPNUM_SIGN/DEXP/DIG layout) for gfx_circ_boundary_prep's bounded compares +
; the brad scale. Own-design decimal digits of pi/2, pi, 3*pi/2, 128/pi (15
; significant digits each -- see the G4 slice report for the derivation).
GFX_HALF_PI:
                db      0, 1,0, 1,5,7,0,7,9,6,3,2,6,7,9,4,8,9
GFX_PI_CONST:
                db      0, 1,0, 3,1,4,1,5,9,2,6,5,3,5,8,9,7,9
GFX_THREE_HALF_PI:
                db      0, 1,0, 4,7,1,2,3,8,8,9,8,0,3,8,4,6,8
GFX_K_128_PI:
                db      0, 2,0, 4,0,7,4,3,6,6,5,4,3,1,5,2,5,2

; --- gfx_round_arga_de: IN ARGA/FAC = value (canonical, sign meaningful). ---
; OUT: DE = round-half-away-from-zero(value) as int16. Own-design (the same
; "abs, +0.5, truncate, reapply sign" shape as the tenant's 8.8 scale).
; Clobbers A, ARGA/ARGB/FAC (via fp_add/flt_to_int16), HL.
gfx_round_arga_de:
                ld      a,(ARGA+FPNUM_SIGN)
                push    af
                xor     a
                ld      (ARGA+FPNUM_SIGN),a ; ARGA := |value|
                ld      hl,ARGB
                call    gfx_build_half      ; ARGB := 0.5
                call    fp_add              ; ARGA/FAC := |value| + 0.5
                call    flt_to_int16        ; DE := trunc(|value|+0.5) = round(|value|)
                pop     af
                or      a
                ret     z                   ; was non-negative -> DE already correct
                xor     a                   ; negate DE
                sub     e
                ld      e,a
                ld      a,0
                sbc     a,d
                ld      d,a
                ret

; --- gfx_build_half: IN HL=dest -> writes the 18-byte 0.5 FPNUM record -------
; (sign=0, dexp=0, dig[0]=5, dig[1..13]+guard=0; the sincos_kernel idiom).
; Clobbers A, B, HL.
gfx_build_half:
                xor     a
                ld      (hl),a              ; sign
                inc     hl
                ld      (hl),a              ; dexp lo
                inc     hl
                ld      (hl),a              ; dexp hi
                inc     hl
                ld      (hl),5              ; dig[0] = 5  (0.5 * 10^0)
                inc     hl
                ld      b,14                ; dig[1..13] + guard
gbh_lp:
                ld      (hl),0
                inc     hl
                djnz    gbh_lp
                ret

; =============================================================================
; G5 -- PAINT (SCREEN-2 flood fill). docs/spec-basic-graphics-g5.md. Entry: HL
; just past the PAINT token. Grammar (§3): PAINT [STEP](x,y)[,[C][,[B]]].
;
; SPLIT (as G2/G3/G4): the tenant (sub/graphics.asm, GFX_OP=5) owns the whole
; scanline span-fill engine; this resident stub owns the grammar walk, the
; SCREEN-2 precheck, the off-screen-seed ERR 5 (DISTINCT from PSET/LINE, which
; silently clip/no-op a point -- spec §3), the C/B parses (incl. the MSX2
; tile$ -> ERR 13 reject and the 4th-argument -> ERR 2 reject), and the
; work-area writes. The tenant's own span-stack overflow (GFX_POVF) is
; surfaced here as ERR 7 (Out of memory) -- spec §4 D3, measured on the
; reference.
;
; Unlike PSET/LINE/CIRCLE, the work-area write (GRPAC/GXPOS/GYPOS = seed) is
; deferred to AFTER every field is parsed (spec §6) -- so a syntax error in
; the C/B fields leaves the work area untouched (raise_error resets SP
; anyway, so this is really just spec-fidelity bookkeeping, not a correctness
; requirement of the abort path itself).
; =============================================================================
ex_paint:
                inc     hl                  ; past the PAINT token
                ld      a,(SCRMOD)
                cp      2                   ; SCREEN 2 only (arc D4)
                jp      nz,gfx_err5         ; SCREEN 0/1 -> Illegal function call
                call    parse_coord         ; BC = seed x, DE = seed y (STEP resolved)
                call    gfx_in_range        ; CF = 1 iff 0<=x<=255 and 0<=y<=191
                jp      nc,gfx_err5         ; off-screen seed -> ERR 5 (spec §3 --
                                            ; NOT a silent clip like PSET/LINE)
                push    bc                  ; guard the seed across the C/B field
                push    de                  ; parses (eval/str_eval_one clobber all)
                ; --- default colour = FORCLR ---
                ld      a,(FORCLR)
                and     $0F
                ld      (GFX_C),a
                ; --- optional ",[C][,[B]]" ---
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,ep_default_b     ; no fields at all -> C=FORCLR, B=C
                inc     hl                  ; consume the comma
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      z,ep_c_empty        ; ",," -> C omitted; this comma intros B
                or      a
                jr      z,ep_default_b      ; terminator -> C=FORCLR, B=C
                cp      COLON
                jr      z,ep_default_b
                ; --- given C: the MSX2 tile$ form -> ERR 13 (spec §5); else
                ; eval + range-check 0..15 -> ERR 5 (the CIRCLE/PAINT rule) ---
                call    str_eval_one        ; CF=1 iff a string operand (HL past it)
                jp      c,gfx_typeerr       ; a string colour operand -> Type mismatch
                call    gfx_eval_int16      ; DE = value (silent int16); ERR 6 if > int16
                call    gfx_store_colour_checked  ; ERR 5 if outside 0..15; GFX_C=value
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,ep_default_b     ; no ",B" -> B = C
                inc     hl                  ; consume the comma introducing B
                jr      ep_parse_b
ep_c_empty:
                inc     hl                  ; consume the shared comma
ep_parse_b:
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,ep_default_b      ; empty B field -> B = C
                cp      COLON
                jr      z,ep_default_b
                cp      ','
                jp      z,ep_syntax         ; a 3rd comma here => a 4th argument -> ERR 2
                ; --- given B: eval only, NOT range-checked (spec §3/§5 -- a
                ; border of 16+ is legal, just a comparison value no pixel hits) ---
                call    gfx_eval_int16      ; DE = value (silent int16); ERR 6 if > int16
                ld      a,e
                ld      (GFX_B),a           ; low byte only (spec §6: GFX_B is 1 B)
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      z,ep_syntax         ; a 4th argument -> ERR 2
                jr      ep_draw
ep_default_b:
                ld      a,(GFX_C)
                ld      (GFX_B),a
ep_draw:
                pop     de                  ; seed y
                pop     bc                  ; seed x
                ld      (GXPOS),bc          ; work area (spec §6): unconditional, AFTER
                ld      (GRPACX),bc         ; every field is parsed (unlike PSET's
                ld      (GYPOS),de          ; "unconditional as soon as the seed is
                ld      (GRPACY),de         ; known" -- both already validated on-screen)
                ld      a,5                 ; GFX_OP = 5 -> tenant PAINT
                ld      (GFX_OP),a
                push    hl                  ; guard the token cursor -- CALSLT clobbers HL
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                call    subrom_call         ; CF=1 iff the sub-ROM is absent
                pop     hl
                jp      c,gfx_absent        ; defensive: merged ROM always ships the tenant
                ld      a,(GFX_POVF)
                or      a
                jp      nz,ep_overflow      ; span-stack overflow -> ERR 7 (spec §4 D3)
                jp      exec_stmt           ; chain the next ':'-separated statement
ep_overflow:
                ld      a,7                 ; Out of memory (measured, spec §4 D3)
                jp      raise_error
ep_syntax:
                ld      a,2                 ; Syntax error (a 4th PAINT argument)
                jp      raise_error

    IF G6_RESIDENT
; ===========================================================================
; G6 -- DRAW <string>. docs/spec-basic-graphics-g6.md.
;
; The resident half is deliberately thin: evaluate the string, PRE-PASS it into
; GFX_DBUF, marshal, one subrom_call. All the language lives in the tenant
; (sub/graphics.asm gfx_draw_op), because resident page-1 space is the binding
; constraint of this whole arc and the sub-ROM has room.
;
; THE PRE-PASS (spec §7) is why the tenant can stay variable-free. A page-0
; tenant runs with the float pack (page-0 low) switched out, so the int coercion
; behind `=var;` is simply unreachable from there. So the resident resolves both
; substitution forms first:
;   `=expr;`   -> a 3-byte binary literal escape (GFX_DESC + the coerced int16),
;                 which costs no int->decimal formatting;
;   `X expr$;` -> the string's body spliced inline and RE-SCANNED, so nesting
;                 falls out for free (measured to nest on the reference).
; Each substitution's text is first copied into the bounded GFX_DEXP scratch, so
; eval/str_eval can never walk past the end of the string body into the heap --
; and a missing `;` is then exactly the measured ERR 5 rather than a wild read.
;
; Clean-room: own-design; the DRAW language is the public MSX-BASIC language
; reference and every behavioural rule is our own black-box measurement
; (scratchpad/g6_draw_notes.md). No disassembly.
; ===========================================================================
ex_draw:
                inc     hl                  ; past the DRAW token
                ld      a,(SCRMOD)
                cp      2                   ; SCREEN 2 only (arc D4)
                jp      nz,gfx_err5         ; SCREEN 0/1 -> ERR 5 (measured)
                call    str_eval            ; STRPTR -> [len][ptr]; CF=1 iff a string
                jp      nc,gfx_typeerr      ; DRAW 5 -> Type mismatch (measured)
                call    check_expr_errors   ; surface a deferred string error
                push    hl                  ; guard the statement cursor
                ld      hl,(STRPTR)
                ld      a,(hl)              ; A = length
                call    pu_deref_body       ; HL = body address (A preserved)
                ld      b,a
                ld      de,GFX_DBUF
                xor     a
                ld      (GFX_DDEPTH),a
                call    gdw_prepass         ; DE = one past the last emitted byte
                ld      (GFX_DEND),de
                ld      a,(ATRBYT)
                and     $0F
                ld      (GFX_C),a           ; a colourless DRAW plots in the shared
                                            ; attribute, NOT in FORCLR (spec §6)
                ld      a,6                 ; GFX_OP = 6 -> tenant DRAW
                ld      (GFX_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                call    subrom_call         ; CF=1 iff the sub-ROM is absent
                pop     hl
                jp      c,gfx_absent
                ld      a,(GFX_RES)
                or      a
                jp      nz,raise_error      ; the tenant's ERR code (the §5 table)
                jp      exec_stmt

; ---------------------------------------------------------------------------
; gdw_prepass -- copy [HL,+B) into the buffer at DE, resolving `=` and `X`.
; Recursive (one level per X splice), depth-capped by GFX_DDEPTH so a
; self-referential `A$="XA$;"` cannot run the Z80 stack into the ground.
; ---------------------------------------------------------------------------
gdw_prepass:
                ld      a,b
                or      a
                ret     z                   ; empty string draws nothing (measured)
gdw_pp_loop:
                ld      a,(hl)
                cp      '='
                jr      z,gdw_pp_sub
                cp      'X'
                jr      z,gdw_pp_splice
                cp      'x'
                jr      z,gdw_pp_splice
                ld      (de),a              ; an ordinary byte: copy it through
                inc     hl
                inc     de
                call    gdw_pp_room
                djnz    gdw_pp_loop
                ret

; --- `=expr;` -> the GFX_DESC binary literal escape ---
gdw_pp_sub:
                inc     hl
                dec     b                   ; past the '='
                call    gdw_grab_expr       ; text -> GFX_DEXP; HL/B past the ';'
                push    bc
                push    hl
                push    de
                ld      hl,GFX_DEXP
                call    gfx_eval_int16      ; DE = the coerced int16 (ERR 6 if > int16)
                ld      (GFX_DVAL),de
                pop     de
                pop     hl
                pop     bc
                ld      a,GFX_DESC
                ld      (de),a
                inc     de
                ld      a,(GFX_DVAL)
                ld      (de),a
                inc     de
                ld      a,(GFX_DVAL+1)
                ld      (de),a
                inc     de
                call    gdw_pp_room
                ld      a,b
                or      a
                jr      nz,gdw_pp_loop
                ret

; --- `X expr$;` -> splice the string body in and re-scan it ---
gdw_pp_splice:
                inc     hl
                dec     b                   ; past the 'X'
                call    gdw_grab_expr       ; text -> GFX_DEXP; HL/B past the ';'
                ld      a,(GFX_DDEPTH)
                inc     a
                cp      9                   ; D-G6-4: own-design splice depth cap
                jp      nc,gfx_err5
                ld      (GFX_DDEPTH),a
                push    bc
                push    hl
                push    de
                ld      hl,GFX_DEXP
                call    str_eval
                jp      nc,gfx_typeerr      ; X of a numeric expression -> Type mismatch
                ld      hl,(STRPTR)
                ld      a,(hl)
                call    pu_deref_body       ; HL = body, A = length
                ld      b,a
                pop     de
                call    gdw_prepass         ; recurse: emit the substring's own commands
                pop     hl
                pop     bc
                ld      a,(GFX_DDEPTH)
                dec     a
                ld      (GFX_DDEPTH),a
                ld      a,b
                or      a
                jr      nz,gdw_pp_loop
                ret

; ---------------------------------------------------------------------------
; gdw_grab_expr -- copy the source bytes up to the next ';' into GFX_DEXP,
; NUL-terminated, and advance HL/B past that ';'. No ';' in what remains (or a
; longer run than the scratch holds) -> ERR 5, which is exactly the measured
; behaviour of `DRAW"U=V"` and `DRAW"XA$"`. Clobbers A/C.
; ---------------------------------------------------------------------------
gdw_grab_expr:
                push    de
                ld      de,GFX_DEXP
                ld      c,GFX_DEXP_CAP
gdw_ge_lp:
                ld      a,b
                or      a
                jp      z,gfx_err5          ; ran out of source with no ';'
                ld      a,(hl)
                cp      ';'
                jr      z,gdw_ge_end
                ld      (de),a
                inc     de
                inc     hl
                dec     b
                dec     c
                jp      z,gfx_err5          ; expression longer than the scratch
                jr      gdw_ge_lp
gdw_ge_end:
                inc     hl
                dec     b                   ; consume the ';'
                xor     a
                ld      (de),a              ; NUL-terminate for eval/str_eval
                pop     de
                ret

; ---------------------------------------------------------------------------
; gdw_pp_room -- DE has just advanced; ERR 5 if it has left the buffer.
; ---------------------------------------------------------------------------
gdw_pp_room:
                push    hl
                ld      hl,GFX_DBUF + GFX_DBUF_CAP
                or      a
                sbc     hl,de
                pop     hl
                ret     nc
                jp      gfx_err5            ; splice/expansion overran the buffer (D-G6-4)
    ENDIF

    ENDIF
