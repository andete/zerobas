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
;   SAVE "CAS:F"                     -> tape ASCII: 10x$EA + 6-char name (header
;                                       block); then the LISTING in 256-byte data
;                                       blocks, Ctrl-Z terminated. ✅ D-CASSAVE:
;                                       `,A` OR NOT — this line said "tape
;                                       tokenised: 10x$D3" until 2026-08-07 and
;                                       the code matched it. Both references write
;                                       $EA here (docs/cassave-msx1-characterization.md,
;                                       decoded off the recorded tape on a VG-8020
;                                       and a CF-3300); CSAVE is the tokenised one.
;   CSAVE "F"                        -> tape tokenised: 10x$D3 + 6-char name, then
;                                       the program image. NOT the same as
;                                       SAVE"CAS:F" — measured $D3 on all three
;                                       sides, and it is the control that keeps
;                                       "SAVE"CAS:" is ASCII" from being read as
;                                       "every cassette save is ASCII".
;
; All tape writes use the TAPOON/TAPOUT/TAPOOF BIOS entry points at $00EA/$00ED/$00F0
; (zerobas-tape; sysvars.inc). TAPOUT CLOBBERS EVERY REGISTER: every loop counter
; and pointer must survive TAPOUT calls via RAM (TSV_PTR/TSV_END/TSV_CNT in page $E0).
;
; Cassette file format: two logical blocks per file (MSX2 TH cassette file format;
; cross-checked by cas_encode.py which mirrors what a real CSAVE writes):
;   Block 1 header: TAPOON(long) + 10x file-type-id + 6-char filename + TAPOOF.
;     file-type-id = $D3 (BASIC_ID) for tokenised (CSAVE only -- D-CASSAVE).
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
; while a page-1 tenant runs. 🎯 D-FNEXPR2 CASHED THAT RULE IN AT BLOAD: once a
; FILENAME is a string expression it needs `str_eval`, which is page 1 too, so
; the one piece of parse still living sub-side -- BLOAD's opening quote gate --
; came back to the resident stub (basic/bload.asm). The staged name crosses in
; STRSCR, which is RAM and mapped from both sides. So the parse stays resident — and because it does,
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
; do_bsave — BSAVE <name>,start,end[,exec]     ("device:name" or any string expr)
; Entry: HL -> the bytes after the BSAVE token. ⚠️ D-FNEXPR2: the name is a
; string EXPRESSION (it was "verbatim ASCII filename" here, and that described a
; literal-only gate); the address args are unchanged crunched expressions,
; comma + &H/decimal each, and are parsed from FN_RESUME.
; --- fname_dev: the filename EXPRESSION, then the "CAS:" device test ----------
; D-NGRAM16. Four verbs opened identically -- LOAD, RUN"name", SAVE and BSAVE:
; parse the filename as a string expression, then ask whether it names the tape.
;
; 🔴 IT IS A TAIL JUMP BECAUSE THE CALLER BRANCHES ON `dev_cmp`'s Z FLAG, and
; because `fname_expr` JUMPS OUT: `jp nc,els_tc_common` when the filename is not
; a string. Behind a helper that jump sits one frame deeper -- the D-NGRAM8 shape
; exactly, where a `call` moved an outward jump and a decline stopped declining.
; 🟢 Here it cannot bite, and the reason is checkable rather than hopeful: BOTH
; of `els_tc_common`'s exits (`stmt_error`, `type_mismatch_error`) RAISE and
; never return, so the frame they leave behind is discarded with the rest.
; That is an argument, so it has rows -- `n.load`/`n.save`/`n.bsave` drive a
; NON-STRING filename through three of the four verbs
; (scratchpad/fnamedev_probe.py). `RUN`'s own row set found a SEPARATE bug
; while it was at it -- see D-RUNARG in basic/program.asm.
;   out: HL past a matched "CAS:" prefix (restored on a miss), Z = matched.
fname_dev:
                call    fname_expr          ; HL -> the staged '"'-terminated copy
                ld      de,dev_cas
                jp      dev_cmp             ; TAIL -- Z and HL go to OUR caller

do_bsave:
                xor     a
                ld      (VRAM_FLAG),a       ; default RAM source; ",S" sets it below
                ; ✅ D-FNEXPR2: the filename is a string EXPRESSION. This was
                ; `call skip_spaces` / `cp '"'` / `jp nz,load_error` / `inc hl`:
                ; a LITERAL gate whose refusal PRINTED `load error` and RETURNED,
                ; so `BSAVE A$,&H8000,&H9000` ran on as if nothing had happened.
                call    fname_dev   ; D-NGRAM16
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                ; D-FNFUND: this was a hand-rolled copy of files.asm's dev_cmp --
                ; same upcase, same 0-terminated prefix, same "advance on a hit,
                ; restore HL on a miss" contract, 22 B against 9. The push/pop
                ; pair moved INSIDE dev_cmp, which is why bsv_is_cas below no
                ; longer discards a saved start.
                jr      z,bsv_is_cas        ; matched "CAS:" -> tape (HL past the prefix)
bsv_is_disk:
                ; HL = filename start (after the quote); build the FCB.
                call    pdfcb_resume      ; build DISK_FCB; HL -> closing '"'
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
                ; HL now points just past "CAS:" inside the quotes.
                ; Parse filename: up to 6 chars until '"', space-pad to 6.
                call    tape_parse_name     ; fills TSV_NAME[0..5]; HL -> closing '"'
                ld      hl,(FN_RESUME)      ; D-FNEXPR2: resume past the EXPRESSION
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
; do_save — SAVE <name>[,A]   ("device:name" or any string expr; tokenised-BASIC)
; Entry: HL -> the bytes after the SAVE token. ⚠️ D-FNEXPR2: the name is a string
; EXPRESSION -- `SAVE A$` is `OK` on the CF-3300 (row f.savevar) and was a
; PRINTED `load error` here, so the program carried on having saved nothing.
do_save:
                ; ✅ D-FNEXPR2: the filename is a string EXPRESSION (row f.savevar:
                ; `SAVE A$` is `OK` on the CF-3300 and was `load error` here --
                ; PRINTED, not raised, so the program carried on having saved
                ; nothing at all).
                call    fname_dev   ; D-NGRAM16
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                ; D-FNFUND: the second hand-rolled copy of dev_cmp (see do_bsave
                ; above). Identical contract; the push/pop pair is dev_cmp's now.
                jr      z,sav_is_cas        ; matched "CAS:" -> tape (HL past the prefix)
sav_is_disk:
                call    pdfcb_resume      ; build DISK_FCB; HL -> closing '"'
                ; --- optional ,A -> ASCII listing save; else tokenised ------
                call    skip_comma
                jr      z,sav_ascii_flag    ; SAVE"name",<flag> -> check for ,A
                or      a
                jp      nz,load_error       ; trailing junk after the name
                ; --- SAVE -> disk, tokenised: HAND IT TO disk.rom ------
                ; D-SAVEPORT, step 12 (spec-diskcode-eviction.md §6.6ao), same
                ; ruling and same cell as step 9's LOAD. This used to be
                ; `ld a,SV_OP_SAV_DISK / jp sv_tenant`, which ran the write
                ; engine in the SUB-ROM and reached NO hook -- so a machine with
                ; a foreign disk ROM saved through our engine anyway. The cell
                ; decides now.
                ; ⚠️ SAME EXIT CONTRACT AS `sv_tenant`: `ret` on success, and
                ; `disk_error` otherwise, which raises the mapped code when
                ; disk.rom recorded one in DISKOP_ERR and prints `load error`
                ; when it did not.
                ld      a,FOPEN_SEL_SAVE
                ld      (FOPEN_SEL),a
                ld      hl,H_FOPEN
                call    chan_gate           ; unclaimed -> ERR 5; claimed -> it ran
                ld      a,(DISKOP_STATUS)
                or      a
                ret     z                   ; 0 = written
                jp      disk_error          ; 3 = mount / disk full / write / I-O

; --- SAVE"name",A -> ASCII listing save --------------------------------------
; sav_ascii_flag: HL is at the ',' after the filename. Accept only ",A" (any
; case); anything else -> error.
sav_ascii_flag:
                call    sav_flag_a          ; the shared body, below, beside its
                                            ; other caller -- then FALL THROUGH

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
                call    list_all            ; number + space + detok + CRLF, each line
                                            ; ⚠️ list_ALL, not list_walk: since
                                            ; D-LSTRNG the walk honours LST_LO/LST_HI,
                                            ; and a preceding `LIST 20-30` would
                                            ; otherwise make this save TWO LINES
                                            ; (spec-basic-listrange.md §3.3)
                ld      a,$1A               ; Ctrl-Z soft-EOF (ASCII program terminator)
                rst     $18
                xor     a
                ld      (PRDEST),a          ; restore the screen sink before Close
                ; 🔴 D-KWSAVEEND: AND THEN THE RUN STOPS -- `SAVE"x",A` ENDS THE
                ; PROGRAM ON THE REFERENCE AND USED TO CARRY ON HERE. Measured on
                ; the CF-3300 against a control (scratchpad/saveascii_probe.py):
                ; the TOKENISED save continues normally, and after an ASCII one
                ; neither a readback nor a bare `PRINT` nor a `FILES` is reached.
                ; The mechanism was never a mystery -- this path drives the LIST
                ; walk (`list_all`), and `LIST` inside a program ENDS THE RUN on
                ; BOTH machines -- so `ex_list` finishing `jp end_line_end` was
                ; right and this tail simply did not inherit it.
                ; ⚠️ `call` + `jp`, not the old `jp`: `disk_write_end` ends in a
                ; `ret` whose comment says "back to the prompt", so the tail jump
                ; unwound one frame further than a handler body does. Calling it
                ; leaves the stack exactly where `ex_list` has it when IT reaches
                ; `end_line_end`.
                call    disk_write_end      ; flush partial sector + stamp dir + Close
                jp      end_line_end        ; ...and the run stops, as LIST's does

; --- tape SAVE path ---
sav_is_cas:
                ; HL now points just past "CAS:" inside the quotes.
                ; Parse filename: up to 6 chars until '"', space-pad to 6.
                call    tape_parse_name     ; fills TSV_NAME; HL -> closing '"'
                ld      hl,(FN_RESUME)      ; D-FNEXPR2: resume past the EXPRESSION
                ; --- optional ,A -> ASCII listing save to tape; else tokenised ---
                call    skip_comma
                jr      z,sav_cas_flag      ; SAVE"CAS:name",<flag> -> check for ,A
                or      a
                jp      nz,load_error       ; trailing junk after the name
                ; ✅ D-CASSAVE: NO FLAG IS THE SAME AS `,A` — an ASCII ($EA) tape.
                ; This arm used to `jp tape_save_basic` (tokenised, $D3), which
                ; basic/save.asm's own header table documented as intended. It is
                ; measured WRONG on BOTH references (docs/cassave-msx1-characterization.md):
                ; `SAVE"CAS:x"` writes `EA` + the full listing on a VG-8020 and a
                ; CF-3300 alike, and `,A` writes the byte-identical thing — the two
                ; spellings are one behaviour, which is what makes routing them to
                ; one path faithful rather than a conflation. `CSAVE` is the
                ; tokenised cassette write and reaches tape_save_basic by its own
                ; two paths, unchanged and MEASURED unchanged (`csave:id` = D3 on
                ; all three sides). Costs 0 B: one absolute jump for another.
                jr      cas_ascii_save      ; no flag -> ASCII, exactly as ,A does

; --- sav_flag_a: accept the `,A` of SAVE"...",A -- ONE body, TWO callers ----
; in: HL at the ',' . out: HL past the 'A' and end-of-statement checked, or the
; statement is ABORTED with `load error`.
; 🎯 THE DISK AND CASSETTE FLAG SCANS WERE TWENTY BYTES OF THE SAME PARSE, TWICE
; (tools/clone_scout.py: `sav_ascii_flag, sav_cas_flag`, page 1). They are NOT
; an `equ` alias and D-DUPSPAN2 was right to leave them alone -- they are
; byte-identical but each FALLS THROUGH to a DIFFERENT next routine
; (ascii_save / cas_ascii_save), which is precisely the entry-shape a duplicate-
; span sweep cannot see [[dupspan-slice]]. Collapsing it needs the fallthrough
; kept and only the BODY shared, which is what a `call` + fallthrough is.
; 🔴 AND THE FALLTHROUGH IS EXACTLY WHAT THE FIRST DRAFT BROKE: this body was
; written IN PLACE, between `sav_ascii_flag` and `ascii_save`, so the flag scan
; ran twice and `ascii_save` became reachable from nothing. `make basic-reloc`'s
; hard dead-code gate is what said so -- `[main] ascii_save ... ~23 B` -- on a
; build that had otherwise just succeeded, and it is the same blind spot from
; the other side: a carve that PRESERVES a fallthrough has to preserve what is
; NEXT IN THE FILE, not just what the labels say.
; ⚠️ AND THE `jp nz,load_error` OUT OF A `call`ED BODY IS SAFE FOR A MEASURED
; REASON, not a hopeful one: the abort resets SP from SAVSTK before it prints,
; so it is DEPTH-INDEPENDENT -- the same argument D-LOCPARK wrote into
; basic/missing.asm when it put eval_byte_checked behind a call.
sav_flag_a:
                rst    $10                ; past the ','
                call    upcase
                cp      'A'
                jp      nz,load_error       ; only ,A is supported
                rst    $10                ; past the 'A'
                or      a
                jp      nz,load_error       ; trailing junk after ,A
                ret

sav_cas_flag:
                call    sav_flag_a          ; the shared body, just above
                ; fall into cas_ascii_save

; cas_ascii_save — write the current program as an ASCII (SAVE"CAS:" / ",A") listing to
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
                call    list_all            ; number + space + detok body + CRLF/line
                                            ; (list_ALL -- see ascii_save above:
                                            ; a preceding LIST range must not
                                            ; truncate the tape image either)
                call    cas_ascii_finish    ; Ctrl-Z EOF + pad the final block (flush)
                xor     a
                ld      (PRDEST),a          ; restore the screen sink
                ld      (PRDEV),a           ; restore the default (disk) device
                ret                         ; back to the REPL

; cas_write_ea_header — write the $EA cassette header block for the file named in
; TSV_NAME: TAPOON(long leader) + 10x $EA (ASCII id) + 6-char name (tape_name_emit)
; + TAPOOF, then reset the data-block fill counter CAS_WCNT to 0 (the first data
; byte opens block 1). Shared by cas_ascii_save (SAVE"CAS:", ,A or not) and oo_dev_cas
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
                ld      hl,TSV_CNT
                dec     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
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
                ld      hl,CAS_WCNT
                inc     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
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
                call    skipsp_test
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
                call    skipsp_test ; HL is past the speed (eval advanced it)
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
                call    skipsp_test
                jr      z,csav_noname       ; bare CSAVE -> Missing operand
                cp      COLON
                jr      z,csav_noname       ; `CSAVE:` -> Missing operand
                cp      ','
                jr      z,csav_comma        ; `CSAVE,2` -> Syntax error (measured)
                ; 🟢 D-CSAVEEXPR (2026-09-05): A STRING EXPRESSION, like the other
                ; eight filename verbs since D-FNEXPR2 -- this was the last
                ; `cp '"'` gate in the tree, and it cost FIVE divergent rows,
                ; every one of them a NON-RAISING `load error` that `ON ERROR`
                ; could not trap. Measured on both references, which agree:
                ;
                ;   CSAVE A$      accepted (silent)   was `load error`
                ;   CSAVE A$+""   accepted            was `load error`
                ;   CSAVE 5       Type mismatch       was `load error`
                ;   CSAVE"P       accepted            was `load error`  <- see below
                ;   CLOAD 5       Type mismatch       was `load error`  (do_cload)
                ;
                ; 🔴 `CSAVE"P` -- AN UNTERMINATED LITERAL -- IS THE ROW THIS EDIT
                ; WOULD HAVE MOVED WITHOUT BEING ASKED TO, and it was measured
                ; BEFORE the edit for exactly that reason. The hand-rolled parse
                ; below demanded the CLOSING quote; `str_eval` follows MSX BASIC
                ; and auto-terminates a literal at end of line. Both references
                ; accept it silently, so the fix closes that row rather than
                ; changing it -- but "rather than" is a measurement, not a guess.
                ;
                ; 🎯 tape_parse_name IS UNCHANGED and needs no second source: it
                ; walks (HL) to a '"', and fname_expr hands back exactly that --
                ; a staged, '"'-terminated copy at STRSCR+1.
                call    fname_expr          ; HL -> the staged '"'-terminated copy
                call    tape_parse_name     ; fills TSV_NAME from the staged copy
                ld      hl,(FN_RESUME)      ; resume just past the expression
                call    csav_speed          ; optional ,1/,2 speed; CF=1 on bad speed/junk
                jp      c,load_error
                jr      tape_save_basic
csav_comma:
                ; D-CSAVENAME (2026-09-04): `CSAVE,2` -- no name, a speed --
                ; is `Syntax error` on BOTH references, a different face from the
                ; other two no-name forms. The face depends only on whether a `,`
                ; follows, which is why the three tests above now split here.
                jp      stmt_error
csav_noname:
                ; 🔴 CSAVE's NAME IS NOT OPTIONAL. This used to fill TSV_NAME with
                ; six spaces and SAVE ANYWAY -- so `CSAVE`, `CSAVE:` and `CSAVE,2`
                ; all wrote a tape the reference refuses, with NO MESSAGE. Silent
                ; acceptance, which is the worst class this project ranks.
                ; Measured on both references (scratchpad/csaveexpr_probe.py, on a
                ; fresh recording tape per row):
                ;
                ;   CSAVE      Missing operand   CSAVE:   Missing operand
                ;   CSAVE,2    Syntax error      CSAVE"P",2  accepted (control)
                ;
                ; ⚠️ THE ENTRY THAT FILED THIS CALLED THE ARGUMENT "OPTIONAL" and
                ; asked the `FILES`-style "is there an argument at all" question.
                ; There is no no-name form: the reference errors on all three.
                ; 🟢 And the six-space fill this replaces is why the change is
                ; byte-NEGATIVE rather than a spend, in a page 1 with 8 B free.
                ; 💰 D-CARVE5: this body WAS `ld a,24 / jp raise_error`, byte for
                ; byte the same five bytes as `loc_missing` (basic/missing.asm) and
                ; `g8_missing`. Jumping there saves 2 B of main page 1, which was
                ; at 1 B free on 2026-09-08 and is the shared blocker for two
                ; parked items. `loc_missing` is a bare raiser with NO side effects,
                ; so this is a jump to the same instructions, not a shared tail
                ; that decides anything [[a-shared-tail-is-not-a-decision]].
                ; ⚠️ NOT an `equ` alias, which would be free: the two `jr z,
                ; csav_noname` sites above are 2110 bytes from `loc_missing` and
                ; would each have to become a `jp` (+2 B), netting -1 instead of -2.
                jp      loc_missing         ; ERR 24
tape_save_basic:
                ld      a,SV_OP_SAV_CAS
                jp      sv_tenant           ; CSAVE -> tape, tokenised (D-CASSAVE:
                                            ; SAVE"CAS:" no longer arrives here)

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
;  a stub, it simply moves. The tenant's copy IS `basic/sv-tputw.inc`, included
;  by `sub/save.asm` — arrived; the future tense here was stale until 2026-09-03.)

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
                call    skip_comma
                jr      z,b4_have
                xor     a                   ; no 4th argument (A=0, CF clear)
                ret
b4_have:
                rst    $10                ; past the comma
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
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                jr      z,b4_is_s
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
; expression. DE = value, HL advanced. On a missing comma, RAISES ERR 2.
;
; 🔴 D-SAVETRAP: THIS USED TO `jp nz,load_error`, WHICH PRINTS AND DOES NOT RAISE.
; `BSAVE"CAS:X"` and `BSAVE"CAS:X",0` — both missing a REQUIRED positional
; argument — printed `load error` and let the program RUN ON with no error at all.
; Both references raise a TRAPPABLE `Syntax error`; measured with a witness set
; inside the ON ERROR handler, so "trapped" and "printed and continued" are
; distinguishable rather than both reading as ERR 2
; (scratchpad/savetrap_probe.py: refs ERR 2 / A=9, here ERR 0 / A=0).
; 🎯 AND THE UNTRAPPABILITY IS THE SERIOUS HALF, exactly as in D-MAXFTAIL: a
; program that guards its saves with ON ERROR was told nothing went wrong.
; 💰 BYTE-NEUTRAL — both targets are a 3-byte `jp`, and this helper's ONLY four
; callers are do_bsave's own ,start and ,end on the disk and CAS paths, so the
; change cannot reach another verb [[a-shared-tail-is-not-a-decision]].
; ⚠️ `bsave_opt4`'s stray-4th-token reject still `jp c,load_error` and is NOT
; changed here: no row measures it, because the forms that reach it have valid
; start/end and would start a real tape write. Left as filed, not as agreed.
expect_comma_eval:
                call    skip_comma
                jp      nz,stmt_error       ; ERR 2, RAISED — trappable
                inc     hl                  ; past the comma
                jp      eval                ; DE = value, HL advanced (BC clobbered)

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
                call    sc_call             ; D-SCCALL: tenant call + absent raise
                ld      a,(SV_STAT)         ; D-DISKERR: a DSKIO failure raises its code below
                or      a
                jr      nz,disk_error       ; the tenant hit sv_load_error: report ONCE --
                                            ; ERR 70 on an empty drive (D-DISKERR), else `load error`
                ret
