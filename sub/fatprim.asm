; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — fatprim.asm  (FAT12 primitive/sector-layer tenant)
; ===========================================================================
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
; Read DISKOP_OP (RAM) and dispatch via fp_table, indexed by BC*3 (a `jp`
; table entry is 3 bytes) so HL/DE -- the primitive's REAL inputs, passed
; through CALSLT untouched by subrom_call -- survive intact into whichever
; primitive body gets picked.
fatprim_tenant:
                xor     a
                ld      (DISKOP_ERR),a      ; D-DISKERR: no DSKIO failure pending yet
                ld      a,(DISKOP_OP)
                ld      c,a
                ld      b,0                 ; BC = op (0..24)
                ld      ix,fp_table
                add     ix,bc
                add     ix,bc
                add     ix,bc               ; IX = fp_table + 3*op
                jp      (ix)

fp_table:
                jp      t_read_sector           ; 0  DISKOP_SEL_READ_SECTOR
                jp      t_write_sector          ; 1  DISKOP_SEL_WRITE_SECTOR
                jp      t_fat_mount             ; 2  DISKOP_SEL_FAT_MOUNT
                jp      t_fat_find              ; 3  DISKOP_SEL_FAT_FIND
                jp      t_name_cmp              ; 4  DISKOP_SEL_NAME_CMP
                jp      t_fat_open              ; 5  DISKOP_SEL_FAT_OPEN
                jp      t_fat_read_fat_sector   ; 6  DISKOP_SEL_FAT_READ_FAT_SECTOR
                jp      t_fat_read_file_sector  ; 7  DISKOP_SEL_FAT_READ_FILE_SECTOR
                jp      t_fat_alloc_cluster     ; 8  DISKOP_SEL_FAT_ALLOC_CLUSTER
                jp      t_fat_write_fat_entry   ; 9  DISKOP_SEL_FAT_WRITE_FAT_ENTRY
                jp      t_fat_count_free        ; 10 DISKOP_SEL_FAT_COUNT_FREE
                jp      fp_stash_ok             ; 11 retired (D-ASAVEDOUT: no sender;
                                                ; main's flush stub went with SAVE ,A)
                jp      t_fat_dir_create        ; 12 DISKOP_SEL_FAT_DIR_CREATE
                jp      t_fat_dir_update        ; 13 DISKOP_SEL_FAT_DIR_UPDATE
                jp      t_fat_delete            ; 14 DISKOP_SEL_FAT_DELETE
; --- rows 15-17: RETIRED by S10.D (2026-10-15). They were the fat_rand_*
; random-access record engine (docs/spec-eviction-g4-space.md §3, carve #1:
; DISKOP_SEL_RAND_OPEN / GET / PUT, bodies in sub/randio.asm). RANDOM OPEN / GET
; / PUT / CLOSE run in disk.rom now (hk_frnd / hk_dget / hk_chclose), so nothing
; sends these; each keeps its 3 B so 18.. stay put (the table is append-only).
                jp      fp_stash_ok             ; 15 retired (was DISKOP_SEL_RAND_OPEN)
                jp      fp_stash_ok             ; 16 retired (was DISKOP_SEL_RAND_GET)
                jp      fp_stash_ok             ; 17 retired (was DISKOP_SEL_RAND_PUT)
; --- row 18: fat_io_append's resume-point tail (docs/spec-eviction-g7-space.md,
; carve 2). Body in sub/fiawalk.asm, included after this file in sub/sub.asm.
                jp      t_fia_walked            ; 18 DISKOP_SEL_FIA_WALKED
; --- row 19: the file-channel re-stage (D-FCH S-FCH-1, docs/spec-basic-
; filechan-alloc.md §3.1) -- RETIRED by S10.C (2026-10-15). Its body,
; fat_restage_channel, re-read an INPUT channel's staged sector (no other mode
; ever staged one), and an INPUT channel is disk.rom's FCB now, its read-ahead the
; block's record. No sender had used the row itself since D-FCBSHAPE S0 (the
; shim went; t_fch_load called the body directly).
                jp      fp_stash_ok             ; 19 retired (was DISKOP_SEL_FCH_RESTAGE)
                jp      fp_stash_ok             ; 20 retired (D-MODE2DEAD: no sender;
                                                ; the detach flushed mode 2 only)
; --- rows 21-22: the channel context save/load (D-FCBSHAPE S0), main's
; fch_save_active/fch_load_ctx bodies moved here so the block layout lived in
; one ROM. RETIRED, both: row 21 by D-FLDDESC (2026-10-17) -- its last copy was
; RANDOM's record, FSECTOR_BUF -> block+9, and that record lives at block+9 --
; and row 22 by S10.E (2026-10-19): t_fch_load's last job was MIRRORING the live
; channel's LOF / LOC (the FCB's +16 size and +33 random record) into main's
; FAT_FILESIZE / FWR_BYTES on every channel switch, and LOF / LOC now ask
; disk.rom for the FCB's own value (H_CHIN ops 6 / 8, disk/fat.asm din_lofloc).
; main's fch_save_active / fch_load_ctx, their only senders, went with it. Each
; row keeps its 3 B so 23.. stay put (the table is append-only).
                jp      fp_stash_ok             ; 21 retired (was DISKOP_SEL_FCH_SAVE)
                jp      fp_stash_ok             ; 22 retired (was DISKOP_SEL_FCH_LOAD)
; SBH-3 (2026-10-03) made the sequential WRITE cursor's open/close rows 23/24;
; S10 increment 3 (D-ASAVEDOUT, 2026-10-08) retired both -- main's stubs over
; them were SAVE ,A's, and disk.rom writes that file now.
                jp      t_fch_hdr               ; 23 DISKOP_SEL_FCH_HDR (D-FCBHDR; was
                                                ; FAT_IO_CREATE, retired by D-ASAVEDOUT)
                jp      fp_stash_ok             ; 24 retired (D-ASAVEDOUT)

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
fp_stash_err:
                ld      (DISKOP_HL),hl
                ld      (DISKOP_A),a
                ld      a,1
                ld      (DISKOP_STATUS),a
                ret

; --- per-primitive wrappers: call the shared body, marshal the result ------
t_read_sector:
                call    read_sector
                jr      c,fp_stash_err
                jr      fp_stash_ok
; t_write_sector — the shared body names its copy `fatprim_write_sector`, not
; `write_sector` (sub/format.asm already owns that name for its OWN private
; write path in this same sub.rom assembly; see fat-prim-body.inc's header).
t_write_sector:
                call    fatprim_write_sector
                jr      c,fp_stash_err
                jr      fp_stash_ok
t_fat_mount:
                call    fat_mount
                jr      c,fp_stash_err
                jr      fp_stash_ok
t_fat_find:
                call    fat_find
                jr      c,fp_stash_err
                jr      fp_stash_ok
; t_name_cmp — Z, not Cy: STATUS doubles as the Z surrogate (0 = match/Z,
; nonzero = no-match/NZ), same polarity as the Cy convention elsewhere.
t_name_cmp:
                call    name_cmp
                jr      z,fp_stash_ok
                jr      fp_stash_err
t_fat_open:
                call    fat_open
                jr      c,fp_stash_err
                jr      fp_stash_ok
t_fat_read_fat_sector:
                call    fat_read_fat_sector
                jr      c,fp_stash_err
                jr      fp_stash_ok
t_fat_read_file_sector:
                call    fat_read_file_sector
                jr      c,fp_stash_err
                jr      fp_stash_ok
; t_fat_alloc_cluster — HL is fat_alloc_cluster's real output (the allocated
; cluster number, read by field.asm:576/599 via the resident shim); covered
; by the uniform fp_stash_ok/err reload, no bespoke tail needed.
t_fat_alloc_cluster:
                call    fat_alloc_cluster
                jr      c,fp_stash_err
                jr      fp_stash_ok
t_fat_write_fat_entry:
                call    fat_write_fat_entry
                jr      c,fp_stash_err
                jr      fp_stash_ok
; t_fat_count_free — DE, not Cy/HL: mirror DE into FAT_WRTMP2 (fat_count_
; free's OWN scratch, already RAM-visible from the resident side) on EVERY
; exit path, so the resident shim can just `ld de,(FAT_WRTMP2)`. Harmless on
; the normal fcf_done path (DE already == FAT_WRTMP2 there); corrective on
; the fcf_zero/mount-failure path, which sets DE=0 directly without touching
; FAT_WRTMP2 (see basic/sysvars.inc's DISKOP block comment). No Cy to
; marshal either: the original never guaranteed one (its only caller,
; expr.asm ev_ff_dskf, reads DE only).
t_fat_count_free:
                call    fat_count_free
                ld      (FAT_WRTMP2),de
                ret
t_fat_dir_create:
                call    fat_dir_create
                jr      c,fp_stash_err
                jr      fp_stash_ok
t_fat_dir_update:
                call    fat_dir_update
                jr      c,fp_stash_err
                jr      fp_stash_ok
t_fat_delete:
                call    fat_delete
                jr      c,fp_stash_err
                jr      fp_stash_ok

; (t_fch_restage, row 19's wrapper over fat_restage_channel, is gone with it:
; S10.C, 2026-10-15 -- see the row.)

; (t_fch_load (D-FCBSHAPE S0) -- GONE with S10.E, 2026-10-19; row 22 is
; `jp fp_stash_ok`. It was main's fch_load_ctx body, moved here whole so the
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
t_fch_hdr:
                push    hl
                ld      a,(OO_DEVTYPE)
                dec     a
                add     a,a
                ld      e,a
                ld      d,0
                ld      hl,fhd_tab
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
                jp      z,fp_stash_ok       ; disk.rom's position stands
                ld      (hl),0
                jp      fp_stash_ok
fhd_tab:        db      1,0, 2,0, 2,0, 4,0, 2,$FE, 2,$FD, 2,$FF, 1,$FF
                db      2,$FC               ; 9 GRP: (D-OPENGRP: VARPTR(#1)+0 = 2,
                                            ; +4 = 252 on the VG-8020, round 5)

; (t_fch_save -- GONE with D-FLDDESC, 2026-10-17; row 21 is `jp fp_stash_ok`.
; D-MODE2DEAD had dropped its flush, S10.C its engine-state LDIR, and the last
; thing it did -- RANDOM's record, FSECTOR_BUF -> block+9 -- has no source now:
; the record lives in the block.)

; (fch_engrow (D-FCBSHAPE S2) -- GONE with t_fch_load, its only caller: S10.E,
; 2026-10-19. disk.rom's dout_row is the one copy of that arithmetic.)

; (t_fat_rand_open / get / put -- the wrappers over sub/randio.asm's record
; engine -- are GONE with it: S10.D, 2026-10-15, disk.rom runs RANDOM files.)

; The shared primitive bodies (dskio_calslt/read_sector/write_sector through
; fat_dir_update, then fat_delete). Included here WHOLESALE -- this file's
; own copies of dskio_calslt/read_sector/write_sector (inside fat-prim-
; body.inc) ARE the tenant's sub-local CALSLT path (see header).
                include "basic/fat-prim-body.inc"
                include "basic/fatfits-body.inc"     ; fat_fits (D-SAVEFULLSTAMP)
                include "basic/fat-delete-body.inc"
