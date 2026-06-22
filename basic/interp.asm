; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; interp.asm — the tokeniser + execution-loop front-end.
;
; A small interpreter spine: crunch an ASCII line into tokens, then walk the
; line statement-by-statement (separated by ':'), dispatching each on its
; leading token. Statements implemented: BLOAD (cassette load + ,R handoff),
; POKE, a single-letter variable assignment, and REM (comment). PEEK is a
; function handled inside the expression evaluator.
;
; Derived only from this project's own black-box oracle observations
; (basic-spec/docs/spec-tokenise.md, spec-tokens-statements.md) and the public
; MSX-BASIC language reference. No disassembly.

; --- INIT entry (cartridge header points here) -----------------------------
init:
                ei                          ; keyboard ISR must run for CHGET
                call    clear_vars          ; deterministic variable table
                call    clear_usrtab        ; zero the DEF USR vectors
                call    init_filechan       ; no open channel; PRINT dest = screen
                call    new_prog            ; empty stored program (Step B)
                call    init_ext_roms       ; run the boot-scan INITs C-BIOS skips
                                            ; (e.g. zerobas-disk in slot 3-1) since
                                            ; our own INIT never returns to the scan
                call    show_title          ; startup header lines
                jp      repl                ; read/eval loop (never returns)

; --- tokenise: ASCII line -> token stream ----------------------------------
; in:  HL = source (0-terminated ASCII), DE = destination buffer
; out: destination holds tokens, 0x00-terminated
; spec-tokenise.md / spec-tokens-statements.md: a keyword crunches to its token
; byte(s) (case-folded); string literals and other bytes are copied verbatim;
; REM (and the '\'' abbreviation) keep the rest of the line verbatim; the line
; is terminated by 0x00.
; External entry: reset the in-name flag, then run the per-char loop. Internal
; jumps target tk_loop (which preserves the flag across characters).
tokenise:
                xor     a
                ld      (TKNAME),a          ; a fresh line starts outside any name
tk_loop:
                ld      a,(TKNAME)
                ld      b,a                 ; B = were we inside a name? (digit rule)
                xor     a
                ld      (TKNAME),a          ; default after this char: not in a name
                ld      a,(hl)
                or      a
                jp      z,tk_end
                cp      '"'                 ; string literal: copy verbatim
                jp      z,tk_string
                cp      QUOTE_REM           ; "'" comment -> treat as REM
                jp      z,tk_apos
                cp      '0'                 ; a digit?
                jr      c,tk_nondigit
                cp      '9'+1
                jr      nc,tk_nondigit
                ; A digit continues a name (verbatim) only if we were in one;
                ; otherwise it begins a numeric constant. This is why `A1` keeps
                ; the '1' as $31 while `=1` crunches `1` to a number token.
                ld      a,b
                or      a
                jr      nz,tk_namedig
                jp      tk_number           ; '0'..'9' starting a numeric constant
tk_namedig:
                ld      a,1
                ld      (TKNAME),a          ; the digit extends the name
                ld      a,(hl)              ; copy it verbatim
                ld      (de),a
                inc     de
                inc     hl
                jp      tk_loop
tk_nondigit:
                cp      '&'                 ; "&H" hex constant
                jp      z,tk_hex
                call    match_kw            ; keyword match runs at EVERY position, so
                jr      nc,tk_notkw         ; reserved words inside a name still tokenise
                                            ; (SCORE -> SC,OR,E); TKNAME stays 0 here, so
                                            ; a keyword correctly breaks the name.
                cp      REM_TOKEN           ; REM swallows the rest of the line
                jp      z,tk_rem_rest
                cp      DATA_TOKEN          ; DATA body is stored verbatim (to ':')
                jp      z,tk_data_rest
                call    branch_lineno       ; GOTO/GOSUB/THEN/… <n> -> $0E,<n LE>
                jp      tk_loop
tk_notkw:
                ld      a,(hl)              ; not a keyword
                cp      '='
                jp      z,tk_op_eq
                cp      '+'
                jp      z,tk_op_plus
                cp      '-'
                jp      z,tk_op_minus
                cp      '*'
                jp      z,tk_op_star
                cp      '<'
                jp      z,tk_op_lt
                cp      '>'
                jp      z,tk_op_gt
                cp      '/'
                jp      z,tk_op_div
                cp      '\'
                jp      z,tk_op_idiv
                cp      '?'                 ; '?' abbreviates PRINT
                jp      z,tk_print_q
                call    is_letter           ; a letter starts / continues a name
                jr      c,tk_copy_up
tk_copy:
                ld      a,(hl)              ; punctuation / space: copy verbatim
                ld      (de),a
                inc     de
                inc     hl
                jp      tk_loop
tk_copy_up:
                ld      a,(hl)              ; a name letter, upcased (§4)
                call    upcase
                ld      (de),a
                inc     de
                inc     hl
                ld      a,1
                ld      (TKNAME),a          ; now inside a name
                jp      tk_loop
tk_string:
                ld      a,(hl)              ; opening quote
                ld      (de),a
                inc     de
                inc     hl
tk_str_loop:
                ld      a,(hl)
                or      a
                jr      z,tk_end            ; unterminated string -> just end
                ld      (de),a
                inc     de
                inc     hl
                cp      '"'                 ; copy through the closing quote
                jr      nz,tk_str_loop
                jp      tk_loop
tk_apos:
                ld      a,COLON             ; "'" -> $3A $8F $E6 (spec §3, byte-exact)
                ld      (de),a
                inc     de
                ld      a,REM_TOKEN
                ld      (de),a
                inc     de
                ld      a,APOS_MARK
                ld      (de),a
                inc     de
                inc     hl                  ; skip the "'"
tk_rem_rest:
                ld      a,(hl)              ; rest of line copied verbatim
                or      a
                jr      z,tk_end
                ld      (de),a
                inc     de
                inc     hl
                jr      tk_rem_rest
tk_data_rest:                               ; DATA body verbatim up to ':' or EOL
                ld      a,(hl)              ; (oracle: items stored as ASCII text;
                or      a                   ;  ':' ends DATA, the next statement is
                jp      z,tk_end            ;  crunched normally). Quoted ':' inside
                cp      COLON               ;  DATA is not special-cased (no strings).
                jp      z,tk_loop
                ld      (de),a
                inc     de
                inc     hl
                jr      tk_data_rest
tk_end:
                xor     a
                ld      (de),a              ; 0x00 terminator
                ret

; --- tk_op_*: emit an operator token (spec §4) -----------------------------
tk_op_eq:
                ld      a,EQ_TOKEN
                jr      tk_op_emit
tk_op_plus:
                ld      a,PLUS_TOKEN
                jr      tk_op_emit
tk_op_minus:
                ld      a,MINUS_TOKEN
                jr      tk_op_emit
tk_op_star:
                ld      a,STAR_TOKEN
                jr      tk_op_emit
tk_op_lt:
                ld      a,LT_TOKEN
                jr      tk_op_emit
tk_op_gt:
                ld      a,GT_TOKEN
tk_op_emit:
                ld      (de),a
                inc     de
                inc     hl
                jp      tk_loop
tk_print_q:                                 ; '?' -> PRINT token (oracle: ? -> $91)
                ld      a,PRINT_TOKEN
                jr      tk_op_emit
tk_op_div:
                ld      a,DIV_TOKEN
                jr      tk_op_emit
tk_op_idiv:
                ld      a,IDIV_TOKEN
                jr      tk_op_emit

; --- tk_number: crunch a decimal integer constant (spec §3) ----------------
;   0..9   -> $11+n          10..255 -> $0F,<byte>
;   256..  -> $1C,<word LE>  (>=32768 diverges from the reference's float form,
;                             which is out of scope this step — use &H instead)
; HL = source cursor, DE = destination cursor. DE is parked on the stack while
; the value is accumulated in DE; HL is parked during each *10 step.
tk_number:
                push    de                  ; save destination cursor
                ld      de,0                ; DE = accumulated value
tk_num_lp:
                ld      a,(hl)
                cp      '0'
                jr      c,tk_num_done
                cp      '9'+1
                jr      nc,tk_num_done
                sub     '0'                 ; A = digit
                ld      c,a
                push    hl                  ; DE = DE*10 + C
                ld      h,d
                ld      l,e
                add     hl,hl               ; 2*acc
                add     hl,hl               ; 4*acc
                add     hl,de               ; 5*acc
                add     hl,hl               ; 10*acc
                ld      e,c
                ld      d,0
                add     hl,de               ; +digit
                ex      de,hl               ; DE = new acc
                pop     hl                  ; restore source cursor
                inc     hl
                jr      tk_num_lp
tk_num_done:
                ld      b,d
                ld      c,e                 ; BC = value
                pop     de                  ; restore destination cursor
                ld      a,b
                or      a
                jr      nz,tk_num_w         ; >=256 -> two-byte form
                ld      a,c
                cp      10
                jr      nc,tk_num_b         ; 10..255 -> one-byte form
                add     a,INT_DIGIT_BASE    ; 0..9 -> $11+n
                ld      (de),a
                inc     de
                jp      tk_loop
tk_num_b:
                ld      a,INT1_TOKEN
                ld      (de),a
                inc     de
                ld      a,c
                ld      (de),a
                inc     de
                jp      tk_loop
tk_num_w:
                ld      a,INT2_TOKEN
                ld      (de),a
                inc     de
                ld      a,c                 ; value low
                ld      (de),a
                inc     de
                ld      a,b                 ; value high
                ld      (de),a
                inc     de
                jp      tk_loop

; --- tk_hex: crunch "&H" hex / "&O" octal constants -> $0C / $0B,<word LE> ---
; Oracle (basic_probe_crunch.py): the reference crunches `&H<hex>` to
; $0C,<value16 LE> and `&O<oct>` to $0B,<value16 LE> (HEX_TOKEN / OCT_TOKEN),
; full 0..&HFFFF — same shape as $1C int constants. `&B` and a bare `&` are
; copied VERBATIM: the VG-8020 has no `&B` binary token (oracle showed
; `a=&b1010` crunches to `& B 1 0 1 0` ASCII), so we must not invent one — `&B`
; is a documented own-design descope (PROVENANCE.md, quarantined). The single
; accumulator loop is parameterised by base (B) and token (C): hex *16 over
; 0-9 A-F, octal *8 over 0-7.
tk_hex:
                inc     hl                  ; past '&'
                ld      a,(hl)
                call    upcase
                cp      'H'
                jr      z,tk_hex_h
                cp      'O'
                jr      z,tk_hex_o
                dec     hl                  ; not &H/&O (&B, bare &) -> copy '&' verbatim
                jp      tk_copy
tk_hex_h:
                ld      a,16                ; hex: radix 16, accumulate over 0-9 A-F
                ld      (TKRADIX),a
                ld      a,HEX_TOKEN
                ld      (TKRTOK),a
                jr      tk_hex_go
tk_hex_o:
                ld      a,8                 ; octal: radix 8, accumulate over 0-7
                ld      (TKRADIX),a
                ld      a,OCT_TOKEN
                ld      (TKRTOK),a
tk_hex_go:
                inc     hl                  ; past the H / O
                push    de                  ; save destination cursor
                ld      de,0                ; DE = value
tk_hex_lp:
                ld      a,(hl)
                call    upcase
                cp      '0'
                jr      c,tk_hex_done       ; below '0' -> end of digits
                ld      c,a                 ; C = the upcased source char
                ld      a,(TKRADIX)
                cp      8
                jr      z,tk_hex_oct        ; octal: only '0'..'7'
                ; hex digit test: '0'..'9','A'..'F'
                ld      a,c
                cp      '9'+1
                jr      c,tk_hex_dig        ; '0'..'9'
                cp      'A'
                jr      c,tk_hex_done
                cp      'F'+1
                jr      nc,tk_hex_done
                sub     'A'-10              ; 'A'..'F' -> 10..15
                jr      tk_hex_acc
tk_hex_oct:                                 ; octal digit test: '0'..'7'
                ld      a,c
                cp      '7'+1
                jr      nc,tk_hex_done
                sub     '0'                 ; '0'..'7' -> 0..7
                jr      tk_hex_acc
tk_hex_dig:
                ld      a,c
                sub     '0'                 ; '0'..'9' -> 0..9
tk_hex_acc:
                ld      c,a                 ; digit value
                push    hl                  ; DE = DE*radix + digit
                ld      h,d
                ld      l,e
                ld      a,(TKRADIX)
                add     hl,hl               ; *2  (both radices)
                add     hl,hl               ; *4
                add     hl,hl               ; *8
                cp      8
                jr      z,tk_hex_mac        ; octal stops at *8
                add     hl,hl               ; *16 (hex)
tk_hex_mac:
                ld      e,c
                ld      d,0
                add     hl,de               ; + digit
                ex      de,hl               ; DE = new value
                pop     hl
                inc     hl
                jr      tk_hex_lp
tk_hex_done:
                ld      b,d
                ld      c,e                 ; BC = value
                pop     de                  ; restore destination cursor
                ld      a,(TKRTOK)          ; HEX_TOKEN ($0C) or OCT_TOKEN ($0B)
                ld      (de),a
                inc     de
                ld      a,c                 ; value low
                ld      (de),a
                inc     de
                ld      a,b                 ; value high
                ld      (de),a
                inc     de
                jp      tk_loop

; --- match_kw: is a table keyword present at (HL)? -------------------------
; in:  HL = source position, DE = destination cursor
; out: CF set   -> match: token byte(s) emitted to (DE), DE advanced, HL past
;                  the keyword, A = first token byte
;      CF clear -> no match: HL and DE unchanged
; Uses IX as the table cursor and IY as the keyword-char walker.
match_kw:
                push    iy
                ld      ix,kwtable
mk_entry:
                ld      a,(ix+0)            ; keyword length (0 = end of table)
                or      a
                jr      z,mk_none
                push    hl                  ; remember source start
                push    ix
                pop     iy
                inc     iy                  ; IY -> keyword chars
                ld      b,a                 ; B = chars to compare
mk_cmp:
                ld      a,(iy+0)            ; keyword char (stored uppercase)
                ld      c,a
                ld      a,(hl)              ; source char
                call    upcase              ; case-fold before comparing
                cp      c
                jr      nz,mk_fail
                inc     hl
                inc     iy
                djnz    mk_cmp
                ; matched: IY -> token-length byte, HL advanced past keyword
                pop     bc                  ; discard saved source start
                ld      a,(iy+0)            ; token length
                ld      b,a
                inc     iy                  ; IY -> token bytes
                ld      c,(iy+0)            ; remember first token byte
mk_emit:
                ld      a,(iy+0)
                ld      (de),a
                inc     iy
                inc     de
                djnz    mk_emit
                ld      a,c                 ; A = first token byte
                pop     iy                  ; restore caller IY
                scf
                ret
mk_fail:
                pop     hl                  ; restore source start
                ld      a,(ix+0)            ; klen
                ld      b,0
                ld      c,a
                inc     bc                  ; skip [klen][chars]
                add     ix,bc               ; IX -> token-length byte
                ld      a,(ix+0)            ; tlen
                ld      b,0
                ld      c,a
                inc     bc                  ; skip [tlen][tokens]
                add     ix,bc               ; IX -> next entry
                jr      mk_entry
mk_none:
                pop     iy                  ; restore caller IY
                or      a                   ; CF clear (no match)
                ret

; --- branch_lineno: emit a line-number reference after a branch keyword ------
; A = first token byte just emitted by match_kw, HL = source cursor (after the
; keyword), DE = dest cursor. If the keyword was GOTO/GOSUB/THEN/RESTORE/RUN, copy
; any spaces verbatim then, if a decimal number follows, emit it as the
; line-number identification code $0E,<value LE> (Figure 2.12) instead of the
; ordinary integer encoding. Otherwise returns unchanged. (ON…GOTO lists and
; ELSE <line> are not specially handled yet — single target only.)
branch_lineno:
                cp      GOTO_TOKEN
                jr      z,bl_yes
                cp      GOSUB_TOKEN
                jr      z,bl_yes
                cp      THEN_TOKEN
                jr      z,bl_yes
                cp      RESTORE_TOKEN
                jr      z,bl_yes
                cp      RUN_TOKEN
                jr      z,bl_yes
                ret                         ; not a branch keyword
bl_yes:
                ld      a,(hl)              ; copy spaces verbatim
                cp      ' '
                jr      nz,bl_num
                ld      (de),a
                inc     de
                inc     hl
                jr      bl_yes
bl_num:
                cp      '0'                 ; a decimal number must follow
                ret     c
                cp      '9'+1
                ret     nc
                push    de                  ; park dest while accumulating
                ld      de,0                ; DE = value
bl_acc:
                ld      a,(hl)
                cp      '0'
                jr      c,bl_done
                cp      '9'+1
                jr      nc,bl_done
                sub     '0'
                ld      c,a
                push    hl                  ; DE = DE*10 + C
                ld      h,d
                ld      l,e
                add     hl,hl
                add     hl,hl
                add     hl,de
                add     hl,hl
                ld      e,c
                ld      d,0
                add     hl,de
                ex      de,hl
                pop     hl
                inc     hl
                jr      bl_acc
bl_done:
                ld      b,d
                ld      c,e                 ; BC = line number
                pop     de                  ; restore dest cursor
                ld      a,LINENO_TOKEN      ; $0E
                ld      (de),a
                inc     de
                ld      a,c                 ; value low
                ld      (de),a
                inc     de
                ld      a,b                 ; value high
                ld      (de),a
                inc     de
                ; extend for ON…GOTO/GOSUB comma-separated lists
                ld      a,(hl)
                cp      ','
                ret     nz                  ; no comma -> single target, done
                ld      (de),a              ; emit the comma verbatim
                inc     de
                inc     hl                  ; past the comma
                jr      bl_yes              ; loop: spaces then next number

; keyword -> token table. Entry layout: [klen][UPPERCASE chars][tlen][token...].
; Terminated by a 0 length byte. Tokens are oracle-sourced (spec-tokenise.md,
; spec-tokens-statements.md). PEEK is a two-byte function token ($FF $97).
kwtable:
                db      5,"BLOAD",1,BLOAD_TOKEN
                ; SAVE / BSAVE statement tokens (oracle-LOCKED, Philips VG-8020;
                ; MSX2 TH Table 2.20). BSAVE must precede SAVE in the crunch: the
                ; tokeniser attempts a keyword match at EVERY position, so at the
                ; 'B' of "BSAVE" match_kw must find the full "BSAVE" entry (it does
                ; — it compares the whole keyword and returns the first full match,
                ; so 'B' is never copied verbatim and "SAVE" is never matched at
                ; position 1). "BSAVE" and "BLOAD" share only the leading 'B', so
                ; there is no longest-match hazard between them. Order within the
                ; table is otherwise free (match_kw is full-keyword, not prefix).
                db      5,"BSAVE",1,BSAVE_TOKEN
                db      4,"SAVE",1,SAVE_TOKEN
                ; Disk BASIC: FILES (list the directory). Token oracle-locked
                ; ($B7; MSX2 TH Table 2.20). Shares no prefix with another entry.
                db      5,"FILES",1,FILES_TOKEN
                ; MERGE (merge an ASCII program from disk). Token oracle-locked
                ; ($B6; MSX2 TH Table 2.20) — in the main ROM table like FILES.
                db      5,"MERGE",1,MERGE_TOKEN
                ; Sequential file-channel verbs (Phase 2). Tokens oracle-locked
                ; (OPEN $B0, INPUT $85, LINE $AF, CLOSE $B4; MSX2 TH Table 2.20).
                ; match_kw compares the full keyword, so table order is free.
                db      4,"OPEN",1,OPEN_TOKEN
                db      5,"INPUT",1,INPUT_TOKEN
                db      4,"LINE",1,LINE_TOKEN
                db      5,"CLOSE",1,CLOSE_TOKEN
                ; PUT exists only so "OUTPUT" crunches to OUT($9C)+PUT($B3); the
                ; PUT statement (random access) is sub-phase 2c (no dispatch yet).
                db      3,"PUT",1,PUT_TOKEN
                ; File-info functions: $FF-prefixed (EOF=$FF$AB, LOF=$FF$AD,
                ; DSKF=$FF$A6).
                db      3,"EOF",2,PEEK_PREFIX,EOF_TOKEN
                db      3,"LOF",2,PEEK_PREFIX,LOF_TOKEN
                db      4,"DSKF",2,PEEK_PREFIX,DSKF_TOKEN
                ; Random-access conversions (Phase 2c). $FF-prefixed function tokens
                ; (MKI$=$FF$AE returns a string — the '$' is PART of the keyword, unlike
                ; INPUT$; CVI=$FF$A8 returns a number). Oracle-locked to the VG-8020.
                db      4,"MKI$",2,PEEK_PREFIX,MKI_TOKEN
                db      3,"CVI",2,PEEK_PREFIX,CVI_TOKEN
                ; File management: KILL (delete) + NAME (rename). Oracle-locked
                ; tokens ($D4 / $D3). "NAME" shares no prefix with another entry.
                db      4,"KILL",1,KILL_TOKEN
                db      4,"NAME",1,NAME_TOKEN
                ; MAXFILES = MAX($CD) + FILES($B7) — two reserved words (oracle-
                ; locked, like OUTPUT = OUT+PUT). FILES is already in this table, so
                ; only "MAX" is added; the tokeniser then crunches "MAXFILES" to
                ; $CD $B7 by matching MAX then FILES. match_kw is full-keyword, so
                ; MAX never shadows a variable that merely starts with it unless the
                ; whole word "MAX" appears — faithful (the reference reserves MAX too).
                db      3,"MAX",1,MAX_TOKEN
                ; Cassette save keyword. CSAVE token oracle-LOCKED ($9A) via
                ; basic_probe_crunch.py against Philips VG-8020 (MSX2 TH Table
                ; 2.20). Single-byte statement token; filename kept verbatim ASCII.
                db      5,"CSAVE",1,CSAVE_TOKEN
                ; Cassette program-load keywords (oracle-confirmed; MSX2 TH
                ; Table 2.20). CLOAD precedes BLOAD's family for no special
                ; reason — match_kw compares the full keyword, so order is free.
                db      5,"CLOAD",1,CLOAD_TOKEN
                db      4,"LOAD",1,LOAD_TOKEN
                db      4,"POKE",1,POKE_TOKEN
                db      4,"PEEK",2,PEEK_PREFIX,PEEK_TOKEN
                db      3,"REM",1,REM_TOKEN
                ; Step B control flow (spec-controlflow.md; MSX2 TH Table 2.20).
                db      4,"GOTO",1,GOTO_TOKEN
                db      5,"GOSUB",1,GOSUB_TOKEN
                db      6,"RETURN",1,RETURN_TOKEN
                db      2,"IF",1,IF_TOKEN
                db      4,"THEN",1,THEN_TOKEN
                db      4,"ELSE",2,COLON,ELSE_TOKEN
                db      3,"FOR",1,FOR_TOKEN
                db      2,"TO",1,TO_TOKEN
                db      4,"STEP",1,STEP_TOKEN
                db      4,"NEXT",1,NEXT_TOKEN
                db      4,"DATA",1,DATA_TOKEN
                db      4,"READ",1,READ_TOKEN
                db      7,"RESTORE",1,RESTORE_TOKEN
                db      3,"RUN",1,RUN_TOKEN
                db      3,"NEW",1,NEW_TOKEN
                db      3,"END",1,END_TOKEN
                db      4,"STOP",1,STOP_TOKEN
                db      2,"ON",1,ON_TOKEN
                ; Phase 1: CONT (resume after STOP / Ctrl-STOP). Oracle-confirmed
                ; CONT -> $99 (MSX2 TH Table 2.20). NOTE: "ON" must precede "CONT"
                ; only by table coincidence — match_kw compares the full keyword,
                ; so order is free; CONT will not shadow ON.
                db      4,"CONT",1,CONT_TOKEN
                db      5,"PRINT",1,PRINT_TOKEN
                db      3,"LET",1,LET_TOKEN
                ; Phase 1: CLEAR [<strings>][,<himem>] (MSX2 TH Table 2.20).
                db      5,"CLEAR",1,CLEAR_TOKEN
                ; Phase 1: DEF USR / USR + screen verbs (MSX2 TH Table 2.20).
                db      3,"DEF",1,DEF_TOKEN
                db      3,"USR",1,USR_TOKEN
                db      4,"LIST",1,LIST_TOKEN
                db      3,"CLS",1,CLS_TOKEN
                db      6,"SCREEN",1,SCREEN_TOKEN
                db      5,"COLOR",1,COLOR_TOKEN
                db      5,"WIDTH",1,WIDTH_TOKEN
                db      3,"KEY",1,KEY_TOKEN
                db      3,"OFF",1,OFF_TOKEN
                ; Phase 1: memory / I-O access (MSX2 TH Table 2.20; oracle-
                ; confirmed). VPOKE/OUT = 1-byte statement tokens; VPEEK/INP =
                ; $FF-prefixed function tokens; VARPTR/BASE = 1-byte function
                ; tokens. VPEEK precedes VPOKE so the longer-matching reserved
                ; word is found first when both share the "VP" prefix (match_kw
                ; compares the full keyword, so order is not strictly required,
                ; but this keeps the more specific entries adjacent).
                db      5,"VPOKE",1,VPOKE_TOKEN
                db      5,"VPEEK",2,PEEK_PREFIX,VPEEK_TOKEN
                db      3,"OUT",1,OUT_TOKEN
                db      3,"INP",2,PEEK_PREFIX,INP_TOKEN
                db      6,"VARPTR",1,VARPTR_TOKEN
                db      4,"BASE",1,BASE_TOKEN
                ; Phase 1: logical / bitwise + MOD operator keywords (Table 2.20).
                db      3,"AND",1,AND_TOKEN
                db      2,"OR",1,OR_TOKEN
                db      3,"XOR",1,XOR_TOKEN
                db      3,"NOT",1,NOT_TOKEN
                db      3,"MOD",1,MOD_TOKEN
                db      0

; --- upcase: fold A to uppercase if it is 'a'..'z' -------------------------
; Preserves BC/DE/HL. Source: ASCII (allowed).
upcase:
                cp      'a'
                ret     c                   ; below 'a'
                cp      'z'+1
                ret     nc                  ; above 'z'
                sub     $20
                ret

; --- is_letter: CF set if A is 'A'..'Z' or 'a'..'z' (A preserved) ----------
is_letter:
                push    af
                call    upcase
                cp      'A'
                jr      c,il_no
                cp      'Z'+1
                jr      nc,il_no
                pop     af
                scf
                ret
il_no:
                pop     af
                or      a                   ; CF clear
                ret

; --- exec: walk the line, dispatching each statement -----------------------
; in: HL = token buffer (0x00-terminated). Statements are separated by ':'.
; Returns to the REPL at end of line (or hands off via BLOAD,R, never to return).
exec:
exec_stmt:
                xor     a                   ; each statement starts on the screen;
                ld      (PRDEST),a          ; only PRINT#'s own item loop sets dest=file
                call    skip_spaces         ; leading spaces are skipped (spec §5)
                ld      a,(hl)
                or      a
                ret     z                   ; end of line -> back to the prompt
                cp      COLON               ; ':' separator / empty statement
                jp      z,ex_sep
                cp      BLOAD_TOKEN
                jp      z,ex_bload
                cp      CLOAD_TOKEN
                jp      z,ex_cload
                cp      LOAD_TOKEN
                jp      z,ex_load
                cp      RUN_TOKEN
                jp      z,ex_run
                cp      BSAVE_TOKEN
                jp      z,ex_bsave
                cp      SAVE_TOKEN
                jp      z,ex_save
                cp      FILES_TOKEN
                jp      z,ex_files
                cp      MERGE_TOKEN
                jp      z,ex_merge
                cp      OPEN_TOKEN
                jp      z,ex_open
                cp      INPUT_TOKEN
                jp      z,ex_input
                cp      LINE_TOKEN
                jp      z,ex_line
                cp      CLOSE_TOKEN
                jp      z,ex_close
                cp      KILL_TOKEN
                jp      z,ex_kill
                cp      NAME_TOKEN
                jp      z,ex_name
                cp      MAX_TOKEN           ; MAX FILES = n  (MAXFILES config)
                jp      z,ex_maxfiles
                cp      CSAVE_TOKEN
                jp      z,ex_csave
                cp      POKE_TOKEN
                jp      z,ex_poke
                cp      VPOKE_TOKEN
                jp      z,ex_vpoke
                cp      OUT_TOKEN
                jp      z,ex_out
                cp      CLEAR_TOKEN
                jp      z,ex_clear
                cp      DEF_TOKEN
                jp      z,ex_def
                cp      PRINT_TOKEN
                jp      z,ex_print
                cp      CLS_TOKEN
                jp      z,ex_cls
                cp      SCREEN_TOKEN
                jp      z,ex_screen
                cp      COLOR_TOKEN
                jp      z,ex_color
                cp      WIDTH_TOKEN
                jp      z,ex_width
                cp      KEY_TOKEN
                jp      z,ex_key
                cp      LIST_TOKEN
                jp      z,ex_list
                cp      REM_TOKEN
                jr      z,ex_rem
                cp      DATA_TOKEN          ; DATA: skip this statement at run time
                jp      z,ex_data
                cp      READ_TOKEN
                jp      z,ex_read
                cp      RESTORE_TOKEN
                jp      z,ex_restore
                cp      GOTO_TOKEN
                jp      z,ex_goto
                cp      GOSUB_TOKEN
                jp      z,ex_gosub
                cp      ON_TOKEN
                jp      z,ex_on
                cp      RETURN_TOKEN
                jp      z,ex_return
                cp      FOR_TOKEN
                jp      z,ex_for
                cp      NEXT_TOKEN
                jp      z,ex_next
                cp      IF_TOKEN
                jp      z,ex_if
                cp      END_TOKEN
                jr      z,ex_end
                cp      STOP_TOKEN
                jp      z,ex_stop
                cp      CONT_TOKEN
                jp      z,ex_cont
                cp      ELSE_TOKEN          ; reached after a true THEN clause -> done
                jr      z,ex_rem
                cp      LET_TOKEN
                jp      z,ex_letkw
                call    is_letter           ; bare letter -> assignment
                jr      c,ex_let
                jp      stmt_error
ex_sep:
                inc     hl
                jp      exec_stmt
ex_end:
                ld      a,1                 ; END / STOP -> stop the run
                ld      (ENDFLAG),a
                ret
ex_rem:
                ret                         ; rest of line is a comment -> done
ex_data:                                    ; DATA is a no-op at run time: skip its
                inc     hl                  ; verbatim body up to ':' or EOL, then
exd_lp:                                     ; continue with the next statement.
                ld      a,(hl)
                or      a
                ret     z                   ; end of line
                cp      COLON
                jp      z,exec_stmt         ; ':' -> next statement runs
                inc     hl
                jr      exd_lp
ex_bload:
                inc     hl                  ; HL -> args (past the BLOAD token)
                jp      do_bload
ex_cload:
                inc     hl                  ; HL -> args (past the CLOAD token)
                jp      do_cload
ex_load:
                inc     hl                  ; HL -> args (past the LOAD token)
                jp      do_load
ex_run:
                inc     hl                  ; HL -> args (past the RUN token)
                jp      do_run
ex_bsave:
                inc     hl                  ; HL -> args (past the BSAVE token)
                jp      do_bsave
ex_save:
                inc     hl                  ; HL -> args (past the SAVE token)
                jp      do_save
ex_csave:
                inc     hl                  ; HL -> args (past the CSAVE token)
                jp      do_csave
ex_poke:
                inc     hl                  ; HL -> args (past the POKE token)
                jp      do_poke
ex_vpoke:
                inc     hl                  ; HL -> args (past the VPOKE token)
                jp      do_vpoke
ex_out:
                inc     hl                  ; HL -> args (past the OUT token)
                jp      do_out

; --- ex_let: variable assignment  <var> = <expr> --------------------------
; The name may be multi-character (significant to 2 chars; see vars.asm). A
; `$`-suffixed name (A$) is a string variable: the RHS is a string operand (a
; "literal" or another string variable) — see ex_let_str. Numeric vars keep the
; integer path.
ex_let:
                call    var_str_type        ; A=1 if the name carries a `$` suffix
                or      a
                jr      nz,ex_let_str       ; string variable -> string assignment
                call    var_name_key        ; BC = key, HL past the name
                push    bc                  ; save key across '=' + eval
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' crunches to $EF (spec §4)
                jr      nz,ex_let_err
                inc     hl
                call    eval                ; DE = value, HL = cursor (BC clobbered)
                pop     bc                  ; BC = key
                push    hl                  ; guard cursor across var_set_key
                call    var_set_key         ; var[key] = DE
                pop     hl
                jp      exec_stmt           ; continue the line
ex_let_err:
                pop     bc
                jp      stmt_error

; --- ex_let_str: string-variable assignment  A$ = <string operand> -----------
; HL is on the name's first letter (var_str_type did not advance it). Parse the
; name + `$` for the destination key, the '=' token, then evaluate the RHS
; string operand into STRPTR and copy it into the variable's slot.
ex_let_str:
                call    var_name_key        ; BC = dest key, HL past name + `$`
                push    bc                  ; save key across '=' + str_eval
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' -> $EF
                jr      nz,ex_let_err
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> RHS descriptor, HL advanced
                jr      nc,els_err          ; not a string operand -> syntax error
                pop     bc                  ; BC = dest key
                push    hl                  ; guard cursor across str_set_key
                ld      de,(STRPTR)         ; DE -> source descriptor
                call    str_set_key         ; A$[key] := descriptor (clamped)
                pop     hl
                jp      exec_stmt
els_err:
                pop     bc
                jp      stmt_error

; --- skip_spaces: advance HL past 0x20 bytes -------------------------------
skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      skip_spaces

; --- stmt_error: unknown statement — report and return to the prompt -------
stmt_error:
                xor     a                   ; an error mid-PRINT# must reach the
                ld      (PRDEST),a          ; screen, not the half-written file
                ld      a,$DD               ; distinct from BLOAD's $EE tape error
                ld      (ERRMARK),a
                ld      hl,err_syntax
                call    print_string
                ret
err_syntax:
                db      "syntax error",13,10,0

; --- ex_letkw: optional LET keyword before an assignment -------------------
ex_letkw:
                inc     hl                  ; past the LET token
                call    skip_spaces
                jp      ex_let              ; reuse <letter> = <expr>

; --- ex_goto: GOTO <line> --------------------------------------------------
; The target is the line-number reference $0E,<lineno LE> (the tokeniser emits
; this for a number after GOTO/THEN). Resolves it to the line's address, parks it
; in GOTOTGT and raises GOTOFLAG; the RUN loop performs the branch. `ex_goto_at`
; is the same with HL already on the $0E token (used by IF…THEN <line>).
ex_goto:
                inc     hl                  ; past the GOTO token
ex_goto_at:
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN        ; $0E expected
                jp      nz,stmt_error
                inc     hl
                ld      c,(hl)              ; target line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl
                call    find_line_bc        ; CF set + HL = line addr if found
                jr      nc,ex_goto_undef
                ld      (GOTOTGT),hl
                ld      a,1
                ld      (GOTOFLAG),a
                ret
ex_goto_undef:
                ld      a,$DB               ; "undefined line" landmark
                ld      (ERRMARK),a
                ld      hl,err_line
                jp      print_string
err_line:
                db      "undefined line",13,10,0

; --- ex_if: IF <expr> THEN <clause> [ELSE <clause>] ------------------------
; A clause is either a line number (implicit GOTO) or statements. Condition is
; true when the expression is non-zero (no comparison operators yet).
ex_if:
                inc     hl                  ; past the IF token
                call    skip_spaces
                call    eval                ; DE = condition, HL after expr
                call    skip_spaces
                ld      a,(hl)
                cp      THEN_TOKEN
                jr      z,if_then
                cp      GOTO_TOKEN          ; allow `IF <expr> GOTO <line>`
                jr      z,if_goto_form
                jp      stmt_error
if_goto_form:
                ld      a,d                 ; condition true?
                or      e
                jr      z,if_false
                jp      exec_stmt           ; true: let exec run the GOTO at HL
if_then:
                inc     hl                  ; past THEN
                call    skip_spaces
                ld      a,d                 ; condition true?
                or      e
                jr      z,if_false
                ld      a,(hl)              ; true: line number -> GOTO, else run
                cp      LINENO_TOKEN
                jr      z,if_branch
                jp      exec_stmt
if_branch:
                jp      ex_goto_at          ; HL on $0E -> conditional GOTO
if_false:
                call    if_skip_to_else     ; scan to ELSE token or end of line
                or      a
                ret     z                   ; no ELSE -> line done
                inc     hl                  ; past the ELSE ($A1) token
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN
                jr      z,if_branch
                jp      exec_stmt           ; ELSE <statements>

; --- if_skip_to_else: token-aware scan to the ELSE token or EOL -------------
; out: HL on the $A1 ELSE token (A = $A1) or on the 0 terminator (A = 0).
; Steps over operand bytes so a value that happens to equal $A1/$00 is not
; mistaken for a delimiter.
if_skip_to_else:
                ld      a,(hl)
                or      a
                ret     z                   ; end of line
                cp      ELSE_TOKEN
                ret     z                   ; ELSE found
                call    tok_skip
                jr      if_skip_to_else

; --- tok_skip: advance HL past one token, including its operand bytes -------
tok_skip:
                ld      a,(hl)
                inc     hl
                cp      HEX_TOKEN           ; $0C ,word
                jr      z,tsk2
                cp      INT2_TOKEN          ; $1C ,word
                jr      z,tsk2
                cp      LINENO_TOKEN        ; $0E ,word
                jr      z,tsk2
                cp      LINEADDR_TOKEN      ; $0D ,word
                jr      z,tsk2
                cp      OCT_TOKEN           ; $0B ,word
                jr      z,tsk2
                cp      INT1_TOKEN          ; $0F ,byte
                jr      z,tsk1
                cp      PEEK_PREFIX         ; $FF ,function-token byte
                jr      z,tsk1
                cp      '"'                 ; string literal
                jr      z,tsk_str
                cp      REM_TOKEN           ; REM -> rest of line
                jr      z,tsk_rem
                cp      DATA_TOKEN          ; DATA -> verbatim body to ':' / EOL
                jr      z,tsk_data
                ret                         ; 0-operand token / plain byte
tsk1:
                inc     hl
                ret
tsk2:
                inc     hl
                inc     hl
                ret
tsk_str:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                cp      '"'
                jr      nz,tsk_str
                ret
tsk_rem:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                jr      tsk_rem
tsk_data:                                   ; DATA body: verbatim ASCII to ':' or EOL,
                ld      a,(hl)              ; left un-consumed (the ':' / 00 is stepped by
                or      a                   ; the caller's outer loop). Skipping the body
                ret     z                   ; as a unit means a stray control byte in it
                cp      COLON               ; can never be misread as an operand-bearing
                ret     z                   ; token — same end position as the old
                inc     hl                  ; byte-by-byte walk on valid printable DATA.
                jr      tsk_data

; --- skip_to_eol: HL at a token body -> HL just past the line's 00 terminator -
; Token-aware (steps whole tokens via tok_skip), so an operand byte equal to 00
; (e.g. the low byte of &HD000 -> $0C $00 $D0) is not mistaken for the
; terminator. Used to find a stored line's length and its next-line address.
skip_to_eol:
                ld      a,(hl)
                or      a
                jr      z,ste_done
                call    tok_skip
                jr      skip_to_eol
ste_done:
                inc     hl                  ; advance past the 00 terminator
                ret
