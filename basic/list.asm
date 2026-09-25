; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; list.asm — the LIST statement (display the stored program).
;
;   LIST          list the whole stored program
;
; LIST walks the stored numbered-line program (the same one NEW / RUN manage,
; in program.asm) and prints each line as source text: the decimal line number,
; a space, then the *de-tokenised* body, then CR/LF.
;
; The hard part is the detokeniser (`detok`) — the exact inverse of interp.asm's
; `tokenise:`. It walks a line's crunched token body and renders every token the
; tokeniser can emit back to ASCII:
;   - keyword tokens                -> their keyword text (reverse of `kwtable`)
;   - 2-byte function token $FF $97 -> PEEK
;   - digit/byte/word int tokens
;     ($11+n / $0F,b / $1C,w / $0C &H,w / $0B &O,w) -> the decimal/hex source
;   - operator tokens ($EF $F1 $F2 $F3 $F4 $FC $EE $F0) -> = + - * / \ > <
;   - line-number reference $0E,<lineno LE> (and $0D,<addr> post-RUN) -> decimal
;   - string literals "…", REM / ' tails, and DATA bodies -> copied verbatim
;   - ELSE ($3A $A1) and ' ($3A $8F $E6) -> ELSE / ' (the leading ':' folded out)
; Everything `tok_skip` (interp.asm) knows how to step, `detok` knows how to
; render — they cover the same token set.
;
; Clean-room: original code. LIST *semantics* (number, space, source, newline)
; from the public MSX-BASIC language reference; the detokeniser is the reverse of
; this project's own oracle-sourced tokeniser (interp.asm `tokenise:` / `kwtable`,
; spec-tokenise.md / spec-tokens-statements.md). No constant here is new — each
; token byte it decodes is already defined+cited in sysvars.inc. No disassembly.
;
; Line-range arguments are implemented (D-LSTRNG, docs/spec-basic-listrange.md,
; measured in docs/listrange-msx1-characterization.md):
;
;   LIST          the whole program        LIST n-m      lines n..m
;   LIST n        line n only              LIST n-       line n to the END
;   LIST -m       the start up to line m
;
; 🔴 AND THESE ARE **NOT** `DELETE`'s RANGE RULES, though the two verbs share a
; byte-identical argument grammar. LIST has no high-end existence check, no
; reversal check, and no range error of any kind: `LIST 20-35`, `LIST 30-20` and
; `LIST 10-65529` list what is in range (or nothing) with ERR 0, where the same
; three shapes are ERR 5 under DELETE. Sharpest of all, an ABSENT HIGH END IS
; 65535 -- `LIST 20-` lists to the end of the program, where `DELETE 20-` means
; 20-0 and raises. Five of the twenty measured shapes would be wrong if the
; rules had been carried across; see spec §2.
;
; Entry: ex_list, HL -> the LIST token.

; --- ex_list: LIST [<lo>][-[<hi>]] -------------------------------------------
; docs/spec-basic-listrange.md, measured in
; docs/listrange-msx1-characterization.md. HL enters on the LIST token (the
; es_hit contract). This is the marshalling head; the ARGUMENT PARSE lives in
; sub/lineedit.asm's le_lstrange, beside the DELETE parse it deliberately does
; NOT resemble.
;
; WHY ONLY THE PARSE GOES SUB-SIDE (spec §3.1). DELETE put its WHOLE verb in the
; page-1 tenant for 37 B of main page 1. That is IMPOSSIBLE here, and not for
; budget reasons: list_walk prints through pchar (main page 1) and reaches the
; detokeniser by CALSLT to a page-0 tenant, and a page-1 tenant has main page 1
; switched out and cannot call either. So the walk stays resident and only the
; parse -- which marshals as ONE POINTER, the grammar being `[$0E lo] [$F2 [$0E
; hi]]` with no expression evaluation anywhere -- is evicted. A fully resident
; parse was costed at ~107 B against 82 B free: it does not fit (knife K7).
;
; ⚠️ NOTHING COMES BACK BUT A STATUS, AND THAT IS R-LS7, NOT A SHORTCUT. LIST
; ENDS the line and the program -- `LIST 20:B=9` leaves B at 0 with ERR 0
; (lse-tail, against lse-tailctl's 9) and `20 LIST 40` inside a RUN stops the
; program (lse-inprog reads 1, not 13). ⚠️ BOTH OF THOSE WERE PREDICTED THE
; OTHER WAY and the measurement refuted the prediction; the reasoning was that
; DELETE ends the run because it memmoved the text CURLINE points into and LIST
; moves nothing. So the advanced cursor has no reader and is never marshalled
; back -- which is also what makes the head this small.
; --- ex_llist: LLIST [<lo>][-[<hi>]] (D-EDITVERB) ---------------------------
; 🎯 `LLIST` IS `LIST` WITH A DIFFERENT SINK, AND THAT IS A MEASUREMENT, NOT AN
; ASSUMPTION. docs/editverb-msx1-characterization.md §4 re-asked every one of the
; twenty shapes D-LSTRNG characterized -- the range grammar, the 65535 open high
; end, the absent range error, the `,` Syntax error, the accepted-then-abandoned
; `:` tail -- on the printer, on both references, and all twenty agree. So this
; shares the parse, the validation, the walk and the ENDFLAG tail; the ONLY
; difference is which sink pchar feeds, and the only new code is the two
; instructions that say so.
;
; The verb is carried in LE_OP, which the tenant does not write, so the head
; reads it BACK after the call rather than spending a RAM flag on it -- see
; basic/sysvars.inc at LE_OP_LLSTRANGE.
ex_llist:
                ld      a,LE_OP_LLSTRANGE
                jr      exl_entry
ex_list:
                ld      a,LE_OP_LSTRANGE
exl_entry:
                ld      (LE_OP),a
                ld      (LST_PTR),hl        ; the statement cursor, on the token
                call    le_call             ; A = LE_STATUS, Z = ok. The ERR CODE
                                            ; ITSELF; only ever 2
                                            ; (R-LS6). LIST has NO range error --
                jp      nz,raise_error      ; a high end naming no stored line, a
                                            ; reversed range and a range past the
                                            ; program are all ERR 0 and list
                                            ; nothing, exactly where DELETE raises 5.
                ; ⚠️ THE SINK IS CHOSEN *AFTER* THE PARSE, DELIBERATELY. Set it
                ; before, and an `LLIST 10,20` (R-LL4, Syntax error) raised inside
                ; a program with a live `ON ERROR` would jump into the handler
                ; with PRDEST still 1 -- and the handler's own PRINT would go to
                ; the printer. Every exit above this point leaves PRDEST alone.
                ld      a,(LE_OP)
                sub     LE_OP_LSTRANGE      ; LIST -> 0 = the SCREEN sink;
                ld      (PRDEST),a          ; LLIST -> 1 = the file-channel sink
                jr      z,exl_walk
                ld      (PRDEV),a           ; ...and A is 1 == LPT: the printer
exl_walk:
                call    list_walk           ; walk + emit [LST_LO, LST_HI]
                ; R-LL6 -- the screen sink IS restored, and NOT here.
                ;
                ; 🔴 KNIFE K3 DELETED THE `xor a / ld (PRDEST),a` THAT STOOD HERE
                ; AND `llt-sink` DID NOT MOVE. The justification written with it
                ; was FALSE: it claimed to cover `10 LLIST:...` whose ON ERROR
                ; handler runs first, and no such path exists. Every exit from
                ; this verb reaches the REPL -- the ENDFLAG below stops the run,
                ; and the raise above happens BEFORE the sink is ever set -- and
                ; `repl` opens with its own defensive `ld (PRDEST),a`. Four bytes
                ; of main page 1 that bought nothing measurable, removed.
                ;
                ; ⚠️ THAT MAKES THE RESET repl.asm's JOB, WHICH IS A CROSS-FILE
                ; INVARIANT WITH NO GATE OF ITS OWN. If LLIST ever stops ending
                ; the run, the sink leaks into the next statement and `llt-sink`
                ; is the row that would catch it.
                ; R-LS7: and then the run stops. Same mechanism as ex_end/ex_delete
                ; -- the run loop tests ENDFLAG immediately after `exec` returns.
                ; ⚠️ AND UNLIKE ex_delete, CONTVALID IS *NOT* CLEARED: R-LS8, LIST
                ; is not a program edit, and lse-cont (whose CONT must still resume,
                ; reading 5 like its control) is the row that gates the difference.
                jp      end_line_end

; --- lst_setall / list_all: the WHOLE program ------------------------------
; 🔴 list_walk HAS THREE CALLERS AND A LIST RANGE MUST NOT LEAK INTO TWO OF THEM
; (spec §3.3). ascii_save and cas_ascii_save (basic/save.asm) drive the same walk
; to disk and to tape; left alone, `LIST 20-30` followed by `SAVE"F",A` would
; silently write TWO LINES -- a data-loss bug in a verb this slice never
; mentions. They call list_all instead, which is a 3-byte call exactly like the
; one it replaces, so the split costs the call sites nothing.
lst_setall:
                ld      de,0
                ld      (LST_LO),de
                dec     de                  ; DE = $FFFF
                ld      (LST_HI),de
                ret
list_all:
                call    lst_setall
                ; fall into list_walk

; --- list_walk — walk the stored program, emitting each line as "number space
; detokenised-body CRLF" through pchar. pchar follows the PRDEST sink: the screen
; for LIST (PRDEST=0), or the open file channel for ASCII SAVE (PRDEST=1, see
; ascii_save, save.asm) — so the ONE detokeniser feeds both. Returns after the
; $0000 end-of-program link. Clean-room: our own detokeniser; the ASCII listing
; format is the public MSX-BASIC language reference.
list_walk:
                ld      hl,TXTBASE
lst_lp:
                ld      e,(hl)              ; DE = link to next line
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                ret     z                   ; $0000 link -> end of program
                push    de                  ; guard the link across the print
                inc     hl                  ; skip link (2) -> line number
                inc     hl
                ld      c,(hl)              ; line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl                  ; HL -> token body
                ; R-LS3: the range filter. Lines are stored ASCENDING, so once one
                ; is above hi nothing further can be in range either and the walk
                ; STOPS rather than skipping on. Both exits reuse the link this
                ; loop has already pushed. (D-LSTRNG; for the whole-program
                ; callers lst_setall has made this 0..65535, above.)
                ld      de,(LST_HI)
                ld      a,e                 ; hi - number: CF set -> past the top
                sub     c
                ld      a,d
                sbc     a,b
                jr      c,lst_stop
                ld      de,(LST_LO)
                ld      a,c                 ; number - lo: CF set -> not yet at the
                sub     e                   ; range. The walk starts at the first
                ld      a,b                 ; stored line >= lo; neither end has to
                sbc     a,d                 ; name a stored line (lst-lomid: `LIST
                jr      c,lst_skip          ; 25-30` prints only line 30).
                push    hl                  ; guard the body pointer
                ld      d,b                 ; print_number wants the value in DE
                ld      e,c
                ; D-DOTLINE writer (b) (docs/spec-basic-dotline.md §2 R-DOT3b):
                ; `.` records the LAST LINE THE WALK PRINTED. Three measured
                ; rules fall out of this ONE placement, which is why it is four
                ; bytes and not sixteen:
                ;   * LAST printed, not the argument and not either end --
                ;     `LIST 10-30` records 30 (cln-listrng) and bare `LIST`
                ;     records 40, not the 65535 high end (cln-listbare). Each
                ;     line overwrites the one before, so the last one stands;
                ;   * a walk that prints NOTHING writes nothing -- `LIST 25`
                ;     leaves `.` alone (cln-listmiss). This branch simply never
                ;     runs, so the rule is STRUCTURAL here and has no knife of
                ;     its own (spec §7 K3 says so rather than pretending);
                ;   * 🔴 and the ASCII SAVE paths write it TOO, which is the
                ;     REFERENCE'S OWN BEHAVIOUR and not a leak. Measured on the
                ;     CF-3300 (characterization §4, ONE reference): `.`=20,
                ;     `SAVE"A:F.BAS",A` -> 40, tokenised `SAVE"A:F.BAS"` -> 20.
                ;     ⚠️ THIS IS THE EXACT SHAPE §3.3 HAD TO *FIX* IN THIS
                ;     ROUTINE -- a LIST range leaking into SAVE",A" was a
                ;     data-loss bug -- and inheriting that answer here would have
                ;     cost ~16 B to be measurably WRONG. Same routine, two
                ;     shared-code questions, opposite answers.
                ld      (DOT),de
                call    list_num            ; print the line number (no extra spaces)
                ld      a,' '               ; one space between number and body
                rst     $18
                pop     hl                  ; HL = token body
                call    detok               ; render the body through pchar (PRDEST)
                call    print_crlf
                pop     hl                  ; HL = link -> next line's link field
                jr      lst_lp
lst_skip:
                pop     hl                  ; below lo: the guarded link IS the next
                jr      lst_lp              ; line's address -- step and try again
lst_stop:
                pop     de                  ; past hi: drop the guarded link and end
                ret                         ; the walk (lines are ascending)

; --- list_num: print DE as an unsigned decimal line number ------------------
; print_number formats a *signed* value with a leading sign space and a trailing
; space; a line number wants neither, so we format the magnitude ourselves into
; NUMBUF (reusing div10 from print.asm) with no sign and no trailing space.
list_num:
                ex      de,hl               ; HL = value (magnitude; line nos are >=0)
                jr      ln_div_entry        ; print HL as bare unsigned decimal

; --- detok: render the crunched token body at (HL) -------------------------
; The whole detokeniser body (detok/dt_*/detok_op/detok_kw*/the number renderers
; + ln_div_entry) lives in basic/detok.inc. Its home depends on the build (subrom
; arc WAVE 3, docs/spec-basic-subrom-wave3-detok.md):
;   * repack build: the body is EVICTED to sub-ROM page 0
;     (sub/detok.asm), where pchar/print_string are re-bound to DETOKBUF appends
;     and kwtable is the co-located sub copy. `detok` here is a dispatch stub that
;     CALSLTs the core once per line to fill DETOKBUF, then drains it back through
;     the real pchar — honouring PRDEST, so the one core still feeds BOTH
;     LIST->screen and ASCII-SAVE->disk (the single list_walk:detok call site).
;     Cold path (LIST / ASCII SAVE only), so the whole-line DI span is cosmetic
;     (spec §5, same class as wave-2's tokeniser span). ln_div_entry stays RESIDENT
;     here: list_num (line numbers) and program.asm's error line-number printing
;     reach it by ordinary in-slot call and must not page out — a copy separate
;     from detok.inc's sub-side one (which serves the evicted detok_dec).
detok:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_DETOK
                ; 🎯 D-CARVE3: canonical "detokenise via the tenant, then print"
                ; tail; basic/printusing.asm's number path jumps here.
; 🪟 D-DETOKBUF S1: WINDOWED. The tenant renders through a 96 B window
; (DB_WIN); while it reports DB_MORE, it is run AGAIN with DB_SKIP advanced
; past what was already drained. Only LIST and KEY LIST can ever set DB_MORE --
; they are re-runnable (pure over the line / the key table); PRINT USING's
; tenants cannot, and sub/printusing.asm asserts they fit one window. An
; ordinary line renders once, as before.
detok_emit:
                ld      bc,0                ; skip total
de_win:
                ld      (DB_SKIP),bc
                push    bc
                push    hl                  ; the tenant's argument, for a re-run
                push    ix
                call    subrom_call         ; HL=token body in; the core fills DB_WIN
                                            ; (0-terminated); CF=1 if the sub-ROM is absent
                jp      c,subrom_absent_error ; reduced build w/o sub-ROM (never on the
                                            ; merged machine, which always ships it)
                ld      hl,DB_WIN
                call    print_string        ; drain the window -> pchar (PRDEST sink)
                pop     ix
                pop     hl
                pop     bc
                ld      a,(DB_MORE)
                or      a
                ret     z                   ; the whole render fit -> back to list_walk
                ld      a,(DB_RESUME)
                or      a
                jr      z,de_fromstart
                ld      hl,(DB_RESPTR)      ; LIST: resume AT the token the window
                ld      bc,(DB_RESSKIP)     ; stopped in, skipping what was drained
                jr      de_win
de_fromstart:
                ld      a,c                 ; KEY LIST: re-run from the start
                add     a,DB_WINSZ-1        ; skip past what was just drained
                ld      c,a
                jr      nc,de_win
                inc     b
                jr      de_win

; ln_div_entry (RESIDENT copy): print HL as bare unsigned decimal. list_num and
; program.asm's line-number printing stay resident and reach this by in-slot call;
; detok.inc carries a byte-identical sub-side twin for the evicted detok_dec.
ln_div_entry:
                call    dgt_push            ; D-DGTPUSH: the shared digit loop
                ld      de,NUMBUF
dde_wr:
                pop     af
                cp      $FF
                jr      z,dde_tail
                add     a,'0'
                ld      (de),a
                inc     de
                jr      dde_wr
dde_tail:
                jp      num_publish         ; D-CARVE3 (-5 B, main page 1)

; (Arrays slice-4a: the resident hex_digit/oct_digit copies that used to live
; here for str-engine.asm's HEX$/OCT$ are GONE — HEX$/OCT$ moved their digit-
; building bodies into the sub-ROM tenant (sub/strheap.asm sh_hex_build/
; sh_oct_build, with their own local digit leaves), so nothing in the repack
; main ROM references hex_digit/oct_digit any more. detok.inc carries the
; sub-side twins.)
