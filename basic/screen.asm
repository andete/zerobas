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
                call    req_operand         ; bare `SCREEN` -> Missing operand (ERR
                                            ; 24); `SCREEN :` likewise -- both
                                            ; measured, D-SCRERR spec §2.1. An
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
                call    skip_comma
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
                ; 🎯 D-SCRARITY: THE ARGUMENT LIST STOPS AT FIVE, AND THE BOUND IS
                ; ON THE COMMA COUNT, NOT ON HOW MANY ARGUMENTS ARE PRESENT.
                ; D-SCRSLOT measured `SCREEN 1,,,,,1` as ERR 2 on both references
                ; and could not tell which rule that was: a 6th SLOT and a 6th
                ; VALUE are the same thing in that row. `SCREEN 1,,,,,` separates
                ; them -- an EMPTY 6th slot -- and both references answer **ERR 2**
                ; where the promise rule below would have said ERR 24. So the
                ; bound is here, at the comma, and it fires BEFORE req_operand
                ; (D-SCRARITY, scratchpad/scrarity_probe.py: 11 rows, both
                ; references agreeing on all 11).
                ; ⚠️ `cp 5`, and the first cut wrote `cp 6`. GFX_SARGN counts
                ; TRAILING slots only -- 1 is the sprite size, 4 the printer --
                ; so "the list stops at five" is the MODE plus FOUR of these.
                ; With `cp 6` only `SCREEN 1,,,,,,1` moved and the filed row did
                ; not; the probe named it in one run.
                cp      5                   ; a 5th TRAILING slot = a 6th argument
                jp      nc,pl_syntax        ; ERR 2 (`jp`: pl_syntax is out of jr
                                            ; range from here -- measured, not assumed)
    ENDIF
                call    req_operand         ; a comma PROMISED an argument, so a
                                            ; statement end here is ERR 24 --
                                            ; `SCREEN 2,` and `SCREEN 2,:`, and via
                                            ; the ",," arm `SCREEN ,` too. Measured
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
                call    clr_prep            ; D-PARTIAL: snapshot fg+bg into the shadow
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                ; 🔴 D-BAREFORM: a BARE `COLOR` is `Missing operand`, NOT a re-apply.
                ; Measured on BOTH references (ERR 24 each); zerobas answered with
                ; no error at all, re-applying the current colours. The note in
                ; missing.asm reads "ex_color's bare form re-applies, LOCATE's
                ; simply does not move that axis" -- and LOCATE was written against
                ; the OPPOSITE measured answer to the same question. One of the two
                ; was never re-asked [[two-rules-that-coincide-on-every-row-you-have]].
                ; `clr_apply` keeps every OTHER entry (`COLOR fg`, `COLOR ,bg`,
                ; `COLOR fg,,bd` and the comma-tail forms below).
                jp      z,loc_missing       ; +1 B: `jr` cannot reach it
                cp      ','                 ; "COLOR ,bg" -> fg omitted
                jr      z,clr_bg
                call    clr_eval            ; DE = foreground, VALIDATED 0..15
                ld      a,e
                ld      (CLR_SAVE),a        ; D-PARTIAL: the SHADOW, not the sysvar
                call    skip_comma
                jr      nz,clr_apply
clr_bg:
                call    inc_skip           ; past the comma
                cp      ','                 ; "COLOR fg,,border" -> bg omitted
                jr      z,clr_bd
                or      a
                jr      z,clr_apply
                cp      COLON
                jr      z,clr_apply
                call    clr_eval            ; DE = background, VALIDATED 0..15
                ld      a,e
                ld      (CLR_SAVE+1),a      ; D-PARTIAL: the SHADOW, not the sysvar
                call    skip_comma
                jr      nz,clr_apply
clr_bd:
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                ; 🔴 D-OMITARG: A TRAILING COMMA IS `Missing operand`, NOT A
                ; RE-APPLY. `COLOR 15,4,` and `COLOR ,,` both reach here with the
                ; statement ending right after a separator, and both used to fall
                ; into clr_apply and succeed. Measured ERR 24 on BOTH references,
                ; and every OTHER verb in the tree already rejects its trailing
                ; comma (LOCATE 0,5, / SCREEN 0, / SOUND 0, / POKE x, all ERR 24).
                ; COLOR was the only one that did not.
                ; 💰 BYTE-NEUTRAL: `wid_missing` is 76 bytes away, so this stays a
                ; `jr`. The alias below costs nothing and keeps the name honest --
                ; the same shape as `loc_missing equ g8_missing` in missing.asm.
                jr      z,clr_missing
                call    clr_eval            ; DE = border, VALIDATED 0..15
                ld      a,e
                ld      (BDRCLR),a
clr_apply:
                ; 🔴 D-PARTIAL, second half: SURFACE A DEFERRED TYPE MISMATCH BEFORE
                ; COMMITTING. `COLOR 7,"A"` does not fail inside `eval` — eval sets
                ; TMISMATCH and YIELDS 0 when a string meets a non-string, so
                ; clr_eval's 0..15 check passes on that 0, the statement runs to
                ; completion, and `exec_stmt` raises ERR 13 afterwards. The shadow
                ; alone therefore did NOT fix this row: it faithfully committed a
                ; foreground of 7 and a background of 0 — the "0 that no argument
                ; asked for", finally explained rather than merely observed.
                ; 🎯 The remedy is the one this tree already uses at ev_ff_arg:
                ; ask check_expr_errors before acting, not after.
                call    check_expr_errors   ; TMISMATCH -> ERR 13, before any store
                ld      a,(SCRMOD)          ; CHGCLR wants the current screen mode
                push    hl
                call    clr_commit          ; D-PARTIAL: publish the shadow — the ONLY
                                            ; point at which COLOR becomes visible, and
                                            ; it is past every way the statement can fail
                call    CHGCLR
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt

; --- ex_cls: CLS -----------------------------------------------------------
ex_cls:
                inc     hl                  ; past the CLS token
                push    hl
                xor     a                   ; CLS requires the zero flag set on entry
                call    CLS
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt

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
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt
                ; Both rejects run at ex_width's OWN depth (exec_stmt `jp`s here),
                ; so they need no return-address parking -- the same reason
                ; ex_swap tests its operands at the handler's depth.
wid_illegal:
                jp      gb_illegal          ; ERR 5
wid_missing:
clr_missing:                                ; D-OMITARG: COLOR's trailing-comma
                                            ; reject. Same raiser, 0 bytes -- a
                                            ; second label, not a second body.
                jp      loc_missing         ; ERR 24

; --- ex_key: KEY OFF | KEY ON ----------------------------------------------
ex_key:
                ; 🔴 D-BAREFORM: a BARE `KEY` is `Missing operand`, not `Syntax
                ; error`. Measured ERR 24 on BOTH references; zerobas answered
                ; ERR 2. The test is HERE and not at the `jp stmt_error` below,
                ; because that tail is also the face for `KEY n,"str"` and
                ; `KEY LIST` -- forms that are UNIMPLEMENTED rather than absent,
                ; and whose face is a separate open item. A shared tail is a
                ; label, not a decision [[a-shared-tail-is-not-a-decision]].
                ; ⚠️ `stmt_bare_end` DOES THE `inc hl` ITSELF (interp.asm:978) and
                ; then skip_spaces, so it REPLACES this handler's opening two
                ; instructions -- it does not follow them. The first cut kept the
                ; `inc hl` and called it afterwards, which stepped past the $00
                ; terminator into the next line and never saw end-of-statement:
                ; bare KEY still answered ERR 2 and the row was still red.
                ; Net +2 B this way, against +6 B for the wrong shape.
                call    stmt_bare_end       ; past the KEY token; Z iff it ends here
                jp      z,loc_missing       ; bare KEY / `KEY:` -> ERR 24
    IF TRAPS_T3
                cp      '('                 ; KEY(n) ON|OFF|STOP -- the T3 arming form.
                jp      z,ex_key_stmt       ; Tested AHEAD of ON/OFF so the display form
                                            ; keeps working unchanged (oracle case K10).
    ENDIF
                cp      OFF_TOKEN
                jr      z,key_off
                cp      ON_TOKEN
                jr      z,key_on
                ; --- D-KEYSTR (2026-09-10): KEY LIST and KEY n,"str" -------------
                ; Both were `Syntax error` here and work on both references
                ; (D-MISSOP3's r.keyok, D-KEYSCOUT2's eleven rows). The body is
                ; the SUBROM_IDX_KEYSTR tenant; what stays here is the parse:
                ; LIST, or n (1..10 -> else ERR 5, measured) `,` string -- staged
                ; into STRSCR by fname_expr, the same [len][bytes] contract NAME
                ; and OPEN use. IX is the token pointer: guarded, as evmc_sqr.
                cp      LIST_TOKEN
                jr      nz,key_store
                inc     hl                  ; past LIST
                push    hl
                ld      a,255
                jr      key_call
key_store:
                call    eval_byte_arg       ; A = n, 0..255 (ERR 6 / ERR 5 outside)
                or      a
                jp      z,gb_illegal        ; KEY 0,   -> ERR 5 (measured)
                cp      11
                jp      nc,gb_illegal       ; KEY 11,  -> ERR 5 (measured)
                ; 🔴 NOT into KEYARG yet: it aliases WIDIG, the fp widening
                ; scratch, and the STRING may widen a number on its way in
                ; (`KEY 1,STR$(5)`). The slot rides the stack across the string
                ; evaluation; an error inside it resets SP, so the push is
                ; harmless on every refusal path.
                push    af                  ; [n]
                call    skip_comma
                jp      nz,stmt_error       ; KEY n without `,`: unmeasured, refuse
                inc     hl                  ; skip_comma stops ON the comma (its
                                            ; callers follow it with inc_eval);
                                            ; the first cut handed the comma to
                                            ; str_eval and every store read ERR 2
                call    fname_expr          ; STRSCR+1 := the bytes, `"`-terminated;
                                            ; FN_RESUME set. \U0001f534 It does NOT
                                            ; write the length byte -- parse_disk_fcb
                                            ; stops on the quote -- and the tenant
                                            ; reading STRSCR+0 got a stale count:
                                            ; every store carried a trailing `"`.
                ld      hl,(STRPTR)         ; the descriptor is [len][ptr]: stage
                ld      a,(hl)              ; the TRUE length where the tenant
                ld      (STRSCR),a          ; reads it (a CHR$(34) inside stays exact)
                ld      hl,(FN_RESUME)
                pop     af                  ; A = n
                push    hl                  ; [resume]
key_call:
                ld      (KEYARG),a
                push    ix
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_KEYSTR
                call    sc_call             ; D-SCCALL: tenant call + absent raise
                pop     ix
                ; The tenant leaves DETOKBUF printable after EVERY op -- LIST's
                ; ten lines, or a lone NUL -- so the drain is unconditional and
                ; costs no branch (the D-PUEMIT shape: render sub-side, drain
                ; through the resident print_string).
                ld      hl,DETOKBUF
                call    print_string
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt
; 🟢 D-FNKLINE (Joost, 2026-09-17: *"go with option c for KEY"*). These two used
; to be a bare BIOS call each, and on our target that call PAINTS NOTHING --
; C-BIOS's `DSPFNK` leaves row 23 blank where the reference writes 20 cells
; (D-DSPFNK). So each arm now does three things: keep the BIOS call (harmless,
; and correct on a machine whose BIOS does paint), set `CNSDFG` -- the DOCUMENTED
; flag C-BIOS does not maintain -- and ask the sub-ROM to draw or erase the line.
; 🎯 THE PAINTER IS SUB-SIDE because the macro store already is: `keystr_tenant`
; reads `$F87F` and sub page 0 is not the scarce region. Main pays the flag, the
; op byte and one `sc_call`.
; ⚠️ NO `print_string` DRAIN HERE, unlike `key_call` above: these ops leave
; DETOKBUF a lone NUL, so draining would print nothing and cost bytes.
key_off:
                inc     hl                  ; past OFF
                push    hl
                call    ERAFNK
                xor     a                   ; the line is hidden
                jr      key_disp
key_on:
                inc     hl                  ; past ON
                push    hl
                call    DSPFNK
                ld      a,$FF               ; the reference's own value, measured
key_disp:
                ld      (CNSDFG),a
                or      a
                ld      a,KEYOP_FNKBLANK
                jr      z,kd_op
                ld      a,KEYOP_FNKPAINT
kd_op:
                ld      (KEYARG),a
                push    ix
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_KEYSTR
                call    sc_call             ; D-SCCALL: tenant call + absent raise
                pop     ix
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt
