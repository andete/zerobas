; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — save.asm  (the SAVE / BSAVE / CSAVE write-engine tenant)
; ===========================================================================
; BLOAD's mirror image. The four WRITE ENGINES of the save family — BSAVE to
; disk, BSAVE to tape, SAVE to disk (tokenised) and the shared cassette
; tokenised writer that SAVE"CAS:" and CSAVE both end in — evicted from main
; page 1 into sub-ROM PAGE 1 (docs/decision-fund-time-and-t5.md, D-FUND-1) to
; fund `TIME` and interrupt-traps T5 from ONE carve. The moved code is VERBATIM,
; shared through basic/sv-*.inc, which the lean 16 KB cart still includes at its
; original positions so that ROM stays byte-identical.
;
; WHY PAGE 1, AND WHY THAT IS THE WHOLE POINT — the same fact that made BLOAD
; affordable, on the write side. A page-1 tenant runs with main page 1 switched
; out but the sub-ROM's own page 1 mapped, so it sits beside `fatprim_tenant`
; and calls `fat_mount` / `fat_dir_create` / `fat_flush_data_sector` /
; `fat_dir_update` **sub-locally**, as ordinary in-page calls. In main page 1
; those same names are marshalling stubs that CALSLT into this very ROM.
;
; WHAT STAYS RESIDENT, and why each one has to:
;   * THE WHOLE PARSE. Every save verb evaluates its arguments with `eval`, and
;     `eval` is main page 1 — switched out while this tenant runs. So do_bsave /
;     do_save / do_csave and their argument parsers stay in basic/save.asm. The
;     happy consequence is that this tenant needs NO cursor and NO argument
;     marshalling: by the time it is entered every value is already in its RAM
;     home (DISK_FCB_NAME, TSV_NAME, CURPTR, DSV_END, TSV_END, EXECPTR,
;     VRAM_FLAG). Only SV_OP in and SV_STAT out ride.
;   * The `,A` ASCII-listing paths (ascii_save, cas_ascii_save). They drive
;     list_walk/pchar — the PAGE-0 detokeniser tenant — which a page-1 tenant
;     cannot reach. They keep resident disk_write_begin/disk_write_end, so those
;     two are COPIED here rather than moved.
;   * cas_wbyte / cas_flush_block (pch_file's sink), tape_parse_name
;     (oo_dev_cas), cas_write_ea_header (oocas_do_out), cas_ascii_finish
;     (fdcc_cas_out), tape_name_emit (cas_write_ea_header's own callee) — all
;     have callers outside save.asm. Copies here cost no main page-1 bytes.
;
; ERROR PATH. `sv_load_error` mirrors the resident `load_error`'s shape exactly
; — TAPIOF, ERRMARK, then `ret` — because the bodies reach it by `jp` from
; several stack depths, including from inside disk_putbyte, where the `ret`
; resumes the CALLER's loop rather than aborting ([[load-error-is-not-abort]]).
; That used to be preserved here as "changing it would silently change control
; flow on the error path". 🔴 D-DISKFULLRETRY (2026-10-02) MEASURED WHAT THE
; RESUME COSTS AND IT IS NOW AN ABORT: a BSAVE of 16 KB onto a disk with one
; free cluster answered 66 in 3.2 s on the CF-3300 and NOTHING on ours in a
; 900 s EMULATED run window (scratchpad/bsvfull_probe.py, bsvfull_before.out) --
; every byte after the failure resumed into disk_putbyte and retried the doomed
; flush. `svt_go` notes SP at dispatch
; and sv_load_error restores it, so the FIRST failure ends the engine, as the
; resident path (disk_error raises) and disk.rom's hk_dpsave already do. The
; message is still not printed here: the resident stub sees SV_STAT and reports
; ONCE.
;
; INTERRUPTS. The cassette engines hold the CPU for the length of a tape write.
; subrom_call enters DI, so this tenant re-enables interrupts at entry and
; disables them before returning — the bload_tenant precedent: an IRQ vectors to
; $0038 in MAIN page 0, which stays mapped throughout a page-1 tenant, and
; htimi_guard (basic/subromcall.asm) sees that page 1 is not main-ROM and skips
; the PLAY/trap seam for that frame.
;
; MARSHALLING: SV_OP in (the engine selector), SV_STAT out (0 = written,
; 1 = sv_load_error). subrom_call clobbers every register and forces CF=0 on
; return, so nothing rides in registers — the fatprim/fcbname/bload pattern.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/save.asm and
; basic/fat.asm. Provenance for the BSAVE/BASIC tape and disk formats, the DSKIO
; contract and FAT12 is unchanged (basic/PROVENANCE.md). The dispatch glue is
; own-design, the bload/fatprim precedent. No reference-ROM disassembly.
; See sub/PROVENANCE.md.
; ===========================================================================

; --- save_tenant: the SUBROM_IDX_SAVE entry --------------------------------
; Each engine is `call`ed rather than jumped to, so sv_load_error's `ret` from
; any depth inside it lands back here and the DI/return discipline below still
; runs. The engines' own tails (`ret`, or `jp disk_write_end` which rets) reach
; the same place on success.
save_tenant:
                xor     a
                ld      (DISKOP_ERR),a      ; D-DISKERR: no DSKIO failure pending yet
                ld      (SV_STAT),a         ; assume success; sv_load_error flips it
                ei                          ; the tape engines need a live ISR;
                                            ; htimi_guard makes that safe while
                                            ; page 1 is ours
                call    svt_go              ; every engine, and sv_load_error's
                                            ; abort, returns HERE
                di                          ; subrom_call's CALSLT returns under DI
                ret
; svt_go -- note SP (= the return address into save_tenant) and jump to the
; engine; D-DISKFULLRETRY made sv_load_error unwind to that SP.
svt_go:
                ld      (SVT_SP),sp
                ld      a,(SV_OP)
                or      a
                jp      z,bsv_open          ; SV_OP_BSV_DISK
                dec     a
                jp      z,bsv_cas_open      ; SV_OP_BSV_CAS
                dec     a
                ret     z                   ; SV_OP_SAV_DISK: served by disk.rom now
                jp      tape_save_basic     ; SV_OP_SAV_CAS

; sv_load_error — sub-local reporter. See the ERROR PATH note in the header: it
; ABORTS to save_tenant (D-DISKFULLRETRY), whatever depth it is reached from.
sv_load_error:
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      a,1
                ld      (SV_STAT),a
                ld      sp,(SVT_SP)         ; D-DISKFULLRETRY: ABORT, from any depth
                ret                         ; -> save_tenant, after `call svt_go`

; --- sub-local COPIES of the resident helpers the engines call --------------
; Each of these keeps a resident caller too (header, "WHAT STAYS RESIDENT"), so
; these are duplicates, not evictions. Shared source, so they cannot drift.
                include "basic/sv-tne.inc"           ; tape_name_emit
                include "basic/sv-diskwr.inc"        ; disk_write_begin/putword/
                                                     ; putbyte/write_end
; The sequential FAT12 WRITE cursor. Identical source to the resident copy, but
; here fat_mount/fat_dir_create/fat_flush_data_sector/fat_dir_update bind to
; sub/fatprim.asm's REAL implementations instead of the marshalling stubs --
; the whole reason this tenant is affordable (fatio-body.inc does the same for
; the read side in sub/bload.asm).
                include "basic/fatiocreate-body.inc" ; fat_io_create
                include "basic/fatiow-body.inc"      ; fat_io_putbyte/fwr_bytes_inc/
                                                     ; fat_io_close

; --- the four engines themselves, shared with the resident side ------------
                include "basic/sv-bsvdisk.inc"       ; bsv_open .. bsv_fin
                include "basic/sv-bsvcas.inc"        ; bsv_cas_open .. bsv_cas_fin
                include "basic/sv-tsb.inc"           ; tape_save_basic .. tsb_fin
                include "basic/sv-tputw.inc"         ; tape_putword (BSAVE tape header)
