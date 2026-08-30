; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; tokenise.inc — the tokeniser body (crunch ASCII line -> token stream).
; ===========================================================================
; Extracted from interp.asm so its PLACEMENT could be moved (subrom arc, wave 2,
; docs/spec-basic-subrom-wave2-tokeniser.md). Home:
;   * sub-ROM (sub/sub.asm): the WHOLE body is evicted to sub-ROM
;     page 0, reunited with the tk_float literal crunch (sub/tkfloat.asm) that
;     wave 1 already moved there. The repack MAIN ROM keeps only a two-line
;     `tokenise` dispatch stub (interp.asm) that CALSLTs this body once per line.
;
; Cold path: this runs only at line-entry / program-LOAD, never during RUN (the
; executor walks already-crunched tokens), so it fits the sub-ROM's page-0 tenant
; rule — pure buffer computation over page-2/3 RAM, no BIOS / low-region / ISR
; touch (leaf-audit, spec §3). The only non-RAM callees are pure leaves cloned
; sub-side: upcase (sub/tkfloat.asm), is_letter (sub/sub.asm — the is_ident_cont
; clone that used to sit beside it went away with D-CNAME's CALL device-name
; range test, its last sub-side caller: docs/spec-basic-cname.md §3.1), and
; tk_float itself, now an in-slot jump to the co-located crunch.
;
; Derived only from this project's own black-box oracle observations
; (basic-spec/docs/spec-tokenise.md, spec-tokens-statements.md) and the public
; MSX-BASIC language reference. No disassembly.
; ===========================================================================

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
                ld      (TKLNUM),a          ; ...and outside line-number mode (D-LNLIST
                                            ; R-L1, docs/spec-basic-lnlist.md)
                ld      (TKVALEND),a        ; D-VALFLOAT: ordinary tokenising is
                ld      (TKVALEND+1),a      ; ALWAYS unbounded -- only VAL, which
                                            ; enters tk_float directly, ever sets a
                                            ; bound, and clearing it here means RAM
                                            ; garbage at cold boot cannot fake one
                ld      (TKOVF),a           ; ...and no crunch-time reject yet (F1,
tk_loop:
                ld      a,(TKNAME)
                ld      b,a                 ; B = were we inside a name? (digit rule)
                xor     a
                ld      (TKNAME),a          ; default after this char: not in a name
                ld      a,(hl)
                or      a
                jp      z,tk_end
                ; D-NAMBLANK R-N1 (docs/spec-basic-nameblank.md): a blank is
                ; COPIED but changes NO state, so the in-a-name flag survives a
                ; run of blanks and the digit behind it still CONTINUES the name.
                ; `20 A=B1 1` is the single identifier B11 on the VG-8020 and the
                ; CF-3300 alike, and `20 B1 1=7` is readable back through `B11`.
                ; Tested HERE, before match_kw: B is only known-live ahead of that
                ; call (§4.3), and a blank matches no keyword and no operator, so
                ; short-circuiting past them is behaviour-neutral (knife K4).
                cp      ' '                 ; (`jp`, not `jr`: tk_blank sits past
                jp      z,tk_blank          ;  tk_copy_up, out of relative range)
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
                ; D-LNLIST R-L2 (docs/spec-basic-lnlist.md): inside line-number
                ; mode a digit run that would BEGIN a numeric constant begins a
                ; line-number REFERENCE instead. `20 GOTO 1+5` is TWO $0E
                ; references on the VG-8020 and the CF-3300 alike -- the mode
                ; runs to the end of the STATEMENT, so the '.' the TODO filed
                ; this under was never the subject (spec §1).
                ld      a,(TKLNUM)
                or      a
                jp      nz,bl_num           ; -> $0E,<line LE>, then back here
                jp      tk_float            ; '0'..'9' starting a numeric constant
                                             ; (float-aware, basic/float.asm)
tk_namedig:
                ld      a,1
                ld      (TKNAME),a          ; the digit (or a '.', D-NAMDOT R-D1)
                                            ; extends the name
                ld      a,(hl)              ; copy it verbatim
                ld      (de),a
                inc     de
                inc     hl
                jp      tk_loop
tk_nondigit:
                cp      '.'
                jr      nz,tk_nondot
                ; D-NAMDOT (docs/spec-basic-namedot.md). TWO rules meet in these
                ; four instructions, and the one-character lookahead that used to
                ; stand here is gone because BOTH of them delete it.
                ;
                ; R-D1: a '.' behind a LIVE name state CONTINUES the identifier.
                ; `20 A=B.5` is the variable B.5 on the VG-8020 and the CF-3300
                ; alike -- a row with NO BLANK IN IT, which is why D-NAMBLANK
                ; filed this separately instead of folding it into the blank rule
                ; (docs/nameblank-msx1-characterization.md §3). B is the in-a-name
                ; state loaded at the top of tk_loop, and it is only known-live
                ; AHEAD of match_kw (line 103) -- the identical liveness argument
                ; D-NAMBLANK's K4 established for tk_blank.
                ;
                ; R-D2: with the state DEAD the '.' begins a numeric constant AND
                ; THE DIGIT IS OPTIONAL -- a bare '.' is the single-precision
                ; literal 0. `20 A=.B` stores $1D,0,0,0,0 then `B` on both
                ; references; zerobas stored `.B` verbatim. 🔴 THAT ROW WAS
                ; WRITTEN TO BE A TWO-SIDED CONTROL and it refuted its own
                ; prediction, which is what turned "a '.'+digit leads a literal"
                ; into "a '.' leads a literal" (characterization §3).
                ;
                ; ⚠️ tk_namedig is REUSED, not cloned: it already stores TKNAME=1,
                ; copies (HL) verbatim and returns to tk_loop, which is exactly
                ; what a '.' inside a name must do. And the jump is BACKWARD into
                ; an existing label rather than a new label parked in front of
                ; one -- the check D-NAMBLANK's K2 had to find the hard way, on a
                ; build that read 29/31 green by LUCK (spec §3).
                ;
                ; ⚠️ The deleted lookahead was tkf_fetch's only caller outside
                ; sub/tkfloat.asm; four callers remain there, so the hard
                ; dead-code gate still sees it live.
                ld      a,b                 ; were we inside a name?
                or      a
                jr      nz,tk_namedig       ; R-D1: the dot extends the name
                ; D-LNLIST R-L2: line-number mode SUPPRESSES R-D2. `20 GOTO .5`
                ; stores the value 5 (`<89> .<0E><05><00>`) and `20 GOTO .` stores
                ; a bare '.', where R-D2 alone would make each of them the
                ; single-precision literal 0. The dot is copied verbatim and the
                ; digit run behind it is its OWN line-number reference.
                ld      a,(TKLNUM)
                or      a
                jp      nz,tk_copy
                jp      tk_float            ; R-D2: no digit required (sub/tkfloat.asm)
tk_nondot:
                cp      '&'                 ; "&H" hex constant
                jp      z,tk_hex
                call    match_kw            ; keyword match runs at EVERY position, so
                jr      nc,tk_notkw         ; reserved words inside a name still tokenise
                                            ; (SCORE -> SC,OR,E); TKNAME stays 0 here, so
                                            ; a keyword correctly breaks the name.
                ; D-LNLIST R-L3: a reserved WORD disarms line-number mode --
                ; `20 GOTO 1 AND 5` keeps its 5 as <16>, and `20 IF A THEN PRINT 5`
                ; would otherwise crunch its 5 as a LINE NUMBER. branch_lineno
                ; re-arms below for the FOURTEEN that take one (D-LNREF R-R1,
                ; completed by D-KWGAP4 R-K2 -- the count was "six" until D-LNREF
                ; walked all 162 reserved words).
                ;
                ; ⚠️ THE CLEAR LIVES HERE AND NOT INSIDE branch_lineno, and the
                ; three lines below are why: REM, DATA and CALL are dispatched
                ; BEFORE that call, so a clear inside it would never see them.
                ; `20 IF A THEN CALL X(5)` stores `<CA> X(<16>)` on both
                ; references -- a '(' leaves the mode armed (lnl-paren), so it is
                ; the CALL token that cleared it. Knife K3 aims here.
                push    af                  ; A = the token byte, live for the tests
                xor     a
                ld      (TKLNUM),a
                pop     af
                cp      REM_TOKEN           ; REM swallows the rest of the line
                jp      z,tk_rem_rest
                cp      DATA_TOKEN          ; DATA body is stored verbatim (to ':')
                jp      z,tk_data_rest
                cp      CALL_TOKEN          ; CALL <name>: the device name is verbatim
                jp      z,tk_call_name      ; (oracle: `call format` keeps "FORMAT", not
                                            ;  FOR+MAT — the extended name is not crunched)
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
                ; math pack slice 2c (docs/spec-basic-mathpack-slice2.md
                ; §13.3): '^' -> POW_TOKEN.
                cp      '^'
                jp      z,tk_op_pow
                cp      '?'                 ; '?' abbreviates PRINT
                jp      z,tk_print_q
                cp      '_'                 ; '_' abbreviates CALL: the name is verbatim
                jp      z,tk_underscore
                call    is_letter           ; a letter starts / continues a name
                jr      c,tk_copy_up
tk_copy:
                ld      a,(hl)              ; punctuation: copy verbatim
                ld      (de),a
                inc     de
                inc     hl
                ; D-LNLIST R-L3: the statement separator disarms line-number mode.
                ; `20 GOTO 1:5` stores $0E,0001 then ':' then <16> on both
                ; references -- and `lnl-colsep` is the row that says so, because
                ; `20 GOTO 1.5:A=7` cannot: the `A` behind its colon is a NAME,
                ; which disarms the mode on its own (spec §2, characterization §2).
                ;
                ; ⚠️ TESTED AFTER THE COPY, ON THE CHARACTER ALREADY IN A. tk_copy
                ; is the FALLTHROUGH target of the is_letter test above, and
                ; D-NAMBLANK's K2 is the standing record of what a careless store
                ; in front of it costs -- a build that read 29/31 green BY LUCK.
                ; Nothing here reloads A or touches B, and `ld (de),a`/`inc` leave
                ; the flags alone, so the `cp` still sees the copied byte.
                cp      COLON
                jp      nz,tk_loop
                xor     a
                ld      (TKLNUM),a
                jp      tk_loop
tk_copy_up:
                ld      a,(hl)              ; a name letter, upcased (§4)
                call    upcase
                ld      (de),a
                inc     de
                inc     hl
                ld      a,1
                ld      (TKNAME),a          ; now inside a name
                ; D-LNLIST R-L3: a variable NAME disarms line-number mode, exactly
                ; as a reserved word does -- `20 GOTO X,5` stores `<89> X,<16>`
                ; with no $0E anywhere. Only the leading LETTER needs this:
                ; tk_namedig is reachable only once a name is already open, so it
                ; has always run through here first.
                xor     a
                ld      (TKLNUM),a
                jp      tk_loop
; ⚠️ tk_blank LIVES HERE, NOT NEXT TO tk_copy, AND THAT IS NOT COSMETIC. tk_copy
; is entered by FALLTHROUGH from the `is_letter` test above, so a tk_blank
; placed just before it silently puts EVERY punctuation character through this
; store -- reading a `B` that `match_kw` (line 103) has already clobbered.
; Knife K2 caught it: `20 A=B$1`, which contains no blank at all, kept its digit
; verbatim. The unknifed build read green on all 31 rows by LUCK, on whatever B
; match_kw happened to leave behind (docs/spec-basic-nameblank.md §4.3/§5).
tk_blank:                                   ; a blank: the name survives it (R-N1),
                ld      a,b                 ; and the blank itself is still copied
                ld      (TKNAME),a          ; verbatim -- `20 A= 1` keeps its blank
                jp      tk_copy             ; AND still crunches the 1 (nam-eqnum)
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
tk_underscore:                              ; '_' (CALL abbreviation): copy it, then the
                ; D-LNLIST R-L3, the second symbol that expands to a word token.
                ; `20 IF A THEN _X(5)` stores `_X(<16>)` on both references, like
                ; the spelled-out CALL -- and like '?', '_' never enters match_kw,
                ; so it needs its own clear. Knife K7.
                xor     a
                ld      (TKLNUM),a
                ld      a,(hl)              ; device name verbatim (no keyword crunch).
                ld      (de),a
                inc     de
                inc     hl
                ; fall through into tk_call_name
tk_call_name:                               ; the extended-statement device name.
                ; D-CNAME (docs/spec-basic-cname.md). ⚠️ THIS IS A RANGE TEST, NOT
                ; AN IDENTIFIER SCAN, and the two-phase "blanks first, then a
                ; name" shape this replaced was itself the bug: a blank is not a
                ; prologue, it is an ordinary STORED character that the scan runs
                ; straight past (`20 CALL X Y` is the ONE name `X Y`).
                ;
                ; R-C1: the scan ends at EOL, ':' or '(' -- and at NOTHING else.
                ; The terminator is left for the ordinary crunch, which is why
                ; `20 CALL X(5)` stores the '(' and crunches its 5 (<16>, not
                ; ASCII) and why `20 CALL X:PRINT 5` has a second statement.
                ; R-C2: a character in $21..$2F is DISCARDED and the scan
                ; CONTINUES. All fifteen of that range were walked contiguously
                ; ('(' is the one exception, above) -- a denominator, not a
                ; sample, and it had to be walked because the operators land on
                ; BOTH sides: '+' '-' '*' '/' are dropped and '^' '\' '=' '<' '>'
                ; are kept, so no property of the TOKEN separates them
                ; (characterization §2). The three rows that filed this defect
                ; agree with two rules that are both refuted here.
                ; R-C3: everything else is STORED -- letters upcased, the rest
                ; verbatim, INCLUDING the blank. No keyword crunch (oracle:
                ; `call format` -> CA 20 46 4F 52 4D 41 54, not FOR+MAT), no
                ; numeric crunch, and no length bound (26 chars measured).
                ;
                ; ⚠️ EOL IS TESTED FIRST AND MUST BE. $00 is below '0', so
                ; without the `or a` it would take the R-C2 skip path and the
                ; `inc hl` would run PAST the line terminator. Knife K7 defeats
                ; exactly this test and the MACHINE DOES NOT SURVIVE: run alone,
                ; `20 CALL X` is NOCAPTURE while `20 CALL X(5)` -- whose scan
                ; ends at the '(' -- still reads correctly (spec §7).
                ; ⚠️ TKNAME is deliberately NOT touched, exactly as before: it is
                ; cleared at the top of tk_loop before the CALL token matched and
                ; this scan never re-enters tk_loop, so the 5 behind a '(' or ':'
                ; still BEGINS a numeric constant (cnm-par, cnm-colon).
                ld      a,(hl)
                or      a
                jp      z,tk_loop           ; R-C1: EOL (tk_loop reaches tk_end)
                cp      COLON               ; R-C1: ':' ends the scan
                jp      z,tk_loop
                cp      '('                 ; R-C1: '(' ends the scan
                jp      z,tk_loop
                cp      ' '                 ; R-C3: the blank is STORED
                jr      z,tcn_store
                cp      '0'                 ; R-C2: $21..$2F is DISCARDED
                jr      c,tcn_skip
tcn_store:
                call    upcase              ; R-C3 (upcase touches $61..$7A only,
                ld      (de),a              ;  so '`' and '~' pass through)
                inc     de
tcn_skip:
                inc     hl
                jr      tk_call_name
tk_end:
                xor     a
                ld      (de),a              ; 0x00 terminator
                ; D-LINEMAX R-2 (docs/spec-basic-linemax.md §2): the crunch is BOUNDED.
                ; Refuse a body longer than TOKMAX_BODY (314) -- the reference's measured
                ; ceiling, where it prints `Line buffer overflow` and stores nothing
                ; (characterization §2: 314 accepted / 315 refused, walked a byte at a
                ; time). TKOVF=25 is the reject reason AND the ERR code; dispatch_line
                ; adjudicates it at line ENTRY, exactly like the =6 float-literal
                ; reject, so an over-long line is never executed and never stored.
                ; (This comment read "TKOVF=2 ... the =1 float-literal reject" until
                ; 2026-08-02: the 2 was never right, and the 1 was the defect
                ; D-MSGMIGRATE measured -- see sub/tkfloat.asm tkf_overflow.)
                ;
                ; ONE site, at the true end of the crunch, and that is deliberate: the
                ; verbatim inner loops (tk_str_loop / tk_rem_rest / tk_data_rest) never
                ; re-enter tk_loop, so a per-character test at the loop head would MISS
                ; them. They are 1:1 and LINEMAX-bounded, so TOKBUF absorbs the overshoot
                ; (sysvars.inc) and the adjudication happens here, where the body length
                ; is final and the bound is provable rather than audited.
                push    hl                  ; HL = source cursor; callers don't read it,
                                            ; but tokenise's contract doesn't promise it
                ld      hl,-(TOKBUF+TOKMAX_BODY+1)
                add     hl,de               ; CF <=> DE >= TOKBUF+315, i.e. body > 314
                pop     hl                  ; (pop preserves flags)
                jr      nc,tke_fits
                ld      a,(TKOVF)           ; FIRST reject wins: sub/tkfloat.asm sets =6
                or      a                   ; mid-line and jumps straight here, and that
                jr      nz,tke_fits         ; overflow happened BEFORE the body ran long
                ld      a,25                ; the reject reason IS the ERR code (=25), so
                ld      (TKOVF),a           ; dispatch_line needs no second constant --
                                            ; page-1 room, see program.asm dl_overflow
tke_fits:
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
                ; D-LNLIST R-L3, and this is the site rule "clear on match_kw"
                ; alone gets WRONG. '?' is a SYMBOL that expands to a WORD token,
                ; so it never enters match_kw -- but `20 IF A THEN ?5` stores
                ; `<91><16>` on both references, exactly as the spelled-out PRINT
                ; does. It cannot share tk_op_emit's path, because the symbolic
                ; operators that DO go there ($EE..$F5, $FC) must leave the mode
                ; ARMED (`20 GOTO 1+5` is two $0E references). Knife K5.
                xor     a
                ld      (TKLNUM),a
                ld      a,PRINT_TOKEN
                jr      tk_op_emit
tk_op_div:
                ld      a,DIV_TOKEN
                jr      tk_op_emit
tk_op_idiv:
                ld      a,IDIV_TOKEN
                jr      tk_op_emit
tk_op_pow:
                ld      a,POW_TOKEN
                jr      tk_op_emit


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

; --- branch_lineno: ARM line-number mode after a branch keyword --------------
; A = first token byte just emitted by match_kw. If the keyword was one of the
; FOURTEEN measured arming words, arm TKLNUM (D-LNLIST R-L1); otherwise return
; unchanged. HL/DE are not touched — the mode does its work back in tk_loop, one
; character at a time.
;
; The list is GOTO GOSUB THEN RESTORE RUN RESUME (D-LNLIST) + LIST RETURN ERL
; ELSE (D-LNREF R-R1) + LLIST DELETE AUTO RENUM (D-KWGAP4 R-K2), and it is a
; LIST rather than a range or a threshold — measured over the whole 162-word
; denominator, docs/lnref-msx1-characterization.md §1.1. ELSE is reached by its
; FIRST token byte, which is COLON (R-R2).
;
; 🔴 THIS ROUTINE USED TO WALK THE LIST ITSELF AND NO LONGER DOES. It copied a
; run of blanks, took one number, then looked for a ',' to continue with —
; a design that could only ever be as wide as its separator set, and the measured
; reference has no separator set at all: after a branch keyword EVERY digit run in
; the statement is a line-number reference, whatever stands between them
; (`20 GOTO 1+5` -> $0E,0001 <F1> $0E,0005; `20 GOTO 1.5.7` -> three of them).
; So bl_yes' blank loop, bl_num's comma test and bl_list are DELETED: ordinary
; tk_loop already copies blanks, commas and punctuation verbatim, which is
; exactly what the old code was hand-rolling.
;
; ⚠️ THE EMPTY-SLOT BUG bl_num's comment recorded is fixed by that deletion, not
; regressed by it. `ON KEY GOSUB 100,,600` now works because the ',' characters
; are simply copied and the 600 is still inside the mode — there is no list walk
; left to fall off the end of. `lnl-empty`/`lnl-empty2` pin both shapes, and the
; T2/T3 trap gates (which parse for $0E) are the ones that say so at run time.
;
; ⚠️ bl_acc..bl_done SURVIVES UNCHANGED, D-LNBLANK R5 included: it is now entered
; from tk_loop's digit arm instead of from here, and returns there instead of
; looping for a comma. It remains a SECOND COPY of program.asm's parse_lineno,
; deliberately — the two live in different ROMs.
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
                cp      RESUME_TOKEN        ; RESUME <line> / RESUME 0 (error-handling S2b,
                jr      z,bl_yes            ; repack-only): crunch the following number as
                                            ; $0E, like GOTO. RESUME NEXT / bare RESUME are
                                            ; unaffected (no digit follows, so the
                                            ; mode simply never fires).
                ; D-LNREF R-R1 (docs/spec-basic-lnref.md §2): FOUR more, measured by
                ; walking all 162 reserved words rather than reading a filed list --
                ; which named five verbs, three of which zerobas has no token for and
                ; missed these two entirely (docs/lnref-msx1-characterization.md §1).
                ;
                ; 🔴 THE SET IS A LIST AND CANNOT BE A RANGE OR A THRESHOLD. Every
                ; arming token has a NON-arming neighbour: IF ($8B) sits between GOTO
                ; ($89) and RETURN ($8E); ERROR ($A6) abuts RESUME ($A7); TO ($D9)
                ; abuts THEN ($DA); ERR ($E2) abuts ERL ($E1). The ten `cp`s ARE the
                ; rule. (A cpir over a 10-byte table would save ~18 B and would stop
                ; reading as the measured set; sub page 0 is not the wall.)
                cp      LIST_TOKEN          ; LIST [<line>[-<line>]] -- the args are still
                jr      z,bl_yes            ; ignored (ex_list), but the BYTES are the
                                            ; reference's and LIST round-trips them
                cp      RETURN_TOKEN        ; RETURN <line> -- the STATEMENT is still
                jr      z,bl_yes            ; unimplemented (ex_return ignores its
                                            ; argument, lnrd-return); this is the crunch
                cp      ERL_TOKEN           ; IF ERL=<line> -- the $0E lands inside an
                jr      z,bl_yes            ; EXPRESSION, which is why ev_f grew the
                                            ; $0B..$0E range (basic/expr.asm, R-E)
                ; R-R2: ELSE crunches to COLON,$A1 and match_kw hands us the FIRST
                ; token byte, so the test is `cp COLON`. Safe because branch_lineno is
                ; reached ONLY from the match_kw success path and "ELSE" is the only
                ; kwtable.inc entry whose first token byte is COLON -- tk_apos writes
                ; its own COLON without coming through here, and a bare ':' typed in a
                ; statement is copied by tk_copy, which CLEARS the mode. `lnl-colsep`
                ; (`20 GOTO 1:5` -> `<89> <0E><01><00>:<16>`) is the cell that says so;
                ; knife K3 moves this test into tk_copy and reddens exactly that row.
                cp      COLON               ; ELSE <line> -- if_false (basic/interp.asm)
                jr      z,bl_yes            ; has ALWAYS tested for the $0E this emits;
                                            ; without it `IF 0 THEN 20 ELSE 30` is a
                                            ; Syntax error (lnrd-else)
                ; D-KWGAP4 R-K2 (docs/spec-basic-kwgap4.md §2): the last FOUR of
                ; R-R1's fourteen. D-LNREF measured that these arm and deliberately
                ; left them out, because zerobas had no kwtable.inc entry for any of
                ; them and a test no row could exercise is not a rule -- it pinned
                ; lnrx-delete/-auto/-renum/-llist and ref-delete/-auto/-renum as
                ; KNOWN_DIVERGE instead, so that adding the keywords WITHOUT these
                ; four lines could not pass. The entries landed; these are their arms.
                ;
                ; 🔴 $A7..$AA IS NOW A CONTIGUOUS ARMING RUN (RESUME/DELETE/AUTO/
                ; RENUM) AND IT STAYS FOUR SEPARATE `cp`s ANYWAY. A range test would
                ; save 8 B and would express a rule the 162-word walk REFUTES: the
                ; arming set is a LIST, with a non-arming neighbour on at least one
                ; side of every boundary (ERROR $A6 under RESUME $A7, DEFSTR $AB over
                ; RENUM $AA, IF $8B sitting BETWEEN four arming tokens). A range would
                ; also silently arm any byte later added inside the span. Sub page 0
                ; is not the wall; the 8 B buy nothing. Knife K6 records that this
                ; corpus CANNOT tell the two apart -- the walk is the evidence, not a
                ; red row.
                ;
                ; ⚠️ NONE OF THE FOUR HAS A stmt_table ROW. The crunch is faithful;
                ; the STATEMENTS are filed (spec §3.4) -- kwgd-delete / kwgd-renum are
                ; pinned so the day one lands, the gate says so.
                cp      LLIST_TOKEN         ; LLIST [<line>[-<line>]]
                jr      z,bl_yes
                cp      DELETE_TOKEN        ; DELETE <line>[-<line>]
                jr      z,bl_yes
                cp      AUTO_TOKEN          ; AUTO [<start>][,<inc>] -- the INCREMENT
                jr      z,bl_yes            ; is stored as $0E as well (lna-auto2):
                                            ; nothing here knows what the digits MEAN
                cp      RENUM_TOKEN         ; RENUM [<new>][,[<old>][,<inc>]]
                jr      z,bl_yes
                ret                         ; not a branch keyword
bl_yes:
                ld      a,1                 ; R-L1: arm line-number mode
                ld      (TKLNUM),a
                ret
bl_num:
                ; Entered from tk_loop's digit arm with the mode ARMED and HL on
                ; the first digit; nothing here needs to test for one. The digit
                ; gate, the ',' test and the bl_list continuation loop that used
                ; to stand here are gone with the list walk (see the header):
                ; tk_loop copies a ',' verbatim like any other punctuation and the
                ; next digit run re-enters here on its own, which is what makes
                ; `ON KEY GOSUB 100,,600` and `ON STRIG GOSUB ,300` work without a
                ; special case for an empty slot.
                push    de                  ; park dest while accumulating
                ld      de,0                ; DE = value
bl_acc:
                ; D-LNREF R-V (docs/spec-basic-lnref.md §2): a reference takes another
                ; digit only while the value would stay <= LINENO_CEIL. The digit that
                ; would exceed it is NOT consumed -- the reference ends and, the mode
                ; still being armed (D-LNLIST R-L2), that digit begins a NEW one.
                ; `GOTO 99999` is $0E,9999 then $0E,9 on both references; zerobas used
                ; to wrap at 16 bits and store line 34463, silently.
                ;
                ; 🔴 TESTED HERE, BEFORE THE CHARACTER IS FETCHED, AND THAT PLACEMENT
                ; IS A MEASUREMENT. D-LNBLANK R5's blank lookahead below commits to a
                ; whole run of blanks the moment it sees a digit past it, so a ceiling
                ; tested ON THE DIGIT has already swallowed the blank -- and
                ; `20 GOTO 6 5 5 3 0` KEEPS its blank between the two references on
                ; both machines (`<0E><99><19>` ' ' `<0E><00><00>`, lnv2-blk30). Knife
                ; K5 moves the test down and reddens exactly that one row.
                ;
                ; The bound is the accumulator's, not the value's: see LINENO_ACC_STOP
                ; (basic/sysvars.inc). Knives K6/K7 bracket it from both sides.
                ld      a,d
                cp      high LINENO_ACC_STOP
                jr      c,bl_ac_char
                jr      nz,bl_done
                ld      a,e
                cp      low LINENO_ACC_STOP
                jr      nc,bl_done
bl_ac_char:
                ld      a,(hl)
                cp      '0'
                jr      c,bl_ac_blank
                cp      '9'+1
                jr      nc,bl_ac_blank
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
bl_ac_blank:
                ; D-LNBLANK R5: a blank INSIDE a line-number reference is
                ; transparent, exactly as in the leading line number -- `GOTO 1 0`
                ; crunches to $0E,$000A, byte-identical to `GOTO 10`, on both
                ; references. zerobas emitted $0E,$0001 and then crunched ` 0` as a
                ; separate literal, so `GOTO 1 0` branched to line 1.
                ;
                ; ⚠️ Like parse_lineno's copy, the run is only transparent when it
                ; ENDS IN A DIGIT: blanks BEFORE the number are copied verbatim by
                ; bl_yes and survive in the crunched bytes (`GOTO   10` keeps all
                ; three), and so must a run that merely trails the number. Commit to
                ; the run only after looking past it.
                ;
                ; This is a SECOND COPY of parse_lineno's logic and deliberately so:
                ; the two live in different ROMs (this body is evicted to the sub-ROM,
                ; program.asm stays in the main), so no call could be shared even if
                ; the down-payment were worth it at two callers.
                cp      ' '
                jr      nz,bl_done
                push    hl
bl_ac_lp:
                inc     hl
                ld      a,(hl)
                cp      ' '
                jr      z,bl_ac_lp
                cp      '0'
                jr      c,bl_ac_end
                cp      '9'+1
                jr      nc,bl_ac_end
                pop     af                  ; a digit follows -> keep the advanced HL
                jr      bl_acc
bl_ac_end:
                pop     hl                  ; the run is not ours; bl_yes copies it
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
                ; 🔴 A BLANK BEFORE THE COMMA USED TO END THE LIST, and then a
                ; `jr bl_yes` here went back to re-copy blanks and look for the
                ; next ',' (D-LNBLANK's `ref-oncomma`). Both the bug and its fix
                ; are dissolved rather than kept: there is no list to continue, so
                ; this returns to the ordinary loop and whatever stands between two
                ; numbers -- blanks, a comma, an operator, a '.' -- is copied by the
                ; code that already knew how. The mode is still armed, so the next
                ; digit run comes straight back here.
                jp      tk_loop
