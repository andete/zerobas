; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; save.asm — BSAVE / SAVE / CSAVE statement handlers (disk + cassette write).
;
; The WRITE mirror of bload.asm / cload.asm. Implements three verbs:
;
;   BSAVE "A:F",start,end[,exec]    -> disk binary: [$FE][start][end][exec] + data.
;   BSAVE "CAS:F",start,end[,exec]  -> tape binary: 10x$D0 + 6-char name (header
;                                       block); then start/end/exec + data (data block).
;   SAVE "A:F"                       -> disk tokenised: [$FF] + program image.
;   SAVE "CAS:F"                     -> tape tokenised: 10x$D3 + 6-char name (header
;                                       block); then program image (data block).
;   CSAVE "F"                        -> tape tokenised (same as SAVE"CAS:F").
;
; All tape writes use the TAPOON/TAPOUT/TAPOOF BIOS entry points at $00EA/$00ED/$00F0
; (zerobas-tape; sysvars.inc). TAPOUT CLOBBERS EVERY REGISTER: every loop counter
; and pointer must survive TAPOUT calls via RAM (TSV_PTR/TSV_END/TSV_CNT in page $E0).
;
; Cassette file format: two logical blocks per file (MSX2 TH cassette file format;
; cross-checked by cas_encode.py which mirrors what a real CSAVE writes):
;   Block 1 header: TAPOON(long) + 10x file-type-id + 6-char filename + TAPOOF.
;     file-type-id = $D3 (BASIC_ID) for tokenised (CSAVE / SAVE"CAS:").
;     file-type-id = $D0 (BINARY_ID) for binary (BSAVE"CAS:").
;   Block 2 data: TAPOON(short) + payload + TAPOOF.
;     Tokenised payload = program image TXTBASE..PRGEND+1 (same line-link image
;     the disk SAVE writes after its $FF marker; NO $FE/$FF disk markers on tape).
;     Binary payload = start(LE) + end(LE) + exec(LE) + RAM[start..end inclusive].
;
; Disk-path format (unchanged from the original implementation):
;   BSAVE disk: [$FE][start:2 LE][end:2 LE][exec:2 LE] then raw data.
;   SAVE  disk: [$FF] then the line-link program image.
;
; The ,A ASCII-save form is supported for BOTH disk (ascii_save) and cassette
; (cas_ascii_save): a line-numbered detokenised listing terminated by Ctrl-Z ($1A).
; On tape it is a $EA-header file in fixed 256-byte data blocks (MSX2 TH; §0.1 of
; basic/docs/spec-cas-ascii-saveload.md).
;
; CLEAN-ROOM: cassette format sourced from MSX2 Technical Handbook cassette chapter
; (same allowed source as BINARY_ID/BASIC_ID constants already in sysvars.inc);
; cross-checked by cas_encode.py (our own code). Disk format unchanged. CSAVE token
; oracle-LOCKED ($9A, basic_probe_crunch.py). TAPOON/TAPOUT/TAPOOF contracts from
; tape/tape.asm (our own code). No disassembly. See basic/PROVENANCE.md.

; ===========================================================================
; THE CARVE (docs/decision-fund-time-and-t5.md, D-FUND-1). The four WRITE
; ENGINES below — BSAVE/disk, BSAVE/tape, SAVE/disk and the shared cassette
; tokenised writer — live in a sub-ROM PAGE-1 tenant (sub/save.asm,
; SUBROM_IDX_SAVE) in the repack build, freeing main page 1 to fund `TIME` and
; interrupt-traps T5. BLOAD's mirror, and the same reason it is affordable:
; beside fatprim_tenant the FAT12 write primitives are ordinary in-page calls.
;
; WHAT DOES **NOT** MOVE, and why the split is where it is: every one of these
; verbs PARSES with `eval`, which is main page 1 and therefore switched OUT
; while a page-1 tenant runs. So the parse stays resident — and because it does,
; the tenant needs no cursor and no argument marshalling at all: by the time it
; is called every value already sits in its RAM home (DISK_FCB_NAME, TSV_NAME,
; CURPTR, DSV_END, TSV_END, EXECPTR, VRAM_FLAG). Only SV_OP and SV_STAT ride.
; The `,A` ASCII paths also stay: they drive list_walk/pchar, i.e. the PAGE-0
; detokeniser tenant, which a page-1 tenant cannot reach.
;
; Each engine's `IF the repack build` stub re-declares the SAME entry label the
; resident parse already reaches by `jr`/fall-through, so not one parse
; instruction changes.
sv_load_error   equ     load_error          ; resident: a zero-byte EQU, so every
                                            ; `jp sv_load_error` in the shared bodies
                                            ; assembles to the frozen cart's bytes.
                                            ; In the tenant it is the sub-local
                                            ; reporter that sets SV_STAT.

; ===========================================================================
; do_bsave — BSAVE "device:name",start,end[,exec]
; Entry: HL -> the bytes after the BSAVE token (verbatim ASCII filename, then the
; crunched address args: comma + &H/decimal expression each).
do_bsave:
                xor     a
                ld      (VRAM_FLAG),a       ; default RAM source; ",S" sets it below
                call    skip_spaces
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                push    hl                  ; remember filename start
                ld      de,dev_cas
bsv_dev:
                ld      a,(de)
                or      a
                jp      z,bsv_is_cas        ; matched all of "CAS:" -> tape (out of jr range)
                ld      c,a
                ld      a,(hl)
                call    upcase
                cp      c
                jr      nz,bsv_is_disk      ; prefix mismatch -> disk
                inc     hl
                inc     de
                jr      bsv_dev
bsv_is_disk:
                pop     hl                  ; restore filename start
                ; HL = filename start (after the quote); build the FCB.
                call    parse_disk_fcb      ; build DISK_FCB; HL -> closing '"'
                ld      a,(hl)
                cp      '"'                 ; consume the closing quote
                jp      nz,load_error
                inc     hl
                ; --- ,start ------------------------------------------------
                call    expect_comma_eval   ; DE = start, HL advanced
                ld      (CURPTR),de         ; CURPTR = start (the source walk cursor)
                ld      (EXECPTR),de        ; default exec = start (overridden if ,exec)
                ; --- ,end --------------------------------------------------
                call    expect_comma_eval   ; DE = end
                ld      (DSV_END),de        ; DSV_END = last data byte (inclusive)
                ; --- optional 4th slot: ,exec  OR  ,S (VRAM save) ----------
                ; bsave_opt4 classifies the slot: CF set -> reject a stray
                ; identifier (jp c,load_error at THIS level so the abort unwinds to
                ; the dispatcher); else A=0 none, A=1 ",S" (VRAM), A=2 exec (DE).
                call    bsave_opt4
                jp      c,load_error        ; stray 4th token -> honest reject
                or      a
                jr      z,bsv_open          ; no 4th arg -> exec defaulted to start
                cp      2
                jr      z,bsv_set_exec      ; expression -> exec address
                ld      a,1                 ; A=1: ",S" -> stream data from VRAM
                ld      (VRAM_FLAG),a       ; header start/end/exec kept verbatim
                jr      bsv_open
bsv_set_exec:
                ld      (EXECPTR),de
bsv_open:
                ld      a,SV_OP_BSV_DISK
                jp      sv_tenant           ; BSAVE -> disk: the write engine is a tenant

; --- tape BSAVE path ---
bsv_is_cas:
                pop     af                  ; discard saved filename start (HL past "CAS:")
                ; HL now points just past "CAS:" inside the quotes.
                ; Parse filename: up to 6 chars until '"', space-pad to 6.
                call    tape_parse_name     ; fills TSV_NAME[0..5]; HL -> closing '"'
                ld      a,(hl)
                cp      '"'
                jp      nz,load_error
                inc     hl                  ; past closing '"'
                ; --- ,start ------------------------------------------------
                call    expect_comma_eval   ; DE = start
                ld      (CURPTR),de
                ld      (EXECPTR),de        ; default exec = start
                ; --- ,end --------------------------------------------------
                call    expect_comma_eval   ; DE = end
                ld      (TSV_END),de
                ; --- optional 4th slot: ,exec (,S VRAM-to-tape unsupported) -
                call    bsave_opt4
                jp      c,load_error        ; stray 4th token -> honest reject
                or      a
                jr      z,bsv_cas_open      ; no 4th arg
                cp      2
                jr      z,bsv_cas_exec      ; expression -> exec
                jp      load_error          ; A=1: ",S" VRAM-to-tape not supported
bsv_cas_exec:
                ld      (EXECPTR),de
bsv_cas_open:
                ld      a,SV_OP_BSV_CAS
                jp      sv_tenant           ; BSAVE -> tape

; ===========================================================================
; do_save — SAVE "device:name"   (tokenised-BASIC save; ,A out of scope)
; Entry: HL -> the bytes after the SAVE token.
do_save:
                call    skip_spaces
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                push    hl                  ; remember filename start
                ld      de,dev_cas
sav_dev:
                ld      a,(de)
                or      a
                jp      z,sav_is_cas        ; matched all of "CAS:" -> tape (jp: ascii_save split the range)
                ld      c,a
                ld      a,(hl)
                call    upcase
                cp      c
                jr      nz,sav_is_disk      ; prefix mismatch -> disk
                inc     hl
                inc     de
                jr      sav_dev
sav_is_disk:
                pop     hl                  ; restore filename start
                call    parse_disk_fcb      ; build DISK_FCB; HL -> closing '"'
                ld      a,(hl)
                cp      '"'                 ; consume the closing quote
                jp      nz,load_error
                inc     hl
                ; --- optional ,A -> ASCII listing save; else tokenised ------
                call    skip_spaces
                cp      ','
                jp      z,sav_ascii_flag    ; SAVE"name",<flag> -> check for ,A
                or      a
                jp      nz,load_error       ; trailing junk after the name
                ld      a,SV_OP_SAV_DISK
                jp      sv_tenant           ; SAVE -> disk, tokenised (fall-through entry)

; --- SAVE"name",A -> ASCII listing save --------------------------------------
; sav_ascii_flag: HL is at the ',' after the filename. Accept only ",A" (any
; case); anything else -> error.
sav_ascii_flag:
                inc     hl                  ; past the ','
                call    skip_spaces
                call    upcase
                cp      'A'
                jp      nz,load_error       ; only ,A is supported
                inc     hl                  ; past the 'A'
                call    skip_spaces
                or      a
                jp      nz,load_error       ; trailing junk after ,A
                ; fall through to ascii_save

; ascii_save — write the current program as an ASCII (SAVE",A") listing to disk.
; Reuses the LIST detokeniser walk (list_walk, list.asm) with the PRINT#-to-file
; sink: create the file, route pchar to it via PRDEST=1, walk = number + space +
; detok-body + CRLF per line, append the Ctrl-Z ($1A) soft-EOF, restore the screen
; sink, then flush + Close. A disk-full mid-listing is best-effort (pchar's file
; path, same as PRINT#). Clean-room: public ASCII listing format + our own
; detokeniser; no reference-ROM read. See basic/docs/spec-ascii-saveload.md §5.
ascii_save:
                call    disk_write_begin    ; create/truncate; reset the write state
                ld      a,1
                ld      (PRDEST),a          ; route pchar (LIST's emit) to the file
                call    list_walk           ; number + space + detok + CRLF, each line
                ld      a,$1A               ; Ctrl-Z soft-EOF (ASCII program terminator)
                call    pchar
                xor     a
                ld      (PRDEST),a          ; restore the screen sink before Close
                jp      disk_write_end      ; flush partial sector + stamp dir + Close

; --- tape SAVE path ---
sav_is_cas:
                pop     af                  ; discard saved filename start (HL past "CAS:")
                ; HL now points just past "CAS:" inside the quotes.
                ; Parse filename: up to 6 chars until '"', space-pad to 6.
                call    tape_parse_name     ; fills TSV_NAME; HL -> closing '"'
                ld      a,(hl)
                cp      '"'
                jp      nz,load_error
                inc     hl                  ; past closing '"'
                ; --- optional ,A -> ASCII listing save to tape; else tokenised ---
                call    skip_spaces
                cp      ','
                jr      z,sav_cas_flag      ; SAVE"CAS:name",<flag> -> check for ,A
                or      a
                jp      nz,load_error       ; trailing junk after the name
                jp      tape_save_basic     ; no flag -> tokenised (jp: out of jr range)
sav_cas_flag:
                inc     hl                  ; past the ','
                call    skip_spaces
                call    upcase
                cp      'A'
                jp      nz,load_error       ; only ,A is supported
                inc     hl                  ; past the 'A'
                call    skip_spaces
                or      a
                jp      nz,load_error       ; trailing junk after ,A
                ; fall into cas_ascii_save

; cas_ascii_save — write the current program as an ASCII (SAVE"CAS:",A) listing to
; cassette. Header block = TAPOON(long) + 10x$EA + 6-char name (TSV_NAME) + TAPOOF,
; mirroring tape_save_basic's $D3 header. Body = the LIST detokeniser walk
; (list_walk) piped through a new tape sink (PRDEST=1, PRDEV=3 -> cas_wbyte), framed
; into fixed 256-byte data blocks per §0.1: each block a short leader, a Ctrl-Z
; ($1A) EOF after the listing, and the final block padded to 256 with $1A. Baud is
; whatever the active LOW word selects (CSAVE",speed / default 1200 via TAPOON's
; cas_seed); no new speed parsing. Reaches here with TSV_NAME filled. Clean-room:
; public ASCII listing format + our own detokeniser + MSX2 TH cassette block
; framing; no reference-ROM read. See basic/docs/spec-cas-ascii-saveload.md §5.
cas_ascii_save:
                call    cas_write_ea_header ; $EA header block (name in TSV_NAME); CAS_WCNT=0
                jp      c,load_error
                ld      a,1
                ld      (PRDEST),a          ; route pchar (LIST's emit) to a sink
                ld      a,3
                ld      (PRDEV),a           ; sink 3 = cassette (cas_wbyte)
                call    list_walk           ; number + space + detok body + CRLF/line
                call    cas_ascii_finish    ; Ctrl-Z EOF + pad the final block (flush)
                xor     a
                ld      (PRDEST),a          ; restore the screen sink
                ld      (PRDEV),a           ; restore the default (disk) device
                ret                         ; back to the REPL

; cas_write_ea_header — write the $EA cassette header block for the file named in
; TSV_NAME: TAPOON(long leader) + 10x $EA (ASCII id) + 6-char name (tape_name_emit)
; + TAPOOF, then reset the data-block fill counter CAS_WCNT to 0 (the first data
; byte opens block 1). Shared by cas_ascii_save (SAVE"CAS:",A) and oo_dev_cas
; (OPEN"CAS:" FOR OUTPUT). All loops are tight (uniform inter-byte gaps).
;   out: CF set = a TAPOON/TAPOUT error (caller aborts).
cas_write_ea_header:
                ld      a,$FF               ; non-zero -> long leader (new file)
                call    TAPOON
                ret     c
                ld      a,10
                ld      (TSV_CNT),a
caw_id:
                ld      a,ASCII_ID          ; $EA
                call    TAPOUT
                ret     c
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,caw_id
                call    tape_name_emit
                ret     c
                call    TAPOOF              ; end of header block
                xor     a
                ld      (CAS_WCNT),a        ; 0 bytes -> first byte opens block 1
                ret

; cas_ascii_finish — end a cassette ASCII data stream: append the Ctrl-Z ($1A) EOF,
; then pad the current 256-byte block with $1A until it fills (cas_wbyte flushes it
; when the 256th byte lands). Shared by cas_ascii_save and the OPEN"CAS:" OUTPUT
; CLOSE (fch_do_close_ch). Clobbers all (via cas_wbyte).
cas_ascii_finish:
                ld      a,$1A               ; Ctrl-Z soft-EOF
                call    cas_wbyte
caf_pad:
                ld      a,(CAS_WCNT)
                or      a
                ret     z                   ; count wrapped to 0 -> block flushed
                ld      a,$1A
                call    cas_wbyte
                jr      caf_pad

; cas_wbyte — BUFFER one program byte into CAS_WBUF for the current 256-byte tape
; data block (§0.1). It does NOT TAPOUT per byte: cassette signalling is real-time on
; WRITE just as it is on read, so emitting each byte as list_walk produces it would
; interleave TAPOUT with list_walk's detokenise work (list_num / detok) and stamp
; NON-UNIFORM inter-byte gaps into the tape — TAPIN then loses sync on reload (a
; 2-line file read back only "10 " before failing). Instead bytes accumulate in RAM
; and, when the 256th fills the block, cas_flush_block emits the WHOLE block in one
; tight TAPOUT loop (uniform gaps, exactly like tape_save_basic's data-block loop —
; the write mirror of cal_refill's tight TAPIN*256 slurp). Called from pchar's
; PRDEV=3 sink, which has already saved every register; all state is the RAM cell
; CAS_WCNT, so cas_wbyte + cas_flush_block may clobber freely.
;   in: A = byte to buffer.
cas_wbyte:
                ld      c,a                 ; C = byte (survives the counter load)
                ld      a,(CAS_WCNT)
                ld      l,a
                ld      h,CAS_WBUF >> 8     ; HL = CAS_WBUF + CAS_WCNT (page-aligned)
                ld      (hl),c              ; buffer the byte (no tape I/O)
                inc     a
                ld      (CAS_WCNT),a        ; pos++ ; 255 -> 0 wraps (8-bit)
                ret     nz                  ; block not yet full -> keep buffering
                ; wrapped 255->0: 256 bytes buffered -> flush the whole block to tape
                ; fall into cas_flush_block

; cas_flush_block — write the full 256-byte CAS_WBUF to tape as one data block:
; TAPOON(short leader) + a TIGHT TAPOUT*256 loop + TAPOOF. The loop position lives in
; CAS_WCNT (RAM; TAPOUT clobbers every register) and is 0 on entry (just wrapped), so
; the loop runs 0..255 and leaves CAS_WCNT = 0 for the next block's fill. The gaps
; between TAPOUTs are small and UNIFORM (the whole loop body is a handful of fixed
; instructions), which is what the reader's TAPIN needs — the non-uniform gaps of a
; per-byte-from-list_walk emit are exactly what broke it. CF best-effort ignored.
cas_flush_block:
                xor     a                   ; short leader -> mid-file data block
                call    TAPOON
                xor     a
                ld      (CAS_WCNT),a        ; flush from position 0 (already 0; explicit)
cas_fb_lp:
                ld      a,(CAS_WCNT)
                ld      l,a
                ld      h,CAS_WBUF >> 8     ; HL = CAS_WBUF + pos
                ld      a,(hl)
                call    TAPOUT              ; emit the byte (CF ignored: best-effort)
                ld      a,(CAS_WCNT)
                inc     a
                ld      (CAS_WCNT),a        ; pos++ ; 256 -> wraps to 0
                jr      nz,cas_fb_lp
                jp      TAPOOF              ; block complete; CAS_WCNT = 0 for next fill

; ===========================================================================
; csav_speed — parse the optional ",speed" clause of CSAVE"name"[,speed].
; speed 1 = 1200 baud, 2 = 2400 baud (published MSX-BASIC syntax). The rate is
; HONOURED by setting the active baud slot ($F406) to the selected reference
; LOW-signal-length word (CS120 $5C53 / CS240 $2D25) that the tape write path's
; cas_baud reads — the same mechanism SCREEN,,,baud uses on a real machine (which
; zerobas does not implement). The CS120/CS240 reference tables themselves are
; seeded by TAPOON's cas_seed (a real BIOS cold-init does this), so we only pick
; the active word. No change to the tape signal layer. Absent clause -> unchanged.
;
; Returns CF (not `jp load_error`) on a bad speed / trailing junk so a rejected
; speed can NOT fall through into the actual save — see the load_error-is-not-an-
; abort discipline (a `jp load_error` here would `ret` back and save anyway).
; In:  HL -> bytes after the closing '"'.   Out: CF=0 ok (HL advanced), CF=1 bad.
csav_speed:
                call    skip_spaces
                or      a
                ret     z                   ; end of statement -> no speed (CF=0)
                cp      COLON
                ret     z                   ; ':' separator -> no speed
                cp      ','
                jr      nz,csav_sp_err      ; junk after the name
                inc     hl                  ; past the comma
                ; the speed is a numeric constant -- in the tokenised stream a
                ; literal `1`/`2` is an integer TOKEN ($12/$13), not ASCII, so it is
                ; evaluated (like OPEN's channel number) rather than char-matched.
                call    eval                ; DE = speed value, HL past it
                ld      a,d
                or      a
                jr      nz,csav_sp_err      ; > 255 -> invalid speed
                ld      a,e
                cp      1
                jr      z,csav_sp_1200
                cp      2
                jr      z,csav_sp_2400
                jr      csav_sp_err         ; only ,1 / ,2 are valid
csav_sp_2400:
                ld      de,CAS_LOW_2400     ; selected active-LOW word
                jr      csav_sp_apply
csav_sp_1200:
                ld      de,CAS_LOW_1200
csav_sp_apply:
                ; Set the active LOW word so the tape write path's cas_baud selects
                ; the chosen rate. The CS120/CS240 reference tables are seeded by
                ; TAPOON's cas_seed (a real BIOS cold-init does the same), so BASIC
                ; only picks the active word here -- and leaves HL (the text cursor)
                ; untouched. DE = the selected reference LOW word.
                ld      (ACT_LOW),de        ; active LOW = the selected rate
                call    skip_spaces         ; HL is past the speed (eval advanced it)
                or      a
                ret     z                   ; clean end -> CF=0
                cp      COLON
                ret     z
                ; fall through: trailing junk after ,speed
csav_sp_err:
                scf
                ret

; ===========================================================================
; do_csave — CSAVE ["name"][,speed]  (tokenised-BASIC save to cassette)
; Entry: HL -> the bytes after the CSAVE token.
; The device is implicitly cassette (no "CAS:" prefix). The optional quoted
; name is parsed; a bare CSAVE (no name) uses a 6-space name. The optional
; ,speed clause is honoured in BOTH forms -- CSAVE"n",2 and the no-name CSAVE,2.
do_csave:
                call    skip_spaces
                or      a
                jr      z,csav_noname       ; bare CSAVE (no name)
                cp      COLON
                jr      z,csav_noname       ; CSAVE followed by : -> no name
                cp      ','
                jr      z,csav_noname       ; CSAVE ,speed -> no name, then speed
                cp      '"'
                jp      nz,load_error       ; must be a quoted name
                inc     hl                  ; past opening '"'
                call    tape_parse_name     ; fills TSV_NAME; HL -> closing '"'
                ld      a,(hl)
                cp      '"'
                jp      nz,load_error
                inc     hl                  ; past closing '"'
                call    csav_speed          ; optional ,1/,2 speed; CF=1 on bad speed/junk
                jp      c,load_error
                jr      tape_save_basic
csav_noname:
                ; no name given: fill TSV_NAME with 6 spaces, then honour an
                ; optional ,speed (CSAVE,2 with no name). csav_speed handles the
                ; end/':'/',' cases, so it is called for the bare CSAVE form too.
                ; Preserve the text cursor across the fill (csav_speed needs it).
                push    hl                  ; save text cursor (fill clobbers HL)
                ld      hl,TSV_NAME
                ld      b,6
csav_sp:
                ld      (hl),' '
                inc     hl
                djnz    csav_sp
                pop     hl                  ; restore text cursor (end / ':' / ',')
                call    csav_speed          ; optional ,1/,2 speed; CF=1 on bad speed/junk
                jp      c,load_error
                ; fall into tape_save_basic

; ===========================================================================
tape_save_basic:
                ld      a,SV_OP_SAV_CAS
                jp      sv_tenant           ; SAVE"CAS:" / CSAVE -> tape, tokenised

; ===========================================================================
; tape_parse_name — extract up to 6 filename chars from the token stream.
; in:  HL -> first char of filename, inside an open quote.
; out: TSV_NAME[0..5] = up to 6 chars, space-padded; HL -> the closing '"'
;      (or at a NUL if the string is unterminated — caller checks for '"').
; Clobbers A, B, DE.
tape_parse_name:
                ld      de,TSV_NAME
                ld      b,6
tpn_loop:
                ld      a,(hl)
                or      a
                jr      z,tpn_pad           ; end of line -> pad remaining
                cp      '"'
                jr      z,tpn_pad           ; closing quote -> pad remaining
                ld      (de),a
                inc     hl
                inc     de
                djnz    tpn_loop
                ; 6 chars consumed; skip the rest of the filename to the closing '"'
tpn_skip:
                ld      a,(hl)
                or      a
                ret     z                   ; unterminated string -> stop (caller checks)
                cp      '"'
                ret     z                   ; closing quote found
                inc     hl
                jr      tpn_skip
tpn_pad:
                ; HL is on '"' or NUL; fill remaining TSV_NAME slots with ' '
                ld      a,b
                or      a
                ret     z                   ; nothing to pad
tpn_fill:
                ld      a,' '
                ld      (de),a
                inc     de
                djnz    tpn_fill
                ret

; ===========================================================================
                include "basic/sv-tne.inc"          ; tape_name_emit (copied into the tenant)

; ===========================================================================
; (repack: tape_putword has NO resident caller once the BSAVE tape engine leaves
;  — its only callers were bsv_cas_open's three header words — so it does not get
;  a stub, it simply moves. The tenant's copy arrives with sv-tputw.inc.)

; ===========================================================================
; bsave_opt4 — classify the optional 4th BSAVE slot (,exec or ,S).
; in:  HL -> after the ,end argument (at the possible ',' or a terminator).
; out: CF SET  -> reject: a bare identifier that is neither the standalone S nor
;                 a number (closure-spec item 2 "honest at the walls"). The CALLER
;                 does `jp c,load_error` at the do_bsave level — bsave_opt4 must NOT
;                 branch to load_error itself: load_error ends in `ret`, so a `jp
;                 load_error` from inside this subroutine would RESUME do_bsave right
;                 after the `call bsave_opt4` (the stack top is do_bsave's
;                 continuation, not the dispatcher) and wrongly create the file.
;      CF CLEAR -> A = 0  no 4th argument   (HL at the terminator)
;                  A = 1  literal ",S" flag (HL past the S; DE untouched)
;                  A = 2  numeric expression (DE = value; HL past it)
; Clobbers A, BC, DE, HL. Distinguishing S-the-flag from an S-started variable: the
; flag is a lone 'S' followed by a statement terminator (NUL or ':'); "SX"/"S+1" reject.
bsave_opt4:
                call    skip_spaces
                cp      ','
                jr      z,b4_have
                xor     a                   ; no 4th argument (A=0, CF clear)
                ret
b4_have:
                inc     hl                  ; past the comma
                call    skip_spaces
                call    upcase
                cp      'S'
                jr      z,b4_maybe_s
                ; not S: a bare letter (A..Z) is a rejected identifier; anything
                ; else (digit, &H, '(', '-', ...) is a numeric exec expression.
                cp      'A'
                jr      c,b4_expr           ; below 'A' -> numeric expression
                cp      'Z'+1
                jr      nc,b4_expr          ; above 'Z' -> numeric-ish
                scf                         ; a letter other than S -> reject (CF set)
                ret
b4_maybe_s:
                push    hl                  ; remember the S position
                inc     hl
                call    skip_spaces
                or      a
                jr      z,b4_is_s           ; S then end-of-statement -> the flag
                cp      COLON
                jr      z,b4_is_s           ; S then ':' -> the flag
                pop     hl                  ; S starts a longer identifier/expr
                scf                         ; (unsupported as an exec) -> reject (CF set)
                ret
b4_is_s:
                pop     af                  ; drop the saved S position (HL kept)
                ld      a,1                 ; A = 1: ",S" flag
                or      a                   ; CF clear (success)
                ret
b4_expr:
                call    eval                ; DE = exec expression value
                ld      a,2                 ; A = 2: expression
                or      a                   ; CF clear (success)
                ret

; ===========================================================================
; expect_comma_eval — skip spaces, require a ',', then eval the following
; expression. DE = value, HL advanced. On a missing comma, jumps to load_error.
expect_comma_eval:
                call    skip_spaces
                cp      ','
                jp      nz,load_error
                inc     hl                  ; past the comma
                call    eval                ; DE = value, HL advanced (BC clobbered)
                ret

; ===========================================================================
                include "basic/sv-diskwr.inc"       ; disk_write_* (copied into the tenant)

; ===========================================================================
; sv_tenant — the one marshalling stub every carved engine jumps to (repack).
; Entered by `jp`, never `call`, so the stack top is do_bsave/do_save/do_csave's
; OWN return address: exactly what the un-carved `bsv_fin: jp disk_write_end` /
; `jp load_error` tails had, so success and failure both return where they used
; to (the statement dispatcher) with the stack at the same depth.
;   in: A = SV_OP_* engine selector. Everything else is already in RAM.
sv_tenant:
                ld      (SV_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SAVE
                call    subrom_call
                jp      c,subrom_absent_error
                ld      a,(SV_STAT)
                or      a
                jp      nz,load_error       ; the tenant hit sv_load_error: report ONCE
                ret
