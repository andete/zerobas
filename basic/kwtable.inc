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
    IF ROM_BASE < $4000
                ; math pack slice 1a fallout: adding "INT" as a real keyword
                ; (below) broke DEFINT specifically -- match_kw's linear,
                ; boundary-free scan matched plain "DEF" (3 chars) first,
                ; leaving "INT A-C" for the NEXT match_kw call to find, which
                ; (now that INT is a keyword) tokenised it to $FF $85 instead
                ; of leaving it as the literal ASCII "INT" ex_def_type expects
                ; (usr.asm: "the mnemonics are NOT keyword tokens ... they
                ; arrive as plain upcased ASCII"). Caught live by
                ; float-acceptance's def.* cases regressing. Fix: match the
                ; WHOLE "DEFINT" word as its own entry, EMITTING THE SAME
                ; BYTES the old DEF+copied-name path produced (DEF_TOKEN then
                ; literal 'I','N','T') -- so ex_def_type is untouched and the
                ; crunched byte stream is identical to before this slice.
                ; Placed BEFORE the plain "DEF" entry: match_kw stops at the
                ; FIRST table entry that matches (no longest-match, no word-
                ; boundary check), so DEFINT must be tried first or "DEF"
                ; wins the first 3 chars and the collision reproduces. DEFSNG/
                ; DEFDBL/DEFSTR do NOT collide (no "SNG"/"DBL"/"STR"-alone
                ; keyword exists -- only "CSNG"/"CDBL" do, both requiring a
                ; leading 'C' that DEF's suffix never has, and "STR$" needs a
                ; trailing '$' DEFSTR's suffix never has), so no matching
                ; entry is needed for them.
                db      6,"DEFINT",4,DEF_TOKEN,"INT"
    ENDIF
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
    ENDIF
                db      0
