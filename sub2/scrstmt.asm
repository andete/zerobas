; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; scrstmt.asm -- zerobas-sub2 PAGE 0: the screen-setup STATEMENTS SCREEN, COLOR,
; WIDTH and KEY (D-P0CB slice D, docs/spec-sub2-p0cb.md §5). Moved out of main
; on 2026-10-24: ex_screen / ex_color / ex_width / ex_key from main page 1
; (basic/screen.asm), SCREEN's sprite-size arms (spr_mode_save, spr_mode_restore,
; spr_extra_arg, sea_click) from main page 1 (basic/graphics.asm), and COLOR's
; three helpers (clr_eval, clr_prep, clr_commit) from main's LOW region
; (basic/main.asm). KEY(n) ON|OFF|STOP -- the trap form -- was already slice B's
; (sub2/trapstmt.asm tt_key); KEY's peek for `(` now jumps there directly.
;
; WHAT STAYS IN MAIN, and is reached through p0cb:
;   key_repaint      shared with CLS (cls_keyline) and the prompt's txt_mode
;                    (basic/repl.asm); SCREEN and WIDTH call it.
;   key_op           key_repaint's tail given a name (A = the KEYOP_* op): the
;                    keystr tenant is reached through an INLINE-byte call
;                    (sc_inl0), which a p0cb'd caller cannot hand over -- IX is
;                    p0cb's target. KEY ON / OFF paint and blank through it.
;   spr_tenant       shared with the sprite statements (basic/graphics.asm).
;   CHGMOD / CHGCLR / ERAFNK / DSPFNK   the BIOS, by its fixed jump-table address.
;   ex_cls           CLS is not part of this slice.
; and as a CONTINUATION (returned in DE, never p0cb'd):
;   key_drain        KEY LIST / KEY n,"str": the keystr tenant's render drained
;                    through detok_emit's windowed print loop. It runs in main,
;                    OFF this tenant's CALSLT frame (the D-BLOADSTK rule: nothing
;                    long runs nested under this ROM's frame), with KEYARG set
;                    here and HL = the cursor.
;
; Entered through trap_tenant (sub2/trapstmt.asm) -> file_tenant
; (sub2/filestmt.asm) -> ls_tenant (sub2/loadsave.asm), which forwards every
; token but RUN here. Main's four entry labels share ex_open's ONE byte, `ld c,a`
; in front of ex_sub2 (basic/program.asm): exec_stmt hands a handler A = its
; token (tests/test_stmt_dispatch.py asserts it).
;   in   HL = the cursor ON the statement token (exec_stmt's contract)
;        A = C = the token
;   out  DE = the main address to continue at, HL = what it expects:
;          exec_stmt    HL = the cursor (main's `jp exec_stmt` / `jp pop_exec`)
;          key_drain    HL = the cursor, KEYARG = the op
; ex_sub2 then does `push de / ret` with the stack exactly as the statement was
; entered. No continuation is ever reached through p0cb.
;
; Every other main routine is reached through p0cb (sub2/p0cb.asm) with its `p0_`
; alias from basic-resident-abi.inc; `rst $10` is this ROM's RST 10h (main's
; CHRGTR). A raise reached through p0cb never returns -- raise_error resets SP and
; runs main's error path with main's page 0 mapped -- exactly as the `jp` it
; replaces never returned; a frame this code pushed is discarded by the same
; unwind. The shared tails fs_illegal (gb_illegal, ERR 5), fs_exec and
; fs_pop_exec are sub2/filestmt.asm's; tt_syntax (pl_syntax, a trappable ERR 2)
; is sub2/trapstmt.asm's.
; The code is otherwise main's, statement for statement, and each arm keeps the
; original's order of checks and of side effects (CHGMOD before the trailing
; SCREEN arguments are evaluated; COLOR's shadow published only after every way
; the statement can fail), so the errors and their order are the ones the screen
; gates already pin. The history behind each check is in git (basic/screen.asm,
; basic/graphics.asm and basic/main.asm before D-P0CB slice D); what is kept here
; is the measured rule each one encodes.
;
; 📏 STACK: this tenant runs 14 B below the statement's SP -- ex_sub2's `call
; subrom2_call` (2), sr_slot's `push iy` (2) and C-BIOS's CALSLT frame (10: its
; call, the saved slot pair, calslt_restore, the old $A8, clprim's call) -- and a
; p0cb adds 6 (its call, the old $A8, clprim's call). So CHGMOD / CHGCLR / ERAFNK
; / DSPFNK, entered with the cursor parked, run 22 B below the statement's SP where
; main's ran 4 B below it: 18 B deeper, for the length of one BIOS call. Nothing
; long runs here: KEY LIST's print loop is key_drain's, in main, off this frame.

; --- the dispatch -------------------------------------------------------------
scr_tenant:                                 ; A = C = the token (ls_tenant's tail)
                cp      SCREEN_TOKEN
                jp      z,scr_screen
                cp      COLOR_TOKEN
                jp      z,scr_color
                cp      WIDTH_TOKEN
                jp      z,scr_width
                ; FALL THROUGH: KEY_TOKEN is the only other token main sends here

; ===========================================================================
; KEY OFF | KEY ON | KEY LIST | KEY n,"text"   (main's ex_key)
; ===========================================================================
; KEY(n) ON|OFF|STOP is the T3 trap form: slice B's arm (sub2/trapstmt.asm).
scr_key:
                ; D-BAREFORM: a BARE `KEY` (or `KEY:`) is `Missing operand`, ERR 24
                ; on BOTH references. stmt_bare_end does the `inc hl` past the KEY
                ; token itself, then skips spaces: Z iff the statement ends.
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; past KEY; Z iff it ends; A = the byte
                jp      z,scr_missing
    IF TRAPS_T3
                cp      '('                 ; KEY(n) ON|OFF|STOP -- tested AHEAD of
                jp      z,tt_key            ; ON/OFF (oracle case K10); HL on `(`, the
                                            ; stack as trap_tenant hands its arms
    ENDIF
                cp      OFF_TOKEN
                jr      z,sck_off
                cp      ON_TOKEN
                jr      z,sck_on
                ; D-KEYSTR: KEY LIST and KEY n,"str". The body is the sub-ROM's
                ; SUBROM_IDX_KEYSTR tenant; the parse is here: LIST, or n (1..10,
                ; else ERR 5 -- measured) `,` string, staged into STRSCR by
                ; fname_expr ([len][bytes], the contract NAME and OPEN use).
                cp      LIST_TOKEN
                jr      nz,sck_store
                inc     hl                  ; past LIST
                ld      a,255               ; KEY LIST
                jr      sck_drain
sck_store:
                ld      ix,p0_eval_byte_arg
                call    p0cb                ; A = n, 0..255 (ERR 6 / ERR 5 outside)
                or      a
                jp      z,fs_illegal        ; KEY 0,   -> ERR 5 (measured)
                cp      11
                jp      nc,fs_illegal       ; KEY 11,  -> ERR 5 (measured)
                push    af                  ; [n] across the string's evaluation
                ld      ix,p0_req_comma
                call    p0cb                ; KEY n without `,`: ERR 2; CONSUMES it
                ld      ix,p0_fname_expr
                call    p0cb                ; STRSCR+1 := the bytes, `"`-terminated;
                                            ; FN_RESUME set. It does NOT write the
                                            ; length byte (parse_disk_fcb stops on
                                            ; the quote), so stage the TRUE length
                ld      hl,(STRPTR)         ; the descriptor is [len][ptr], in RAM or
                ld      a,(hl)              ; main page 1 (STR_EMPTY) -- both mapped
                ld      (STRSCR),a          ; here (a CHR$(34) inside stays exact)
                ld      hl,(FN_RESUME)
                pop     af                  ; A = n
sck_drain:                                  ; A = the op, HL = the cursor
                ld      (KEYARG),a
                ld      de,p0_key_drain     ; a CONTINUATION: the tenant's render is
                ret                         ; drained by main, off this CALSLT

; KEY OFF / KEY ON (D-FNKLINE): keep the BIOS call (harmless here, correct on a
; BIOS that paints), set CNSDFG -- the documented flag C-BIOS does not maintain
; -- and have the keystr tenant draw or erase row 23 (C-BIOS's DSPFNK paints
; nothing, D-DSPFNK). CRTCNT is WRITTEN ABSOLUTELY, not adjusted (D-SCROLLBOUND:
; WIDTH rewrites it underneath, so an inc/dec gated on CNSDFG is not idempotent).
sck_off:
                inc     hl                  ; past OFF
                push    hl
                ld      ix,ERAFNK
                call    p0cb
                ld      a,CON_ROWS
                ld      (CRTCNT),a          ; the console gets all 24 rows
                xor     a                   ; the line is hidden
                jr      sck_disp
sck_on:
                inc     hl                  ; past ON
                push    hl
                ld      ix,DSPFNK
                call    p0cb
                ld      a,CON_ROWS_KEYON
                ld      (CRTCNT),a          ; reserve the bottom row
                ld      a,$FF               ; the reference's own value, measured
sck_disp:
                ld      (CNSDFG),a
                or      a
                ld      a,KEYOP_FNKBLANK
                jr      z,sck_op
                ld      a,KEYOP_FNKPAINT
sck_op:
                ld      ix,p0_key_op
                call    p0cb                ; KEYARG := A; the keystr tenant (no drain:
                                            ; these ops leave DETOKBUF a lone NUL)
                jp      fs_pop_exec         ; main's `jp pop_exec`

; --- the shared tail: Missing operand (ERR 24) ---------------------------------
scr_missing:                                ; loc_missing (= g8_missing): ERR 24
                ld      ix,p0_loc_missing
                jp      p0cb                ; raises; never returns

; ===========================================================================
; SCREEN <mode>[,<sprite>][,<click>][,<baud>][,<printer>]   (main's ex_screen)
; ===========================================================================
scr_screen:
    IF G7_RESIDENT
                xor     a                   ; G7: the FIRST trailing argument is the
                ld      (GFX_SARGN),a       ; sprite size -- count the slots from 0
    ENDIF
                inc     hl                  ; past the SCREEN token
                ld      ix,p0_req_operand
                call    p0cb                ; bare `SCREEN` / `SCREEN :` -> ERR 24 (an
                                            ; argument list that ends where a value
                                            ; was required, D-SCRERR spec §2.1)
                cp      ','                 ; "SCREEN ,x" -> mode omitted
                jr      z,scs_extra
                ; D-SCRERR: the mode is a CHECKED BYTE, checked BEFORE CHGMOD: the
                ; deferred expression error first (`SCREEN 0*(1/0)` never applies
                ; the mode on either reference), then ERR 6 past int16, then ERR 5
                ; outside 0..255; it TRUNCATES (`SCREEN 1.6` -> 1). Why the checked
                ; leaf and not eval_byte_arg: spec-basic-screenerr.md §8.
                ld      ix,p0_eval_byte_checked
                call    p0cb                ; A = E = the mode, 0..255, or aborts
                cp      4
                jp      nc,fs_illegal       ; an MSX1 has modes 0..3 -> ERR 5 (`4` is
                                            ; a valid BYTE: its own test)
                push    hl                  ; A = mode -> switch the VDP mode
    IF G7_RESIDENT
                push    af
                call    scs_mode_save       ; G7: keep the sprite size + the attribute x
                pop     af                  ; bytes across CHGMOD (spec G7 §5)
                ld      ix,CHGMOD
                call    p0cb
                call    scs_mode_restore
    ELSE
                ld      ix,CHGMOD
                call    p0cb
    ENDIF
                ld      ix,p0_key_repaint
                call    p0cb                ; D-KEYCLS: a text mode gets its key line
                pop     hl
scs_extra:                                  ; the trailing arguments
                ld      ix,p0_skip_comma
                call    p0cb
                jp      nz,fs_exec          ; no comma -> done (the ONLY legal way
                                            ; out of this loop)
                inc     hl                  ; past the comma
    IF G7_RESIDENT
                ; D-SCRERR: COUNT THE SLOT AT THE COMMA, NOT AT THE VALUE -- the
                ; ",," arm below loops back without evaluating, so a count kept at
                ; the value misses an OMITTED argument (`SCREEN 1,,99` applied 99
                ; as the sprite size). Commas and argument slots are 1:1.
                ld      a,(GFX_SARGN)
                inc     a
                ld      (GFX_SARGN),a
                ; D-SCRARITY: THE LIST STOPS AT FIVE, AND THE BOUND IS ON THE COMMA
                ; COUNT -- `SCREEN 1,,,,,` (an EMPTY 6th slot) is ERR 2 on both
                ; references, where the promise rule below would say ERR 24. So it
                ; fires here, before req_operand. GFX_SARGN counts TRAILING slots
                ; (1 = sprite size .. 4 = printer): 5 is a 6th argument.
                cp      5
                jp      nc,tt_syntax        ; ERR 2 (pl_syntax)
    ENDIF
                ld      ix,p0_req_operand
                call    p0cb                ; a comma PROMISED an argument: ERR 24 at
                                            ; `SCREEN 2,` / `SCREEN 2,:` / `SCREEN ,`
                cp      ','                 ; an omitted argument (",,")
                jr      z,scs_extra
                ; D-SCRERR: the trailing arguments are CHECKED BYTES as well --
                ; `SCREEN 1,,70000` is ERR 6 and `SCREEN 1,,300` ERR 5 on both.
                ld      ix,p0_eval_byte_checked
                call    p0cb                ; DE = the argument (D=0, E=byte)
    IF G7_RESIDENT
                push    hl
                call    scs_extra_arg       ; G7: slot 1 the sprite size, 2 the key
                pop     hl                  ; click, 3 the baud; the rest ignored
    ENDIF
                jr      scs_extra

    IF G7_RESIDENT
; --- SCREEN's sprite-size argument (D-G7-2; main's spr_mode_save / _restore) ----
; `SCREEN <mode>,<size>` selects 8x8 vs 16x16 (bit 1) and magnification (bit 0),
; and the setting PERSISTS across later SCREEN statements that omit it -- both
; measured. RG1SAV bits 1..0 ARE that state, so persistence is "re-apply them
; after CHGMOD", which is also where the attribute-x snapshot goes (D-G7-3). The
; ops are main's spr_tenant's (the graphics sub-ROM tenant, ROM 1), through p0cb.
scs_mode_save:
                ld      a,(RG1SAV)
                and     $03                 ; remember the size across CHGMOD, which
                ld      (GFX_SSIZE),a       ; re-writes VDP register 1 from its own table
                ld      a,10                ; tenant: snapshot the 32 attribute x bytes
                jr      scs_spr
scs_mode_restore:
                ld      a,11                ; tenant: put the x bytes back (CHGMOD zeroes
                                            ; them; the reference leaves them alone) AND
                                            ; re-apply the size bits to VDP register 1
scs_spr:                                    ; A = the op
                ld      ix,p0_spr_tenant
                jp      p0cb                ; raises the tenant's ERR code, else returns

; scs_extra_arg: one evaluated trailing SCREEN argument (DE = its value; main's
; spr_extra_arg). GFX_SARGN = the slot, maintained at each comma above.
;   slot 1  the sprite size, 0..3 (D-SCRERR: `SCREEN 1,99` is ERR 5 on both)
;   slot 2  the key click, stored RAW into CLIKSW (D-SCRCLICK: `,,2` -> 2 on both)
;   slot 3  the cassette baud rate, 1..2, validated and IGNORED (D-SCRBAUD)
;   slot 4  the printer: ignored
; C carries the bound so slots 1 and 3 share one test, then says which slot.
scs_extra_arg:
                ld      a,(GFX_SARGN)
                dec     a                   ; 0 = slot 1 (size), 2 = slot 3 (baud)
                ld      c,4                 ; sprite size: 0..3
                jr      z,scs_bound
                cp      1                   ; slot 2 = the key click
                jr      z,scs_click
                cp      2                   ; slot 3?  (A = slot - 1)
                ret     nz                  ; slots 4 and 5 stay ignored
                dec     e                   ; baud 1..2 -> 0..1, so ONE bound test
                ld      c,2                 ; serves both domains
                ; FALLS THROUGH into scs_bound -- keep nothing between the two
                ; (D-SCRCLICK's first cut put a block here and baud lost its check)
scs_bound:
                ld      a,e
                cp      c
                jp      nc,fs_illegal       ; ERR 5 -- out of this slot's domain
                dec     c
                dec     c                   ; 4 -> 2 (size), 2 -> 0 (baud)
                ret     z                   ; baud is validated and then IGNORED
                ld      (GFX_SSIZE),a       ; A = E, checked against C above
                ld      a,12                ; tenant: apply the size bits to register 1
                jr      scs_spr
scs_click:                                  ; E = the argument, stored RAW (no `and 1`)
                ld      a,e
                ld      (CLIKSW),a
                ret
    ENDIF   ; G7_RESIDENT

; ===========================================================================
; COLOR [<fg>][,<bg>][,<border>]   (main's ex_color)
; ===========================================================================
; Each colour is optional; an omitted one keeps its current value. D-PARTIAL: fg
; and bg are parsed into the CLR_SAVE shadow and published only at scc_apply,
; past every way the statement can fail -- so a refusal (`COLOR 7,99`) leaves the
; colours unchanged, as on both references, even on the exits that reset SP.
scr_color:
                push    hl                  ; (main's clr_prep) snapshot FORCLR+BAKCLR
                ld      hl,(FORCLR)         ; into the shadow: an omitted fg/bg is
                ld      (CLR_SAVE),hl       ; published back unchanged
                pop     hl
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; past COLOR; Z iff the statement ends
                ; D-BAREFORM: a BARE `COLOR` is `Missing operand` (ERR 24 on both
                ; references), NOT a re-apply.
                jp      z,scr_missing
                cp      ','                 ; "COLOR ,bg" -> fg omitted
                jr      z,scc_bg
                call    scc_eval            ; DE = foreground, VALIDATED 0..15
                ld      a,e
                ld      (CLR_SAVE),a        ; D-PARTIAL: the SHADOW, not the sysvar
                ld      ix,p0_skip_comma
                call    p0cb
                jr      nz,scc_apply
scc_bg:
                rst     $10                 ; past the comma
                cp      ','                 ; "COLOR fg,,border" -> bg omitted
                jr      z,scc_bd
                or      a
                jr      z,scc_apply
                cp      COLON
                jr      z,scc_apply
                call    scc_eval            ; DE = background, VALIDATED 0..15
                ld      a,e
                ld      (CLR_SAVE+1),a      ; D-PARTIAL: the SHADOW, not the sysvar
                ld      ix,p0_skip_comma
                call    p0cb
                jr      nz,scc_apply
scc_bd:
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; past the comma; Z iff the statement ends
                ; D-OMITARG: a TRAILING COMMA is `Missing operand` -- `COLOR 15,4,`
                ; and `COLOR ,,` are ERR 24 on both references.
                jp      z,scr_missing
                call    scc_eval            ; DE = border, VALIDATED 0..15
                ld      a,e
                ld      (BDRCLR),a          ; not shadowed: stored LAST, and nothing
                                            ; between here and the commit can fail
scc_apply:
                ; D-PARTIAL: SURFACE A DEFERRED TYPE MISMATCH BEFORE COMMITTING.
                ; `COLOR 7,"A"`: eval yields 0 with TMISMATCH pending, which passes
                ; the 0..15 test -- ask before acting (as at ev_ff_arg), not after.
                ld      ix,p0_check_expr_errors
                call    p0cb                ; TMISMATCH -> ERR 13, before any store
                push    hl
                ld      hl,(CLR_SAVE)       ; (main's clr_commit) publish the shadow:
                ld      (FORCLR),hl         ; FORCLR+BAKCLR are adjacent
                ; D-ADDR29 S3: the reference's COLOR also sets ATRBYT to the
                ; foreground (COLOR 5 -> 5; COLOR ,1 leaves it at the fg).
                ld      a,(FORCLR)
                ld      (ATRBYT),a
                ld      a,(SCRMOD)          ; CHGCLR wants the current screen mode
                ld      ix,CHGCLR
                call    p0cb
                jp      fs_pop_exec         ; main's `jp pop_exec`

; scc_eval (main's clr_eval): evaluate a COLOR component and require 0..15.
; out: E = the value, D = 0. Anything else raises and does not return.
; D-DOMAIN: 16 is the first illegal value and `COLOR 256` is ERR 5 too, so the
; HIGH byte is tested first (256's low byte is 0). D-COLOREQ: a PENDING error
; first -- `COLOR=NEW` / `COLOR=` / `COLOR=,1` are Syntax error on both
; references, where eval leaves the error pending with a junk -1.
scc_eval:
                ld      ix,p0_eval
                call    p0cb
                ld      ix,p0_check_expr_errors
                call    p0cb
                ld      a,d                 ; the HIGH byte first: 256 has a low
                or      a                   ; byte of 0 and must NOT pass
                jp      nz,fs_illegal
                ld      a,e
                cp      16
                ret     c                   ; 0..15 -> good
                jp      fs_illegal          ; ERR 5 Illegal function call

; ===========================================================================
; WIDTH <columns>   (main's ex_width)
; ===========================================================================
; Records the line length in LINLEN and in the active mode's per-mode default
; (LINL40 for SCREEN 0 and every graphics mode, LINL32 for SCREEN 1), then
; re-inits the screen so the new width is programmed into the VDP.
scr_width:
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; past WIDTH; Z iff the statement ends
                jp      z,scr_missing       ; bare WIDTH -> ERR 24
                ; D-EVALCHK: eval + the deferred-error check + the byte coercion,
                ; in that ORDER: `WIDTH 70000+0*(1/0)` is Division by zero on both
                ; references (the expression's error wins), `WIDTH "40"` Type
                ; mismatch, then ERR 6 past int16, ERR 5 at 256..
                ld      ix,p0_eval_byte_checked
                call    p0cb                ; A = the width
                ld      b,a
                ; the MODE-DEPENDENT bound and its slot, measured on the VG-8020:
                ; 1..32 in SCREEN 1 (LINL32), 1..40 in EVERY other mode (LINL40).
                ; LINL40/LINL32 are ADJACENT: one `ld de` plus an `inc de`.
                ld      de,LINL40
                ld      a,(SCRMOD)
                dec     a                   ; SCRMOD 1 = text-2
                ld      a,40                ; (no flags -- the `dec a` Z survives)
                jr      nz,scw_bound
                inc     de                  ; -> LINL32
                ld      a,32
scw_bound:
                cp      b
                jp      c,fs_illegal        ; wanted > the mode's maximum -> ERR 5
                ld      a,b
                or      a
                jp      z,fs_illegal        ; `WIDTH 0` -> ERR 5
                ; D-WIDTHKEEP: a WIDTH to the width ALREADY IN FORCE is a no-op on
                ; the VG-8020 (the screen and the cursor are kept). Tested against
                ; LINLEN, not the per-mode cell; nothing at all is written.
                ld      a,(LINLEN)
                cp      b
                jp      z,fs_exec           ; HL = the cursor
                ld      a,b
                ld      (LINLEN),a
                ld      (de),a              ; the mode's per-mode default
                ld      a,(SCRMOD)
                push    hl
                ld      ix,CHGMOD
                call    p0cb                ; re-init the screen at the new width
                ld      ix,p0_key_repaint
                call    p0cb                ; D-KEYCLS: the re-init cleared row 23
                jp      fs_pop_exec         ; main's `jp pop_exec`
