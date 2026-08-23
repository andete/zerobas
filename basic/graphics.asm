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
                call    parse_coord         ; BC = x, DE = y (int16, STEP resolved); HL past ')'
                ; --- D-LINERR: work area := the point, THEN the SCREEN-2 gate ---
                ; Both used to sit elsewhere: the gate opened the routine (so
                ; `PSET((Q$<5),21)` in SCREEN 0 answered ERR 5 where both
                ; references answer 13) and the work-area write was below the
                ; colour parse (so `PSET(20,21),0*(1/0)` left GRPAC on the seed
                ; where both references leave it on the point). One call now
                ; does both, in the measured order -- spec-basic-lineerr.md §2.
                call    gfx_point_gate      ; BC/DE/HL preserved
                ; --- optional ",c" colour override ---
                call    skip_spaces
                cp      ','
                jr      nz,gfx_plot_go      ; no ",c" -> keep the default colour
                inc     hl                  ; consume the ','
                push    bc                  ; save x across the colour eval (eval clobbers all)
                push    de                  ; save y
                call    gfx_eval_int16   ; DE = colour, ERR 6 if > int16
                ; 🔴 D-LINERR: a RANGE CHECK, not the `and $0F` mask that used to
                ; be here. `PSET(20,21),16` is Illegal function call on BOTH
                ; references (row k.pset16) -- the same 0..15 rule CIRCLE and
                ; PAINT already used, so this is one shared leaf and not a
                ; PSET-specific quirk.
                ; 🔴 THE MASK'S OWN CITATION NEVER RESOLVED. The line this
                ; replaces read `and $0F ; use the low nibble (0..15); see G2
                ; gate note` -- and there is no "G2 gate note", nor any doc in
                ; this tree that states a domain for the colour argument at all
                ; (spec-basic-graphics-g2.md §3.4 covers only the DEFAULT,
                ; FORCLR/BAKCLR). The mask was own design carrying a dangling
                ; pointer, and by its second reader the pointer had been
                ; restated as a measurement on a named machine. The domain is
                ; now stated where it belongs, spec-basic-graphics-g2.md §3.5,
                ; with the rows behind it -- spec-basic-lineerr.md §5.1.
                call    gfx_store_colour_checked   ; ERR 5 outside 0..15; GFX_C=value
                pop     de                  ; restore y
                pop     bc                  ; restore x
gfx_plot_go:
                ; --- range test decides plot vs silent no-op ---
                call    gfx_in_range        ; CF = 1 iff 0<=x<=255 and 0<=y<=191
                jp      nc,exec_stmt        ; off-screen -> no plot (work area already moved)
                ld      a,1                 ; GFX_OP = 1 -> tenant plot (PSET/PRESET)
                ld      (GFX_OP),a
                push    hl                  ; guard the token cursor -- CALSLT clobbers HL
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS   ; page-0 index 8 = $0058
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
                ; D-GIRDOM: marshal through POINT'S OWN cells, NOT GXPOS/GYPOS.
                ; This used to be `ld (GXPOS),bc / ld (GYPOS),de` -- and GXPOS/
                ; GYPOS is BASIC-visible. MEASURED: both references leave BOTH
                ; halves of the work area untouched by a POINT, on-screen
                ; (`w.pt.on`), through STEP (`w.pt.step`) and off-screen
                ; (`w.pt.off`); zerobas moved GXPOS on the first two. The
                ; comment two lines up was RIGHT about GRPAC and that is why
                ; `v.point0` stayed green over it for the whole life of G2 --
                ; the row read the half POINT does not touch. Byte-neutral swap
                ; (`ld a,c`+`ld (nn),a` = `ld (nn),bc`), 2 B of RAM.
                ld      a,c                 ; x, 0..255 (gfx_in_range passed)
                ld      (GFX_PTX),a
                ld      a,e                 ; y, 0..191
                ld      (GFX_PTY),a
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
                ; stage running ref = p1 (STEP chain, §3.3). 🔴 D-LINERR: this
                ; used to write GRPACX/GRPACY ONLY, and the row that caught it
                ; is `w.s0.tm` -- `LINE (11,12)-((Q$<5),21)`, whose GRPAC twin
                ; `m.s0.tm` was already GREEN. Both references stage p1 into
                ; GXPOS/GYPOS as well, so a reading that only looked at the
                ; last-referenced point could not see the difference. Using the
                ; shared leaf writes all four cells and is 5 bytes SHORTER than
                ; the two writes it replaces.
                call    gfx_work_area
                call    skip_spaces
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
                ; --- D-LINERR: work area := p2, THEN the SCREEN-2 gate ---
                ; This is the whole filed defect. The gate used to be the first
                ; thing ex_line_gfx did, so `LINE (0,0)-((Q$<5),1)` in SCREEN 0
                ; answered ERR 5 without evaluating a coordinate, where both
                ; references answer ERR 13. Here, EVERY fault the two endpoints
                ; can raise -- a type fault, a deferred numeric one, an int16
                ; overflow, a missing `-`, a missing `(` -- has already been
                ; reported, and the colour/box fields have not been touched.
                ; ⚠️ The tenant ALSO writes the work area from GFX_X2/GFX_Y2
                ; (sub/graphics.asm gfx_line_op) and that write is KEPT: the
                ; CIRCLE spokes call that op internally and rely on it, so this
                ; is a deliberate duplicate on the drawn path, not dead code.
                call    gfx_point_gate      ; BC/DE/HL preserved
                ; --- optional ",[c][,B|BF]" ---
                xor     a
                ld      (GFX_MODE),a        ; default: segment
                call    skip_spaces
                cp      ','
                jp      nz,elg_draw         ; no options
                inc     hl                  ; consume the 1st comma
                call    skip_spaces
                cp      ','                 ; ",," -> colour omitted, straight to box field
                jr      z,elg_box_comma
                ; 🔴 D-LINERR: a list that ENDS where the colour was required is
                ; `Missing operand` (ERR 24), not Syntax error -- `LINE (0,0)-
                ; (9,9),` and `LINE (0,0)-(9,9),:V=1` are both 24 on BOTH
                ; references (rows a.trailc / a.trailcolon). Same rule D-SCRERR
                ; measured at all four of ex_screen's such slots. The `:` arm is
                ; MEASURED here rather than copied from ex_screen's shape -- and
                ; it does NOT extend to the box slot one field along, which is
                ; ERR 2 for the same two shapes (a.boxc / a.boxcolon).
                or      a                   ; end of line -> Missing operand
                jp      z,loc_missing
                cp      COLON               ; next statement -> the same
                jp      z,loc_missing
                call    is_box_kw           ; single-comma box (",B"/",BF") ?
                jr      z,elg_box_read
                ; --- colour expression ---
                call    gfx_eval_int16   ; ERR 6 if > int16
                ; 🔴 D-LINERR: 0..15 RANGE CHECK, not the old `and $0F` mask --
                ; `LINE (0,0)-(9,9),16` is ERR 5 on both references (k.16 /
                ; k.b16), matching CIRCLE/PAINT and now PSET.
                call    gfx_store_colour_checked
                call    skip_spaces
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
; D-DUPSPAN: an ALIAS, not a second copy -- byte-identical to play.asm's
; pl_syntax, which is the family's canonical tail because its four callers
; are the only ones close enough to reach it with `jr`. The NAME and every
; call site survive; un-alias here for a distinct face and nothing moves.
elg_syntax      equ     pl_syntax   ; ERR 2 (bad LINE form)

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
                cp      '('
                jp      nz,pc_syntax
                inc     hl
                call    gfx_eval_int16   ; DE = x, ERR 6 if > int16 (HL guarded)
                push    de                  ; save x across the y eval
                call    skip_spaces
                cp      ','
                jp      nz,pc_syntax
                inc     hl
                call    gfx_eval_int16   ; DE = value; ERR 6 if > int16
                call    skip_spaces
                cp      ')'
                jp      nz,pc_syntax
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
; D-DUPSPAN: an ALIAS, not a second copy -- byte-identical to play.asm's
; pl_syntax, which is the family's canonical tail because its four callers
; are the only ones close enough to reach it with `jr`. The NAME and every
; call site survive; un-alias here for a distinct face and nothing moves.
; (the raise aborts with SP reset, so the pushed x is still discarded.)
pc_syntax       equ     pl_syntax   ; ERR 2 (bad coordinate form)

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
; D-DUPSPAN: an ALIAS, not a second copy -- the two instructions were
; byte-identical to interp.asm's gb_illegal, on gfx_absent's own precedent.
; The NAME and every call site survive; un-alias here to give this site a
; distinct face and nothing else moves.
gfx_err5        equ     gb_illegal  ; ERR 5 (PSET/PRESET in SCREEN 0/1)
; 🎯 gfx_absent IS NOW AN ALIAS, NOT A SECOND COPY (D-PAINTBORD carve, 5 B of
; main page 1 -- the bytes that fund the border-domain check below). The
; defensive "subrom_call reported the tenant missing" tail, which cannot fire on
; the merged build, raised ERR 5 from the SAME two instructions as gfx_err5, so
; the two were byte-identical and one had to go -- exactly the argument
; interp.asm makes for err_illegal_fn. The NAME survives because the two are
; different CLAIMS: if a later slice wants a distinct face for an absent tenant,
; un-alias it here and no call site moves.
gfx_absent      equ     gfx_err5
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to pl_typeerr,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
gfx_typeerr     equ     pl_typeerr

; --- gfx_point_gate / gfx_mode_gate / gfx_work_area -------------------------
; D-LINERR (docs/spec-basic-lineerr.md). THE ORDERING RULE, in one place:
;
;   a graphics statement moves the WORK AREA to the point its MANDATORY
;   arguments resolve to, and refuses a wrong SCREEN mode IMMEDIATELY AFTER
;   THAT -- after every fault the mandatory arguments can raise, and BEFORE the
;   first OPTIONAL argument is even looked at.
;
; Measured on the VG-8020 AND the CF-3300, at all five verbs that have a
; precheck, with the gate sited from BOTH sides (spec §2.1): in SCREEN 0
; `PSET((Q$<5),21)` is ERR 13 and `PSET(20,21),0*(1/0)` is ERR 5, so the gate
; lies strictly between the coordinate and the colour; and the second of those
; leaves GRPACX/GRPACY *and* GXPOS/GYPOS on (20,21), so the work-area write
; lies before the gate rather than after it. The same pair holds for LINE
; (`m.s0.tm` / `m.s0.col`), for CIRCLE across its TWO mandatory arguments
; (`v.circ0.rt` is ERR 13 for a bad radius, `v.circ0.c` ERR 5 for a bad colour)
; and for PAINT (`v.paint0.tm` / `v.paint0.c`).
;
; 🔴 THIS WAS FILED AS A LINE DEFECT AND IS NOT ONE. `TODO.md` had it as "LINE
; raises its own Illegal function call eagerly from inside its coordinate
; parse" -- but there is no ERR 5 in parse_coord, the refusal was `ex_line_gfx`'s
; own opening `cp 2`, and the identical opening `cp 2` at PSET/PRESET, CIRCLE
; and PAINT diverges identically. It is one rule at five verbs, which is why it
; is one routine and not five edits.
;
; THREE ENTRY POINTS BECAUSE CIRCLE'S TWO MANDATORY ARGUMENTS ARE RESOLVED AT
; TWO DIFFERENT REQUEST SITES, and they NEST, so the extra two cost 4 bytes
; between them: the common case wants both halves (gfx_point_gate), CIRCLE's
; centre wants the work area alone (gfx_work_area) and CIRCLE's radius the gate
; alone (gfx_mode_gate). ⚠️ The radius site gates on EVERY int request, not just
; the first, and that is deliberate: gating twice is the same as gating once
; (the second test can only pass), so it buys the rule without a "which
; argument am I on" flag.
;
; in:  BC = x, DE = y (the resolved point). BC, DE and HL are all preserved --
; every caller still holds the cursor in HL, and PSET's caller still needs the
; point in BC/DE for its own range test. Clobbers A only. Own-design.
gfx_point_gate:
                call    gfx_work_area
                ; fall through into the gate
gfx_mode_gate:
                ld      a,(SCRMOD)
                cp      3                   ; D-SCREEN3: MULTICOLOUR, whose pixel ops
                ret     z                   ; the tenant now implements
                ; D-PAINTMC RETIRED THE SECOND ENTRY POINT. PAINT used to jump PAST
                ; the `cp 3` above (label gfx_mode_gate_s2, entered with A already
                ; loaded) because its flood was the one pixel op multicolour broke.
                ; The tenant's pitch-4 walk fixed that, so all five verbs share ONE
                ; gate again and ex_paint's own `ld a,(SCRMOD)` went with it.
                cp      2                   ; SCREEN 2 (arc D4)
                ret     z
                jp      gfx_err5            ; SCREEN 0/1 -> Illegal function call
gfx_work_area:
                ld      (GXPOS),bc          ; pending pixel target X
                ld      (GRPACX),bc         ; last-referenced point X
                ld      (GYPOS),de
                ld      (GRPACY),de
                ret

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
; once the space question is resolved.
; ⚠️ THAT NOTE IS STALE AND IS INVERTED, NOT DELETED (D-PAINTBORD, 2026-08-22).
; The broader fold is NOT reverted -- PSET, LINE, CIRCLE and parse_coord all call
; gfx_eval_int16 today, at twelve sites in this file. The "resident build is
; currently blocked" it describes was the OLD two-build tree's $8000 hard-stop;
; the merged repack IS the build now. The same staleness sat on
; gfx_store_colour_checked below, which named a `circ_c` this tree does not
; contain -- both notes outlived the tree they describe, and a reader who
; believed either would go looking for a saving that has already been taken.
; Clobbers A (+ whatever eval/get_int16_checked already clobber).
gfx_eval_int16:
                call    eval
                jp      get_int16_checked   ; tail call: ret serves both

; --- gfx_chk_dom: the shared "is this int16 inside its domain?" leaf ---------
; D-PAINTBORD (docs/spec-basic-paintbord.md). IN: DE = an already-eval'd +
; get_int16_checked'd value; A = the HIGH-NIBBLE MASK that names the domain --
;
;     A = $F0  ->  0..15    (a colour nibble)
;     A = $00  ->  0..255   (a byte)
;
; OUT: A = E, the checked value. ERR 5 (Illegal function call) if outside.
;
; 🎯 THE MASK IS WHY THIS IS ONE LEAF AND NOT TWO. Every domain in this file is
; "the value fits in k low bits", so `mask AND e OR d` is zero exactly when it
; does -- `or d` folds the >255/negative half in for free, because a negative or
; >255 int16 is precisely one with a non-zero high byte. One routine therefore
; serves the colour rule (0..15, always) and PAINT's border rule (0..15 in
; MULTICOLOUR, 0..255 in SCREEN 2), which differ ONLY in the mask.
; ⚠️ It does NOT set flags for the caller: A is the value on return, so a caller
; that wants to compare it must do so itself (g8_fn below does).
gfx_chk_dom:
                and     e
                or      d                   ; non-zero -> outside the domain
                jp      nz,gfx_err5
                ld      a,e
                ret

; --- gfx_store_colour_checked: "C" RANGE-CHECK+STORE tail -------------------
; (spec-basic-graphics-g5.md §8 D4 DRY lever). IN: DE = an already-eval'd +
; get_int16_checked'd colour value. Range-checks 0..15 (ERR 5 if outside --
; the stricter CIRCLE/PAINT rule, unlike PSET's silent `and $0F` mask) and
; stores to GFX_C. Used by ex_pset / ex_line / ex_paint's colour parses.
; ⚠️ THE PARAGRAPH THAT USED TO STAND HERE WAS FALSE AND IS INVERTED, NOT
; DELETED. It said the same DRY had been "ALSO factored into ex_circle/circ_c
; ... reverted ... unverifiable while the resident build is blocked". There is
; no `circ_c` in this tree and CIRCLE does not range-check its colour in the
; resident at all -- the tenant does, and reports through GFX_RES. The same
; staleness sits on gfx_eval_int16 above: that comment says the broader fold was
; REVERTED at PSET/LINE/CIRCLE/parse_coord, and all of those sites call
; gfx_eval_int16 today. Both notes outlived the two-build tree whose $8000
; hard-stop they describe. Clobbers A.
gfx_store_colour_checked:
                ld      a,$F0               ; the 0..15 domain
                call    gfx_chk_dom         ; A = E; ERR 5 if outside
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
                ; D-LINERR: the SCREEN-2 gate is NOT here any more. CIRCLE has
                ; TWO mandatory arguments and the gate belongs after the second
                ; of them, so it moved into cp_req_int below -- measured:
                ; `CIRCLE(20,21),(Q$<5)` in SCREEN 0 is ERR 13 (the radius fault
                ; wins) while `CIRCLE(20,21),5,0*(1/0)` is ERR 5 (the colour
                ; fault does not). Rows v.circ0.rt / v.circ0.c.
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
                call    gfx_work_area       ; D-LINERR: work area := the CENTRE, before
                                            ; the radius is even requested (v.circ0.rt
                                            ; reads ' 13 , 20 , 21 ' on both references)
                ld      (GFX_DPTR),hl
                jr      cp_resume
cp_req_int:
                call    gfx_eval_int16      ; DE=value, HL advanced (ERR 6 if > int16)
                call    gfx_mode_gate       ; D-LINERR: the gate, AFTER the value. Runs on
                                            ; every int request rather than only the
                                            ; radius: gating twice is gating once, and
                                            ; that is cheaper than a "which argument" flag
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
; 🔴 THIS HEADER USED TO SAY the work-area write is "deferred to AFTER every
; field is parsed (spec §6), UNLIKE PSET/LINE/CIRCLE". D-LINERR moved the write
; to the top of the routine and D-PAINTSEED moved the seed test below it, so
; the header outlived both edits by describing the code it replaced -- with the
; body three lines down already saying the opposite. PAINT is NOT unlike its
; siblings: it is `gfx_point_gate` at the same site as the other four verbs,
; and the ONLY thing that distinguishes it is the extra off-screen-seed reject
; underneath (spec §3), which no sibling has.
; =============================================================================
ex_paint:
                inc     hl                  ; past the PAINT token
                call    parse_coord         ; BC = seed x, DE = seed y (STEP resolved)
                ; --- D-LINERR: work area := the seed, THEN the SCREEN-2 gate ---
                ; The gate used to open the routine; the work-area write used to
                ; sit at ep_draw, AFTER every field. Both are refuted by
                ; measurement: `PAINT((Q$<5),21)` in SCREEN 0 is ERR 13 on both
                ; references (so the gate is not first) and `PAINT(20,21),
                ; 0*(1/0)` leaves GRPAC/GXPOS on (20,21) (so the write is not
                ; last) -- rows v.paint0.tm / v.paint2.c. ⚠️ THIS SUPERSEDES
                ; spec-basic-graphics-g5.md §6's "deferred to AFTER every field
                ; is parsed", which was a design choice never measured against
                ; the reference.
                ; ⚠️ THE PARAGRAPH THAT USED TO STAND HERE IS NOW FALSE, AND IT IS
                ; INVERTED RATHER THAN DELETED. D-SCREEN3 excluded PAINT from
                ; MULTICOLOUR and this site carried the reason: adjacent LOGICAL
                ; pixels share one 4x4 cell, so with the default border B=C the first
                ; painted cell instantly read as a border to its own neighbours and
                ; the fill stopped dead after the seed. That diagnosis was RIGHT; what
                ; it got wrong was the remedy, which it filed as "a flood engine that
                ; does not re-test painted cells". D-PAINTMC measured the references
                ; instead and found the opposite: they DO stop at an already-C cell
                ; (rows ac2.stop / ac3.stop, both references, in SCREEN 2 AND in
                ; MULTICOLOUR), so the engine's own-design `== C` stop is FAITHFUL and
                ; the only thing that had to change was the walk's PITCH -- 4 in MC,
                ; so a step always lands on the NEXT cell. sub/graphics.asm gfx_pstep.
                ; PAINT is therefore back on the SHARED gate with its four siblings,
                ; which is 3 bytes of main page 1 recovered.
                call    gfx_point_gate      ; work area + mode gate, BC/DE/HL preserved
                ; --- D-PAINTSEED: the OFF-SCREEN-SEED test is BELOW the work
                ; area, not above it. D-LINERR left this ordering where G5 had
                ; put it and filed it unmeasured, because BOTH conditions raise
                ; ERR 5 and the code cannot tell them apart. The WORK AREA can,
                ; and it says the seed is written FIRST: `PAINT(300,100)` leaves
                ; GRPACX/GRPACY *and* GXPOS/GYPOS on the RAW UNCLIPPED (300,100)
                ; on both references before raising ERR 5 -- in SCREEN 2 as well
                ; as SCREEN 0, so it is not the mode gate doing it. Measured
                ; across the whole seed domain (x>255, 192<=y<=255, negatives
                ; read back as 65535, and both off-by-one edges against an
                ; ACCEPTED (255,191)) and through STEP, which writes the
                ; RESOLVED point: rows p.* / w.paint*.off, knives K-PS1..K-PS3.
                ; ⚠️ The seed test versus the MODE gate stays UNORDERED and no
                ; row here claims otherwise: when a seed is off-screen AND the
                ; mode is wrong, both raise ERR 5 with the same work area
                ; whichever runs first. What is measured is the seed test
                ; against the work-area WRITE, and that puts it here.
                call    gfx_in_range        ; CF = 1 iff 0<=x<=255 and 0<=y<=191
                jp      nc,gfx_err5         ; off-screen seed -> ERR 5 (spec §3 --
                                            ; NOT a silent clip like PSET/LINE)
                ; --- default colour = FORCLR ---
                ld      a,(FORCLR)
                and     $0F
                ld      (GFX_C),a
                ; --- optional ",[C][,[B]]" ---
                call    skip_spaces
                cp      ','
                jr      nz,ep_default_b     ; no fields at all -> C=FORCLR, B=C
                inc     hl                  ; consume the comma
                call    skip_spaces
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
                cp      ','
                jr      nz,ep_default_b     ; no ",B" -> B = C
                inc     hl                  ; consume the comma introducing B
                jr      ep_parse_b
ep_c_empty:
                inc     hl                  ; consume the shared comma
ep_parse_b:
                call    skip_spaces
                or      a
                jr      z,ep_default_b      ; empty B field -> B = C
                cp      COLON
                jr      z,ep_default_b
                cp      ','
                jp      z,ep_syntax         ; a 3rd comma here => a 4th argument -> ERR 2
                ; --- given B: eval, then RANGE-CHECK against the MODE'S domain ---
                ; 🔴 D-PAINTBORD (docs/spec-basic-paintbord.md). ⚠️ THE TWO LINES
                ; THAT USED TO STAND HERE ARE FALSE AND ARE INVERTED, NOT DELETED:
                ; they said the border is "eval only, NOT range-checked (spec
                ; §3/§5 -- a border of 16+ is legal, just a comparison value no
                ; pixel hits)". That is right about what a border of 16 DOES in
                ; SCREEN 2 and wrong about the DOMAIN, and it was never right in
                ; MULTICOLOUR at all:
                ;
                ;     B is 0..255 in SCREEN 2 and 0..15 in MULTICOLOUR;
                ;     outside that, ERR 5 (Illegal function call).
                ;
                ; Measured on the VG-8020 AND the CF-3300, which agree on every
                ; row (bd2.* / bd3.*, scratchpad/paintmc_probe.py). ⚠️ Before
                ; D-PAINTMC the SCREEN-3 half AGREED BY ACCIDENT -- every
                ; multicolour PAINT was ERR 5, so `PAINT(10,10),9,16` was right
                ; for the wrong reason -- and the SCREEN-2 half has been wrong
                ; since G5, invisibly, because the one shipped row on this
                ; argument uses B=16, which is INSIDE the SCREEN-2 domain.
                ; ⚠️ THE CHECK READS THE FULL int16, NOT THE STORED BYTE. 256 is
                ; $0100, whose low byte is $00 and would sail through a byte-only
                ; test; `PAINT(10,10),9,256` is ERR 5 on both references in both
                ; modes. That half is what gfx_chk_dom's `or d` costs nothing to
                ; get right.
                ; 🎯 AND THE PLACEMENT IS ITSELF A MEASUREMENT. D-LINERR's finding
                ; is that WHERE a check sits is a claim, so the domain was raced
                ; against the grammar with a 4th argument behind it:
                ;
                ;   PAINT(10,10),9,16,   SCREEN 3  -> ERR 5 both refs  (od3.b16c)
                ;   PAINT(10,10),9,15,   SCREEN 3  -> ERR 2 both refs  (od3.b15c)
                ;   PAINT(10,10),9,256,  SCREEN 2  -> ERR 5 both refs  (od2.b256c)
                ;   PAINT(10,10),9,16,   SCREEN 2  -> ERR 2 both refs  (od2.b16c)
                ;
                ; The in-domain twins are what make the out-of-domain ones mean
                ; anything: they read ERR 2 on the SAME programs, so the trailing
                ; comma really is a 4th argument and the parse really does reach
                ; the grammar. The domain beats it -- which is why this sits ABOVE
                ; the ep_syntax test below, and not under it.
                call    gfx_eval_int16      ; DE = value (silent int16); ERR 6 if > int16
                ld      a,(SCRMOD)
                cp      3                   ; MULTICOLOUR?
                ld      a,$F0               ; ...then B is a nibble, 0..15
                jr      z,ep_b_dom          ; (`ld a,n` does not touch the flags)
                xor     a                   ; SCREEN 2: B is a whole byte, 0..255
ep_b_dom:
                call    gfx_chk_dom         ; A = E; ERR 5 outside the mode's domain
                ld      (GFX_B),a           ; low byte only (spec §6: GFX_B is 1 B)
                call    skip_spaces
                cp      ','
                jp      z,ep_syntax         ; a 4th argument -> ERR 2
                jr      ep_draw
ep_default_b:
                ld      a,(GFX_C)
                ld      (GFX_B),a
ep_draw:
                ; D-LINERR: the work area moved UP to gfx_point_gate, above the
                ; field parses (measured -- see the entry comment), which is
                ; also what retires the push/pop pair that used to guard the
                ; seed across them: nothing below here needs BC/DE any more.
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
; D-DUPSPAN: an ALIAS, not a second copy -- byte-identical to play.asm's
; pl_syntax, which is the family's canonical tail because its four callers
; are the only ones close enough to reach it with `jr`. The NAME and every
; call site survive; un-alias here for a distinct face and nothing moves.
ep_syntax       equ     pl_syntax   ; ERR 2 (a 4th PAINT argument)

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
                ; ⚠️ THE MODE GATE IS FIRST HERE, AND THAT IS MEASURED, NOT
                ; INHERITED. D-LINERR moved the identical three instructions
                ; DOWN at PSET/PRESET/LINE/CIRCLE/PAINT, because at those five a
                ; mandatory-argument fault outranks the mode. At DRAW it does
                ; NOT: `DRAW 5` in SCREEN 0 is ERR 5 on both references while
                ; the same statement in SCREEN 2 is ERR 13 (rows d.tm0/d.tm2),
                ; so the mode is refused BEFORE the string expression is
                ; evaluated. D-DRAWERR swept the six A-vs-B rows to say so;
                ; `v.draw0` -- the one row D-LINERR excluded DRAW on -- uses a
                ; string LITERAL and is blind to the question.
                ; docs/spec-basic-lineerr.md §11.
                call    skip_spaces         ; 🔴 D-DRAWERR: WITHOUT THIS, `DRAW A$`
                                            ; IS ERR 13. str_eval was handed HL on
                                            ; the space after the token, is_letter
                                            ; failed on it, and str_eval_no's CF=0
                                            ; became Type mismatch below -- so DRAW
                                            ; took a string LITERAL and nothing
                                            ; else, and the argument was never
                                            ; evaluated at all. ex_let_str
                                            ; (interp.asm) and spr_assign below
                                            ; both skip here; ex_draw was the only
                                            ; one of the three that did not, which
                                            ; is exactly why `SPRITE$(0)=STR$(...)`
                                            ; (row n.sprdz) never had the defect.
                                            ; Rows n.drawvar / n.drawsp / d.avar2,
                                            ; and it is what made d.dz2/d.ov2
                                            ; answer 13 where the references
                                            ; answer the pending fault (11 / 6).
                call    gfx_mode_gate       ; D-SCREEN3: was 6 B of inline
                                            ; `ld a,(SCRMOD) / cp 2 / jp nz,gfx_err5`.
                                            ; The shared gate is the SAME test and 3 B
                                            ; smaller, and it still runs BEFORE the
                                            ; argument, which is D-DRAWERR's measured
                                            ; ordering. The 3 B saved is what pays for
                                            ; PAINT's narrow gate below.
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
; --- gfx_syntax: a TRAPPABLE Syntax error (ERR 2) --------------------------
; NOT `jp stmt_error`: that prints and aborts the RUN, so an `ON ERROR GOTO`
; program never sees it -- the reference raises a trappable ERR 2 for every
; malformed sprite statement (Phase O caught exactly this on the first run).
; D-DUPSPAN: an ALIAS, not a second copy -- byte-identical to play.asm's
; pl_syntax, which is the family's canonical tail because its four callers
; are the only ones close enough to reach it with `jr`. The NAME and every
; call site survive; un-alias here for a distinct face and nothing moves.
gfx_syntax      equ     pl_syntax   ; ERR 2 (malformed SPRITE statement)
; 🔴 AND IT LIVES OUTSIDE `IF G7_RESIDENT`, WHICH IS NOT COSMETIC. It is used
; from the G8 block too (basic/interp.asm's ex_letkw refuses `LET VDP(0)=` /
; `LET BASE(0)=` with it), so defining it inside G7's block made `G7_RESIDENT
; equ 0` fail to assemble with `Symbol 'gfx_syntax' is undefined  on line 1522
; of file basic/interp.asm` -- a diagnostic naming a different file and a
; different feature. `make switch-build-check` is what found it; an `equ` emits
; no bytes, so hoisting it costs the shipping build nothing.

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

    ENDIF   ; G7_RESIDENT -- reopened after spr_tenant below

; --- spr_tenant: run one sprite tenant op (A = GFX_OP) and raise its error --
; The sprite ops carry no colour, so unlike the drawing statements this leaves
; GFX_C alone (the tenant's ATRBYT stamp deliberately skips ops 7/8/9 -- sprites
; measurably do not touch the shared graphics attribute). Clobbers A, IX.
; 🔴 AND THE G8 BLOCK CALLS IT: `VDP(n)=v` / `BASE(n)=v` run through the SAME
; page-0 tenant, so g8_run's `call spr_tenant` is a G8 site for a G7-named
; routine. Gating it under G7 alone made `G7_RESIDENT equ 0` fail with `Symbol
; 'spr_tenant' is undefined  on line 1350 of file basic/graphics.asm`, which is
; VDP/BASE code. Found by `make switch-build-check`. Nothing falls THROUGH into
; this label (spr_parse_index above ends in `ret`) and nothing falls out of it,
; so bracketing it emits the same instructions in the same order and the
; shipping ROM does not move a byte.
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

    IF G7_RESIDENT

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
                ; D-SCRERR: the slot NUMBER is maintained by ex_screen at each
                ; comma (screen.asm), because an OMITTED argument never reaches
                ; here to be counted. Slot 1 is the sprite size; 2+ are ignored.
                ld      a,(GFX_SARGN)
                dec     a
                ret     nz
                ; D-SCRERR (docs/spec-basic-screenerr.md §2.2): the sprite size has
                ; its OWN domain and it is 0..3, not "the low two bits of whatever
                ; you passed". `SCREEN 1,99` and `SCREEN 1,-1` are Illegal function
                ; call on both references where the `and $03` silently accepted 99
                ; as size 3; `SCREEN 1,70000` is Overflow, which the caller's
                ; eval_byte_checked now raises before we are reached. +3 B.
                ; ⚠️ ONLY `SCREEN 1,99` TESTS THIS TEST. Knife K-SE4 cut it and
                ; `SCREEN 1,-1` did not move -- a negative sprite size never
                ; reaches here at all, because the caller's byte stage rejects a
                ; set high byte first. The two rows look like one class and are
                ; caught by two different stages (spec-basic-screenerr.md §8).
                ld      a,e
                cp      4
                jp      nc,gb_illegal       ; ERR 5 -- sizes are 0..3
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
                cp      ','
                jp      nz,gfx_syntax       ; `PUT SPRITE 0` -> ERR 2 (measured)
                inc     hl
                call    skip_spaces
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
                cp      ','
                jr      nz,pspr_go
pspr_optional:
                inc     hl                  ; past the ',' before the colour
                call    skip_spaces
                cp      ','
                jr      z,pspr_pattern      ; colour omitted -> keep the entry's colour
                call    gfx_eval_int16      ; DE = colour (domain checked by the tenant)
                ld      (GFX_SC),de
                ld      a,(GFX_SFLAGS)
                or      $02                 ; bit 1 = colour given
                ld      (GFX_SFLAGS),a
                call    skip_spaces
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
                ; D-PAINTBORD: the "the index must be a byte" half is
                ; gfx_chk_dom with an EMPTY mask -- `and 0 / or d` is exactly the
                ; `ld a,d / or a` this replaces, and the value comes back in A, so
                ; the C stash goes with it. The LIMIT then stays addressed rather
                ; than copied (GFX_G8V is read twice: once as the ceiling, once to
                ; tell BASE from VDP). 3 B of main page 1, part of what funds the
                ; border domain above.
                xor     a                   ; the 0..255 domain: only D must be 0
                call    gfx_chk_dom         ; A = E; ERR 5 if the index is not a byte
                ld      hl,GFX_G8V
                cp      (hl)
                jp      nc,gfx_err5         ; index outside its domain -> ERR 5
                ld      a,(hl)
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
; D-DUPSPAN2: entered by FALLTHROUGH from the span above, so this cannot
; become an `equ` -- a `jp` has to stay in its place.  Byte-identical to
; evsgn_settype; 6 B -> 3 B.  tools/dupspan_indep.py calls this SAFE-JP.
g8_int_result:
                jp      evsgn_settype

    ENDIF   ; G8_RESIDENT -- reopened after g8_num_operand below

; --- g8_open_paren: HL at "(<expr>)" -> DE = value, HL past the ')' --------
; Shared by the function forms above and the assignment forms below.
; 🔴 AND BY THE G7 BLOCK: spr_parse_index calls it, because `SPRITE$(n)` and
; `VDP(n)` are the same grammar. So these two routines are assembled whenever
; EITHER feature is built, not only under G8 -- gating them with G8 alone made
; `G8_RESIDENT equ 0` fail with `Symbol 'g8_open_paren' is undefined  on line
; 1063 of file basic/graphics.asm`, which is sprite code. Found by
; `make switch-build-check`; in the SHIPPING build both conditions are true, so
; the same instructions are emitted in the same order and not one byte moves.
g8_open_paren:
                call    skip_spaces
                cp      '('
                jp      nz,gfx_syntax
                inc     hl
                call    g8_num_operand      ; DE = n (ERR 13 on a string, ERR 6 > int16)
                call    skip_spaces
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

    IF G8_RESIDENT

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
                cp      EQ_TOKEN
                jp      nz,gfx_syntax       ; `VDP(0)` alone / `VDP(0),1` -> ERR 2
                inc     hl
                call    skip_spaces
                or      a
                jr      z,g8_missing        ; `VDP(0)=` at end of line -> ERR 24
                cp      ':'
                jr      z,g8_missing
                call    g8_num_operand      ; DE = value (ERR 13 on a string)
                ld      (GFX_G8V),de
                call    skip_spaces
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

