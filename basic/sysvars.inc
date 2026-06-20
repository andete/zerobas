; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; sysvars.inc — BIOS entry points and RAM scratch for zerobas.
;
; CLEAN-ROOM: every address below is traced to an allowed source (see
; PROVENANCE.md). No value is taken from any MSX-BASIC / GW-BASIC disassembly
; or from a reference ROM disassembly.

; --- Screen / console BIOS entry points ------------------------------------
; Source: MSX Assembly Page BIOS call list / MSX2 Technical Handbook.
CHGMOD          equ     $005F   ; switch screen mode; A = mode 0..3 (SCREEN n)
CHGCLR          equ     $0062   ; apply FORCLR/BAKCLR/BDRCLR; A = screen mode (COLOR)
INITXT          equ     $006C   ; init SCREEN 0 (TEXT1) and enable the display
CHGET           equ     $009F   ; wait for a character from the keyboard -> A
CHPUT           equ     $00A2   ; output the character in A at the cursor
CLS             equ     $00C3   ; clear the screen; zero flag must be set on entry
ERAFNK          equ     $00CC   ; erase the function-key display line (KEY OFF)
DSPFNK          equ     $00CF   ; display the function-key line (KEY ON)
CSRX            equ     $F3DD   ; cursor column (1-based); C-BIOS sysvars / PRINT comma zones

; --- Screen work-area system variables (C-BIOS; allowed) -------------------
; Source: C-BIOS system variables (BSD 2-clause), cross-checked against the MSX2
; Technical Handbook work-area appendix / MSX Assembly Page. CHGCLR reads the
; three colour bytes; CHGMOD/INITXT read the per-mode line lengths; SCRMOD holds
; the current screen mode (CHGMOD writes it).
LINL40          equ     $F3AE   ; text columns for SCREEN 0 (WIDTH default)
LINL32          equ     $F3AF   ; text columns for SCREEN 1 (WIDTH default)
LINLEN          equ     $F3B0   ; current line length (active width)
FORCLR          equ     $F3E9   ; foreground colour
BAKCLR          equ     $F3EA   ; background colour
BDRCLR          equ     $F3EB   ; border colour
SCRMOD          equ     $FCAF   ; current screen mode (0..3)

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
TKNAME          equ     $E028   ; tokeniser: 1 = previous char was part of a name
                                ; (so a following digit stays verbatim, not crunched)
TKRADIX         equ     $E029   ; tokeniser: &H/&O accumulator radix (16 or 8)
TKRTOK          equ     $E02A   ; tokeniser: &H/&O constant token to emit ($0C/$0B)
NUMBUF          equ     $E0C0   ; PRINT: decimal-format scratch (8 bytes, 0-term)
; Buffers and the variable table live in page $E1, clear of $E000.
LINEBUF         equ     $E100   ; ASCII input line from the keyboard (LINEMAX bytes)
LINEMAX         equ     96      ; LINEBUF capacity; $E100..$E15F stays in page $E1
TOKBUF          equ     $E160   ; crunch buffer: the tokenised line (0-terminated)
; Variable table: dynamically-allocated 4-byte entries [name0][name1][value:2].
; Names are significant to 2 characters (public MSX-BASIC language reference);
; name1 = 0 for a 1-char name. A name0 of 0 marks the first free slot. Phase 1
; grew this from the single-letter A..Z store to multi-character names.
VARTAB          equ     $E1C0   ; base of the variable table
VARENTSZ        equ     4       ; [name0:1][name1:1][value:2]
VARSLOTS        equ     32      ; max distinct variables (128 bytes -> $E240)
VAREND          equ     VARTAB + VARSLOTS*VARENTSZ

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

; --- Phase 1: CLEAR memory-top sysvar --------------------------------------
; HIMEM is the documented home of CLEAR's "highest address BASIC may use"
; argument (CLEAR [<strings>][,<himem>]). zerobas has no allocator that consults
; it yet (fixed RAM layout), so ex_clear stores it record-only; see clear.asm.
; Source: C-BIOS system variables (BSD 2-clause; address $FC4A), cross-checked
; against the MSX2 Technical Handbook work-area appendix / MSX Assembly Page.
HIMEM           equ     $FC4A   ; highest RAM address BASIC may use (2 bytes)
; USRTAB: the 10 DEF USR vectors (USR0..USR9), 2 bytes each, $F39A..$F3AD.
; Source: C-BIOS system variables (BSD 2-clause). On C-BIOS (no BASIC) this is
; unused work-area RAM, so DEF USR writing it is safe and observable.
USRTAB          equ     $F39A   ; 10 USR jump vectors, 2 bytes each
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
CLEAR_TOKEN     equ     $92     ; Table 2.20 (cross-checks MSX Assembly Page token table)
; Phase 1 statement / function tokens (MSX2 Technical Handbook Table 2.20; the
; overlaps DEF=$97, ON=$95, PRINT=$91, LIST=$93, GOTO=$89, GOSUB=$8D all match
; the values already oracle-confirmed elsewhere here — strong corroboration).
DEF_TOKEN       equ     $97     ; DEF (statement; PEEK's $97 is the 2nd byte after $FF)
USR_TOKEN       equ     $DD     ; USR (function token, single byte; DEF USR target)
LIST_TOKEN      equ     $93     ; LIST
CLS_TOKEN       equ     $9F     ; CLS
SCREEN_TOKEN    equ     $C5     ; SCREEN
COLOR_TOKEN     equ     $BD     ; COLOR
WIDTH_TOKEN     equ     $A0     ; WIDTH
KEY_TOKEN       equ     $CC     ; KEY
OFF_TOKEN       equ     $EB     ; OFF (KEY OFF); dev-workflow.md tokeniser quirk, oracle-observed
LINENO_TOKEN    equ     $0E     ; line number reference (before RUN): $0E,<lineno LE>
LINEADDR_TOKEN  equ     $0D     ; line number reference (after RUN): $0D,<addr LE>
OCT_TOKEN       equ     $0B     ; &O constant: $0B,<value16 LE>
; Relational operators (Table 2.20). '=' is EQ_TOKEN ($EF) above; compound forms
; (<=, >=, <>) are two consecutive operator tokens, combined by the evaluator.
GT_TOKEN        equ     $EE     ; '>'
LT_TOKEN        equ     $F0     ; '<'
; Phase 1: division + logical/bitwise operators (MSX2 TH Table 2.20).
DIV_TOKEN       equ     $F4     ; '/'  (real division; zerobas approximates with int divide)
IDIV_TOKEN      equ     $FC     ; '\'  integer division
MOD_TOKEN       equ     $FB     ; MOD  remainder
AND_TOKEN       equ     $F6     ; AND  (bitwise)
OR_TOKEN        equ     $F7     ; OR   (bitwise)
XOR_TOKEN       equ     $F8     ; XOR  (bitwise)
NOT_TOKEN       equ     $E0     ; NOT  (bitwise complement, unary)
; Runtime control-flow state (page $E0).
CURLINE         equ     $E038   ; link-field addr of the line being executed (2)
GOTOTGT         equ     $E03A   ; pending branch-target line addr (2)
GOTOFLAG        equ     $E03C   ; 1 = a branch (GOTO) is pending
ENDFLAG         equ     $E03D   ; 1 = END/STOP reached, stop the run
; Mid-line resume: GOTO branches to a line *start*, but RETURN and NEXT must
; resume at an exact token position (the statement after GOSUB / the FOR loop
; body). When RESUMEFLAG is set the RUN loop runs from RESUMEPTR instead of
; recomputing the body from CURLINE; the resuming statement sets CURLINE to the
; line that holds RESUMEPTR so the post-statement "advance to next line" works.
RESUMEPTR       equ     $E03E   ; mid-line resume token pointer (2)
RESUMEFLAG      equ     $E040   ; 1 = resume at RESUMEPTR (set by RETURN / NEXT)
; Control stacks (page $E0, below LINEBUF at $E100). Both grow upward; the
; pointer addresses the next free slot, and the stack is empty when it equals
; its base. GOSUB frame = [curline:2][resume:2] (4 bytes). FOR frame =
; [var:1][limit:2][step:2][curline:2][resume:2] (9 bytes).
GSP             equ     $E041   ; GOSUB return-stack pointer (2)
FSP             equ     $E043   ; FOR-stack pointer (2)
FOR_CUR         equ     $E045   ; scratch: a working copy of one FOR frame (9)
FOR_NEW         equ     $E04E   ; scratch: NEXT's freshly-stepped loop value (2)
GOSUB_STK       equ     $E050   ; GOSUB return-stack base
GOSUB_DEPTH     equ     8
GOSUB_STK_END   equ     GOSUB_STK + GOSUB_DEPTH*4   ; $E070
FOR_STK         equ     $E070   ; FOR-stack base
FOR_DEPTH       equ     8
FOR_STK_END     equ     FOR_STK + FOR_DEPTH*9       ; $E0B8 (stays below LINEBUF)
; DATA / READ / RESTORE state. The reference stores DATA items as verbatim ASCII
; text (oracle: `data 5,6` -> $84 $20 '5' ',' '6'), so READ parses ASCII from the
; stored program at run time and a DATA cursor walks the $84-tagged statements.
DATASTATE       equ     $E0B8   ; 0 = unpositioned (RESTORE), 1 = ready, 2 = exhausted
DATAPTR         equ     $E0B9   ; next unread DATA item (ASCII) in the program (2)
DATALINE        equ     $E0BB   ; link-field of the line holding DATAPTR (2)
RESTORE_LINE    equ     $E0BD   ; link-field a READ seeks DATA from when unpositioned (2)
READVAR         equ     $E0BF   ; READ: name of the variable being filled (1)
