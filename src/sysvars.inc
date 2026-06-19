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
