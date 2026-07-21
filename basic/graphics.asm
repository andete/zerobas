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
    ENDIF
