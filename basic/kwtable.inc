; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; kwtable.inc — the keyword -> token crunch table (extracted from interp.asm).
; ===========================================================================
; Clean-room: the tokens are ORACLE-SOURCED, not lifted -- each was read off a
; live VG-8020 by crunching the keyword and observing the bytes the machine
; stored (probes/basic/basic_probe_crunch.py, byte-identity verified). The
; table's layout is this project's own. Nothing here is derived from a
; disassembly or byte-copy of any reference ROM. Basis: basic/PROVENANCE.md.
; ===========================================================================
; Entry layout: [klen][UPPERCASE chars][tlen][token...]. Terminated by a 0 length
; byte. Tokens are oracle-sourced (spec-tokenise.md, spec-tokens-statements.md).
; PEEK is a two-byte function token ($FF $97).
;
; This table is DATA, reached only via `ld ix,kwtable` from match_kw (tokeniser)
; and detok_kw / detok_kw2 (LIST detokeniser) — all scan it linearly, so BOTH
; directions are data-driven off ONE table. It was extracted into its own file so
; its PLACEMENT could be moved (string-engine arc S3, spec §5b), first into the
; main ROM's reclaimed low region and then out of the main ROM entirely.
;
; ⚠️ HOME, AND THE OLD HEADER HERE NAMED THE WRONG ONE UNTIL D-KWGAP4. The
; resident copy was DROPPED in the sub-ROM arc's wave 3; `sub/sub.asm:355` is now
; the SOLE include site and the table is a sub-ROM PAGE-0 tenant. That is what
; makes an entry added here a sub-ROM change costing nothing on the main ROM's
; 9 B / 6 B walls — a fact worth having right, since it decides whether a new
; keyword is affordable at all. `tools/check_kwtable_identity.py` asserts
; single-copy on every build.
;
; match_kw compares the FULL table keyword against the input and takes the FIRST
; entry that matches — no longest-match, no word-boundary check — so table order
; is free EXCEPT where one keyword is a prefix of another (see the DEFINT/DEF note
; below, the only such pair in the table).
; ===========================================================================
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
                ; D-LFILES (docs/spec-basic-lfiles.md): FILES' printer twin. Token
                ; $BB oracle-locked from D-LNREF's crunch walk and equated since
                ; D-LPTVERB, which measured the verb in full and could not afford
                ; it. ⚠️ POSITION IS FREE BUT NOT OBVIOUSLY SO: "LFILES" CONTAINS
                ; "FILES", and this entry sits AFTER it. That is harmless because
                ; match_kw anchors at the input position it was called with and
                ; compares the FULL table keyword -- it is not a substring search --
                ; so at the 'L' of "LFILES" the "FILES" entry simply does not match
                ; and the scan continues to this one. The hazard match_kw DOES have
                ; is PREFIX (DEFINT/DEF), and neither word is a prefix of the other.
                ; Before this entry existed the sequence crunched as the variable
                ; `L` plus the genuine FILES token -- `L<B7>`, the same stray-letter
                ; shape LLIST and LPRINT had -- which is what `lnrx-lfiles` pinned.
                ;
                ; ⚠️ LIKE LPRINT AND UNLIKE THE FOUR EDITOR VERBS, LFILES DOES NOT
                ; ARM LINE-NUMBER MODE, so it needs no branch_lineno arm: its
                ; argument is a quoted filespec, never a line number.
                db      6,"LFILES",1,LFILES_TOKEN
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
                ; PUT crunches OUTPUT's 2nd half (OUT+PUT) and is the random-access
                ; PUT statement (slice 2 of 2c — no dispatch yet). Random-access
                ; record verbs (Phase 2c slice 1): FIELD/LSET/RSET. Tokens oracle-
                ; locked to the VG-8020 ($B1/$B8/$B9). match_kw is full-keyword, so
                ; order is free.
                db      3,"PUT",1,PUT_TOKEN
                db      3,"GET",1,GET_TOKEN
                db      5,"FIELD",1,FIELD_TOKEN
                db      4,"LSET",1,LSET_TOKEN
                db      4,"RSET",1,RSET_TOKEN
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
                ; D-MKSD: the FLOAT siblings. Until 2026-09-03 these four were
                ; absent from this table entirely, so `MKS$(1.5)` was not
                ; tokenised as a keyword at all -- it parsed as the string ARRAY
                ; `MKS$(1)` and answered 0. `kwsweep` calls that a SILENT-GAP,
                ; its own "worst kind", and could not see it either until
                ; D-KWORACLE fixed the second oracle's boot.
                ; Order is free here: match_kw is FULL-KEYWORD, not prefix.
                db      4,"MKS$",2,PEEK_PREFIX,MKS_TOKEN
                db      4,"MKD$",2,PEEK_PREFIX,MKD_TOKEN
                db      3,"CVS",2,PEEK_PREFIX,CVS_TOKEN
                db      3,"CVD",2,PEEK_PREFIX,CVD_TOKEN
                ; File management: KILL (delete) + NAME (rename). Oracle-locked
                ; tokens ($D4 / $D3). "NAME" shares no prefix with another entry.
                db      4,"KILL",1,KILL_TOKEN
                db      4,"NAME",1,NAME_TOKEN
                ; D-DONOTHING3: SET / IPL / CMD — reserved words in plain MSX
                ; BASIC (the DISKLESS VG-8020 reserves them too, measured), so
                ; they belong in the base table and not behind a disk switch.
                ; Tokenised here so the crunch matches the reference byte for
                ; byte; the statement handler is
                ; `gb_illegal`, because ERR 5 on sight IS the reference's verb.
                ; Order is free (match_kw is full-keyword), and "SET" cannot
                ; shadow LSET/RSET/PSET/PRESET for the same reason: the match
                ; starts at the current text position, which for those begins
                ; with L, R or P.
                db      3,"SET",1,SET_TOKEN
                db      3,"IPL",1,IPL_TOKEN
                db      3,"CMD",1,CMD_TOKEN
                ; D-ATTRFN: ATTR$ is the same class, but a FUNCTION — the
                ; handler is an `ev_f` arm rather than a stmt_table row.
                db      5,"ATTR$",1,ATTR_TOKEN
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
                db      5,"USING",1,USING_TOKEN
                db      4,"CALL",1,CALL_TOKEN
                db      3,"LET",1,LET_TOKEN
                ; Phase 1: CLEAR [<strings>][,<himem>] (MSX2 TH Table 2.20).
                db      5,"CLEAR",1,CLEAR_TOKEN
                ; Phase 1: DEF USR / USR + screen verbs (MSX2 TH Table 2.20).
                ;
                ; D-DEFINTTOK (2026-08-18): DEFINT gets its OWN single-byte
                ; token now, $AC (DEFINT_TOKEN, basic/sysvars.inc), matching
                ; the reference byte-for-byte: `20 DEFINT 10` crunches to
                ; `<AC> <0F><0A>` on the Philips VG-8020 (oracle-pinned,
                ; docs/lnref-msx1-characterization.md §4) and zerobas now
                ; agrees. `ex_deftype` (basic/usr.asm) is reached from this
                ; row's token and, since D-DEFTYPETOK, from the three rows below
                ; it as well -- ONE handler for all four verbs -- and hands the
                ; cursor to the SAME range-list parser (sub/deftype.asm
                ; deftype_tenant). There is no mnemonic-TEXT dispatch left
                ; anywhere on that path: with every DEF<type> carrying its own
                ; token, no caller could reach it, so it was DELETED rather than
                ; left unreachable (`make deadcode` fails a build that keeps
                ; unreachable code). The tenant recovers WHICH of the four this
                ; was by PEEKING at the byte one below the cursor it is handed --
                ; that byte IS the statement token, and $AB..$AE are contiguous
                ; by construction, so it indexes a 4-byte type-code table
                ; directly (no flag byte, no new ABI cell: main page 1 had no
                ; room for one) -- see ex_deftype's comment in basic/usr.asm for
                ; the measurement that ruled the ABI cell out.
                ;
                ; History, for anyone diffing against an old build: this row
                ; USED TO emit DEF_TOKEN + literal ASCII "INT" (four bytes, the
                ; same shape a plain "DEF" match followed by copying the next
                ; three letters would have produced) so the mnemonic parser in
                ; the then-`ex_def_type` (the routine D-DEFTYPETOK merged away
                ; into today's `ex_deftype`) could read it -- a deliberate
                ; regression-preserving workaround, not the reference's own byte
                ; shape. That was
                ; itself standing in for an even older bug: before this row
                ; existed at all, adding "INT" as a real keyword (math pack
                ; slice 1a) broke DEFINT, because match_kw's linear,
                ; boundary-free scan matched plain "DEF" (3 chars) first,
                ; leaving "INT A-Z" for the NEXT match_kw call to find, which
                ; (now that INT was a keyword) tokenised it to $FF $85 instead
                ; of leaving it as literal ASCII. Both of those are gone now:
                ; this row matches the WHOLE word and emits the real token
                ; directly, so there is no "DEF" + copied-suffix path left to
                ; collide with anything.
                ;
                ; ⚠️ STILL PLACED BEFORE THE PLAIN "DEF" ENTRY, AND STILL FOR
                ; THE SAME REASON. match_kw stops at the FIRST table entry
                ; that matches -- no longest-match, no word-boundary check --
                ; so with DEFINT's entry emitting its own token now, table
                ; order is MORE load-bearing than before, not less: if "DEF"
                ; were tried first it would match the first 3 characters of
                ; "DEFINT A-Z", tokenise to plain DEF_TOKEN, and leave "INT A-Z"
                ; for the next match_kw call to mis-tokenise via the real "INT"
                ; function keyword (exactly the math-pack-1a bug above, back
                ; from the dead).
                ;
                ; ⚠️ DEFSNG/DEFDBL/DEFSTR HAVE ROWS OF THEIR OWN NOW TOO (below),
                ; AND THE ORDERING RULE BINDS THEM EQUALLY -- BUT NOT FOR THIS
                ; REASON, AND THE DIFFERENCE IS WORTH KEEPING STRAIGHT. Those
                ; three genuinely do NOT collide: no "SNG"/"DBL"/"STR"-alone
                ; keyword exists -- only "CSNG"/"CDBL" do, both requiring a
                ; leading 'C' that DEF's suffix never has, and "STR$" needs a
                ; trailing '$' DEFSTR's suffix never has. So a plain "DEF" match
                ; followed by three copied letters could never MIS-CRUNCH those
                ; three the way it mis-crunches "INT" into $FF $85. DEFINT's row
                ; is therefore load-bearing against a WRONG TOKEN; theirs is not,
                ; and all three could have gone on working with no row at all.
                ;
                ; They were given rows anyway, because not colliding is not
                ; the same as being harmless -- and what the collision analysis
                ; does NOT cover is the state the copied letters leave BEHIND.
                ; S,T,R are copied as NAME letters, so TKNAME stays SET and the
                ; tokeniser is still inside an identifier when it reaches what
                ; follows the keyword. A row is what CLOSES that name. So the
                ; analysis above stands unchanged and still true; only the
                ; conclusion it used to carry -- "so they need no entry of their
                ; own" -- was wrong: right about collisions, silent about the
                ; argument bytes. The D-DEFTYPETOK block below, and
                ; todo-staleness-sweep-2026-08.md §4.11, carry the measured
                ; shapes.
                db      6,"DEFINT",1,DEFINT_TOKEN
                ; D-DEFTYPETOK (2026-08-19): DEFINT's three siblings, for the
                ; same reason and with the same oracle behind them ($AB/$AD/$AE,
                ; docs/lnref-msx1-characterization.md §4). Until now these had
                ; NO entry and fell to the plain "DEF" row + three copied ASCII
                ; letters -- which cost more than a wrong token byte: "STR" does
                ; not match STR$ (that needs a trailing '$'), so S,T,R were
                ; copied as NAME letters, TKNAME stayed SET, and the digits
                ; behind the keyword CONTINUED the name instead of starting a
                ; constant. That is why `20 DEFSTR 10` stored its argument as
                ; ASCII "10" (31 30) where the reference -- and DEFINT, which
                ; had a whole-word row -- store the int literal `0f 0a`
                ; (todo-staleness-sweep-2026-08.md §4.11). One row each fixes
                ; BOTH halves at once: the token byte, and the argument behind
                ; it, because a whole-word match leaves no name open.
                ;
                ; ⚠️ ALL THREE MUST PRECEDE THE PLAIN "DEF" ROW, exactly as
                ; DEFINT does -- match_kw takes the FIRST match with no
                ; longest-match and no word boundary, so a "DEF" row tried first
                ; would eat three of their six characters and hand the suffix
                ; back to the ordinary scan. (The old no-entry behaviour WAS
                ; that path; it is what this fixes.)
                db      6,"DEFSTR",1,DEFSTR_TOKEN
                db      6,"DEFSNG",1,DEFSNG_TOKEN
                db      6,"DEFDBL",1,DEFDBL_TOKEN
                db      3,"DEF",1,DEF_TOKEN
                db      3,"USR",1,USR_TOKEN
                ; D-DEFFN: `FN` crunches to ONE token ($DE) with the function
                ; NAME left as plain ASCII behind it, exactly as USR's row above
                ; leaves a USR number. TABLE POSITION IS FREE HERE: match_kw
                ; takes the FIRST entry that is a prefix of the input and does no
                ; longest-match, so a row only has to precede any keyword it is a
                ; prefix OF -- and "FN" is a prefix of nothing in this table (the
                ; F-words are FOR, FIELD, FILES, FIX, FRE, FN$-less), while
                ; nothing here is a prefix of "FN".
                ; ⚠️ AND THE MATCH RUNS AT EVERY POSITION, WHICH IS THE POINT: a
                ; keyword is not gated on a word boundary, so `FNA` crunches
                ; $DE 'A' and `AFN` crunches 'A' $DE -- the reference's own
                ; behaviour, and the reason `FN` is a reserved word at all.
                db      2,"FN",1,FN_TOKEN
                db      4,"LIST",1,LIST_TOKEN
                ; D-KWGAP4 (docs/spec-basic-kwgap4.md §2 R-K1): the four editor
                ; verbs. Tokens oracle-locked from the reference's own crunch
                ; emission (docs/lnref-msx1-characterization.md §4).
                ;
                ; ⚠️ TABLE POSITION IS FREE FOR ALL FOUR, AND THAT WAS WALKED
                ; RATHER THAN EYEBALLED. match_kw stops at the FIRST entry that
                ; matches and does no longest-match -- which is why DEFINT must
                ; precede DEF above. All 137 pre-existing entries were checked in
                ; BOTH directions: none is a prefix of these four, and none of
                ; these four is a prefix of an existing entry (characterization
                ; §2). The near-misses stay near-misses: DEF diverges from DELETE
                ; at char 3 (F vs L), REM from RENUM at char 3 (M vs N), LIST
                ; from LLIST at char 2 (I vs L) -- which is ALSO exactly why the
                ; old mangles were DE+LET+E, AU+TO and L+LIST: the reserved word
                ; was being found one or two positions LATE.
                ;
                ; 🔴 EACH OF THESE ALSO NEEDS ITS branch_lineno ARM, in the same
                ; slice. All four arm line-number mode on the reference; an entry
                ; on its own turns `20 DELETE 10` from "no token" into "token,
                ; WRONG argument". `lnrx-lprint` (`L<91>`, the identical stray-L
                ; shape that does NOT arm) is the standing control that says four
                ; entries were added here and not five.
                db      5,"LLIST",1,LLIST_TOKEN
                db      6,"DELETE",1,DELETE_TOKEN
                db      4,"AUTO",1,AUTO_TOKEN
                db      5,"RENUM",1,RENUM_TOKEN
                ; D-LPTVERB (docs/spec-basic-lptverb.md): the FIFTH entry the
                ; comment above says would move `lnrx-lprint`. It does, and this
                ; slice is what authorises it -- that row went from DIVERGE
                ; (`L<91> <0F><0A>`, a stray L plus the genuine PRINT token) to
                ; AGREEING with the reference's `<9D> <0F><0A>`, and left
                ; INFORMATIONAL to become an ordinary gating row. `lnrx-wait`
                ; survives as the control of that shape, because WAIT is still
                ; tokenless.
                ;
                ; ⚠️ UNLIKE THE FOUR ABOVE, LPRINT DOES *NOT* ARM LINE-NUMBER
                ; MODE, so it needs NO branch_lineno arm -- `20 LPRINT 10` stores
                ; the argument as the ordinary numeric literal `<0F><0A>` on the
                ; reference, not as `$0E,lo,hi`. Adding an arm here would be the
                ; D-LNREF defect inverted: a line-number reference invented where
                ; the reference has a plain constant.
                ;
                ; Position is free: match_kw compares the FULL keyword, and
                ; neither new word is a prefix of any entry nor has one as a
                ; prefix. The near-misses stay near-misses -- LPRINT vs LPOS
                ; diverge at char 3 (R vs O), LPRINT vs LLIST at char 2 (P vs L),
                ; LPOS vs LOF at char 2 (P vs O).
                db      6,"LPRINT",1,LPRINT_TOKEN
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
                db      4,"WAIT",1,WAIT_TOKEN
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
                ; EQV/IMP. ⚠️ THIS COMMENT SAID "repack only:." AND THEN A
                ; DANGLING HALF-SENTENCE about a build that no longer exists --
                ; truncated when S3 (19e8bfd) retired the lean cart, whose frozen
                ; ev_xor/ev_or/ev_and chain had no level for either word. There is
                ; ONE build now and it ships both (basic/expr.asm lg_eqv/lg_imp,
                ; landed ef098e9 at 156/156). D-EXPKW read the stale text as
                ; evidence that they might not ship at all, which is the whole
                ; cost of leaving a half-deleted sentence in place.
                ; Tokens oracle-measured from the VG-8020's own crunch emission.
                ; Neither shares a prefix with an existing keyword, so table order
                ; is free. 🔴 But `EQV` DOES collide with the float exponent
                ; marker: `E` in front of `Q` (or `L`, for `ELSE`) is not a marker
                ; -- sub/tkfloat.asm tke_mark_e, docs/spec-basic-expkw.md.
                db      3,"EQV",1,EQV_TOKEN
                db      3,"IMP",1,IMP_TOKEN
                ; Cursor / PRINT cluster (repack only, like everything above).
                ; "TAB(" and "SPC(" carry the '(' INSIDE the keyword — that is what
                ; the reference tokenises, and it is why a variable named TAB stays
                ; a variable. match_kw is full-keyword, so no prefix hazard: "POS"
                ; shares no 3-char prefix with an existing entry, and CSRLIN's "CS"
                ; lead is not a keyword.
                db      6,"CSRLIN",1,CSRLIN_TOKEN
                db      3,"POS",2,PEEK_PREFIX,POS_TOKEN
                ; D-LPTVERB: POS's printer twin. Same $FF alphabet and the same
                ; two-byte shape, so it belongs HERE and not beside LPRINT --
                ; LPOS $FF,$9C is a FUNCTION, LPRINT $9D a STATEMENT, and $9C is
                ; ALSO OUT_TOKEN in the statement alphabet (basic/sysvars.inc).
                ; Cross the two tables and each word answers the other's verb.
                ; ⚠️ MUST PRECEDE NOTHING IN PARTICULAR but must EXIST before
                ; `POS` can be reached inside `LPOS`: with no entry, the sequence
                ; crunches as the variable `L` plus the function `POS`, which is
                ; not an error and quietly prints two numbers
                ; (docs/lptverb-msx1-characterization.md §6).
                db      4,"LPOS",2,PEEK_PREFIX,LPOS_TOKEN
                db      4,"TAB(",1,TAB_TOKEN
                db      4,"SPC(",1,SPC_TOKEN
                ; --- string engine (repack build only) — string-engine arc S3 -----
                ; The core string-function keywords, all $FF-prefixed 2-byte function
                ; tokens. Selector bytes were black-box-captured from the VG-8020 crunch
                ; and cross-checked vs MSX2 TH Table 2.20 (S2, commit 517bd26; equates in
                ; sysvars.inc). The '$' is PART of the keyword for LEFT$/RIGHT$/MID$/STR$/
                ; CHR$ (like MKI$). match_kw / detok_kw2 pick these up automatically (both
                ; scan this table), so adding them here wires BOTH the crunch and LIST.
                ; None share a 2-char prefix with an existing keyword, so order is free.
                ; Handlers land in S4 (LEN also enables typed OPEN..LEN= — files.asm's
                ; oo_parse_reclen already expects $FF $92; until now only the unit test
                ; injected it). Gated reloc-only:.
                db      3,"LEN",2,PEEK_PREFIX,LEN_TOKEN      ; $FF $92
                db      5,"LEFT$",2,PEEK_PREFIX,LEFTD_TOKEN  ; $FF $81
                db      6,"RIGHT$",2,PEEK_PREFIX,RIGHTD_TOKEN; $FF $82
                db      4,"MID$",2,PEEK_PREFIX,MIDD_TOKEN    ; $FF $83
                db      4,"STR$",2,PEEK_PREFIX,STRD_TOKEN    ; $FF $93
                db      3,"VAL",2,PEEK_PREFIX,VAL_TOKEN      ; $FF $94
                db      3,"ASC",2,PEEK_PREFIX,ASC_TOKEN      ; $FF $95
                db      4,"CHR$",2,PEEK_PREFIX,CHRD_TOKEN    ; $FF $96
                ; --- string-functions slice (repack build only) — S2 -------------
                ; HEX$/OCT$/SPACE$: $FF-prefixed, same shape as the S3 verbs above.
                ; STRING$/INSTR: SINGLE-byte reserved-word tokens ($E3/$E5) — not
                ; $FF-prefixed. All five oracle-locked (VG-8020 crunch, MSX2 TH
                ; Table 2.20; equates in sysvars.inc). "STR$" is already in this
                ; table above; match_kw compares the FULL keyword (not a prefix),
                ; so "STRING$" never matches the "STR$" entry (or vice versa) —
                ; no shadow, order is free.
                db      4,"HEX$",2,PEEK_PREFIX,HEXD_TOKEN    ; $FF $9B
                db      4,"OCT$",2,PEEK_PREFIX,OCTD_TOKEN    ; $FF $9A
                ; BIN$ / FRE (keyword-gaps arc step 4): tokens oracle-measured
                ; off the VG-8020's own CRUNCH output (docs/kwsweep-msx1-
                ; coverage.md), not read from a table. FRE takes an argument of
                ; EITHER type, so unlike its $FF neighbours it is dispatched by
                ; its own arm in ev_f_ff rather than via ev_ff_argtab.
                db      4,"BIN$",2,PEEK_PREFIX,BIND_TOKEN    ; $FF $9D
                db      3,"FRE",2,PEEK_PREFIX,FRE_TOKEN      ; $FF $8F
                db      6,"SPACE$",2,PEEK_PREFIX,SPACED_TOKEN; $FF $99
                db      7,"STRING$",1,STRING_TOKEN           ; $E3
                db      5,"INSTR",1,INSTR_TOKEN               ; $E5
                ; --- INKEY$ slice (repack build only) — S2 ------------------------
                ; INKEY$: a SINGLE-byte reserved-word token ($EC), the '$' PART of the
                ; keyword (S2 black-box capture: `a$=inkey$` -> 41 24 EF EC, no separate
                ; $24; `print inkey$` -> 91 20 EC). match_kw compares the FULL keyword,
                ; and no keyword is a prefix of "INKEY$" (INPUT/INSTR diverge at char 3),
                ; so no shadow — order is free. detok_kw2 renders $EC -> "INKEY$" for LIST.
                db      6,"INKEY$",1,INKEY_TOKEN              ; $EC
                ; --- math pack slice 1a (repack build only) -----------------------
                ; docs/spec-basic-math-pack.md §9.3. ABS/SGN/INT/FIX/CINT/CSNG/CDBL:
                ; $FF-prefixed function tokens, same contiguous MSX-BASIC function
                ; table as LEN/VAL/HEX$ above (MSX2 TH Table 2.20), black-box
                ; captured from the VG-8020 crunch (probes/basic/basic_probe_math_
                ; conv.py) and cross-checked. None share a keyword prefix with an
                ; existing entry (INT/INPUT/INSTR/INKEY$ all diverge by the 2nd
                ; char; CINT/CSNG/CDBL vs CVI/CLS diverge by the 2nd char) — order
                ; is free (match_kw is full-keyword, not prefix, regardless).
                db      3,"ABS",2,PEEK_PREFIX,ABS_TOKEN        ; $FF $86
                db      3,"SGN",2,PEEK_PREFIX,SGN_TOKEN        ; $FF $84
                db      3,"INT",2,PEEK_PREFIX,INT_TOKEN        ; $FF $85
                db      3,"FIX",2,PEEK_PREFIX,FIX_TOKEN        ; $FF $A1
                db      4,"CINT",2,PEEK_PREFIX,CINT_TOKEN      ; $FF $9E
                db      4,"CSNG",2,PEEK_PREFIX,CSNG_TOKEN      ; $FF $9F
                db      4,"CDBL",2,PEEK_PREFIX,CDBL_TOKEN      ; $FF $A0
                ; --- math pack slice 1b (repack build only) -----------------
                ; docs/spec-basic-math-pack.md §10.1. SQR: same $FF-prefixed
                ; function-token shape, MSX2 TH Table 2.20, black-box captured
                ; from the VG-8020 crunch (probes/basic/basic_probe_math_
                ; conv.py). No prefix collision with any existing 3-char
                ; entry (SGN/INT/FIX/ABS all diverge by char 1 or 2) -- order
                ; is free.
                db      3,"SQR",2,PEEK_PREFIX,SQR_TOKEN         ; $FF $87
                ; --- math pack slice 2a (repack build only) -----------------
                ; docs/spec-basic-mathpack-slice2.md §11.1. ATN: same $FF-
                ; prefixed function-token shape, MSX2 TH Table 2.20, black-box
                ; captured from the VG-8020 crunch (probes/basic/basic_probe_
                ; math_conv.py). No prefix collision with any existing 3-char
                ; entry (ABS/SGN/INT/FIX/SQR all diverge by char 1 or 2) --
                ; order is free.
                db      3,"ATN",2,PEEK_PREFIX,ATN_TOKEN         ; $FF $8E
                ; --- math pack slice 2b (repack build only) -----------------
                ; docs/spec-basic-mathpack-slice2.md §12.2. EXP/LOG: same
                ; $FF-prefixed function-token shape, MSX2 TH Table 2.20,
                ; black-box captured from the VG-8020 crunch (probes/basic/
                ; basic_probe_math_conv.py). No prefix collision with any
                ; existing entry (match_kw compares the FULL keyword, so
                ; order is free regardless -- same as every entry above).
                db      3,"EXP",2,PEEK_PREFIX,EXP_TOKEN         ; $FF $8B
                db      3,"LOG",2,PEEK_PREFIX,LOG_TOKEN         ; $FF $8A
                ; --- math pack slice 2d (repack build only) -----------------
                ; docs/spec-basic-mathpack-slice2.md §14.4. SIN/COS/TAN: same
                ; $FF-prefixed function-token shape, MSX2 TH Table 2.20,
                ; black-box captured from the VG-8020 crunch (probes/basic/
                ; basic_probe_math_conv.py). No prefix collision with any
                ; existing entry (match_kw compares the FULL keyword, so
                ; order is free regardless -- same as every entry above).
                db      3,"SIN",2,PEEK_PREFIX,SIN_TOKEN         ; $FF $89
                db      3,"COS",2,PEEK_PREFIX,COS_TOKEN         ; $FF $8C
                db      3,"TAN",2,PEEK_PREFIX,TAN_TOKEN         ; $FF $8D
                ; --- math pack slice 2e (repack build only) -----------------
                ; docs/spec-basic-mathpack-slice2.md §15.4. RND: same
                ; $FF-prefixed function-token shape, MSX2 TH Table 2.20,
                ; black-box captured from the VG-8020 crunch (probes/basic/
                ; basic_probe_math_conv.py). No prefix collision with any
                ; existing entry (match_kw compares the FULL keyword, so
                ; order is free regardless -- same as every entry above).
                db      3,"RND",2,PEEK_PREFIX,RND_TOKEN         ; $FF $88
                ; --- arrays slice-1 (repack build only) -----------------------
                ; docs/spec-basic-arrays.md §5. DIM: single-byte STATEMENT token
                ; ($86, NOT $FF-prefixed), black-box VG-8020 crunch capture +
                ; MSX2 TH Table 2.20. No prefix collision with any existing
                ; entry (match_kw compares the FULL keyword, so order is free
                ; regardless -- same as every entry above).
                db      3,"DIM",1,DIM_TOKEN                     ; $86
                ; --- arrays slice-2 (repack build only) -----------------------
                ; docs/spec-basic-arrays-slice2-erase.md §2. ERASE: single-byte
                ; STATEMENT token ($A5, NOT $FF-prefixed), black-box VG-8020
                ; crunch capture + MSX2 TH Table 2.20. No prefix collision with
                ; any existing entry (EOF/ELSE/END/EXP are the only other "E..."
                ; keywords and none is a prefix of "ERASE"; match_kw compares
                ; the FULL keyword, so order is free regardless -- same as
                ; every entry above).
                db      5,"ERASE",1,ERASE_TOKEN                 ; $A5
                ; --- error-handling S2a (repack build only) -------------------
                ; docs/spec-basic-error-handling-s2a-packet.md §1. ERROR/ERR/ERL:
                ; single-byte tokens, black-box VG-8020 crunch capture (probes/
                ; basic/basic_probe_pin_errtokens.py) + MSX2 TH Table 2.20 cross-
                ; check. HARD HAZARD: "ERR" is a prefix of "ERROR"; match_kw
                ; returns the FIRST matching entry (no longest-match), so ERROR's
                ; entry MUST precede ERR's here or "ERROR" would crunch to
                ; ERR_TOKEN + verbatim "OR". ERL shares no prefix with either, so
                ; its position is free.
                db      5,"ERROR",1,ERROR_TOKEN                 ; $A6 (statement)
                db      3,"ERR",1,ERR_TOKEN                     ; $E2 (value token)
                db      3,"ERL",1,ERL_TOKEN                     ; $E1 (value token)
                ; --- TIME (repack build only) ---------------------------------
                ; docs/spec-basic-time.md §1.1. Single-byte token, black-box
                ; VG-8020 crunch capture (probes/basic/basic_probe_time.py) +
                ; MSX2 TH Table 2.20 cross-check. No prefix collision in either
                ; direction: no keyword is a prefix of "TIME" and "TIME" is a
                ; prefix of none, so order is free -- and the greedy match is
                ; WHAT THE ORACLE DOES: `A=TIMES` crunches to TIME + verbatim
                ; "S", `A=TIME$` to TIME + "$", `A=ATIME` to "A" + TIME. Only a
                ; plain `TI` survives as a variable.
                db      4,"TIME",1,TIME_TOKEN                   ; $CB (factor AND lvalue)
                ; --- error-handling S2b (repack build only) -------------------
                ; docs/spec-basic-error-handling-s2b-packet.md §2. RESUME:
                ; single-byte STATEMENT token ($A7), black-box VG-8020 crunch
                ; capture ([[s2-error-token-pins]]) + MSX2 TH Table 2.20 cross-
                ; check. No prefix collision with any existing entry.
                db      6,"RESUME",1,RESUME_TOKEN                ; $A7
                ; --- audio slice 1 (repack build only) ------------------------
                ; docs/spec-basic-audio-play.md. SOUND: single-byte STATEMENT
                ; token ($C4), black-box VG-8020 crunch capture ("sound 1,255"
                ; -> C4 20 12 2C 0F FF 00; scratchpad/spike_sound_token.py) +
                ; MSX2 TH Table 2.20 cross-check. No prefix collision with any
                ; existing entry ("SCREEN"/"STOP"/"STEP"/"STR$"/"SPACE$" share
                ; no prefix with "SOUND"; match_kw compares the FULL keyword).
                db      5,"SOUND",1,SOUND_TOKEN                  ; $C4
                ; --- audio slice 2a (repack build only) -----------------------
                ; docs/spec-basic-audio-play-slice2a.md. PLAY: single-byte
                ; STATEMENT token ($C1, black-box VG-8020 crunch capture; see
                ; sysvars.inc). No prefix collision (PRINT/POKE/PEEK share only
                ; "P"; match_kw compares the FULL keyword).
                db      4,"PLAY",1,PLAY_TOKEN                    ; $C1
                ; --- audio close-out (repack build only) ----------------------
                ; docs/spec-basic-audio-beep.md. BEEP: single-byte STATEMENT token
                ; ($C0, black-box VG-8020 crunch capture; see sysvars.inc). No arg.
                ; No prefix collision (no keyword shares the "BEEP" prefix;
                ; match_kw compares the FULL keyword).
                db      4,"BEEP",1,BEEP_TOKEN                    ; $C0
                ; --- graphics slice G2 (repack build only) --------------------
                ; docs/spec-basic-graphics-g2.md. PSET/PRESET STATEMENT tokens and
                ; POINT FUNCTION token, single-byte, RE-VERIFIED black-box on the
                ; VG-8020 (stored-line crunch, sysvars.inc / arc §11.9). match_kw
                ; compares the FULL keyword: PSET vs PRESET differ at the 2nd char
                ; (no prefix overlap), and POINT shares no full keyword with
                ; POKE/POS/PRINT. $C2 is the value the WRONG SOUND guess used --
                ; now confirmed genuinely PSET.
                db      4,"PSET",1,PSET_TOKEN                    ; $C2
                db      6,"PRESET",1,PRESET_TOKEN                ; $C3
                db      5,"POINT",1,POINT_TOKEN                  ; $ED
                ; --- graphics slice G4 (repack build only) --------------------
                ; docs/spec-basic-graphics-g4.md §7/§11.1. CIRCLE is a NEW
                ; single-byte STATEMENT token (unlike G3's LINE, which reused
                ; LINE=$AF). No prefix collision: match_kw compares the FULL
                ; keyword, and no other keyword shares "CIRCLE".
                db      6,"CIRCLE",1,CIRCLE_TOKEN                ; $BC
                ; --- graphics slice G5 (repack build only) --------------------
                ; docs/spec-basic-graphics-g5.md §7. PAINT is a NEW single-byte
                ; STATEMENT token (sysvars.inc PAINT_TOKEN=$BF), black-box
                ; crunch-pinned (scratchpad/g5_paint_notes.md C1). No prefix
                ; collision: match_kw compares the FULL keyword, and no other
                ; keyword shares "PAINT".
                db      5,"PAINT",1,PAINT_TOKEN                  ; $BF
                ; --- graphics slice G6 (repack build only) --------------------
                ; docs/spec-basic-graphics-g6.md §3. DRAW is a NEW single-byte
                ; STATEMENT token (sysvars.inc DRAW_TOKEN=$BE), black-box
                ; crunch-pinned (scratchpad/g6_draw_notes.md §1). No prefix
                ; collision: match_kw compares the FULL keyword, and no other
                ; keyword shares "DRAW".
    IF G6_RESIDENT
                db      4,"DRAW",1,DRAW_TOKEN                    ; $BE
    ENDIF
                ; --- graphics slice G7 (repack build only) --------------------
                ; docs/spec-basic-graphics-g7.md §1. SPRITE is ONE reserved word
                ; ($C7) behind the whole sprite surface: `SPRITE$(n)` (the `$` is
                ; separate ASCII), `PUT SPRITE`, and `SPRITE ON|OFF|STOP`. No
                ; prefix collision -- match_kw compares the FULL keyword.
    IF G7_RESIDENT
                db      6,"SPRITE",1,SPRITE_TOKEN                ; $C7
    ENDIF
                ; --- graphics slice G8 (repack build only) --------------------
                ; docs/spec-basic-graphics-g8.md §2. VDP joins BASE (already
                ; above, since Phase 1) as a single-byte FUNCTION token; the
                ; assignment form `VDP(n)=v` needs no keyword of its own -- it is
                ; the same token, dispatched as a statement (§2).
    IF G8_RESIDENT
                db      3,"VDP",1,VDP_TOKEN                      ; $C8
    ENDIF
                ; --- input devices, slice I1 (repack build only) --------------
                ; docs/spec-basic-input-devices.md §3. Two-byte $FF-prefixed
                ; FUNCTION tokens, same row shape as EOF/LOF/DSKF above. Neither
                ; shares a prefix with an existing keyword (STICK/STRIG share only
                ; "ST" with each other and with STEP/STOP/STR$, and match_kw
                ; compares the FULL keyword, so table order is free).
    IF I1_RESIDENT
                db      5,"STICK",2,PEEK_PREFIX,STICK_TOKEN      ; $FF $A2
                db      5,"STRIG",2,PEEK_PREFIX,STRIG_TOKEN      ; $FF $A3
    ENDIF
    IF I2_RESIDENT
                db      3,"PDL",2,PEEK_PREFIX,PDL_TOKEN          ; $FF $A4
                db      3,"PAD",2,PEEK_PREFIX,PAD_TOKEN          ; $FF $A5
    ENDIF
                ; --- the MISSING class (docs/spec-basic-missing-class.md §3.1) -
                ; The table is
                ; a sub.rom tenant (wave 3) with ~8 KB free, so these ~39 B cost
                ; nothing in either tight region.
                ;
                ; ⚠️ THREE OF THESE COLLIDE BY VALUE with the $FF-prefixed
                ; STICK/STRIG/PDL rows directly above -- $A2/$A3/$A4 in a
                ; different namespace. That is correct and it is measured. The
                ; CRUNCH direction is safe by construction (match_kw compares the
                ; full keyword and these five share no prefix with anything: MOTOR
                ; vs MERGE/MID$/MKI$/MAX, SWAP vs nothing, LOCATE vs LOF/LSET/LINE,
                ; TRON/TROFF vs each other only -- and match_kw returning the FIRST
                ; FULL match makes even that pair order-free). It is the
                ; DETOKENISER that has to keep the namespaces apart, so the slice
                ; carries LIST round-trip cases.
                db      6,"LOCATE",1,LOCATE_TOKEN                ; $D8
                db      3,"LOC",2,PEEK_PREFIX,LOC_TOKEN    ; D-LOC: $FF $AC, oracle-taken.
                                                    ; AFTER LOCATE, never before: match_kw takes the
                                                    ; FIRST prefix match, and "LOC" ahead of "LOCATE"
                                                    ; crunched LOCATE as LOC+ATE (11 gates red, 2026-09-11)
    IF SWAP_RESIDENT
                db      4,"SWAP",1,SWAP_TOKEN                    ; $A4
    ENDIF
                db      5,"TROFF",1,TROFF_TOKEN                  ; $A3
                db      4,"TRON",1,TRON_TOKEN                    ; $A2
                db      5,"MOTOR",1,MOTOR_TOKEN                  ; $CE
                db      0
