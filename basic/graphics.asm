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
; hand off with one subrom_call.
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
                call    gfx_eval_int16   ; DE = colour, ERR 6 if > int16
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
                call    gfx_eval_int16   ; ERR 6 if > int16
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
                ; The work-area writes (GXPOS/GYPOS + GRPACX/GRPACY = p2, §11.5)
                ; moved INTO the tenant with G8's space carve -- it already has
                ; GFX_X2/GFX_Y2 in RAM, so they cost nothing there and freed 24
                ; resident bytes (docs/spec-basic-graphics-g8.md §6).
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
                call    gfx_eval_int16   ; DE = x, ERR 6 if > int16 (HL guarded)
                push    de                  ; save x across the y eval
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,pc_syntax
                inc     hl
                call    gfx_eval_int16   ; DE = value; ERR 6 if > int16
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
                ; CIRCLE re-hosted as an eval-bounce co-routine (docs/spec-circle-
                ; coroutine-space.md). The grammar walk AND the angle/aspect float
                ; math now live in the page-1 tenant gfx_circle_parse (sub/circleparse.
                ; asm), which reclaims ~350-500 B of resident page-1 to fund the
                ; interrupt-trap arc. The tenant can't call eval/parse_coord (main
                ; page-1, switched out under it), so it walks the grammar over the RAM
                ; token stream and REQUESTS each value via GFX_DREQ; this thin resident
                ; servicer resolves the request (parse_coord / gfx_eval_int16 / eval),
                ; advances the shared cursor GFX_DPTR, and re-enters. On "done" it does
                ; the resident GFX_OP=4 geometry call (page-0 tenant -- the parse tenant
                ; can't nest-call it). HL enters just past the CIRCLE token.
                inc     hl                  ; past the CIRCLE token
                ld      a,(SCRMOD)
                cp      2                   ; SCREEN 2 only (arc D4)
                jp      nz,gfx_err5
                ld      (GFX_DPTR),hl       ; seed the shared token cursor
                xor     a
                ld      (GFX_DRESUME),a     ; first entry is a fresh parse
                ld      (GFX_RES),a         ; clear the tenant error slot
cp_loop:
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_CIRCLEPARSE
                call    subrom_call         ; run the page-1 parse tenant; CF=1 if absent
                jp      c,gfx_absent
                ld      a,(GFX_DREQ)
                or      a
                jr      z,cp_done           ; 0 = the tenant finished parsing
                ld      hl,(GFX_DPTR)       ; resolve the request from the cursor
                dec     a
                jr      z,cp_req_coord      ; DREQ=1: parse centre (x,y)
                dec     a
                jr      z,cp_req_int        ; DREQ=2: eval int16 (r / c)
                ; DREQ=3: eval a float expression (angle / aspect) -> ARGA canonical
                call    eval                ; HL advanced; value in FAC
                ld      (GFX_DPTR),hl
                ld      hl,ARGA
                call    widen_rhs_operand   ; ARGA := canonical(value); tenant reads it
                jr      cp_resume
cp_req_coord:
                call    parse_coord         ; BC=cx, DE=cy (STEP resolved), HL advanced
                ld      (GFX_CXC),bc
                ld      (GFX_CYC),de
                ld      (GFX_DPTR),hl
                jr      cp_resume
cp_req_int:
                call    gfx_eval_int16      ; DE=value, HL advanced (ERR 6 if > int16)
                ld      (GFX_DPTR),hl
                ld      (GFX_DVAL),de
cp_resume:
                ld      a,1
                ld      (GFX_DRESUME),a
                jr      cp_loop
cp_done:
                ld      a,(GFX_RES)
                or      a
                jp      nz,raise_error      ; the tenant's ERR code (ERR 2/5/6 sites)
                ld      a,4                 ; GFX_OP = 4 -> tenant CIRCLE geometry
                ld      (GFX_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                call    subrom_call
                jp      c,gfx_absent
                ld      hl,(GFX_DPTR)       ; continue the statement stream after CIRCLE
                jp      exec_stmt

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
; The resident half is deliberately thin (D-G6-1b): evaluate the string, hand its
; body to the tenant, then serve the tenant's substitution requests until it says
; it is finished. All the language lives in the tenant (sub/graphics.asm
; gfx_draw_op), because resident page-1 space is the binding constraint of this
; whole arc and the sub-ROM has room.
;
; THE CO-ROUTINE. `=expr;` and `X expr$;` need eval/str_eval, which a page-0
; tenant cannot reach (eval bottoms out in the float pack, which lives in the
; page-0 low region that the sub-ROM has replaced). So the tenant parses until it
; meets one, copies the text to GFX_DEXP, sets GFX_DREQ and returns; we resolve
; that ONE substitution into GFX_DVAL/GFX_DVLEN and re-enter with GFX_DRESUME=1.
; The tenant banks the value and re-parses the same command, which now finds it
; ready. Round trips only happen per substitution, so an ordinary DRAW string
; costs exactly one subrom_call.
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
                call    gdw_hand_string     ; GFX_DVAL/GFX_DVLEN = the body + length
                ld      a,(ATRBYT)
                and     $0F
                ld      (GFX_C),a           ; a colourless DRAW plots in the shared
                                            ; attribute, NOT in FORCLR (spec §6)
                ld      a,6                 ; GFX_OP = 6 -> tenant DRAW
                ld      (GFX_OP),a
                xor     a
                ld      (GFX_DRESUME),a     ; the first entry is a fresh parse
gdw_call:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                call    subrom_call         ; CF=1 iff the sub-ROM is absent
                jp      c,gdw_absent
                ld      a,(GFX_DREQ)
                or      a
                jr      z,gdw_finish        ; the tenant is done
                dec     a
                jr      z,gdw_want_int
                ; --- the tenant wants a STRING (the X command) ---
                ld      hl,GFX_DEXP
                call    str_eval
                jp      nc,gfx_typeerr      ; X of a numeric expression -> Type mismatch
                call    gdw_hand_string
                jr      gdw_resume
gdw_want_int:
                ld      hl,GFX_DEXP
                call    gfx_eval_int16      ; DE = the coerced int16 (ERR 6 if > int16)
                ld      (GFX_DVAL),de
gdw_resume:
                ld      a,1
                ld      (GFX_DRESUME),a
                jr      gdw_call
gdw_finish:
                pop     hl
                ld      a,(GFX_RES)
                or      a
                jp      nz,raise_error      ; the tenant's ERR code (the §5 table)
                jp      exec_stmt
gdw_absent:
                pop     hl                  ; defensive: merged ROM always ships the tenant
                jp      gfx_absent

; --- gdw_hand_string: the just-evaluated string (STRPTR) -> GFX_DVAL/GFX_DVLEN.
; The tenant COPIES that body into its own frame buffer immediately, which is what
; makes the round trip safe: a later eval here may reuse the temp-string pool the
; body lives in.
gdw_hand_string:
                ld      hl,(STRPTR)         ; the [len][ptr] descriptor
                ld      a,(hl)
                ld      (GFX_DVLEN),a
                call    pu_deref_body       ; HL = body address (A preserved)
                ld      (GFX_DVAL),hl
                ret
    ENDIF

; ===========================================================================
; G7 -- SPRITES: SPRITE$(n)= / SPRITE$(n) / PUT SPRITE / SPRITE ON|OFF|STOP
; docs/spec-basic-graphics-g7.md. The RESIDENT half EVALUATES and nothing else:
; `eval`, the string heap and the token cursor are page-1 resident, so the parse
; lives here and every decision downstream of the values -- entry size and
; address, the domain checks, the early-clock rule, the x4 pattern scaling, the
; merge that makes an omitted argument keep the byte already in the entry -- is
; the page-0 tenant's (sub/graphics.asm, GFX_OP = 7/8/9). That split is what
; keeps this half inside the page-1 tail (spec §7/§8).
;
; Every rule is a black-box measurement (scratchpad/g7_sprite_notes.md), never a
; disassembly.
; ===========================================================================
    IF G7_RESIDENT

; --- ex_sprite: the statement forms that START with the SPRITE token --------
; `SPRITE$(n) = <string$>` (the pattern write) and the three trap-arming forms
; `SPRITE ON|OFF|STOP`, which are accepted no-ops (D-G7-4: the trap itself is the
; interrupt-trap slice's; the reference accepts them in EVERY mode, SCREEN 0 too).
; A bare `SPRITE` is Syntax error (measured).
ex_sprite:
                inc     hl                  ; past the SPRITE token
                ld      a,(hl)
                cp      '$'                 ; the `$` is separate ASCII (crunch pin)
                jr      z,spr_assign
                call    skip_spaces
                ld      a,(hl)
    IF TRAPS_T4
                ; The shared decode (program.asm onoff_decode). ⚠️ It lives behind
                ; `IF the repack build`, and this routine is always-assembled
                ; page-1 code, so the split here is NOT cosmetic: TRAPS_T4 is
                ; (spec-basic-missing-class S-MC-5). The ELSE arm is the
                ; original instruction sequence, unchanged.
                call    onoff_decode        ; A = ZTS_OFF / ZTS_ON / ZTS_STOP
                jp      nc,gfx_syntax       ; bare SPRITE -> ERR 2 (measured)
spr_set:
                ; DELIBERATELY NO EDGE-SHADOW SEED -- and unlike ex_stop's, this is not
                ; even a judgement call: SPRITE is a LEVEL sampled per frame, with no
                ; shadow to seed (sprtrap.asm). A collision already present when
                ; `SPRITE ON` runs FIRES, measured (spec-traps-t4-sprite.md §1.3), so
                ; there is nothing to suppress. `SPRITE STOP` is a plain suspend: it
                ; does NOT latch, and a collision that happened while suspended is
                ; forgotten -- also measured, built decisive by moving the sprites
                ; APART before re-enabling.
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                push    hl                  ; guard the exec-continue ptr across set_state
                ld      hl,ZTRAP+ZTI_SPRITE*ZTRAP_ENTSZ
                call    set_state
                pop     hl
                jp      exec_stmt           ; continue the line (a bare `ret` would
                                            ; SWALLOW the rest of it -- the T1 lesson)
    ELSE
                cp      ON_TOKEN
                jr      z,spr_on
                cp      OFF_TOKEN
                jr      z,spr_off
                cp      STOP_TOKEN
                jp      nz,gfx_syntax       ; bare SPRITE -> ERR 2 (measured)
spr_on:
spr_off:
                inc     hl                  ; D-G7-4: accepted no-op (trap not built)
                jp      exec_stmt
    ENDIF

; --- gfx_syntax: a TRAPPABLE Syntax error (ERR 2) --------------------------
; NOT `jp stmt_error`: that prints and aborts the RUN, so an `ON ERROR GOTO`
; program never sees it -- the reference raises a trappable ERR 2 for every
; malformed sprite statement (Phase O caught exactly this on the first run).
gfx_syntax:
                ld      a,2
                jp      raise_error

; --- SPRITE$(n) = <string$> ------------------------------------------------
; WRITING needs a graphics mode (SCREEN 0 -> ERR 5) even though READING does not
; (§3, the measured asymmetry). Short strings zero-pad and long ones truncate --
; both fall out of handing the tenant min(len,32) bytes and their count.
spr_assign:
                inc     hl                  ; past the '$'
                ld      a,(SCRMOD)
                or      a
                jp      z,gfx_err5          ; SPRITE$= in SCREEN 0 -> ERR 5
                call    spr_parse_index     ; GFX_SN = n; HL past ')'
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN
                jp      nz,gfx_syntax       ; `SPRITE$(0)` with no `=` -> ERR 2
                inc     hl
                call    str_eval            ; STRPTR -> [len][ptr]; CF=1 iff a string
                jp      nc,gfx_typeerr      ; SPRITE$(0)=5 -> ERR 13 (measured)
                call    check_expr_errors
                push    hl                  ; guard the statement cursor
                ld      hl,(STRPTR)         ; the [len][ptr] descriptor -- the tenant
                ld      (GFX_SDESC),hl      ; dereferences it and does the copy, the
                                            ; truncate and the pad (string bodies live
                                            ; in page-3 RAM, which it can read)
                ld      a,7                 ; GFX_OP = 7 -> tenant pattern write
                call    spr_tenant
                pop     hl
                jp      exec_stmt

; --- ev_f_sprite: SPRITE$(n) as a string FACTOR -----------------------------
; Reached from str_eval_one (basic/strvar.asm) with HL ON the SPRITE token. The
; result is EXACTLY the entry size the tenant reports -- never the length that was
; assigned (§3). Legal in every screen mode, SCREEN 0 included.
ev_f_sprite:
                inc     hl                  ; past the SPRITE token
                ld      a,(hl)
                cp      '$'
                jp      nz,str_eval_no      ; not SPRITE$ -> not a string operand
                inc     hl
                call    spr_parse_index     ; GFX_SN = n; HL past ')'
                push    hl                  ; guard the cursor across the read
                ld      a,8                 ; GFX_OP = 8 -> tenant pattern read
                call    spr_tenant
                ld      a,(GFX_VLEN)
                call    str_temp_alloc      ; HL = temp descriptor, DE = body (0 = failed)
                ld      (STRPTR),hl
                ld      a,d
                or      e
                jr      z,spr_rd_done       ; allocation failed -> the empty temp stands
                ld      hl,GFX_VBUF
                ld      a,(GFX_VLEN)
                ld      c,a
                ld      b,0
                ldir
spr_rd_done:
                pop     hl
                jp      str_eval_ok

; --- spr_parse_index: "(n)" -> GFX_SN, HL past ')' -------------------------
; n is an ordinary numeric expression (ERR 6 beyond int16, inside gfx_eval_int16);
; its 0..255 domain is the tenant's check, so the ERR 5 comes back through
; spr_tenant like every other sprite domain error. Clobbers A, DE.
spr_parse_index:
                call    g8_open_paren       ; DE = n, HL past ')' (shared with G8's
                ld      (GFX_SN),de         ; VDP(n)/BASE(n) -- same grammar, and
                ret                         ; `SPRITE$0` -> ERR 2 either way)

; --- spr_tenant: run one sprite tenant op (A = GFX_OP) and raise its error --
; The sprite ops carry no colour, so unlike the drawing statements this leaves
; GFX_C alone (the tenant's ATRBYT stamp deliberately skips ops 7/8/9 -- sprites
; measurably do not touch the shared graphics attribute). Clobbers A, IX.
spr_tenant:
                ld      (GFX_OP),a
                xor     a
                ld      (GFX_RES),a         ; 0 = no error; the tenant sets 5 on a domain miss
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                call    subrom_call         ; CF=1 iff the sub-ROM is absent (clobbers all --
                                            ; every caller guards its own cursor)
                jp      c,gfx_absent        ; defensive: merged ROM always ships it
                ld      a,(GFX_RES)
                or      a
                ret     z
                jp      raise_error         ; the tenant's ERR code (ERR 5, §6)

; --- SCREEN's sprite-size argument (D-G7-2) --------------------------------
; `SCREEN <mode>,<size>` selects 8x8 vs 16x16 (bit 1) and magnification (bit 0),
; and the setting PERSISTS across later SCREEN statements that omit it -- both
; measured. RG1SAV bits 1..0 ARE that state (the tenant reads them for the entry
; size and the pattern scaling), so persistence is just "re-apply them after
; CHGMOD", which is also where the attribute-x snapshot goes (D-G7-3).
; Called from ex_screen (basic/screen.asm).
spr_mode_save:
                ld      a,(RG1SAV)
                and     $03                 ; remember the size across CHGMOD, which
                ld      (GFX_SSIZE),a       ; re-writes VDP register 1 from its own table
                ld      a,10                ; tenant: snapshot the 32 attribute x bytes
                jr      spr_tenant
spr_mode_restore:
                ld      a,11                ; tenant: put the x bytes back (CHGMOD zeroes
                jr      spr_tenant          ; them; the reference leaves them alone) AND
                                            ; re-apply the size bits to VDP register 1
; spr_extra_arg: one evaluated trailing SCREEN argument (DE = its value). Only the
; FIRST is the sprite size; the rest (key click, baud, printer) stay ignored.
spr_extra_arg:
                ld      a,(GFX_SARGN)
                inc     a
                ld      (GFX_SARGN),a
                dec     a
                ret     nz
                ld      a,e
                and     $03
                ld      (GFX_SSIZE),a
                ld      a,12                ; tenant: apply the size bits to register 1
                jr      spr_tenant

; --- ex_put_sprite: PUT SPRITE p[,(x,y)|STEP(dx,dy)][,c][,n] ---------------
; Reached from ex_put (basic/field.asm) with HL ON the SPRITE token. Parses into
; the parameter block with a "given" flag per optional argument, then ONE tenant
; call does the merge. Coordinates go over RAW (unwrapped, possibly negative) --
; the tenant applies the mod-256 store and the early-clock rule, and the work area
; measurably keeps the raw value.
ex_put_sprite:
                inc     hl                  ; past the SPRITE token
                ld      a,(SCRMOD)
                or      a
                jp      z,gfx_err5          ; PUT SPRITE in SCREEN 0 -> ERR 5
                xor     a
                ld      (GFX_SFLAGS),a
                call    gfx_eval_int16      ; DE = plane (domain checked by the tenant)
                ld      (GFX_SN),de
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,gfx_syntax       ; `PUT SPRITE 0` -> ERR 2 (measured)
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                cp      '('
                jr      z,pspr_coords
                cp      STEP_TOKEN
                jr      z,pspr_coords
                cp      ','
                jr      z,pspr_optional     ; `PUT SPRITE p,,c,n` keeps BOTH coordinates
                jp      gfx_syntax          ; `PUT SPRITE 0,` -> ERR 2 (measured)
pspr_coords:
                call    parse_coord         ; BC = x, DE = y (int16, STEP resolved)
                ld      (GXPOS),bc          ; the work area takes the RAW coordinate
                ld      (GRPACX),bc
                ld      (GYPOS),de
                ld      (GRPACY),de         ; ... which is ALSO how the tenant reads them:
                                            ; GXPOS/GYPOS are the arc's pinned coordinate
                                            ; marshalling cells (no G7-private pair)
                ld      a,1                 ; bit 0 = coordinates given
                ld      (GFX_SFLAGS),a
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,pspr_go
pspr_optional:
                inc     hl                  ; past the ',' before the colour
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      z,pspr_pattern      ; colour omitted -> keep the entry's colour
                call    gfx_eval_int16      ; DE = colour (domain checked by the tenant)
                ld      (GFX_SC),de
                ld      a,(GFX_SFLAGS)
                or      $02                 ; bit 1 = colour given
                ld      (GFX_SFLAGS),a
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,pspr_go
pspr_pattern:
                inc     hl                  ; past the ',' before the pattern number
                call    gfx_eval_int16      ; DE = pattern number
                ld      (GFX_SPATN),de
                ld      a,(GFX_SFLAGS)
                or      $04                 ; bit 2 = pattern given
                ld      (GFX_SFLAGS),a
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      z,gfx_syntax        ; a 5th argument -> ERR 2 (measured)
pspr_go:
                push    hl
                ld      a,9                 ; GFX_OP = 9 -> tenant attribute merge
                call    spr_tenant
                pop     hl
                jp      exec_stmt

    ENDIF


    IF G8_RESIDENT
; =============================================================================
; G8 -- VDP(n) / BASE(n): the VDP-register and table-base pseudo-arrays.
; docs/spec-basic-graphics-g8.md. The READS are wholly resident: both are plain
; work-area fetches (RG0SAV.. and BASETAB), so marshalling them into the tenant
; would cost more page-1 bytes than it saves. The WRITES marshal to the tenant
; (GFX_OP 13/14), which owns the ports, the domain checks and the register
; programming.
;
; `BASE(n)` USED TO BE DESCOPED here -- it parsed its argument, returned 0 and
; set ERRMARK, because zerobas had no per-mode table map of its own. It now has
; one for free: our C-BIOS runtime maintains BASETAB identically to the
; reference in every mode (spec §4.1, measured both sides), so the divergence is
; retired rather than reimplemented.

; --- ev_f_vdp / ev_f_base: the function forms (expr.asm dispatch, IX cursor) --
; One body for both: they differ only in the index limit and in whether the
; result is a byte from the register mirrors or a word from the table. Returns
; DE = value with FACTYP int, the ERR/ERL single-token pattern. The expression
; evaluator runs on HL, so this switches cursors the way ev_f_point does.
ev_f_vdp:
                ld      a,9                 ; VDP(n): n in 0..8
                jr      g8_fn
ev_f_base:
                ld      a,20                ; BASE(n): n in 0..19
g8_fn:
                ld      (GFX_G8V),a         ; park the limit in RAM, NOT in a register:
                                            ; eval clobbers BC on its float path, which
                                            ; is how a first cut turned every fractional
                                            ; index (VDP(1.7), even VDP(1.0)) into a
                                            ; bogus ERR 5 while integer ones passed
                inc     ix                  ; past the VDP / BASE token
                push    ix
                pop     hl
                call    g8_open_paren       ; DE = n, HL past ')'
                push    hl
                pop     ix
                ld      a,d
                or      a
                jp      nz,gfx_err5
                ld      a,(GFX_G8V)
                ld      c,a
                ld      a,e
                cp      c
                jp      nc,gfx_err5         ; index outside its domain -> ERR 5
                ld      a,c
                cp      20
                ld      hl,RG0SAV           ; ..+7 = the register mirrors, +8 = STATFL,
                jr      nz,g8_fn_byte       ; which is exactly what VDP(8) returns
                ex      de,hl
                add     hl,hl               ; BASE: the word at BASETAB + 2n
                ld      de,BASETAB
                add     hl,de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                jr      g8_int_result
g8_fn_byte:
                add     hl,de
                ld      e,(hl)
                ld      d,0
g8_int_result:
                ld      a,2
                ld      (FACTYP),a          ; the result is an int16
                ret

; --- g8_open_paren: HL at "(<expr>)" -> DE = value, HL past the ')' --------
; Shared by the function forms above and the assignment forms below.
g8_open_paren:
                call    skip_spaces
                ld      a,(hl)
                cp      '('
                jp      nz,gfx_syntax
                inc     hl
                call    g8_num_operand      ; DE = n (ERR 13 on a string, ERR 6 > int16)
                call    skip_spaces
                ld      a,(hl)
                cp      ')'
                jp      nz,gfx_syntax
                inc     hl
                ret

; --- g8_num_operand: eval a NUMERIC operand, ERR 13 on a string -----------
; `VDP("A")=1` / `VDP(0)="A"` / `BASE(0)="A"` are all Type mismatch on the
; reference; gfx_eval_int16 alone would silently take the string's numeric
; residue. str_eval_one is the same detector ex_paint uses for its tile$ form
; (CF=1 = string operand, HL past it; CF=0 leaves HL for eval).
g8_num_operand:
                call    str_eval_one
                jp      c,gfx_typeerr
                jp      gfx_eval_int16      ; tail call: its ret serves ours

; --- ex_vdp_assign / ex_base_assign: the STATEMENT forms -------------------
; There is no statement token: a statement whose first token is VDP/BASE IS the
; assignment (spec §2), which is why these hang off interp.asm's dispatch rather
; than off ex_let. `LET VDP(0)=2` is ERR 2 on the reference -- and falls out
; here for free, since ex_letkw only accepts a variable name.
ex_vdp_assign:
                ld      a,13                ; GFX_OP = 13 -> tenant VDP register write
                jr      g8_assign
ex_base_assign:
                ld      a,14                ; GFX_OP = 14 -> tenant BASE write + reprogram
g8_assign:
                ld      (GFX_OP),a          ; parked in the selector cell itself rather
                                            ; than on the stack: the parse below can exit
                                            ; through raise_error, which unwinds SP
                inc     hl                  ; past the VDP / BASE token
                call    g8_open_paren       ; DE = n, HL past ')'
                ld      (GFX_G8N),de
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN
                jp      nz,gfx_syntax       ; `VDP(0)` alone / `VDP(0),1` -> ERR 2
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,g8_missing        ; `VDP(0)=` at end of line -> ERR 24
                cp      ':'
                jr      z,g8_missing
                call    g8_num_operand      ; DE = value (ERR 13 on a string)
                ld      (GFX_G8V),de
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,g8_run
                cp      ':'
                jp      nz,gfx_syntax       ; `VDP(0)=1,2` -> a TRAPPABLE ERR 2, not the
g8_run:                                     ; run-aborting stmt_error exec_stmt would give
                push    hl                  ; keep the cursor across the tenant call
                ld      a,(GFX_OP)
                call    spr_tenant          ; runs GFX_OP=A, raises the tenant's ERR code
                pop     hl
                jp      exec_stmt
g8_missing:
                ld      a,24                ; Missing operand (measured, spec §3)
                jp      raise_error
    ENDIF

