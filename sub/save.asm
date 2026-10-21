; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — save.asm  (the SAVE / BSAVE / CSAVE TAPE write-engine tenant)
; ===========================================================================
; 🏗️ D-ROMSIZE step 1 (2026-10-19): THE TAPE ENGINES ONLY. This tenant was BLOAD's
; mirror image -- the four WRITE ENGINES of the save family, evicted from main
; page 1 into sub-ROM PAGE 1 (docs/decision-fund-time-and-t5.md, D-FUND-1) to
; fund `TIME` and interrupt-traps T5 from ONE carve. The two DISK engines have
; left it for disk.rom, which keeps a real MSX's disk BASIC: tokenised SAVE in
; step 12 (D-SAVEPORT, hk_dpsave), BSAVE on 2026-10-19 (hk_dpbsave, H_FOPEN
; selector FOPEN_SEL_BSAVE -- the CF-3300's BSAVE enters $FE5D exactly once,
; scratchpad/bsave_hook_run.out). With BSAVE went the last reason this tenant
; included a disk write path at all: sv-bsvdisk.inc, sv-diskwr.inc and the
; sequential write cursor (fatiocreate-body.inc / fatiow-body.inc) over this
; ROM's second FAT engine (sub/fatprim.asm) are disk.rom's alone now. What is
; left is BSAVE "CAS:" and the shared cassette tokenised writer SAVE"CAS:" and
; CSAVE end in, shared through basic/sv-*.inc.
;
; WHY PAGE 1. A page-1 tenant runs with main page 1 switched out and the BIOS in
; page 0, so the tape engines call TAPOON / TAPOUT / TAPOOF directly. (The
; original reason -- fatprim's write primitives as in-page calls -- left with the
; disk engines.)
;
; WHAT STAYS RESIDENT, and why each one has to:
;   * THE WHOLE PARSE. Every save verb evaluates its arguments with `eval`, and
;     `eval` is main page 1 — switched out while this tenant runs. So the BSAVE /
;     SAVE / CSAVE statements and their argument parsers stay out of this
;     tenant (in basic/save.asm until D-P0CB slice C2; sub2/loadsave.asm since,
;     which reaches main's eval through p0cb). The
;     happy consequence is that this tenant needs NO cursor and NO argument
;     marshalling: by the time it is entered every value is already in its RAM
;     home (TSV_NAME, CURPTR, TSV_END, EXECPTR). Only SV_OP in and SV_STAT out
;     ride.
;   * The `,A` ASCII-listing path (cas_ascii_save). It drives list_walk/pchar —
;     the PAGE-0 detokeniser tenant — which a page-1 tenant cannot reach.
;   * cas_wbyte / cas_flush_block (pch_file's sink), tape_parse_name
;     (oo_dev_cas), cas_write_ea_header (oocas_do_out), cas_ascii_finish
;     (fdcc_cas_out), tape_name_emit (cas_write_ea_header's own callee) — all
;     have callers outside save.asm. Copies here cost no main page-1 bytes.
;
; ERROR PATH. A tape engine's TAPOON / TAPOUT failure (Ctrl-STOP in the write,
; D-CASWBRK) jumps to `sv_tape_err`: SV_STAT 19, TAPIOF, ERRMARK, and an ABORT to
; save_tenant from whatever depth (D-DISKFULLRETRY made the unwind: `svt_go` notes
; SP at dispatch and sv_fail restores it). The resident stub sees SV_STAT and
; raises it ONCE -- `Device I/O error`, as the VG-8020 does. (`sv_load_error`, the
; disk engines' reporter, went with them on 2026-10-19: its history -- the
; resume-into-disk_putbyte that retried a doomed flush on every byte, a 16 KB
; BSAVE onto a full disk running 900 s here against 3.2 s on the CF-3300 -- is in
; scratchpad/bsvfull_probe.py and bsvfull_before.out, and disk.rom's reporter
; keeps the abort.)
;
; INTERRUPTS. The cassette engines hold the CPU for the length of a tape write.
; subrom_call enters DI, so this tenant re-enables interrupts at entry and
; disables them before returning — the bload_tenant precedent: an IRQ vectors to
; $0038 in MAIN page 0, which stays mapped throughout a page-1 tenant, and
; htimi_guard (basic/subromcall.asm) sees that page 1 is not main-ROM and skips
; the PLAY/trap seam for that frame.
;
; MARSHALLING: SV_OP in (the engine selector), SV_STAT out (0 = written,
; 19 = the tape write broke). subrom_call clobbers every register and forces CF=0
; on return, so nothing rides in registers — the fatprim/fcbname/bload pattern.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/save.asm.
; Provenance for the BSAVE/BASIC tape format is unchanged (basic/PROVENANCE.md).
; The dispatch glue is own-design, the bload/fatprim precedent. No reference-ROM
; disassembly. See sub/PROVENANCE.md.
; ===========================================================================

; --- save_tenant: the SUBROM_IDX_SAVE entry --------------------------------
; Each engine is `call`ed rather than jumped to, so sv_fail's `ret` from any
; depth inside it lands back here and the DI/return discipline below still runs.
; The engines' own `ret` tails reach the same place on success.
save_tenant:
                xor     a
                ld      (DISKOP_ERR),a      ; D-DISKERR: no DSKIO failure pending yet
                ld      (SV_STAT),a         ; assume success; sv_tape_err flips it
                ei                          ; the tape engines need a live ISR;
                                            ; htimi_guard makes that safe while
                                            ; page 1 is ours
                call    svt_go              ; every engine, and sv_fail's
                                            ; abort, returns HERE
                di                          ; subrom_call's CALSLT returns under DI
                ret
; svt_go -- note SP (= the return address into save_tenant) and jump to the
; engine; D-DISKFULLRETRY made the error path (now sv_fail) unwind to that SP.
svt_go:
                ld      (SVT_SP),sp
                ld      a,(SV_OP)
                ; 2026-10-19: the two DISK selectors (0 BSAVE, 2 SAVE) are gone --
                ; disk.rom writes both files -- so 1 and 3 are all that arrive.
                dec     a
                jp      z,bsv_cas_open      ; SV_OP_BSV_CAS
                jp      tape_save_basic     ; SV_OP_SAV_CAS

; sv_fail -- record the SV_STAT code in A and ABORT to save_tenant, whatever depth
; it is reached from (D-DISKFULLRETRY; the header's ERROR PATH note).
sv_fail:                                    ; A = the SV_STAT code
                ld      (SV_STAT),a
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      sp,(SVT_SP)         ; D-DISKFULLRETRY: ABORT, from any depth
                ret                         ; -> save_tenant, after `call svt_go`
; sv_tape_err -- a TAPE engine's TAPOON/TAPOUT failed (D-CASWBRK: Ctrl-STOP in
; the write). SV_STAT 19 and sv_tenant RAISES it -- `Device I/O error`, as the
; VG-8020 does. Not through DISKOP_ERR: a stale 19 there would outlive this.
sv_tape_err:
                ld      a,19
                jr      sv_fail

; --- sub-local COPIES of the resident helpers the engines call --------------
; tape_name_emit keeps a resident caller too (header, "WHAT STAYS RESIDENT"), so
; this is a duplicate, not an eviction. Shared source, so they cannot drift.
                include "basic/sv-tne.inc"           ; tape_name_emit
; (2026-10-19: sv-diskwr.inc -- disk_write_begin / putbyte / write_end -- and the
; sequential FAT12 write cursor, fatiocreate-body.inc / fatiow-body.inc, are no
; longer included: their last caller here was BSAVE's disk engine, which is
; disk.rom's now, and disk.rom includes its own copies. The cursor bound to
; sub/fatprim.asm's fat_dir_create / fat_flush_data_sector / fat_dir_update, the
; WRITE half of this ROM's FAT engine, which nothing here calls any more. BLOAD's
; disk read path (sub/bload.asm) used the read half until later the same day, when
; it moved to disk.rom too and the engine left this ROM -- sub/fatprim.asm.)
; (t_fat_io_create / t_fat_io_close, fatprim rows 23/24 since SBH-3, are gone:
; S10 increment 3, D-ASAVEDOUT, 2026-10-08.)

; --- the two TAPE engines, shared through basic/sv-*.inc ---------------------
; (basic/sv-bsvdisk.inc -- BSAVE's disk engine -- left for disk.rom on
; 2026-10-19; sv-savdisk.inc, tokenised SAVE's, in step 12.)
                include "basic/sv-bsvcas.inc"        ; bsv_cas_open .. bsv_cas_fin
                include "basic/sv-tsb.inc"           ; tape_save_basic .. tsb_fin
                include "basic/sv-tputw.inc"         ; tape_putword (BSAVE tape header)
