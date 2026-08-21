; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; bload-body.inc — the BLOAD verb body (parse + dispatch + tape load + disk load).
; ===========================================================================
; Home:
;   * the sub-ROM PAGE-1 tenant (sub/bload.asm, SUBROM_IDX_BLOAD) — evicted there
;     in the repack build to free main page-1 space (docs/spec-traps-t3-key.md
;     §7.6). The fcbname-body.inc precedent, one level larger.
;
; WHY THE BODY PORTS UNCHANGED. Every name it calls resolves correctly on BOTH
; sides without editing a single line:
;   parse_disk_fcb / parse_close_run / bl_upcase — sub-local
;     (D-FNEXPR2 retired this body's only `bl_skip_spaces` call with the opening
;     quote gate; the tenant's own parse_close_run still uses it, so the clone
;     stays for that caller and not for this one)
;     clones co-located in sub/bload.asm for the
;     tenant (the resident originals must STAY resident regardless: they have
;     61/9/6 external callers between them, so they are not evicted, only copied).
;   fat_io_open / fat_io_getbyte — in the sub-ROM these bind to sub-local bodies whose fat_mount /
;     fat_find / fat_open / fat_read_file_sector are the REAL implementations
;     (sub/fatprim.asm), so the marshalling round-trip disappears entirely.
;   bl_load_error — sub-local in the tenant, where it does TAPIOF + ERRMARK + sets BL_STAT
;     and rets, with the SAME stack behaviour, so control flow is unchanged and
;     the resident stub does the reporting once on the way out.
;   bl_notfound / bl_badmode — its two siblings, for the failures that are not a
;     `load error`. bl_notfound: the volume mounted and the 8.3 name is not in
;     the directory (D-BLNF). bl_badmode: the name WAS found and header byte 0 is
;     not the $FE BSAVE marker (D-BLMODE). Each files its own MSX ERR code in
;     BL_STAT — 53 and 61 — and rets the same way; the resident stub RAISES it.
;     Neither drops bl_load_error's ERRMARK landmark — these are raised errors,
;     not printed ones, and the landmark names the printed one.
;   load_handoff — the ,R exec jump. RESIDENT ON BOTH SIDES: it ends in `jp (hl)`
;     into the loaded program and never returns, so it must NOT run inside the
;     tenant's CALSLT — that would leave main page 1 switched out forever. The
;     tenant returns normally and the resident stub performs the handoff.
;
; TAPIN/TAPION/TAPIOF/WRTVRM are BIOS calls; main page 0 stays mapped while a
; page-1 tenant runs, so they are reachable from both sides unchanged.
;
; CLEAN-ROOM: extracted verbatim from our own basic/bload.asm; provenance for the
; BSAVE formats and the DSKIO/FAT12 engine is unchanged (basic/PROVENANCE.md).
; ===========================================================================

do_bload:
                ; --- parse: <name expression> [ ,R ] -----------------------
                ; ✅ D-FNEXPR2: the opening `call bl_skip_spaces` / `cp '"'` /
                ; `jp nz,bl_load_error` / `inc hl` gate is GONE. HL arrives (via
                ; BL_PTR) already pointing at a staged, '"'-terminated copy of
                ; the evaluated filename, because `str_eval` lives in main page 1
                ; and cannot be called from inside a page-1 tenant -- see the
                ; resident stub in basic/bload.asm. Everything below is unchanged:
                ; the dispatch and parse_disk_fcb walk (HL) exactly as before and
                ; neither cares where the bytes came from.
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
                call    bl_upcase              ; case-insensitive (typed may be lower)
                cp      c
                jp      nz,is_disk          ; prefix mismatch -> disk path (out of jr range)
                inc     hl
                inc     de
                jr      parse_dev
is_tape:
                pop     af                  ; discard saved filename start
                ; HL points just past "CAS:" IN THE STAGED COPY, so the closing
                ; '"' there is fname_expr's terminator and not program text; the
                ; `,R` / `,S` tail is parsed from the real cursor (D-FNEXPR2).
                ld      hl,(FN_RESUME)
                call    pcr_noquote         ; optional ,R / ,S only
                jp      c,bl_load_error
                ld      a,(VRAM_FLAG)
                or      a
                jp      nz,bl_load_error       ; ,S VRAM-from-tape not supported here
                ; --- open the tape and skip the file-header block's tone ---
                call    TAPION              ; sync block 1 (file header)
                jp      c,bl_load_error

                ; --- file-header block: 10x BINARY_ID + 6-char filename ---
                ; spec-bload-r.md §1: header block is 16 bytes; byte 0 is the
                ; binary-file id. We verify the id and discard the rest.
                call    TAPIN
                jp      c,bl_load_error
                cp      BINARY_ID           ; must be a binary (BSAVE) file
                jp      nz,bl_load_error
                ld      b,15                ; remaining header bytes
skip_hdr:
                push    bc                  ; TAPIN trashes all regs
                call    TAPIN
                pop     bc
                jp      c,bl_load_error
                djnz    skip_hdr

                ; --- data block: skip its tone, then read the 6-byte header --
                call    TAPION              ; sync block 2 (data)
                jp      c,bl_load_error

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
                jp      c,bl_load_error
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
    IF SUB_BUILD
                ; TENANT: do nothing. This tail ends in `jp (hl)` INTO THE LOADED
                ; PROGRAM and never returns -- inside the tenant's CALSLT that would
                ; leave main page 1 switched out forever. Return normally instead and
                ; let the resident stub (basic/bload.asm) perform the handoff; RUNFLAG
                ; and EXECPTR are already in RAM for it.
                ret
    ELSE
                ld      a,(RUNFLAG)
                or      a
                ret     z                   ; plain BLOAD: return to caller
                ld      hl,(EXECPTR)
                jp      (hl)
    ENDIF

; ===========================================================================
; Disk path: parse a disk filename into the scratch FCB, then route to the
; placeholder. This item is PARSE-ONLY — do_disk_bload deliberately falls
; through to bl_load_error; the NEXT TODO item ("Disk BLOAD execute") fills it in.
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
                pop     hl                  ; HL = filename start (staged copy)
                call    parse_disk_fcb      ; build DISK_FCB; HL -> closing '"'
                ; --- shared ,R parse, from the PROGRAM cursor (D-FNEXPR2) ---
                ld      hl,(FN_RESUME)
                call    pcr_noquote
                jp      c,bl_load_error
                ; FCB is fully built (DISK_FCB_DRV + DISK_FCB_NAME) and RUNFLAG
                ; is set. Hand off to the disk loader.
                jp      do_disk_bload

                include "basic/pdfcb-body.inc"

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
                jp      z,bl_load_error
                ; (2) open the file via the FAT12 engine (mount + find + prime).
                ; D-BLNF: unrolled across fat_io_open's OWN mount/find boundary so
                ; the two failures can be told apart. A carry out of fat_mount is a
                ; missing/unreadable volume -> the unchanged `load error`; a carry
                ; out of fat_io_find is "mounted fine, the name is not there" ->
                ; ERR 53 `File not found`, which is what both references raise
                ; (docs/loaderr-msx1-characterization.md). This is the SAME
                ; distinction df_or_loaderr makes on the resident side; it cannot
                ; use that test because here fat_find is the REAL sub-side
                ; primitive and nothing writes DISKOP_OP (see this file's header).
                call    fat_mount
                jp      c,bl_load_error        ; no volume / I-O error
                call    fat_io_find            ; find + prime the sequential reader
                jp      c,bl_notfound          ; the 8.3 name is not in the directory
                ; (3a) header byte 0 must be the BSAVE disk marker $FE.
                call    fat_io_getbyte
                jp      c,bl_load_error
                cp      BSAVE_DISK_ID
                jp      nz,bl_badmode          ; D-BLMODE: the file EXISTS and is
                                               ; not a BSAVE binary -- a DIFFERENT
                                               ; error from both `load error` and
                                               ; `File not found`, and the ONLY arm
                                               ; retargeted here. The `jp c` above
                                               ; is an I/O failure on the very
                                               ; first byte, whose reference face
                                               ; is unmeasured, so it keeps the
                                               ; shared tail's safe default.
                ; header bytes 1..6: start(LE), end(LE), exec(LE) into the same
                ; CURPTR/ENDPTR/EXECPTR vars the tape path uses.
                call    fat_io_getbyte
                jp      c,bl_load_error
                ld      (CURPTR),a          ; start low
                call    fat_io_getbyte
                jp      c,bl_load_error
                ld      (CURPTR+1),a        ; start high
                call    fat_io_getbyte
                jp      c,bl_load_error
                ld      (ENDPTR),a          ; end low
                call    fat_io_getbyte
                jp      c,bl_load_error
                ld      (ENDPTR+1),a        ; end high
                call    fat_io_getbyte
                jp      c,bl_load_error
                ld      (EXECPTR),a         ; exec low
                call    fat_io_getbyte
                jp      c,bl_load_error
                ld      (EXECPTR+1),a       ; exec high
                ; (3b) stream data bytes into [start..end] inclusive. With ",S"
                ; (VRAM_FLAG) the start/end/exec header words are VRAM addresses
                ; and each byte is stored via WRTVRM ($004D) instead of a RAM
                ; write; the loop shape is otherwise identical.
disk_load_loop:
                call    fat_io_getbyte
                jp      c,bl_load_error        ; ran out before reaching end -> error
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
