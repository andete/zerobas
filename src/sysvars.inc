; sysvars.inc — BIOS entry points and RAM scratch for zerobas.
;
; CLEAN-ROOM: every address below is traced to an allowed source (see
; PROVENANCE.md). No value is taken from any MSX-BASIC / GW-BASIC disassembly
; or from a reference ROM disassembly.

; --- Screen / console BIOS entry points ------------------------------------
; Source: MSX Assembly Page BIOS call list / MSX2 Technical Handbook.
INITXT          equ     $006C   ; init SCREEN 0 (TEXT1) and enable the display
CHGET           equ     $009F   ; wait for a character from the keyboard -> A
CHPUT           equ     $00A2   ; output the character in A at the cursor

; --- Cassette BIOS entry points -------------------------------------------
; Source: MSX Assembly Page BIOS call list / MSX2 Technical Handbook,
;         cassette I/O chapter.
TAPION          equ     $00E1   ; read tape header (motor on); CF set = fail
TAPIN           equ     $00E4   ; read one byte -> A;           CF set = fail
TAPIOF          equ     $00E7   ; stop the tape motor

; --- Binary (BSAVE) file identifier ---------------------------------------
; Source: MSX2 Technical Handbook, BSAVE file format ("D0" x10 = binary).
BINARY_ID       equ     $D0

; --- Tokeniser / executor --------------------------------------------------
; Keyword tokens. Each value is an oracle observation (the crunch buffer KBUF
; dump), cross-checked against the MSX Assembly Page token table.
; Source: spec-tokenise.md (BLOAD) and spec-tokens-statements.md (REM/POKE/PEEK).
BLOAD_TOKEN     equ     $CF     ; spec-tokenise.md
REM_TOKEN       equ     $8F     ; spec-tokens-statements.md; swallows rest of line
POKE_TOKEN      equ     $98     ; spec-tokens-statements.md
; PEEK is a *function* token: a $FF prefix followed by a second byte.
PEEK_PREFIX     equ     $FF     ; spec-tokens-statements.md (function-token prefix)
PEEK_TOKEN      equ     $97     ; spec-tokens-statements.md
; ASCII bytes the tokeniser / evaluator treat specially (all public ASCII).
COLON           equ     $3A     ; ':' statement separator
QUOTE_REM       equ     $27     ; "'" — apostrophe comment, treated as REM
APOS_MARK       equ     $E6     ; "remark-quote" marker emitted after `'`'s REM token

; --- Step A: byte-identical constant + operator tokens --------------------
; Captured byte-exact from the reference (spec-tokens-statements.md §3/§4,
; fidelity sweep). Numbers/operators are no longer kept verbatim: the tokeniser
; emits these exact tokens so a crunched line matches a real ROM's KBUF.
INT_DIGIT_BASE  equ     $11     ; digits 0..9 -> $11+n (one byte, no value byte)
INT1_TOKEN      equ     $0F     ; one-byte int 10..255: $0F, <value>
INT2_TOKEN      equ     $1C     ; two-byte int 256..32767: $1C, <value LE>
HEX_TOKEN       equ     $0C     ; &H constant: $0C, <value16 LE>  (full 0..FFFF)
EQ_TOKEN        equ     $EF     ; '='
PLUS_TOKEN      equ     $F1     ; '+'
MINUS_TOKEN     equ     $F2     ; '-'
STAR_TOKEN      equ     $F3     ; '*'

; --- RAM scratch (page-3 RAM; NOT part of the ROM image) -------------------
; Chosen to avoid the demo blob's regions ($C000 load, $E000 "JONG" marker /
; POKE test target). All "own choice — free RAM"; see PROVENANCE.md.
CURPTR          equ     $E020   ; current load pointer (2 bytes)
ENDPTR          equ     $E022   ; final load address  (2 bytes)
EXECPTR         equ     $E024   ; execution address   (2 bytes)
ERRMARK         equ     $E010   ; error landmark marker byte
RUNFLAG         equ     $E02F   ; 1 = ,R handoff requested (set while parsing)
; Buffers and the variable table live in page $E1, clear of $E000.
LINEBUF         equ     $E100   ; ASCII input line from the keyboard (LINEMAX bytes)
LINEMAX         equ     96      ; LINEBUF capacity; $E100..$E15F stays in page $E1
TOKBUF          equ     $E160   ; crunch buffer: the tokenised line (0-terminated)
VARTAB          equ     $E1C0   ; 26 integer variables A..Z, 2 bytes each (52 bytes)
VARCOUNT        equ     26      ; A..Z

; --- Step B: stored-program text area (numbered lines) ---------------------
; Numbered lines are stored in the real MSX line-link format at the real text
; base, so a stored program's bytes match a reference ROM's (Step A's crunch
; gives byte-identical line bodies; storing at the same base gives identical
; link pointers). Each line: [link:2 LE][lineno:2 LE][tokens...][00]; the
; program ends with a link word of $0000.
; Source: TXTTAB sysvar $F676 and its post-boot value $8001 are oracle-confirmed
; (msx-preservation/basic-spec spec-bload-r.md §4 — "sourced"); the line-link
; layout is MSX2 Technical Handbook / MSX Assembly Page (allowed), same
; provenance as the BIOS and token constants used elsewhere here.
TXTTAB          equ     $F676   ; sysvar: pointer to the BASIC text base
TXTBASE         equ     $8001   ; text base (oracle: TXTTAB value after boot)
TXTMAX          equ     $C000   ; text must stay below the $C000 BLOAD region
PRGEND          equ     $E026   ; addr of the $0000 end-of-program marker (2 bytes)
; Step B scratch (page $E0, clear of LINEBUF/VARTAB in page $E1).
SL_NUM          equ     $E030   ; store_line: target line number (2)
SL_SLOT         equ     $E032   ; store_line: insertion slot address (2)
SL_SIZE         equ     $E034   ; store_line: new line size in bytes (2)
SL_TOK          equ     $E036   ; store_line: saved token-body pointer (2)

; --- Step B control flow: keyword tokens + line-number references ----------
; Keyword tokens from MSX2 Technical Handbook Table 2.20; the line-number
; identification codes from Figure 2.12. See basic-spec/docs/spec-controlflow.md.
; Allowed-source-sourced; every value that overlaps an existing oracle token
; (POKE/BLOAD/PEEK/REM/= + - *) matches it.
GOTO_TOKEN      equ     $89
GOSUB_TOKEN     equ     $8D
RETURN_TOKEN    equ     $8E
IF_TOKEN        equ     $8B
THEN_TOKEN      equ     $DA
ELSE_TOKEN      equ     $A1     ; in the stream ELSE is COLON,$A1 (like REM = $3A $8F)
FOR_TOKEN       equ     $82
TO_TOKEN        equ     $D9
STEP_TOKEN      equ     $DC
NEXT_TOKEN      equ     $83
DATA_TOKEN      equ     $84
READ_TOKEN      equ     $87
RESTORE_TOKEN   equ     $8C
RUN_TOKEN       equ     $8A
NEW_TOKEN       equ     $94
END_TOKEN       equ     $81
STOP_TOKEN      equ     $90
ON_TOKEN        equ     $95
PRINT_TOKEN     equ     $91
LET_TOKEN       equ     $88
LINENO_TOKEN    equ     $0E     ; line number reference (before RUN): $0E,<lineno LE>
LINEADDR_TOKEN  equ     $0D     ; line number reference (after RUN): $0D,<addr LE>
OCT_TOKEN       equ     $0B     ; &O constant: $0B,<value16 LE>
; Runtime control-flow state (page $E0).
CURLINE         equ     $E038   ; link-field addr of the line being executed (2)
GOTOTGT         equ     $E03A   ; pending branch-target line addr (2)
GOTOFLAG        equ     $E03C   ; 1 = a branch (GOTO) is pending
ENDFLAG         equ     $E03D   ; 1 = END/STOP reached, stop the run
