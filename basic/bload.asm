; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; bload.asm — the BLOAD statement handler.
;
; This is the *interpreter half* of BLOAD: it does NOT decode the cassette
; signal itself (that is the BIOS "device half" — TAPION/TAPIN). It parses its
; arguments from the crunched token stream, drives the documented cassette BIOS
; contract to read a BSAVE-format binary, places the bytes in RAM, and (for ,R)
; performs the handoff by jumping to the exec address.
;
; Derived only from basic-spec/docs/spec-bload-r.md and spec-tokenise.md (this
; project's own black-box oracle observations) + the MSX2 Technical Handbook.
; No disassembly.
;
; Entry: do_bload, HL -> the bytes after the BLOAD token. spec-tokenise.md: the
; arguments are kept verbatim as ASCII, i.e. `"CAS:",R` followed by 0x00.
;
; Device-string grammar (this build):
;   "CAS:"            -> tape path (verbatim, unchanged from the original)
;   "A:name"/"B:name" -> disk path, explicit drive letter (case-insensitive)
;   "name"            -> disk path, defaults to drive A
; A disk filename needs NO new token: BLOAD arguments are kept verbatim ASCII in
; the crunch stream (spec-tokenise.md), so the tokeniser is untouched.

do_bload:
                ; --- parse: "<device>" [ ,R ] ------------------------------
                call    skip_spaces
                ld      a,(hl)
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                ; Peek for the literal "CAS:" prefix. Match it verbatim and
                ; non-destructively decide; only commit to the tape path once
                ; the full prefix matched, so a name like "CASE.BIN" falls
                ; through to the disk path cleanly.
                push    hl                  ; remember filename start
                ld      de,dev_cas          ; compare device name to "CAS:"
parse_dev:
                ld      a,(de)
                or      a
                jr      z,is_tape           ; matched all of "CAS:" -> tape
                ld      c,a                 ; expected (uppercase) char
                ld      a,(hl)              ; typed char
                call    upcase              ; case-insensitive (typed may be lower)
                cp      c
                jp      nz,is_disk          ; prefix mismatch -> disk path (out of jr range)
                inc     hl
                inc     de
                jr      parse_dev
is_tape:
                pop     af                  ; discard saved filename start
                ; HL now points just past "CAS:"; tape path continues verbatim.
                call    parse_close_run     ; closing quote + optional ,R / ,S
                jp      c,load_error
                ld      a,(VRAM_FLAG)
                or      a
                jp      nz,load_error       ; ,S VRAM-from-tape not supported here
                ; --- open the tape and skip the file-header block's tone ---
                call    TAPION              ; sync block 1 (file header)
                jp      c,load_error

                ; --- file-header block: 10x BINARY_ID + 6-char filename ---
                ; spec-bload-r.md §1: header block is 16 bytes; byte 0 is the
                ; binary-file id. We verify the id and discard the rest.
                call    TAPIN
                jp      c,load_error
                cp      BINARY_ID           ; must be a binary (BSAVE) file
                jp      nz,load_error
                ld      b,15                ; remaining header bytes
skip_hdr:
                push    bc                  ; TAPIN trashes all regs
                call    TAPIN
                pop     bc
                jp      c,load_error
                djnz    skip_hdr

                ; --- data block: skip its tone, then read the 6-byte header --
                call    TAPION              ; sync block 2 (data)
                jp      c,load_error

                ; spec-bload-r.md §1: start(LE), end(LE), exec(LE).
                ; TAPIN trashes every register, so store each byte immediately.
                call    TAPIN
                ld      (CURPTR),a          ; start low
                call    TAPIN
                ld      (CURPTR+1),a        ; start high
                call    TAPIN
                ld      (ENDPTR),a          ; end low
                call    TAPIN
                ld      (ENDPTR+1),a        ; end high
                call    TAPIN
                ld      (EXECPTR),a         ; exec low
                call    TAPIN
                ld      (EXECPTR+1),a       ; exec high

                ; --- load loop: bytes start..end inclusive, verbatim --------
                ; spec-bload-r.md §2. State lives in RAM because TAPIN trashes
                ; all registers on every call.
load_loop:
                call    TAPIN
                jp      c,load_error
                ld      hl,(CURPTR)
                ld      (hl),a              ; store the byte
                ld      de,(ENDPTR)
                ld      a,h
                cp      d
                jr      nz,load_next        ; high bytes differ -> more to do
                ld      a,l
                cp      e
                jr      z,load_done         ; cur == end -> last byte stored
load_next:
                inc     hl
                ld      (CURPTR),hl
                jr      load_loop

load_done:
                call    TAPIOF              ; motor off
                ; fall through to the shared ,R handoff tail.

; load_handoff — shared ,R exec handoff (cassette + disk paths). spec-bload-r.md
; §3 / disk BLOAD: plain BLOAD returns; ,R jumps to the exec address (RUNFLAG was
; set by the parser; CURPTR/ENDPTR/EXECPTR are filled by whichever load ran).
load_handoff:
                ld      a,(RUNFLAG)
                or      a
                ret     z                   ; plain BLOAD: return to caller
                ld      hl,(EXECPTR)
                jp      (hl)

; ===========================================================================
; Disk path: parse a disk filename into the scratch FCB, then route to the
; placeholder. This item is PARSE-ONLY — do_disk_bload deliberately falls
; through to load_error; the NEXT TODO item ("Disk BLOAD execute") fills it in.
;
; On entry to is_disk: the top of the stack holds the filename start (the
; char after the opening quote), and HL points partway through the prefix
; comparison (it must NOT be trusted — restore from the stack). DE was
; pointing into dev_cas (don't care).
;
; FCB convention (CP/M / MSX-DOS, MSX2 TH): drive code 0=default, 1=A, 2=B.
; The 11-byte 8.3 name field is space-padded ($20), upper-cased. See
; basic/sysvars.inc DISK_FCB and PROVENANCE.md §disk-BLOAD scratch FCB.
is_disk:
                pop     hl                  ; HL = filename start (after quote)
                call    parse_disk_fcb      ; build DISK_FCB; HL -> closing '"'
                ; --- shared closing-quote + ,R parse -----------------------
                call    parse_close_run
                jp      c,load_error
                ; FCB is fully built (DISK_FCB_DRV + DISK_FCB_NAME) and RUNFLAG
                ; is set. Hand off to the disk loader.
                jp      do_disk_bload

; parse_disk_fcb — parse a disk filename into the scratch FCB at DISK_FCB.
; Shared by BOTH do_bload's disk path (is_disk) and do_load's disk path so the
; drive-letter + 8.3-name logic lives in one place.
;   in:  HL -> first char of the quoted name (the byte after the opening '"'),
;             possibly an "A:"/"B:" drive prefix.
;   out: DISK_FCB_DRV = drive code (1=A, 2=B; default A when no prefix);
;        DISK_FCB_NAME = the 11-byte space-padded upper-case 8.3 field;
;        HL -> the closing '"' (so parse_close_run resumes there).
; On a malformed drive spec or a name that doesn't fit 8.3, jumps to load_error
; (does not return). Clobbers A, B, C, DE, HL.
parse_disk_fcb:
                ; --- detect an optional drive letter "X:" -------------------
                ; "A:" / "B:" (case-insensitive). Default drive = A when absent.
                ; Look at name[0] and name[1]: a letter followed by ':' is a
                ; drive spec; anything else is a bare filename on drive A.
                ld      a,1                 ; default drive code = A
                ld      (DISK_FCB_DRV),a
                ld      a,(hl)
                call    upcase
                ld      c,a                 ; C = candidate drive letter (upper)
                inc     hl
                ld      a,(hl)              ; second char
                cp      ':'
                jr      nz,no_drive         ; not "X:" -> bare name, drive A
                ; second char is ':' -> first char must be A or B
                ld      a,c
                cp      'A'
                jr      z,drive_a
                cp      'B'
                jr      z,drive_b
                jp      load_error          ; "X:" with X not A/B -> reject
drive_a:
                ld      a,1
                jr      set_drive
drive_b:
                ld      a,2
set_drive:
                ld      (DISK_FCB_DRV),a
                inc     hl                  ; HL -> char after the ':'
                jr      build_name
no_drive:
                dec     hl                  ; undo the second-char peek; HL = name[0]
build_name:
                ; HL -> first char of the bare filename (after any "X:").
                ; --- convert to the 11-byte 8.3 field at DISK_FCB_NAME ------
                call    build_83_name       ; HL advanced to the closing quote
                jp      c,load_error        ; name didn't fit 8.3 / malformed
                ret

; do_disk_bload — real disk load via the loader-side FAT12 engine over DSKIO.
;
; The FCB name at DISK_FCB_NAME is fully built (8.3 name) and RUNFLAG is set. We
; reach the file through the STANDARD $4010 DSKIO physical-sector entry of whatever
; disk ROM is in the slot (CALSLT cross-slot; slot id = DISKSLOT, recorded by the
; INIT scan) and own the FAT12/directory logic ourselves (basic/fat.asm) — NOT the
; private bdos_entry. This makes the loader disk-ROM-independent (own ROM or a
; foreign standard ROM both work). The flow:
;   fat_io_open    -> mount BPB, find the 8.3 name, prime the sequential reader.
;   fat_io_getbyte -> the file's byte stream; the first 7 bytes are the on-disk
;                     BSAVE header [$FE][start:2 LE][end:2 LE][exec:2 LE], the rest
;                     is data loaded into [start..end] inclusive.
; Then share the ,R handoff tail with the cassette path. (No Close needed on the
; read side — there is no dirty state.)
;
; Sources: DSKIO register convention + $4010 offset — MSX2 TH §5 / black-box
; CF-3300 observation (disk/docs/expansion-protocol.md); FAT12 — Microsoft FAT
; spec (ported from disk/disk.asm); disk BSAVE header — MSX-BASIC file formats
; (public MSX-BASIC file-format reference). See basic/PROVENANCE.md §disk DSKIO host engine.
do_disk_bload:
                ; (1) disk ROM slot must have been recorded by the INIT scan.
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                ; (2) open the file via the FAT12 engine (mount + find + prime).
                call    fat_io_open
                jp      c,load_error        ; not found / mount / I-O error
                ; (3a) header byte 0 must be the BSAVE disk marker $FE.
                call    fat_io_getbyte
                jp      c,load_error
                cp      BSAVE_DISK_ID
                jp      nz,load_error
                ; header bytes 1..6: start(LE), end(LE), exec(LE) into the same
                ; CURPTR/ENDPTR/EXECPTR vars the tape path uses.
                call    fat_io_getbyte
                jp      c,load_error
                ld      (CURPTR),a          ; start low
                call    fat_io_getbyte
                jp      c,load_error
                ld      (CURPTR+1),a        ; start high
                call    fat_io_getbyte
                jp      c,load_error
                ld      (ENDPTR),a          ; end low
                call    fat_io_getbyte
                jp      c,load_error
                ld      (ENDPTR+1),a        ; end high
                call    fat_io_getbyte
                jp      c,load_error
                ld      (EXECPTR),a         ; exec low
                call    fat_io_getbyte
                jp      c,load_error
                ld      (EXECPTR+1),a       ; exec high
                ; (3b) stream data bytes into [start..end] inclusive. With ",S"
                ; (VRAM_FLAG) the start/end/exec header words are VRAM addresses
                ; and each byte is stored via WRTVRM ($004D) instead of a RAM
                ; write; the loop shape is otherwise identical.
disk_load_loop:
                call    fat_io_getbyte
                jp      c,load_error        ; ran out before reaching end -> error
                ld      hl,(CURPTR)
                ld      b,a                 ; save the byte across the flag test
                ld      a,(VRAM_FLAG)
                or      a
                ld      a,b                 ; A = byte again (ld leaves Z intact)
                jr      z,dll_ram
                call    WRTVRM              ; HL=CURPTR (VRAM addr), A=byte
                jr      dll_adv
dll_ram:
                ld      (hl),a              ; HL=CURPTR (RAM addr)
dll_adv:
                ld      hl,(CURPTR)         ; reload (WRTVRM makes no reg guarantees)
                ld      de,(ENDPTR)
                ld      a,h
                cp      d
                jr      nz,disk_load_next   ; high bytes differ -> more to do
                ld      a,l
                cp      e
                jr      z,disk_load_fin     ; cur == end -> last byte stored
disk_load_next:
                inc     hl
                ld      (CURPTR),hl
                jr      disk_load_loop
disk_load_fin:
                ; (4) shared ,R handoff tail (no Close: read has no dirty state).
                jp      load_handoff

; build_83_name — convert the filename at HL into the 11-byte 8.3 field at
; DISK_FCB_NAME. EVICTED to a sub-ROM PAGE-1 tenant (SUBROM_IDX_FCBNAME) in the
; repack build to free page-1 space for the interrupt-traps T1 slice (docs/spec-
; basic-interrupt-traps.md §10.4, D-T-8c/D-T-8d). The body is now shared
; byte-identically via basic/fcbname-body.inc: inline here for the lean 16 KB
; cart (ELSE, byte-frozen), sub-ROM-resident in the tenant. The casmatch /
; cas_open_match precedent.
    IF ROM_BASE < $4000
; --- build_83_name: resident marshalling shim (repack build) ----------------
; The body (build_83_name..bn_star_fill, basic/fcbname-body.inc) moved whole to
; sub/fcbname.asm (SUBROM_IDX_FCBNAME, a page-1 tenant). Marshal the one register
; input (HL = source ptr) and the two outputs (HL advanced -> closing quote, CF =
; reject) through RAM: subrom_call clobbers every register and forces CF=0 on
; return, so neither HL nor CF can ride back directly (the fatprim/casmatch
; pattern). BN_PTR carries the pointer both ways; BN_STAT carries CF back.
;   in:  HL -> first filename char.  out: HL -> closing '"', CF = reject.
build_83_name:
                ld      (BN_PTR),hl         ; source ptr -> tenant
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FCBNAME
                call    subrom_call
                jp      c,subrom_absent_error
                ld      hl,(BN_PTR)         ; tenant wrote back the advanced ptr
                ld      a,(BN_STAT)
                rra                         ; BN_STAT bit0 -> CF (1 = reject)
                ret
    ELSE
fcb_upcase      equ     upcase              ; lean: the body's upcaser IS the
                                            ; resident upcase (a zero-byte EQU, so
                                            ; `call fcb_upcase` == the frozen cart's
                                            ; `call upcase` byte-for-byte)
                include "basic/fcbname-body.inc"    ; lean: inline, byte-identical
    ENDIF

; parse_close_run — shared tail parse used by BOTH the tape and disk paths.
; Consumes the closing '"' and an optional single option flag (,R run or ,S
; VRAM); sets RUNFLAG / VRAM_FLAG accordingly.
;   in:  HL -> the closing '"' of the device string
;   out: CF set on ANY syntax error (missing quote, unrecognized flag, or junk
;        after the flag — caller -> load_error); CF clear on success, with
;        RUNFLAG = 1 iff ,R and VRAM_FLAG = 1 iff ,S.
; "Honest at the walls" (closure-spec item 2): an unrecognized flag or a trailing
; token (a second flag, or the deferred ,offset — Q1.2/Q1.4) is a clean error,
; never a silent no-op. Only ONE option flag is allowed, so ,R and ,S cannot
; combine.
parse_close_run:
                ld      a,(hl)
                cp      '"'                 ; closing quote required
                jr      nz,pcr_err
                inc     hl
                xor     a
                ld      (RUNFLAG),a         ; default: no ,R handoff
                ld      (VRAM_FLAG),a       ; default: RAM load
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,pcr_ok            ; end of statement -> plain load
                cp      COLON
                jr      z,pcr_ok            ; statement separator -> plain load
                cp      ','
                jr      nz,pcr_err          ; junk after the quote -> error
                ; --- one option flag: ,R (run) or ,S (VRAM) ----------------
                inc     hl                  ; past the comma
                call    skip_spaces
                ld      a,(hl)
                call    upcase              ; accept ,r / ,s as well
                cp      'R'
                jr      z,pcr_run
                cp      'S'
                jr      z,pcr_vram
                jr      pcr_err             ; unrecognized flag -> error
pcr_run:
                ld      a,1
                ld      (RUNFLAG),a
                jr      pcr_flag_end
pcr_vram:
                ld      a,1
                ld      (VRAM_FLAG),a
pcr_flag_end:
                ; after the flag ONLY a statement terminator is allowed; a second
                ; flag or a trailing ,offset is rejected (not silently ignored).
                inc     hl                  ; past the flag letter
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,pcr_ok
                cp      COLON
                jr      z,pcr_ok
                ; fall through to pcr_err
pcr_err:
                scf
                ret
pcr_ok:
                or      a                   ; CF clear = success
                ret

; device name accepted by this build. Source: spec-bload-r.md §5 ("CAS:").
dev_cas:
                db      "CAS:",0

; --- error path: stop the tape, drop a marker, report, return to the prompt -
; Reached when a cassette BIOS call fails (CF set), the file is not binary, or
; the arguments do not parse. Under bare C-BIOS this fires immediately: its
; TAPION/TAPIN are stubs that always set CF (observable as $EE at ERRMARK).
load_error:
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      hl,err_io
                call    print_string
                ret
err_io:
                db      "load error",13,10,0
