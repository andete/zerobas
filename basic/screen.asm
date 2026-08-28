; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; screen.asm — the SCREEN / COLOR / CLS / WIDTH / KEY screen-setup verbs.
;
;   SCREEN <mode>[,<sprite>][,<click>]...   set the VDP display mode
;   COLOR [<fg>][,<bg>][,<border>]          set the three screen colours
;   CLS                                     clear the screen
;   WIDTH <columns>                         set the text line length
;   KEY OFF | KEY ON                        hide / show the function-key line
;
; A loader stub almost always does some of this before `BLOAD`, e.g.
; `SCREEN 2 : COLOR 15,1,1 : CLS` or `KEY OFF : SCREEN 1`. These are thin
; wrappers over the documented C-BIOS screen entry points — zerobas owns no VDP
; programming of its own, it just calls down through the BIOS jump table the way
; the real BASIC does (see docs/msx1-basic-bios-coupling.md):
;   SCREEN -> CHGMOD ($005F)   COLOR -> CHGCLR ($0062)   CLS -> CLS ($00C3)
;   KEY OFF/ON -> ERAFNK/DSPFNK ($00CC/$00CF)
; WIDTH records the new line length in the per-mode work variable, then re-runs
; CHGMOD so the change takes effect.
;
; Divergences from full MSX-BASIC (Phase 2 scope), accepted here:
;   - SCREEN's extra arguments past the FIRST are evaluated (and range-checked
;     as bytes — D-SCRERR) and then ignored: the key-click, baud and printer
;     arguments have no effect. The first one, the sprite size, IS applied and
;     domain-checked (G7, docs/spec-basic-graphics-g7.md).
;   - COLOR applies the colours via CHGCLR but does not repaint already-drawn
;     text; omitted arguments leave that colour unchanged.
;   - KEY only recognises OFF / ON; `KEY <n>,"str"` (redefine) and `KEY LIST`
;     are not supported and raise a syntax error.
;
; Clean-room: original code. Statement *semantics* from the public MSX-BASIC
; language reference; every BIOS entry point and work-area address is traced to
; the MSX Assembly Page / MSX2 Technical Handbook / C-BIOS (see sysvars.inc and
; PROVENANCE.md). No disassembly.
;
; Each handler is entered with HL on its statement token and continues the line
; via `jp exec_stmt`, so the verbs chain on one `:`-separated line. The C-BIOS
; entry points make no register guarantees, so HL is guarded across every call.

; --- ex_screen: SCREEN <mode>[,<extra>]... ---------------------------------
ex_screen:
    IF G7_RESIDENT
                xor     a                   ; graphics G7: the FIRST trailing argument is the
                ld      (GFX_SARGN),a       ; sprite size, and it is no longer discarded
    ENDIF
                inc     hl                  ; past the SCREEN token
                call    skip_spaces
                or      a
                jp      z,loc_missing       ; bare `SCREEN` -> Missing operand (ERR
                cp      COLON               ; 24); `SCREEN :` likewise -- both
                jp      z,loc_missing       ; measured, D-SCRERR spec §2.1. An
                                            ; ARGUMENT LIST THAT ENDS WHERE A VALUE
                                            ; WAS REQUIRED is ERR 24 at every one of
                                            ; this routine's four such slots; the
                                            ; other two are in scr_extra below.
                cp      ','                 ; "SCREEN ,x" -> mode omitted
                jr      z,scr_extra
                ; D-SCRERR (docs/spec-basic-screenerr.md): the mode is a CHECKED
                ; BYTE, and it is checked BEFORE CHGMOD. This was `call eval` and
                ; two hand-rolled range rejects that `jp stmt_error` -- a GRAMMAR
                ; verdict on a DOMAIN fault -- and the shape had TWO divergences
                ; in it, not one:
                ;   `SCREEN -1` / `SCREEN 256` / `SCREEN (1<5)` answered Syntax
                ;   error where both references answer Illegal function call, and
                ;   `SCREEN 70000` answered NOTHING AT ALL -- eval's silent
                ;   flt_to_int16 zeroed DE, so an out-of-int16 mode SET SCREEN 0
                ;   where both references answer Overflow.
                ;   `SCREEN 0*(1/0)` reported the right code at the wrong TIME:
                ;   the range tests pass, CHGMOD runs, and only then does
                ;   `jp exec_stmt` read the pending cell -- so the screen was
                ;   reinitialised before the message. Both references never apply
                ;   the mode (measured as SCRMOD over a `SCREEN 1` seed).
                ; eval_byte_checked is exactly the reference contract and closes
                ; both: the DEFERRED expression error first (ERR 11/6/5/13 --
                ; `SCREEN 70000+0*(1/0)` is 11 and `70000+0*SQR(-1)` is 5, a
                ; DIFFERENT code, which is what says the expression's error wins
                ; rather than that division by zero is special), then ERR 6 past
                ; int16 (-32769 and 32768; -32768 is IN range and is ERR 5),
                ; then ERR 5 outside 0..255.
                ; 🔴 BUT NOT BECAUSE THE CHEAPER eval_byte_arg WOULD ANSWER
                ; DIFFERENTLY HERE -- knife K-SE2 swapped them and moved NOTHING,
                ; twice, INCLUDING the two 70000+fault rows written specifically
                ; to discriminate. The reason is D-PENDERR: every writer into the
                ; pending cell is SET-IF-EMPTY, so fac_to_int_strict's own ERR 6
                ; can no longer overwrite a live code, and D-EVALCHK's stated
                ; justification for the checked leaf (spec-basic-evalchk.md: "it
                ; writes FPERR=1 OVER THE TOP of the pending FPERR=2") was true
                ; when written and made FALSE by D-PENDERR a few commits later.
                ; The checked leaf is kept because it is the same 3 bytes, is
                ; what WIDTH/FIELD/CLEAR use, and states the ordering explicitly
                ; -- NOT because a row here can tell the two apart. The o.dzov /
                ; o.5ov rows still earn their place: they pin the RULE (a fault
                ; that already happened outranks the coercion), they just do not
                ; pin the ROUTINE. See spec-basic-screenerr.md §8.
                ; It also TRUNCATES rather than
                ; rounding, which `SCREEN 1.6` -> mode 1 and `SCREEN 3.6` -> mode
                ; 3 require (PROVENANCE.md: fac_to_int_strict is oracle-pinned
                ; truncating -- checked before the substitution, not after).
                ; -6 B: 14 B of eval + two hand-rolled rejects for 8 B.
                call    eval_byte_checked   ; A = E = the mode, 0..255, or aborts
                cp      4
                jp      nc,gb_illegal       ; an MSX1 has modes 0..3 -> ERR 5. `4`
                                            ; is a VALID byte, so this test cannot
                                            ; be folded into the coercion.
                push    hl                  ; A = mode -> switch the VDP mode
    IF G7_RESIDENT
                push    af
                call    spr_mode_save       ; G7: keep the sprite size + the attribute x
                pop     af                  ; bytes across CHGMOD (spec G7 §5)
                call    CHGMOD
                call    spr_mode_restore
    ELSE
                call    CHGMOD
    ENDIF
                pop     hl
scr_extra:                                  ; the trailing arguments
                call    skip_spaces
                cp      ','
                jp      nz,exec_stmt        ; no comma -> done (the ONLY legal way
                                            ; out of this loop)
                inc     hl                  ; past the comma
    IF G7_RESIDENT
                ; 🔴 D-SCRERR: COUNT THE SLOT AT THE COMMA, NOT AT THE VALUE.
                ; The ",," arm below loops back WITHOUT evaluating anything, so
                ; a counter bumped by spr_extra_arg never sees an OMITTED
                ; argument and every argument after one is off by one position:
                ; `SCREEN 1,,99` applied 99 as the SPRITE SIZE. That was already
                ; wrong before this slice and NO row could see it -- the old
                ; `and $03` quietly turned it into size 3, and a wrong sprite
                ; size does not show up in SCRMOD. It became visible only when
                ; the domain check below turned it into an ERROR the reference
                ; does not raise (row a.clk). Commas and argument slots are 1:1,
                ; so counting here is both correct and cheaper than counting at
                ; the value: spr_extra_arg's own increment goes away (-4 B).
                ld      a,(GFX_SARGN)       ; 🔴 NOT `ld hl,GFX_SARGN / inc (hl)`
                inc     a                   ; (D-PEEPHOLE): HL is the PARSE CURSOR
                ld      (GFX_SARGN),a       ; here -- skip_spaces below advances it.
    ENDIF
                call    skip_spaces
                or      a                   ; a comma PROMISED an argument, so a
                jp      z,loc_missing       ; statement end here is ERR 24 --
                cp      COLON               ; `SCREEN 2,` and `SCREEN 2,:`, and via
                jp      z,loc_missing       ; the ",," arm `SCREEN ,` too. Measured
                                            ; on both references (spec §2.1).
                cp      ','                 ; an omitted argument (",,")
                jr      z,scr_extra
                ; D-SCRERR: the trailing arguments are CHECKED BYTES as well --
                ; `SCREEN 1,,70000` is ERR 6 and `SCREEN 1,,300` is ERR 5 on both
                ; references, so the int16 AND the byte stage are both live here
                ; and not only on the mode. Free: it replaces a `call eval` that
                ; was already there.
                call    eval_byte_checked   ; DE = the argument (D=0, E=byte)
    IF G7_RESIDENT
                push    hl
                call    spr_extra_arg       ; G7: the first one is the sprite size; the
                pop     hl                  ; rest (click, baud, printer) stay ignored
    ENDIF
                jr      scr_extra

; --- ex_color: COLOR [<fg>][,<bg>][,<border>] ------------------------------
; Each colour is optional; an omitted one keeps the current work-area value.
ex_color:
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                jr      z,clr_apply
                cp      ','                 ; "COLOR ,bg" -> fg omitted
                jr      z,clr_bg
                call    eval                ; DE = foreground
                ld      a,e
                ld      (FORCLR),a
                call    skip_spaces
                cp      ','
                jr      nz,clr_apply
clr_bg:
                inc     hl                  ; past the comma
                call    skip_spaces
                cp      ','                 ; "COLOR fg,,border" -> bg omitted
                jr      z,clr_bd
                or      a
                jr      z,clr_apply
                cp      COLON
                jr      z,clr_apply
                call    eval                ; DE = background
                ld      a,e
                ld      (BAKCLR),a
                call    skip_spaces
                cp      ','
                jr      nz,clr_apply
clr_bd:
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                jr      z,clr_apply
                call    eval                ; DE = border
                ld      a,e
                ld      (BDRCLR),a
clr_apply:
                ld      a,(SCRMOD)          ; CHGCLR wants the current screen mode
                push    hl
                call    CHGCLR
                pop     hl
                jp      exec_stmt

; --- ex_cls: CLS -----------------------------------------------------------
ex_cls:
                inc     hl                  ; past the CLS token
                push    hl
                xor     a                   ; CLS requires the zero flag set on entry
                call    CLS
                pop     hl
                jp      exec_stmt

; --- ex_width: WIDTH <columns> ---------------------------------------------
; Records the line length in LINLEN and in the active mode's per-mode default
; (LINL40 for text-1, LINL32 for text-2), then re-inits the screen so the new
; width is programmed into the VDP.
ex_width:
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                jr      z,wid_missing
                ; D-EVALCHK (docs/spec-basic-evalchk.md): eval + the deferred-
                ; error check + the byte coercion, in ONE call. This was 13 B
                ; written out inline -- `call eval`, a hand-rolled TMISMATCH
                ; test, `call get_byte_arg` -- and the inline shape had the
                ; CHECK AFTER THE COERCION, which is a divergence and not just
                ; five spare bytes: fac_to_int_strict writes FPERR=1 over the
                ; FPERR the expression already set, so `WIDTH 70000+0*(1/0)`
                ; answered Overflow where both references answer Division by
                ; zero (and `WIDTH 70000+0*SQR(-1)` answered Overflow where both
                ; answer Illegal function call -- a DIFFERENT code, which is
                ; what says the rule is "the expression's error wins" and not
                ; "division by zero is special").
                ; `WIDTH "40"` -> Type mismatch and the two domain stages
                ; (>int16 ERR 6, 256.. ERR 5) are unchanged; A = width.
                call    eval_byte_checked
                ld      b,a
                ; --- the MODE-DEPENDENT bound, and the slot that goes with it ---
                ; Measured on the VG-8020: the legal width is 1..32 in SCREEN 1
                ; and 1..40 in EVERY other mode, and the per-mode default written
                ; is LINL32 for SCREEN 1 and LINL40 otherwise -- graphics modes
                ; included, which is where the old `or a` (any non-zero SCRMOD ->
                ; LINL32) was wrong. LINL40/LINL32 are ADJACENT, so one `ld de`
                ; plus an `inc de` picks the slot; the bound rides the same test.
                ld      de,LINL40
                ld      a,(SCRMOD)
                dec     a                   ; SCRMOD 1 = text-2
                ld      a,40                ; (no flags -- the `dec a` Z survives)
                jr      nz,wid_bound
                inc     de                  ; -> LINL32
                ld      a,32
wid_bound:
                cp      b
                jr      c,wid_illegal       ; wanted > the mode's maximum
                ld      a,b
                or      a
                jr      z,wid_illegal       ; `WIDTH 0` -> Illegal function call
                ld      (LINLEN),a
                ld      (de),a              ; the mode's per-mode default
wid_apply:
                ld      a,(SCRMOD)
                push    hl
                call    CHGMOD              ; re-init the screen at the new width
                pop     hl
                jp      exec_stmt
                ; Both rejects run at ex_width's OWN depth (exec_stmt `jp`s here),
                ; so they need no return-address parking -- the same reason
                ; ex_swap tests its operands at the handler's depth.
wid_illegal:
                jp      gb_illegal          ; ERR 5
wid_missing:
                jp      loc_missing         ; ERR 24

; --- ex_key: KEY OFF | KEY ON ----------------------------------------------
ex_key:
                inc     hl                  ; past the KEY token
                call    skip_spaces
    IF TRAPS_T3
                cp      '('                 ; KEY(n) ON|OFF|STOP -- the T3 arming form.
                jp      z,ex_key_stmt       ; Tested AHEAD of ON/OFF so the display form
                                            ; keeps working unchanged (oracle case K10).
    ENDIF
                cp      OFF_TOKEN
                jr      z,key_off
                cp      ON_TOKEN
                jr      z,key_on
                jp      stmt_error          ; KEY <n>,"str" / KEY LIST unsupported
key_off:
                inc     hl                  ; past OFF
                push    hl
                call    ERAFNK
                pop     hl
                jp      exec_stmt
key_on:
                inc     hl                  ; past ON
                push    hl
                call    DSPFNK
                pop     hl
                jp      exec_stmt
