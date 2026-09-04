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
WRTVDP          equ     $0047   ; write VDP register C with value B (and update RGnSAV)
CHGCLR          equ     $0062   ; apply FORCLR/BAKCLR/BDRCLR; A = screen mode (COLOR)
INITXT          equ     $006C   ; init SCREEN 0 (TEXT1) and enable the display
CHSNS           equ     $009C   ; test the keyboard buffer -> Z if empty, NZ if a key waits
CHGET           equ     $009F   ; wait for a character from the keyboard -> A
CHPUT           equ     $00A2   ; output the character in A at the cursor
LPTOUT          equ     $00A5   ; print the character in A to the printer (Centronics);
                                ; supplied by zerobas-tape on the C-BIOS target
CLS             equ     $00C3   ; clear the screen; zero flag must be set on entry
ERAFNK          equ     $00CC   ; erase the function-key display line (KEY OFF)
DSPFNK          equ     $00CF   ; display the function-key line (KEY ON)
CSRX            equ     $F3DD   ; cursor column (1-based); C-BIOS sysvars / PRINT comma zones
CSRY            equ     $F3DC   ; cursor row (1-based); the CSRLIN pseudo-variable reads it
; BREAKX: test the Ctrl-STOP key combination by directly scanning keyboard matrix
; row 6 (no side effects, no ISR dependency). CF set on return = Ctrl-STOP held,
; CF clear = not held. Source: MSX Assembly Page BIOS call list / MSX2 Technical
; Handbook; oracle-confirmed working on C-BIOS_MSX1 (bios_probe_breakx.py: carry
; clear when no key pressed, identical to the reference VG-8020).
BREAKX          equ     $00B7   ; check Ctrl-STOP via keyboard matrix; CF set = pressed

; --- input-device BIOS entry points (STICK / STRIG) ------------------------
; docs/spec-basic-input-devices.md §6. Published BIOS jump-table entries (MSX
; Assembly Page BIOS call list / MSX Technical Data Book). Both are REAL in
; C-BIOS -- keyboard row-8 scan + PSG joystick-port read -- and their behaviour
; matches the VG-8020 measurement in the spec's §5 (scratchpad/i1_input_notes.md
; round 4), so STICK/STRIG are thin wrappers over them. Called from ordinary
; resident context (page 0 = BIOS), like CHSNS/CHGET for INKEY$.
GTSTCK          equ     $00D5   ; A = device (0 cursors, 1/2 joystick port) -> A = 0..8
GTTRIG          equ     $00D8   ; A = trigger (0 space, 1..4 buttons) -> A = $00 or $FF
GTPAD           equ     $00DB   ; A = 4*device+sub -> A = touch-panel read (zerobas-tape)
GTPDL           equ     $00DE   ; A = paddle 1..12 -> A = 0..255 dial (zerobas-tape)

; --- VDP VRAM access BIOS entry points (VPOKE / VPEEK) ---------------------
; Source: MSX Assembly Page BIOS call list / MSX2 Technical Handbook, VDP I/O.
WRTVRM          equ     $004D   ; write A to VRAM address HL (VPOKE)
RDVRM           equ     $004A   ; read VRAM address HL -> A (VPEEK)

; --- Graphics arc (SCREEN 2 geometry engine; docs/spec-basic-graphics.md) ----
; The graphics tenant (sub/graphics.asm, page-0) does DIRECT VDP port I/O -- it
; runs with the BIOS paged out (page-0 island) so it cannot CALSLT WRTVRM, and a
; pixel engine must not pay a CALSLT per byte anyway (arc D2). Ports are the fixed
; MSX VDP hardware contract (TMS9918A datasheet), identical on every MSX1.
VDP_DATA        equ     $98     ; VDP VRAM data port (write = store+autoinc; read = fetch+autoinc)
VDP_ADDR        equ     $99     ; VDP address/register port; READ = status S#0 (the ISR reads
                                ; this every VBLANK, which resets the addr latch flip-flop --
                                ; the race the 2-byte-latch DI guard closes, spec-...-g1 §3)
; SCREEN 2 (GRAPHIC-2) VRAM base tables -- PINNED black-box (BASE(10..14),
; docs/spec-basic-graphics.md §11.2): pattern generator @ $0000, color @ $2000.
; Pixel byte addr = (y>>3)*256 + (x>>3)*8 + (y&7); color byte = pattern + $2000.
GFX_PGEN_BASE   equ     $0000   ; SCREEN 2 pattern generator (the pixel/pattern plane)
GFX_COLOR_OFST  equ     $2000   ; color-plane offset from the pattern byte (fg|bg per 8x1 group)
; Graphics work-area cells -- PINNED addresses (RAM-scan diff, §11.5), matching the
; published MSX2-TH work area. DECLARED in G1 (pin the addresses once); WRITTEN by
; G2+ (no plot statement in G1). GXPOS/GYPOS = pending pixel target; GRPACX/GRPACY =
; the last-referenced point for LINE -(x,y)/STEP; CLOC/CMASK = computed VRAM addr+mask.
GXPOS           equ     $FCB3   ; pending plot X (int16 LE)
GYPOS           equ     $FCB5   ; pending plot Y (int16 LE)
GRPACX          equ     $FCB7   ; last-referenced point X (int16 LE)
GRPACY          equ     $FCB9   ; last-referenced point Y (int16 LE)
CLOC            equ     $F92A   ; computed VRAM byte address of the current pixel (2)
CMASK           equ     $F92C   ; MSB-first bit mask of the current pixel (1)
; ATRBYT -- the SHARED graphics attribute (published MSX work area). Introduced
; in G6 (docs/spec-basic-graphics-g6.md §6, D-G6-3) because DRAW's colour is
; measurably this cell, not a DRAW-private one: every graphics statement given an
; explicit colour stamps it, every colourless one stamps FORCLR, and DRAW READS it
; (writing only on `C n`). That is what makes `LINE ..,4 : DRAW"BM..R8"` draw in 4
; while `DRAW"C6.." : LINE ..` (colourless) draws in FORCLR -- both measured.
ATRBYT          equ     $F3F2   ; current graphics attribute / plot colour (1)
; G1 floor self-test results (PROBE-ONLY; docs/spec-basic-graphics-g1.md §5). The
; graphics self-test tenant (SUBROM_IDX_GRAPHICS, GFX_OP=0) is never invoked by real
; BASIC -- only by basic_probe_graphics_floor.py -- so its two result bytes live in
; high scratch RAM (page 3, the same $C0xx region the inttest probe uses), NOT in the
; exhausted system-variable area. The probe reads them straight after the CALSLT.
; 🔴 THESE TWO WERE STRANDED AT $C120, ABOVE A BOUNDARY EVERY OTHER ALLOCATION
; RESPECTS -- two bytes alone in the 8192 B the text ceiling was reserving. That
; is what made them findable (D-FREGAP) and what forced them to move: with
; TXTMAX raised over $C000 they would sit INSIDE the BASIC text area, written by
; any draw, corrupting a program larger than ~16 KB. Homed 2026-09-01 in two
; cells this file already documents as retired-and-free, one each:
;   $E220      was STOPGRACE (retired 2026-07-25, spec §12.3)
;   $E3E5      was STRENG_SPARE / the D-2 flag (D-PENDERR)
GFX_DJ          equ     $E220   ; JIFFY delta observed while drawing under EI (1)
GFX_BAD         equ     $E3E5   ; VRAM read-back mismatch count (1)

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
; inverse. 🔴 THE FLOAT SIBLINGS (MKS$/MKD$/CVS/CVD) ARE MISSING, AND THIS LINE
; USED TO DEFER THEM TO "Phase-3 floats" -- WHICH LANDED. Measured 2026-09-03
; (D-DEFERCHECK) against the CF-3300, the only reference that has these verbs
; (the VG-8020 raises ERR 5 on all of them, Disk BASIC):
;     CVS(MKS$(1.5))  cf3300 1.5   here ERR 13      LEN(MKS$(1.5))  4  here 0
;     CVD(MKD$(1.5))  cf3300 1.5   here ERR 13      LEN(MKD$(1.5))  8  here 0
; MKS$ returns an EMPTY STRING. The integer pair (MKI$/CVI) round-trips 258 and
; LEN 2, matching. Filed in TODO.md, unpriced. The old text said they "need
; Phase-3 floats and are"
; deferred. MKI$ is evaluated in basic/strvar.asm (string result); CVI in
; basic/expr.asm ev_f_ff (numeric result, string argument).
MKI_TOKEN       equ     $AE     ; MKI$(n)  -> 2-byte LE string of integer n
CVI_TOKEN       equ     $A8     ; CVI(s$)  -> integer from the first 2 bytes of s$
; The FLOAT siblings, shipped 2026-09-03 (D-MKSD, docs/spec-basic-mksd.md). Token
; bytes are BLACK-BOX ORACLE READINGS: `kwsweep`'s crunch layer captured what the
; CF-3300 stores for `a$=mks$(1)` / `a=cvs("abcd")` and so on -- `FF AF`, `FF B0`,
; `FF A9`, `FF AA`. Typed input in, stored bytes out; no disassembly.
MKS_TOKEN       equ     $AF     ; MKS$(n)  -> 4-byte string: the SINGLE-precision bytes
MKD_TOKEN       equ     $B0     ; MKD$(n)  -> 8-byte string: the DOUBLE-precision bytes
CVS_TOKEN       equ     $A9     ; CVS(s$)  -> single from the first 4 bytes of s$
CVD_TOKEN       equ     $AA     ; CVD(s$)  -> double from the first 8 bytes of s$
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
; String-engine function tokens (Phase 3, repack-only — docs/spec-basic-string-engine.md).
; All $FF-prefixed function suffixes from the same contiguous MSX-BASIC function table as
; LEN/STR$/VAL above (MSX2 TH Table 2.20) AND black-box-captured from the Philips VG-8020
; crunch 2026-07-10 (scratchpad/capture_str_tokens.py; e.g. `a$=left$("hi",1)` -> ...EF FF
; 81 28...). The `$` in a keyword is part of the name (like MKI$); the equate drops it (…D).
; These crunch entries land in kwtable. No disassembly.
LEFTD_TOKEN     equ     $81     ; LEFT$(a$,n)  -> $FF $81
RIGHTD_TOKEN    equ     $82     ; RIGHT$(a$,n) -> $FF $82
MIDD_TOKEN      equ     $83     ; MID$(a$,p,n) -> $FF $83
STRD_TOKEN      equ     $93     ; STR$(n)      -> $FF $93
VAL_TOKEN       equ     $94     ; VAL(a$)      -> $FF $94
ASC_TOKEN       equ     $95     ; ASC(a$)      -> $FF $95
CHRD_TOKEN      equ     $96     ; CHR$(n)      -> $FF $96
; string-functions slice (Phase 3, repack-only — docs/spec-basic-string-functions.md).
; HEX$/OCT$/SPACE$ are $FF-prefixed function tokens (same contiguous table as above);
; STRING$/INSTR are single-byte reserved-word tokens (not $FF-prefixed), like VARPTR/
; BASE. All five oracle-locked black-box on the Philips VG-8020 crunch 2026-07-10
; (basic_probe_str_fn.py) AND cross-checked vs MSX2 TH Table 2.20. The `$` in a
; keyword is part of the name (like MKI$/LEFT$); the equate drops it (…D). No
; disassembly.
HEXD_TOKEN      equ     $9B     ; HEX$(n)      -> $FF $9B
OCTD_TOKEN      equ     $9A     ; OCT$(n)      -> $FF $9A
BIND_TOKEN      equ     $9D     ; BIN$(n)      -> $FF $9D
FRE_TOKEN       equ     $8F     ; FRE(n)/FRE(s$) -> $FF $8F
SPACED_TOKEN    equ     $99     ; SPACE$(n)    -> $FF $99
STRING_TOKEN    equ     $E3     ; STRING$(n,c) -> $E3   (single-byte, reserved word)
INSTR_TOKEN     equ     $E5     ; INSTR([p,]a$,b$) -> $E5 (single-byte, reserved word)
INKEY_TOKEN     equ     $EC     ; INKEY$ -> $EC (single-byte reserved word; '$' part of
                                ; the keyword — S2 black-box capture, VG-8020 crunch)
; Math float pack, slice F1 (Phase 3, repack-only — docs/spec-basic-float-core.md).
; Single/double float-literal tokens: MSX2 TH Table 2.20 (the number-format chapter
; lists $1D/$1F alongside the $11-$1C int forms) + oracle-captured byte-exact by
; basic_probe_floatlit.py (VG-8020 KBUF, e.g. `a=1.5`->1D 41 15.., `a=1#`->1F 41 10..).
SNG_TOKEN       equ     $1D     ; single-precision float literal: token + 4 value bytes
DBL_TOKEN       equ     $1F     ; double-precision float literal: token + 8 value bytes
; Math pack slice 1a (Phase 3, repack-only — docs/spec-basic-math-pack.md §9.3).
; ABS/SGN/INT/FIX/CINT/CSNG/CDBL: $FF-prefixed function tokens from the same
; contiguous MSX-BASIC function table as LEN/VAL/HEX$ above (MSX2 TH Table
; 2.20) + black-box VG-8020 crunch capture (probes/basic/basic_probe_math_conv.py).
; Bare-byte namespace overlaps with existing SINGLE-byte statement/keyword
; tokens are expected + harmless (same PEEK_TOKEN/DEF_TOKEN precedent, line
; above): SGN==DATA_TOKEN($84), INT==INPUT_TOKEN($85), FIX==ELSE_TOKEN($A1),
; CDBL==WIDTH_TOKEN($A0) as raw byte values — the $FF prefix disambiguates.
ABS_TOKEN       equ     $86     ; ABS(x)  -> $FF $86
SGN_TOKEN       equ     $84     ; SGN(x)  -> $FF $84
INT_TOKEN       equ     $85     ; INT(x)  -> $FF $85
FIX_TOKEN       equ     $A1     ; FIX(x)  -> $FF $A1
CINT_TOKEN      equ     $9E     ; CINT(x) -> $FF $9E
CSNG_TOKEN      equ     $9F     ; CSNG(x) -> $FF $9F
CDBL_TOKEN      equ     $A0     ; CDBL(x) -> $FF $A0
; Math pack slice 1b (Phase 3, repack-only -- docs/spec-basic-math-pack.md
; §10.1). SQR: same $FF-prefixed function-token table, MSX2 TH Table 2.20 +
; black-box VG-8020 crunch capture (probes/basic/basic_probe_math_conv.py).
; Interleaves cleanly: ABS $86 . SQR $87 . RND $88. (⚠️ said "RND not yet
; implemented" until 2026-09-03 -- STALE: fp_rnd ships as a sub-ROM tenant and
; RND(1)/RND(0)/RND(-1) all agree with both references, D-DEFERCHECK.)
SQR_TOKEN       equ     $87     ; SQR(x) -> $FF $87
; Math pack slice 2a (Phase 3, repack-only -- docs/spec-basic-mathpack-
; slice2.md §11.1). ATN: same $FF-prefixed function-token table, MSX2 TH
; Table 2.20 + black-box VG-8020 crunch capture (probes/basic/basic_probe_
; math_conv.py, §1.4). Interleaves cleanly: SIN $89 . LOG $8A . EXP $8B .
; COS $8C . TAN $8D . ATN $8E . RND $88 (SIN/LOG/EXP/COS/TAN/RND not yet
; implemented -- later sub-slices).
ATN_TOKEN       equ     $8E     ; ATN(x) -> $FF $8E
; Math pack slice 2b (Phase 3, repack-only -- docs/spec-basic-mathpack-
; slice2.md §12.2). EXP/LOG: same $FF-prefixed function-token table, MSX2
; TH Table 2.20 + black-box VG-8020 crunch capture (probes/basic/basic_
; probe_math_conv.py, §1.4). Interleaves cleanly with the slice-2a comment
; above: SIN $89 . LOG $8A . EXP $8B . COS $8C . TAN $8D . ATN $8E . RND $88
; (⚠️ said SIN/COS/TAN/RND "not yet implemented -- later sub-slices" until
; 2026-09-03; all four ship. D-DEFERCHECK measured RND directly.)
EXP_TOKEN       equ     $8B     ; EXP(x) -> $FF $8B
LOG_TOKEN       equ     $8A     ; LOG(x) -> $FF $8A
; Math pack slice 2d (Phase 3, repack-only -- docs/spec-basic-mathpack-
; slice2.md §14.1/§14.4). SIN/COS/TAN: same $FF-prefixed function-token
; table, MSX2 TH Table 2.20 + black-box VG-8020 crunch capture (probes/
; basic/basic_probe_math_conv.py, §14.8, fresh 2026-07-14 capture). Completes
; the interleave: SIN $89 . LOG $8A . EXP $8B . COS $8C . TAN $8D . ATN $8E .
; RND $88. (⚠️ said "not yet implemented" until 2026-09-03 -- STALE, D-DEFERCHECK.)
SIN_TOKEN       equ     $89     ; SIN(x) -> $FF $89
COS_TOKEN       equ     $8C     ; COS(x) -> $FF $8C
TAN_TOKEN       equ     $8D     ; TAN(x) -> $FF $8D
; Math pack slice 2e (Phase 3, repack-only -- docs/spec-basic-mathpack-
; slice2.md §15.4). RND: same $FF-prefixed function-token table, MSX2 TH
; Table 2.20 + black-box VG-8020 crunch capture (probes/basic/basic_probe_
; math_conv.py, §15.5). LAST slice-2 function: completes the interleave
; SIN $89 . LOG $8A . EXP $8B . COS $8C . TAN $8D . ATN $8E . RND $88
; every slice-1b/2a/2b/2d comment above already forward-referenced.
RND_TOKEN       equ     $88     ; RND(x) -> $FF $88
; Arrays slice-1 (Phase 3, repack-only -- docs/spec-basic-arrays.md §5). DIM: a
; single-byte STATEMENT token (not $FF-prefixed), black-box VG-8020 crunch
; capture ("DIM A(5)" -> 86 20 41 28 16 29 00) + MSX2 TH Table 2.20. NUMERIC
; coincidence with ABS_TOKEN ($86, a $FF-prefixed FUNCTION token) is expected
; and harmless -- same disambiguated-by-namespace precedent as SAVE_TOKEN/
; BINARY_ID and NAME_TOKEN/BASIC_ID above (a bare exec_stmt dispatch byte is
; never confused with a $FF-prefixed function selector).
DIM_TOKEN       equ     $86     ; DIM A(n)[,B(n1,n2)...] (statement)
; Arrays slice-2 (docs/spec-basic-arrays-slice2-erase.md §2). ERASE: single-byte
; STATEMENT token, black-box VG-8020 crunch capture ("ERASE A" -> a5 20 41 00)
; cross-checked vs MSX2 TH Table 2.20/MAP (never asserted from memory) --
; same provenance discipline as DIM_TOKEN above.
ERASE_TOKEN     equ     $A5     ; ERASE <name>[,<name>...] (statement)
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
; Audio (docs/spec-basic-audio-play.md). SOUND is a single-byte STATEMENT token,
; black-box VG-8020 crunch capture ("sound 1,255" -> C4 20 12 2C 0F FF 00 =>
; SOUND=$C4; scratchpad/spike_sound_token.py, 2026-07-21) cross-checked vs MSX2
; TH Table 2.20 -- NOT asserted from memory (the guessed $C2 was wrong). PLAY is
; captured as $C1 for its later slice. Same provenance discipline as DIM/ERASE.
SOUND_TOKEN     equ     $C4     ; SOUND reg,value (statement)
PLAY_TOKEN      equ     $C1     ; PLAY "mml"[,..] (statement; audio Slice 2a, play.asm)
BEEP_TOKEN      equ     $C0     ; BEEP (statement, no args; audio close-out, sound.asm).
                                ; Black-box VG-8020 crunch capture ("beep" -> C0 00;
                                ; "beep:beep" -> C0 3A C0 00; scratchpad/spike_beep_token.py)
                                ; + MSX2 TH Table 2.20 cross-check. See spec-basic-audio-beep.md.
; Graphics G2 (docs/spec-basic-graphics-g2.md). Single-byte tokens, RE-VERIFIED
; black-box on VG-8020 (stored-line crunch, arc §11.9): "PSET(0,0)" -> C2 28 11 2C
; 11 29 00; "PRESET(0,0)" -> C3 ...; "X=POINT(0,0)" -> 58 EF ED ...  So PSET=$C2 (the
; value the WRONG SOUND guess used -- now confirmed genuinely PSET), PRESET=$C3, and
; POINT=$ED is a FUNCTION token (dispatched in expr.asm like BASE/VARPTR). STEP=$DC
; already exists.
PSET_TOKEN      equ     $C2     ; PSET (x,y)[,c]      (statement, basic/graphics.asm)
PRESET_TOKEN    equ     $C3     ; PRESET (x,y)[,c]    (statement)
POINT_TOKEN     equ     $ED     ; POINT(x,y)          (function -> pixel colour / -1)
; Graphics G4 (docs/spec-basic-graphics-g4.md §7/§11.1). CIRCLE is a NEW single-byte
; STATEMENT token (unlike G3's LINE, which reused an existing token). $BC collides
; with nothing in the existing table (arc §7); re-confirmed by the G4 characterisation
; pass (stored-line crunch, spec §11.1: "CIRCLE(30,30),10" -> BC 28 ... 29 ... 00).
CIRCLE_TOKEN    equ     $BC     ; CIRCLE (x,y),r[,c[,start[,end[,aspect]]]] (statement)
; Graphics G5 (docs/spec-basic-graphics-g5.md §7). PAINT is a NEW single-byte
; STATEMENT token; pinned by the G5 black-box crunch characterisation pass
; (scratchpad/g5_paint_notes.md C1: PAINT=$BF, matches no other keyword's
; prefix).
PAINT_TOKEN     equ     $BF     ; PAINT [STEP](x,y)[,[c][,[b]]] (statement)
; G6_RESIDENT -- the DRAW statement's RESIDENT half (ex_draw + the pre-pass, and
; with it the kwtable row and the interp dispatch arm) is gated OFF until the
; space for it exists. MEASURED 2026-07-22: with it in, the page-1 image ends at
; $80EF, i.e. it overruns the $8000 ceiling by 239 B (ex_draw ~261 B against the
; 22 B of tail that were free). The scouted runway -- do_tape_prog/ctp_*, 224 B --
; turned out NOT to be a clean carve: 6 of its callees (load_error, cas_open_match,
; cas_put, verify_error, cas_ascii_load, new_prog, relink) are page-1 RESIDENT, so
; it straddles as a page-1 tenant, and it calls BIOS TAPION/TAPIN/TAPIOF, so it
; cannot be a page-0 tenant either. See docs/spec-basic-graphics-g6.md §8.
; The TENANT half (sub/graphics.asm GFX_OP=6) is unconditional -- the sub-ROM has
; room -- so flipping this to 1 after the space lands is the whole switch-on.
G6_RESIDENT     equ     1
; Graphics G7 (docs/spec-basic-graphics-g7.md). SPRITE is a single-byte reserved
; word ($C7) shared by ALL of the sprite surface -- `SPRITE$(n)` (the `$` is plain
; ASCII after the token), `PUT SPRITE` (PUT $B3 + SPRITE) and the trap-arming
; `SPRITE ON|OFF|STOP` -- black-box crunch-pinned (scratchpad/g7_sprite_notes.md).
; G7_RESIDENT gates the RESIDENT half the way G6_RESIDENT gated DRAW's, so the
; slice can be built with the tenant alone if the page-1 tail runs out again.
G7_RESIDENT     equ     1
; --- D-CLP: the CLEAR string-pool partition (docs/spec-basic-clearpool.md) ---
; ✅ ON. Funded by promoting fld_lookup to a page-0 sub-ROM tenant (sub/fldlook.asm,
; docs/decision-clearpool-funding.md §6.1), which returned 38 B of main page 1
; (3 B free -> 41 B) against this slice's measured 22 B requirement.
; What the flag gates, main-ROM side:
;     basic/clear.asm   the CLEAR <n> domain check + the POOLSIZE store
;     basic/interp.asm  the cold-boot default of 200, and err_msgtab entry 14
;     basic/str-engine.asm  the ERR 14 message string + str_heap_oom_error's code
; The pool FLOOR itself is nowhere in this ROM: it is derived sub-side as
; min(HIMEM,TXTMAX) - POOLSIZE (S-CLP-2, reversed), so the scarce low region
; spends nothing on it and `CLEAR ,himem` keeps its size for free.
; (Until 2026-07-29 this had an ELSE branch for the lean 16 KB cart, which had no
; sub-ROM for the floor derivation to live in. That build is retired.)
CLEARPOOL       equ     1
; FPERR code a STRING-HEAP allocation failure defers through (basic/str-engine.asm
; str_temp_alloc / str_snapshot_to_temp / sct_append_err / shx_finish /
; str_heap_oom_error, all reached from SH_ERR=1). With the partition ON, a heap
; failure means the pool `CLEAR n` sized ran out, which is `Out of string space`
; (ERR 14) and NOT `Out of memory` (ERR 7) -- telling those two apart is what the
; probe's whole `oos` battery is about. Routing it through a DIFFERENT FPERR code
; rather than a different code path costs zero bytes at the five sites (they were
; already `ld a,<code>`); the only new byte is fperr_to_err's 11th entry
; (basic/interp.asm). ⚠️ ARRAY allocation failures keep FPERR=6 / ERR 7 on
; purpose -- an array that will not fit ran out of VARIABLE space, and the
; oos-vs-oom row exists to pin exactly that distinction.
; 🎯 THE LINE ABOVE IS ABOUT THE ALLOCATION, AND THE STRING ARRAY *STORE* WAS
; ON THE WRONG SIDE OF IT UNTIL 2026-08-20 (D-ARYOOS). `A$(2)=B$` on a full
; pool is a BODY that will not fit, not an array that will not fit, and both
; references say `Out of string space`; it reached ERR 7 because
; aeng_copy_str's OOM reused ary_alloc's ARY_ERR=4. It now raises ARY_ERR=5,
; which ary_errmap maps to THIS symbol. The denominator that keeps the two
; apart is row s.strdim: `CLEAR 100:DIM A$(20000)` is a STRING array and is
; `Out of memory` on vg8020, cf3300 and here -- so the split is by the SITE
; that failed, never by the array's type
; (docs/aryoos-msx1-characterization.md).
    IF CLEARPOOL
FPERR_STROOM    equ     11      ; -> ERR 14 "out of string space"
FPERR_MISSOP    equ     12      ; -> ERR 24 "Missing operand" (D-MISSOP)
    ELSE
FPERR_STROOM    equ     6       ; -> ERR 7 "Out of memory" (pre-partition)
FPERR_MISSOP    equ     11      ; -> ERR 24 "Missing operand" (D-MISSOP)
    ENDIF
; D-MISSOP (docs/spec-basic-missop.md): the code ev_f_err defers when a factor
; was REQUIRED and the statement ended instead. It is equated HERE, inside the
; same IF, because fperr_to_err is a DENSE table indexed by the code -- the
; entry FPERR_STROOM occupies only exists when CLEARPOOL does, so the next free
; index is not a constant. Getting this wrong is silent: it reads a neighbouring
; table byte and reports some other error.
; D-PENDERR (docs/spec-basic-penderr.md §4): the pending-error code a DEFERRED
; TYPE MISMATCH records. Named because it is now written from two places that
; used to speak in different currencies -- basic/str-engine.asm's
; type_mismatch_set (which used to arm the separate TMISMATCH flag) and
; basic/expr.asm's ev_f_tmm (which always deferred through FPERR). Both mean the
; same thing and always did; fperr_to_err entry 10 maps it to ERR 13, the SAME
; table entry type_mismatch_error raises directly (basic/interp.asm).
; D-STRLONG (docs/spec-basic-strlong.md): a concatenation whose combined length
; exceeds STRMAX. `sh_append` used to CLAMP such a result to 255 and return it,
; which is a SILENT WRONG ANSWER -- both references raise ERR 15. Defined as
; FPERR_MISSOP+1 rather than a literal for the reason the block above gives: the
; table is DENSE and every code above it MOVES with the CLEARPOOL switch.
FPERR_STRLONG   equ     FPERR_MISSOP + 1    ; -> ERR 15 "String too long"
FPERR_TYPEMM    equ     10      ; -> ERR 13 "Type mismatch"
; Graphics G8 (docs/spec-basic-graphics-g8.md). VDP(n) and BASE(n) are single-byte
; FUNCTION tokens, and their assignment form has no statement token of its own: a
; statement whose first token is $C8/$C9 IS the assignment (crunch-pinned,
; scratchpad/g8_vdp_notes.md C1). Gated like G6/G7 so the slice can build with the
; tenant alone if the page-1 tail runs out; the reads are resident either way
; (they are plain work-area fetches -- cheaper than marshalling a subrom_call).
; Unlike G6/G7 this slice REPLACES an earlier routine (expr.asm's descoped
; ev_f_base stub); `IF !G8_RESIDENT` is what selects the stub instead.
G8_RESIDENT     equ     1
; Input devices, slice I1 (docs/spec-basic-input-devices.md §3). STICK/STRIG are
; $FF-prefixed FUNCTION tokens (selector byte after PEEK_PREFIX), crunch-pinned on
; the VG-8020 (scratchpad/i1_input_notes.md round 1) -- the same shape as PEEK, so
; they dispatch through expr.asm's ev_f_ff and need no statement token. PDL ($A4)
; and PAD ($A5) are slice I2 and are NOT defined yet: they wait on the zerobas-tape
; GTPAD/GTPDL BIOS completions (spec §6.2, decision D-I-6).
; Gated like G6/G7/G8 so the slice can be dropped if the page-1 tail runs out.
; --- TRAPS_T3: the KEY-trap build gate (docs/spec-traps-t3-key.md §7.2) ------
; T3 needs 236 B (60 low-region + 176 page-1). The BLOAD carve funded the page-1
; half (main page 1 9 B -> 271 B free), so the flip below is now 1; the low-region
; half is funded by promotion (spec §7.4).
; Gated like G8_RESIDENT/I1_RESIDENT, and it MUST be: the
; T3 parse surface (ex_on_key/ex_key_stmt) lives in the low region, so it exists
; only in the repack build, while its two call sites (ex_on's peek in program.asm
; and ex_key's peek in basic/screen.asm) sit in always-assembled page-1 code, so
; a bare `IF TRAPS_T3` there would leave them referencing symbols the disabled
; build never assembles -- i.e. the gate could not be flipped at all without this
; ELSE. (It also had to carry the retired lean cart, which assembled neither.)
TRAPS_T3        equ     1

; --- TRAPS_T4: the SPRITE-trap build gate (docs/spec-traps-t4-sprite.md §7) --
; The arc's last slice. Gated for exactly T3's reason and NOT a
; bare `equ`: the poll stanza is low-region (repack-only) while its call sites --
; ex_on's sibling peek and ex_sprite in graphics.asm -- are always-assembled
; page-1 code, so a bare gate leaves them referencing symbols the disabled build
; never assembles. T3 lost a round to precisely that.
TRAPS_T4        equ     1

; --- TRAPS_T5: the INTERVAL-trap build gate (docs/spec-traps-t5-interval.md) --
; The arc's FIFTH slice -- reopened after "INTERVAL is MSX2" was retracted (arc
; spec §0: it is a reserved-word COMPOUND, INT + "ER" + VAL, so it never needed a
; keyword-table entry to exist). Gated for T3/T4's reason: the
; call sites (ex_on's peek, ex_ff_stmt's) are always-assembled page-1 code, so a
; bare gate leaves them referencing symbols the disabled build never assembles.
TRAPS_T5        equ     1

I1_RESIDENT     equ     1
; I2 (PDL/PAD) rides the same repack-only gate as I1: the two functions are thin
; wrappers over the zerobas-tape GTPDL/GTPAD BIOS completions (spec §9). Split
; from I1_RESIDENT only so the flags read where each slice's code is gated.
I2_RESIDENT     equ     1
STICK_TOKEN     equ     $A2     ; STICK(n) -> 0..8 direction (0 = centred)
STRIG_TOKEN     equ     $A3     ; STRIG(n) -> 0 / -1 trigger state
PDL_TOKEN       equ     $A4     ; PDL(n)   -> 0..255 paddle dial (input devices, I2)
PAD_TOKEN       equ     $A5     ; PAD(n)   -> touch-panel read (input devices, I2)
VDP_TOKEN       equ     $C8     ; VDP(n)      (single-byte function token)
SPRITE_TOKEN    equ     $C7     ; SPRITE (statement + string function + PUT SPRITE)
DRAW_TOKEN      equ     $BE     ; DRAW <string> (statement; graphics G6) -- crunch of
                                ; `DRAW"u10"` on the reference is BE 22 75 31 30 22,
                                ; measured (scratchpad/g6_draw_notes.md §1)
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
; Graphics G2 own-design marshalling block (main -> page-0 graphics tenant, selector
; dispatch). MUST NOT alias the audio/disk param cells (DISKOP_OP/AUDIO_VMASK $E9FB):
; graphics runs CONCURRENTLY with a live PLAY drain (arc D1 -- music keeps playing
; during a draw), so a shared cell would race the ISR. Homed in the free $E030 gap
; ($E02F RUNFLAG..$E0C0 NUMBUF). Coordinates are marshalled through the pinned
; GXPOS/GYPOS cells (the resident stub writes them anyway, §6); only the op selector,
; the resolved colour, and the POINT result need own bytes. All dead outside a GFX
; call. GFX_OP=0 is still G1's floor self-test (the floor probe now sets it).
; 🔴 D-GIRDOM 2026-08-11: "THE RESIDENT STUB WRITES THEM ANYWAY" IS FALSE FOR ONE
; OP. It holds for GFX_OP=1/3/5 (PSET/PRESET, LINE, PAINT) -- STATEMENTS that move
; the work area, so the marshalling and the contract are the same write. GFX_OP=2
; is POINT, a read-only FUNCTION that both references leave the work area untouched
; by, so the "anyway" was doing work it had not earned and the free ride shipped a
; BASIC-VISIBLE side effect (rows w.pt.on / w.pt.step). POINT now marshals through
; GFX_PTX/GFX_PTY below. ⚠️ Before reusing a pinned cell as a parameter, ask whether
; THIS op writes it as part of its contract -- not whether the block does.
GFX_OP          equ     $E030   ; main->tenant op: 0=selftest(G1) 1=plot(PSET/PRESET) 2=point (1)
GFX_C           equ     $E031   ; main->tenant: resolved plot colour 0..15 (PSET/PRESET) (1)
GFX_RES         equ     $E032   ; tenant->main: POINT result colour 0..15 (1)
GFX_REL         equ     $E033   ; parse_coord: 1 = STEP (relative) coordinate, 0 = absolute (1)
; Graphics G3 (LINE) marshalling + Bresenham state. G3 needs ~40 B that persist for
; the WHOLE draw (the tenant loops while EI). The $E034+ gap is NOT usable: CURLINE /
; the FOR/GOSUB stacks / GOTOTGT live there and must be preserved across the
; subrom_call (the main interpreter is frozen mid-`LINE`, not dead).
; Home = $E100..$E157 (docs/spec-basic-graphics-g3.md §6), below the PLAY ISR region
; ($F959+) so a live PLAY drain can't race it (arc D1). Dead outside a GFX_OP=3 call.
; GFX_OP/GFX_C stay at $E030 (G1/G2 dispatch + colour, unchanged).
;
; ⚠️ THE ALIASING ARGUMENT THIS BLOCK USED TO CARRY IS RETIRED, NOT WEAKENED
; (D-LINEMAX §3.1). These cells were homed on the documented claim that they overlay
; the LINEBUF region and that LINEBUF is dead during any graphics statement — a claim
; that had to be true for the layout to be safe. D-LINEMAX moved LINEBUF ($E100) and
; TOKBUF ($E160) out of page 3 to $BA00/$B700, so in the repack build these cells
; overlay NOTHING and simply own free RAM; the precondition is no longer load-bearing
; and must not be re-derived by a later reader as a live constraint.
GFX_X1          equ     $E100   ; LINE endpoint 1 X (int16 LE) -- resident marshals, tenant reads
GFX_Y1          equ     $E102   ; LINE endpoint 1 Y (int16 LE)
GFX_X2          equ     $E104   ; LINE endpoint 2 X (int16 LE)
GFX_Y2          equ     $E106   ; LINE endpoint 2 Y (int16 LE)
GFX_MODE        equ     $E108   ; GFX_OP=3 sub-mode: 0=segment 1=box outline 2=box fill (1)
GFX_CX          equ     $E109   ; Bresenham: current pixel X (int16, may be off-screen) (2)
GFX_CY          equ     $E10B   ; Bresenham: current pixel Y (int16) (2)
GFX_ERR         equ     $E10D   ; Bresenham: error accumulator, in [0,DMAJ) (2)
GFX_DMAJ        equ     $E10F   ; Bresenham: major-axis delta (2)
GFX_DMIN        equ     $E111   ; Bresenham: minor-axis delta (2)
GFX_CNT         equ     $E113   ; Bresenham: major steps still to take (2)
GFX_STEEP       equ     $E115   ; Bresenham: 0 = x-major, 1 = y-major (1)
GFX_SMIN        equ     $E116   ; Bresenham: minor-axis step, $0001 (+1) or $FFFF (-1) (2)
GFX_SDX         equ     $E118   ; init scratch: sign of (x2-x1), $01/$FF (1)
GFX_SDY         equ     $E119   ; init scratch: sign of (y2-y1), $01/$FF (1)
GFX_TX1         equ     $E11A   ; box: stashed corner 1 X (2)
GFX_TY1         equ     $E11C   ; box: stashed corner 1 Y (2)
GFX_TX2         equ     $E11E   ; box: stashed corner 2 X (2)
GFX_TY2         equ     $E120   ; box: stashed corner 2 Y (2)
GFX_FILLCNT     equ     $E122   ; box fill: scanlines remaining (2)
GFX_YSTEP       equ     $E124   ; box fill: row step, $0001/$FFFF (2)   -> ends $E126
; Graphics G4 (CIRCLE, docs/spec-basic-graphics-g4.md §6). Append-only after G3's
; $E126, same discipline (dead during any graphics statement, below the PLAY ISR
; region; the LINEBUF overlay it was originally argued from is retired — G3 header
; above). GFX_OP=4 selects the tenant arm; GFX_OP/GFX_C ($E030/$E031)
; stay shared with G1/G2/G3 (op selector + resolved colour). Spoke lines (§5.3) are
; marshalled through the EXISTING G3 GFX_X1/Y1/X2/Y2/GFX_MODE cells with GFX_OP=3 --
; no new cells needed for that reuse.
GFX_CXC         equ     $E126   ; centre X (int16 LE) (2)
GFX_CYC         equ     $E128   ; centre Y (int16 LE) (2)
GFX_R           equ     $E12A   ; radius (int16, >=0 -- resident guards G4-rneg) (2)
GFX_ASPMAJ      equ     $E12C   ; 0 = x-major (aspect<=1), 1 = y-major (aspect>1) (1)
GFX_ASPS        equ     $E12D   ; 8.8 minor scale S, round(minor_ratio*256); 256=no scale (2)
GFX_ARCF        equ     $E12F   ; 0 = full circle (ignore S/E), 1 = arc (apply the mask) (1)
GFX_SVX         equ     $E130   ; start boundary vector X, screen-offset scaled ints (2)
GFX_SVY         equ     $E132   ; start boundary vector Y (2)
GFX_EVX         equ     $E134   ; end boundary vector X (2)
GFX_EVY         equ     $E136   ; end boundary vector Y (2)
GFX_FULLW       equ     $E138   ; full-wrap flag (0/1): the two boundaries land in the
                                ; SAME (octant,pos) cell but their RAW (oct,u14) records
                                ; differ -- a near-2*pi sweep, keep everything. Replaces
                                ; GFX_ARCBIG: the D-ARCMASK wedge test needs no big/small
                                ; split, the cyclic pair compare covers both. (1)
GFX_QX          equ     $E139   ; midpoint-circle octant state: x (2)
GFX_QY          equ     $E13B   ; midpoint-circle octant state: y (2)
GFX_QD          equ     $E13D   ; midpoint-circle octant state: d (signed) (2)
GFX_PX          equ     $E13F   ; tenant scratch: current (mirrored+scaled) offset X,
                                ; used as the arc cross-product test point P (2)
GFX_PY          equ     $E141   ; tenant scratch: current offset Y (2)
GFX_CS_AX       equ     $E143   ; circleparse scratch: cpt_angle_from_arga's neg-flag
                                ; cell address stash (was gfx_cross_ge0's A.x -- that
                                ; routine is retired, D-ARCMASK) (2)
GFX_CS_AY       equ     $E145   ; circleparse scratch: cpt_angle_from_arga /
                                ; cpt_boundary_prep's dest-record-base stash (2)
GFX_M           equ     $E147   ; D-ARCMASK: M = floor(r/sqrt(2)), the octant's top
                                ; step index; gfx_circ_wedge_prep, once per CIRCLE (2)
GFX_WS_P        equ     $E149   ; wedge START boundary: in-octant position, 0..M-1 (2)
GFX_WS_O        equ     $E14B   ; wedge START boundary: octant 0..7 (1)
; --- D-ARCMASK (2026-08-17, docs/arcmask-msx1-characterization.md §5.5): the arc
; boundary records are (oct_raw, u14) pairs -- the angle's octant count and its
; 14-bit fraction into the octant, both trunc'd, from a SINGLE-precision-rounded
; angle. Replaces the 2026-07-21 (brad, sign_c, sign_s) records: the boundary is
; the octant loop's STEP INDEX distributed linearly over the in-octant angle,
; measured against 54 whole reference planes, not a rounded exact ray. The
; records keep the old cells' addresses and 4-byte-per-boundary size.
GFX_SOCT        equ     $E14C   ; start: trunc(|a0|*4/pi), RAW/unmasked int16 (the
                                ; full word feeds the full-wrap detector; only the
                                ; low 3 bits are the octant) (2)
GFX_SU14        equ     $E14E   ; start: trunc(frac * 16384), 0..16383 (2)
GFX_EOCT        equ     $E150   ; end: trunc(|a1|*4/pi), RAW/unmasked (2)
GFX_EU14        equ     $E152   ; end: trunc(frac * 16384) (2)
GFX_SNEG        equ     $E154   ; resident: start angle was negative -> spoke pending (1)
GFX_ENEG        equ     $E155   ; resident: end angle was negative -> spoke pending (1)
GFX_WE_P        equ     $E156   ; wedge END boundary: in-octant position, 0..M-1 (2)
GFX_WE_O        equ     $E158   ; wedge END boundary: octant 0..7 (1)
GFX_WRAPF       equ     $E159   ; wedge wraps 0: pair S > pair E lexicographically (1)
                                ; -> ends $E15A (the G3/G4/G5 window ends $E15F
                                ; inclusive; well within the G3 header's budget note)
; G5 PAINT (docs/spec-basic-graphics-g5.md §6). ONE new cell in the same window:
; the resident-marshalled border colour (the raw, NOT range-checked comparison
; value -- spec §3/§5). Same discipline as G3/G4 (dead during any graphics
; statement, below the PLAY ISR region; the LINEBUF overlay is retired -- G3
; header). GFX_OP=5 selects the tenant arm; GFX_OP/GFX_C stay shared with G1-G4.
; The much bigger span-stack + its own working scratch do NOT fit here (only 9 B
; remain, $E157-$E15F) -- they live in a separate repack-only RAM window below
; (GFX_PSTK).
GFX_B           equ     $E156   ; border colour B, RANGE-CHECKED against the mode's
                                ; domain before it is stored: 0..255 in SCREEN 2,
                                ; 0..15 in MULTICOLOUR, else ERR 5 (D-PAINTBORD --
                                ; ⚠️ this comment used to read "NOT range-checked").
                                ; Still 1 B, and still the LOW byte -- what changed
                                ; is that a value whose HIGH byte is non-zero can no
                                ; longer reach the store. (1) -> ends $E157
; D-GIRDOM: POINT's OWN marshal cells. POINT used to hand the tenant its target
; through GXPOS/GYPOS, which is a BASIC-VISIBLE work-area cell -- and MEASURED
; (rows w.pt.on / w.pt.step) both references leave GXPOS/GYPOS untouched by a
; POINT, on-screen or off. `v.point0` could not see it: that row reads GRPACX/
; GRPACY, which POINT does not touch on either side, so the leak sat behind a
; green row for the whole life of G2. ⚠️ THE $E030 BLOCK HEADER'S "coordinates
; are marshalled through the pinned GXPOS/GYPOS cells (the resident stub writes
; them anyway)" IS EXACTLY THE ASSUMPTION THAT WAS WRONG -- true for PSET/
; PRESET/LINE/PAINT, which are statements that MOVE the work area, and false for
; POINT, which is a read-only function. One byte each: the resident only reaches
; here after gfx_in_range passed, so both coordinates are 0..255.
GFX_PTX         equ     $E158   ; main->tenant: POINT target X, 0..255 (1)
GFX_PTY         equ     $E159   ; main->tenant: POINT target Y, 0..191 (1) -> ends $E15A
GFX_CPHASE      equ     $E157   ; CIRCLE-parse co-routine phase (sub/circleparse.asm):
                                ; which arg the tenant last requested, so it resumes at
                                ; the right point after each resident eval-bounce
                                ; (0=centre 1=r 2=c 3=start 4=end 5=aspect). (1)
; G7 sprites (docs/spec-basic-graphics-g7.md §8). Table bases + the VDP register
; mirror the sprite size lives in; the parameter block itself is in the repack-only
; window next to GFX_VBUF below (the G3/G4/G5 window's last 9 B do not fit it).
GFX_SPAT_BASE   equ     $3800   ; SCREEN 1/2 sprite PATTERN generator table base
GFX_SATR_BASE   equ     $1B00   ; SCREEN 1/2 sprite ATTRIBUTE table base (4 B per plane)
RG1SAV          equ     $F3E0   ; VDP register 1 mirror; bits 1..0 = SCREEN's sprite-size
                                ; argument (bit1 = 16x16, bit0 = magnify), which measurably
                                ; PERSISTS across later SCREEN statements (spec G7 §5)
; G8 VDP(n) / BASE(n) (docs/spec-basic-graphics-g8.md). The TMS9918's registers are
; write-only, so every MSX reads them back through the RAM mirrors: RG0SAV..RG7SAV
; are what `VDP(0..7)` returns, and STATFL (the frame ISR's status copy) is what
; `VDP(8)` returns -- measured, NOT a live port read (spec §4.2). BASETAB is the
; 20-word per-mode table-base map `BASE(n)` reads and `BASE(n)=` writes; our C-BIOS
; runtime maintains it identically to the reference in every mode (spec §4.1), which
; is what let the descoped BASE stub be retired.
RG0SAV          equ     $F3DF   ; VDP register 0..7 mirrors ($F3DF..$F3E6); RG1SAV = +1
STATFL          equ     $F3E7   ; VDP status-register copy kept by the frame ISR
BASETAB         equ     $F3B3   ; BASE(0..19): 20 LE words, 4 groups of 5 (name, colour,
                                ; pattern generator, sprite attribute, sprite pattern),
                                ; group g describing SCREEN g

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
; FCH_MODES — per-channel mode array [0..FCH_CEIL]; [0] unused, [ch] = 0 closed /
; 1 INPUT / 2 OUTPUT / 5-6 LPT-CRT / 7-8 CAS (FCH_CEIL+1 bytes).
; ⚠️ D-FCH §3.2: the repack build's FCH_CEIL is 15, so this array is 16 B and no
; longer fits the 3-byte $E013 slot (INDLR_N sits at $E016). It moves into the
; page-3 window S-FCH-1 freed by retiring the static FCH_CTX table ($EA00..$EAFF,
; below LINEBUF $EB00).
FCH_MODES       equ     $EA00   ; 16 B ($EA00..$EA0F)
; D-LNLIST (docs/spec-basic-lnlist.md R-L1..R-L3): the tokeniser's LINE-NUMBER
; MODE. A branch keyword (GOTO/GOSUB/THEN/RESTORE/RUN/RESUME) arms it and it runs
; to the end of the STATEMENT, turning every digit run that would begin a numeric
; constant into a $0E,<line> reference instead -- `GOTO 1+5` is TWO line-number
; references on both references. Cleared by anything ALPHABETIC (a reserved word
; or a variable name), by '?'/'_' (symbols that expand to word tokens), and by
; ':'. Lives in the free $E013..$E015 gap FCH_MODES vacated for $EA00.
; Same aliasing argument as TKNAME/TKRADIX/TKRTOK ($E028..): a line's whole
; tokenise pass completes BEFORE any of its tokens execute, so this is dead for
; the entire duration of any statement's execution.
TKLNUM          equ     $E013   ; tokeniser: 1 = line-number mode is armed (1)
INDLR_N         equ     $E016   ; INPUT$(n,#f): remaining bytes to read (transient, 1)
MRG_PTR         equ     $E017   ; MERGE: write cursor into LINEBUF for the current line (2)
; Random-access (FIELD/LSET/RSET) transient parse/store scratch (Phase 2c slice 1).
; All dead outside a single FIELD or LSET/RSET statement. Free $E019.. gap below
; CURPTR ($E020). See basic/field.asm + PROVENANCE.md §random-access records.
FLD_CUROFF      equ     $E019   ; FIELD: running byte offset into the record buffer (2)
FLD_CHAN        equ     $E01B   ; FIELD/LSET/RSET: the channel being fielded (1)
LRSET_JUST      equ     $E01C   ; LSET/RSET: 0 = left-justify, 1 = right-justify (1)
LRSET_W         equ     $E01D   ; LSET/RSET: destination field width (1)
LRSET_DEST      equ     $E01E   ; LSET/RSET: destination ADDRESS of the store (2).
                                ; D-LRVAR renamed this from LRSET_OFF (same address,
                                ; 0 RAM): it held the field's OFFSET while the only
                                ; destination was FSECTOR_BUF + off, but a
                                ; non-FIELDed LSET writes into the target variable's
                                ; own heap body, which no offset into a record buffer
                                ; names. Both callers now compute the address and
                                ; sub/lrsetst.asm just loads it (spec §4.1).
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
; MID$-statement: the destination var's descriptor address, stashed for one
; MID$(A$,n,m)=B$ so the token cursor can stay in HL through the arg parse.
; Repack (arrays slice-4a): a DEDICATED cell in the freed STRTAB window
; (ABOVE the last-used byte STRENG_SPARE $E3E5, below the $E560 WBUF wall) — it
; can NO LONGER alias NUMBUF, because slice-4a moved HEX$/OCT$'s digit-building
; into NUMBUF (sub-side sh_hex_build/sh_oct_build), so `MID$(A$,1)=HEX$(N)`
; would clobber the stashed dest across the RHS str_eval. 2 B.
; BUG A (Fable, 2026-07-17): the S8 fix hardcoded $E3D9 from a STALE layout
; comment (SH_* as 5 B / TEMPTOP $E372). The SH_* param block is actually 18 B
; (twelve extra cells added since), so the temp-descriptor pool assembles to
; TEMPPOOL $E381..TEMPBASE $E3E1 and $E3D9 lands INSIDE the 3rd temp slot's ptr
; field ($E3D8-$E3DA). Any MID$(A$,..)=RHS whose RHS pushed >=3 temps overwrote
; the stashed dest -> sh_mid_store LDIR'd through a garbage pointer (silent
; corruption). Now anchored SYMBOLICALLY to STRENG_SPARE+1 so it tracks the real
; top of the block; $E3E6, 378 B under the wall. (That anchor was TMISMATCH+1
; until D-PENDERR retired the TMISMATCH cell; STRENG_SPARE is the same address,
; deliberately left standing so MIDS_DEST does NOT move -- see its definition.)
MIDS_DEST       equ     STRENG_SPARE + 1
; Console INPUT (repack build only): the LINEBUF read cursor for linebuf_getbyte
; (basic/input.asm). LINEBUF is one PAGE (page-aligned, <= 256 B), so a single low
; byte suffices. Aliases NUMBUF like MIDS_DEST — dead during INPUT, which formats no
; numbers; the MID$ statement and console INPUT never execute simultaneously.
INP_CURSOR      equ     NUMBUF   ; console INPUT LINEBUF read cursor (1 B, aliases NUMBUF)
; --- The line buffers (D-LINEMAX, docs/spec-basic-linemax.md) ---------------
; MEASURED (docs/linemax-vg8020-characterization.md §1): the reference's last intact
; input line is 254 characters; both machines then DROP the tail, keep and store the
; line, and raise nothing — the disposition already agreed, only the ceiling differed.
; So LINEMAX is one constant, and in the repack build it is the reference's.
;
; The single-low-byte idiom in BOTH readers (repl.asm read_line, files.asm
; ascii_read_lines) and in console INPUT (input.asm `ld h,high LINEBUF`) needs a
; PAGE-ALIGNED base and <= 256 bytes — NOT <= 96. $EB00+254 = $EBFE is one page, so
; no reader logic changes and the item's feared "one-page trick blocks this" does not
; hold.
;
; ⚠️ D-FCH §3.3: MOVED $BA00 -> $EB00 (page 2 -> page 3). It sat in page 2 only
; because D-LINEMAX had to put it somewhere, and it cost 1792 B of TXTMAX to do
; so. S-FCH-1 freed $EA64..$EE63 by retiring the per-channel sector save copies,
; and this buffer + TOKBUF move into that window so TXTMAX can climb back.
; Page 3 is always-mapped RAM and is NOT paged out by a sub-ROM CALSLT (the
; tokenise tenant takes page 0, the fatprim/detok tenants page 1), so both
; buffers stay addressable from the tenants that fill them.
LINEBUF         equ     $EB00   ; repack: ASCII input line from the keyboard (LINEMAX B)
LINEMAX         equ     255     ; 254 chars + the 0 terminator (measured reference ceiling)
; The largest STORABLE line number. Anything past this is refused outright with
; `Syntax error` (ERR 2) at line entry -- MEASURED on both the VG-8020 and the
; CF-3300, which agree: 65529 stores, 65530 and 99999 store NOTHING
; (docs/lnblank-msx1-characterization.md §4 / §10.1, D-LNBLANK R4). It is the
; documented MSX-BASIC maximum, and it is a CEILING and not a mask: unguarded,
; `99999 REM` silently stored a line numbered 99999-65536 = 34463.
LINENO_CEIL     equ     65529
; D-LNREF R-V (docs/spec-basic-lnref.md §2): the SAME ceiling bounds a line-number
; REFERENCE inside a statement -- with a DIFFERENT response. A leading number past
; it is REFUSED; a reference past it is SPLIT, the digit that would overflow
; starting a fresh $0E. bl_acc tests the accumulator BEFORE taking a digit, so the
; bound it wants is the largest value that may still take one:
;   v*10 + d > LINENO_CEIL  <=>  v >= (LINENO_CEIL/10)+1   for d <= 9
; = 6553. `GOTO 65529` is one reference; `GOTO 65530` is 6553 then 0, measured on
; both references (docs/lnref-msx1-characterization.md §2).
LINENO_ACC_STOP equ     (LINENO_CEIL/10)+1
; TOKBUF — the crunch destination. Sized 576 B for a 314-byte LOGICAL body limit, and
; the gap between those two numbers is deliberate.
;
; 🔴 The crunch EXPANDS and was BOUNDED NOWHERE (§2): `0#` is two source characters
; and NINE bytes (DBL_TOKEN + 8), so a 27-CHARACTER line already overran the old
; 96-byte buffer, and the worst case wrote 407 bytes into it — over ARYTAB, the whole
; error-trap block, ZTRAP, POOLSIZE, into STRTAB — silently, and stored the line.
; After it zerobas could not execute `B=7`. The reference refuses at 315 body bytes
; with `Line buffer overflow` (ERR 25), measured; TOKMAX_BODY is that ceiling.
;
; WHY 576 AND NOT 315. The overflow test is ONE site (tk_end, tokenise.inc) rather
; than one per emit site — the spec warned that bounding every emit site is "easy to
; miss one", and it was right for a reason it did not name: tk_str_loop, tk_rem_rest
; and tk_data_rest are INNER COPY LOOPS that never re-enter tk_loop, so a per-
; character test at the loop head would not have covered them either. Those loops are
; strictly 1:1 (one source byte -> one dest byte) and their input is bounded by
; LINEMAX, so the buffer only has to ABSORB the worst single pass and let tk_end
; adjudicate: 314 (accepted body) + 258 (the widest one-character step — tk_apos's 3
; bytes plus a 253-byte verbatim tail) + 1 (terminator) = 573, rounded to 576. The
; bound is then PROVABLE from LINEMAX rather than audited emit site by emit site.
; ⚠️ D-FCH §3.3: MOVED $B700 -> $EC00, into the window S-FCH-1 freed. This is the
; buffer that BLOCKED TXTMAX: it sat immediately above the text ceiling, so
; nothing above it could be reclaimed until it moved. See LINEBUF above.
TOKBUF          equ     $EC00   ; repack: crunch buffer, 576 B ($EC00..$EE3F)
TOKBUFSZ        equ     576     ; physical size (absorbs one over-long pass, above)
TOKMAX_BODY     equ     314     ; logical ceiling: a longer body is REFUSED (ERR 25)
; (The retired lean 16 KB cart kept the OLD, UNBOUNDED crunch and the old 96-byte
; TOKBUF — a known defect deliberately carried forward rather than fixed, since the
; build was on its way out. It is gone; D-LINEMAX's bound is the only crunch now.)
; --- the $E1C0..$E240 window: HISTORY, and what actually lives there --------
; This span was Phase 1's fixed variable table VARTAB: 32 dynamically-allocated
; 4-byte entries [name0][name1][value:2], names significant to 2 characters
; (public MSX-BASIC language reference), name0=0 marking the first free slot.
;
; It has been dead since arrays slice-4b (docs/spec-basic-arrays-slice4b-scalar-
; reloc.md §2/Q3) relocated numeric scalars into the real-MSX contiguous chain
; (program text -> scalars -> arrays -> free -> string heap), sharing arrays'
; own [PRGEND+2, FRETOP) region. The four constants that described it --
; VARTAB / VARENTSZ / VARSLOTS / VAREND -- were read ONLY by vars.asm's
; var_find / var_get_key / var_set_key, and those had no callers at all; all
; seven were deleted by the ROM REGION STRUCTURE REVIEW's R1 carve
; (docs/spec-rom-region-rebalance-r1.md A1/A4).
;
; ⚠️ THE WINDOW IS NOT FREE RAM, AND THE COMMENTS BELOW USED TO SAY IT WAS.
; Three later slices already spent it, each describing itself as homing in
; "the freed VARTAB window" -- so a reader arriving at the R1 carve expecting
; 128 recoverable bytes finds ARYTAB, DIRECTF, SAVSTK, SAVTXT and ZTRAP sitting
; in them. Measured 2026-07-30: the only free RAM in the neighbourhood is
; $E226..$E23F, and it is accounted for on its own below. R1 therefore frees
; 122 ROM bytes and ZERO RAM bytes (review §4).
;
; What lives here now, low to high: ARYTAB $E1C0, DIRECTF $E1C2, SAVSTK $E1C3,
; SAVTXT ..$E1D1, ZTRAP $E1D1..$E207.
;
; ⚠️ AND THERE IS NOW A HOLE: $E1C5..$E1CA (6 B). D-REHOME (2026-08-01,
; docs/sysvar-rehoming-decisions.md) moved ERRCODE/ERRLINE/ONELIN/ONEFLG OUT of
; this window to their PUBLISHED addresses ($F414/$F6B3/$F6B9/$F6BB), leaving
; ERRRESUME $E1CB and SAVTXT $E1CF above the gap. The 6 bytes are NOT reclaimed
; and NOT re-packed -- deliberately, because repacking this window is exactly the
; kind of space-driven move that put the published variables here in the first
; place. If you want them, take them as a decision, not as tidying.
; 🔴 The probe asserts these six stay QUIET (C-VACATED in
; probes/basic/basic_probe_sysvarsweep.py): a leftover store at a vacated address
; is a half-done relocation that every other check would report as green.
;
; ARYTAB is the ONE new STORED live cell the
; target model needs (§2/§4): scalar base is DERIVED as (PRGEND)+2 exactly
; like the array base used to be; ARYTAB = end of the scalar region = base
; of the array region (every array-anchor site that used to read
; `(PRGEND)+2` now reads `(ARYTAB)` instead -- sub/arrays.asm ary_find/
; ary_alloc, sub/strheap.asm strheap_aryend/sg_walk_arrays, basic/arrays.asm
; ary_reset). Homed at the foot of the now-dead VARTAB span so no new RAM
; claim was needed anywhere else (own choice -- just-freed RAM).
; ❌ RE-HOMING DECISION: **REJECT-GROUP** — stays at $E1C0, published address
; $F6C4 (docs/sysvar-rehoming-decisions.md §3). ⚠️ NOT rejected on semantics:
;   SEMANTICS  SAME-VAR, BYTE-IDENTICAL to both references in all four
;              direct-mode states ($8003 -> $800E -> $8024, and -> $8009 for a
;              string scalar). zerobas' unified variable chain reproduces the
;              reference's variable-table layout exactly. It is the same
;              variable at a different address, measured.
;   WHY REJECT The published contract is a CHAIN, not a cell:
;              TXTTAB $F676 <= VARTAB $F6C2 <= ARYTAB $F6C4 <= STREND $F6C6, and
;              a consumer computes array space as STREND-ARYTAB. zerobas has NO
;              stored VARTAB (derived as (PRGEND)+2, below) and NO STREND at
;              all. 🔴 Publishing a plausible ARYTAB beside two power-on ZEROS
;              yields a large NEGATIVE length — a confident wrong answer — where
;              today a consumer gets 0-0 and an obviously dead reading.
;              Honouring one member of a group its consumers read as a set is
;              WORSE than honouring none.
;   ⚠️ To revisit, cost publishing the WHOLE chain; do not move ARYTAB alone.
ARYTAB          equ     $E1C0   ; live 2-byte cell: scalar-region end == array
                                ; base (repack only; VARTAB's own dead RAM)
; Error-handling S1 (docs/spec-basic-error-handling.md §5.5): the freed VARTAB
; window $E1C2..$E240 is the home for error-handling state. D-2 needs one byte:
DIRECTF         equ     $E1C2   ; 1 = executing a DIRECT-mode line, 0 = running a
                                ; stored program. Read by fre_abort_low to decide
                                ; the run-mode " in <line>" suffix. Written by
                                ; run_prog/ex_cont (0) and dispatch_line (1) before
                                ; any statement runs, so it is always valid when an
                                ; error reads it — no cold-boot init needed.
; Error-handling S2b (docs/spec-basic-error-handling-s2b-packet.md §3): the
; trap + RESUME state. SAVSTK claims the $E1C3/C4 window S2a reserved for it.
; ⏸ RE-HOMING DECISION: **DEFER** — stays at $E1C3, published address $F6B1
; (docs/sysvar-rehoming-decisions.md §3). ⚠️ It is not "different", it is
; UNMEASURED, and the difference matters:
;   SEMANTICS  NO READING. $F6B1 is NO-ORACLE on absolute value ($F09E on the
;              VG-8020 vs $DB95 on the CF-3300 — two different stack tops) AND
;              refsΔ=+0 under every stimulus, so the delta route that rescued
;              FRETOP does not rescue this one either. The references simply do
;              not move it at any moment this instrument can capture.
;   WHAT WOULD SETTLE IT: a capture taken INSIDE a running statement rather than
;              at a prompt (the holds/breakpoint mechanism basic_probe_bload.py
;              already uses). Another direct-mode line will not do it.
;   ⚠️ Until then, "zerobas' SAVSTK is an SP anchor and the published one might
;      not be" stays an OPEN question, not an answered one.
SAVSTK          equ     $E1C3   ; 2 B: SP anchor for the trap unwind. Written by
                                ; run_prog / dispatch_line's direct-exec path
                                ; before any statement runs; raise_error's trap
                                ; branch does `ld sp,(SAVSTK)` to reset the stack
                                ; to a clean run-loop depth before jumping to the
                                ; handler line (the trap fires from arbitrary
                                ; call depth). No cold-init needed (written
                                ; before read, same as DIRECTF).
; --- ✅ RE-HOMING DECISION (D-REHOME, docs/sysvar-rehoming-decisions.md) -----
; These two were `ERRCODE $E1C5` / `ERRLINE $E1C6` -- the published variables
; under private names at private addresses. DECISION: **HONOUR**, name and
; address, and the reasons are measured, not argued:
;   SEMANTICS  SAME-VAR, exactly. Both references and zerobas move ERRFLG 00->08
;              under `GOTO 99999` and ERRLIN 0000->FFFF in direct mode /
;              ->0014 (=20) from a stored line -- the 65535 direct-mode
;              convention included (make sysvarsweep, s1-err + s7-fired).
;   OBSERVER   🔴 `ERR` READS $F414 on a real MSX: `POKE&HF414,0 : PRINT ERR`
;              prints 0 on BOTH references. That is a READ-BACK, so a write-only
;              MIRROR would satisfy PEEK and FAIL POKE -- mirroring is refuted
;              here by an already-filed measurement, and only relocation works.
;   COST       ZERO ROM bytes: every access is through the symbol.
;   PUB-FREE   measured -- zerobas' byte at each published address never moved
;              in any of the 9 swept states, so nothing (zerobas or C-BIOS)
;              claims it.
ERRFLG          equ     $F414   ; 1 B: last error's MSX ERR code (0 = none yet).
                                ; Set by raise_error; read by the ERR function.
                                ; ⚠️ The PUBLISHED address. Do not re-home it
                                ; back into the $E1Cx window for space: that is
                                ; how it got there the first time, and the
                                ; placement was never a decision to reject the
                                ; standard address.
ERRLIN          equ     $F6B3   ; 2 B: last error's line number, or 65535 if it
                                ; happened in direct mode. Set by record_errline;
                                ; read by the ERL function. PUBLISHED address.
; --- ✅ D-DOTLINE: `.`, the current-line pseudo-line-number ------------------
; docs/spec-basic-dotline.md, measured in docs/dotline-msx1-characterization.md.
; The line `.` names in LIST / DELETE (and in AUTO / RENUM / EDIT, when those
; are dispatched). `.` is NOT crunched -- it reaches every statement as the
; literal $2E (R-DOT1) -- so the resolver is sub-side in ldr_num, the one place
; both le_delrange and le_lstrange read a line number from.
;
; ✅ RE-HOMING DECISION: **HONOUR** the published name AND address, D-REHOME's
; four-point record (docs/sysvar-rehoming-decisions.md §3):
;   SEMANTICS  SAME-VAR, measured. 24 `clp` rows PEEK $F6B5 on both references
;              after 24 different stimuli, and every one AGREES with its
;              behavioural `cln`/`cle` twin -- which is what makes the PEEK
;              evidence about `.` and not about a byte.
;   OBSERVER   PEEK: the cold value (0) and NEW's non-reset are readable ONLY
;              this way. ⚠️ `LIST .` is structurally blind to both -- on a cold
;              machine, and after a NEW, the program is EMPTY, so nothing is
;              listed whatever the cell holds. Whether POKE-then-`LIST .` reads
;              back is NOT measured (spec §3).
;   COST       ZERO ROM bytes: every access is through the symbol, and no
;              existing cell moves. The free $E234..$E23F window is untouched.
;   PUB-FREE   measured -- zerobas' byte at $F6B5 read 0 in ALL 24 swept states
;              before this slice, so nothing (zerobas or C-BIOS) claimed it.
;
; 🔴 FOUR WRITERS, AND `ERRLIN` ABOVE IS *NOT* ONE OF THEIR TWINS:
;   (a) storing a line -- insert, replace, or the bare-line-number delete --
;       records the number TYPED, even when the line is thereby removed
;       (sub/lineedit.asm le_ok);
;   (b) the LIST walk records the LAST LINE IT PRINTED, and a walk that prints
;       nothing writes nothing (basic/list.asm list_walk). ⚠️ That is the SHARED
;       walk on purpose: an ASCII SAVE writes $F6B5 too and a tokenised SAVE
;       does not, measured (characterization §4, cf3300 only);
;   (c) an error in a STORED line records the erroring line (record_errline's
;       RUN-MODE ARM ONLY). 🔴 A DIRECT-MODE error writes NOTHING -- it does not
;       take ERRLIN's 65535 sentinel, so the two cells part company inside one
;       routine and the write may NOT move to a shared tail;
;   (d) RESUME, any form, records the line it is IN (ex_resume).
; NON-writers, each measured with its own row: RUN, STOP/break, CONT, CLEAR,
; **NEW**, the DELETE VERB, a direct-mode statement, GOTO, GOSUB, ON ERROR GOTO,
; a direct-mode error, a tokenised SAVE.
; ⚠️ NEW DOES NOT RESET IT (clp-new). Do not "tidy" a zero into new_prog: that
; is the TRACEFLAG shape one line down in this file (NEW is TRON's only
; non-statement writer) and it is measurably wrong here.
DOT             equ     $F6B5   ; 2 B: the line `.` names. Cold value 0 (init).
                                ; PUBLISHED address and PUBLISHED name.
; ✅ RE-HOMING DECISION: **HONOUR** ($E1C8 -> the published $F6B9).
;   SEMANTICS  SAME-VAR. Under `10 ON ERROR GOTO 100 / 20 STOP / 100 STOP / RUN`
;              the references and zerobas both store $8015 -- byte-identical.
;              🟢 And the ARMED-vs-FIRED control pair is what proves this is
;              ONELIN's own reading: ONELIN moves in BOTH s6-armed and s7-fired
;              (it is ARMED state) while ONEFLG/ERRFLG/ERRLIN move in s7 only.
;              ⚠️ Under s7 the two differ ($801C vs $8019) and that is NOT an
;              ONELIN divergence: `20 GOTO 99999` tokenises 3 bytes shorter on
;              zerobas, so the pointer is right and the text it points into is
;              what differs. Filed separately -- do not "fix" ONELIN for it.
;   OBSERVER   PEEK: whether a handler is armed, and where.
;   COST       ZERO ROM bytes (all access symbolic). PUB-FREE measured.
ONELIN          equ     $F6B9   ; 2 B: ON ERROR handler line's LINK address (the
                                ; find_line_bc / GOTOTGT-shaped value, NOT the
                                ; token body) — 0 = no handler armed. Written by
                                ; ex_on_error; read by raise_error's trap
                                ; decision.
                                ; ✅ Reset scope MEASURED 2026-07-29 (14 rows on
                                ; the VG-8020, docs/spec-basic-onelin-reset-
                                ; scope.md): a handler is disarmed EXACTLY when
                                ; the variable table is cleared — RUN, NEW,
                                ; CLEAR (direct-mode AND in-run, so MAXFILES
                                ; too) and EVERY program EDIT. So the zero lives
                                ; in vars_reset (basic/arrays.asm), the one
                                ; routine all of those funnel through, plus init
                                ; for cold boot. NOT clear_vars — a program edit
                                ; never reaches it.
                                ; ⚠️ The old note here read "NOT clear_vars, so
                                ; NEW/CLEAR alone do not disarm a handler" and
                                ; was WRONG IN BOTH HALVES: CLEAR does disarm,
                                ; and the reason is not the one that sentence
                                ; implies. ⚠️ It is also NOT "invalidate a stale
                                ; link when what it points into MOVES": the
                                ; reference disarms on an APPEND that moves
                                ; nothing (the `onelin_edit_append` gate row is
                                ; what falsified that reading).
; ✅ RE-HOMING DECISION: **HONOUR** ($E1CA -> the published $F6BB), AND the
; sentinel with it.
;   SEMANTICS  SAME-ROLE, then SAME-VAR. Measured under s7-fired the references
;              store **$FF**, not 1 -- so the address was one of two divergences
;              and the flag VALUE was the other. Both readers here test it with
;              `or a` (boolean), and the single setter was `ld a,1`, so matching
;              the reference's $FF costs ZERO bytes and cannot change control
;              flow. Honouring the address while leaving `1` would have
;              published a value no reference ever holds.
;   OBSERVER   PEEK: "am I inside a handler". ⚠️ NOT group-bound -- unlike the
;              ARYTAB pointer chain, a one-byte boolean is read on its own, so
;              the REJECT-GROUP argument does not reach it.
;   COST       ZERO ROM bytes. PUB-FREE measured.
ONEFLG          equ     $F6BB   ; 1 B: $FF = currently inside a handler (no RESUME
                                ; yet) — a second error while set is a forced
                                ; abort with the INNER message (real-MSX nested-
                                ; error semantics, via raise_error_forced/rerr_
                                ; report).
                                ; ⚠️ Reset scope: NOT "same as ONELIN" (it said
                                ; so for a whole arc, and that was the bug —
                                ; docs/spec-basic-oneflg-reset-scope.md, MEASURED
                                ; on the VG-8020, six divergent rows). ONELIN's
                                ; hypothesis above is about RE-ENTRY hooks; this
                                ; flag also has to be cleared on the way OUT:
                                ;   * ANY abort — run-mode AND direct-mode, even
                                ;     while a run is only SUSPENDED (site A,
                                ;     fre_abort_low, basic/arrays.asm);
                                ;   * ANY run TERMINATION — END (site B, ex_end)
                                ;     and running off the end of the program.
                                ; ⚠️ SITE C IS DELETED (D-ERR21, 2026-08-21
                                ;   re-read as D-RETZ). This list used to name
                                ;   "site C, rp_lp's $0000-link exit" as the
                                ;   third clearing site. There is no store
                                ;   there any more: on the arm that survives
                                ;   that exit, ONEFLG is already 0 by the test
                                ;   just above it, and on the arm that does not,
                                ;   the ERR 21 abort funnels through site A,
                                ;   which clears unconditionally. THE RULE IS
                                ;   UNCHANGED -- the flag still has to be clear
                                ;   after running off the end -- and deleting
                                ;   site C also FIXED a defect it was causing
                                ;   (a typed line falls through dir_line's own
                                ;   $0000 link into that exit, so site C killed
                                ;   the handler context on every benign direct
                                ;   line typed at a `Break in <handler>`
                                ;   prompt). basic/program.asm carries the whole
                                ;   argument at the site itself.
                                ; It is DELIBERATELY kept across a STOP/Ctrl-STOP
                                ; SUSPENSION: CONT has to be able to resume
                                ; INSIDE the handler, and its RESUME must still
                                ; work there. Gated by the oneflg_* rows of
                                ; probes/basic/basic_probe_error_trap.py, two of
                                ; which fail if the clear is placed anywhere that
                                ; also catches a STOP.
ERRRESUME       equ     $E1CB   ; 4 B: resume context captured at trap time —
                                ; [0..1] the erroring statement's CURLINE (link
                                ; addr), [2..3] the erroring statement's text
                                ; pointer (from SAVTXT). Read by the RESUME
                                ; family. No cold-init needed (written by the
                                ; trap before RESUME can ever read it — ONEFLG=0
                                ; guards a premature read via "RESUME without
                                ; error", ERR 22).
; ❌ RE-HOMING DECISION: **REJECT-UNOBSERVABLE** — stays at $E1CF, published
; address $F6AF (docs/sysvar-rehoming-decisions.md §3).
;   SEMANTICS  MEASURED: both references hold a CONSTANT $F40F at $F6AF in all
;              nine swept states. By the time the machine is back at a prompt —
;              the only instant this instrument captures — the reference's
;              SAVTXT points at its own line buffer, so its LIVE value is not
;              reachable and no BASIC-visible channel reads it.
;   ⚠️ "Never moves" here means UNOBSERVABLE, not INERT. It reads like "nothing
;      to honour" and it means the opposite: the question could not be put.
SAVTXT          equ     $E1CF   ; 2 B: the CURRENT statement's text pointer,
                                ; refreshed at every exec_stmt entry (line start
                                ; AND after every ':' via ex_sep) — mirrors
                                ; MSX's own SAVTXT/NEWSTT. This is the ONLY
                                ; source for the erroring statement's start
                                ; address (raise_error fires from arbitrary
                                ; call depth, not at the statement head). No
                                ; cold-init needed (written before any raise_
                                ; error can read it via ERRRESUME capture).
; Interrupt-traps arc (docs/spec-basic-interrupt-traps.md §3): the own-design
; event-trap table ZTRAP + its bookkeeping, homed in the freed VARTAB window
; directly after the error-trap state (SAVTXT ends at $E1D1). NOT the reference
; TRPTBL address or bit layout — behaviour-faithful, layout own-design (quarantined
; in PROVENANCE.md alongside CONTLINE). MUST be zeroed at cold boot (garbage RAM =
; phantom armed traps) — trap_init does this; RUN re-arms via the same reset.
; Repack-only (the whole arc is IF the repack build).
ZTRAP           equ     $E1D1   ; 18 entries * 3 B = 54 B ($E1D1..$E207). Each
                                ; entry = [state:1][handler_line_link:2].
                                ; state bits: 1-0 = 00 OFF / 01 ON / 10 STOP(user)
                                ; / 11 SERVICING(auto-suspend in handler);
                                ; bit 7 = PENDING (event latched, awaiting dispatch).
                                ; handler_line_link = the find_line_bc/GOTOTGT-shaped
                                ; LINK address (0 = no handler armed). Entry order:
                                ;   0      INTERVAL   1      STOP       2      SPRITE
                                ;   3..7   STRIG 0..4  8..17  KEY 1..10
ZTRAP_ENTSZ     equ     3       ; bytes per entry
ZTI_INTERVAL    equ     0       ; entry index: INTERVAL
ZTI_STOP        equ     1       ; entry index: STOP
ZTI_SPRITE      equ     2       ; entry index: SPRITE
ZTI_STRIG0      equ     3       ; entry index: STRIG 0 (STRIG n -> 3+n, n=0..4)
ZTI_KEY1        equ     8       ; entry index: KEY 1 (KEY n -> 7+n, n=1..10)
ZTRAP_NENT      equ     18      ; total entries
; trap state field bit values
ZTS_OFF         equ     0       ; disabled (OFF clears PENDING too)
ZTS_ON          equ     1       ; enabled — the only state the dispatcher fires
ZTS_STOP        equ     2       ; user-suspended (event latches, does not fire)
ZTS_SERVICING   equ     3       ; auto-suspended while its handler runs
ZTS_STATE_MASK  equ     3       ; bits 1-0 = tri/quad-state
ZTS_PENDING     equ     $80     ; bit 7 = an event occurred, awaiting dispatch
ZTS_SHADOW      equ     $40     ; bit 6 = the DEVICE EDGE SHADOW (traps T2,
                                ; spec-traps-t2-strig.md §3): "this entry's device read
                                ; PRESSED at the last sample". event_poll fires only on a
                                ; 0->1 transition of it, and samples an entry ONLY while
                                ; its state is exactly ON. The arming statement SETS it on
                                ; an OFF/STOP->ON transition ("assume pressed"), so a
                                ; trigger already held when the trap is enabled cannot
                                ; manufacture a spurious edge (VG-8020-measured, §1.2).
                                ; Lives in the entry byte rather than a separate bitmap so
                                ; every access is a 2-byte bit op on the pointer the poll
                                ; already holds. check_traps must PRESERVE it across the
                                ; ON->SERVICING write, or a trigger still held when the
                                ; handler RETURNs would re-fire (oracle Q2 says it must
                                ; not); trap_return_check's SERVICING->ON already does.
ZINTVAL         equ     $E207   ; 2 B: INTERVAL reload period in frames (0 = disarmed)
ZINTCNT         equ     $E209   ; 2 B: INTERVAL live down-counter (frames to next fire)
TRAPENA         equ     $E20B   ; 1 B: count of traps currently in state ON. Gates the
                                ; H.TIMI event_poll (fast-out when 0 — the common no-trap
                                ; program's cost). Bumped by set_state on OFF/STOP->ON,
                                ; dropped on ON->anything (incl. the auto ON->SERVICING).
TRAPPEND        equ     $E21F   ; 1 B (was just past the retired TRAPSTK): 1 =
                                ; event_poll has latched a PENDING on some ON
                                ; trap since the last dispatch. Gates the run-loop
                                ; check_traps subrom_call — set (resident) by event_poll,
                                ; cleared by the dispatch tenant once it drains the
                                ; pending set. Keeps the per-statement cost a RAM load.
TRAPSVC         equ     $E20C   ; 1 B: count of live SERVICING entries == depth of the
                                ; service stack. Gates ex_return's re-enable hook (0 =
                                ; no added cost on a normal RETURN).
; D-CTLPOOL: TRAPSTK ($E20D, 6 x 3 B) IS RETIRED -- $E20D..$E21F is FREE. The
; service record now lives in the control pool (TSP, sysvars below), pushed
; BEFORE its GOSUB frame so it lands under it and stays out of the [CSP,FSP) run
; a `NEXT` walks. TRAPSVC survives as the COUNT, because ex_return gates on it
; with one RAM load on every RETURN and a pointer compare there would cost more.
; 🎯 THE `gsp` KEY IS GONE WITH THE ARRAY. The record sits immediately above its
; own GOSUB frame, so "is this RETURN the trap's own?" is the pointer identity
; TSP == GSP + GOSUB_FRAME -- no stored key, no search.
; ($E220 is FREE again. It held STOPGRACE, the STOP-trap handler grace: a byte set by
; check_traps on fire and cleared by event_poll each VBLANK, during which rp_break
; would not break a SERVICING STOP handler. Retired 2026-07-25, spec §12.3 — the
; entry's own edge shadow (ZTS_SHADOW, bit 6, preserved across a fire) does that job
; without a timing window, and the grace's one-frame expiry made zerobas abort
; handlers the VG-8020 never aborts. Do NOT reintroduce a timing proxy here.)
; --- BLOAD tenant marshalling (docs/spec-traps-t3-key.md §7.6) ---------------
; The BLOAD verb body lives in a sub-ROM PAGE-1 tenant (sub/bload.asm). subrom_call
; clobbers every register and forces CF=0 on return, so the one input and the one
; output ride through RAM -- the fatprim/fcbname pattern. These need their OWN
; cells rather than aliasing DISKOP_HL/DISKOP_STATUS: unlike fcbname (which runs
; strictly in the PARSE phase, before any fat_io_* primitive), the BLOAD tenant
; holds its status ACROSS the whole load, during which the fatprim cells are live
; on every getbyte.
BL_PTR          equ     $E221   ; 2 B: main -> tenant, the token cursor after BLOAD
BL_STAT         equ     $E223   ; 1 B: tenant -> main. 0 = loaded, 1 = `load
                                ; error` PRINTED, and ANY OTHER VALUE IS THE MSX
                                ; ERR CODE THE RESIDENT STUB RAISES (D-BLMODE,
                                ; 2026-08-21): 53 `File not found` (D-BLNF),
                                ; 61 `Bad file mode`. Carrying the CODE rather
                                ; than a fourth index is what makes a new BLOAD
                                ; error face cost ONE byte of main page 1.
                                ; ⚠️ 1 is taken, so BLOAD can never raise ERR 1
                                ; through this cell. Named here and beside both
                                ; arms in sub/bload.asm.
; --- SAVE-family tenant marshalling (docs/decision-fund-time-and-t5.md) ------
; BLOAD's mirror: the SAVE / BSAVE / CSAVE WRITE ENGINES live in a sub-ROM PAGE-1
; tenant (sub/save.asm) beside fatprim, so the fat_io_* write cursor they drive
; is an in-page call instead of a cross-slot round trip. Unlike BLOAD, the parse
; stays RESIDENT -- it calls `eval`, which is main page 1 and switched out while
; a page-1 tenant runs -- so the tenant needs no cursor: by the time it is called
; every argument is already in its RAM home (DISK_FCB_NAME / TSV_NAME / CURPTR /
; DSV_END / TSV_END / EXECPTR / VRAM_FLAG). Only the op selector and the status
; ride. Own cells rather than DISKOP_OP/DISKOP_STATUS for BL_STAT's reason: the
; status is held ACROSS the whole write, during which the fatprim cells are live
; on every putbyte.
SV_OP           equ     $E224   ; 1 B: main -> tenant, SV_OP_* engine selector
SV_STAT         equ     $E225   ; 1 B: tenant -> main, 0 = written, 1 = load_error
SV_OP_BSV_DISK  equ     0       ; BSAVE to disk   (bsv_open ..  bsv_fin)
SV_OP_BSV_CAS   equ     1       ; BSAVE to tape   (bsv_cas_open .. bsv_cas_fin)
SV_OP_SAV_DISK  equ     2       ; SAVE to disk, tokenised (sav_disk_write .. sav_fin)
SV_OP_SAV_CAS   equ     3       ; SAVE"CAS:" / CSAVE, tokenised (tape_save_basic ..)
; --- TRON/TROFF (docs/spec-basic-missing-class.md §3.4) ---------------------
; 1 B in the free $E226..$E23F window (between SV_STAT and the retired STRTAB
; span, which nothing uses). Nonzero = decorate each STORED
; line with `[<lineno>]` before it runs.
;
; The measured scope rules are all "one byte, and almost nothing touches it":
; RUN does NOT reset it, END does not clear it, a line carrying TROFF is itself
; traced, and a TRON typed at the prompt DOES trace a subsequent RUN. Only NEW
; clears it -- so new_prog is the single writer besides the two statements.
TRACEFLAG       equ     $E226   ; 1 B: TRON state (0 = TROFF)
; --- CON_LASTROW: the console's last usable text row (LOCATE's row clamp) ----
; S-MC-2. A NAMED constant rather than a bare 23, because the thing it names is
; not obvious and was measured the hard way (missing-vg8020-characterization
; §3.5, the 18-row `locrow` battery):
;
;   * LOCATE's row does NOT error out of range -- it CLAMPS, and it clamps to
;     the console's OWN bottom row, which is not a language constant. On the
;     reference that row MOVES WITH `KEY`: 22 with the function-key row painted
;     (KEY ON, the boot default), 23 with it off. zerobas paints no function-key
;     row, so it is 23 in both states -- which is why the gate's row-clamp cases
;     are `KEY OFF`-pinned, exactly as the column cases are `WIDTH 40`-pinned.
;   * ⚠️ `CRTCNT` ($F3B1) is the sysvar that LOOKS like the answer and IS NOT:
;     it measures 24 on BOTH machines, under every WIDTH and both KEY states.
;
; So if a function-key row is ever added to this console, THIS is the definition
; that has to move with it -- which is the entire reason it has a name.
CON_LASTROW     equ     23      ; 0-based; CSRY is 1-based, so CSRY max = 24
; --- $E227..$E228 (2 B): FN_RESUME. The cell `LOC_RET` freed -----------------
; D-FNEXPR, 2026-08-21: a filename argument is a string EXPRESSION, so the
; statement cursor no longer sits inside the name -- `fname_expr`
; (basic/files.asm) stages the evaluated name in STRSCR and parks the cursor
; that follows the expression HERE, for OPEN / KILL / NAME to resume from. Two
; bytes, one writer, read once per filename operand. That is the whole tenancy.
; ⚠️ IT IS NOT A SAVED RETURN ADDRESS and must not be treated as one -- unlike
; the LOC_RET below, nothing `ret`s through it and no stack depth depends on it.
; The history of the cell is kept because the reason it was FREED is the reason
; it is SAFE to re-let: nothing parks a frame here any more.
;
; `LOC_RET` lived here and is DELETED
; (D-LOCPARK, 2026-08-21, docs/spec-basic-locarg.md §3.1.) It held LOCATE's
; parked return address so that `loc_next` could run `eval` / `raise_error` at
; the STATEMENT HANDLER's own stack depth. The reason it existed was true when it
; was written: the abort chain printed and then RETURNED, and it was built to
; return into the run loop, so an abort one frame deeper landed back in the
; middle of LOCATE and errored a SECOND time -- measured as
; `missing operand/missing operand` and `type mismatch/missing operand`.
; `4d35b6d` (D-CUR-D) made the abort DEPTH-INDEPENDENT -- both arms of
; raise_error_hl reset SP from SAVSTK -- so the park was buying a property that
; is now free, at 11 bytes of page 1. Deleted; loc_next is an ordinary
; `call`/`ret`. The two bytes were left NAMED rather than silently reused, so
; that the next cell wanting them would know what had been here -- and that is
; exactly how they were re-let above, one day later.
FN_RESUME       equ     $E227   ; D-FNEXPR: text cursor just past a filename
                                ; EXPRESSION, parked by fname_expr while the
                                ; staged name is parsed out of STRSCR (2 B)
; LOCATE parses all three arguments and applies them only when all three are
; valid -- measured (basic/missing.asm ex_locate). Both cells are SEEDED from the
; live cursor, so an omitted axis is re-applied unchanged and needs no
; present-flag of its own.
LOC_COL         equ     $E229   ; 1 B: LOCATE's parsed column, pre-clamp
LOC_ROW         equ     $E22A   ; 1 B: LOCATE's parsed row, pre-clamp
; --- SWAP_RESIDENT: the SWAP build gate -------------------------------------
; 1 = SWAP is BUILT (2026-07-28). The flag is kept rather than removed because it
; is the seam the MISSING class was split on, and because it still guards three
; places that must move together: this file's SW_* cells, the `kwtable.inc` crunch
; row, and the code in `basic/missing.asm`.
;
; ⚠️ RE-MEASURED FROM CLEAN, and the split's own number was 3 B off: SWAP costs
; **183 B** of page 1, not the 186 B recorded when it was gated off (measured by
; building with the flag on and reading __MEAS_PAGE1_END past the $8000 ceiling --
; 27 B over against the 156 B then free). The spec estimated 90-130 B, i.e. it was
; ~53 B light, for the reasons spec-basic-missing-class.md §10 records.
;
; FUNDED BY TWO CLONE COLLAPSES, both repack-only, neither touching SWAP:
;   * fat_rand_open/put/get onto the shared `fatprim_bounce`  +45 B  (1b8d5e7)
;   * the five TOTAL math calls onto one table               +41 B  (5f35a1e)
; 156 -> 242 B free, so SWAP lands with 59 B still banked. This deliberately did
; NOT spend the ~28 B fat_rand_* estimate as "the last reserve": collapsing that
; group onto a body the FAT carve had already built yielded 45 B, not 28.
SWAP_RESIDENT   equ     1

; --- SWAP (basic/missing.asm ex_swap) ---------------------------------------
; SWAP is the one statement in the language that writes TWO lvalues, so it must
; hold the FIRST operand's resolved address and type across the parse of the
; second -- and that parse runs a nested eval() for any subscript list. Nothing
; in a register survives that, so both live here.
SW_ADDR         equ     $E22B   ; 2 B: the operand just resolved
SW_TYPE         equ     $E22D   ; 1 B: its type (1 = string, 2/4/8 numeric)
SW_ADDR1        equ     $E22E   ; 2 B: operand 1, held across operand 2's parse
SW_TYPE1        equ     $E230   ; 1 B: operand 1's type
SW_MODE         equ     $E231   ; 1 B: 0 = this operand MAY be created, 1 = must exist
; --- D-CLP: the CLEAR string-pool partition RAM (docs/spec-basic-clearpool.md)
; zerobas used to have ONE free gap between the variable area (up to ARYEND) and
; the string heap (down from the ceiling C); the reference has TWO POOLS split by
; a boundary CLEAR moves. Measured: CLEAR 200 -> FRE(0)=28815 and CLEAR 4000 ->
; 25015, a difference of EXACTLY 3800, so the pool is carved from the same RAM --
; a moving boundary, not a second allocator (characterization §2.1).
POOLSIZE        equ     $E232   ; 2 B: the size CLEAR recorded. Written ONLY by
                                ; `CLEAR <n>`; initialised to 200 at cold boot and
                                ; deliberately NOT reset by NEW / RUN / bare CLEAR /
                                ; `CLEAR ,himem` -- all four keep the current size
                                ; (measured, characterization §2.4).
; ⚠️ There is deliberately NO POOLBASE cell. S-CLP-2 originally stored the
; derived boundary here; it is computed sub-side instead (see heap_reset's
; comment in basic/str-engine.asm) because the low region is the scarce ROM and
; the sub-ROM is not. $E234 stays free.
; --- D-EVLNO: the line-number scanner's tenant result pair --------------------
; parse_lineno (basic/program.asm) is a sub-ROM PAGE-1 tenant from D-EVLNO on
; (docs/spec-rom-region-evict-lineno.md). Its two results cannot ride back in
; registers -- subrom_call passes HL/DE IN, but CALSLT owns everything on the way
; out, which is why fatprim_bounce reloads DISKOP_HL/DISKOP_A rather than trusting
; them. So the tenant writes them here and the resident stub reads them straight
; back. Own choice, in the free window this comment block used to describe.
PLN_NUM         equ     $E234   ; 2 B: the parsed line number (BC), $FFFF if the
                                ; BC*10+digit chain carried (pl_sat's saturation --
                                ; dl_store's ceiling check rejects it)
PLN_PTR         equ     $E236   ; 2 B: LINEBUF pointer at the body (HL)
; ($E238..$E23F still free; STRTAB/VAREND begin at $E240.)
; Direct-mode control flow (docs/spec-basic-direct-ctrl.md §3) claims NO new RAM:
; the virtual line header a typed line executes under (`dir_line`, program.asm) is
; a 4-byte ROM constant, and CURLINE == dir_line is the sole definition of direct
; mode from that slice on. Recorded here because CURLINE is a sysvar and this is
; the one value it takes that is NOT an address in the program text.

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
;
; Arrays slice-4c (docs/spec-basic-arrays-slice4c-string-scalar-unification.md
; §5): on the repack path this fixed pool is RETIRED — string scalars now live
; in the unified scalar chain [PRGEND+2, ARYTAB) alongside numeric scalars
; (basic/vars.asm str_get_key/str_set_key -> ARY_OP 4/5 glue over sub/
; arrays.asm scv_find/scv_alloc). STRTAB/STRENTSZ/STRSLOTS/STREND belonged to the
; retired lean cart's fixed pool and are gone; the $E240..$E268 window they
; occupied is freed RAM. STRMAX stays a repack-wide knob (consulted by string-heap body
; allocation, unrelated to where scalar descriptors live) in both branches.
STRMAX          equ     255     ; repack build: string heap (slice-4a §8)

; Expression value-type signalling (own-design VALTYP notion). After eval_any /
; a factor, VALTYP says whether the result is a number (0; value in DE as usual)
; or a string (1; STRPTR points at a [len:1][bytes...] descriptor). Kept minimal:
; only LET and PRINT consult it; arithmetic stays numeric-only.
; ❌ RE-HOMING DECISION: **REJECT-UNOBSERVABLE** — stays at $E0C8, published
; address $F663 (docs/sysvar-rehoming-decisions.md §3).
;   SEMANTICS  MEASURED: both references hold a CONSTANT $03 at $F663 in all
;              NINE swept states. VALTYP is a TRANSIENT — its value at any
;              instant a PEEK could run is an artifact of the line editor, not
;              of the stimulus. There is nothing there to be right about.
;   OBSERVER   exactly one, and its decision ALREADY EXISTS, measured: the USR
;              calling convention (basic/usr.asm, oracle-locked by
;              probes/basic/basic_probe_usr.py). The reference passes the arg in
;              DAC+2..3 and sets VALTYP=$02; zerobas is integer-only, passes it
;              in HL, and leaves DAC/VALTYP untouched — a deliberate own-design
;              divergence. 🔴 THE ITEM WAS FILED AS "nobody decided that"; for
;              this one variable somebody did, just not HERE. That is the whole
;              reason this comment exists.
;   ⚠️ Honouring the ADDRESS without the 2/3/4/8 float type ENCODING would
;      publish a value no reference holds — worse than the dead byte today.
;   ⚠️ Its cold-boot value here is $FF, which is NEITHER of the two documented
;      values below. MEASURED 2026-08-21 (D-VALTYP, docs/valtyp-coldram-notes.md):
;      that $FF is POWER-ON RAM, not a write -- nothing in the tree writes a third
;      value, and every never-written cell in this private $E0xx block reads $FF
;      on a cold machine. Benign (written before read at every eval), and the
;      3-byte cold-boot init is PRICED AND DECLINED against a 2 B page-1 wall
;      (2026-08-21). Filed in TODO.md; reopen it for a new caller that READS
;      BEFORE WRITING, not for a spare byte.
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
; --- repack build: string HEAP RAM (arrays slice-4a, spec-basic-arrays- -----
; slice4a-string-heap.md). Shrinking STRTAB to 5-B descriptors (from 8*67=536 B
; to 8*5=40 B) frees ~500 B of the STRTAB..$E560 window; this layout spends that
; on the heap boundary, the temp-descriptor stack (replaces the old STRTMP N=3
; ring — the STRCAT_R re-entrancy bug that lived in that ring is GONE, §7), the
; string-heap sub-ROM tenant's param block, and INSTR's body-base scratch —
; still well inside the 800 B window, with margin to spare (§12 of the spec):
;   STRTAB    $E240 .. $E268     40 B            [name0][name1][len][ptr] * 8
;   FRETOP    $E268 .. $E26A      2 B            string-heap low boundary (§2)
;   RVDESC    $E26A .. $E26D      3 B            non-heap rvalue scratch descriptor
;                                                 (literal-lift/MKI$/INPUT$/STRSCR
;                                                 wrap — never a GC root, §5.2)
;   STRSCR    $E26D .. $E36D    256 B            [len][bytes:255] staging buffer
;                                                 for a value of unknown-until-
;                                                 read length (read_into_strscr/
;                                                 INPUT$)
;   SH_*      $E36D .. $E37F     18 B            string-heap tenant param block
;                                                 (SH_OP..SH_ERR; grew from the
;                                                 original 5 B as slice-4a added
;                                                 SLICE/HEX/FILL/MID/INSTR cells)
;   TEMPTOP   $E37F .. $E381      2 B            temp-descriptor stack cursor
;   (pool)    $E381 .. $E3E1     96 B            TEMPD=32 * 3 B temp-stack slots
;   ISRCH_*   $E3E1 .. $E3E5      4 B            INSTR resolved-body-base scratch
;   STRENG_SPARE $E3E5 .. $E3E6   1 B            FREE (was the D-2 flag, D-PENDERR)
;   MIDS_DEST $E3E6 .. $E3E8      2 B            MID$-statement stashed dest desc
; ⚠️ 🔴 THIS BLOCK TOPS OUT AT $E3E8, AND THE "376 B SPARE" THAT USED TO BE
;   WRITTEN HERE IS FALSE. The line read *"-> top $E3E8, well below the disk
;   WBUF wall at $E560 (376 B spare)"* and it has been false since G5 homed
;   GFX_PSTK/GFX_DBUF at **$E3F2** (256 B) with the rest of the GFX_D* and
;   GFX_S* cells running up past $E4F9 -- see the G5 PAINT and DRAW blocks
;   below, which are the current tenants of that window. What is actually free
;   between this block and the next one is **$E3E8..$E3F2, i.e. 10 bytes**.
;   Found 2026-08-22 by D-DEFFN, which sized a 100-byte FN parameter area
;   against the old figure; the assembler caught the page crossing and the
;   window then turned out to be occupied as well
;   (docs/deffn-design-2026-08-22.md §7). The conclusion is INVERTED rather
;   than the note deleted, because the next slice to want a RAM block will
;   arrive here with the same question: **do not size anything from this
;   comment -- read the EQU chain, and check the G5 blocks below.**
; NOTE: these addresses are the ACTUAL assembled values (verify in build/
; basic-reloc.sym). An earlier copy of this table still said SH_*=5 B /
; TEMPTOP=$E372 and caused BUG A (MIDS_DEST hardcoded at $E3D9, inside the
; temp pool). Keep it in sync with the EQU chain below.
; Arrays slice-4c (spec §5): FRETOP is now its OWN literal cell — the STRTAB
; pool it used to derive from (via STREND) no longer exists on the repack
; path (dissolved into the unified scalar chain). Value UNCHANGED ($E268,
; the old STRTAB+40 B) so every other repack-side address below (RVDESC,
; STRSCR, SH_*, TEMPTOP, the temp pool, ISRCH_*, STRENG_SPARE, MIDS_DEST) stays
; at its EXACT pre-4c address — no reshuffle, no reflow.
; ❌ RE-HOMING DECISION: **REJECT-GROUP** — stays at $E268, published address
; $F69B (docs/sysvar-rehoming-decisions.md §3). ⚠️ NOT rejected on semantics:
;   SEMANTICS  SAME-DELTA, exact. Both references AND zerobas move it by -4 for
;              a 4-byte string and -20 for a 20-byte one (sysvarsweep s8/s9), so
;              the published FRETOP is an ALLOCATION POINTER and so is this one.
;              The shared name turned out to be the shared variable — measured,
;              not assumed.
;   WHY REJECT 🔴 The measurement itself shows the ABSOLUTE value carries no
;              portable meaning: the two references disagree ($F168 vs $DC5F)
;              because their string spaces begin in different places. Only the
;              difference against MEMSIZ $F672 / STKTOP $F674 means anything,
;              and zerobas defines NEITHER. Publishing one end of a subtraction
;              is the ARYTAB failure again.
;   ⚠️ This pair is also why the sweep grew a SAME-DELTA verdict: read as
;      absolute bytes it scored NO-ORACLE, i.e. "no reading", while all three
;      sides agreed perfectly on the movement. NO-ORACLE is a verdict about the
;      COMPARISON, not about the variable.
FRETOP          equ     $E268               ; heap low boundary; heap occupies
                                            ; [FRETOP,C), grows DOWN as strings alloc.
                                            ; Reset to the ceiling C at cold start/
                                            ; NEW/RUN/CLEAR (heap_reset, str-
                                            ; engine.asm) -- called from clear_vars
                                            ; AND (arrays slice-4c §3d/H3 fix) from
                                            ; vars_reset itself (basic/arrays.asm),
                                            ; so it also runs on a bare relink
                                            ; (store_line edit / CLOAD without a
                                            ; full clear_vars). Pre-4c this was
                                            ; deliberately NOT the case (a bare
                                            ; relink left string-SCALAR bodies
                                            ; valid, since their STRTAB descriptors
                                            ; survived the edit untouched); post-4c
                                            ; those descriptors are THEMSELVES wiped
                                            ; by the SAME vars_reset call (chain-
                                            ; resident scalars), so nothing valid
                                            ; can still reference the heap after it
                                            ; runs -- reclaiming it there too is
                                            ; correct, not just permitted.
RVDESC          equ     FRETOP + 2          ; $E26A: [len:1][ptr:2] scratch descriptor
                                            ; for a value whose body is NOT in the
                                            ; heap (a token-stream literal / STRSCR) —
                                            ; excluded from GC roots by construction
                                            ; (ptr never lands in [FRETOP,C)); reused
                                            ; by str_eval_lit/str_mki/str_inputd/the
                                            ; INPUT#/LINE INPUT#/MERGE STRSCR-store
                                            ; sites. Safe as a SINGLE shared cell only
                                            ; because each producer's content is
                                            ; consumed (copied out, e.g. into a heap
                                            ; temp or a var's heap body) before the
                                            ; next string sub-expression can reuse it
                                            ; — the same "single shared scratch, safe
                                            ; by immediate consumption" property the
                                            ; pre-4a STRSCR already relied on.
STRSCR          equ     RVDESC + 3          ; $E26D: [len][bytes:STRMAX] staging
                                            ; buffer — UNCHANGED role from pre-4a,
                                            ; just widened 65->256 B (1+STRMAX).
                                            ; NOT a heap root (fixed RAM, outside
                                            ; [FRETOP,C)) — same as a literal.
; String-heap sub-ROM tenant (SUBROM_IDX_STRHEAP, sub/equates.inc) param block —
; mirrors the ARY_* block's marshalling convention (basic/sysvars.inc §10.2).
; ops: 0=ALLOC, 1=GC, 2=BUILD_CONCAT, 3=TEMP_ALLOC, 4=SNAPSHOT (the last two
; are the shape-C follow-up move of the temp-descriptor-stack allocators
; themselves into the tenant — basic/str-engine.asm ran out of low-region
; room for them; see str_temp_alloc/str_snapshot_to_temp's own headers).
SH_OP           equ     STRSCR + 1 + STRMAX ; $E36D (1 B)
SH_LEN          equ     SH_OP + 1           ; ALLOC/TEMP_ALLOC/BUILD_CONCAT arg:
                                            ; requested length / operand count (1 B)
SH_SRC          equ     SH_LEN + 1          ; SNAPSHOT arg: source descriptor
                                            ; address (2 B)
SH_PTR          equ     SH_SRC + 2          ; result: ALLOC's body ptr / GC's new
                                            ; FRETOP / BUILD_CONCAT's & TEMP_ALLOC's
                                            ; & SNAPSHOT's new temp-stack slot (2 B)
SH_PTR2         equ     SH_PTR + 2          ; result: TEMP_ALLOC's body-to-fill
                                            ; address (0 if length 0 or OOM) (2 B)
SH_START        equ     SH_PTR2 + 2         ; SLICE (op=5) arg: 0-based start (1 B)
SH_COUNT        equ     SH_START + 1        ; SLICE (op=5) arg: byte count (1 B)
SH_NUM          equ     SH_COUNT + 1        ; HEX_BUILD/OCT_BUILD (op=6/7) arg: the
                                            ; unsigned-16 value to render (2 B)
SH_FILLBYTE     equ     SH_NUM + 2          ; FILL (op=8) arg: the byte to repeat
                                            ; SH_LEN times (1 B) — covers SPACE$/
                                            ; STRING$/CHR$'s shared "n copies of
                                            ; one byte" shape
SH_DEST         equ     SH_FILLBYTE + 1     ; MID_STORE (op=9) arg: the MID$-
                                            ; statement destination (A$)
                                            ; descriptor address (2 B) — SH_SRC
                                            ; doubles as the source (B$) descriptor,
                                            ; SH_START as the 1-based position,
                                            ; SH_COUNT as the pre-Lb-clamped cap.
                                            ; CMP (op=10) reuses SH_SRC/SH_DEST as
                                            ; the lhs/rhs descriptors. INSTR_SEARCH
                                            ; (op=11) reuses SH_SRC/SH_DEST as the
                                            ; a$/b$ descriptors, SH_P as the
                                            ; 1-based start position.
SH_P            equ     SH_DEST + 2         ; INSTR_SEARCH (op=11) arg: p (2 B)
SH_ERR          equ     SH_P + 2            ; result: 0 ok, 1 Out of memory, 2 =
                                            ; temp-descriptor stack full (1 B)
; Temp-descriptor stack (§6): replaces the old STRTMP N=3 ring. A downward-
; growing array of [len:1][ptr:2] entries; TEMPTOP is the live cursor (reset to
; TEMPBASE — the empty-stack value — at every statement boundary, exec_stmt,
; and by clear_vars at cold start). TEMPD is chosen generously within the freed
; window (spec §17 Q-1: "implementation maximizes within the freed window,
; >= 8") — 32 is 4x the reference's ~8 and costs only 96 B, leaving ~290 B of
; further headroom in the historical 800 B window for future growth.
TEMPTOP         equ     SH_ERR + 1          ; $E37F: current cursor (2 B)
TEMPD           equ     32                  ; temp-descriptor stack depth
TEMPPOOL        equ     TEMPTOP + 2         ; $E381: low (deepest-push) address
TEMPBASE        equ     TEMPPOOL + TEMPD*3  ; $E3E1: high boundary = the empty-
                                            ; stack value for TEMPTOP
; INSTR (ev_f_instr/instr_search, str-engine.asm) resolves both operand
; descriptors' heap-body BASE addresses once up front (their [len][ptr]
; descriptors, aT/bT, are no longer inline-bodied, so IX/IY can't index bytes
; directly off them any more) — two scratch cells hold those bases across the
; search loop.
ISRCH_A         equ     TEMPBASE            ; $E3E1: resolved A-operand body base (2 B)
ISRCH_B         equ     ISRCH_A + 2         ; $E3E3: resolved B-operand body base (2 B)
; TMISMATCH ($E3E5, 1 B) STOOD HERE -- the string-comparison D-2 marker
; (spec-basic-string-compare.md §3c), a boolean read by fourteen sites ahead of
; FPERR. D-PENDERR (docs/spec-basic-penderr.md) retired it: it was only ever a
; shorthand for the one FPERR value FPERR_TYPEMM (=10, -> ERR 13), and the
; interpreter now carries a SINGLE pending-error code cell written set-if-empty.
; ⚠️ THE BYTE IS LEFT UNCLAIMED ON PURPOSE, NOT RECLAIMED. MIDS_DEST is anchored
; symbolically one byte above it, so deleting the equ would silently relocate a
; LIVE cell belonging to a different subsystem (the MID$()= statement) — a real
; regression surface bought for nothing, since RAM is not a wall this project is
; anywhere near and both ROM walls are. Spend it when something needs a byte.
STRENG_SPARE    equ     ISRCH_B + 2         ; $E3E5: 1 B free (was TMISMATCH)
; MIDS_DEST ($E3E6, 2 B, STRENG_SPARE+1, defined above) sits right above here — the
; last claimed cell in the freed STRTAB window; up to $E560 (disk WBUF) is spare.
    IF MIDS_DEST + 2 > $E560
                db      STRING_HEAP_LAYOUT_OVERRAN_E560_DISK_WBUF_WALL
    ENDIF

; --- G5 PAINT (docs/spec-basic-graphics-g5.md §4/D3): the scanline span-fill
; stack home. The fill needs a FIXED-CAPACITY span stack (D3, sign-off'd) that
; the LINEBUF region (G3/G4's own window) is far too small for (only 9 free B
; there after GFX_B, see above) -- this needs hundreds of bytes.
;
; ALIASING-SAFETY ARGUMENT (must NOT alias live interpreter/PLAY state, the
; recurring bug class flagged by the spec):
;   * NOT touched by the PLAY ISR (H.TIMI drains QUETAB/VOIC*Q/VCB* at
;     $F959+, MSX-JIFFY at $FC9E) -- this window is entirely below that, so a
;     PAINT running EI (music-plays-during-draw, spec §2) never races it.
;   * NOT live interpreter state that must survive PAST this one PAINT
;     statement's execution: MIDS_DEST above (STRENG_SPARE+1, ends $E3E8) is the
;     LAST cell the repack string engine currently claims out of its own
;     originally-reserved $E240..$E560 (800 B) window -- TEMPTOP's own header
;     already documents "~290 B of further headroom in the historical 800 B
;     window for future growth" as unclaimed. $E3E8..$E560 (376 B) is that
;     unclaimed span TODAY (grepped: no other basic-core/sub/tape equ falls in
;     it). Spending PART of it on PAINT's stack is a real, if quantifiable,
;     claim against that future headroom -- documented here as the tradeoff
;     (there was no OTHER aliasing-safe window big enough; see the G5 slice
;     report). It is empty at the START of any statement (the string engine's
;     own scratch there, e.g. TEMPPOOL, is reset at every statement boundary,
;     per TEMPTOP's own header) and PAINT's own C/B/coordinate evals (which
;     DO touch the string engine, e.g. via str_eval_one's tile$ probe) all run
;     in ex_paint BEFORE the tenant's subrom_call -- so by the time the
;     tenant writes here, no in-flight string-engine state can still need it.
;   * NOT the disk component's own RAM: disk/equates.inc places its FAT12/BDOS
;     scratch (FAT_SECPERCLUS.. BDOS_DTA etc.) at $E4A0-$E55B, DIRECTLY
;     overlapping this same window -- but that is the STANDALONE MSX1 disk-ROM
;     (slot 3-1, docs/spec-msx1-disk-rom.md), which only ever runs while
;     booting/driving MSX-DOS, never while the BASIC interpreter (and so never
;     a PAINT statement) is live. This is the SAME "mutually-exclusive
;     execution context" aliasing precedent basic-core RAM already uses
;     against that same disk-ROM component (basic-core's own STRTAB/SH_*/
;     TEMPPOOL/etc. above already overlap disk's SECTOR_BUF $E2A0-$E49F for
;     the identical reason), not a new risk class.
;   * NOT zerobas-disk's OWN (different) FAT scratch used by BASIC's disk
;     statements (basic/sysvars.inc's own FAT_* cluster) -- that lives at
;     $E9C0+, nowhere near here.
;
; Layout: GFX_PTOP/GFX_POVF (the stack cursor + overflow flag) and the flood
; loop's own small working cells, then the span-stack array itself -- entries
; are [y:1][xL:1][xR:1] (3 B; NO stored parent-direction byte, unlike the
; spec's own ~5 B/entry estimate: gfx_paint_inside's border test also stops at
; "already == C", not just "== B" -- see sub/graphics.asm gfx_paint_op header
; -- which makes re-scanning an already-filled span a safe, cheap no-op and
; removes the need for Smith's direction/overhang bookkeeping entirely). This
; buys MORE capacity per byte than the spec's own estimate assumed.
GFX_PTOP        equ     $E3E8   ; span-stack top-of-stack index, 0..GFX_PSTK_CAP (1)
GFX_POVF        equ     $E3E9   ; 1 = the stack overflowed; resident raises ERR 7 (1)
GFX_PTESTX      equ     $E3EA   ; gfx_paint_inside/gfx_paint_plot: pixel-under-test X (1)
GFX_PTESTY      equ     $E3EB   ; ...Y (1)
GFX_PFY         equ     $E3EC   ; gfx_paint_flood/_process: current span's row (1)
GFX_PXL         equ     $E3ED   ; ...current span's left column (1)
GFX_PXR         equ     $E3EE   ; ...current span's right column (1)
GFX_PSCX        equ     $E3EF   ; gfx_paint_process/_scan_row: scan cursor column (1)
GFX_PSCY        equ     $E3F0   ; gfx_paint_scan_row: the neighbour row being scanned (1)
GFX_PSPA        equ     $E3F1   ; gfx_paint_scan_row: pending sub-span's start column (1)
GFX_PSTK        equ     $E3F2   ; span-stack array base: GFX_PSTK_CAP * [y][xL][xR]
GFX_PSTK_ENTSZ  equ     3
GFX_PSTK_CAP    equ     120     ; capacity (360 B); window is 376 B ($E3E8..$E560)
                                ; minus 10 B of the working cells above -> 366 B
                                ; available for the array, 6 B headroom kept spare.
                                ; Comfortably above every realistic-fill span count
                                ; measured (scratchpad/g5_paint_notes.md D3: even a
                                ; 73-parallel-channel comb pattern completed at
                                ; normal HIMEM); short of the spec's own aspirational
                                ; "target >=128" (which assumed a fatter ~5 B/entry
                                ; that would not have fit this window AT ALL: 128*5
                                ; =640 B > 376 B available) but achievable ONLY
                                ; because of the 3 B/entry redesign above.
GFX_PSTK_END    equ     GFX_PSTK + GFX_PSTK_CAP*GFX_PSTK_ENTSZ
    IF GFX_PSTK_END > $E560
                db      PAINT_SPAN_STACK_OVERRAN_E560_DISK_WBUF_WALL
    ENDIF

; --- G6 DRAW (docs/spec-basic-graphics-g6.md §7, D-G6-1b) -----------------
; DRAW's frame buffer + parse state ALIAS the PAINT span stack above: both are
; graphics statements and only one graphics tenant is ever in flight, the same
; one-tenant-at-a-time aliasing the disk/line-editor status cells already use.
; The window's whole aliasing-safety argument (see GFX_PSTK's header) is
; inherited unchanged.
;
; THE CO-ROUTINE SPLIT (D-G6-1b). The tenant parses; when it meets `=expr;` or
; `X expr$;` it cannot resolve it itself (a page-0 tenant has the float pack
; switched out, so the int coercion behind `=var;` is unreachable), so it copies
; the text to GFX_DEXP, sets GFX_DREQ, REWINDS to the command start and returns.
; The resident resolves that one substitution into GFX_DVAL/GFX_DVLEN and re-enters
; with GFX_DRESUME=1; the tenant banks the value in the next GFX_DSUB slot and
; re-parses the same command, now finding the value ready. Re-parsing is free of
; side effects (nothing is drawn before a command's arguments are complete).
;
; Strings are COPIED into GFX_DBUF frame by frame, because the resident's eval
; between round trips can reuse the temp-string pool a DRAW argument may live in
; -- reading the body in place across an eval would be a use-after-free.
; D-CIRCOVF: CIRCLE's arc cross-product magnitudes are 32-bit once the minor
; scale is computed exactly (sub/graphics.asm gfx_cross_ge0 / gfx_mul16u32), and
; the G3/G4/G5 window above has only 6 B left ($E15A-$E15F) against the 8 these
; need. They ALIAS the same span-stack window on the same argument DRAW's frame
; buffer already uses below: one graphics tenant is ever in flight, and PAINT's
; stack and DRAW's buffer are both dead for the whole of a CIRCLE. ⚠️ These are
; live only INSIDE gfx_cross_ge0, which runs in the octant loop -- long after
; CIRCLE's parse co-routine is done. That co-routine borrows GFX_DPTR ($E4F2),
; 256 B clear of these 8, and basic/graphics.asm reads GFX_DPTR again AFTER the
; draw to continue the statement stream, so the two must not and do not overlap.
GFX_CS_M1       equ     GFX_PSTK        ; $E3F2: D-ARCMASK: 2*M*M during the M
                                        ; floor-correction (was cross_ge0's mag1) (4)
GFX_CS_M2       equ     GFX_CS_M1 + 4   ; $E3F6: r*r for the same compare, CONTIGUOUS with
                                        ; M1 -- gcx_zlp tests both as one 8-byte run (4)
GFX_DBUF        equ     GFX_PSTK        ; $E3F2: frame text (concatenated), 256 B
GFX_DBUF_CAP    equ     256
GFX_DPTR        equ     GFX_DBUF + GFX_DBUF_CAP   ; $E4F2: parse cursor in the current frame (2)
GFX_DEND        equ     GFX_DPTR + 2    ; $E4F4: one past the current frame's last byte (2)
GFX_DFREE       equ     GFX_DEND + 2    ; $E4F6: next free byte in GFX_DBUF (2)
GFX_DFTOP       equ     GFX_DFREE + 2   ; $E4F8: X-frame stack depth (1)
GFX_DFCAP       equ     8               ; max X nesting (own-design cap, D-G6-4)
GFX_DFSTK       equ     GFX_DFTOP + 1   ; $E4F9: saved [ptr][end] per outer frame (4 B each)
GFX_DCMD        equ     GFX_DFSTK + 4*GFX_DFCAP   ; $E519: current command's start cursor,
                                        ; the rewind point for a substitution (2)
GFX_DSUBN       equ     GFX_DCMD + 2    ; $E51B: substitutions RESOLVED for this command (1)
GFX_DSUBI       equ     GFX_DSUBN + 1   ; $E51C: substitutions SEEN so far this re-parse (1)
GFX_DSUB        equ     GFX_DSUBI + 1   ; $E51D: the resolved values, 2 slots (M takes two) (4)
GFX_DSUBLEN     equ     GFX_DSUB + 4    ; $E521: slot 0's string length (X only) (1)
GFX_DREQ        equ     GFX_DSUBLEN + 1 ; $E522: tenant->resident: 0 = done, 1 = resolve an
                                        ; int, 2 = resolve a string (1)
GFX_DRESUME     equ     GFX_DREQ + 1    ; $E523: resident->tenant: 1 = resuming (1)
GFX_DVAL        equ     GFX_DRESUME + 1 ; $E524: the resolved int16, or a string body ptr (2)
GFX_DVLEN       equ     GFX_DVAL + 2    ; $E526: that string's length (1)
GFX_DEXP        equ     GFX_DVLEN + 1   ; $E527: NUL-terminated copy of the text between
                                        ; `=`/`X` and its `;`, so the resident's eval runs
                                        ; on a BOUNDED buffer and can never walk off the
                                        ; end of a string body into the heap (24 B)
GFX_DEXP_CAP    equ     24
GFX_DFB         equ     GFX_DEXP + GFX_DEXP_CAP   ; $E53F: 1 = B (blank move) prefix pending (1)
GFX_DFN         equ     GFX_DFB + 1     ; $E540: 1 = N (no-update) prefix pending (1)
GFX_DARG        equ     GFX_DFN + 1     ; $E541: last parsed argument (int16 LE) (2)
GFX_DDX         equ     GFX_DARG + 2    ; $E543: this command's dx (int16) (2)
GFX_DDY         equ     GFX_DDX + 2     ; $E545: ...dy (2)
GFX_DTX         equ     GFX_DDY + 2     ; $E547: move target X (2)
GFX_DTY         equ     GFX_DTX + 2     ; $E549: ...Y (2)
GFX_DTMP        equ     GFX_DTY + 2     ; $E54B: mul/rotate/sign scratch (2)
GFX_DSP         equ     GFX_DTMP + 2    ; $E54D: tenant entry SP -- an error deep in the
                                        ; parse restores it and exits, so every helper can
                                        ; just jump to the error tail instead of threading
                                        ; a CF through the whole call chain (2) -> ends $E54F
GFX_DESC        equ     $01             ; (unused by D-G6-1b; kept out of the buffer grammar)
; G7 sprites: the <=32 byte staging buffer for the tenant's VRAM block ops, and
; the 4-byte attribute entry the resident read-modify-writes through them. It
; ALIASES the PAINT span stack / DRAW frame buffer for exactly the reason those
; two alias each other: one graphics statement is in flight at a time, and a
; sprite statement neither paints nor draws. Sized 32 = the 16x16 pattern entry.
GFX_VBUF        equ     GFX_PSTK        ; $E3F2: sprite pattern/attribute staging (32 B)
; The sprite parameter block. The resident EVALUATES (that is what it is for --
; `eval`, the string heap and the token cursor are all page-1 resident) and the
; TENANT decides: entry size and address, the domain checks, the early-clock rule,
; the x4 pattern scaling and the merge with the bytes already in the entry. That
; split is what keeps the space-blocked resident half small (spec §7/§8).
GFX_SN          equ     GFX_VBUF + 32   ; $E412: SPRITE$ entry index / PUT SPRITE plane (2)
GFX_VLEN        equ     GFX_SN + 2      ; $E414: the entry size the tenant read back (1)
GFX_SDESC       equ     GFX_VLEN + 1    ; $E415: SPRITE$(n)= RHS string descriptor
                                        ; ([len][ptr]); the tenant dereferences it (2)
GFX_SC          equ     GFX_SDESC + 2   ; $E417: PUT SPRITE colour (2). x/y need no cells --
                                        ; they ride the arc's pinned GXPOS/GYPOS pair, which
                                        ; PUT SPRITE writes anyway (the work area keeps the
                                        ; raw, unwrapped coordinate)
GFX_SPATN       equ     GFX_SC + 2      ; $E419: ...pattern number (2)
GFX_SSIZE       equ     GFX_SPATN + 2   ; $E41B: SCREEN's sprite-size argument while a mode
                                        ; set is in flight (RG1SAV bits 1..0 hold it after) (1)
GFX_SARGN       equ     GFX_SSIZE + 1   ; $E41C: how many extra SCREEN arguments have been
                                        ; seen -- only the FIRST is the sprite size (1)
GFX_SFLAGS      equ     GFX_SARGN + 1   ; $E41D: which arguments were GIVEN --
                                        ; bit0 = coordinates, bit1 = colour, bit2 = pattern;
                                        ; an omitted one keeps the entry's own byte (1)
;
; The PERSISTENT pair (spec §4 -- the measured pin: S and A survive RUN, NEW,
; CLEAR, CLS, COLOR and SCREEN; ONLY a power-on resets them). They therefore may
; NOT live in the LINEBUF region G3/G4/G5 use for marshalling (the keyboard line
; editor overwrites that between statements) nor in the heavily-aliased $E0xx
; block -- they need a private home that nothing else touches, which is why they
; sit in the bytes this window deliberately kept spare above the span stack
; (GFX_PSTK_END = $E55A). Cold-boot init only (interp.asm `init`).
; --- DEFtype tenant ABI (SUBROM_IDX_DEFTYPE, docs/spec-eviction-g6-space.md) --
; The token cursor travels through RAM because CALSLT clobbers the registers.
; DEFT_PTR sits in this same repack-only graphics window, above DRAW's own cells:
; a DEFtype statement and a graphics statement can never be in flight at once
; (one statement runs at a time and neither leaves state behind) -- the same
; one-tenant-at-a-time aliasing LE_*/CM_* already use against DISKOP_*. Defined
; HERE rather than beside SUBROM_IDX_DEFTYPE because that block sits inside
; `IFNDEF SUBROM_ENTRY_BASE_P0`, which the sub-ROM build skips -- and the tenant
; needs these addresses.
DEFT_PTR        equ     GFX_DSP + 2     ; $E54F: token cursor in AND out (2)
DEFT_STATUS     equ     DISKOP_STATUS   ; tenant -> main: 0 ok / 1 = stmt_error
; --- READ/DATA tenant ABI (SUBROM_IDX_READVAL, docs/spec-eviction-g7-space.md) -
; read_one_value's (A, DE) contract cannot ride back through subrom_call, so the
; tenant lands it here and basic/program.asm's stub rebuilds it. Same window and
; the same one-statement-at-a-time aliasing argument as DEFT_PTR above (a READ and
; a graphics statement are never in flight together), and clear of the PERSISTENT
; GFX_DSCALE/GFX_DANGLE pair below.
RDV_VAL         equ     DEFT_PTR + 2    ; $E551: the value read (int16 LE) (2)
RDV_ST          equ     RDV_VAL + 2     ; $E553: tenant -> main STATUS (1):
                                        ;   0 = out of data      (ERR 4)
                                        ;   1 = an item was read (RDV_VAL / STRSCR)
                                        ;   2 = the item is not a NUMBER (ERR 2) --
                                        ;       D-READVAR's c.strnum, numeric mode only
RDV_MODE        equ     RDV_ST + 1      ; $E554: main -> tenant MODE (1), D-READVAR:
                                        ;   0 = numeric, data_parse_int -> RDV_VAL
                                        ;   1 = string, the item's RAW ASCII span ->
                                        ;       STRSCR ([len][bytes]); RDV_VAL undefined
                                        ; 🔴 A PAGE-0 TENANT CANNOT WRAP IT: strscr_desc
                                        ; ($2896) is in the main LOW region, switched out
                                        ; while the sub-ROM's page 0 is in. The tenant
                                        ; FILLS STRSCR; ex_read wraps + stores main-side,
                                        ; exactly as ex_input does (spec §4.1).
; --- D-ARYLV: the resolved lvalue TARGET of a READ / INPUT / LINE INPUT -------
; docs/spec-basic-arylv.md §4.3. tgt_parse (basic/vars.asm) writes it; the two
; tgt_store_* helpers read it to pick their destination:
;   0        -> a SCALAR: store through the key in BC (var_store_fac/str_set_key)
;   nonzero  -> an ARRAY ELEMENT at that address (ary_store_write / ARY_OP=3)
; A resolved element address is never 0, so the cell needs no separate flag byte.
; Same window and the same one-statement-at-a-time aliasing argument as the RDV_*
; cells above -- a READ/INPUT and a DRAW are never in flight together.
; ⚠️ REUSING ARY_ADDR FOR THIS WAS CONSIDERED AND REJECTED (spec §4.3): it would
; work today (nothing between the target parse and the store calls the array
; engine), but its failure mode is a SCALAR store writing to a stale element
; address -- silent memory corruption, not an error -- guarded only by a property
; nothing enforces. 2 B buys that away.
TGT_ADDR        equ     RDV_MODE + 1    ; $E555: element address, or 0 = scalar (2)
; D-DEFINTTOK (2026-08-18) / D-DEFTYPETOK (2026-08-19): all four DEFtype verbs
; reach ONE handler (basic/usr.asm `ex_deftype`) and ONE tenant (sub/deftype.asm
; `deftype_tenant`), and needing to know WHICH of the four cost NO extra
; memory-ABI cell here -- no new byte was spent in this window (a real
; constraint: main page 1 sits within a handful of bytes of the $8000 ceiling,
; docs/rom-region-structure-review.md). The tenant recovers the verb for free,
; by reading the byte already sitting one below the handed-over DEFT_PTR cursor:
; that byte IS the statement token, because `ex_deftype` does nothing but
; `inc hl` past it before handing the cursor over. DEFSTR/DEFINT/DEFSNG/DEFDBL
; are $AB..$AE and CONTIGUOUS BY CONSTRUCTION (see the token equates and the
; do-not-reorder note that goes with them), so `sub DEFSTR_TOKEN` turns the
; peeked byte into a 0..3 index straight into the tenant's 4-byte type-code
; table -- no compare chain, and no range check either, because none is
; reachable: `deftype_tenant` has exactly ONE caller and interp.asm's dispatch
; table reaches it from exactly those four token rows, so the byte below the
; cursor cannot be anything else. (Before D-DEFTYPETOK this same peek served a
; narrower job -- telling TWO callers apart, `ex_defint` from the ASCII-mnemonic
; `ex_def_type` -- and rested on the argument that the latter's callers could
; only ever leave DEF_TOKEN or a space there. That routine and that path no
; longer exist; the peek now discriminates four tokens rather than two, and
; contiguity has replaced the false-positive argument.) A DEFT_PRESET-style
; preset flag byte was drafted and measured too expensive (it cost a `ld a,n`/
; `ld (nn),a` pair in the MAIN-ROM handler plus a cold-boot reset in `init`,
; ~9 B this window could not afford); the token-peek needs none of that, so it
; is what shipped.
;
GFX_DSCALE      equ     GFX_PSTK_END    ; $E55A: persistent scale, quarter units,
                                        ; 0 = NEVER SET (D-DSCALE): a distinct
                                        ; state from S4, in which no scaling runs
                                        ; at all. `gdo_s` maps S0 to 4, so no
                                        ; explicit S can write the sentinel. (1)
GFX_DANGLE      equ     GFX_DSCALE + 1  ; $E55B: persistent angle 0..3 (1). Boot 0
                                        ; and an explicit `A0` are the SAME state
                                        ; (measured, d.a0.32k): no sentinel here.
; G8 marshalling (docs/spec-basic-graphics-g8.md §5): the index and the value of a
; `VDP(n)=v` / `BASE(n)=v` write, handed to the tenant, which owns the domain checks
; and the register programming. Dead outside such a statement -- the last 4 B before
; the $E560 disk-WBUF wall, which the guard below still enforces.
GFX_G8N         equ     GFX_DANGLE + 1  ; $E55C: written index n (int16 LE) (2)
GFX_G8V         equ     GFX_G8N + 2     ; $E55E: written value (int16 LE) (2)
; --- D-PAINTMC: PAINT's COORDINATE PITCH, 1 (SCREEN 2) or 4 (MULTICOLOUR) -----
; sub/graphics.asm gfx_paint_op writes it once per statement; the flood's seven
; step sites read it. It ALIASES G8's index cell above, on the same
; one-statement-at-a-time argument DEFT_PTR / RDV_* / TGT_ADDR / GFX_DBUF /
; GFX_CS_M1 / GFX_VBUF all rest on in this window: a `VDP(n)=v` (or `BASE(n)=v`)
; and a PAINT are never in flight together, one statement runs at a time, and
; neither leaves state behind -- G8's own header above says these 4 B are "dead
; outside such a statement". Both writer and readers are the graphics tenant, so
; the lifetime is one CALSLT call, narrower than every other alias here.
; ⚠️ IT IS A CACHE, NOT A CHOICE OF STYLE, AND THE NUMBER IS WHY. The pitch was
; first read by CALLING a 4-instruction helper (`gfx_pstep`, which asked SCRMOD)
; at each of those seven sites. Measured on tests/test_graphics.py's full-screen
; case C, which is the largest fill this project runs: 3,205,330 Z80 steps before
; the slice, 4,339,041 with the helper -- +35% on EVERY SCREEN-2 PAINT, paid so
; that SCREEN 3 works, and enough to blow that test's 4,000,000-step runaway
; guard. One byte turns those seven calls into seven `ld hl,nn` and gives the
; cost back. A wall this window could not afford would have been the other
; answer; it is 0 B here because G8's cells were already dead.
GFX_PPITCH      equ     GFX_G8N         ; $E55C: 1 or 4, live only inside a PAINT
    IF GFX_DSP + 2 > GFX_PSTK_END
                db      DRAW_SCRATCH_OVERRAN_THE_PERSISTENT_STATE_CELLS
    ENDIF
    IF TGT_ADDR + 2 > GFX_DSCALE
                db      TGT_ADDR_OVERRAN_THE_PERSISTENT_DRAW_STATE_CELLS
    ENDIF
    IF GFX_G8V + 2 > $E560
                db      G8_MARSHALLING_OVERRAN_E560_DISK_WBUF_WALL
    ENDIF

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
; TXTMAX — the program-text ceiling (OUT OF MEMORY threshold). Lowered 2304 B
; below the $C000 BLOAD ceiling to reserve
; $B700-$BFFF for the three line buffers (map below): DETOKBUF (subrom wave 3,
; docs/spec-basic-subrom-wave3-detok.md §5/Q3-a) plus TOKBUF and LINEBUF, which
; D-LINEMAX re-homes out of page 3 because neither fits there at its true size.
;
; This 1792 B of the cut is D-LINEMAX's, and it is CHOSEN BY MEASUREMENT rather than
; preference (spec §4 Q3): the reference charges its own file-channel buffers 267 B
; each out of the very FRE(0) pool programs live in, so funding buffers from program
; space is the mechanism the REFERENCE uses — while the alternative (dropping
; MAXFILES to 1) moves AWAY from a reference that supports at least 15. Repack
; program capacity is 15871 -> 14079 B. It is per-build because
; TXTMAX is emitted as an immediate (`ld de,TXTMAX` in program.asm / cload.asm).
; --- The page-2 buffer window, $B700..$BFFF (D-LINEMAX §3) ------------------
;   TOKBUF   $B700..$B93F   576 B  (crunch destination; 314-byte logical body limit)
;   (spare)  $B940..$B9FF   192 B
;   LINEBUF  $BA00..$BAFE   255 B  (page-aligned — the readers' low-byte idiom)
;   (spare)  $BAFF            1 B
;   DETOKBUF $BB00..$BFFF  1280 B  (LIST/ASCII-SAVE render target)
;
; ⚠️ DETOKBUF'S SIZE IS A CONSEQUENCE OF LINEMAX, AND D-LINEMAX'S SPEC MISSED IT.
; The 512 B figure was DERIVED from the old ceiling — docs/spec-basic-subrom-wave3-
; detok.md §0.2: "every char a `?`->PRINT (5x per char) = 95x5 = 475" — and that
; spec's §5 sketch considered the 255-char case explicitly and dismissed it because
; "the source line is capped at 96 bytes, not 255". Raising LINEMAX REMOVES that
; premise, and sub/detok.asm's pchar says in as many words "No overflow check (the
; buffer is sized for the worst case)". So LIST of a line of 254 `?` would have
; written 254x5 = 1270 bytes into 512 — the SAME defect class as the TOKBUF overrun
; this slice exists to fix, newly CREATED by fixing it. 1280 = $BB00..$BFFF covers
; the 1271-byte ceiling (254x5 + terminator) and still tops out just under the $C000
; BLOAD region, so the "free during both sinks, below the stack" argument is intact.
; ⚠️ D-FCH §3.3: RAISED $B700 -> $BB00, giving back 1024 B of program space.
; D-LINEMAX had to drop this ceiling 1792 B ($BE00 -> $B700) to house three
; buffers; TOKBUF and LINEBUF have now moved to page 3 (into the window S-FCH-1
; freed by retiring the per-channel sector save copies), so only DETOKBUF is
; still charged to page 2 and the ceiling rises to meet it.
; ⚠️ The rise is BOUNDED BY DETOKBUF, not by the freed RAM: at 1280 B it does not
; fit in the 1024 B window, so $BB00 is the ceiling until it is dealt with.
; 🟢 D-RECLAIM (2026-09-01): THE CEILING RISES OVER $C000, +8192 B OF BASIC RAM.
; FRE(0) 14767 -> 22959, against the CF-3300's 23348 -- within 389 B of the
; reference, from 8581 B short. docs/spec-fre-gap.md is the measurement that
; found it; docs/spec-reclaim.md is this change.
; 🎯 WHAT WAS ACTUALLY RESERVING IT: nothing in BASIC mode. $C000..$E000 is
; MSX-DOS territory -- boot-sector load $C000, kernel work area $D606, BDOS
; dispatcher $D831, kernel FCB $DA40, DOS work area $DD0E..$DD8E -- and
; **BASIC and DOS never co-exist** (Joost, 2026-09-01). A DOS boot replaces
; BASIC wholesale; the boot sector loads at $C000 during INIT, before any
; program exists. The reference proves the model: the CF-3300 runs BASIC up to
; HIMEM $DE77 and expects a program that BLOADs high to CLEAR/HIMEM down first,
; which is what those verbs are for.
; ⚠️ THE OLD COMMENT NAMED THE SMALL LEVER AND NOT THE BIG ONE. "The rise is
; BOUNDED BY DETOKBUF" was true and worth ~768 B; the 8192 B $C000 reservation
; was priced NOWHERE and held two bytes ($C120, now rehomed above).
TXTMAX          equ     $DB00   ; repack: text ceiling. DETOKBUF sits immediately
                                ; above it, topping out exactly at the $E000
                                ; workspace floor.
DETOKBUF        equ     $DB00   ; repack: 1280 B one-shot detok output buffer,
                                ; $DB00..$DFFF. Size is a consequence of LINEMAX
                                ; (254 chars x 5 + terminator = 1271); see the
                                ; derivation above.
PRGEND          equ     $E026   ; addr of the $0000 end-of-program marker (2 bytes)

; --- Arrays slice-1, SPLIT design (repack build only, docs/spec-basic- ------
; arrays.md §10). The array area is the LOW free region: it begins right
; after the stored program's own $0000 terminator (PRGEND) and grows up
; toward the allocator ceiling (min(HIMEM,TXTMAX)). own-design descriptor
; (§9.2/§10.3): [name0][name1][type][ndim][stride:2][bound0:2]...[boundK:2]
; [element data...], packed back-to-back, TERMINATED by a 2-byte $0000
; sentinel. There is no separately-stored "ARYEND" pointer: the sentinel IS
; the "end of array area" marker (sub/arrays.asm ary_find/ary_alloc;
; ary_reset, basic/arrays.asm, rewrites it whenever the program area
; rebases, §9.6). ARYBASE itself WAS derived as (PRGEND)+2 through slice-4a;
; arrays slice-4b (docs/spec-basic-arrays-slice4b-scalar-reloc.md §2) inserts
; a numeric-SCALAR region between the program text and the array area, so
; ARYBASE is now the STORED live cell `ARYTAB` (above, in the freed VARTAB
; span) instead -- the scalar region itself is still derived as (PRGEND)+2,
; exactly the array area's old anchor.
;
; The engine (ary_find/ary_alloc/ary_resolve) is a SUB-ROM page-0 tenant
; (SUBROM_IDX_ARY, sub/equates.inc) -- §10's split fix for a ~284 B repack
; ROM overrun in the monolithic design. Main and the tenant marshal through
; this RAM param block instead of registers (subrom_call/CALSLT clobbers
; everything): main fills ARY_OP..ARY_IDXP, `subrom_call`s, then reads
; ARY_ADDR/ARY_ERR. This REPLACES the monolithic WIP's own ARY_NIDX/ARY_IDX-
; only scratch (basic/arrays.asm on branch arrays-slice1-wip) with the wider
; ~16-byte block below, at the SAME address range and under the SAME
; aliasing argument (kept verbatim, only the field boundaries changed):
; TKNAME/TKRADIX/TKRTOK (tokeniser scratch -- a line's whole tokenise pass
; always completes BEFORE any of its tokens execute, so this is dead for the
; entire duration of any statement's execution, including array references)
; + CLPTR/CLINK/RUNFLAG (CLOAD/BLOAD scratch -- CLOAD's filename is kept
; verbatim ASCII, never an expression, so it can never itself evaluate an
; array subscript while these are live; RUNFLAG is BLOAD's own ",R" parse
; flag, same argument) + SL_NUM/SL_SLOT/SL_SIZE/SL_TOK (store_line scratch --
; store_line only STORES a numbered line, it never EXECUTES one, so it can
; never itself be mid-array-reference). None of these three "owners" can be
; active at the same moment array-subscript parsing is (single-threaded
; interpreter, one statement executing at a time). $E028..$E037, 16 bytes --
; EXACTLY the span this aliasing argument already covers (CURLINE, live
; during almost all statement execution, sits immediately above at $E038, so
; there is no slack for anything more — see sub/arrays.asm's own header for
; where the split engine's ADDITIONAL transient bookkeeping went instead, a
; per-call hardware-stack frame, since no further RAM byte was available).
; D-ARR-C (docs/spec-basic-arrdim-c.md): `MAXDIM equ 4` STOOD HERE and is gone.
; It was a slice-1 subscript-count cap, recorded in docs/spec-basic-arrays.md
; §9.1 Q-9b with the disposition ">MAXDIM subscripts -> Subscript out of range"
; -- CHOSEN, WRITTEN DOWN AND NEVER MEASURED. The reference has no cap anywhere a
; program can reach it: ERR=0 at 4, 8, 16, 32, 64, 100 and 120 subscripts, the
; last on a 249-character line (docs/arrdim-c-vg8020-characterization.md §1), and
; it stores and reads an element back through 32 of them (§2). There was no
; number to raise the cap TO.
; The cap existed only to bound a copy into a fixed 8-byte ARY_IDX buffer that had
; nowhere to grow (CURLINE sits immediately above this span, see below).
; ary_parse_subs ALREADY collects every subscript on the hardware stack -- the
; 2026-07-15 re-entrancy fix, since X(X(0)) needs a per-nesting-level region --
; so the fix deletes the copy and hands the tenant a POINTER instead of a buffer.
; The block's ceiling is then the input line (43 subscripts, LINEMAX=96) against
; 1024 B of measured stack headroom, not a constant anyone had to pick.
ARY_OP          equ     $E028   ; 0=RESOLVE (read/write element, auto-dim on
                                ; read) / 1=DIM (explicit declare) / 2=ERASE
                                ; (free, slice-2, docs/spec-basic-arrays-
                                ; slice2-erase.md §4.2) / 3=COPY_STR (slice-3/
                                ; 4a) / 4=SCALAR_FIND / 5=SCALAR_ALLOC (arrays
                                ; slice-4b, docs/spec-basic-arrays-slice4b-
                                ; scalar-reloc.md §4: numeric scalar find /
                                ; find-or-insert-and-shift, folded into this
                                ; SAME tenant + param block per Q4 -- reuses
                                ; ARY_KEY/ARY_TYPE in, ARY_ADDR/ARY_ERR out,
                                ; identical shape to RESOLVE) (1)
ARY_KEY         equ     $E029   ; name0/name1 key (BC round-trip: written via
                                ; `ld (ARY_KEY),bc`, read via `ld bc,(ARY_KEY)`
                                ; on both sides -- byte order unobserved) (2)
ARY_TYPE        equ     $E02B   ; 2/4/8 (int/single/double) (1)
ARY_NIDX        equ     $E02C   ; parsed subscript/bound count for the CURRENT
                                ; reference (1)
ARY_IDXP        equ     $E02D   ; [D-ARR-C] POINTER to the parsed subscripts
                                ; (RESOLVE) or bounds (DIM) -- int16 LE, ndim of
                                ; them, living in the CALLER's own hardware-stack
                                ; block, not here (2). ⚠️ IT ADDRESSES SUBSCRIPT
                                ; **0**, THE HIGH END, and every tenant walk runs
                                ; DOWNWARD from it. That is not a quirk to tidy
                                ; away: ary_parse_subs pushes subscript 0 FIRST,
                                ; so subscript 0 lands at the highest address, and
                                ; addressing that end is exactly what lets all
                                ; four tenant walks keep visiting k = 0..ndim-1 in
                                ; the order they always did -- the element-offset
                                ; math in ary_resolve is untouched. Turning the
                                ; pointer round without turning the walks round is
                                ; SILENT MEMORY CORRUPTION (the resolve still
                                ; succeeds, on the wrong element), and it is
                                ; invisible on equal bounds; tests/test_arrays.py
                                ; case 2b is the asymmetric witness.
ARY_CUR         equ     $E02F   ; [D-ARR-C] the text cursor, parked across the
                                ; engine call (2). subrom_call/CALSLT clobbers HL,
                                ; and the fused ary_parse_call has no caller left
                                ; to hold a [CURSOR] push for it. Safe against the
                                ; same re-entrancy ARY_NIDX/the old ARY_IDX already
                                ; survived: written at the close paren AFTER every
                                ; eval has returned and consumed by the engine call
                                ; immediately after, so no nested parse can
                                ; interleave with it.
                                ; $E031..$E034 (4 B) FREED by the above -- the old
                                ; ARY_IDX was 8 bytes. Unassigned on purpose: this
                                ; span has CURLINE immediately above it at $E038.
ARY_ADDR        equ     $E035   ; [tenant return, RESOLVE] element address (2)
                                ; -- also SCALAR_FIND/SCALAR_ALLOC's own
                                ; return (§4b): the scalar entry address, or
                                ; 0 for SCALAR_FIND's "not found" (0 is never
                                ; a valid entry address -- program text
                                ; starts at $8001)
ARY_ERR         equ     $E037   ; [tenant return] 0 ok; 1 Subscript-oor;
                                ; 2 Illegal-fn (negative); 3 Redimensioned;
                                ; 4 Out of memory -- an ALLOCATION that will
                                ; not fit VARIABLE space (DIM, auto-dim, and
                                ; SCALAR_ALLOC's insert; SCALAR_FIND is always
                                ; 0, a miss is not an error); 5 Out of string
                                ; space -- COPY_STR's heap_alloc could not get
                                ; a BODY out of the `CLEAR n` pool (D-ARYOOS,
                                ; 2026-08-20). 4 and 5 were ONE code until
                                ; then, and the conflation cost the message:
                                ; ary_errmap maps 4 -> FPERR=6 -> ERR 7, where
                                ; both references answer ERR 14 for a store.

; --- Phase 1: CLEAR memory-top sysvar --------------------------------------
; HIMEM is the documented home of CLEAR's "highest address BASIC may use"
; argument (CLEAR [<strings>][,<himem>]). zerobas has no allocator that consults
; it yet (fixed RAM layout), so ex_clear stores it record-only; see clear.asm.
; Source: C-BIOS system variables (BSD 2-clause; address $FC4A), cross-checked
; against the MSX2 Technical Handbook work-area appendix / MSX Assembly Page.
HIMEM           equ     $FC4A   ; highest RAM address BASIC may use (2 bytes)
; --- D-HIMRANGE: CLEAR memory-ceiling range-check bounds --------------------
; The <memory-top> argument's accepted band, MEASURED on the VG-8020 AND the
; CF-3300 (both agree on every row; scratchpad/himdom_probe.py,
; docs/spec-basic-himdom.md §5/§6). value > CLR_HIMEM_TOP or < $8000 -> ERR 5;
; $8000 <= value < PRGEND+POOLSIZE+CLR_HIMEM_MARGIN -> ERR 7 (Out of memory);
; else accepted and HIMEM moves. Used by clr_himem (basic/clear.asm).
; ⚠️ CLR_HIMEM_TOP is a CONSTANT on BOTH machines despite their boot HIMEMs
; differing (62336 vs 56951): CLEAR reads a FIXED top, NOT live HIMEM -- you may
; raise the ceiling back up to $F380 after lowering it (probe row t.4to6). This
; REFUTES docs/spec-basic-himdom.md §5's guess that the edge was machine-
; specific, and is why the check needs no boot-time HIMEM init. $F380 is the
; documented top of BASIC-usable RAM (below the BIOS work area).
CLR_HIMEM_TOP    equ    $F380   ; 62336: highest address CLEAR accepts
; The reserve (interpreter stack + overhead) that must remain between the top of
; the program text and the string space below the new ceiling. DERIVED, not
; guessed: the measured floor for the 5-line n=200 probe program is in
; (33700,33750] and that program's PRGEND is 32843, so
; MARGIN = floor - PRGEND - POOLSIZE is in (657,707]; 680 sits at the centre.
; The floor tracks program TEXT (PRGEND) and string space (POOLSIZE) exactly as
; the reference does -- variables do NOT count (CLEAR wipes them; rows p.dim*).
CLR_HIMEM_MARGIN equ    680
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
; Error-handling S2a (docs/spec-basic-error-handling-s2a-packet.md §1): tokens
; black-box-pinned via probes/basic/basic_probe_pin_errtokens.py on the VG-8020
; (`ERROR` -> $A6 statement token; `a=err` -> ...EF E2, `a=erl` -> ...EF E1 --
; both single-byte value tokens, expr.asm).
ERROR_TOKEN     equ     $A6     ; ERROR n  (also ON ERROR GOTO)
ERR_TOKEN       equ     $E2     ; ERR function (last error's MSX code)
ERL_TOKEN       equ     $E1     ; ERL function (last error's line, 65535=direct)
TIME_TOKEN      equ     $CB     ; TIME — the software-clock pseudo-variable, a SINGLE-byte
                                ; reserved word that is BOTH a factor and an lvalue
                                ; (docs/spec-basic-time.md §1.1, oracle-pinned on the
                                ; VG-8020). $CB sits between CALL ($CA) and KEY ($CC),
                                ; consistent with the rest of the pinned table, and was
                                ; unused in zerobas. TIME shares no prefix with another
                                ; entry, so its kwtable position is free.
; --- the MISSING class (docs/spec-basic-missing-class.md §3.1) ---------------
; All five tokens PINNED from the reference's own crunch, read back through
; ("stored_line", TXTTAB) -- the VG-8020 tokeniser's output, never ROM code.
; `10 LOCATE 5,3` -> d8 20 16 2c 14 00 ; `10 SWAP A,B` -> a4 20 41 2c 42 00 ;
; `10 TRON` -> a2 00 ; `10 TROFF` -> a3 00 ; `10 MOTOR` -> ce 00. All five are
; SINGLE-byte statement tokens. MOTOR ON/OFF crunch to the existing ON_TOKEN
; ($95) / OFF_TOKEN ($EB), so they need no token of their own.
;
; ⚠️ $A2/$A3/$A4 ARE ALREADY SPOKEN FOR -- as STICK/STRIG/PDL, which are
; $FF-PREFIXED *FUNCTION* tokens (see above). Same byte value, different
; namespace; this is exactly the existing ASC_TOKEN $95 / ON_TOKEN $95
; situation. The tokeniser is safe by construction (match_kw is full-keyword),
; but the DETOKENISER has to keep the two apart in both directions, which is why
; the slice carries LIST round-trip cases like `10 TRON:A=STICK(0)`.
; $CE was free between MAX ($CD) and BLOAD ($CF); $D8 between KILL ($D4) and
; TO ($D9). Neither shares a prefix with another kwtable entry.
LOCATE_TOKEN    equ     $D8     ; LOCATE [col][,[row][,cursor]]
SWAP_TOKEN      equ     $A4     ; SWAP a,b   (== PDL_TOKEN's byte, other namespace)
TRON_TOKEN      equ     $A2     ; TRON       (== STICK_TOKEN's byte, other namespace)
TROFF_TOKEN     equ     $A3     ; TROFF      (== STRIG_TOKEN's byte, other namespace)
MOTOR_TOKEN     equ     $CE     ; MOTOR | MOTOR ON | MOTOR OFF
STMOTR          equ     $00F3   ; BIOS: cassette motor. A=0 stop, $FF toggle,
                                ; else start (tape/tape.asm implements it).
; Error-handling S2b (docs/spec-basic-error-handling-s2b-packet.md §2): RESUME.
; Black-box-pinned ([[s2-error-token-pins]]): `resume next` -> A7 20 83,
; `resume 0` -> A7 20 0E 00 00. No prefix hazard (unlike ERR/ERROR).
RESUME_TOKEN    equ     $A7     ; RESUME / RESUME 0 / RESUME NEXT / RESUME <line>
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
; D-DEFFN: FN is ONE token, the byte immediately after USR's, and the NAME is
; plain ASCII after it (`FNA` -> $DE 'A'), arbitrary length, read at run time
; like any identifier -- measured off the STORED LINE BYTES on both references
; before any behaviour row was taken (docs/deffn-scout-2026-08-22.md §2). There
; is NO definition table in the crunch. Before this row the same line crunched
; `46 4E` -- "FN" as literal text, one byte longer per occurrence -- which is
; both why `DEF FN` fell to stmt_error and why an undefined `FNZ(1)` read as an
; ordinary subscripted array reference and answered a silent 0.
FN_TOKEN        equ     $DE     ; FN (function token, single byte; DEF FN target)
; D-DEFINTTOK (2026-08-18): DEFINT's OWN single-byte statement token, oracle-
; pinned against the Philips VG-8020 (`20 DEFINT 10` -> `<AC> <0F><0A>`,
; docs/lnref-msx1-characterization.md §4, and re-confirmed against the
; reference by docs/todo-staleness-sweep-2026-08.md §4.11's `c.defint` row).
; Previously zerobas had no entry for this and matched plain "DEF" instead,
; storing DEF_TOKEN + literal ASCII "INT" -- see the kwtable.inc row this
; token now feeds (basic/kwtable.inc, the "DEFINT" entry) for the full history.
DEFINT_TOKEN    equ     $AC     ; DEFINT (statement, single byte -- NOT DEF_TOKEN+"INT")
; D-DEFTYPETOK (2026-08-19): DEFINT's three siblings, same shape and the same
; oracle row (docs/todo-staleness-sweep-2026-08.md §4.11's `c.defstr`, plus the
; $AB/$AD/$AE pins in docs/lnref-msx1-characterization.md §4). These are
; CONTIGUOUS with DEFINT_TOKEN and sub/deftype.asm's type-code lookup indexes
; off that fact ($AB..$AE -> 0..3), so they may not be reordered or spaced.
DEFSTR_TOKEN    equ     $AB     ; DEFSTR  (= DEFINT_TOKEN-1; keep adjacent)
DEFSNG_TOKEN    equ     $AD     ; DEFSNG  (= DEFINT_TOKEN+1; keep adjacent)
DEFDBL_TOKEN    equ     $AE     ; DEFDBL  (= DEFINT_TOKEN+2; keep adjacent)
LIST_TOKEN      equ     $93     ; LIST
; D-KWGAP4 (docs/spec-basic-kwgap4.md §2 R-K1): the four EDITOR verbs, measured
; from the reference's own crunch emission over the whole 162-word denominator
; (docs/lnref-msx1-characterization.md §4), not read off a table.
;
; ⚠️ THE TOKEN IS ONLY HALF OF EACH OF THESE. All four ARM line-number mode on
; the reference, so branch_lineno grows a test for each one in the same slice --
; an entry without the arm crunches `DELETE 10` to `<A8> <0F><0A>`, which is the
; defect D-LNREF closed, reintroduced for four verbs (spec-basic-kwgap4.md §1).
;
; ✅ ALL FOUR ARE DISPATCHED. DELETE_TOKEN got its stmt_table row in D-DELETE
; (docs/spec-basic-delete.md, 2026-08-02); LLIST/AUTO/RENUM got theirs in
; D-EDITVERB (docs/spec-basic-editverb.md, 2026-08-06) -- ex_llist sharing
; ex_list's body, ex_renum, ex_auto, gated at 61 rows on three sides by
; `make editverb-acceptance`. No token in this block falls through to
; es_noentry -> stmt_error any more.
;
; 🔴 AND THIS COMMENT IS WHY. Until 2026-08-06 the paragraph above read "THREE OF
; THE FOUR ARE STILL NOT DISPATCHED", which was true when written and false from
; the day D-DELETE landed -- and D-EDITVERB opened by CITING these very lines as
; the two places the tree said so while TODO.md's index did not follow. The index
; was then corrected and this comment was not, so for one commit the tree carried
; the same defect pointing the other way. A comment that states a COUNT of what is
; implemented dates the moment it was written, not the code; if a fifth verb ever
; joins this block, restate the count here in the same commit.
;
; ⚠️ THE FILED REASON THEY DID NOT FIT WAS STALE TWICE OVER. spec-basic-kwgap4.md
; §3.4 costed four dispatch rows at 3 B each against a page 1 with 6 B free;
; D-RETLN's 160 B dead-instruction carve took page 1 to 124 B, and by D-EDITVERB
; it was 356 B. The 3 B/row figure (its knife K5) held; the WALL did not. The
; second half of that reason -- "AUTO/LLIST are unputtable to a reference in this
; harness at all" -- was REFUTED, not outgrown: a plugged openMSX `printerport
; logger` reports READY unconditionally so LLIST cannot block, and Ctrl-STOP is a
; key-matrix combination (row 6 bit 1 + row 7 bit 4) that keymatrixdown delivers
; and BREAKX sees (docs/editverb-msx1-characterization.md §1).
;
; None of these four bytes was previously equated in EITHER namespace, so unlike
; TRON/STICK ($A2) there is no same-value-different-alphabet hazard here.
LLIST_TOKEN     equ     $9E     ; LLIST                 (arms line-number mode)
DELETE_TOKEN    equ     $A8     ; DELETE <line>[-<line>] (arms)
AUTO_TOKEN      equ     $A9     ; AUTO [<start>][,<inc>] (arms -- and the INCREMENT
                                ; is stored as $0E too: lna-auto2 is why the
                                ; mechanism is a MODE and not a typed argument)
RENUM_TOKEN     equ     $AA     ; RENUM [<new>][,[<old>][,<inc>]] (arms)
; D-LPTVERB: the rest of the printer surface. Same provenance as the four above --
; D-LNREF's walk oracle-locked these bytes from the REFERENCE'S OWN CRUNCH
; EMISSION over the 162-word denominator (docs/lnref-msx1-characterization.md §4),
; not read off a published table. None of the three arms line-number mode, so
; unlike the editor verbs there is no branch_lineno work here.
;
; 🔴 BOTH NEW TOKENS COLLIDE BY VALUE WITH AN EQUATE IN THE OTHER ALPHABET, which
; is the TRON/STICK ($A2) shape this file already warns about -- safe, and only
; safe because the two namespaces are dispatched by different tables:
;   LPRINT $9D  (statement)  vs  BIND_TOKEN $9D  = BIN$, an $FF-prefixed FUNCTION
;   LPOS $FF,$9C (function)  vs  OUT_TOKEN  $9C  = OUT, a bare STATEMENT
; So LPOS must join the `ev_ff_argtab` / `ev_f_ff` chain in basic/expr.asm and
; LPRINT the `stmt_table` in basic/interp.asm. Cross them and each would answer
; the other's verb. $BB was equated in NEITHER namespace.
LPRINT_TOKEN    equ     $9D     ; LPRINT [<items>]      (statement; PRINT to LPT)
LFILES_TOKEN    equ     $BB     ; LFILES ["<filespec>"] (statement; Disk BASIC)
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
; Math pack slice 2c (Phase 3, repack-only -- docs/spec-basic-mathpack-
; slice2.md §13.1/§13.3). `^` (POW): single-byte operator token, MSX2 TH
; Table 2.20 + black-box VG-8020 crunch capture (probes/basic/basic_probe_
; math_conv.py), same family as STAR_TOKEN/IDIV_TOKEN above.
POW_TOKEN       equ     $F5     ; '^'  power (binds above * / and unary minus)
MOD_TOKEN       equ     $FB     ; MOD  remainder
AND_TOKEN       equ     $F6     ; AND  (bitwise)
OR_TOKEN        equ     $F7     ; OR   (bitwise)
XOR_TOKEN       equ     $F8     ; XOR  (bitwise)
; EQV/IMP: oracle-measured from the VG-8020's own CRUNCH emission (the kwsweep
; token table, docs/kwsweep-msx1-coverage.md) -- bytes the REFERENCE emitted,
; not a table lookup. They fill the $F9/$FA hole between XOR and MOD.
EQV_TOKEN       equ     $F9     ; EQV  (bitwise equivalence, = NOT (a XOR b))
IMP_TOKEN       equ     $FA     ; IMP  (bitwise implication, = (NOT a) OR b)
NOT_TOKEN       equ     $E0     ; NOT  (bitwise complement, unary)
; Cursor / PRINT-positioning cluster. Tokens oracle-measured from the VG-8020's
; own crunch emission (docs/kwsweep-msx1-coverage.md). TAB( and SPC( include the
; '(' IN THE KEYWORD, which is what keeps a variable named TAB a variable.
CSRLIN_TOKEN    equ     $E8     ; CSRLIN — bare pseudo-variable, 0-based cursor ROW
POS_TOKEN       equ     $91     ; POS(n) — $FF-prefixed; 0-based COLUMN, arg discarded
; D-LPTVERB: LPOS(n) is POS(n)'s printer twin -- same $FF alphabet, same dummy
; argument, same required parentheses (docs/lptverb-msx1-characterization.md
; R-LS4/R-LS5), different SOURCE: the printer column LPTPOS, not the screen's
; CSRX. ⚠️ $9C is also OUT_TOKEN in the STATEMENT alphabet -- see LPRINT_TOKEN.
LPOS_TOKEN      equ     $9C     ; LPOS(n) — $FF-prefixed; 0-based PRINTER column
TAB_TOKEN       equ     $DB     ; TAB(n) — PRINT item, ABSOLUTE column
SPC_TOKEN       equ     $DF     ; SPC(n) — PRINT item, RELATIVE n spaces
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
; BSAVE/BLOAD) -- also cassette ASCII load's CAL_CURHI (below): a BSAVE/BLOAD
; ",S" and a cassette ASCII LOAD/CLOAD never run at the same time, so the two
; overlay (same discipline as CAL_CNT/CAL_NEEDFILL/CAL_SAVE further down).
; VRAM_FLAG: 1 = the ",S" flag was given -> the data bytes stream to/from VRAM
; (RDVRM/WRTVRM) instead of RAM; the $FE header start/end/exec are stored/read
; verbatim as VRAM addresses. Cleared at the top of every BSAVE/BLOAD parse.
VRAM_FLAG       equ     $E0E9   ; 1 = ",S" VRAM save/load (1)
; CAL_CURHI: cassette ASCII load's DOUBLE-BUFFER "which buffer is being served"
; pointer -- the high byte of CAL_BUF ($E6) or CAL_BUF2 ($E8), CAL_CNT (below)
; being the low byte. TWO 256-byte buffers, not one, because a SINGLE buffer's
; refill-on-drain (the earlier fix here) still calls TAPION for block N+1 only
; once block N is fully DRAINED -- i.e. after ascii_read_lines has tokenised
; every line block N held. On a real cassette the tape keeps moving the whole
; time (cload.asm requirement 2), so a block whose lines are unusually slow to
; tokenise (long/complex ones: nested parens, several keywords) lets the tape
; play past block N+1's leader before TAPION is even called -- TAPION then
; locks onto whatever short/long cycles happen to be at the CURRENT (too-late)
; position, which on a well-formed tape is misaligned data, not a leader, and
; the very first TAPIN of that "block" fails (measured: a real 21-line, 4-block
; program truncated after line 110, one text block earlier than the reported
; bug, once the single-buffer fix moved the failure from block 2 to block 4 --
; docs/spec-cas-ascii-saveload.md).
;
; The double buffer gives every block's TAPION a full extra block's worth of
; head start: cas_ascii_setup primes block 1 into one buffer, then IMMEDIATELY
; (before any tokenising) primes block 2 into the other -- back-to-back, same
; regime as block 1 alone always used. Thereafter, draining the buffer CAL_CURHI
; points at swaps to the other (already pre-fetched -- an instant swap, no
; TAPION on the critical path) and kicks off refilling the JUST-FREED buffer
; with the block after next. So a block's own TAPION always fires when the
; block BEFORE its predecessor drains -- one whole block's tokenise time
; earlier than a single-buffer scheme -- covering realistic per-line tokenise
; cost (confirmed: this is what let a 4-block real program's block 4 succeed
; where it failed under the single-buffer fix, block 3's slow lines no longer
; delaying block 4's own TAPION).
;
; cal_refill (cal-refill-body.inc) always fills "whichever buffer CAL_CURHI is
; NOT pointing at", derived per TAPIN'd byte (CAL_CURHI can't ride a register
; across TAPIN, which clobbers everything) as CAL_CURHI XOR CAL_XORHI (an
; assembly-time constant, CAL_BUF>>8 XOR CAL_BUF2>>8 -- no extra RAM needed
; since XORing either buffer's own high byte into that constant yields the
; other). cas_skip_data's csd_ascii arm (sub/casmatch.asm, the OTHER cal_refill
; caller sharing this .inc) wants a single fixed buffer, not double-buffering --
; it gets that by setting CAL_CURHI to CAL_BUF2's high byte ONCE before its
; loop and never touching it again, so every cal_refill call in that loop keeps
; targeting CAL_BUF, unchanged from before this fix.
CAL_CURHI       equ     $E0E9   ; cassette ASCII load: high byte of the CURRENTLY
                                ; SERVED buffer, CAL_BUF ($E6) or CAL_BUF2 ($E8) (1)
; Cassette ASCII load (cload.asm cal_getbyte) read position within the current
; 256-byte tape block, 0..255 (§0.1: fixed 256-byte tape data blocks). Also the
; drain trigger: wrapping 255->0 means "this buffer is now empty -> swap to the
; pre-fetched other one". Dead outside a cassette ASCII LOAD/CLOAD — never live
; at the same time as a BSAVE/BLOAD ",S" — so it reuses the same free gap (like
; IN_RDLEN and FILES_ENTIDX below overlay each other).
CAL_CNT         equ     $E0EA   ; cassette ASCII load: read position in the
                                ; current 256-byte tape block, 0..255 (1)
CAL_NEEDFILL    equ     $E0EB   ; cassette ASCII load: whether the buffer CAL_CURHI
                                ; does NOT point at holds a live pre-fetched block.
                                ; 0 = it does (the normal, steady-state case: swap
                                ; to it freely on drain). 1 = a read-ahead attempt
                                ; found no further block (checked only at a drain,
                                ; before swapping -- fine on a well-formed tape,
                                ; where ascii_read_lines stops at Ctrl-Z first).
                                ; 2 = TERMINAL: the drain that just happened was
                                ; genuinely the last byte on the tape (no buffer
                                ; left to swap to) -- the byte itself is still
                                ; returned, but the NEXT cal_getbyte call reports
                                ; CF with no further buffer access (1)
; cal_getbyte parks the block's last byte here while cal_refill's 256-TAPIN slurp of
; the read-ahead buffer overwrites the OTHER buffer -- the held byte cannot ride
; the stack across TAPIN (requirement 1 in cload.asm). Overlays CAS_WCNT ($E0EC):
; that is the cassette SAVE block counter, dead during a LOAD, so the two never
; collide.
CAL_SAVE        equ     $E0EC   ; cassette ASCII load: parked byte across a prefetch (1)
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
; CALL FORMAT sub-ROM tenant args/result (repack eviction, docs/spec-evict-call-
; format.md §3/§4). ALIASED over the tape CSAVE/BSAVE write scratch just above —
; CALL FORMAT and a tape CSAVE/BSAVE are distinct top-level statements that never
; run at the same instant (the same collision-checked-reuse pattern as
; IN_RDLEN/FILES_ENTIDX below), and RAM below DRVA_DPB ($F195) is exhausted (math
; pack slice 2 §11.6), so no fresh claim is available. Both are RAM, so visible
; from main (page-1 resident stub) and the sub-ROM page-1 tenant alike.
FMT_GEOMSEL     equ     TSV_CNT ; main -> tenant: 0 = 360k, 1 = 720k (1)
FMT_RESULT      equ     TSV_NAME ; tenant -> main: 0 = ok, 1 = DSKIO write error (1)
; scan_stmt_end (SUBROM_IDX_SCANSTMT, sub/errtrap.asm) result -- error-
; handling S2b's RESUME NEXT (docs/spec-basic-error-handling-s2b-packet.md
; §5.5). ALIASED over the SAME tape CSAVE/BSAVE write scratch as FMT_GEOMSEL/
; FMT_RESULT just above -- RESUME NEXT, a tape CSAVE/BSAVE, and CALL FORMAT
; are three distinct top-level statements that never run at the same instant
; (the same collision-checked-reuse pattern), and RAM below DRVA_DPB is
; exhausted. No dedicated input cell: the tenant reads ERRRESUME+2 directly
; (own header has the rationale). A single output cell (TSV_PTR, untouched by
; FMT_*, which only claims TSV_CNT/TSV_NAME): $0000 doubles as the failure
; sentinel (a real statement/line pointer is never $0000), so no separate
; disposition byte is needed. RAM, so visible from main (page-1 resident
; stub) and the sub-ROM page-1 tenant alike.
SSE_OUT         equ     TSV_PTR ; tenant -> main: next statement's start, or
                                ; $0000 if the erroring line's own link was
                                ; $0000 (degenerate -- nothing to resume to) (2)
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
; placed ABOVE all basic-core RAM (which is capped at $E560 -- the ceiling the
; assembler asserts at sysvars.inc `IF GFX_G8V + 2 > $E560` / `IF GFX_PSTK_END >
; $E560`; the topmost cell today is GFX_G8V $E55E..$E55F).
; 🔴 THIS READ "tops out at STRSCR $E360..$E380" UNTIL 2026-08-27 (D-WALLIT) AND WAS
; WRONG TWICE: STRSCR is $E26D..$E36D (this same file, :1481), and it is not the top
; -- the GFX_PSTK/GFX_D* block above it runs to $E55F, 512 B higher. A reader siting
; a new host buffer off this sentence would have overlapped live graphics scratch.
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
; DISKOP marshalling block (repack eviction, docs/spec-evict-diskfile-cluster.md
; §11): the FAT12 primitive/sector layer's resident<->tenant ABI. Claims the
; LAST 5 free bytes below FCH_CTX ($E9FB..$E9FF, between FWR_DIROFF+2 and the
; $EA00 channel-context table) -- a genuine unclaimed gap (FCH_STATESZ's own
; comment below computes the span as ending at $E9FA), not a live-scratch
; alias: unlike FMT_GEOMSEL/FMT_RESULT (which safely alias tape CSAVE/BSAVE
; scratch because CALL FORMAT never nests inside a tape save), a FATPRIM shim
; is reachable from INSIDE do_save's DSV_PTR/DSV_END walk and field.asm's
; GP_* random-access loop state, so aliasing onto EITHER of those would let a
; primitive call clobber the caller's own live loop variables mid-walk. RAM,
; so visible from main (page-1 resident shims) and the sub-ROM page-1 tenant
; (sub/fatprim.asm) alike.
DISKOP_OP       equ     $E9FB   ; main -> tenant: DISKOP_SEL_* primitive selector (1)
DISKOP_STATUS   equ     $E9FC   ; tenant -> main: 0 = ok (Cy=0 / Z set); nonzero =
                                ; error (Cy=1) or no-match (NZ), per primitive (1)
DISKOP_A        equ     $E9FD   ; tenant -> main: the primitive's real A output,
                                ; if it has one (read_sector/write_sector's DSKIO
                                ; error code); reloaded uniformly even where no
                                ; caller currently reads it (1)
DISKOP_HL       equ     $E9FE   ; tenant -> main: the primitive's real HL output
                                ; (fat_alloc_cluster's allocated cluster number);
                                ; reloaded uniformly for every primitive (2)
; fat_count_free's DE output (free cluster count) is NOT a new DISKOP_DE cell --
; the 5-byte gap above is already fully claimed. It rides back over FAT_WRTMP2
; instead (fat_count_free's OWN scratch, already RAM-visible both sides): the
; tenant wrapper (sub/fatprim.asm t_fat_count_free) copies DE into FAT_WRTMP2
; unconditionally before returning (harmless on the normal path, where
; fat_count_free already left DE == FAT_WRTMP2 at fcf_done; corrective on the
; fcf_zero/mount-failure path, which sets DE=0 directly without touching
; FAT_WRTMP2). No external code reads FAT_WRTMP2 (grep-verified), so this is
; safe to repurpose as fat_count_free's own dedicated return channel.
; DISKOP_OP selector values -- one per marshalled FAT12 primitive (spec §11's
; 15-routine "danger list" + the plain Cy-only primitives), in basic/fat.asm's
; original routine order. Never renumber (both basic/fat.asm's shims and
; sub/fatprim.asm's dispatch table key off these numerically).
DISKOP_SEL_READ_SECTOR          equ 0
DISKOP_SEL_WRITE_SECTOR         equ 1
DISKOP_SEL_FAT_MOUNT            equ 2
DISKOP_SEL_FAT_FIND             equ 3
DISKOP_SEL_NAME_CMP             equ 4
DISKOP_SEL_FAT_OPEN             equ 5
DISKOP_SEL_FAT_READ_FAT_SECTOR  equ 6
DISKOP_SEL_FAT_READ_FILE_SECTOR equ 7
DISKOP_SEL_FAT_ALLOC_CLUSTER    equ 8
DISKOP_SEL_FAT_WRITE_FAT_ENTRY  equ 9
DISKOP_SEL_FAT_COUNT_FREE       equ 10
DISKOP_SEL_FAT_FLUSH_DATA_SECTOR equ 11
DISKOP_SEL_FAT_DIR_CREATE       equ 12
DISKOP_SEL_FAT_DIR_UPDATE       equ 13
DISKOP_SEL_FAT_DELETE           equ 14
; DISKOP_SEL_RAND_OPEN/GET/PUT (docs/spec-eviction-g4-space.md §3, carve #1):
; three MORE rows on the SAME fp_table/DISKOP_OP selector (still
; SUBROM_IDX_FATPRIM, no new tenant index) -- the fat_rand_* random-access
; record engine (basic/field.asm), evicted whole to sub/randio.asm and
; co-located after fatprim so its own FAT12 primitive calls (fat_mount/
; fat_find/fat_dir_create/fat_alloc_cluster/fat_write_fat_entry/
; fat_read_fat_sector/read_sector/write_sector/fat_dir_update) resolve
; sub-locally, the same "dirverb" pattern. Never renumber.
DISKOP_SEL_RAND_OPEN            equ 15
DISKOP_SEL_RAND_GET             equ 16
DISKOP_SEL_RAND_PUT             equ 17
; DISKOP_SEL_FIA_WALKED (docs/spec-eviction-g7-space.md, carve 2): fat_io_append's
; "chain already walked" tail -- pure FAT_*/FWR_*/FSECTOR_BUF arithmetic, evicted
; whole to free page-1 tail for G7's sprite statements.
DISKOP_SEL_FIA_WALKED           equ 18
; DISKOP_SEL_FCH_RESTAGE (D-FCH S-FCH-1, docs/spec-basic-filechan-alloc.md §3.1):
; re-read into FSECTOR_BUF whatever the just-loaded channel had staged there, so
; the per-channel 512-byte save copy can go away. Sited in the SUB-ROM because
; the cluster->absolute-sector arithmetic it needs already lives there twice
; (fat_read_file_sector's frs_incluster, fat_flush_data_sector's ffds_haveclus)
; and main page 1 has 6 B free.
DISKOP_SEL_FCH_RESTAGE          equ 19
DISKOP_SEL_FCH_DETACH           equ 20  ; the inverse: flush the dirty partial
                                        ; sector in place before handing the
                                        ; shared buffer to another channel
; DISKOP_OP selector values for the dirverb_tenant (SUBROM_IDX_DIRVERB, Phase 2,
; spec §12). A SEPARATE value namespace on the SAME DISKOP_OP cell: fatprim
; (index 12) and dirverb (index 13) are never in flight at once (one subrom_call
; reaches exactly one tenant), so 0/1 here are dirverb-local and do NOT alias
; fatprim's READ_SECTOR/WRITE_SECTOR despite sharing the numeric value.
DISKOP_SEL_KILL                 equ 0   ; dirverb: KILL's fat_delete loop
DISKOP_SEL_NAME_STAMP           equ 1   ; dirverb: NAME's read+overwrite+write
; D-LFILES (docs/spec-basic-lfiles.md §2/§3): the directory LISTING, the third
; body of this tenant and the eviction Phase 2 dropped. ⚠️ THESE TWO ARE NOT ONLY
; A SELECTOR. The same cell picks the tenant's SINK (CHPUT vs LPTOUT, df_out) and
; its LAYOUT (packed rows vs one entry per line, df_emit/df_end), which is why
; LFILES needed no mode cell of its own and why nothing may write DISKOP_OP
; between the head's store and the tenant's return.
DISKOP_SEL_FILES                equ 2   ; dirverb: FILES  -> screen, packed rows
DISKOP_SEL_LFILES               equ 3   ; dirverb: LFILES -> printer, one per line

; --- Line-editor tenant ABI (SUBROM_IDX_LINEEDIT, docs/spec-eviction-g4-
; space.md §4, carve #2): reuses the SAME DISKOP_OP/DISKOP_STATUS RAM cells,
; ANOTHER separate value namespace (fatprim/dirverb/audio/lineedit are never
; in flight at once -- one subrom_call reaches exactly one tenant), aliased
; under line-editor-local names for readability at the call sites.
LE_OP           equ     DISKOP_OP       ; main -> tenant: LE_OP_* selector
; LE_STATUS: tenant -> main. D-DELETE (docs/spec-basic-delete.md §4) WIDENED
; this from a boolean to an ERR CODE, and the two ops read it differently only
; because 1 was never a BASIC error number:
;   LE_OP_STORE    0 = ok, 1 = out of memory -> the resident head's own `ld a,7`
;   LE_OP_DELRANGE 0 = ok, else the ERR CODE ITSELF (2 = R-D6 trailing junk,
;                  5 = R-D2/R-D4 illegal function call) -> `jp raise_error`
;   LE_OP_LSTRANGE 0 = ok, else the ERR CODE ITSELF -- only ever 2 (R-LS6). LIST
;                  has NO range error at all: a high end naming no stored line,
;                  a reversed range and a range past the program are all ERR 0
;                  and simply list nothing (docs/listrange-msx1-characterization.md
;                  §5.1). That is measured, not assumed -- it is exactly where
;                  DELETE raises 5.
; The delrange head can therefore raise without a second table or a second
; compare. LE_OP_RELINK never fails and does not touch the cell.
LE_STATUS       equ     DISKOP_STATUS
LE_OP_STORE             equ 0   ; lineedit: process SL_NUM/SL_TOK (store or delete)
LE_OP_RELINK            equ 1   ; lineedit: relink-only (cload.asm's own call sites)
LE_OP_DELRANGE          equ 2   ; lineedit: DELETE <lo>-<hi> -- parse SL_TOK, then
                                ; unlink every line in [SL_DELLO, SL_DELHI]
LE_OP_LSTRANGE          equ 3   ; lineedit: LIST <lo>-<hi> -- PARSE ONLY (D-LSTRNG).
                                ; Fills LST_LO/LST_HI from LST_PTR and returns; the
                                ; WALK stays resident, because it prints through
                                ; main page-1 pchar and CALSLTs the page-0
                                ; detokeniser -- neither reachable from a page-1
                                ; tenant (spec-basic-listrange.md §3.1, where that
                                ; makes DELETE's whole-verb split IMPOSSIBLE here).
                                ; Status: 0 = ok, 2 = R-LS6 trailing junk.
; --- D-EDITVERB (docs/spec-basic-editverb.md) -------------------------------
; 🎯 LLIST SHARES LIST'S PARSE BYTE-FOR-BYTE. All twenty range shapes D-LSTRNG
; measured answer identically under LLIST (R-LL2/R-LL3, characterization §4), so
; op 4 routes to the SAME tenant body; it exists only so the RESIDENT head can
; read LE_OP BACK and choose the sink. That read-back is why this is an op and
; not a new RAM flag -- LE_OP is already marshalled and already survives the
; call, so the sink costs ZERO cells.
LE_OP_LLSTRANGE         equ 4   ; lineedit: LLIST <lo>-<hi> -- le_lstrange verbatim
; RENUM. Op 5 parses, validates and runs the reference pass; it returns
; LE_STATUS = 1 with RN_TGT/RN_LINE set for EACH dangling reference (R-RN9 --
; one message per reference, and `1 ON 1 GOTO 77,88` emits two from ONE line),
; because the message must be printed by the head: `Undefined line` renders
; through main page-1 print_msg/list_num, which a page-1 tenant cannot reach.
; Op 6 resumes that walk at RN_PTR. Status: 0 = done, 1 = report and re-enter,
; else the ERR CODE ITSELF (2 = R-RN14/R-RN15, 5 = R-RN11/R-RN12/R-RN13).
LE_OP_RENUM             equ 5   ; lineedit: RENUM [<new>][,[<old>][,<inc>]]
LE_OP_RENUM_NEXT        equ 6   ; lineedit: resume the reference pass at RN_PTR
; AUTO parses its argument here and runs its MODAL LOOP in main -- the mirror of
; LIST's split, and for the mirror reason: the loop drives read_line/
; dispatch_line/CHPUT, all main page 1.
LE_OP_AUTO              equ 7   ; lineedit: AUTO [<start>][,<inc>] -- PARSE ONLY
; D-DELETE §3.2: DELETE's two range ends and its statement cursor ride the SAME
; THREE CELLS store_line marshals -- a SECOND VALUE NAMESPACE on them, exactly
; like LE_OP on DISKOP_OP one screen up.
;
; 🔴 THE NON-OVERLAP IS PROVED BY GREP, NOT ASSERTED. Every reader of SL_NUM /
; SL_SIZE / SL_TOK is on the LE_OP_STORE path: le_store itself, prog_find_del
; (SL_NUM) and open_gap (SL_SIZE). delete_at reads only SL_SLOT + PRGEND;
; relink_body reads neither. One subrom_call reaches exactly one LE_OP, so a
; store and a delrange are never in flight together. (SL_SLOT is NOT aliased --
; le_delrange's walk hands it to delete_at for its real store_line meaning.)
SL_DELLO        equ     SL_NUM          ; DELETE: low end of the range (2)
SL_DELHI        equ     SL_SIZE         ; DELETE: high end of the range (2)
SL_DELPTR       equ     SL_TOK          ; DELETE: the statement cursor, on the token

; D-LSTRNG §3.4: LIST <range> is a THIRD namespace on the same three cells, and
; the grep that proves it is WIDER than DELETE's had to be. DELETE's range dies
; inside one subrom_call; LIST's must survive the whole list_walk, which CALSLTs
; the page-0 detokeniser per line and -- through the SAME walk reached from
; ascii_save / cas_ascii_save -- runs the FAT12 disk writer or the cassette
; block writer. So the question is not "is a store in flight" but "does anything
; on ANY of those three paths touch these cells".
;
;   grep -rn 'SL_NUM\|SL_SIZE\|SL_TOK\|SL_SLOT\|SL_DEL' basic/*.asm sub/*.asm
;
; returns readers in exactly two files: basic/program.asm (store_line,
; ex_delete) and sub/lineedit.asm (le_store, le_delrange, prog_find_del,
; delete_at, open_gap). NO detok, save, FAT or cassette path appears. One
; subrom_call reaches exactly one LE_OP, so a store, a delrange and a listrange
; are never in flight together.
LST_LO          equ     SL_NUM          ; LIST: low end of the range (2)
LST_HI          equ     SL_SIZE         ; LIST: high end of the range (2)
LST_PTR         equ     SL_TOK          ; LIST: the statement cursor, on the token

; --- D-EDITVERB: RENUM's namespace ------------------------------------------
; The two REPORT cells are a FOURTH value namespace on SL_NUM/SL_SIZE, on the
; same argument the block above makes for DELETE and LIST: one subrom_call
; reaches exactly one LE_OP, and the grep at the head of that block still
; returns readers in exactly two files.
RN_TGT          equ     SL_NUM          ; RENUM: the UNDEFINED target being reported (2)
RN_LINE         equ     SL_SIZE         ; RENUM: the OLD number of the line it is in --
                                        ; R-RN8, the message says `in 1`, not `in 10` (2)
; 🔴 THE OTHER FOUR MAY NOT BE ALIASES, AND THAT IS THE WHOLE REASON THIS BLOCK
; EXISTS. They are live ACROSS the report/re-enter round trip (LE_OP_RENUM ->
; the head prints `Undefined line N in M` -> LE_OP_RENUM_NEXT), and the head
; runs print_msg + list_num in between. list_num goes through ln_div_entry,
; which formats into NUMBUF; print_msg walks the message pool. Neither touches
; $EAxx -- but neither can be relied on to leave the SL_* block alone across a
; call the DELETE and LIST heads never make, because those two verbs report
; nothing and re-enter nothing.
;
; ⚠️ HOMED IN THE $EA30 WINDOW THE TREE ITSELF DOCUMENTS AS FREE (FCH_RECLENS,
; "$EA30..$EAFF free"), NOT in the $E00x gap below CURPTR. That gap looked free
; to a grep and is not: $E000 is the demo blob's "JONG" marker / POKE test
; target (the RAM-scratch header above says so in as many words), and a 2-byte
; cell at $E00F runs straight over ERRMARK at $E010.
RN_PTR          equ     $EA30           ; RENUM: the reference-pass cursor (2)
RN_NEW          equ     $EA32           ; RENUM: first new line number (2)
RN_OLD          equ     $EA34           ; RENUM: old line to start renumbering at (2)
RN_INC          equ     $EA36           ; RENUM: increment (2)
; AUTO's two values, a FIFTH namespace on RENUM's own cells: one subrom_call
; reaches one LE_OP, and an AUTO session and a RENUM cannot be in flight
; together (each ends the line and the program on its way out).
AU_NUM          equ     RN_NEW          ; AUTO: the line number being prompted (2)
AU_INC          equ     RN_INC          ; AUTO: the increment (2)
; read_line's mode flag. 0 = block in CHGET (the REPL); 1 = poll CHSNS and
; BREAKX (an AUTO session), because Ctrl-STOP is NOT a character and can never
; arrive through CHGET -- R-AU8. Cleared defensively at the top of `repl`, so a
; line that ERRORS out of an AUTO session cannot leave the prompt polling.
RL_AUTO         equ     $EA38           ; read_line: 1 = AUTO's polling mode (1)

; --- D-LPTVERB: the printer column ------------------------------------------
; LPOS(n)'s source, and LPRINT's flush condition. 0-based: 0 = the printer head
; is at the start of a line.
;
; 🔴 MAINTAINED IN THE SINK (pch_lpt), NOT IN THE STATEMENT, and R-LS6 is why:
; `LPRINT TAB(10);` leaves LPOS reading 10, and that padding is emitted through
; pchar by the PRINT item loop -- ex_lprint never sees those ten bytes. A counter
; incremented in the statement head reads 0 there. Knife K5 is that pair.
;
; ⚠️ AND IT IS NOT CSRX. ev_ff_lpos is written by copying ev_ff_pos, whose body
; reads CSRX; on a fresh machine the screen column and the printer column are
; BOTH 0, so `lps-init` cannot tell them apart. `lps-after`/`lps-tab`/`lps-multi`
; are the rows that can, and knife K6 is the cut.
;
; Zeroed on CR ($0D). ⚠️ A LONE LF IS UNMEASURED: no reference row asks it, and
; both "zero on CR only" and "zero on CR or LF" satisfy R-LS3 (after CR/LF the
; count is 0 either way). LF is simply not counted as an advance here; that is a
; CHOICE, recorded as one, not a measured rule.
LPTPOS          equ     $EA39           ; printer head column, 0-based (1)

; --- Cassette name-match/skip tenant ABI (SUBROM_IDX_CASMATCH, docs/spec-
; eviction-g5-space.md): reuses the SAME DISKOP_STATUS RAM cell, ANOTHER
; separate value namespace (fatprim/dirverb/audio/lineedit/casmatch are never
; in flight at once -- one subrom_call reaches exactly one tenant). No OP
; selector cell needed (unlike LE_OP) -- casmatch_tenant has exactly one
; entry point (cas_open_match), no selector to marshal.
CM_STATUS       equ     DISKOP_STATUS   ; tenant -> main: 0 = matched (-> CF
                                        ; clear) / 1 = not found or tape error
                                        ; (-> CF set); converted back to CF by
                                        ; the resident cas_open_match shim.

; --- 8.3-FCB-name builder tenant ABI (SUBROM_IDX_FCBNAME, docs/spec-basic-
; interrupt-traps.md §10.4): the build_83_name eviction (basic/bload.asm ->
; sub/fcbname.asm). build_83_name takes HL in and returns HL (advanced) + CF;
; subrom_call clobbers every register and forces CF=0 on return, so both outputs
; ride through RAM. BN_PTR carries the source pointer to the tenant AND the
; advanced pointer back; BN_STAT carries the reject flag back (0 = ok / 1 =
; reject, `rra`'d to CF by the resident shim). Both ALIAS the fatprim
; DISKOP_HL/DISKOP_STATUS cells: the FCB-name build runs entirely in the disk-verb
; PARSE phase, strictly before any fat_io_* primitive, so the fatprim marshalling
; cells are provably dead here -- the CM_STATUS/LE_STATUS "never in flight at
; once, one subrom_call reaches one tenant" precedent.
BN_PTR          equ     DISKOP_HL       ; main <-> tenant: filename ptr (in) /
                                        ; advanced ptr = closing '"' (out) (2)
BN_STAT         equ     DISKOP_STATUS   ; tenant -> main: 0 ok / 1 reject (-> CF) (1)

; --- Audio: PLAY work area + queue packet format (audio Slice 2a) -----------
; docs/spec-basic-audio-play-slice2a.md. The program-visible cells are the
; STANDARD MSX music work area at their MSX2-Technical-Handbook addresses (a
; published-contract layout, ALSO reserved by our open target C-BIOS -- it inits
; QUETAB at boot but never drains; its PLAY is a TODO stub). Placing everything
; here is the placement AND the Q2 faithfulness: a program that PEEKs MUSICF /
; QUETAB / a VCB sees reference-compatible values. No stock-ROM disassembly, no
; C-BIOS bytes copied ([memory: no-reference-rom-disasm]). The queue *packet
; bytes* are own-design (byte-exact match to the reference queue content is the
; deferred Slice-3 stretch); the drain algorithm is Slice 3.
QUETAB          equ     $F959   ; 4 x 6-byte ring descriptors (3 voice + 1 RS232)
VOICAQ          equ     $F975   ; voice-0 packet buffer (128 B)
VOICBQ          equ     $F9F5   ; voice-1 packet buffer (128 B)
VOICCQ          equ     $FA75   ; voice-2 packet buffer (128 B)
VOICEN          equ     $FB38   ; voice currently being parsed (0..2)
MCLPTR          equ     $FB3C   ; address of the MML string being parsed (source cursor)
QUEUEN          equ     $FB3E   ; active queue # scratch (0..2)
MUSICF          equ     $FB3F   ; bitmask: bit v = voice v queue active (SET LAST)
PLYCNT          equ     $FB40   ; count of PLAY statements parsed, not yet executed
VCBA            equ     $FB41   ; Voice Control Block, voice 0 (37 B)
VCBB            equ     $FB66   ; Voice Control Block, voice 1
VCBC            equ     $FB8B   ; Voice Control Block, voice 2
VCB_STRIDE      equ     VCBB - VCBA         ; $25 = 37 B between voice blocks
; QUETAB per-voice ring descriptor field offsets (base = QUETAB + 6*voice):
QD_PUT          equ     0       ; put (write) position within the buffer
QD_GET          equ     1       ; get (read) position -- 0 in Slice 2a (no drain)
QD_PUTBAK       equ     2       ; putback flag (unused in 2a)
QD_SIZE         equ     3       ; buffer size (128)
QD_ADDR         equ     4       ; buffer base address (VOICxQ), 2 B
QD_STRIDE       equ     6       ; bytes per descriptor
; VCB field offsets (MSX2-TH layout; base = VCBA/VCBB/VCBC). 2a uses the parse
; state (persisted across PLAY statements per D4-B) + the packet-source fields:
VCX_VCXLEN      equ     2       ; MCLLEN for this voice (marshalled string length)
VCX_VCXPTR      equ     3       ; MCLPTR for this voice (marshalled string ptr, 2 B)
VCX_ENVPER      equ     13      ; ENVPRX: envelope period (M command), 2 B
VCX_OCTAVE      equ     15      ; OCTAVX: current octave 1..8
VCX_NOTEL       equ     16      ; NOTELX: default note length 1..64
VCX_TEMPO       equ     17      ; TEMPOX: tempo 32..255
VCX_VOLUME      equ     18      ; VOLUMX: volume 0..15
VCX_ENVSH       equ     19      ; ENVLPX: envelope shape 0..15 ($10 bit = env mode on)
; Audio Slice 3 (docs/audio-slice3-characterization.md §2): the live drain servicer's
; per-voice frame down-counter. OWN-DESIGN offset (past the parse-state fields; the
; MSX music player keeps an equivalent counter in the VCB, exact offset not lifted --
; no disassembly). Seeded to 0 by the parser's queue reset so the first VBLANK fetches
; packet 0; play_service loads it with a note's `dur` and decrements once per frame.
VCX_FRAMES      equ     20      ; frames remaining for this voice's current note, 2 B
; H.TIMI ($FD9F) timer-interrupt hook -- the seam play_service installs at boot (a
; JP; the hook is C9-free on our target so no chain). It is our entry into C-BIOS's
; $0038 ISR; play_service is main-ROM page-1 resident (reached by a near JP, mapped
; whenever the ISR fires -- page-1 tenants run DI, §4a) and does the MUSICF==0 fast-out.
H_TIMI          equ     $FD9F   ; timer-interrupt hook, 5-byte inter-slot call area
; --- BASIC-extension hooks the DISK ROM claims (D-MKHOOK) -------------------
; docs/spec-basic-nodisk.md. On real MSX the MAIN ROM owns the disk keywords'
; TABLE and the DISK ROM supplies their IMPLEMENTATION through these -- which is
; why a diskless machine tokenises `MKI$` and then answers Illegal function call.
; Unclaimed, the slot is C-BIOS's `ret` (its hook-area init $C9-fills
; $FD9A..$FFE7) and leaves CF exactly as the caller set it, which is what makes
; "CF=0 -> no disk ROM" a sound test rather than a guess.
H_DSKF          equ     $FE12   ; DSKF handler
H_MKI           equ     $FE30   ; MKI$ handler (disk/kernel.asm hk_present)
H_MKS           equ     $FE35   ; MKS$ handler
H_MKD           equ     $FE3A   ; MKD$ handler
H_CVI           equ     $FE3F   ; CVI handler
H_CVS           equ     $FE44   ; CVS handler
H_CVD           equ     $FE49   ; CVD handler
H_NAME          equ     $FDF9   ; NAME handler   (channel verbs, D-CHANHOOK)
H_KILL          equ     $FDFE   ; KILL handler
H_FILE          equ     $FE7B   ; FILES handler
; --- the KEY-trap fn-key hook (interrupt-traps T3, docs/spec-traps-t3-key.md §4) ---
; NOT a standard MSX hook: it is added by OUR C-BIOS patch
; (cbios-repack/key-trap-hook.patch) because no published hook can see the current
; frame's KEYBUF insertion -- both H.KEYI and H.TIMI run BEFORE the keyboard scan
; (D-T3-3, measured on C-BIOS and on the VG-8020), and a sweep of all ~112 slots
; found no post-scan seam with a program running (spec §4.1).
; PLACEMENT: $FFCF sits just past H.BEXT ($FFCA..$FFCE), the highest hook C-BIOS
; defines, and still INSIDE the span C-BIOS $C9-fills at boot ($FD9A..$FFE7, its
; own hook-area init). So the slot needs no initialisation of ours and defaults to
; `ret` with CF undisturbed -- an unpatched or non-BASIC boot is unaffected. The
; span is C-BIOS-managed scratch with no standard hook meaning and nothing else in
; zerobas claims it (checked against the whole RAM map).
H_ZKEY          equ     $FFCF   ; fn-key delivery hook, 5-byte JP vector (zkey_install)
; NEWKEY ($FBE5): the published MSX key-matrix work area, 11 rows, ACTIVE LOW
; (0 = pressed; C-BIOS seeds it $FF at boot). zkey_hook reads row 6 bit 0 = SHIFT
; to fold F1-F5 into F6-F10 -- C-BIOS does not fold it itself (D-T3-7, measured).
NEWKEY          equ     $FBE5   ; key matrix snapshot, 11 B (row 6 bit 0 = SHIFT)
; PLAY parse defaults (cold-boot seed; TEMPOX==0 is the "not seeded" sentinel,
; reliable because C-BIOS zeroes $F380.. at boot):
PLAY_DEF_OCTAVE equ     4
PLAY_DEF_NOTEL  equ     4
PLAY_DEF_TEMPO  equ     120
PLAY_DEF_VOLUME equ     8
; Marshalling: audio and disk are never in flight together (a PLAY does no disk
; I/O, one subrom_call reaches one tenant), so audio reuses the DISKOP cells --
; the same "separate namespace, same cell" precedent as fatprim vs dirverb above.
AUDIO_VMASK     equ     DISKOP_OP       ; $E9FB main->tenant: voices-present bitmask
AUDIO_STATUS    equ     DISKOP_STATUS   ; $E9FC tenant->main: 0 ok / nonzero ERR code
; play_parse_tenant parse scratch -- transient, dead outside a PLAY parse. Reuses
; the DISKOP result cells ($E9FD-FF, audio/disk never concurrent) + the unused
; QUEBAK putback area ($F971-F974, a "TODO purpose" cell in the music work area we
; do not use in 2a). The persistent per-voice state (octave/length/tempo/...) lives
; in the VCBs; the source cursor rides HL and the byte count B during a voice parse.
PLY_NUMOVF      equ     DISKOP_A        ; $E9FD (1): pt_number 16-bit overflow latch
;                 (was PLY_NUM, a 'decimal number-literal accumulator' that NOTHING
;                 referenced -- the accumulator rides HL. D-PLAYCORNER repurposes the
;                 byte: a wrapped number literal must REJECT, not alias into range)
PLY_LASTDUR     equ     $F971           ; QUEBAK+0 (2): saved write pointer across pt_length
PLY_BUFEND      equ     $F973           ; QUEBAK+2 (2): current voice buffer end (overflow guard)
; Queue packet opcodes (own-design; docs spec §6). A voice buffer is a stream of:
PLAY_OP_NOTE    equ     $00     ; + amp:1, tone_lo:1, tone_hi:1, dur:2  (rest = amp 0)
PLAY_OP_ENV     equ     $01     ; + shape:1, per_lo:1, per_hi:1         (S/M envelope)
PLAY_OP_END     equ     $FF     ; end of this voice's queue

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
; D-FCH S-FCH-1 (docs/spec-basic-filechan-alloc.md §3.1): a context block is now
; JUST THE STATE — [state:FCH_STATESZ], no data buffer. It used to be
; [state][buffer:512], i.e. 562 B per channel, of which the 512 was nothing but a
; SAVE COPY of the one global FSECTOR_BUF that the switch memcpy'd in and out.
;
; ⚠️ MEASURED (docs/chancost-cf3300-characterization.md): the reference charges
; **267 B** per channel -- LESS than one sector -- so its sector staging is not
; per-channel at all. It treats the shared buffer as a CACHE: flush on switch
; away, re-read on switch back. That is what fch_save_active/fch_load_ctx now do
; (basic/files.asm), via fch_restage / DISKOP_SEL_FCH_RESTAGE.
;
; A channel's live streaming state spans the contiguous engine-state span
; FCH_STATE0..(+FCH_STATESZ). That span ($E9C9..$E9FA) covers every per-channel
; value — the read iterator (FAT_CURCLUS/FAT_CLUSSEC), file meta
; (FAT_FIRSTCLUS/FAT_FILESIZE for LOF), the read stream (FREAD_OFF/FREAD_LEFT)
; and the whole write state (FWR_*). It also spans a few shared/transient bytes
; (FAT_NUMFATS/FAT_SECPERFAT geometry, the FAT_B0/FAT_BYTEIDX/... scratch) —
; harmless to save/restore (identical across channels on one drive, or dead
; between statements). The mount geometry proper (FAT_SECPERCLUS..FAT_FIRSTDATA
; at $E9C0..$E9C8) sits BELOW the span and stays SHARED — correct for a single
; drive (every fat_mount re-derives it identically).
;
; D-FCH §3.2 (repack): the table is no longer AT a fixed address at all. It is
; CARVED OUT OF THE POOL at MAXFILES time, immediately below the string pool's
; floor, so `MAXFILES=n` costs n*FCH_CTXSZ of FRE(0) exactly as the reference
; charges 267 B/channel out of its own FRE(0) pool (characterization §2/§4/§5):
;
;   channel table base = min(HIMEM,TXTMAX) - POOLSIZE - MAXF*FCH_CTXSZ
;
; DERIVED, NEVER STORED — the same S-CLP-2 discipline strheap_floor uses, and
; for the same reason: the arithmetic lives sub-side (sub/strheap.asm
; strheap_varceil / op 18) where ROM is not scarce, so `CLEAR n`, `CLEAR ,himem`
; and `MAXFILES=n` are all picked up for free by the next derivation.
FCH_STATE0      equ     FAT_CURCLUS         ; $E9C9 — base of the per-channel state span
FCH_STATESZ     equ     FWR_DIROFF+2-FCH_STATE0     ; $E9C9..$E9FA inclusive = 50 bytes
FCH_CEIL        equ     15      ; repack: the MEASURED reference ceiling (§3, exactly
                                ; 15) — free now that unused channels cost nothing
FCH_CTXSZ       equ     FCH_STATESZ         ; repack: block = state ONLY (no buffer)
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
PU_WP           equ     $EEFB   ; pu_fmt_int scratch write pointer (2) -- ALIASED by
                                ; PU_COMMAS / PU_DEC below; see the block there
; 🔴 THE $EED6..$EEFF GAP IS FULL: PU_WP ends at $EEFC and FMT_SEC / FMT_DESC own
; $EEFD..$EEFF. D-PUDOT first put PU_DEC at $EEFE saying "free byte in the same
; gap" -- FALSE, it aliased FMT_DESC, and nothing caught it because RAM HAS NO
; GATE (wall-assertion-check covers ROM only).
;
; Aliasing itself is normal here (scratchpad/rammap_sweep.py: 50 addresses carry
; more than one name). What was wrong was the PARTNER and the unstated argument.
; These two share PU_WP, whose exclusivity is provable in ONE file against ONE
; flag: PU_WP is scratch for `pu_fmt_int`, and basic/printusing.asm reaches
; `pu_fmt_int` only when PU_FLAGS bits 6/7 are BOTH CLEAR -- while these two cells
; are written only by the scanner branches that SET those same bits. A field is
; scanned and then rendered before the next field is scanned, so a later plain
; `#` field cannot reach back into an earlier `##.##` field's count.
; That argument is measured, not asserted: probe row `x.mixed` puts a plain field
; and a `.` field in ONE format string, which is the statement that would break
; if the exclusion ever stopped holding.
; 🔴 PRINT USING RENDERS INTO ITS OWN BUFFER, NOT `NUMBUF`. NUMBUF is EIGHT
; bytes at $E0C0 and is shared with print.asm / list.asm / str-engine.asm, so it
; cannot simply be widened. D-PUCOMMA rendered `12,345,678` into it -- ten
; characters plus a terminator, ELEVEN bytes -- which runs into VALTYP ($E0C8)
; and STRPTR ($E0C9). That shipped, and stayed invisible because both cells are
; rewritten by the next evaluation before anything reads them; RAM HAS NO GATE,
; so nothing could have flagged it either.
;
; The exponent form measured in docs/spec-basic-pufloat.md §14 makes it real
; rather than latent: ` 1234.50E+00` is THIRTEEN bytes with its terminator and
; reaches PRDEST ($E0CB) and PRDEV ($E0CC), which ARE live across the render --
; PRINT# USING reads PRDEST to choose its sink.
;
; This sits in DETOKBUF's tail. That buffer is 1280 bytes and is already the
; established PRINT USING scratch (D-PUEMIT builds the finished field at
; DETOKBUF+0), so both are live at once and cannot collide: a field is bounded by
; PU_FMTMAX, far below the 256-byte offset here.
PU_NUM          equ     DETOKBUF + 256      ; PRINT USING numeric render buffer,
                                            ; 32 bytes, 0-terminated
PU_DIG          equ     DETOKBUF + 512      ; D-PUEXP: the significant digits of
                                            ; flt_fmt's text, point removed, 32 B
PU_COMMAS       equ     $EEFB   ; PRINT USING `,`: commas to insert (D-PUCOMMA) (1)
PU_DEC          equ     $EEFC   ; PRINT USING `.`: decimal places requested (D-PUDOT) (1)
; CALL FORMAT loop counter — the current sector being written. write_sector's CALSLT
; clobbers every register, so the format loop keeps its position here in RAM. One byte
; ($EEFD) in the gap below FLD_DESC. Repack eviction (docs/spec-evict-call-format.md):
; the sub-ROM page-1 tenant owns these two cells (it runs the build/write loop).
; They are RAM, always visible. See basic/format.asm / basic/format-body.inc / sub/format.asm.
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
; ⚠️ D-FCH §3.2: with FCH_CEIL=15 the repack array is 32 B and would run over
; GP_RECLEN/OO_RECLEN_CHAN/FILES_HASPAT/CAS_WANT at $F006..; it moves into the
; same freed $EA00 page-3 window as FCH_MODES.
FCH_RECLENS     equ     $EA10   ; 32 B ($EA10..$EA2F); $EA92..$EAFF free (110 B)
                                ; ⚠️ THIS LINE READ "$EA39..$EAFF free" UNTIL
                                ; D-FORVAR, AND IT WAS ONE BYTE STALE: D-LPTVERB
                                ; took $EA39 for LPTPOS and never updated it. A
                                ; comment claiming free RAM is a claim like any
                                ; other, and this one was measured before it was
                                ; spent. D-FORVAR then took $EA3A..$EA92 for the
                                ; relocated FOR stack (see FOR_STK above).
                                ; (D-EDITVERB took $EA30..$EA38: the RENUM
                                ; round-trip cells RN_PTR/RN_NEW/RN_OLD/RN_INC
                                ; and read_line's RL_AUTO mode flag)
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
; CAL_BUF2: the double buffer's SECOND 256-byte block buffer (see CAL_CURHI above).
; Page-aligned at $E800, entirely inside the idle FWBUF ($E7C0..$E9BF, FAT/dir
; metadata scratch) -- a cassette ASCII load does no disk I/O, so FWBUF is as dead
; for it as FSECTOR_BUF (CAL_BUF's home) is. CAL_XORHI is the constant that recovers
; "the other buffer" from CAL_CURHI without extra RAM: CAL_BUF>>8 XOR CAL_BUF2>>8 --
; XORing either buffer's own high byte into it yields the other one.
CAL_BUF2        equ     $E800   ; cassette ASCII load: 256-byte read-ahead buffer (in idle FWBUF)
; pasmo has no XOR operator in EQU expressions, so this is the literal result of
; ($E6 XOR $E8): CAL_BUF>>8 is $E6 (1110_0110), CAL_BUF2>>8 is $E8 (1110_1000);
; XORed, the shared high bits cancel and $0E (0000_1110) is what's left.
CAL_XORHI       equ     $0E     ; = (CAL_BUF>>8) XOR (CAL_BUF2>>8)
; Cassette ASCII SAVE (save.asm cas_wbyte / cas_flush_block) uses the SAME 256-byte
; buffer for the WRITE mirror: list_walk fills it a byte at a time (no tape I/O), and
; a full block is flushed in one tight TAPOUT*256 loop so the inter-byte gaps stay
; uniform. Overlays CAL_BUF at $E600 — a SAVE and a LOAD never run at the same time,
; and both sit in the idle FSECTOR_BUF (no disk I/O during either), below any stack
; descent. Same rationale as CAL_BUF above.
CAS_WBUF        equ     $E600   ; cassette ASCII save: 256-byte tape block buffer (overlays CAL_BUF)
; Control stacks. Both grow upward; the pointer addresses the next free slot,
; and the stack is empty when it equals its base. GOSUB frame =
; [curline:2][resume:2] (4 bytes). FOR frame =
; [name0:1][name1:1][type:1][limit:2][step:2][curline:2][resume:2] (11 bytes).
;
; D-FORVAR (docs/spec-basic-forvar.md §4.1/§4.6): the FOR frame's variable field
; was ONE character. Both references match a NEXT on the loop variable's whole
; identity -- both significant name characters AND the resolved type (row
; n.xtype: `FOR A%=1 TO 3` / `NEXT A` is NEXT without FOR) -- so the field is now
; the same (name0, name1, type) triple var_find_typed keys on, and the frame is
; 11 bytes.
;
; 🔴 AND THAT IS WHY THE FOR STACK LEFT THIS PAGE. 8 frames x 11 = 88 B does not
; fit at $E070 (DATASTATE is at $E0B8) and page $E0 is otherwise full, so the
; honest choices were "relocate the stack" or "6 nested loops instead of 8". Row
; f.dep8 (8 nested FOR/NEXT pairs, OK on all three sides) is what makes that a
; measurement rather than a preference. $E070..$E0B8 -- 72 B of this crowded
; page -- is now FREE.
; 🎯 D-CTLPOOL (docs/spec-basic-trapsvc.md §11-§16): THESE ARE POINTERS INTO ONE
; DESCENDING POOL, not indices into three fixed arrays. The pool runs DOWN from
; CTLTOP -- which is `strheap_varceil()`, the SAME address the reference publishes
; as STKTOP (§14 measured the two formulas identical) -- and collides with the
; variable/array region at ARYEND+2. That is what makes the reachable depth
; respond to `CLEAR` and to HIMEM at all, which is §11's whole finding.
;
;   [PRGEND+2 .. ARYEND+2)  variables + arrays, growing UP
;        [ the free gap ]
;                            control frames, growing DOWN   <- CSP
;   CTLTOP = strheap_varceil()
;   [varceil .. floor)      the MAXFILES channel table
;   [floor .. C)            the string pool          C = min(HIMEM,TXTMAX)
;
; 🔴 FSP IS THE `FOR` RUN'S **FLOOR**, NOT AN INDEX. The FOR frames a `NEXT` may
; match are exactly [CSP, FSP) -- everything pushed since the last non-FOR frame.
; That is not a convenience: D-CTLCROSS (§12) measured that BOTH references
; refuse to match a `FOR` frame lying below a live GOSUB frame, and this is the
; invariant that reproduces it with no per-frame type tag and no walk.
GSP             equ     $E041   ; newest GOSUB frame's address; == CTLTOP if none (2)
FSP             equ     $E043   ; the FOR run's FLOOR: FOR frames are [CSP,FSP) (2)
FOR_FRAME       equ     11      ; FOR frame size, in bytes (see the layout above)
FOR_CUR         equ     $E045   ; scratch: a working copy of one FOR frame (11), and
                                ; ALSO the key a NEXT parses into before it matches
                                ; (spec §4.3 -- nx_have only writes it after the
                                ; match, so the two uses cannot collide). Ends at
                                ; $E04F: exactly the span the retired FOR_NEW frees,
                                ; so GOSUB_STK below is untouched.
; $E04E was FOR_NEW — NEXT's freshly-stepped loop value, parked in RAM across the
; var_set call. D-FORVAR keeps it on the STACK instead (one push/pop replaces one
; store and two loads on mutually exclusive branches), and FOR_CUR grew over it.
; D-CTLPOOL: $E050.. held GOSUB_STK (8 x 6 B). The array is retired; these six
; bytes are the pool's own pointers and $E058..$E080 is FREE.
CSP             equ     $E050   ; the pool's allocation frontier, descending (2)
CTLTOP          equ     $E052   ; the pool's TOP = strheap_varceil(), cached (2)
TSP             equ     $E054   ; newest trap SERVICE record; valid iff TRAPSVC != 0 (2)
CTLLIM          equ     $E056   ; the pool's collision FLOOR = ARYEND+2 (2). Written
                                ; sub-side by strheap_ctllim at the two allocator
                                ; success paths and at reset; read by the main ROM's
                                ; ctl_alloc on every push. ARYEND needs an array-chain
                                ; walk (sub-ROM knowledge) and a push cannot afford a
                                ; subrom_call -- `FOR I=1 TO 1000:GOSUB 100:NEXT`
                                ; pushes a thousand times. 🔴 A STORED DERIVATION,
                                ; therefore a staleness hazard; §17 of
                                ; docs/spec-basic-trapsvc.md is its gate.
; ⚠️ CTLTOP IS THE ONE STORED DERIVATION HERE, and it is bounded on purpose. Its
; inputs (POOLSIZE, HIMEM, MAXF) change only at `CLEAR` and `MAXFILES`, and
; `clear_vars` -- the four-site hook (cold boot, RUN, NEW, CLEAR) -- rewrites it
; there. Everything else (the collision floor, which moves on EVERY variable
; allocation) stays DERIVED, sub-side, exactly as strheap_floor's own comment
; argues. 🔴 §14 measured that `MAXFILES` moves the reference's stack top too, so
; the dependency is faithful rather than an artefact -- but a `MAXFILES` with
; frames already live is a staleness window this cell does not close.
GOSUB_FRAME     equ     8       ; [CURLINE:2][resume:2][prevGSP:2][prevFSP:2].
                                ; prevGSP chains the GOSUB frames (they are no
                                ; longer contiguous -- FOR frames interleave), and
                                ; prevFSP is D-FORRET's field under its new name:
                                ; restoring it discards every FOR opened since the
                                ; GOSUB (docs/spec-basic-forret.md §4). Both are
                                ; needed; neither is derivable from the other.
TRAP_FRAME      equ     3       ; [prevTSP:2][idx:1] -- see TRAPSTK's retirement above
; $E056..$E080 is FREE (was the rest of GOSUB_STK), and so is $E080..$E0B8.
; $EA3A..$EA92 (88 B) is FREE: it was FOR_STK, retired with the same arc.
FOR_STK_END     equ     $EA92   ; RETIRED AS A STACK; the literal survives ONLY as
                                ; FN_BASE's anchor below, which must not move.
; --- DEF FN: the parameter (shadow) area -----------------------------------
; D-DEFFN (docs/deffn-design-2026-08-22.md §2, docs/deffn-ramhunt-2026-08-22.md).
; The formal parameters of the FN call in progress live here, NOT in the
; variable table: `X=5 : P=VARPTR(X) : DEF FNA(X)=PEEK(P)` reads 5 on both
; references, so the real cell is never written (design §1) -- the formal is a
; SHADOW CELL only the defining function's own body sees.
;
; 🎯 THE CEILING IS A DIVISION, NOT A RULE. The reference's shadow sits 3 bytes
; into a 100-byte block and 100/11 = 9, which is the measured 9-formal ceiling
; (o.p9 -> 1, o.p10 -> ERR 5 AT THE CALL). So this sizes the AREA from the window
; and lets FN_MAXP fall out of the same division; nothing here hardcodes 9. A
; slot is shaped EXACTLY like a scalar chain entry -- [name0][name1][type]
; [value:2/4/8] -- which is what lets sub/arrays.asm's scv_find hand one back to
; var_load_fac / var_store_fac / str_get_key / str_set_key unchanged.
;
; ⚠️ THE WINDOW IS $EA92..$EB00, 110 B, MEASURED not read: no name in basic/,
; sub/ or disk/ claims it (scratchpad/rammap_sweep.py) and 14 of 14 empirical
; rows -- a FULL FOR stack and a NINTH frame, GOSUB, the crunch, PAINT, DRAW,
; PLAY's ISR, strings, a disk write round trip, FILES -- changed 0 bytes of it
; (scratchpad/ramfree_probe.py). Page 3, always mapped, so a sub-ROM CALSLT can
; read it: that is what lets the shadow lookup live in the ARY tenant and cost
; the main ROM nothing.
; 🔴 THE THREE CELLS COME FIRST, AND THAT IS A FIX, NOT A STYLE CHOICE. A
; nested call saves only the LIVE prefix of the frame -- 3 bytes at top level
; instead of 102, which is what keeps a plain `FNA(2)` off a Z80 stack this
; machine has a few hundred bytes of. That save is ONE `ldir`, so the cells and
; the live prefix have to be CONTIGUOUS from a fixed base. Put the cells above
; the area and they are not: the copy then runs from FN_PAREA for
; `used + 3` bytes and takes the first three bytes of SLOT 0 instead of the
; cells, so FN_FEND/FN_SLOTP/FN_RTYPE are never restored at all. Cells first,
; area second, and one base address covers both.
; 🔴 D-DEFFNEV: THE TENANT ABI CELLS ARE PART OF THE FRAME, AND A NESTED CALL IS
; WHAT SAYS SO. The draft kept the parse state in registers and on the Z80 stack,
; where nesting takes care of itself. A tenant cannot: a CALSLT is not resumable,
; so the phase, both cursors and the pending formal all have to live in RAM --
; and `DEF FNB(X)=FNA(X+1)+X` evaluates FNA's actual IN THE MIDDLE of FNB's own
; parse, through eval, through a second fn_call. Left above the area these five
; cells would be outside the saved prefix and the inner call would eat them.
; They go at the BOTTOM, inside FN_CELLS, so ONE `ldir` from FN_BASE carries
; them exactly as it carries FN_FEND/FN_SLOTP/FN_RTYPE. o.nestsame is the row.
; ⚠️ The price is 8 more bytes of Z80 stack per NESTED call (11 saved, not 3);
; a top-level FNA(2) still saves 11 rather than the 110 a fixed block would.
FN_BASE         equ     FOR_STK_END     ; $EA92: base of the whole DEF FN frame
FN_PTR          equ     FN_BASE         ; 2 B: the call cursor, main <-> tenant
FN_DPTR         equ     FN_BASE + 2     ; 2 B: the definition cursor, tenant-only
; ⚠️ THERE IS NO `FN_REQ` CELL, AND THERE WAS: the request/answer byte travels
; in **L** through CALSLT instead (basic/deffn.asm fn_lp). "A CALSLT is not
; resumable, so the phase lives in RAM" is true of the TENANT's state and false
; of the SERVICER's -- the servicer is ordinary main-ROM code holding an
; ordinary register across a `call`, and an inner fn_call runs entirely inside
; the outer one's `call eval`, which sets L again on the way back. -7 B of main
; ROM at three sites, and one byte back here.
FN_KEY          equ     FN_BASE + 4     ; 2 B: the formal (or the $FFFF result slot)
FN_TYP          equ     FN_BASE + 6     ; 1 B: its type -- and the ERR code on req 0
FN_FEND         equ     FN_BASE + 7     ; 1 B: low byte of one-past the live frame.
                                        ; == low FN_PAREA means "no FN call in
                                        ; progress" -- the fast miss every ordinary
                                        ; variable reference takes.
FN_SLOTP        equ     FN_BASE + 8     ; 1 B: low byte of the slot the NEXT formal takes
FN_RTYPE        equ     FN_BASE + 9     ; 1 B: the FN's own resolved type (its result type)
FN_CELLS        equ     10              ; ...the ten above, saved WITH the live prefix
FN_PAREA        equ     FN_BASE + FN_CELLS  ; the shadow-parameter slots themselves
FN_SLOTSZ       equ     11              ; [name0][name1][type][value:8] -- a scalar entry
FN_AREA         equ     ((LINEBUF - FN_PAREA)/FN_SLOTSZ)*FN_SLOTSZ
FN_MAXP         equ     FN_AREA/FN_SLOTSZ   ; the ceiling IS this division (9)
FN_PAREA_END    equ     FN_PAREA + FN_AREA
FN_BLK          equ     FN_CELLS + FN_AREA  ; the whole frame, cells first
; --- FN_STK_FLOOR: the Z80-stack floor a nested FN call refuses to cross -----
; `DEF FNA(X)=FNA(X)` is ERR 7 Out of memory on both references (b.recurse), and
; a recursion that saves an outer frame on the Z80 stack has to have SOME floor
; or the answer is a wrecked machine instead. Compared HIGH BYTE ONLY -- page
; granularity is all this needs and it costs 6 bytes instead of 12. $F200 is
; clear of every private sysvar (the highest is the SQRT block around $F194) and
; leaves ~384 B below the $F380 stack base tests/msxtest.py and the runaway
; sweep both measure.
; ⚠️ NOT AN ORACLE FIGURE. The references' own limit is unmeasured -- b.recurse
; says ERR 7, not at what depth. What IS pinned is that the LEGAL depths in the
; row set (2, at b.nested / o.nestsame / z.addr2i) work and unbounded recursion
; does not.
FN_STK_FLOOR    equ     $F200
; ⚠️ THE ASSERTS SHIP WITH THE ALLOCATION, NOT AFTER IT. The last RAM obstacle
; this verb hit was a BUILD ERROR rather than a probe reading garbage out of the
; PLAY parser's stack only because the draft carried its own page-crossing
; assert (docs/deffn-design-2026-08-22.md §7(2)). Both survive here.
    IF FN_BASE + FN_BLK > LINEBUF
                db      FN_PARAM_AREA_OVERRAN_LINEBUF
    ENDIF
    IF (high FN_BASE) != (high (FN_BASE + FN_BLK - 1))
                db      FN_PAREA_CROSSES_A_PAGE__8BIT_SLOT_WALK_WOULD_CARRY
    ENDIF
; D-CTLPOOL: FOR_STK is retired, so this no longer guards a live stack -- but
; FN_BASE is PINNED at $EA92 and the assert is what says so out loud.
    IF FN_BASE != $EA92
                db      FN_PAREA_MOVED__FN_BASE_IS_PINNED_AT_EA92
    ENDIF
    IF FN_MAXP < 9
                db      FN_PARAM_CEILING_BELOW_THE_MEASURED_NINE
    ENDIF
; DATA / READ / RESTORE state. The reference stores DATA items as verbatim ASCII
; text (oracle: `data 5,6` -> $84 $20 '5' ',' '6'), so READ parses ASCII from the
; stored program at run time and a DATA cursor walks the $84-tagged statements.
DATASTATE       equ     $E0B8   ; 0 = unpositioned (RESTORE), 1 = ready, 2 = exhausted
DATAPTR         equ     $E0B9   ; next unread DATA item (ASCII) in the program (2)
DATALINE        equ     $E0BB   ; link-field of the line holding DATAPTR (2)
RESTORE_LINE    equ     $E0BD   ; link-field a READ seeks DATA from when unpositioned (2)
; $E0BF was READVAR — the ONE letter ex_read latched as its target name. D-READVAR
; (docs/spec-basic-readvar.md) routes READ's target through var_name_key, which
; carries the whole (name, suffix) key in BC across the DATA read, so there is no
; name to stash. The byte is FREE; it is left named here rather than reused so the
; map above stays contiguous with the $E010-$E0FF audit recorded below.

; --- Math float pack, slice F1 RAM (repack build only) ----------------------
; docs/spec-basic-float-core.md §9.4 suggests FACTYP $E0BB / TKOVF $E0BC /
; FAC $E0C8 / FOUTBUF $E0D0 / TKDIG $E0E8, but every byte of $E010-$E0FF is
; ALREADY claimed (verified against this file 2026-07-11): DATALINE/
; RESTORE_LINE own $E0BB-$E0BE (+ the byte $E0BF that READVAR held until
; D-READVAR retired it, still not re-let), VALTYP/STRPTR/PRDEST/PRDEV/
; OO_DEVTYPE/ARL_GETBYTE own $E0C8-$E0CF, and CONTLINE/CONTPTR/CONTVALID/
; SCAN_*/DISK_FCB/DISKSLOT* own $E0D0-$E0E8 — none of it is free. Genuinely
; free own-choice RAM instead: the window starting at $F01A, between basic's
; own last claim (CAS_VMIS $F019 above) and zerobas-disk's first resident
; claim (DRVA_DPB $F195, disk/init.asm) — neither component's scratch reaches
; into it, and it sits below HIMEM ($F380, the documented top of BASIC-usable
; RAM; see TODO.md §8.19-8.20 / disk/docs/provider-oracle-scope.md §8.20,
; "HIMEM $F380 = the no-disk baseline"), so it is legitimate low RAM whether
; or not zerobas-disk is present in the combined machine. "own choice — free
; RAM" (like every other cell in this section), just relocated off the
; spec's suggested addresses to avoid the collision.
FACTYP          equ     $F01A   ; 2=int / 4=single / 8=double (1)
TKOVF           equ     $F01B   ; tokeniser: 0 = ok, else the ERR CODE of the
                                ; crunch-time reject -- 6 float literal, 25 body
                                ; too long. dl_overflow stores it into ERRFLG
                                ; unconditionally (D-MSGMIGRATE) (1)
FAC             equ     $F01C   ; float accumulator: value bytes as tokenised (8)
FOUTBUF         equ     $F024   ; flt_out formatter output scratch (24)
TKDIG           equ     $F03C   ; tokeniser/formatter: significant-digit array,
                                ; one decimal digit value (0-9) per byte (24)
; tk_float single-literal scan state (own choice — free RAM; transient, dead
; between literals). See sub/tkfloat.asm tk_float for field semantics (the crunch
; was evicted to the sub-ROM; this pointer said basic/float.asm until 2026-08-30).
TKPOS           equ     $F054   ; running digit-position counter (1)
TKINTLEN        equ     $F055   ; integer-part digit count = P (1)
TKHAVESIG       equ     $F056   ; 1 once the first nonzero digit is seen (1)
TKNZPOS         equ     $F057   ; position of the first nonzero digit = f (1)
TKDCOUNT        equ     $F058   ; classification digit count = D, saturating (1)
TKSTORED        equ     $F059   ; digits actually written to TKDIG, capped 24 (1)
TKFLAGS         equ     $F05A   ; bit0=dot bit1=exp bit2=expD bit3=! bit4=# bit5=% (1)
TKEXP           equ     $F05B   ; signed explicit exponent, saturated +-9999 (2)
TKEXPD          equ     $F05D   ; 1 = the exponent marker being parsed is D/d (1)
TKEXPSIGN       equ     $F05E   ; 1 = the exponent being parsed is negative (1)
TKPC            equ     $F05F   ; target precision digit count: 6 / 14 (1)
TKDEXP          equ     $F060   ; signed dec_exp, pre-/post-round (2)
TKLEAD          equ     $F062   ; computed lead byte (sign+excess-64 exponent) (1)
; flt_out formatter scratch (own choice — free RAM; transient, dead between
; PRINT items). TKPC/TKDEXP/TKDIG above are reused here too — flt_out never runs
; concurrently with tk_float.
; 🔴 AND THE REASON FOR THAT CHANGED ON 2026-08-30. It used to be "tokenising a
; line always finishes before any statement, including PRINT, executes", and
; D-VALFLT MADE THAT SENTENCE FALSE: `VAL` calls tk_float AT STATEMENT TIME, from
; inside an expression that a PRINT is very likely to be formatting. The
; conclusion survives, for a different and stronger reason — the two never
; INTERLEAVE, because neither can reach the other:
;   * tk_float calls only its own tkf_* helpers plus the sub-local `upcase` /
;     `cmp16_bits` clones. It never reaches the evaluator or PRINT, so no flt_out
;     can start inside a scan.
;   * flt_out/flt_fmt calls only flo_* plus cmp16_bits and print_string. It never
;     reaches VAL, so no scan can start inside a format.
; So every use is a COMPLETED call, and the cells are dead across the boundary in
; both directions. D-STRFLT (str_fn_str calling flt_fmt directly) is the closest
; the two now come, and it is still strictly sequential: VAL finishes, then the
; formatter runs.
; ⚠️ THE OLD SENTENCE WAS TRUE WHEN WRITTEN, AND THE ITEM THAT PREDICTED ITS
; DEATH SAID SO IN ADVANCE. Recorded rather than quietly edited, because the next
; reader would otherwise inherit "tokenising finishes before statements run" as a
; live invariant about this machine, and it is not one any more.
; [[a-fix-falsifies-the-justification-beside-it]]
; D-VALFLOAT: the VAL-mode SOURCE BOUND for tk_float, aliased onto two of the
; formatter's own cells. FOSIGCOUNT/FOMBYTES are written ONLY by flt_out
; (`basic/float.asm`) and appear ZERO times in `sub/tkfloat.asm`, so they are
; dead for the whole of a tk_float scan -- the same sharing argument the block
; above already makes for TKDIG/TKPC/TKDEXP, applied in the other direction.
; 0 = no bound (ordinary tokenising); otherwise the first address PAST the
; source. `tokenise` clears it on entry, so only VAL can ever set it.
TKVALEND        equ     $F064   ; VAL-mode source bound, 0 = unbounded (2)
FOSIGN          equ     $F063   ; 0 / $80 = the value's sign bit (1)
FOSIGCOUNT      equ     $F064   ; significant digit count = s, trailing zeros
                                ; stripped (1)
FOMBYTES        equ     $F065   ; mantissa byte count: 3 (single) / 7 (double) (1)
; tk_float's own final-encode helpers (tkf_int_value/tkf_calc_and_round/
; tkf_emit_mantissa) all use HL as scratch to walk TKDIG -- but HL is also
; tk_float's LIVE SOURCE CURSOR, which tk_loop needs back, unclobbered, the
; moment control returns to it. TKSRCSAVE parks the post-scan source cursor
; across those calls (own choice — free RAM; simpler and less error-prone
; than juggling stack push/pop order against the also-stacked TOKBUF dest
; cursor). See tkf_classify / the tkf_go_int / tkf_single / tkf_double tails.
TKSRCSAVE       equ     $F067   ; (2)

; --- Math float pack, slice F2 RAM (repack build only) ----------------------
; docs/spec-basic-float-core.md §10. Own-choice free RAM, same rationale as the
; F1 block above: the window from $F069 (right after TKSRCSAVE) up to DRVA_DPB
; ($F195, disk/init.asm) is unclaimed by any other component. F2's BCD
; arithmetic core works over UNPACKED digit arrays (one decimal digit value
; 0-9 per byte, not the packed-BCD FAC/TKDIG convention) — deliberately
; separate scratch from TKDIG/FOUTBUF (tokeniser/formatter) per the brief, so
; a PRINT of an arithmetic result mid-tokenise (never actually concurrent, but
; keeping the scratch spans disjoint avoids ever having to reason about it).
;
; FPNUM record layout (18 bytes), shared by ARGA/ARGB/RES: a sign-magnitude
; double float held as [sign:1][dexp:2 signed][dig:15] where dig[0..13] are
; the 14 significant BCD digit VALUES (0-9, MSD first) and dig[14] is a guard
; digit used mid-computation for half-up rounding (spec §10.2) — own design,
; unpacked-digit-array representation chosen so add/sub/mul/div can be
; expressed as ordinary byte arithmetic (no nibble packing) with Z80 LDIR/LDDR
; doing the alignment/normalisation shifts.
FPNUM_SIGN      equ     0       ; field offset: 0/$80 (1)
FPNUM_DEXP      equ     1       ; field offset: signed dec_exp (2)
FPNUM_DIG       equ     3       ; field offset: digit array, 14 sig + 1 guard (15)
FPNUM_SIZE      equ     18

FPERR           equ     $F069   ; runtime numeric-error flag: 0 none / 1 overflow /
                                ; 2 division by zero (spec §10.2 D-F2-1) / 3 illegal
                                ; function call (math pack slice 1b, SQR(x<0),
                                ; spec-basic-math-pack.md §10.4/§10.5 -- same
                                ; disposition idiom, new value) / 4 syntax error
                                ; (empty parenthesised/argument expression, D-F2-3,
                                ; spec-basic-empty-expr-syntax-error.md) (1)
; ARGA doubles as the WORKING/RESULT record: fp_add/fp_sub/fp_mul/fp_div all
; produce their answer back into ARGA in place (its own operand digits are
; dead once the op's own algorithm has consumed them), so a separate RES
; record isn't needed -- one less buffer, one less "which one is the answer"
; bookkeeping question. round_and_finalize (float-arith.asm) always reads/
; writes ARGA.
ARGA            equ     $F06A   ; operand A / working result, FPNUM record (18)
ARGB            equ     $F07C   ; operand B, FPNUM record (18)
MULPROD         equ     $F08E   ; fp_mul: 28-digit product (14x14), MSD first (28)
DIVPAD          equ     $F0AA   ; fp_div: divisor zero-padded to 15 digits (15)
DIVREM          equ     $F0B9   ; fp_div: running remainder, 15 digits (15)
CVT             equ     $F0C8   ; fac_to_int_strict/addr + flt_to_int16 (float.asm)
                                ; shared unpack scratch, FPNUM-shaped (18)
LHS_FACTYP      equ     $F0DA   ; ev_e/ev_t binary-op sites: the LHS operand's FACTYP,
                                ; popped off the machine-stack frame (spec §1 bullet 4:
                                ; "fixed lhs frames live on the machine stack, not RAM")
                                ; into RAM so the widening loaders can address it (1)
LHS_FAC         equ     $F0DB   ; ...and the LHS operand's raw FAC bytes (8)
; Small general scratch cells, own choice — free RAM, grouped so each use is
; documented once instead of at every call site (float-arith.asm headers name
; which routine owns which cell at the point of use).
FP_SHIFTAMT     equ     $F0E3   ; dig15_shr/dig15_shl: shift-amount parameter (1)
FP_LHSVAL       equ     $F0E4   ; combine_*: the LHS operand's plain int16 value,
                                ; stashed off the machine stack (2)
FP_TMP_B        equ     $F0E6   ; combine_*: the RHS operand's plain int16 value,
                                ; stashed so it survives a widen_* call (2)
FP_RSIGN        equ     $F0E8   ; signed_div_de_bc/signed_mod_de_bc: result sign (1)
WIDIG           equ     $F0E9   ; widen_int_to: binary->BCD digit scratch, up to
                                ; 5 decimal digits (32768 max magnitude) (5)
MUL_I           equ     $F0EE   ; fp_mul: outer-loop digit index i, 13 downto 0;
                                ; widen_int_to: digit count N, 0..5 (shared, dead
                                ; between uses) (1)
MUL_ADIG        equ     $F0EF   ; fp_mul: A[i], the current outer-loop digit (1)
MUL_CARRY       equ     $F0F0   ; fp_mul: running carry within one outer pass;
                                ; fp_div's fpd_trial_digit: trial-subtract count
                                ; (shared, dead between uses) (1)
MUL_PP          equ     $F0F1   ; fp_mul: MULPROD write-cursor for the inner loop (2)
MULCAND         equ     $F0F3   ; mul16x16_32: multiplicand operand (2)
MULTPLR         equ     $F0F5   ; mul16x16_32: multiplier operand, shifted in place (2)
MUL32           equ     $F0F7   ; mul16x16_32: 32-bit unsigned product, LE
                                ; (low16 then high16) (4)
WSRC            equ     $F0FB   ; widen_fac_to/widen_lhsframe_to (shared unpack
                                ; body): address of the source's lead+mantissa
                                ; bytes, FAC or LHS_FAC (2)
WSRC_TYP        equ     $F0FD   ; ...and the address of its type byte, FACTYP
                                ; or LHS_FACTYP (2)
FP_OPMODE       equ     $F0FF   ; combine_add/combine_sub shared body: 0=add,
                                ; 1=sub (1)
CVT_MODE        equ     $F100   ; domain_convert_core: 0=strict int16 domain,
                                ; 1=address domain (1)
PLF_RA          equ     $F101   ; pop_lhs_and_probe: scratch home for its own
                                ; "call"-pushed return address (2)
PLF_RA2         equ     $F103   ; ...and for its DIRECT caller's (combine_add/
                                ; sub/mul/cmp/div_float's own) "call"-pushed
                                ; return address, which sits ON TOP of the
                                ; persistent lhs frame too -- every combine_*
                                ; is itself reached via a plain "call" from an
                                ; ev_* site AFTER push_lhs_frame already ran,
                                ; so ITS return address is in the way exactly
                                ; like pop_lhs_and_probe's own (own design,
                                ; see pop_lhs_and_probe's header comment).
                                ; Neither is a register, since DE (and BC)
                                ; must stay live across the call for the
                                ; combine_* callers (2)
; --- sub-ROM dispatch (subrom S2b, docs/spec-basic-subrom.md §3c/§3g) ---------
; Recorded by init_ext_roms' page-0 CD scan; read by subrom_call at dispatch.
; SUB_PING ($F105, sub/equates.inc) is the S2a injection-gate cell and is not
; referenced by main-ROM code; SUBSLOT/SUBSLOT_OK are the private dispatch path
; (decoupled from EXBRSA $FAF8, which a stray program could clobber — D-6/R4).
SUBSLOT         equ     $F106   ; slot id of zerobas-sub (bit7 exp | 3-2 | 3), 1
SUBSLOT_OK      equ     $F107   ; 1 = a CD sub-ROM was found and recorded, else 0
DB_CUR          equ     $F108   ; wave-3 detok: the DETOKBUF write cursor, held across
                                ; the whole sub-side walk (the core clobbers DE/HL, so
                                ; the cursor cannot live in a register). Own-choice free
                                ; RAM, the $F108.. tail of the $F01A-$F194 window (below
                                ; DRVA_DPB $F195); idle outside a LIST/ASCII-SAVE. (2)
; --- interrupt trampoline (subrom trampoline slice, docs/spec-basic-subrom-trampoline.md) ----
; Lets a page-0 sub-ROM tenant run EI. The sub-ROM's own $0038 does `jp SUB_INT_RAM`,
; a RAM-resident stub (page 3 stays mapped through any page-0 switch) that maps the
; MAIN (BIOS) slot back into page 0, `call $0038` the real ISR (VDP ack, JIFFY++,
; H.TIMI/H.KEYI), then maps the sub-ROM back and RETIs to the tenant. Installed at boot
; by sub_int_install (basic/subromcall.asm) when SUBSLOT_OK. These cells are permanent
; (unlike the transient DB_CUR), so they take fresh RAM above it. HOST ASSUMPTION: the
; main page-0 slot is UNEXPANDED (slot 0 on the merged machine), so only its $A8 primary
; field is toggled — mirrors disk/init.asm page0_ram_in's single-slot philosophy. The
; stub is the SAME technique the BIOS uses for CLPRIM ($F38C, the RAM inter-slot call
; primitive); these cells sit at $F10A.. — well below the C-BIOS sysvar/primitive area
; (RDPRIM/WRPRIM/CLPRIM $F380+ and the C-BIOS stack), so there is no collision.
SUB_INT_RAM     equ     $F10A   ; the copied trampoline stub (<= 64 B; executes from RAM)
INT_MAIN_PRIM   equ     $F14A   ; page-0 primary field of the MAIN (BIOS) slot (=0)
INT_SUB_PRIM    equ     $F14B   ; page-0 primary field of the sub-ROM slot (=3, slot 3)
INT_SUB_SUBSL   equ     $F14C   ; page-0 subslot  field of the sub-ROM slot (=2, i.e. 3-2)
SUB_INT_DELTA   equ     $F14D   ; self-test tenant result: JIFFY ticks observed under EI (1)
; --- Math pack slice 2e RND_SEED (repack build only, docs/spec-basic- -------
; mathpack-slice2.md §15.3): the RND generator's persistent 14-digit LCG
; state, packed BCD (2 digits/byte, MSD-first -- same nibble convention as
; arga_pack_fac's own FAC-mantissa packing), 7 bytes. It must survive
; arbitrary statements between calls, so it cannot reuse transient math
; scratch (unlike fp_rnd's own working cells below) -- but RAM below
; DRVA_DPB ($F195) is exhausted (SQRT_POW10 took the last free byte, see the
; F3 S3a block's own header below). Placement: the TAIL SLACK of the
; SUB_INT_RAM trampoline reservation above. The copied stub
; (sub_int_template, basic/subromcall.asm) is currently 47 bytes, but its
; reservation runs a conservative 64 B ($F10A..$F149) so future trampoline
; growth has headroom -- RND_SEED claims 7 bytes of that UNUSED tail
; ($F142..$F148), safely below $F149 and clear of INT_MAIN_PRIM ($F14A)
; above. Safe-by-construction: subromcall.asm carries a build-time ASSERT
; (`sub_int_template_end - sub_int_template <= RND_SEED - SUB_INT_RAM`,
; currently 47<=56) right after sub_int_template_end, so any future
; trampoline growth that would collide with RND_SEED FAILS THE BUILD loudly
; instead of silently overlapping. Reset to packed(S0) by clear_vars
; (basic/vars.asm), the same single hook DEFTBL's own reset uses (covers
; NEW/CLEAR/RUN + cold boot, §15.1/§15.3).
RND_SEED        equ     $F142   ; packed BCD, MSD-first, 7 bytes (-> $F148)
; --- Math float pack, slice F3 S3a RAM (repack build only) ------------------
; docs/spec-basic-float-core.md §11. Own-choice free RAM, same rationale as the
; F1/F2 blocks above: $F14E.. is unclaimed free RAM below DRVA_DPB ($F195,
; disk/init.asm) and above SUB_INT_DELTA (permanent, not transient like DB_CUR).
VARTYPE         equ     $F14E   ; var_name_key: the RESOLVED type (2/4/8) of the
                                ; just-parsed name's suffix (unsuffixed -> 8,
                                ; hardcoded double in S3a; the per-letter DEFtbl
                                ; override is S3b, not here). Read by ev_f_var/
                                ; ev_f_varptr/ex_let right after var_name_key (1)
VS_TARGET_TYPE  equ     $F14F   ; var_store_fac/var_alloc_or_find (vars.asm):
                                ; the target type parameter, stashed across the
                                ; coercion calls that clobber A (1)
VS_INT_VAL      equ     $F150   ; var_store_fac (vars.asm): the coerced int16 value
                                ; (fac_to_int_strict's DE), stashed across the
                                ; var_alloc_or_find call that CLOBBERS DE for its
                                ; own room-check arithmetic, so the int write-back
                                ; sees the value and not leftover VAREND (2)
LHS_VARTYPE     equ     $F152   ; ex_let (interp.asm): the LHS variable's resolved
                                ; type, latched from (VARTYPE) BEFORE eval -- every
                                ; RHS variable factor re-runs var_name_key, which
                                ; overwrites the GLOBAL (VARTYPE), so a cross-type
                                ; assignment (A%=A#) must read this latched copy for
                                ; the var_store_fac target, not the clobbered global (1)
; --- Math float pack, slice F3 S3b RAM (repack build only) ------------------
; docs/spec-basic-float-core.md §11.1. The per-letter DEFtbl: a 26-byte map
; (index name0-'A', A..Z) holding the resolved default type of an UNSUFFIXED
; name of that first letter -- 2 int / 4 single / 8 double / 1 string
; (DEFTBL_STR). Written by DEFINT/DEFSNG/DEFDBL/DEFSTR ranges (ex_deftype,
; usr.asm); consulted at every reference by var_name_key (numeric default type)
; and var_str_type (string vs numeric). Reset to all-8 (double) by clear_vars
; at INIT/RUN.
; ✅ RE-HOMING DECISION: **HONOUR** ($F153 -> the published $F6CA). It used to
; read "own-choice free RAM, the $F153.. tail below DRVA_DPB ($F195)" -- which
; is a SPACE decision, and there was no decision about the standard address.
;   SEMANTICS  SAME-VAR for 25 of 26 bytes, and this REFUTED the source. The
;              `DEFTBL_STR equ 1` sentinel below reads like an own-design 0/1
;              encoding; MEASURED, zerobas' table is byte-identical to the
;              references' -- boot = 26x$08 (double) on all three sides, and
;              `DEFINT A` writes $02 on all three. Exactly ONE value differs:
;              `DEFSTR A` gives $03 on both references and $01 here.
;   OBSERVER   PEEK($F6CA + letter): a variable's default type. The published
;              encoding is a FLOAT TYPE CODE and zerobas already uses it for
;              three of the four codes.
;   COST       ZERO ROM bytes -- every access is `ld hl,DEFTBL` + index/fill.
;              PUB-FREE measured across all 26 bytes.
; ✅ D-DEFSTR (docs/spec-basic-deftbl-strcode.md) CLOSED the one remaining byte:
; DEFTBL_STR is now 3, so all 26 published bytes match both references in every
; measured state. D-REHOME left it alone on the grounds that "3 is also a value
; WIDTH on the numeric side (2/4/8)" -- a real hazard, but NOT the live one. The
; live one was a collision with a STRING code: see DEFTBL_STR just below.
DEFTBL          equ     $F6CA   ; per-letter default-type map, A..Z (26) --
                                ; the PUBLISHED address ($F6CA..$F6E3)
; --- DEFTBL_STR: the DEFtbl's STRING code (namespace P) ----------------------
; ⚠️ TWO NAMESPACES SHARE THESE NUMBERS, AND THEY USED TO SHARE THIS VALUE TOO.
;   P (published, HERE)  the DEFtbl's float type code: 2 int / 3 string /
;                        4 single / 8 double -- what PEEK($F6CA+letter) reads.
;   C (chain, own)       the variable-chain entry's `type` byte, alias ARY_TYPE:
;                        2/4/8 numeric and **1** string, with sub/arrays.asm's
;                        elsize_from_type mapping 1 -> 3 (the [len][ptr] width).
; On the references the two are ONE namespace -- 3 is both the code and the
; descriptor width, so `elsize == type` is an identity and no map exists.
; 🔴 THE OLD VALUE 1 WAS NOT A SENTINEL; IT WAS AN ACCIDENTAL COLLISION WITH C's
; STRING TAG, AND IT WAS MASKING A LIVE MEMORY CORRUPTION. var_get/var_set fed
; this code straight to var_load_fac/var_store_fac, which use it as the chain
; type AND as an `ld c,a` + `ldir` BYTE COUNT: `DEFSTR I:FOR I=1 TO 3` allocated
; a real STRING entry (because 1 == C's tag) and then wrote one byte of FAC over
; its descriptor's `len` field -- PRINT then dumped arbitrary RAM. Because 1 is a
; valid C code the write landed inside a legitimate entry, so it read as a wrong
; VALUE rather than as a crash. Both references raise ERR 13 there.
; Every namespace P -> C crossing is now CHECKED, not coincidental:
;   ev_f_var         -> check_vartype_num (basic/arrays.asm, low region; covers
;                                          ev_f_arr too)
;   FOR/NEXT         -> ex_for's own `cp DEFTBL_STR` (basic/program.asm). The
;                       crossing MOVED there at D-FORVAR: the frame now carries a
;                       type var_name_key resolved rather than a letter for
;                       deftbl_num_type to look up, so the check happens once at
;                       PARSE time -- which is also where both references put it
;                       (`DEFSTR A` / `FOR AB=1 TO 3` is ERR 13, row f.defstr).
;                       deftbl_num_type had no callers left and is deleted.
; 🎯 AND D-FORVAR WIDENED WHAT THE FIRST ONE CATCHES. var_name_key's vnk_dollar
; used to resolve an EXPLICIT `$` suffix to type 8, so `B=1+A$` crossed into the
; numeric road unchecked and silently read the numeric `A` as 0 (` 1 ` here
; against Type mismatch on both references, row x.numstr) -- the identical
; silent-wrong-answer this block describes for the DEFSTR form, in the one form
; D-DEFSTR did not cover. vnk_dollar now writes DEFTBL_STR.
; var_str_type (basic/vars.asm) reads this code RAW and must keep doing so: it
; is used symmetrically by sub/deftype.asm's write and that test, which is the
; whole reason the value can change at all without breaking DEFSTR.
DEFTBL_STR      equ     3       ; an unsuffixed name of this letter is a STRING
                                ; var. A namespace-P code -- NEVER hand it to
                                ; the chain (ARY_TYPE) or to a `ldir` count.
; --- Math pack slice 1a RAM (repack build only) ------------------------------
; docs/spec-basic-math-pack.md §9.2. Own-choice free RAM, the $F16D.. tail
; below DRVA_DPB ($F195), immediately following DEFTBL (ends $F153+26=$F16D).
MC_TYPE         equ     $F16D   ; evmc_sub1 (expr.asm): the operand's FACTYP (4/8),
                                ; stashed across fp_sub's forced-double
                                ; round_and_finalize so INT's post-truncate -1
                                ; adjustment (negative operand, spec §9.2) can
                                ; re-round the exact result back to single when
                                ; the original argument was single (1)
; --- Math pack slice 1b RAM (repack build only) ------------------------------
; docs/spec-basic-math-pack.md §10.4. Own-choice free RAM, the $F16E.. tail
; immediately following MC_TYPE (ends $F16D+1=$F16E). fp_sqrt (sub/sub.asm,
; migrated to the sub-ROM page-1 tenant 2026-07-13 -- docs/spec-basic-subrom-
; mathpack.md; this RAM stays resident, always mapped from either page)
; needs two PERSISTENT FPNUM-shaped operands across its Heron loop -- unlike
; every other fp_* consumer, which widens a fresh ARGA/ARGB right before each
; single op and never needs the value again -- because the iterate (y) and the
; efficiency-normalized argument (x') must survive MULTIPLE fp_add/fp_div
; calls that themselves clobber ARGA/ARGB. Both are kept CANONICAL (guard
; digit dig[14] always 0, i.e. always populated via widen_fac_to/a raw copy of
; an already-canonical record, never a raw copy of a fresh fp_add/fp_div
; result) -- fp_add's dig15_shr/dig15_add_inplace read the FULL 15-byte digit
; array including the guard, so reusing an op's own post-round leftover guard
; digit as if it were real extra precision would silently corrupt the next
; alignment/round (own-design pitfall, caught in this slice's design pass).
SQRT_X          equ     $F16E   ; the efficiency-normalized argument x' (constant
                                ; across the whole iterate loop), FPNUM record (18)
SQRT_Y          equ     $F180   ; the current iterate y (updated once per loop
                                ; pass, canonical/clean per the note above),
                                ; FPNUM record (18). REUSED post-loop (§10.4
                                ; step 4, REVISED 2026-07-13) as the final
                                ; Newton-correction's canonical-y scratch --
                                ; the loop is done with it by then.
SQRT_K          equ     $F192   ; signed net count of the x'/y<->x/y-under-100^k
                                ; rescale (spec §10.4 step 2): +1 per /100 step,
                                ; -1 per *100 step applied to reach x'∈[1,100);
                                ; the result is rescaled by 10^SQRT_K at the end
                                ; (dexp+=SQRT_K -- exact, no digit shift, since
                                ; the FPNUM digit array is magnitude-independent) (1)
SQRT_ITER       equ     $F193   ; Heron loop iteration counter, 1-based (the stop-
                                ; rule's "suppress the check on iteration 1" needs
                                ; to know which pass this is) (1); REUSED post-loop
                                ; as the final decision-loop's own pass counter.
SQRT_R          equ     FOUTBUF ; final-correction high-precision residual scratch
                                ; (§10.4 step 4, REVISED 2026-07-13), FPNUM record
                                ; (18). ALIASES FOUTBUF (basic/float.asm's flt_out
                                ; PRINT-formatter scratch, 24 B, own-choice-free-RAM
                                ; region above) -- NOT a fresh "own choice free RAM"
                                ; claim: flt_out only runs AFTER a PRINT argument's
                                ; expression has FULLY evaluated (converting the
                                ; already-computed FAC to text), so it is always
                                ; dead for fp_sqrt's own duration (a nested call
                                ; like STR$(SQR(x)) still finishes SQR(x) -- and
                                ; releases this scratch -- before STR$'s own
                                ; flt_out runs). Same reuse discipline as
                                ; MUL_CARRY/fpd_trial_digit above (two routines
                                ; that provably never run concurrently sharing a
                                ; cell) -- avoids a second SQRT_* RAM claim when
                                ; the $F194..$F195(DRVA_DPB) gap has only 1 free
                                ; byte left.
SQRT_POW10      equ     $F194   ; final decision-loop (§10.4 step 4, REVISED
                                ; 2026-07-13): 1=SQRT_Y is exactly a power of 10
                                ; (its "step down" needs the next decade's finer
                                ; ulp, not its own -- see fsqn_down_check), 0
                                ; otherwise. The LAST free byte below DRVA_DPB
                                ; ($F195, disk/init.asm) -- no more room here
                                ; after this (1)
; --- Math pack slice 2a RAM (repack build only) ------------------------------
; docs/spec-basic-mathpack-slice2.md §11.6: RAM below DRVA_DPB is exhausted
; (SQRT_POW10 above took the last free byte), so fp_atan (sub/fp_atan.asm)
; MUST NOT claim new RAM -- it reuses the SAME SQR scratch cells as generic
; math scratch (SQR and ATN never run concurrently: one factor evaluated at a
; time). Pure ALIASES, no new addresses -- just renamed for the generic
; (non-Heron-specific) role this slice puts them to.
MATH_SIGN       equ     SQRT_K  ; fp_atan's saved input sign s (0/$80, atan is
                                ; odd -- applied to the final magnitude at the
                                ; very end); alias of SQR's rescale counter,
                                ; dead outside SQR's own routine (1)
MATH_RECIP      equ     SQRT_ITER   ; fp_atan's reduction-1 flag (1 = "a:=1/a"
                                ; was applied, so the reconstruction needs
                                ; PI_2-r); alias of SQR's Heron iteration
                                ; counter, same reuse (1)
MATH_BREAK      equ     SQRT_POW10  ; fp_atan's reduction-2 flag (1 = the
                                ; a>BREAK substitution was applied, so the
                                ; reconstruction needs r+PI_6); alias of SQR's
                                ; power-of-10 decision flag, same reuse (1)
MATH_A          equ     SQRT_Y  ; fp_atan's persistent reduced-argument "a" --
                                ; set by the sign-fold/reduction steps, held
                                ; canonical across the whole routine including
                                ; through the fp_poly_horner call (which never
                                ; touches this cell), consumed one final time
                                ; by the core "r := a*P" product (1)
MATH_T          equ     SQRT_X  ; fp_atan's reduction-stage scratch (the
                                ; reduction-2 numerator/denominator algebra),
                                ; RETIRED before the core stage begins and then
                                ; reused as HORNER_G below (sequential reuse,
                                ; never simultaneously live) (1)
HORNER_G        equ     SQRT_X  ; fp_poly_horner's "g" input cell (an alias of
                                ; MATH_T -- fp_atan's reduction scratch is
                                ; retired by the time it computes g:=a*a and
                                ; calls the Horner evaluator, so reusing the
                                ; same cell is safe; see fp_atan.asm step 4) (1)
MATH_R          equ     SQRT_R  ; fp_atan's own "r" (post-core, pre-
                                ; reconstruction result) scratch -- an alias of
                                ; fp_sqrt's FOUTBUF-backed residual cell, dead
                                ; for fp_atan's whole duration for the exact
                                ; same reason SQRT_R's own header argues (no
                                ; PRINT-formatter call is live mid-expression-
                                ; evaluation). REUSED, mid-routine, as
                                ; fp_poly_horner's OWN accumulator (see
                                ; HORNER_ACC below) during the core stage,
                                ; then re-populated with the real "r" right
                                ; after the Horner call returns -- never
                                ; simultaneously needed as both (1)
HORNER_ACC      equ     SQRT_R  ; fp_poly_horner's running Horner accumulator
                                ; (an alias of MATH_R -- see above) (1)
HORNER_CNT      equ     FOUTBUF+18  ; fp_poly_horner's own remaining-term loop
                                ; counter, 1 byte. FOUTBUF is a 24-byte
                                ; scratch region and SQRT_R/MATH_R/HORNER_ACC
                                ; only claim its FIRST 18 bytes (a single
                                ; FPNUM); this reuses one of the 6 still-dead
                                ; TRAILING bytes of that SAME already-justified
                                ; region (see SQRT_R's own header above) --
                                ; NOT a new RAM claim, no additional region is
                                ; touched. Needed because B (the natural
                                ; Z80 loop-counter register) is clobbered by
                                ; the fp_mul/fp_add calls inside the loop body,
                                ; same reasoning as every other persistent
                                ; cell on this page (1)
HORNER_PTR      equ     FOUTBUF+19  ; fp_poly_horner's own advancing coeff-
                                ; table read pointer, 2 bytes (ends at
                                ; FOUTBUF+20, still inside the 24-byte region,
                                ; same reuse as HORNER_CNT above) -- HL is
                                ; clobbered by the same calls, so the pointer
                                ; must be stashed across each iteration too (2)
; --- Math pack slice 2b RAM (repack build only, docs/spec-basic-mathpack- --
; slice2.md §12.6) -- two MORE aliases over the SAME already-justified SQR
; cells (RAM below DRVA_DPB is still exhausted, no new claim permitted):
; fp_exp/fp_log's own n8/e' (16-bit signed int) and m/j (1 byte) scratch.
; SQR/ATN/EXP/LOG never run concurrently (one factor evaluated at a time),
; so aliasing fp_atan's own MATH_SIGN/MATH_RECIP cells here is safe by the
; exact same argument fp_atan's own header already makes.
MATH_N          equ     SQRT_K  ; fp_exp's n8 (steps 2-4)/n (steps 4-8) or
                                ; fp_log's e' (whole routine) -- SIGNED int16,
                                ; 2 bytes spanning SQRT_K+SQRT_ITER
                                ; ($F192-$F193, an alias of fp_atan's
                                ; MATH_SIGN+MATH_RECIP taken TOGETHER as one
                                ; word instead of two independent flags) (2)
MATH_J          equ     SQRT_POW10  ; fp_exp's m (0..7) or fp_log's j (0..8),
                                ; 1 byte; alias of fp_atan's MATH_BREAK
                                ; ($F194), same reuse argument (1)
; --- Math pack slice 2e RAM (repack build only, docs/spec-basic-mathpack- ---
; slice2.md §15.2/§15.4) -- fp_rnd's OWN transient working cells, all
; ALIASES over already-justified dead scratch (RAM below DRVA_DPB is still
; exhausted, no new claim permitted). Safe by the SAME "one factor at a
; time" argument fp_atan's own header makes (SQR/ATN/EXP/LOG/POW/SIN/COS/
; TAN/RND never run concurrently) -- and safer still: unlike every other
; slice-2 tenant, fp_rnd calls NEITHER fp_add/fp_sub/fp_mul/fp_div NOR
; fp_poly_horner internally (§15.2 -- the 14-digit BCD multiply-add is NOT
; built from the resident fp ops), so there is no nested-call risk of a
; callee clobbering these cells mid-routine either.
RND_STATE       equ     MATH_A  ; the 14-digit decimal state, UNPACKED digit
                                ; array (values 0-9, MSD-first -- d[0]=the
                                ; 10^13 place, same convention as ARGA_DIG),
                                ; first 14 of MATH_A's (=SQRT_Y) 18-byte
                                ; cell. Holds S BEFORE the advance (either
                                ; RND_SEED unpacked, or -- read directly, not
                                ; via this alias -- ARGA+FPNUM_DIG for a
                                ; reseed) and the NEW state AFTER it; also
                                ; the value fp_rnd normalises to FAC (14)
RND_LE          equ     MATH_T  ; S's digits, byte-REVERSED to little-endian
                                ; (index 0 = units/LSD) for the multiply-add
                                ; core (rnd_advance_bcd_le mirrors tools/
                                ; sim_math_chain.py's rnd_advance_bcd, which
                                ; is little-endian) -- first 14 of MATH_T's
                                ; (=SQRT_X/HORNER_G) 18-byte cell (14)
RND_ACCLE       equ     MULPROD ; the multiply-add's running accumulator,
                                ; little-endian, 14-digit window (values
                                ; mod 1e14 -- overflow past digit 13 is
                                ; dropped, §15.2); first 14 of MULPROD's own
                                ; 28-byte cell (dead outside fp_mul, and
                                ; fp_rnd never calls fp_mul -- see header
                                ; above) (14)
RND_I           equ     MULPROD+14  ; multiply-add loop: S/acc digit index i
                                ; (0..13), the SAME MULPROD cell's own spare
                                ; second half (1)
RND_J           equ     MULPROD+15  ; multiply-add loop: A's digit index j
                                ; (0..13) (1)
RND_IJ          equ     MULPROD+16  ; multiply-add loop: i+j, the target
                                ; accumulator index for the current (i,j)
                                ; pair (1)
RND_AJ          equ     MULPROD+17  ; multiply-add loop: A_LE[j], stashed
                                ; across the inner i-loop (1)
RND_CARRY       equ     MULPROD+18  ; multiply-add loop: running BCD carry,
                                ; shared by both the multiply phase (per
                                ; outer j pass) and the final +C ripple-add
                                ; phase (reset to 0 at the start of each) (1)
RND_K           equ     MULPROD+19  ; output normalisation: count of leading
                                ; zero digits in the post-advance state
                                ; (0..14 -- 14 means S=0, the astronomically
                                ; rare all-zero guard, §15.4 step 3) (1)
JIFFY           equ     $FC9E   ; MSX software clock, bumped by the timer ISR (MSX2 TH work area)
; Dispatch ABI (mirror of sub/equates.inc — the append-only page-0 entry table).
; IX = SUBROM_ENTRY_BASE_P0 + 3*index selects a tenant; never renumber an index.
; IFNDEF-guarded: sub.asm includes BOTH this and sub/equates.inc (which defines
; these first), so the guard lets the sub build reuse those and the main build
; (no equates.inc) define its own — one ABI, no double-definition.
    IFNDEF SUBROM_ENTRY_BASE_P0
SUBROM_ENTRY_BASE_P0 equ $0040  ; sub-ROM page-0 jp-table base (ABOVE the fixed
                                ; $0038 IM1 vector -- D-P0BASE, docs/spec-rom-
                                ; region-p0base.md. Mirrors sub/equates.inc;
                                ; NOTHING cross-checks the two, so a one-sided
                                ; edit builds clean and dispatches into pad)
SUBROM_IDX_TOKENISE  equ 1      ; the WHOLE tokeniser tenant (sub/tokenise.inc +
                                ; sub/tkfloat.asm); wave 2 replaced wave 1's
                                ; per-literal tk_float entry (the crunch is now an
                                ; in-slot callee of the co-located loop)
SUBROM_IDX_DETOK     equ 2      ; the detokeniser core (wave 3; sub/detok.asm). The
                                ; main-ROM stub is basic/list.asm `detok`.
SUBROM_IDX_INTTEST   equ 3      ; the interrupt self-test tenant (trampoline slice;
                                ; sub/sub.asm sub_int_selftest). Runs EI, spins > 1
                                ; frame, returns the JIFFY delta in SUB_INT_DELTA —
                                ; the subrom-inttest gate asserts it is >= 1.
SUBROM_IDX_ARY       equ 4      ; the numeric-array engine (arrays slice-1 SPLIT
                                ; design, docs/spec-basic-arrays.md §10; sub/
                                ; arrays.asm ary_engine) — a pure-RAM leaf (no
                                ; resident-ABI import). Main-ROM stub is
                                ; basic/arrays.asm `ary_engine_call`.
SUBROM_IDX_STRHEAP   equ 5      ; the string-heap engine (arrays slice-4a, docs/
                                ; spec-basic-arrays-slice4a-string-heap.md §9;
                                ; sub/strheap.asm strheap_engine) — a pure-RAM
                                ; leaf. Main-ROM stubs are basic/str-engine.asm
                                ; `call_strheap` + one SH_* wrapper per op.
                                ; ⚠️ NOT op 0 (ALLOC): its wrapper
                                ; `str_heap_alloc` had lost its last main
                                ; caller and D-SEEDPROSE deleted it, so no
                                ; main-side code issues op 0 today.
SUBROM_IDX_PU_TOFIELD equ 6     ; PRINT USING format scanner: emit leading literals +
                                ; identify the next field (docs/spec-evict-printusing.md;
                                ; sub/printusing.asm pu_tofield_tenant) — a pure PU_*-RAM
                                ; leaf. Main-ROM stub basic/printusing.asm `pu_to_field`.
SUBROM_IDX_PU_TAIL   equ 7      ; PRINT USING trailing-literal emitter (sub/printusing.asm
                                ; pu_tail_tenant). Main-ROM stub `pu_emit_tail`. (Both
                                ; kept in sync with sub/equates.inc.)
SUBROM_IDX_GRAPHICS  equ 8      ; the SCREEN-2 geometry engine (graphics arc; sub/
                                ; graphics.asm graphics_tenant) — GFX_OP-selector
                                ; dispatched (0=floor self-test G1, 1=PSET/PRESET plot,
                                ; 2=POINT read). Main-ROM stubs basic/graphics.asm
                                ; ex_pset/ex_preset/ev_f_point; IX = SUBROM_ENTRY_BASE_P0
                                ; + 3*8 = $0028. (Kept in sync with sub/equates.inc.)
; Page-1 dispatch (docs/spec-basic-subrom-mathpack.md §2): the FIRST page-1
; tenant. SUBROM_ENTRY_BASE_P1 mirrors the disk $4010 DSKIO convention (also
; independently defined in sub/equates.inc for the sub build — same value,
; IFNDEF-guarded here so the two never drift/double-define). Index 0 (not
; re-listed here) is the S2a page-1 ping (sub/sub.asm sub_p1_ping).
SUBROM_ENTRY_BASE_P1 equ $4010  ; sub-ROM page-1 jp-table base
SUBROM_IDX_SQR       equ 1      ; fp_sqrt tenant (sub/sub.asm, migrated from
                                ; main-ROM page-0 low 2026-07-13). Main-ROM
                                ; stub is basic/expr.asm `evmc_sqr`.
SUBROM_IDX_ATN       equ 2      ; fp_atan tenant (math pack slice 2a, sub/
                                ; fp_atan.asm) -- the FIRST transcendental
                                ; page-1 tenant (docs/spec-basic-mathpack-
                                ; slice2.md §11.1). Main-ROM stub is
                                ; basic/expr.asm `evmc_atn`.
SUBROM_IDX_EXP       equ 3      ; fp_exp tenant (math pack slice 2b, sub/
                                ; fp_exp.asm), docs/spec-basic-mathpack-
                                ; slice2.md §12.2. Main-ROM stub is
                                ; basic/expr.asm `evmc_exp`.
SUBROM_IDX_LOG       equ 4      ; fp_log tenant (math pack slice 2b, sub/
                                ; fp_log.asm), docs/spec-basic-mathpack-
                                ; slice2.md §12.2. Main-ROM stub is
                                ; basic/expr.asm `evmc_log`.
SUBROM_IDX_POW       equ 5      ; fp_pow tenant (math pack slice 2c, sub/
                                ; fp_pow.asm): the `^` operator's int-path
                                ; square-and-multiply / frac-path EXP(y*LOG(x))
                                ; body, docs/spec-basic-mathpack-slice2.md
                                ; §13.2/§13.5. Main-ROM stub is basic/
                                ; float-arith.asm `combine_pow`.
SUBROM_IDX_SIN       equ 6      ; fp_sin tenant (math pack slice 2d, sub/
                                ; fp_sin.asm): the shared sincos_kernel +
                                ; SIN's own quadrant-select, docs/spec-basic-
                                ; mathpack-slice2.md §14.4/§14.5/§14.6.
                                ; Main-ROM stub is basic/expr.asm `evmc_sin`.
SUBROM_IDX_COS       equ 7      ; fp_cos tenant (math pack slice 2d, sub/
                                ; fp_sin.asm, same sincos_kernel), docs/spec-
                                ; basic-mathpack-slice2.md §14.4/§14.6.
                                ; Main-ROM stub is basic/expr.asm `evmc_cos`.
SUBROM_IDX_TAN       equ 8      ; fp_tan tenant (math pack slice 2d, sub/
                                ; fp_sin.asm): SIN(x)/COS(x) over the same
                                ; sincos_kernel, docs/spec-basic-mathpack-
                                ; slice2.md §14.4/§14.6. Main-ROM stub is
                                ; basic/expr.asm `evmc_tan`.
SUBROM_IDX_RND       equ 9      ; fp_rnd tenant (math pack slice 2e, sub/
                                ; fp_rnd.asm): the 14-digit BCD LCG advance,
                                ; docs/spec-basic-mathpack-slice2.md §15.3/
                                ; §15.4. LAST slice-2 tenant. Main-ROM stub
                                ; is basic/expr.asm `evmc_rnd`.
SUBROM_IDX_FORMAT    equ 10     ; format_tenant (CALL FORMAT eviction, sub/
                                ; format.asm, docs/spec-evict-call-format.md):
                                ; the pure sector-build/write bulk (shared
                                ; basic/format-body.inc), reached via its OWN
                                ; sub-local CALSLT write path (main's
                                ; write_sector/dskio_calslt are page-1
                                ; main-resident, invisible to a page-1
                                ; tenant). Main-ROM stub is basic/format.asm
                                ; `do_format`'s fmt_dispatch; the interactive
                                ; 360k/720k menu stays main-side (console I/O).
SUBROM_IDX_SCANSTMT  equ 11     ; scan_stmt_end tenant (error-handling S2b
                                ; RESUME NEXT's statement-advance, sub/
                                ; errtrap.asm, docs/spec-basic-error-handling-
                                ; s2b-packet.md §5.5) -- a pure-leaf (playbook
                                ; §3A: walks only tokenised program RAM text,
                                ; calls nothing in main). Main-ROM stub is
                                ; basic/interp.asm `ex_resume`'s res_next arm.
SUBROM_IDX_FATPRIM   equ 12     ; fatprim_tenant (sub/fatprim.asm): the FAT12
                                ; primitive/sector layer (docs/spec-evict-
                                ; diskfile-cluster.md §11, Phase 1) -- a SINGLE
                                ; selector-dispatched tenant (one index for
                                ; all 15 marshalled primitives, not one index
                                ; each -- DISKOP_OP picks the routine). A pure
                                ; RAM+BIOS(CALSLT) leaf, same shape as
                                ; format_tenant/scan_stmt_end (needs no
                                ; resident-ABI import). Main-ROM stubs are the
                                ; resident shims in basic/fat.asm (repack,
                                ; the repack build), replacing the moved
                                ; bodies under the SAME names (read_sector,
                                ; write_sector, fat_mount, fat_find, ...).
SUBROM_IDX_DIRVERB   equ 13     ; dirverb_tenant (sub/dirverb.asm): the
                                ; directory-verb I/O bodies (docs/spec-evict-
                                ; diskfile-cluster.md §12, Phase 2) -- a SINGLE
                                ; selector-dispatched tenant (DISKOP_OP picks
                                ; KILL's delete loop vs NAME's dir-entry stamp).
                                ; Its bodies call the Phase-1 fatprim primitives
                                ; (fat_delete / read_sector / fatprim_write_
                                ; sector) SUB-LOCALLY. A pure RAM+BIOS(CALSLT)
                                ; leaf. Main-ROM heads are the repack `ELSE`
                                ; branches of do_kill/do_name (basic/files.asm).
SUBROM_IDX_PLAY_PARSE equ 14    ; play_parse_tenant (sub/playparse.asm): the audio
                                ; Slice-2a MML parser (docs/spec-basic-audio-play-
                                ; slice2a.md). A pure RAM leaf: reads the per-voice
                                ; (ptr,len) from the VCBs + AUDIO_VMASK, parses each
                                ; MML string into its VOICxQ ring buffer, sets MUSICF
                                ; LAST. Only ex_play (basic/play.asm) computes
                                ; IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_PLAY_PARSE.
SUBROM_IDX_PUEMIT    equ 16     ; pu_emit_tenant (sub/printusing.asm): PRINT USING's
                                ; numeric PAD + EMIT, built into DETOKBUF for the
                                ; resident stub to drain (D-PUEMIT). PAGE-0 index
                                ; space. It cannot call pchar itself -- see the
                                ; tenant's own header -- which is exactly why it
                                ; buffers, as pu_to_field already does.
SUBROM_IDX_PUSIGN    equ 15     ; pu_sign_tenant (sub/printusing.asm): PRINT USING's
                                ; `+` / `-` sign placement (D-PUSIGN). PAGE-0 index
                                ; space -- pure RAM work over NUMBUF + PU_FLAGS, no
                                ; main-ROM call, so it satisfies the page-0 closure
                                ; rule. Sited sub-side because the transformation is
                                ; ~60 B and main page 1 had 50.
SUBROM_IDX_LINEEDIT  equ 15     ; lineedit_tenant (sub/lineedit.asm): the numbered-
                                ; line editor's TXTTAB memmove engine (docs/spec-
                                ; eviction-g4-space.md §4, carve #2 of the G4-space
                                ; eviction slice) -- store_line's insert/delete body
                                ; (prog_find_del/delete_at/open_gap/copy) + the
                                ; relink loop, LE_OP-selector dispatched (0=process
                                ; store/delete via SL_NUM/SL_TOK, 1=relink-only, for
                                ; cload.asm's own `call relink` sites). Calls
                                ; vars_reset directly (page-0 low-region resident,
                                ; in the resident-ABI import list -- reachable, NOT
                                ; a straddle). Main-ROM stubs are basic/program.asm
                                ; `store_line`/`relink`. NOTE: the spec's own §4 text
                                ; said "index 14" -- stale by the time of impl
                                ; (SUBROM_IDX_PLAY_PARSE claimed 14 first); 15 is the
                                ; actual next-free index.
SUBROM_IDX_READVAL   equ 10     ; readdata_tenant (sub/readdata.asm): the READ/DATA
                                ; value engine, carved out of the resident to fund
                                ; graphics G7 (docs/spec-eviction-g7-space.md). Page-0
                                ; (index 10 in the page-0 table -- the page-1 table's
                                ; own index 10 is FORMAT; the two spaces are separate).
                                ; Result rides back in RDV_ST/RDV_VAL.
SUBROM_IDX_BEEP      equ 11     ; beep_tenant (sub/beep.asm): the BEEP body (direct
                                ; PSG blip + busy-wait), carved out of basic/sound.asm
                                ; to fund input-devices slice I1 (docs/spec-basic-
                                ; input-devices.md §7). PAGE-0 table index 11 -- IX =
                                ; SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_BEEP. No args,
                                ; no result, cannot fail, so nothing marshals.
SUBROM_IDX_FLDLOOK   equ 12     ; fld_lookup_tenant (sub/fldlook.asm): the FIELDed-
                                ; variable READ hook's pure-RAM half (record-slice
                                ; copy out of FSECTOR_BUF into FLD_DESC + the RVDESC
                                ; wrap), carved out of basic/field.asm to fund D-CLP's
                                ; 22 B of main page 1 (docs/decision-clearpool-
                                ; funding.md). PAGE-0 table index 12 -- IX =
                                ; SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_FLDLOOK. The
                                ; located field-table entry rides in HL (subrom_call
                                ; passes it through CALSLT); the result is STRPTR, so
                                ; nothing marshals through a param block.
                                ; ⚠️ Used to be the LAST index that fits before the
                                ; $0038 vector; D-P0BASE moved the table base to
                                ; $0040, above it, and index 13 below is that note
                                ; being cashed.
SUBROM_IDX_LRSETST   equ 13     ; lrset_store_tenant (sub/lrsetst.asm): the LSET/RSET
SUBROM_IDX_DEFFN     equ 14     ; deffn_tenant (sub/deffn.asm): DEF FN's
                                ; parse -- name resolve, the two lists
                                ; walked together, the shadow slots and
                                ; their ceiling. Page 0 because it calls
                                ; NO eval: every one of those is a token
                                ; walk over page-3 RAM (D-DEFFNEV).
                                ; record-field STORE (space-fill the field, then copy
                                ; min(srclen,width) bytes in left- or right-aligned),
                                ; carved out of basic/field.asm to fund D-FLDARY's
                                ; 38 B of main page 1 (docs/spec-basic-fldary.md
                                ; §6.4; the carve returns 57). PAGE-0 table index 13
                                ; -- IX = SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_LRSETST.
                                ; 🎯 NOTHING MARSHALS AT ALL: every input is already a
                                ; RAM cell (LRSET_DEST/W/JUST, STRPTR) and
                                ; there is no return value, which is exactly why this
                                ; member of the cluster was the one taken.
SUBROM_IDX_DEFTYPE   equ 9      ; deftype_tenant (sub/deftype.asm): DEFINT/DEFSNG/
                                ; DEFDBL/DEFSTR, carved out of basic/usr.asm to fund
                                ; G6 DRAW's resident half (docs/spec-eviction-g6-
                                ; space.md). PAGE-0 table index 9 (the P0 and P1
                                ; tables number independently) -- IX =
                                ; SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_DEFTYPE.
SUBROM_IDX_CASMATCH  equ 16     ; casmatch_tenant (sub/casmatch.asm): the
                                ; cassette Tier-3 name-match/data-skip engine
                                ; (docs/spec-eviction-g5-space.md) -- cas_open_match
                                ; + cas_skip_data (basic/cload.asm), evicted whole
                                ; to free page-1 tail space for the G5 PAINT slice.
                                ; A pure RAM+BIOS leaf (TAPION/TAPIN + CAS_WANT*/
                                ; CAS_HDRNAME/CAS_HDRID/CAL_BUF/CAL_CNT) -- no
                                ; register marshalling, only the CM_STATUS byte
                                ; (CF cannot ride back through subrom_call
                                ; directly). Only basic/cload.asm `cas_open_match`
                                ; computes IX = SUBROM_ENTRY_BASE_P1 +
                                ; 3*SUBROM_IDX_CASMATCH.
SUBROM_IDX_TITLE     equ 17     ; title_tenant (sub/title.asm): the startup header
                                ; (show_title + banner_text, basic/title.asm),
                                ; evicted whole to fund the input-devices I2 slice
                                ; (docs/spec-basic-input-devices.md §9.5 -- a
                                ; measured 55 B page-1 deficit). PAGE 1, because
                                ; its only edges are INITXT/CHPUT, which are page-0
                                ; BIOS and so invisible to a page-0 tenant. No
                                ; arguments, no result, no RAM state: nothing to
                                ; marshal at all. Only basic/title.asm `show_title`
                                ; computes IX = SUBROM_ENTRY_BASE_P1 +
                                ; 3*SUBROM_IDX_TITLE, and it needs no absent-sub-ROM
                                ; error path -- printing no header is a fine
                                ; degradation, unlike every other tenant's silent
                                ; failure.
SUBROM_IDX_FCBNAME   equ 18     ; fcbname_tenant (sub/fcbname.asm): the disk
                                ; 8.3-FCB-name builder build_83_name, evicted to
                                ; fund interrupt-traps T1 (docs/spec-basic-
                                ; interrupt-traps.md §10.4). PAGE 1 (the page-0
                                ; table is full to the $0038 vector); a pure RAM
                                ; leaf with an inlined upcase clone. Marshals HL/CF
                                ; via BN_PTR/BN_STAT (above). Only basic/bload.asm
                                ; `build_83_name` (repack branch) computes
                                ; IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FCBNAME.
SUBROM_IDX_CIRCLEPARSE equ 19  ; circleparse_tenant (sub/circleparse.asm): CIRCLE's
                                ; whole grammar walk + angle/aspect float math, evicted
                                ; as an eval-bounce co-routine to reclaim ~350-500 B of
                                ; resident page-1 for the interrupt-trap arc (docs/spec-
                                ; circle-coroutine-space.md). PAGE 1 (reaches the
                                ; low-region float pack, the fp_sqrt pattern); bounces
                                ; eval/parse_coord back to the resident ex_circle servicer
                                ; via GFX_DREQ/GFX_DPTR. IX = SUBROM_ENTRY_BASE_P1 +
                                ; 3*SUBROM_IDX_CIRCLEPARSE.
SUBROM_IDX_BLOAD     equ 20     ; bload_tenant (sub/bload.asm): the whole BLOAD verb
                                ; body -- device dispatch, the cassette load loop and
                                ; the disk load loop -- evicted from main page 1 to fund
                                ; interrupt-traps T3 (docs/spec-traps-t3-key.md §7.6).
                                ; A PAGE-1 tenant specifically so it sits beside
                                ; fatprim_tenant and calls fat_mount/fat_find/fat_open/
                                ; fat_read_file_sector SUB-LOCALLY -- which is what makes
                                ; the carve possible at all. Input BL_PTR, output BL_STAT;
                                ; IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_BLOAD. The ,R
                                ; handoff stays RESIDENT (basic/bload-body.inc).
SUBROM_IDX_SAVE      equ 21     ; save_tenant (sub/save.asm): BLOAD's mirror -- the
                                ; SAVE / BSAVE / CSAVE WRITE ENGINES (four SV_OP_*
                                ; selectors), evicted from main page 1 to fund `TIME`
                                ; and interrupt-traps T5 together (docs/decision-fund-
                                ; time-and-t5.md, D-FUND-1). PAGE 1 beside fatprim for
                                ; the same reason BLOAD is: the fat_io_* WRITE cursor
                                ; it drives reaches fat_dir_create/fat_flush_data_sector/
                                ; fat_dir_update sub-locally. The PARSE stays resident
                                ; (it calls `eval`), so nothing but SV_OP/SV_STAT rides;
                                ; IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SAVE.
SUBROM_IDX_ERRMSG    equ 22     ; errmsg_tenant (sub/errmsg.asm): the fourteen ERR
                                ; codes zerobas never RAISES but must still PRINT
                                ; (D-MSGSUB, docs/spec-basic-msgsub.md). PAGE 1 for
                                ; title_tenant's exact reason -- its only outward
                                ; edge is CHPUT, page-0 BIOS, invisible to a page-0
                                ; tenant -- and because main's OWN printer is
                                ; unreachable from either island (print_string
                                ; $4673 / print_msg $7717 are main page 1, which a
                                ; page-1 CALSLT switches out). NOTHING MARSHALS: the
                                ; sole input is ERRFLG, already in RAM. Reached from
                                ; print_msg_stopcr's MSGESC_SUB arm (basic/
                                ; program.asm `pm_sub`), which is the only site that
                                ; computes IX = SUBROM_ENTRY_BASE_P1 +
                                ; 3*SUBROM_IDX_ERRMSG.
SUBROM_IDX_PUNUM     equ 24     ; pu_num_tenant (sub/punum.asm): PRINT USING's
                                ; numeric renderer (D-PUNUM). PAGE 1, because it
                                ; calls flt_fmt in the main LOW region -- and
                                ; because main page 1 had 32 B free.
SUBROM_IDX_PARSELN   equ 23     ; parseln_tenant (sub/lineno.asm): the ASCII
                                ; line-number scanner `dl_store` runs once per
                                ; typed/loaded numbered line (D-EVLNO, docs/
                                ; spec-rom-region-evict-lineno.md -- rank 4 of
                                ; the ROM REGION STRUCTURE REVIEW). PAGE 1 for a
                                ; reason neither title_tenant's nor errmsg's: the
                                ; body calls NOTHING AT ALL, so it needs neither
                                ; island's privilege -- and the page-0 table is
                                ; full to the $0038 vector (sub/sub.asm), so the
                                ; review's "prefer page 0" rule has no room to
                                ; apply. Marshals BC/HL back through PLN_NUM/
                                ; PLN_PTR; HL rides IN through subrom_call.
                                ; Sole caller basic/program.asm `parse_lineno`.
    ENDIF
; EXBRSA ($FAF8): published MSX2 work area for the sub-ROM slot id (D-6) — written
; for convention-compat with a future real SUBROM/EXTROM; our private dispatch
; reads SUBSLOT, not EXBRSA (R4). Source: MSX2 Technical Handbook work-area map.
EXBRSA          equ     $FAF8

; --- D-MSGENC: error-message phrase escapes (repack build only) ---------------
; docs/spec-basic-msgenc-carve.md §4.1. These are the BYTE VALUES that appear
; inside an encoded message string; print_msg_stopcr (basic/program.asm) expands
; them from msg_phrase_tab, which must list the phrases in exactly this order.
; Values stay below $20 so no printable literal can collide, and the decoder's
; single `cp MSGESC_HI + 1` is an exact test (the baked 13,10 are gone, §4.2).
MSGESC_ERROR    equ     1       ; " error"
MSGESC_UTOF     equ     2       ; "ut of "              (leading letter dropped:
MSGESC_ILLFN    equ     3       ; "llegal function call"  "Out of"/"out of" and
; 🎯 D-MSGMIGRATE DELETED MSGESC_WITHOUT (4, " without") AND MSGESC_FILE
; (5, "file "). Every user of both migrated into the sub-ROM tenant, where
; strings are stored PLAIN -- MSGESC_WITHOUT had THREE (err_noret, err_nofor and,
; the one the filed estimate missed, err_resume_noerr) and MSGESC_FILE two
; (err_bad_filenum, err_bad_filemode). A phrase with no users is dead DATA; the
; dead-code gate walks spans of CODE and cannot see it, so it has to be found by
; enumerating users -- which is the same instrument that refuted the "different
; key" claim this slice was filed under.
; ⚠️ THEY WERE THE TOP TWO VALUES, so nothing below renumbers and MSGESC_HI simply
; follows MSGESC_ILLFN. Re-adding a phrase must APPEND (4, then 5) and re-point
; MSGESC_HI at it -- never insert below, which would silently re-spell every
; message that uses a lower escape.
                                ; ("bad file number" / "file not open") are the only
                                ; pair in the corpus that shares a substring neither
                                ; of the four above covers. Added rather than spelled
                                ; out because the phrase table is PAGE 1 and the two
                                ; messages are LOW REGION: it spends 6 bytes of the
                                ; roomy wall to save 8 of the scarce one. The decoder
                                ; needs no change -- it is bounded by MSGESC_HI.
MSGESC_LO       equ     MSGESC_ERROR                    ; share one entry, so the
MSGESC_HI       equ     MSGESC_ILLFN                    ; decoder needs NO case flag

; --- D-MSGSUB: the SUB-ROM-HOSTED marker (docs/spec-basic-msgsub.md §3.1) -----
; NOT a phrase. A message body that is just this byte says "the text lives in the
; sub-ROM page-1 tenant SUBROM_IDX_ERRMSG, keyed on ERRFLG"; print_msg_stopcr's
; pm_sub arm dispatches and the tenant emits through BIOS CHPUT. Main keeps the
; CRLF and the run-mode " in <line>" suffix, so this is a BODY substitution and
; nothing about fre_abort_low's two arms changes.
;
; ⚠️ DELIBERATELY ABOVE MSGESC_HI, AND THE DECODER TESTS IT **BEFORE** THE PHRASE
; BOUND. Two separate reasons, both load-bearing:
;   * MSGESC_HI bounds msg_phrase_tab's LENGTH, and tests/test_msgenc.py reads
;     exactly MSGESC_HI - MSGESC_LO + 1 phrases out of the ROM. Folding this byte
;     into the phrase range would make that read run one entry PAST the table and
;     compare against whatever follows -- a readout that fails by producing
;     plausible garbage rather than by going red. test_msgenc.py now asserts
;     MSGESC_SUB > MSGESC_HI to keep a future tidy-up from doing exactly that.
;   * Being above the bound means `cp MSGESC_HI + 1 / jr nc,pm_lit` would treat
;     it as a LITERAL and pchar a raw $06. The pm_sub test must precede it.
MSGESC_SUB      equ     6       ; body = this byte alone -> the sub-ROM tenant
