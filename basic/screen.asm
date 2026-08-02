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
;   - SCREEN's extra arguments (sprite size, key-click, baud, printer) are
;     evaluated and ignored — only the display mode is applied.
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
                jp      z,exec_stmt         ; bare SCREEN -> mode omitted, no-op
                cp      COLON
                jp      z,exec_stmt
                cp      ','                 ; "SCREEN ,x" -> mode omitted
                jr      z,scr_extra
                call    eval                ; DE = mode
                ld      a,d
                or      a
                jp      nz,stmt_error       ; mode must be 0..3 (MSX1)
                ld      a,e
                cp      4
                jp      nc,stmt_error
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
scr_extra:                                  ; evaluate + ignore any trailing args
                call    skip_spaces
                cp      ','
                jp      nz,exec_stmt        ; no comma -> done
                inc     hl                  ; past the comma
                call    skip_spaces
                or      a
                jp      z,exec_stmt
                cp      COLON
                jp      z,exec_stmt
                cp      ','                 ; an omitted argument (",,")
                jr      z,scr_extra
                call    eval                ; DE = the argument
    IF G7_RESIDENT
                push    hl
                call    spr_extra_arg       ; G7: the first one is the sprite size; the
                pop     hl                  ; rest (click, baud, printer) stay ignored
    ENDIF
                jr      scr_extra

; --- ex_color: COLOR [<fg>][,<bg>][,<border>] ------------------------------
; Each colour is optional; an omitted one keeps the current work-area value.
ex_color:
                inc     hl                  ; past the COLOR token
                call    skip_spaces
                or      a
                jp      z,clr_apply         ; bare COLOR -> re-apply current colours
                cp      COLON
                jp      z,clr_apply
                cp      ','                 ; "COLOR ,bg" -> fg omitted
                jr      z,clr_bg
                call    eval                ; DE = foreground
                ld      a,e
                ld      (FORCLR),a
                call    skip_spaces
                cp      ','
                jp      nz,clr_apply
clr_bg:
                inc     hl                  ; past the comma
                call    skip_spaces
                cp      ','                 ; "COLOR fg,,border" -> bg omitted
                jr      z,clr_bd
                or      a
                jp      z,clr_apply
                cp      COLON
                jp      z,clr_apply
                call    eval                ; DE = background
                ld      a,e
                ld      (BAKCLR),a
                call    skip_spaces
                cp      ','
                jp      nz,clr_apply
clr_bd:
                inc     hl                  ; past the comma
                call    skip_spaces
                or      a
                jp      z,clr_apply
                cp      COLON
                jp      z,clr_apply
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
                inc     hl                  ; past the WIDTH token
                call    skip_spaces         ; returns A = (HL)
                or      a
                jr      z,wid_missing       ; bare `WIDTH` -> Missing operand (ERR 24)
                cp      COLON
                jr      z,wid_missing       ; `WIDTH :` likewise -- both measured
                call    eval                ; DE = column count
                ld      a,(TMISMATCH)       ; `WIDTH "40"` -> Type mismatch (measured)
                or      a
                jp      nz,type_mismatch_error
                call    get_byte_arg        ; D-F2-2 stage B: WIDTH n is a byte 0..255
                ld      b,a                 ; (>int16 ERR 6, 256.. ERR 5); A = width
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
