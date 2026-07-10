; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; kwtable.inc — the keyword -> token crunch table (extracted from interp.asm).
; ===========================================================================
; Entry layout: [klen][UPPERCASE chars][tlen][token...]. Terminated by a 0 length
; byte. Tokens are oracle-sourced (spec-tokenise.md, spec-tokens-statements.md).
; PEEK is a two-byte function token ($FF $97).
;
; This table is DATA, reached only via `ld ix,kwtable` from match_kw (tokeniser)
; and detok_kw2 (LIST detokeniser) — both scan it linearly, so BOTH directions are
; data-driven off whichever copy the build placed. The table was extracted into its
; own file so its PLACEMENT can be gated (string-engine arc S3, spec §5b): the lean
; 16 KB build includes it inline in interp.asm (byte-identical); the repack build
; (ROM_BASE < $4000) instead includes it in the reclaimed low region (main.asm),
; freeing page-1 room for the string engine. match_kw is full-keyword (not prefix),
; so table order is free except for the documented longest-match notes below.
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
                db      5,"USING",1,USING_TOKEN
                db      4,"CALL",1,CALL_TOKEN
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
    IF ROM_BASE < $4000
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
                ; injected it). Gated reloc-only: the lean table stays byte-identical.
                db      3,"LEN",2,PEEK_PREFIX,LEN_TOKEN      ; $FF $92
                db      5,"LEFT$",2,PEEK_PREFIX,LEFTD_TOKEN  ; $FF $81
                db      6,"RIGHT$",2,PEEK_PREFIX,RIGHTD_TOKEN; $FF $82
                db      4,"MID$",2,PEEK_PREFIX,MIDD_TOKEN    ; $FF $83
                db      4,"STR$",2,PEEK_PREFIX,STRD_TOKEN    ; $FF $93
                db      3,"VAL",2,PEEK_PREFIX,VAL_TOKEN      ; $FF $94
                db      3,"ASC",2,PEEK_PREFIX,ASC_TOKEN      ; $FF $95
                db      4,"CHR$",2,PEEK_PREFIX,CHRD_TOKEN    ; $FF $96
    ENDIF
                db      0
