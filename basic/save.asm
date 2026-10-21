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
; 🏗️ 2026-10-19 (D-ROMSIZE step 1): ONLY THE TWO TAPE ENGINES ARE STILL THE
; SUB-ROM'S. Tokenised SAVE to disk left the tenant for disk.rom in step 12
; (D-SAVEPORT, FOPEN_SEL_SAVE) and BSAVE to disk followed (FOPEN_SEL_BSAVE ->
; disk.rom hk_dpbsave): both cross H_FOPEN through one tail (sv_cross). The
; carve's account below is the history of all four; its parse argument holds
; unchanged for the disk ones -- they cross with every value in RAM.
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
; 🔴 D-WPROTECT (2026-09-28): ONTO disk_error, NOT load_error. The resident write
; paths (SAVE ,A's disk_write_begin / putbyte / end) reported a write-protected
; disk as `load error`, printed and continued, where the CF-3300 raises 68
; (scratchpad/errkeep2_probe.py wp_asave). disk_error raises the mapped DSKIO code
; when one is pending and falls to load_error otherwise -- a successful transfer
; clears DISKOP_ERR, so a failure that is not a DSKIO one keeps its old face.
; 🏗️ S10 increment 3 (D-ASAVEDOUT, 2026-10-08): the resident `sv_load_error equ
; disk_error` that stood here is GONE -- its last user in main was sv-diskwr.inc
; (SAVE ,A's disk_write_begin / putbyte / end), no longer included. SAVE ,A's
; create now fails through fopen_cross -> `jp nz,disk_error`, the same raise. In
; the tenant and in disk.rom sv_load_error is still each ROM's own reporter.

; ===========================================================================
; 🏗️ D-P0CB slice C2 (2026-10-21): THE PARSE LEFT MAIN. do_bsave, do_save and
; their arms -- fname_dev (D-NGRAM16), the disk and tape BSAVE arguments
; (expect_comma_eval, bsave_opt4, bsave_opt4_cas), SAVE's `,A` (sav_flag_a), the
; disk SAVE / BSAVE crossing tail (sv_cross -> ks_nz_diskerr), SAVE ,A to disk
; (ascii_save) and SAVE "CAS:" (cas_ascii_save), and CSAVE (do_csave, csav_speed,
; tape_parse_name / tape_parse_cut) -- are sub2/loadsave.asm's, in zerobas-sub2
; page 0, calling main back through p0cb. What stays here is what other verbs
; and the tenant share: the tape writers below (cas_write_ea_header for OPEN
; "CAS:" too, cas_ascii_finish for its CLOSE, cas_wbyte as pchar's tape sink,
; cas_flush_block), tape_name_emit, and sv_tenant (its sub-ROM call carries an
; INLINE byte, which a p0cb'd caller cannot hand over). The measured rules each
; arm encodes (D-SAVECOLON, D-SAVETAIL, D-TAPETAIL, D-CASSAVE, D-CASWBRK,
; D-KWSAVEEND, D-ASAVEDEV, D-BSAVEVAR, D-SAVETRAP, D-CSAVENAME) are kept beside
; the code in the tenant; their history is in this file's history before the
; slice.

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
                ld      e,a
                ld      d,0
                ld      hl,(CAS_BUFP)       ; D-CASFCB: the channel's buffer
                add     hl,de               ; HL = buffer + CAS_WCNT
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
                ld      e,a
                ld      d,0
                ld      hl,(CAS_BUFP)       ; D-CASFCB: the channel's buffer; the same
                add     hl,de               ;  instructions every byte, so the gaps
                ld      a,(hl)              ;  between TAPOUTs stay uniform
                call    TAPOUT              ; emit the byte
                jp      c,dpl_dio           ; D-CASWBRK: Ctrl-STOP -> 19, raised
                ld      hl,CAS_WCNT
                inc     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
                jr      nz,cas_fb_lp
                jp      TAPOOF              ; block complete; CAS_WCNT = 0 for next fill

; ===========================================================================
; (csav_speed, do_csave and tape_parse_name: MOVED to sub2/loadsave.asm --
; ls_csav_speed, ls_csave, ls_tape_parse_name -- D-P0CB slice C2.)

; ===========================================================================
                include "basic/sv-tne.inc"          ; tape_name_emit (copied into the tenant)

; ===========================================================================
; (repack: tape_putword has NO resident caller once the BSAVE tape engine leaves
;  — its only callers were bsv_cas_open's three header words — so it does not get
;  a stub, it simply moves. The tenant's copy IS `basic/sv-tputw.inc`, included
;  by `sub/save.asm` — arrived; the future tense here was stale until 2026-09-03.)

; ===========================================================================
; (bsave_opt4, bsave_opt4_cas and expect_comma_eval: MOVED to sub2/loadsave.asm
; -- ls_opt4, ls_opt4_cas, ls_comma_eval -- D-P0CB slice C2.)

; (S10 increment 3, D-ASAVEDOUT: basic/sv-diskwr.inc is no longer included
; here. ascii_save was main's last caller of disk_write_begin / _end; the
; sub-ROM save tenant and disk.rom include their own copies.)

; ===========================================================================
; sv_tenant — the one marshalling stub the carved TAPE engines are reached through
; (repack). Reached through p0cb from sub2/loadsave.asm's ls_sv_tenant (CSAVE and
; the tape BSAVE, D-P0CB slice C2); it RETURNS on success, and the tenant then
; hands main's bp_ret back as the continuation -- the handler's own `ret`, which
; is what this stub's `ret z` was when do_csave reached it by `jp`.
;   in: A = SV_OP_* engine selector. Everything else is already in RAM.
; 🗑️ 2026-10-19 (D-ROMSIZE step 1): THE DISK DECODE IS GONE WITH THE LAST DISK
; ENGINE. SV_STAT was 0 / 1 (the tenant's sv_load_error: `jr nz,disk_error`,
; ERR 70 on an empty drive, else `load error`) / 19; BSAVE's disk write is
; disk.rom's now (bsv_open -> sv_cross), and the tape engines' only failure is
; sv_tape_err's 19 (sub/save.asm). So a nonzero status IS the code: `cp 19 /
; jp z / or a / jr nz,disk_error` became `or a / ret z / jp raise_error`, the
; same answer for every value the tenant can leave, 4 B shorter -- refilled in
; front of the $6CF3 pin by the chunk below.
sv_tenant:
                ld      (SV_OP),a
                call    sc_inl1             ; D-STUBINL: D-SCCALL: tenant call + absent raise
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SAVE)
                ld      a,(SV_STAT)         ; 0 = written; 19 = a tape write broken
                or      a                   ; with Ctrl-STOP (D-CASWBRK)
                ret     z
                jp      raise_error         ; Device I/O error (motor off)

; 📌 PIN REFILL (2026-10-19): 5 B moved here from past the $73E5 pin
; (basic/main.asm) to take back the 5 B this slice freed in front of $6CF3 --
; BSAVE's disk arm sharing do_save's tail (1) and sv_tenant's decode above (4).
; Every byte removed ahead of a pinned address grows its pad (files.asm's
; `ds $6CF3 - $` behind the `jr` bridge), and Joost: no growing holes. Whole and
; entered only by label (`jp` / `jp cc` from files.asm and the channel checks),
; with no `jr` across its edges (tools/pin_plan.py chunks()); sited after
; sv_tenant's `jp`, so nothing falls into it. Its notes stay in basic/main.asm.
oo_fail_bfn:                                ; OPEN's bad-file-number reject (ERR 52)
err_badfnum_raise:                          ; D-CHDIR: PRINT#/INPUT# the wrong way (52)
                ld      a,52
                jp      raise_error
