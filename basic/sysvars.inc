; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

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
LPTOUT          equ     $00A5   ; print the character in A to the printer (Centronics);
                                ; supplied by zerobas-tape on the C-BIOS target
CLS             equ     $00C3   ; clear the screen; zero flag must be set on entry
ERAFNK          equ     $00CC   ; erase the function-key display line (KEY OFF)
DSPFNK          equ     $00CF   ; display the function-key line (KEY ON)
CSRX            equ     $F3DD   ; cursor column (1-based); C-BIOS sysvars / PRINT comma zones
; BREAKX: test the Ctrl-STOP key combination by directly scanning keyboard matrix
; row 6 (no side effects, no ISR dependency). CF set on return = Ctrl-STOP held,
; CF clear = not held. Source: MSX Assembly Page BIOS call list / MSX2 Technical
; Handbook; oracle-confirmed working on C-BIOS_MSX1 (bios_probe_breakx.py: carry
; clear when no key pressed, identical to the reference VG-8020).
BREAKX          equ     $00B7   ; check Ctrl-STOP via keyboard matrix; CF set = pressed

; --- VDP VRAM access BIOS entry points (VPOKE / VPEEK) ---------------------
; Source: MSX Assembly Page BIOS call list / MSX2 Technical Handbook, VDP I/O.
WRTVRM          equ     $004D   ; write A to VRAM address HL (VPOKE)
RDVRM           equ     $004A   ; read VRAM address HL -> A (VPEEK)

; --- Slot access BIOS entry points + work area (extension-ROM INIT scan) ----
; Source: MSX Assembly Page BIOS call list / MSX2 Technical Handbook. The
; slot-id byte format is the MSX2 TH slot architecture convention: bit 7 = slot
; expanded, bits 3-2 = secondary slot, bits 1-0 = primary slot. RDSLT destroys
; AF/BC/DE and preserves HL/IX/IY; CALSLT performs the inter-slot call.
RDSLT           equ     $000C   ; A = byte at (slot=A, addr=HL); reads any slot
CALSLT          equ     $001C   ; inter-slot call (slot=IYh, addr=IX)
EXPTBL          equ     $FCC1   ; expanded-slot flags, 1 byte/primary, bit7 = expanded
PSLTREG         equ     $A8     ; I/O port: primary slot select (page-1 field = bits 3-2)

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
; Cassette WRITE BIOS entry points (MSX Assembly Page / MSX2 Technical
; Handbook, cassette I/O chapter). All clobber every register (A,BC,DE,HL,IX
; etc.) — state must live in RAM across every TAPOUT call.
TAPOON          equ     $00EA   ; write tape header; A=0 short, A!=0 long; CF=fail
TAPOUT          equ     $00ED   ; write one byte (A); all registers clobbered; CF=fail
TAPOOF          equ     $00F0   ; flush carrier + motor off

; Cassette-write baud selection work area (MSX2 TH cassette chapter; addresses
; also in tape/PROVENANCE.md + tape/docs/spec-cassette.md). When a baud is chosen
; the system copies a reference LOW-signal-length word — CS120 (1200) or CS240
; (2400) — into the active slot; the tape write path's cas_baud reads the active
; slot to pick the rate. CSAVE"n",speed honours the speed by doing that same copy.
CS120_LOW       equ     $F3FC   ; 1200-baud reference low-signal length word
CS240_LOW       equ     $F401   ; 2400-baud reference low-signal length word
ACT_LOW         equ     $F406   ; active low-signal length word (the live baud)
; Reference low-signal-length VALUES. On a real MSX the main BIOS cold-init seeds
; CS120/CS240 and SCREEN,,,baud copies one into the active slot. Nothing seeds them
; in the C-BIOS + zerobas-tape stack: C-BIOS's cold-init doesn't, the zerobas-tape
; patch supplies the cassette *signal routines* (not stubbed!) but has no cold-init
; hook, and zerobas has no SCREEN,,,baud -- so they stay 0. CSAVE"n",speed therefore
; seeds the tables itself before selecting. cas_baud (tape.asm) only compares the active
; word to these for equality (the real timing is tape.asm's own constants), so the
; values need only be distinct — but we use the genuine ones the VG-8020 holds,
; captured black-box from work-area RAM (probes/tape/cas_baud_oracle.py; no ROM read):
; SCREEN,,,1 -> active LOW = 53 5C, SCREEN,,,2 -> active LOW = 25 2D.
CAS_LOW_1200    equ     $5C53   ; CS120 active-LOW word (bytes 53 5C)
CAS_LOW_2400    equ     $2D25   ; CS240 active-LOW word (bytes 25 2D)

; --- Cassette file identifiers --------------------------------------------
; Source: MSX2 Technical Handbook, cassette file format: the 10-byte file-type
; block before the filename selects the file kind. Binary (BSAVE) = $D0 x10;
; tokenised BASIC = $D3 x10; ASCII = $EA x10. zerobas reads $D0 (BLOAD), $D3
; (CLOAD / LOAD"CAS:") and $EA (CLOAD / LOAD"CAS:" ASCII, cas_ascii_load,
; cload.asm) — the device half (TAPION/TAPIN) is byte-stream agnostic; this id
; is interpreted by the interpreter half, exactly like BLOAD's $D0 check.
BINARY_ID       equ     $D0     ; BSAVE binary image
BASIC_ID        equ     $D3     ; tokenised BASIC program (CLOAD / LOAD"CAS:")
ASCII_ID        equ     $EA     ; ASCII program, SAVE"CAS:",A (CLOAD / LOAD"CAS:")

; --- Tokeniser / executor --------------------------------------------------
; Keyword tokens. Each value is an oracle observation (the crunch buffer KBUF
; dump), cross-checked against the MSX Assembly Page token table.
; Source: spec-tokenise.md (BLOAD) and spec-tokens-statements.md (REM/POKE/PEEK).
BLOAD_TOKEN     equ     $CF     ; spec-tokenise.md
; Cassette program-load keywords (MSX2 TH Table 2.20; oracle-confirmed
; byte-identical via basic_probe_crunch.py against the Philips VG-8020:
; `cload` -> $9B, `cload"name"` -> $9B "name"; `load"cas:name"` -> $B5
; "cas:name"). Both are single-byte statement tokens with the quoted filename
; kept verbatim, exactly like BLOAD's argument.
CLOAD_TOKEN     equ     $9B     ; CLOAD ["filename"] (cassette tokenised-BASIC load)
; CSAVE statement token: oracle-LOCKED (Philips VG-8020 KBUF via
; basic_probe_crunch.py: `csave"x"` -> $9A "x"; cross-checked MSX2 TH Table
; 2.20). Single-byte statement token; the quoted filename is kept verbatim
; ASCII, exactly like CLOAD. Adjacent to CLOAD ($9B) by MSX design.
CSAVE_TOKEN     equ     $9A     ; CSAVE "filename" (cassette tokenised-BASIC save)
LOAD_TOKEN      equ     $B5     ; LOAD "CAS:filename" (unified tape load)
; SAVE / BSAVE statement tokens are oracle-LOCKED (Philips VG-8020 KBUF via
; basic_probe_crunch.py; cross-checked MSX2 TH Table 2.20). Both are single-byte
; statement tokens, NOT $FF-prefixed. See PROVENANCE.md "SAVE / BSAVE statement
; tokens — oracle-locked" for the full KBUF evidence. NOTE: BSAVE_TOKEN ($D0)
; equals the cassette binary-file id BINARY_ID ($D0) by NUMERIC coincidence only
; — one is a keyword token in the crunch stream, the other a cassette header
; byte; they are kept as SEPARATELY NAMED constants on purpose (no collision).
SAVE_TOKEN      equ     $BA     ; SAVE "device:name"[,A]   (statement)
BSAVE_TOKEN     equ     $D0     ; BSAVE "device:name",start,end[,exec] (statement)
; Disk BASIC file-channel verbs (Phase 2). FILES token oracle-locked to the real
; National CF-3300 Disk BASIC crunch (MSX2 TH Table 2.20; confirmed byte-identical
; by basic_probe_crunch_disk.py). The handler lives in basic/files.asm.
FILES_TOKEN     equ     $B7     ; FILES ["filespec"] — list the directory (statement)
MERGE_TOKEN     equ     $B6     ; MERGE "name" — merge an ASCII program from disk (stmt)
; Sequential file-channel verbs (Phase 2 read path). Tokens oracle-LOCKED
; byte-identical to the Philips VG-8020 crunch (basic_probe_crunch.py: OPEN -> B0,
; INPUT -> 85, LINE -> AF, CLOSE -> B4; cross-checked MSX2 TH Table 2.20). "AS" and
; "#" are NOT tokenised (kept verbatim ASCII). Handlers live in basic/files.asm.
OPEN_TOKEN      equ     $B0     ; OPEN "name" FOR INPUT AS #n           (statement)
INPUT_TOKEN     equ     $85     ; INPUT #n,var$ (file form) / LINE INPUT (statement)
LINE_TOKEN      equ     $AF     ; LINE (only "LINE INPUT #n" supported in Phase 2)
CLOSE_TOKEN     equ     $B4     ; CLOSE [#n]                            (statement)
; PUT token: the 2nd half of "OUTPUT" (OUT $9C + PUT $B3 — two reserved words, not
; one keyword, oracle-observed) AND the random-access PUT statement (write a record).
; $B3, MSX2 TH 2.20.
PUT_TOKEN       equ     $B3     ; PUT — OUTPUT's 2nd half + random-access PUT statement
; Random-access record verbs (Phase 2c). Tokens oracle-LOCKED to the VG-8020 crunch
; (FIELD=$B1, GET=$B2, LSET=$B8, RSET=$B9; PUT=$B3 above; MSX2 TH Table 2.20),
; discovered by freezing at TAPION mid-BLOAD and reading KBUF — no disassembly.
;   field#1,2 as a$ -> B1 23 12 2C 13 20 41 53 20 41 24   (FIELD #1, 2 "AS" A$)
;   lset a$="x"     -> B8 20 41 24 EF 22 78 22            (LSET A$ = "x")
;   rset b$="y"     -> B9 ...                              (RSET B$ = "y")
;   get#1 / put#1,1 -> B2 23 12 / B3 23 12 2C 12          (GET/PUT a record)
; FIELD partitions a channel's record buffer into named slices; LSET/RSET write a
; string left/right-justified into a slice; GET/PUT read/write record N (byte offset
; (N-1)*256) of the file into/from that buffer. Handlers live in basic/field.asm. The
; "AS" keyword is kept verbatim ASCII.
FIELD_TOKEN     equ     $B1     ; FIELD #f, w AS v$[,...] — define record fields (stmt)
GET_TOKEN       equ     $B2     ; GET [#f][,rec] — read a record into the buffer (slice 2)
LSET_TOKEN      equ     $B8     ; LSET v$ = s$ — left-justify s$ into fielded v$ (stmt)
RSET_TOKEN      equ     $B9     ; RSET v$ = s$ — right-justify s$ into fielded v$ (stmt)
; File-info FUNCTIONS (Phase 2). $FF-prefixed function tokens (selector byte after
; PEEK_PREFIX), oracle-locked to the VG-8020 crunch (EOF=$FF$AB, LOF=$FF$AD;
; MSX2 TH Table 2.20). Evaluated in basic/expr.asm ev_f_ff.
EOF_TOKEN       equ     $AB     ; EOF(#n)  -> -1 at end of the input file, else 0
LOF_TOKEN       equ     $AD     ; LOF(#n)  -> length of the open file in bytes
DSKF_TOKEN      equ     $A6     ; DSKF(d)  -> free clusters on the drive (=free KB)
; Random-access conversion functions (Phase 2c). $FF-prefixed function tokens,
; oracle-locked to the VG-8020 crunch (MKI$=$FF$AE, CVI=$FF$A8; MSX2 TH Table 2.20).
; MKI$(n) packs a 16-bit int into a 2-byte little-endian string; CVI(s$) is the
; inverse. The float siblings (MKS$/MKD$/CVS/CVD) need Phase-3 floats and are
; deferred. MKI$ is evaluated in basic/strvar.asm (string result); CVI in
; basic/expr.asm ev_f_ff (numeric result, string argument).
MKI_TOKEN       equ     $AE     ; MKI$(n)  -> 2-byte LE string of integer n
CVI_TOKEN       equ     $A8     ; CVI(s$)  -> integer from the first 2 bytes of s$
; File/directory management (Phase 2). Tokens oracle-locked to the VG-8020 crunch
; (KILL=$D4, NAME=$D3; MSX2 TH Table 2.20). The handlers live in basic/files.asm.
KILL_TOKEN      equ     $D4     ; KILL "name" — delete a file (statement)
; MAXFILES config (Phase 2). Oracle-LOCKED: the VG-8020 crunches "MAXFILES" to TWO
; reserved words — MAX ($CD) + FILES ($B7) — exactly like OUTPUT = OUT+PUT (proven
; byte-identical by basic_probe_crunch.py: `max` -> $CD, `files` -> $B7,
; `maxfiles=2` -> $CD $B7 $EF $13). So zerobas adds a "MAX" reserved word and forms
; MAXFILES = MAX+FILES; the statement is dispatched on $CD (then requires $B7).
MAX_TOKEN       equ     $CD     ; MAX — 1st half of MAXFILES (statement: MAX FILES = n)
; NAME crunch token. Same VALUE as BASIC_ID ($D3) but a DIFFERENT namespace — this
; is a keyword token in the crunch stream; BASIC_ID is a cassette file-format byte.
; Kept as separately-named constants on purpose (no collision), like SAVE/BSAVE.
NAME_TOKEN      equ     $D3     ; NAME "old" AS "new" — rename a file (statement)
REM_TOKEN       equ     $8F     ; spec-tokens-statements.md; swallows rest of line
POKE_TOKEN      equ     $98     ; spec-tokens-statements.md
; PEEK is a *function* token: a $FF prefix followed by a second byte.
PEEK_PREFIX     equ     $FF     ; spec-tokens-statements.md (function-token prefix)
PEEK_TOKEN      equ     $97     ; spec-tokens-statements.md
; LEN is a $FF-prefixed function token too (used here only as the OPEN..AS #n
; LEN= record-size clause keyword, not the string LEN() function). Its suffix sits
; 5 slots before PEEK ($97) in the core MSX-BASIC function table (…STR$ $93, LEN
; $92, VAL $94…); the LEN= gate (test_open_len / diskbasic-acceptance) types a real
; LEN= line, so a wrong suffix here fails the parse and the gate catches it.
LEN_TOKEN       equ     $92     ; LEN function-token suffix (after PEEK_PREFIX)
; Memory / I-O access tokens (MSX2 TH Table 2.20; oracle-confirmed byte-for-byte
; via basic_probe_crunch.py — see PROVENANCE.md). VPOKE / OUT are one-byte
; statement tokens; VPEEK / INP are $FF-prefixed two-byte function tokens (like
; PEEK); VARPTR / BASE are single-byte function tokens (no $FF prefix).
VPOKE_TOKEN     equ     $C6     ; VPOKE addr,value (statement)
OUT_TOKEN       equ     $9C     ; OUT port,value   (statement)
VPEEK_TOKEN     equ     $98     ; VPEEK(addr) -> $FF $98 (function)
INP_TOKEN       equ     $90     ; INP(port)   -> $FF $90 (function)
VARPTR_TOKEN    equ     $E7     ; VARPTR(var) (single-byte function token)
BASE_TOKEN      equ     $C9     ; BASE(n)     (single-byte function token)
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
; --- Phase 2: MAXFILES multi-channel control (free $E011.. gap below CURPTR) ---
; The Phase-2 file verbs gained a real multi-channel table (retiring the single-
; channel limit). FCH_CEIL channels can be open at once. Because fat.asm keeps ONE
; global set of streaming state (FSECTOR_BUF + the FREAD_*/FWR_*/FAT_CUR* scratch),
; only one channel's state is "live" in those globals at a time; each channel also
; owns a context block (FCH_CTX) holding a saved copy. A write-back cache discipline
; swaps state in/out: FCH_ACTIVE names the channel whose state is currently live,
; FCH_MODE/FCH_NUM mirror it, and a switch saves the old globals to its ctx and
; loads the new one's. fat.asm is untouched (its oracle validation holds). The
; ceiling is RAM-bounded (each ctx = 50-byte state save + a 512-byte data buffer);
; real MSX MAXFILES is RAM-bounded too, just to a larger value — documented
; divergence. See basic/files.asm §channel manager + PROVENANCE.md §MAXFILES.
MAXF            equ     $E011   ; current MAXFILES ceiling (0..FCH_CEIL); default 1 (1)
FCH_ACTIVE      equ     $E012   ; channel live in the engine globals, 0 = none (1)
FCH_MODES       equ     $E013   ; per-channel mode array [0..FCH_CEIL]; [0] unused,
                                ; [ch] = 0 closed / 1 INPUT / 2 OUTPUT (FCH_CEIL+1 bytes)
INDLR_N         equ     $E016   ; INPUT$(n,#f): remaining bytes to read (transient, 1)
MRG_PTR         equ     $E017   ; MERGE: write cursor into LINEBUF for the current line (2)
; Random-access (FIELD/LSET/RSET) transient parse/store scratch (Phase 2c slice 1).
; All dead outside a single FIELD or LSET/RSET statement. Free $E019.. gap below
; CURPTR ($E020). See basic/field.asm + PROVENANCE.md §random-access records.
FLD_CUROFF      equ     $E019   ; FIELD: running byte offset into the record buffer (2)
FLD_CHAN        equ     $E01B   ; FIELD/LSET/RSET: the channel being fielded (1)
LRSET_JUST      equ     $E01C   ; LSET/RSET: 0 = left-justify, 1 = right-justify (1)
LRSET_W         equ     $E01D   ; LSET/RSET: destination field width (1)
LRSET_OFF       equ     $E01E   ; LSET/RSET: destination field offset in the buffer (2)
RUNFLAG         equ     $E02F   ; 1 = ,R handoff requested (set while parsing)
CLPTR           equ     $E02B   ; CLOAD/LOAD: store cursor into the program area (2)
CLINK           equ     $E02D   ; CLOAD/LOAD: saved link word of the current line
                                ; (= the saving machine's absolute start address of
                                ; the line; used to derive each line's body length
                                ; from consecutive link-word differences) (2)
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

; --- Phase 1: minimal string-variable store (own-design; see PROVENANCE.md) --
; A `$`-suffixed variable (e.g. A$) holds a short string value. This is a
; deliberately minimal own-design store — NOT the reference ROM's string heap +
; descriptor layout (that is Phase 2, and reproducing it would need a forbidden
; source). Each string variable is a fixed-capacity inline record keyed by the
; same 2-character [name0][name1] key as a numeric variable:
;     [name0:1][name1:1][len:1][bytes:STRMAX]
; name0 = 0 marks a free slot; len is the live byte count (0..STRMAX). There is
; no shared heap and no growth: a value longer than STRMAX is truncated. This is
; "enough for PRINT" — assign a literal / copy a string var, then PRINT it.
STRTAB          equ     $E240   ; base of the string-variable store
STRMAX          equ     32      ; max chars held per string variable (own choice)
STRENTSZ        equ     3 + STRMAX  ; [name0][name1][len][bytes:STRMAX] = 35
STRSLOTS        equ     8       ; max distinct string variables (280 bytes)
STREND          equ     STRTAB + STRSLOTS*STRENTSZ   ; $E358

; Expression value-type signalling (own-design VALTYP notion). After eval_any /
; a factor, VALTYP says whether the result is a number (0; value in DE as usual)
; or a string (1; STRPTR points at a [len:1][bytes...] descriptor). Kept minimal:
; only LET and PRINT consult it; arithmetic stays numeric-only.
VALTYP          equ     $E0C8   ; 0 = numeric result, 1 = string result (1 byte)
STRPTR          equ     $E0C9   ; pointer to the [len][bytes] descriptor (2 bytes)
; PRINT output destination (Phase 2 PRINT#). 0 = screen (CHPUT), 1 = the open
; file channel (fat_io_putbyte). The print primitives emit through `pchar`, which
; consults this. Zeroed at cold start (init_filechan) and re-cleared at every
; statement boundary / the REPL prompt / stmt_error, so only PRINT#'s own item
; loop ever sees 1. Free byte in the $E0CB gap (NUMBUF/VALTYP/STRPTR below it).
PRDEST          equ     $E0CB   ; PRINT destination: 0=screen, 1=file channel (1)
; When PRDEST=1, PRDEV selects WHICH sink pchar uses: 0 = disk file (fat_io_putbyte),
; 1 = LPT printer (LPTOUT), 2 = CRT screen (CHPUT). Set by PRINT#'s channel classify;
; only read while PRDEST=1, so its staleness between statements is harmless. A "device
; channel" (LPT:/CRT:) stores FCH_MODES[ch]=LPT_MODE/CRT_MODE and owns no fat.asm
; context. OO_DEVTYPE is the transient device type stashed across the OPEN parse.
; Free bytes in the $E0CC gap (below CONTLINE $E0D0).
PRDEV           equ     $E0CC   ; PRINT# device sink selector (1)
OO_DEVTYPE      equ     $E0CD   ; OPEN device-channel type being parsed (transient, 1)
; ascii_read_lines' byte-source vector (files.asm D2 getbyte indirection; the
; read-side mirror of PRDEST/PRDEV above). Holds the address of the routine
; arl_getbyte (files.asm) jumps into for the next file byte: A=byte/CF clear,
; or CF set = no more data — the same contract fat_io_getbyte already has.
; Defaulted to fat_io_getbyte at cold start (init_filechan) so MERGE and disk
; ASCII LOAD are byte-for-byte unchanged; cload.asm's cas_ascii_load re-points
; it at cal_getbyte (a TAPIN wrapper) for the duration of a cassette ASCII
; load, then restores the default before returning. Fills the last 2 bytes of
; the $E0CC gap (below CONTLINE $E0D0).
ARL_GETBYTE     equ     $E0CE   ; ascii_read_lines byte-source vector (2)
LPT_MODE        equ     5       ; FCH_MODES value: channel open to the LPT: printer device
CRT_MODE        equ     6       ; FCH_MODES value: channel open to the CRT: screen device
; Cassette sequential channels (OPEN"CAS:name" FOR OUTPUT|INPUT). Like LPT/CRT
; these own NO fat.asm context (never fch_select'd) — PRINT#/INPUT#/CLOSE classify
; them straight from FCH_MODES. Their byte layer is the M1/M2 cassette-ASCII block
; buffer at $E600 (CAL_BUF/CAS_WBUF), so a cassette channel and a disk file channel
; must NOT be interleaved (they share that buffer) — documented, and matching the
; real-MSX single-cassette-file norm. Values chosen > CRT_MODE so the existing
; ">= LPT_MODE = device channel" tests still hold.
CAS_OUT_MODE    equ     7       ; FCH_MODES value: OPEN"CAS:" FOR OUTPUT (PRINT# -> tape sink)
CAS_IN_MODE     equ     8       ; FCH_MODES value: OPEN"CAS:" FOR INPUT (INPUT# <- tape source)
; Scratch descriptor for a string literal lifted out of the token stream
; ([len:1][bytes:STRMAX]); LET copies from here into the variable's slot. Placed
; in page $E3 above the string table (NOT in page $E0, which the C-BIOS keyboard
; ISR's work area touches — an EI'd interrupt mid-LET would corrupt a $E0 byte).
STRSCR          equ     $E360   ; [len][bytes:STRMAX] = 33 bytes ($E360..$E380)

; --- Step B: stored-program text area (numbered lines) ---------------------
; Numbered lines are stored in the real MSX line-link format at the real text
; base, so a stored program's bytes match a reference ROM's (Step A's crunch
; gives byte-identical line bodies; storing at the same base gives identical
; link pointers). Each line: [link:2 LE][lineno:2 LE][tokens...][00]; the
; program ends with a link word of $0000.
; Source: TXTTAB sysvar $F676 and its post-boot value $8001 are oracle-confirmed
; (basic/docs/spec-bload-r.md §4 — "sourced"); the line-link
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
; PRINT USING formatted output. USING is a reserved word ($E4; oracle-locked to the
; VG-8020 crunch: `print using"###";5` -> 91 20 E4 22 23 23 23 22 3B 16, and
; `a$=using` -> ... EF E4). The format string is kept verbatim ASCII in its quotes.
; Handled in basic/printusing.asm (reached from ex_print on the USING token).
USING_TOKEN     equ     $E4     ; USING (PRINT USING "fmt"; values)
; CALL — extended-statement dispatch (CALL <name> or the '_' abbreviation). CALL is a
; reserved word ($CA; oracle-locked: `call format` -> CA 20 46 4F 52 4D 41 54, the
; name kept verbatim ASCII; `_format` -> 5F 46 ... i.e. '_' is a literal, not a token).
; zerobas handles only CALL FORMAT (basic/format.asm); other names error.
CALL_TOKEN      equ     $CA     ; CALL <name>  (extended statement)
NEXT_TOKEN      equ     $83
DATA_TOKEN      equ     $84
READ_TOKEN      equ     $87
RESTORE_TOKEN   equ     $8C
RUN_TOKEN       equ     $8A
NEW_TOKEN       equ     $94
END_TOKEN       equ     $81
STOP_TOKEN      equ     $90
ON_TOKEN        equ     $95
CONT_TOKEN      equ     $99     ; CONT (resume a STOPped/broken program). Oracle-
                                ; confirmed byte-identical via basic_probe_crunch.py
                                ; against the Philips VG-8020 (`cont` -> $99);
                                ; cross-checks MSX2 TH Table 2.20.
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
; CONT / Ctrl-STOP break-resume state (own-design; see PROVENANCE.md). When a
; running program is broken by the STOP statement or by Ctrl-STOP (BREAKX), the
; run loop records exactly where to resume: CONTLINE = the link-field address of
; the line that was interrupted (same meaning as CURLINE), CONTPTR = the token
; position at which to continue (the statement after STOP, or the start of the
; next line for a Ctrl-STOP between lines). CONTVALID = 1 means "a CONT resume
; point is live". Editing the program (store_line / NEW) clears CONTVALID so CONT
; then errors with "Can't CONTINUE", matching the reference's behaviour.
CONTLINE        equ     $E0D0   ; saved CURLINE for CONT (2)
CONTPTR         equ     $E0D2   ; saved resume token pointer for CONT (2)
CONTVALID       equ     $E0D4   ; 1 = a CONT resume point is valid (1)
; Extension-ROM INIT scan scratch (initext.asm). Used ONCE at INIT, entirely
; under `di`, and dead afterwards; free page-3 RAM in the $E0D5..$E0FF gap
; (between CONT state and LINEBUF). RDSLT clobbers AF/BC/DE, so the slot id and
; INIT address are held here across reads rather than in registers.
SCAN_PRIM       equ     $E0D5   ; primary slot currently being scanned (1)
SCAN_SLOT       equ     $E0D6   ; candidate slot id for RDSLT/CALSLT (1)
SCAN_INIT       equ     $E0D7   ; candidate ROM's INIT entry address (2)
SCAN_IY         equ     $E0D9   ; CALSLT slot word: high byte = slot (IYh) (2)
; Disk filename scratch (the disk loader/saver verbs). Built by parse_disk_fcb;
; the loader-side FAT12 engine (basic/fat.asm) consumes the 8.3 NAME field directly
; — fat_find / fat_dir_create take an 11-byte name pointer, no FCB needed. The +0
; drive code is kept (parse fills it) but the engine ignores it (single drive A);
; it is forward-compat only. NAME +0..+10 = the 11-byte 8.3 field (8 name + 3 ext,
; space-padded $20, UPPER-CASE). Placed in the free page-3 gap after the INIT-scan
; scratch and clear of the FAT engine's buffers (page $E5+). The "FCB" name is
; retained for continuity with the parser; only the NAME field is load-bearing now.
; See basic/PROVENANCE.md §disk-BLOAD scratch FCB / §disk DSKIO host engine.
DISK_FCB        equ     $E0DB   ; scratch name block ($E0DB.., 12 bytes)
DISK_FCB_DRV    equ     DISK_FCB        ; +0: drive code (0=default,1=A,2=B; ignored)
DISK_FCB_NAME   equ     DISK_FCB + 1    ; +1..+11: 8.3 name field (11 bytes)
; Disk-ROM slot id recorded by the INIT scan (initext.asm) when it inits an
; external "AB" ROM, so the disk verbs can CALSLT the disk ROM's standard DSKIO
; ($4010) across slots (basic/fat.asm dskio_calslt). The combined machine has
; exactly one external AB ROM (the disk ROM), so this is unambiguous; a multi-ROM
; setup would need per-ROM tracking (documented limit, see PROVENANCE.md §disk-ROM
; slot capture). DISKSLOT_OK = 1 once a slot was recorded. Free page-3 RAM in the
; $E0E7.. gap (after the name block, before LINEBUF at $E100). See basic/
; PROVENANCE.md §disk-ROM slot capture.
DISKSLOT        equ     $E0E7   ; disk ROM slot id for CALSLT (1)
DISKSLOT_OK     equ     $E0E8   ; 1 = DISKSLOT holds a valid disk-ROM slot id
; BSAVE/BLOAD ",S" VRAM select (page $E0 free gap $E0E9..$E0EC; dead outside a
; BSAVE/BLOAD). 1 = the ",S" flag was given -> the data bytes stream to/from VRAM
; (RDVRM/WRTVRM) instead of RAM; the $FE header start/end/exec are stored/read
; verbatim as VRAM addresses. Cleared at the top of every BSAVE/BLOAD parse.
VRAM_FLAG       equ     $E0E9   ; 1 = ",S" VRAM save/load (1)
; Cassette ASCII load (cload.asm cal_getbyte) read position within the current
; 256-byte tape block, 0..255 (§0.1: fixed 256-byte tape data blocks). Also the
; refill trigger: == 0 at getbyte entry means "buffer drained -> slurp the next
; block". Dead outside a cassette ASCII LOAD/CLOAD — never live at the same time
; as a BSAVE/BLOAD ",S" — so it reuses the same free gap (like IN_RDLEN and
; FILES_ENTIDX below overlay each other).
CAL_CNT         equ     $E0EA   ; cassette ASCII load: read position in the
                                ; current 256-byte tape block, 0..255 (1)
CAL_NEEDFILL    equ     $E0EB   ; cassette ASCII load: 1 = CAL_BUF drained, the
                                ; next cal_getbyte must TAPION+refill (blocks 2+);
                                ; block 1 is primed promptly by cas_ascii_load so
                                ; its TAPION stays in TAPION's di regime (1)
; Cassette ASCII SAVE (save.asm cas_wbyte) block-fill counter: bytes buffered into
; CAS_WBUF for the current 256-byte tape data block, 0..255 (§0.1). cas_wbyte does
; NOT TAPOUT per byte — like the READ side's block buffer, tape signalling is
; real-time on WRITE too, so interleaving list_walk's detokenise work between TAPOUTs
; would insert non-uniform inter-byte gaps that desync TAPIN on reload (confirmed:
; a 2-line file read back only "10 " before losing sync). So bytes accumulate in RAM
; and a FULL block is flushed (cas_flush_block) in one tight TAPOUT*256 loop — the
; write mirror of cal_refill's tight TAPIN*256 slurp. When a byte fills the 256th
; slot the counter wraps to 0 and cas_flush_block emits the block; the same counter
; then drives the flush loop (it is 0 at flush entry). Dead outside a cassette ASCII
; SAVE — never live with a BSAVE (VRAM_FLAG) or a cassette ASCII LOAD (CAL_CNT) — so
; it reuses the same $E0E9..$E0EC free gap (the last byte, $E0EC).
CAS_WCNT        equ     $E0EC   ; cassette ASCII save: bytes buffered in the
                                ; current 256-byte tape data block, 0..255 (1)
; SAVE / BSAVE program-image source-walk pointers (page $E0; dead outside a
; SAVE/BSAVE). DSV_PTR / DSV_END drive do_save's program-image source walk and
; disk_putword's word-emit (the FAT12 engine's own write buffering lives in its
; FWR_* scratch, basic/fat.asm — NOT here).
DSV_PTR         equ     $E0ED   ; SAVE: current source byte pointer (2)
DSV_END         equ     $E0EF   ; SAVE/BSAVE: last source byte addr, inclusive (2)
; Tape CSAVE / BSAVE write scratch (page $E0, $E0F1.. gap; dead outside a tape
; CSAVE/BSAVE). All state lives in RAM — TAPOUT clobbers every register, so no
; register can survive a TAPOUT call.
TSV_PTR         equ     $E0F1   ; tape save: current source-byte pointer (2)
TSV_END         equ     $E0F3   ; tape save: last source-byte address, inclusive (2)
TSV_CNT         equ     $E0F5   ; tape save: loop counter (1)
TSV_NAME        equ     $E0F6   ; tape save: 6-char filename buffer (space-padded)
; Disk BASIC FILES scratch (page $E0; dead outside a FILES listing). One byte in
; the $E0FC.. gap below LINEBUF ($E100). The dir-walk position lives in the
; fat.asm FAT_DIRSEC/FAT_DIRREM scratch; only the per-sector entry index needs a
; home that survives the CHPUT register clobber.
FILES_ENTIDX    equ     $E0FC   ; FILES: dir entry index 0..15 within a sector (1)
; Sequential file-channel state (Phase 2). A SINGLE open channel for now (the
; loader/file engine has one global FREAD_*/FWR_* state); a MAXFILES channel table
; is a later sub-item. FCH_NUM/FCH_MODE persist across statements (OPEN … : LINE
; INPUT … : CLOSE); FCH_RDMODE + IN_RDLEN are transient within one read statement.
FCH_NUM         equ     $E0FD   ; open channel's file number, 0 = none open (1)
FCH_MODE        equ     $E0FE   ; open mode: 0=none, 1=INPUT, 2=OUTPUT (1)
FCH_RDMODE      equ     $E0FF   ; current read: 0=INPUT# (stop at ','/CR), 1=LINE (1)
; The read-length counter overlays FILES_ENTIDX ($E0FC): FILES and a file read are
; distinct statements that never run at the same instant, and the per-sector entry
; index is dead outside do_files, so the byte is reused (collision-checked).
IN_RDLEN        equ     $E0FC   ; INPUT#/LINE INPUT#: bytes stored so far (1)
; Disk BSAVE on-disk binary-file header (MSX-BASIC file formats, an allowed
; public language reference). 7 bytes, then raw
; data: [$FE][start:2 LE][end:2 LE][exec:2 LE]. This is the DISK format and is
; DIFFERENT from the cassette header (10x $D0 + 6-char name + addresses); the
; filename lives in the directory entry, not the file body. Data bytes run
; start..end inclusive.
BSAVE_DISK_ID   equ     $FE     ; on-disk BSAVE binary-file marker
; On-disk TOKENISED-BASIC file marker. A BASIC program SAVEd to disk in the
; default (tokenised, non-",A") form is a single leading $FF byte followed by the
; in-memory program image (the same line-link chain do_tape_prog reads:
; [link:2 LE][lineno:2 LE][tokens...][00] per line, ending in a $0000 link word).
; This is DISTINCT from the BSAVE binary's $FE marker above. Source: MSX-BASIC
; file formats (the same allowed public-language-reference class the $FE BSAVE
; marker was sourced from). LOAD"filename" verifies
; this marker (mismatch -> load_error). See basic/PROVENANCE.md §disk LOAD.
BASIC_DISK_ID   equ     $FF     ; on-disk tokenised-BASIC program marker

; --- Phase 1.5: loader-side FAT12 engine over the STANDARD DSKIO ($4010) ----
; basic/fat.asm runs the FAT12 read+write engine HOST-side (in zerobas-BASIC),
; driving the in-slot disk ROM's standard physical-sector entry DSKIO at $4010
; across slots (CALSLT). This replaces the private bdos_entry ($F37D) path so the
; loader is disk-ROM-independent: any standard MSX1 disk ROM (our own or a foreign
; one, e.g. the National CF-3300) services the same loader unchanged. The engine
; and these scratch addresses are PORTED from disk/disk.asm (our own clean-room
; FAT12 code); see basic/fat.asm header + basic/PROVENANCE.md §disk DSKIO host engine.
;
; DSKIO_ENTRY: the disk-ROM interface table's DSKIO offset. The standard MSX disk
; ROM header is 16 bytes, so the six fixed JP entries start at base+$10 (DSKIO),
; +$13 (DSKCHG), +$16 (GETDPB)... — MSX2 Technical Handbook §5, disk-ROM interface;
; cross-checked by black-box CF-3300 observation (disk/docs/expansion-protocol.md
; §3). The ROM base is $4000 for a page-1 disk ROM, so DSKIO sits at $4010. The
; loader needs ONLY DSKIO + the on-disk BPB (no GETDPB on the host side).
DSKIO_ENTRY     equ     $4010   ; standard DSKIO entry (ROM base $4000 + $10)
; BPB field offsets within the boot sector (Microsoft FAT spec §3.1).
BPB_BYTSPERSEC  equ     11      ; bytes per sector (word LE)
BPB_SECPERCLUS  equ     13      ; sectors per cluster (byte)
BPB_RSVDSECCNT  equ     14      ; reserved sectors incl. boot (word LE)
BPB_NUMFATS     equ     16      ; number of FAT copies (byte)
BPB_ROOTENTCNT  equ     17      ; max root-directory entries (word LE)
BPB_FATSZ16     equ     22      ; sectors per FAT copy (word LE)
; FAT directory-entry field offsets + the end-of-chain marker (Microsoft FAT spec
; §3.2/§3.4).
DIRENT_FIRSTCLUS equ    26      ; first-cluster word (LE) within a dir entry
DIRENT_FILESIZE equ     28      ; file-size dword (LE) within a dir entry
EOC             equ     $0FFF   ; end-of-chain marker we write (Microsoft FAT §3.2)
;
; Scratch RAM (page-3 RAM; NOT part of the ROM image). The host buffers below are
; placed ABOVE all basic-core RAM (which tops out at STRSCR $E360..$E380).
;
; CROSS-COMPONENT OVERLAP INVARIANT (the load-bearing one — read before moving any
; address here). On the combined machine these host buffers ($E5C0..$E9FB) OVERLAP
; zerobas-disk's own scratch: disk SECTOR_BUF $E2A0..$E49F sits just below, and disk
; WBUF $E560..$E75F overlaps FSECTOR_BUF directly. This is safe ONLY because the
; host drives zerobas-disk exclusively through the raw DSKIO ($4010) entry, and
; DSKIO touches just its FDC work bytes ($E29A..$E29F) + the caller's HL buffer —
; it never reaches disk's SECTOR_BUF / WBUF (those belong to disk's GETDPB / bdos
; FAT paths, which the host never calls: it owns FAT12 itself via basic/fat.asm and
; parses the BPB directly, never invoking $4016 GETDPB). Break that discipline —
; e.g. make the host call $4016, or route disk DSKIO through SECTOR_BUF — and these
; buffers corrupt silently. No compile-time guard enforces it (two separate
; assembly units); the contract lives here and in disk/disk.asm's scratch map.
; A *foreign* disk ROM's DSKIO scratch is outside our control and could in principle
; collide with this region; the CF-3300 oracle keeps its work area in the
; $F2xx-$F3xx sysvar block (MSX2 TH work area), clear of page $E2/$E5/$E7/$E9, so it
; survives — but that is an observed property of that ROM, not a guarantee.
;
; Two independent 512-byte sector buffers: FSECTOR_BUF holds the file's in-flight
; READ sector OR the data being accumulated for a WRITE; FWBUF is used by the
; FAT/dir metadata helpers (alloc / link / dir create/update) so a cluster scan or
; dir stamp never disturbs FSECTOR_BUF's in-flight data (same discipline as
; disk.asm's SECTOR_BUF/WBUF split). Placed at $E5C0/$E7C0 — above basic-core RAM
; and the old disk-ROM DTA region, in 64 KB page-3 RAM.
FSECTOR_BUF     equ     $E5C0   ; file data / read sector buffer ($E5C0..$E7BF)
FWBUF           equ     $E7C0   ; FAT/dir metadata sector buffer ($E7C0..$E9BF)
; FAT12 geometry, filled by fat_mount from the on-disk BPB (own-choice free RAM in
; page $E9 above the buffers).
FAT_SECPERCLUS  equ     $E9C0   ; sectors per cluster (byte)
FAT_FATSTART    equ     $E9C1   ; first FAT sector (= reserved sectors) (word)
FAT_FIRSTROOT   equ     $E9C3   ; first root-directory sector (word)
FAT_ROOTSECS    equ     $E9C5   ; number of root-directory sectors (word)
FAT_FIRSTDATA   equ     $E9C7   ; first data sector (word)
FAT_CURCLUS     equ     $E9C9   ; current cluster in the open file's chain (word)
FAT_CLUSSEC     equ     $E9CB   ; sector index within current cluster (byte)
FAT_FIRSTCLUS   equ     $E9CC   ; first cluster of the found file (word)
FAT_FILESIZE    equ     $E9CE   ; file size in bytes (4-byte LE)
FAT_NUMFATS     equ     $E9D2   ; number of FAT copies (byte; from BPB +16)
FAT_SECPERFAT   equ     $E9D3   ; sectors per FAT copy (word; from BPB +22)
; FAT12 working scratch (transient within a single call).
FAT_PARITY      equ     $E9D5   ; 1 = odd cluster, 0 = even (FAT12 nibble pack)
FAT_BYTEIDX     equ     $E9D6   ; byte index within a FAT sector (word, 0..511)
FAT_FATSEC      equ     $E9D8   ; FAT sector currently read (word)
FAT_B0          equ     $E9DA   ; first FAT byte of a 12-bit entry
FAT_B1          equ     $E9DB   ; second FAT byte of a 12-bit entry
FAT_NAMEPTR     equ     $E9DC   ; -> 11-byte search name (word)
FAT_DIRSEC      equ     $E9DE   ; current root-dir sector being scanned (word)
FAT_DIRREM      equ     $E9E0   ; root-dir sectors remaining to scan (word)
FAT_WRTMP       equ     $E9E2   ; transient scratch for the FAT12 write helpers (word)
FAT_WRTMP2      equ     $E9E4   ; second transient (free-cluster scan cached sector)
; Read byte-stream state (fat_io_open / fat_io_getbyte).
FREAD_OFF       equ     $E9E6   ; next byte index within FSECTOR_BUF (0..512) (word)
FREAD_LEFT      equ     $E9E8   ; bytes of the open file still undelivered (4-byte LE)
; Write byte-stream state (fat_io_create / fat_io_putbyte / fat_io_close).
FWR_CLUS        equ     $E9EC   ; chain-tail cluster currently being filled (word)
FWR_FIRST       equ     $E9EE   ; file's first cluster, 0 until first allocated (word)
FWR_SECIDX      equ     $E9F0   ; sector index within the current cluster (byte)
FWR_BUFLEN      equ     $E9F1   ; bytes currently buffered in FSECTOR_BUF (word, 0..512)
FWR_BYTES       equ     $E9F3   ; total bytes written so far = final file size (4-byte LE)
FWR_DIRSEC      equ     $E9F7   ; logical sector holding the open file's dir entry (word)
FWR_DIROFF      equ     $E9F9   ; byte offset of that dir entry within its sector (word)
; --- Phase 2: MAXFILES per-channel context blocks --------------------------
; A channel's live streaming state spans TWO global regions: the 512-byte data
; buffer FSECTOR_BUF, and a contiguous engine-state span FCH_STATE0..(+FCH_STATESZ).
; That span ($E9C9..$E9FA) covers every per-channel value — the read iterator
; (FAT_CURCLUS/FAT_CLUSSEC), file meta (FAT_FIRSTCLUS/FAT_FILESIZE for LOF), the
; read stream (FREAD_OFF/FREAD_LEFT) and the whole write state (FWR_*). It also
; spans a few shared/transient bytes (FAT_NUMFATS/FAT_SECPERFAT geometry, the
; FAT_B0/FAT_BYTEIDX/... scratch) — harmless to save/restore (identical across
; channels on one drive, or dead between statements). The mount geometry proper
; (FAT_SECPERCLUS..FAT_FIRSTDATA at $E9C0..$E9C8) sits BELOW the span and stays
; SHARED — correct for a single drive (every fat_mount re-derives it identically).
; Each context block = [state:FCH_STATESZ][buffer:512]; FCH_CEIL of them live in
; clean high RAM ($EA00..), clear of all basic-core + zerobas-disk scratch (disk
; tops out at WBUF $E75F; C-BIOS sysvars start ~$F380). FCH_CEIL=2 fits cleanly
; (2*562 = $0464 -> $EA00..$EE63). Growing it = bump FCH_CEIL once RAM is found.
FCH_CEIL        equ     2       ; max simultaneously-open channels (RAM-bounded)
FCH_STATE0      equ     FAT_CURCLUS         ; $E9C9 — base of the per-channel state span
FCH_STATESZ     equ     FWR_DIROFF+2-FCH_STATE0     ; $E9C9..$E9FA inclusive = 50 bytes
FCH_CTXSZ       equ     FCH_STATESZ + 512   ; one context block = state + data buffer
FCH_CTX         equ     $EA00   ; FCH_CEIL context blocks, each [state][512-byte buf]
; --- Phase 2c slice 1: random-access FIELD table + fielded-read scratch -----
; zerobas stores string vars INLINE in STRTAB ([name0][name1][len][bytes:32]); a
; MS-BASIC-style descriptor pointing into a record buffer does not exist. So a
; FIELDed variable is recorded HERE instead: a side table maps a var key to a slice
; (channel, byte offset, width) of that channel's record buffer (= FSECTOR_BUF while
; the channel is active, swapped by the write-back cache). str_eval consults it on
; READ (building a transient [len][bytes] descriptor in FLD_DESC from the slice);
; LSET/RSET write into the slice. Placed in clean high RAM above FCH_CTX (which ends
; at $EE63: $EA00 + FCH_CEIL*FCH_CTXSZ = $EA00 + 2*562 = $EE64) and below the C-BIOS
; sysvars (~$F380). See basic/field.asm + PROVENANCE.md §random-access records.
FLD_ENTSZ       equ     6       ; field entry = [chan:1][k0:1][k1:1][off:2][wid:1]
FLD_SLOTS       equ     16      ; max simultaneously-defined fields (own choice)
FLD_TAB         equ     $EE64   ; field table base ($EE64..$EEC3, 96 bytes)
FLD_TABEND      equ     FLD_TAB + FLD_SLOTS*FLD_ENTSZ   ; $EEC4
; --- Phase 2c slice 2: GET/PUT random-record I/O scratch -------------------
; Transient (dead outside a single GET/PUT statement; one statement runs at a time,
; so not per-channel). The disk-position walk survives read_sector/CALSLT clobbers
; by keeping its loop state here in RAM. Free gap above FLD_TAB, below FLD_DESC
; ($EEC4..$EEFF = 60 bytes). See basic/field.asm §GET/PUT.
GP_RECNO        equ     $EEC4   ; record number (1-based, 2)
GP_SEC          equ     $EEC6   ; file logical-sector index of the record (2)
GP_WITHIN       equ     $EEC8   ; byte offset of the record within its sector (0/256, 2)
GP_CLUS         equ     $EECA   ; current cluster during the chain walk (2)
GP_CLIDX        equ     $EECC   ; cluster steps still to walk (2)
GP_SECINCL      equ     $EECE   ; sector index within the final cluster (1)
GP_PHYS         equ     $EECF   ; resolved absolute physical sector (2)
GP_OLDNSEC      equ     $EED1   ; file's old sector count (ceil(size/512), 2)
GP_FLAGS        equ     $EED3   ; bit0 = extend (PUT allocates; GET does not) (1)
GP_MODE         equ     $EED4   ; 0 = GET (read), 1 = PUT (write) (1)
GP_CHAN         equ     $EED5   ; the channel number being GET/PUT (1)
; --- PRINT USING formatted-output scratch (Phase 2) ------------------------
; Transient (dead outside one PRINT USING statement). The format string is copied
; here so it survives the str_eval calls that evaluate the string VALUES (a literal
; format lives in the volatile STRSCR otherwise). Free gap $EED6..$EEFF, below
; FLD_DESC ($EF00). See basic/printusing.asm.
PU_FMT          equ     $EED6   ; copied format string ($EED6..$EEF5, 32 chars)
PU_FMTMAX       equ     32      ; format length cap (longer formats truncate)
PU_FMTLEN       equ     $EEF6   ; live format length (1)
PU_POS          equ     $EEF7   ; current scan index into PU_FMT (1)
PU_W            equ     $EEF8   ; current field width (1)
PU_TYPE         equ     $EEF9   ; field type: 0 num #, 1 str &, 2 str !, 3 str \..\ (1)
PU_FLAGS        equ     $EEFA   ; bit0 = trailing separator (suppress NL); bit1 = wrapped (1)
PU_WP           equ     $EEFB   ; pu_fmt_int scratch write pointer (2)
; CALL FORMAT loop counter — the current sector being written. write_sector's CALSLT
; clobbers every register, so the format loop keeps its position here in RAM. One byte
; ($EEFD) in the gap below FLD_DESC. See basic/format.asm.
FMT_SEC         equ     $EEFD   ; CALL FORMAT: current sector index being written (1)
FMT_DESC        equ     $EEFE   ; CALL FORMAT: chosen geometry descriptor pointer (2)
FLD_DESC        equ     $EF00   ; transient fielded-read descriptor [len][bytes:255]
; --- Phase 2c: random-record LEN= (OPEN..AS #n LEN=r) ----------------------
; The random record length, per channel. GET/PUT geometry (basic/field.asm) uses
; it in place of the old hard-wired 256: a record of r bytes tiles the 512-byte
; sector (recPerSec = 512/r) with NO straddle, so r is constrained to a power of
; two in 1..256 (parsed + validated at OPEN). FCH_RECLENS is a per-channel word
; array [0..FCH_CEIL] (a channel opened without LEN= defaults to 256); GP_RECLEN
; is the active channel's value, loaded from FCH_RECLENS[FCH_ACTIVE] at the start
; of each GET/PUT record calc. Clean high RAM above FLD_DESC ($EF00..$EFFF), well
; below the C-BIOS sysvars (~$F380). See basic/field.asm §GET/PUT + files.asm OPEN.
FCH_RECLENS     equ     $F000   ; per-channel record length words [0..FCH_CEIL] (6 B)
GP_RECLEN       equ     $F006   ; active channel's record length (word), loaded per calc
OO_RECLEN_CHAN  equ     $F008   ; OPEN scratch: channel # stashed across the LEN= eval (1)
FILES_HASPAT    equ     $F009   ; FILES: 1 = a filespec pattern is in DISK_FCB_NAME (1)
; --- Tier-3 cassette name-matching (CLOAD"name" / LOAD"CAS:name" / RUN"CAS:" /
; MERGE"CAS:"): tape/docs/spec-cas-tier3-cload.md Item A. Clean high RAM above
; FCH_RECLENS ($F00A.., below the C-BIOS sysvars ~$F380). Live ONLY during a
; cassette program open (cas_open_match): the requested name, the name read from
; each candidate header, and the matched file-type id for the caller's dispatch.
; The compare is BYTE-EXACT / case-sensitive — oracle-confirmed on the stock
; National_CF-3300 (spec §A.5): CLOAD"ABC" does NOT match a tape file "abc".
CAS_WANT        equ     $F00A   ; requested 6-char tape name, space-padded (6)
CAS_WANT_ON     equ     $F010   ; 1 = match CAS_WANT; 0 = load next file (bare form) (1)
CAS_HDRNAME     equ     $F011   ; 6-char name read from the current tape header (6)
CAS_HDRID       equ     $F017   ; file-type id byte read from the current header (1)
; --- Tier-3 CLOAD? verify (Item B): compare a tokenised tape program against the
; in-memory program WITHOUT mutating it; "Verify error" on any difference. The
; tokenised reader (ctp_line/ctp_body) runs in compare-mode when CAS_VERIFY=1:
; via cas_put, each byte it would store is instead compared against the in-memory
; program at CLPTR (which walks TXTBASE.. in lock-step, so it IS the comparand
; cursor — no separate pointer needed), setting the sticky CAS_VMIS on a diff.
; Scope: tokenised ($D3) only (spec §B).
CAS_VERIFY      equ     $F018   ; 1 = CLOAD? compare-mode (no store) (1)
CAS_VMIS        equ     $F019   ; sticky: 1 = a verify mismatch was seen (1)
; --- Cassette ASCII load 256-byte block buffer (cload.asm cal_getbyte) -------
; A DEDICATED 256-byte RAM block buffer the cassette-ASCII byte source serves
; from, so TAPIN is called only in the tight 256-read refill loop at each block
; boundary and NEVER interleaved with the per-line tokenise/store work (which
; would desync the real-time tape read — the M1 first-cut bug; see
; basic/docs/spec-cas-ascii-saveload.md §4). Symmetric with fat_io_getbyte's
; 512-byte FSECTOR_BUF on the disk side. PAGE-ALIGNED at $E600 so the read
; address is simply high=$E6 / low=CAL_CNT (no add). Placed INSIDE the file data
; sector buffer FSECTOR_BUF ($E5C0..$E7BF) — that buffer is used only by disk
; I/O, and a cassette CLOAD/LOAD"CAS:" does NONE, so it is dead for the whole
; load. This is deliberately LOW RAM: the earlier $F100 sat only ~640 bytes below
; the C-BIOS stack (~$F380), and the tokenise/dispatch pass (call-heavy) drove SP
; down into it, corrupting a filled block before it was served — a single-block
; file loaded as an EMPTY program. $E600 is far below any stack descent and clear
; of the tokenise/dispatch path (page $E0..$E3), LINEBUF ($E100), and program
; text ($8001+).
CAL_BUF         equ     $E600   ; cassette ASCII load: 256-byte tape block buffer (in idle FSECTOR_BUF)
; Cassette ASCII SAVE (save.asm cas_wbyte / cas_flush_block) uses the SAME 256-byte
; buffer for the WRITE mirror: list_walk fills it a byte at a time (no tape I/O), and
; a full block is flushed in one tight TAPOUT*256 loop so the inter-byte gaps stay
; uniform. Overlays CAL_BUF at $E600 — a SAVE and a LOAD never run at the same time,
; and both sit in the idle FSECTOR_BUF (no disk I/O during either), below any stack
; descent. Same rationale as CAL_BUF above.
CAS_WBUF        equ     $E600   ; cassette ASCII save: 256-byte tape block buffer (overlays CAL_BUF)
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
