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
; do_bsave — BSAVE "device:name",start,end[,exec]
; Entry: HL -> the bytes after the BSAVE token (verbatim ASCII filename, then the
; crunched address args: comma + &H/decimal expression each).
do_bsave:
                xor     a
                ld      (VRAM_FLAG),a       ; default RAM source; ",S" sets it below
                call    skip_spaces
                ld      a,(hl)
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
                ; --- create the file and set the DTA -----------------------
                call    disk_write_begin    ; require DISKSLOT_OK; Set-DTA; Create
                ; --- 7-byte header: $FE start(LE) end(LE) exec(LE) ----------
                ; disk_putbyte clobbers ALL registers (its CALSLT may flush a
                ; record), so each 16-bit field is emitted via disk_putword, which
                ; reloads the word from its RAM home for the high byte rather than
                ; trusting a register across the call.
                ld      a,BSAVE_DISK_ID     ; $FE
                call    disk_putbyte
                ld      hl,CURPTR           ; start (LE)
                call    disk_putword
                ld      hl,DSV_END          ; end (LE)
                call    disk_putword
                ld      hl,EXECPTR          ; exec (LE)
                call    disk_putword
                ; --- data bytes [start..end] inclusive, RAM or VRAM --------
                ; With ",S" (VRAM_FLAG) the start/end are VRAM addresses and each
                ; byte is fetched via RDVRM ($004A) instead of a RAM read; the
                ; loop shape is otherwise identical.
bsv_data:
                ld      hl,(CURPTR)
                ld      a,(VRAM_FLAG)
                or      a
                jr      z,bsv_data_ram
                call    RDVRM               ; HL=CURPTR (VRAM addr) -> A
                jr      bsv_data_put
bsv_data_ram:
                ld      a,(hl)              ; HL=CURPTR (RAM addr) -> A
bsv_data_put:
                call    disk_putbyte
                ld      hl,(CURPTR)
                ld      de,(DSV_END)
                ld      a,h
                cp      d
                jr      nz,bsv_next         ; high bytes differ -> more to do
                ld      a,l
                cp      e
                jr      z,bsv_fin           ; cur == end -> last byte written
bsv_next:
                ld      hl,(CURPTR)
                inc     hl
                ld      (CURPTR),hl
                jr      bsv_data
bsv_fin:
                jp      disk_write_end      ; flush + Close + back to the prompt

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
                ; --- tape header block: TAPOON(long) + 10x$D0 + 6-char name + TAPOOF ---
                ld      a,$FF               ; non-zero -> long header
                call    TAPOON
                jp      c,load_error
                ; emit 10x BINARY_ID ($D0)
                ld      a,10
                ld      (TSV_CNT),a
bsv_cas_id:
                ld      a,BINARY_ID         ; $D0
                call    TAPOUT
                jp      c,load_error
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,bsv_cas_id
                ; emit 6-char name from TSV_NAME
                call    tape_name_emit
                jp      c,load_error
                call    TAPOOF              ; end of header block
                ; --- tape data block: TAPOON(short) + start/end/exec + data + TAPOOF ---
                xor     a                   ; zero -> short header
                call    TAPOON
                jp      c,load_error
                ; start (LE): low byte then high byte, each from CURPTR
                ld      hl,CURPTR
                call    tape_putword        ; emits (HL) then (HL+1)
                jp      c,load_error
                ; end (LE)
                ld      hl,TSV_END
                call    tape_putword
                jp      c,load_error
                ; exec (LE)
                ld      hl,EXECPTR
                call    tape_putword
                jp      c,load_error
                ; data bytes RAM[start..end] inclusive; CURPTR = start
bsv_cas_data:
                ld      hl,(CURPTR)
                ld      a,(hl)
                call    TAPOUT
                jp      c,load_error
                ld      hl,(CURPTR)
                ld      de,(TSV_END)
                ld      a,h
                cp      d
                jr      nz,bsv_cas_next
                ld      a,l
                cp      e
                jr      z,bsv_cas_fin       ; cur == end -> done
bsv_cas_next:
                ld      hl,(CURPTR)
                inc     hl
                ld      (CURPTR),hl
                jr      bsv_cas_data
bsv_cas_fin:
                call    TAPOOF              ; end of data block; motor off
                ret                         ; back to the REPL

; ===========================================================================
; do_save — SAVE "device:name"   (tokenised-BASIC save; ,A out of scope)
; Entry: HL -> the bytes after the SAVE token.
do_save:
                call    skip_spaces
                ld      a,(hl)
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
                ld      a,(hl)
                cp      ','
                jp      z,sav_ascii_flag    ; SAVE"name",<flag> -> check for ,A
                or      a
                jp      nz,load_error       ; trailing junk after the name
                ; --- (no flag) tokenised save: create + $FF marker + image --
                call    disk_write_begin
                ; --- $FF tokenised-BASIC disk marker -----------------------
                ld      a,BASIC_DISK_ID     ; $FF
                call    disk_putbyte
                ; --- program image: TXTBASE .. PRGEND+1 inclusive ----------
                ; PRGEND points at the $0000 end-of-program marker (program.asm),
                ; so the last image byte is PRGEND+1. Walk inclusive.
                ld      hl,TXTBASE
                ld      (DSV_PTR),hl
                ld      hl,(PRGEND)
                inc     hl                  ; last image byte = PRGEND+1
                ld      (DSV_END),hl
sav_data:
                ld      hl,(DSV_PTR)
                ld      a,(hl)
                call    disk_putbyte
                ld      hl,(DSV_PTR)
                ld      de,(DSV_END)
                ld      a,h
                cp      d
                jr      nz,sav_next
                ld      a,l
                cp      e
                jr      z,sav_fin
sav_next:
                ld      hl,(DSV_PTR)
                inc     hl
                ld      (DSV_PTR),hl
                jr      sav_data
sav_fin:
                jp      disk_write_end

; --- SAVE"name",A -> ASCII listing save --------------------------------------
; sav_ascii_flag: HL is at the ',' after the filename. Accept only ",A" (any
; case); anything else -> error.
sav_ascii_flag:
                inc     hl                  ; past the ','
                call    skip_spaces
                ld      a,(hl)
                call    upcase
                cp      'A'
                jp      nz,load_error       ; only ,A is supported
                inc     hl                  ; past the 'A'
                call    skip_spaces
                ld      a,(hl)
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
                ld      a,(hl)
                cp      ','
                jr      z,sav_cas_flag      ; SAVE"CAS:name",<flag> -> check for ,A
                or      a
                jp      nz,load_error       ; trailing junk after the name
                jp      tape_save_basic     ; no flag -> tokenised (jp: out of jr range)
sav_cas_flag:
                inc     hl                  ; past the ','
                call    skip_spaces
                ld      a,(hl)
                call    upcase
                cp      'A'
                jp      nz,load_error       ; only ,A is supported
                inc     hl                  ; past the 'A'
                call    skip_spaces
                ld      a,(hl)
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
                ; --- header block: TAPOON(long) + 10x$EA + 6-char name + TAPOOF ---
                ld      a,$FF               ; non-zero -> long leader (new file)
                call    TAPOON
                jp      c,load_error
                ld      a,10
                ld      (TSV_CNT),a
cas_as_id:
                ld      a,ASCII_ID          ; $EA
                call    TAPOUT
                jp      c,load_error
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,cas_as_id
                call    tape_name_emit
                jp      c,load_error
                call    TAPOOF              ; end of header block
                ; --- data blocks (256-byte framed, opened lazily by cas_wbyte) ----
                xor     a
                ld      (CAS_WCNT),a        ; 0 bytes -> first byte opens block 1
                ld      a,1
                ld      (PRDEST),a          ; route pchar (LIST's emit) to a sink
                ld      a,3
                ld      (PRDEV),a           ; sink 3 = cassette (cas_wbyte)
                call    list_walk           ; number + space + detok body + CRLF/line
                ; append the EOF Ctrl-Z, then pad the final block to 256 with $1A
                ld      a,$1A               ; Ctrl-Z soft-EOF (ASCII program terminator)
                call    cas_wbyte
cas_as_pad:
                ld      a,(CAS_WCNT)
                or      a
                jr      z,cas_as_done       ; count wrapped to 0 -> block auto-closed
                ld      a,$1A
                call    cas_wbyte
                jr      cas_as_pad
cas_as_done:
                xor     a
                ld      (PRDEST),a          ; restore the screen sink
                ld      (PRDEV),a           ; restore the default (disk) device
                ret                         ; back to the REPL

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
                ld      a,(hl)
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
                ld      a,(hl)
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
                ld      a,(hl)
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
; tape_save_basic — shared cassette tokenised-BASIC save path.
; Writes a two-block cassette file: header block ($D3 ×10 + 6-char name in
; TSV_NAME) then data block (program image TXTBASE..PRGEND+1 inclusive).
; Reaches here with TSV_NAME already filled and HL past the opening quote.
; Clobbers everything (TAPOUT does); no return value (jumps to load_error on
; TAPOON/TAPOUT failure, else returns to the REPL).
; Format source: MSX2 TH cassette chapter; cas_encode.py build_cas_basic().
tape_save_basic:
                ; --- header block: TAPOON(long) + 10x$D3 + 6-char name + TAPOOF ---
                ld      a,$FF               ; non-zero -> long leader
                call    TAPOON
                jp      c,load_error
                ; emit 10x BASIC_ID ($D3)
                ld      a,10
                ld      (TSV_CNT),a
tsb_id:
                ld      a,BASIC_ID          ; $D3
                call    TAPOUT
                jp      c,load_error
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,tsb_id
                ; emit 6-char name
                call    tape_name_emit
                jp      c,load_error
                call    TAPOOF              ; end of header block
                ; --- data block: TAPOON(short) + program image + TAPOOF ------
                xor     a                   ; zero -> short leader
                call    TAPOON
                jp      c,load_error
                ; Set up the image walk: TSV_PTR = TXTBASE, TSV_END = PRGEND+1
                ld      hl,TXTBASE
                ld      (TSV_PTR),hl
                ld      hl,(PRGEND)
                inc     hl
                ld      (TSV_END),hl
tsb_data:
                ld      hl,(TSV_PTR)
                ld      a,(hl)
                call    TAPOUT
                jp      c,load_error
                ld      hl,(TSV_PTR)
                ld      de,(TSV_END)
                ld      a,h
                cp      d
                jr      nz,tsb_next
                ld      a,l
                cp      e
                jr      z,tsb_fin           ; cur == end -> done
tsb_next:
                ld      hl,(TSV_PTR)
                inc     hl
                ld      (TSV_PTR),hl
                jr      tsb_data
tsb_fin:
                call    TAPOOF              ; end of data block; motor off
                ret                         ; back to the REPL

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
; tape_name_emit — emit the 6 bytes of TSV_NAME via TAPOUT.
; in:  TSV_NAME[0..5] = the name to emit.
; out: CF = set if TAPOUT reported an error; else CF = clear.
; TAPOUT clobbers every register; the loop counter is kept in TSV_CNT.
tape_name_emit:
                ld      a,6
                ld      (TSV_CNT),a
                ld      hl,TSV_NAME
                ld      (TSV_PTR),hl        ; reuse TSV_PTR as walk pointer
tne_loop:
                ld      hl,(TSV_PTR)
                ld      a,(hl)
                call    TAPOUT
                ret     c                   ; propagate error
                ld      hl,(TSV_PTR)
                inc     hl
                ld      (TSV_PTR),hl
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,tne_loop
                or      a                   ; CF = 0 (success)
                ret

; ===========================================================================
; tape_putword — emit a 16-bit little-endian word stored at address HL via
; TAPOUT (low byte then high byte). TAPOUT clobbers every register, so the
; source address is held in TSV_PTR and reloaded for the high byte.
;   in:  HL = address of a 2-byte LE word in page-3 RAM.
;   out: CF set = error; both bytes emitted on success.
tape_putword:
                ld      (TSV_PTR),hl        ; save the word's address
                ld      a,(hl)              ; low byte
                call    TAPOUT
                ret     c
                ld      hl,(TSV_PTR)        ; reload (TAPOUT clobbered HL)
                inc     hl
                ld      a,(hl)              ; high byte
                call    TAPOUT
                ret                         ; CF from TAPOUT

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
                ld      a,(hl)
                cp      ','
                jr      z,b4_have
                xor     a                   ; no 4th argument (A=0, CF clear)
                ret
b4_have:
                inc     hl                  ; past the comma
                call    skip_spaces
                ld      a,(hl)
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
                ld      a,(hl)
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
                ld      a,(hl)
                cp      ','
                jp      nz,load_error
                inc     hl                  ; past the comma
                call    eval                ; DE = value, HL advanced (BC clobbered)
                ret

; ===========================================================================
; Shared disk-write helper (the WRITE analogue of the read side's fat_io_open /
; fat_io_getbyte). Built on the loader-side FAT12 engine over the STANDARD $4010
; DSKIO entry (basic/fat.asm) — disk-ROM-independent, NOT the private bdos_entry.
; disk_write_begin creates a fresh file; disk_putbyte appends one byte (the engine
; buffers it into a 512-byte sector and flushes whole sectors as they fill);
; disk_write_end flushes the partial final sector and stamps the directory size.
; The engine tracks exact byte counts, so the on-disk file size is its true length
; (no 128-byte record zero-padding) — SAVE/BSAVE produce byte-exact images.

; disk_write_begin — require a recorded disk-ROM slot, then Create (truncate-or-
; make) the file named in DISK_FCB_NAME and arm the sequential-write iterator.
; On any failure jumps to load_error (does not return).
;
; DOCUMENTED DIVERGENCE (no write rollback): fat_io_create stamps the directory
; entry up front. If a later disk_putbyte/disk_write_end fails mid-stream (disk
; full / write error), the error path jumps to load_error WITHOUT fat_io_close, so
; the entry is left with an un-stamped size/first-cluster (a zero-length or partial
; file). Acceptable for a game loader — a failed SAVE simply needs re-issuing — and
; no caller depends on atomic write; surfaced here so it is not mistaken for a bug.
disk_write_begin:
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                call    fat_io_create       ; mount + dir-create + reset write state
                jp      c,load_error        ; disk full / dir full / write protect / I-O
                ret

; disk_putword — write the 16-bit little-endian word stored at RAM address HL out
; through disk_putbyte (low byte then high byte). disk_putbyte clobbers HL (and
; everything else), so the source address is kept in a RAM slot (DSV_PTR, which is
; otherwise only used by do_save's own loop and is free during the BSAVE header)
; and reloaded for the high byte rather than trusted in a register.
;   in:  HL = address of a 2-byte LE word in page-3 RAM.
;   out: both bytes appended to the write stream. Clobbers all (via disk_putbyte).
disk_putword:
                ld      (DSV_PTR),hl        ; remember the word's address
                ld      a,(hl)              ; low byte
                call    disk_putbyte
                ld      hl,(DSV_PTR)        ; reload (disk_putbyte clobbered HL)
                inc     hl
                ld      a,(hl)              ; high byte
                call    disk_putbyte
                ret

; disk_putbyte — append the byte in A to the open-for-write file via the FAT12
; engine (which buffers into a 512-byte sector and flushes whole sectors as they
; fill). On a write error jumps to load_error.
;   in:  A = byte to write.
;   out: byte appended. Clobbers all (CALSLT clobbers everything across a sector
;        flush's DSKIO; the engine keeps its state in RAM).
disk_putbyte:
                call    fat_io_putbyte
                jp      c,load_error        ; disk full / write error
                ret

; disk_write_end — flush the buffered partial final sector and stamp the directory
; entry with the true byte count + first cluster (fat_io_close). On a write error
; jumps to load_error. Returns to the caller's caller (the REPL) on success.
disk_write_end:
                call    fat_io_close
                jp      c,load_error
                ret                         ; back to the prompt
