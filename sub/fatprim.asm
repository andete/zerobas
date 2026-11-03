; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — fatprim.asm  (FAT12 primitive/sector-layer tenant)
; ===========================================================================
; 🗑️ 2026-10-19 (D-ROMSIZE step 1): WHAT FOLLOWS IS MOSTLY HISTORY. Every row
; that reached a primitive is retired (fatprim_tenant, below): the resident shims in
; basic/fat.asm that sent them are all gone, and the last sub-ROM writer through
; this engine -- BSAVE's disk engine in the save tenant -- moved to disk.rom. The
; tenant's one live row is 23 (t_fch_hdr, OPEN's FCB header stamp, a pure RAM
; leaf). And the FAT engine it once carried is gone from this ROM: BLOAD's disk
; load, the last sub-ROM caller of its READ half, moved to disk.rom (hk_dpbload)
; later the same day, and the include went with it (the note at the end).
; The FAT12 primitive/sector layer, evicted from the repack main ROM's
; basic/fat.asm into sub-ROM PAGE 1 (docs/spec-evict-diskfile-cluster.md §11,
; Phase 1 of the disk/file cluster eviction), to free page-1 window space
; (funding D-F2-2 A2+VPEEK and the eviction roadmap beyond it).
;
; ONE index, SELECTOR-DISPATCHED (not one index per primitive): 15 marshalled
; routines would otherwise burn 15 of the scarce SUBROM_ENTRY_BASE_P1 slots
; for a single eviction. Instead `fatprim_tenant` (SUBROM_IDX_FATPRIM) reads
; a DISKOP_OP byte (RAM, set by the resident shim before subrom_call) and
; jumps to the requested primitive via a local jp table indexed by BC*3 (NOT
; HL/DE -- subrom_call passes the caller's real HL/DE through CALSLT
; untouched, spec §11, so the dispatch machinery must never touch them; A/BC/
; IX are free because none of the 15 primitives use them as an input).
;
; WHY PAGE 1, no split needed (unlike CALL FORMAT). Every one of these
; primitives is ALREADY pure CALSLT-side code (fat.asm's own header: "the
; ONLY routines that differ from disk.asm" are exactly the ones that CALSLT
; the disk ROM) -- none of them touch `eval` or any other main-page-1-only
; resident code, so the WHOLE primitive/sector layer moves as one leaf tenant,
; no resident/tenant split within a single primitive (playbook §2/§3;
; sub/format.asm needed a split only because CALL FORMAT's menu needed
; console I/O AND write_sector needed CALSLT -- no such straddle here).
;
; The shared bodies are basic/fat-prim-body.inc (dskio_calslt..fat_dir_update)
; and basic/fat-delete-body.inc (fat_delete -- kept in a separate file only
; because it sits AFTER the resident fat_io_* byte cursor in basic/fat.asm,
; so the original byte order can't be preserved by concatenating it into
; the first file; see that file's own header). Included here WHOLESALE: since
; the primitive/sector layer being moved already STARTS at dskio_calslt/
; read_sector/write_sector, this file's own copies of those (via the
; include) ARE the tenant's sub-local CALSLT path -- no separate duplication
; is needed the way sub/format.asm needed one for write_sector alone (that
; eviction moved a bulk that did NOT include write_sector itself).
;
; RESULT MARSHALLING (spec §11's uniform shim convention -- the load-bearing
; correctness point, docs/error-handling-arc lesson: green builds hide
; register/order bugs). Cy cannot ride back through subrom_call/CALSLT (its
; own `or a` always clears it, sub/format.asm's rule) -- so every primitive's
; exit path here funnels through fp_stash_ok/fp_stash_err, which persist
; {HL, A, a 0/nonzero STATUS byte} into the DISKOP result block (basic/
; sysvars.inc) before returning; the resident shim in basic/fat.asm reloads
; HL+A and reconstructs Cy from STATUS identically for every primitive. Two
; primitives need a DIFFERENT real output and get their own tail instead of
; the uniform one: name_cmp (Z, not Cy -- STATUS doubles as the Z surrogate,
; same 0=match polarity) and fat_count_free (DE, not Cy/HL -- mirrored into
; FAT_WRTMP2, its own already-RAM-visible scratch, rather than a new DISKOP
; cell; see that cell's sysvars.inc comment for why no new RAM was free).
; fat_alloc_cluster's HL (the one real caller-read HL output, field.asm
; 576/599) is covered by the uniform path -- no bespoke tail needed.
;
; CLEAN-ROOM: original code (the dispatch/marshalling glue is own-design, the
; CALL FORMAT precedent + MSX2 Technical Handbook CALSLT/EXBRSA/sub-ROM-
; signature ABIs); the primitive bodies are copied verbatim from our own
; basic/fat.asm via basic/fat-prim-body.inc / basic/fat-delete-body.inc (see
; those files' headers, and basic/fat.asm's own header, for the full FAT12/
; DSKIO provenance / oracle citations). No reference-ROM disassembly.
; ===========================================================================

; --- fatprim_tenant: the SUBROM_IDX_FATPRIM entry --------------------------
; Read DISKOP_OP (RAM): row 23 (DISKOP_SEL_FCH_HDR) runs t_fch_hdr with the
; caller's HL (passed through CALSLT untouched by subrom_call); every other op
; is a retired row and goes straight to fp_stash_ok.
fatprim_tenant:
                xor     a
                ld      (DISKOP_ERR),a      ; D-DISKERR: no DSKIO failure pending yet
                ld      a,(DISKOP_OP)
                cp      DISKOP_SEL_FCH_HDR
                jr      nz,fp_stash_ok      ; every other row is retired
; (fp_table -- 25 `jp` rows, op 0..24 by BC*3 -- is GONE, D-SUB2RETIRE batch 3,
; 90 B: every row but 23 was `jp fp_stash_ok` (each retired by the slice named
; in its DISKOP_SEL_* equate, basic/sysvars.inc, and in `git log -- sub/fatprim.asm`),
; and 23 is the one live op (t_fch_hdr, its note below). An op that is not 23
; still gets exactly the old retired-row result: fp_stash_ok with A = the op and
; the caller's HL. The DISKOP_SEL_* numbering is unchanged; only 23 is decoded.)
t_fch_hdr:
                push    hl
                ld      a,(OO_DEVTYPE)
                add     a,a
                ld      e,a
                ld      d,0
                ld      hl,fhd_tab-2        ; FCH_MODES 1.. -> row 0..
                add     hl,de
                ld      c,(hl)              ; the mode code
                inc     hl
                ld      a,(hl)              ; the device code, 0 = the drive
                pop     hl
                ld      (hl),c              ; +0
                or      a
                jr      nz,fhd_dev
                ld      a,(DISK_FCB_DRV)
fhd_dev:
                ld      de,4
                add     hl,de
                ld      (hl),a              ; +4
                inc     hl
                inc     hl                  ; +6
                ld      a,(OO_DEVTYPE)
                cp      DOUT_MODE
                jr      z,fp_stash_ok       ; disk.rom's position stands
                ld      (hl),0
; --- uniform result-stash tails --------------------------------------------
; Persist {HL, A, STATUS} into the DISKOP block; STATUS=0 (ok) from
; fp_stash_ok, STATUS=1 (error) from fp_stash_err. A is saved BEFORE either
; clobbers it (fp_stash_err's `ld a,1`), so DISKOP_A always reflects the
; primitive's OWN real A, never our bookkeeping value.
fp_stash_ok:
                ld      (DISKOP_HL),hl
                ld      (DISKOP_A),a
                xor     a
                ld      (DISKOP_STATUS),a
                ret
; (fp_stash_err -- STATUS = 1 -- went 2026-10-19 with the last primitive wrapper
; that could fail; t_fch_hdr, the one live row, always succeeds.)

; --- per-primitive wrappers -- ALL GONE (2026-10-19) ------------------------
; t_read_sector, t_write_sector, t_name_cmp, t_fat_open, t_fat_read_fat_sector,
; t_fat_read_file_sector, t_fat_alloc_cluster, t_fat_write_fat_entry,
; t_fat_count_free, t_fat_dir_create, t_fat_dir_update and t_fat_delete each
; called a shared body and marshalled Cy / HL / A (or Z, or DE through
; FAT_WRTMP2) into the DISKOP block for a main-side shim. Every shim is gone
; (basic/fat.asm's history block), so nothing reached a wrapper; their ops now
; go straight to fp_stash_ok. The marshalling convention they implemented is still
; t_fch_hdr's exit and still fatprim_bounce's decode.

; (t_fch_restage, row 19's wrapper over fat_restage_channel, is gone with it:
; S10.C, 2026-10-15.)

; (t_fch_load (D-FCBSHAPE S0) -- GONE with S10.E, 2026-10-19; op 22 is a
; retired op. It was main's fch_load_ctx body, moved here whole so the
; block's layout was known in one ROM, and it shrank slice by slice: S10.C took
; the arm that LDIR'd an INPUT row into the FCH_STATE0 globals and re-staged its
; sector (every disk channel's row is disk.rom's FCB since then), D-FLDDESC the
; RANDOM record's copy (the record lives at block+9). What was left -- re-caching
; the block address at DOUT_BLK and MIRRORING the FCB's size (+16, LOF) and random
; record (+33, LOC) into main's FAT_FILESIZE / FWR_BYTES -- served LOF and LOC
; alone, and they read the FCB through disk.rom now (H_CHIN ops 6 / 8). The block
; cannot move while its channel is open -- CLEAR and MAXFILES close every file
; first (D-CLEARCLOSE) -- so dout_open's one store at OPEN is the cache. Its
; D-FLOORREC lesson stays true of whatever replaces it: a DEVICE channel's switch
; must write nothing, since on a diskless machine FSECTOR_BUF is program RAM.)

; t_fch_save (D-FCBSHAPE S0, GONE since D-FLDDESC -- see its note below): the
; engine globals -> channel context block at HL. Was main's fch_save_active
; body, moved whole.
; 🗑️ D-MODE2DEAD (2026-10-07): IT USED TO FLUSH FIRST (fat_detach_channel) and
; report the flush's Cy/A/HL as its own result. Only a mode-2 channel -- OUTPUT
; through main's engine -- could be dirty, and none has been stored since S10.B
; increment 2, so for every stored mode the flush returned Cy=0 untouched: this
; op reported success either way. It now says so directly. chan_gate discards
; the result on purpose (basic/files.asm) and its claimed path reads the VERB's
; status, set after the crossing, not this one.
; t_fch_hdr -- D-FCBHDR (2026-10-08): the FCB header a program PEEKs through
; VARPTR(#n), as the references write it at OPEN (probes/basic/
; basic_probe_fcbhdr.py): +0 the MODE (1 INPUT, 2 OUTPUT -- APPEND too -- 4
; RANDOM), +4 the DEVICE ($FD CRT:, $FE LPT:, $FF CAS:, else the drive as typed:
; 0 none, 1 A:, 2 B:), +6 the position, 0 -- except a disk OUTPUT / APPEND
; channel, whose +6 disk.rom keeps (an APPEND opens at the size). Bytes +1..+3,
; +5, +7, +8 are a pointer into the reference's disk work area or leftover RAM
; there: not written.
;   in:  HL = the block (main's fch_ctx_addr), OO_DEVTYPE = the FCH_MODES value
;        (1 INPUT, 3 DOUT, 4 RANDOM, 5 LPT, 6 CRT, 7 CAS OUT, 8 CAS IN, 9 GRP).
fhd_tab:        db      1,0, 2,0, 2,0, 4,0, 2,$FE, 2,$FD, 2,$FF, 1,$FF
                db      2,$FC               ; 9 GRP: (D-OPENGRP: VARPTR(#1)+0 = 2,
                                            ; +4 = 252 on the VG-8020, round 5)

; (t_fch_save -- GONE with D-FLDDESC, 2026-10-17; op 21 is a retired op.
; D-MODE2DEAD had dropped its flush, S10.C its engine-state LDIR, and the last
; thing it did -- RANDOM's record, FSECTOR_BUF -> block+9 -- has no source now:
; the record lives in the block.)

; (fch_engrow (D-FCBSHAPE S2) -- GONE with t_fch_load, its only caller: S10.E,
; 2026-10-19. disk.rom's dout_row is the one copy of that arithmetic.)

; (t_fat_rand_open / get / put -- the wrappers over sub/randio.asm's record
; engine -- are GONE with it: S10.D, 2026-10-15, disk.rom runs RANDOM files.)

; (The shared primitive bodies -- `include "basic/fat-prim-body.inc"`, the
; tenant's sub-local dskio_calslt / read_sector and the FAT12 layers over it,
; included here WHOLESALE since Phase 1 -- are GONE from the sub-ROM, 2026-10-19
; (D-ROMSIZE step 1). The last caller was BLOAD's disk path (sub/bload.asm over
; basic/fatio-body.inc: fat_mount / fat_find / name_cmp / fat_open /
; fat_next_cluster / fat_read_file_sector / fat_dir_start / read_sector), and the
; disk load is disk.rom's hk_dpbload now. The write half went earlier the same
; day with BSAVE's disk engine, and fatfits-body.inc / fat-delete-body.inc with
; it. disk.rom is the body's one home; sub/format.asm keeps its own write_sector,
; as it always did.)
