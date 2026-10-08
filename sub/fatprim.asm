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
; --- rows 15-17: the fat_rand_* random-access record engine (docs/spec-
; eviction-g4-space.md §3, carve #1). Same fp_table/DISKOP_OP selector, no new
; tenant index -- the bodies live in sub/randio.asm, included right after
; this file (+ dirverb.asm) in sub/sub.asm.
                jp      t_fat_rand_open         ; 15 DISKOP_SEL_RAND_OPEN
                jp      t_fat_rand_get          ; 16 DISKOP_SEL_RAND_GET
                jp      t_fat_rand_put          ; 17 DISKOP_SEL_RAND_PUT
; --- row 18: fat_io_append's resume-point tail (docs/spec-eviction-g7-space.md,
; carve 2). Body in sub/fiawalk.asm, included alongside randio.asm in sub/sub.asm.
                jp      t_fia_walked            ; 18 DISKOP_SEL_FIA_WALKED
; --- row 19: the file-channel re-stage (D-FCH S-FCH-1, docs/spec-basic-
; filechan-alloc.md §3.1). Body is fat_restage_channel in basic/fat-prim-body.inc,
; already included below. Sited here rather than resident because the
; cluster->absolute-sector arithmetic it needs lives in this file twice over and
; main page 1 has 6 B free.
                jp      t_fch_restage           ; 19 DISKOP_SEL_FCH_RESTAGE
                jp      fp_stash_ok             ; 20 retired (D-MODE2DEAD: no sender;
                                                ; the detach flushed mode 2 only)
; --- rows 21-22: the channel context save/load (D-FCBSHAPE S0), main's
; fch_save_active/fch_load_ctx bodies moved here so the block layout lives in
; one ROM. HL = the context block on entry to both.
                jp      t_fch_save              ; 21 DISKOP_SEL_FCH_SAVE
                jp      t_fch_load              ; 22 DISKOP_SEL_FCH_LOAD
; SBH-3 (2026-10-03) made the sequential WRITE cursor's open/close rows 23/24;
; S10 increment 3 (D-ASAVEDOUT, 2026-10-08) retired both -- main's stubs over
; them were SAVE ,A's, and disk.rom writes that file now.
                jp      fp_stash_ok             ; 23 retired (D-ASAVEDOUT)
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
                jp      c,fp_stash_err
                jp      fp_stash_ok
; t_write_sector — the shared body names its copy `fatprim_write_sector`, not
; `write_sector` (sub/format.asm already owns that name for its OWN private
; write path in this same sub.rom assembly; see fat-prim-body.inc's header).
t_write_sector:
                call    fatprim_write_sector
                jp      c,fp_stash_err
                jp      fp_stash_ok
t_fat_mount:
                call    fat_mount
                jp      c,fp_stash_err
                jp      fp_stash_ok
t_fat_find:
                call    fat_find
                jp      c,fp_stash_err
                jp      fp_stash_ok
; t_name_cmp — Z, not Cy: STATUS doubles as the Z surrogate (0 = match/Z,
; nonzero = no-match/NZ), same polarity as the Cy convention elsewhere.
t_name_cmp:
                call    name_cmp
                jp      z,fp_stash_ok
                jp      fp_stash_err
t_fat_open:
                call    fat_open
                jp      c,fp_stash_err
                jp      fp_stash_ok
t_fat_read_fat_sector:
                call    fat_read_fat_sector
                jp      c,fp_stash_err
                jp      fp_stash_ok
t_fat_read_file_sector:
                call    fat_read_file_sector
                jp      c,fp_stash_err
                jp      fp_stash_ok
; t_fat_alloc_cluster — HL is fat_alloc_cluster's real output (the allocated
; cluster number, read by field.asm:576/599 via the resident shim); covered
; by the uniform fp_stash_ok/err reload, no bespoke tail needed.
t_fat_alloc_cluster:
                call    fat_alloc_cluster
                jp      c,fp_stash_err
                jp      fp_stash_ok
t_fat_write_fat_entry:
                call    fat_write_fat_entry
                jp      c,fp_stash_err
                jp      fp_stash_ok
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
                jp      c,fp_stash_err
                jp      fp_stash_ok
t_fat_dir_update:
                call    fat_dir_update
                jp      c,fp_stash_err
                jp      fp_stash_ok
t_fat_delete:
                call    fat_delete
                jp      c,fp_stash_err
                jp      fp_stash_ok

; t_fch_restage (D-FCH S-FCH-1): re-read the live channel's staged sector back
; into the shared FSECTOR_BUF. Takes no register inputs -- fat_restage_channel
; reads FCH_ACTIVE/FCH_MODES and the engine state straight out of RAM -- so the
; resident shim marshals nothing.
t_fch_restage:
                call    fat_restage_channel
                jp      c,fp_stash_err
                jp      fp_stash_ok

; t_fch_load (D-FCBSHAPE S0): channel context block -> the engine globals, then
; the re-stage. HL = the block (main's fch_ctx_addr, passed through CALSLT
; untouched); FCH_ACTIVE is already the new channel, which the re-stage reads.
; This was main's fch_load_ctx body, moved whole: the block's LAYOUT is now
; known in one ROM only, the one D-FCBSHAPE's later slices change.
t_fch_load:
                push    hl                  ; the block
                call    fch_engrow          ; HL = the channel's engine row; CF = none
                jr      c,tfl_rec           ; a device channel keeps no engine state
                cp      DOUT_MODE-1
                jr      z,tfl_dout          ; S10.B: the row is disk.rom's FCB
                ld      de,FCH_STATE0
                ld      bc,FCH_STATESZ
                ldir                        ; engine row -> globals
tfl_rec:
                pop     hl
                ld      de,FCH_HDRSZ
                add     hl,de               ; the record, after the FCB header
                ld      de,FSECTOR_BUF      ; D-FIELDFIX: and this channel's record
                ld      bc,FCH_RECMAX
                ldir
                jr      t_fch_restage
; S10.B: a DOUT_MODE row is an MSX-DOS FCB (+16..19 its size, +37..38 the cached
; block address). The block cannot move while the channel is open -- CLEAR and
; MAXFILES close every file first (D-CLEARCLOSE) -- but every load re-caches it
; anyway, the cost of one store. LOF reads FAT_FILESIZE: the FCB's size, i.e.
; the bytes committed in whole records, as on the CF-3300 (spec-diskcode-
; eviction.md, S10.B DESIGN INPUT 2). No record copy and no re-stage: the record
; lives in the block, and FSECTOR_BUF is not this channel's.
tfl_dout:
                ld      bc,DOUT_BLK
                add     hl,bc
                pop     de                  ; DE = the block
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ld      bc,16-DOUT_BLK-1
                add     hl,bc               ; HL = FCB +16, the size
                ld      de,FAT_FILESIZE
                ld      bc,4
                ldir                        ; LOF
                ld      bc,33-20
                add     hl,bc               ; HL = FCB +33, the random record
                ld      de,FWR_BYTES
                ld      bc,3
                ldir                        ; LOC (S10.B increment 2: on an APPEND
                xor     a                   ; channel it is not LOF)
                ld      (de),a
                jp      fp_stash_ok

; t_fch_save (D-FCBSHAPE S0): the engine globals -> channel context block at
; HL. Was main's fch_save_active body, moved whole.
; 🗑️ D-MODE2DEAD (2026-10-07): IT USED TO FLUSH FIRST (fat_detach_channel) and
; report the flush's Cy/A/HL as its own result. Only a mode-2 channel -- OUTPUT
; through main's engine -- could be dirty, and none has been stored since S10.B
; increment 2, so for every stored mode the flush returned Cy=0 untouched: this
; op reported success either way. It now says so directly. chan_gate discards
; the result on purpose (basic/files.asm) and its claimed path reads the VERB's
; status, set after the crossing, not this one.
t_fch_save:
                ; D-MODE2DEAD (2026-10-07): no flush first any more -- only a mode-2
                ; channel could be dirty, and none is stored. Nothing here can fail;
                ; fch_save_active's three callers read no result.
                push    hl                  ; the block
                call    fch_engrow          ; HL = the engine row; CF = no disk channel
                jr      c,tfs_rec
                cp      DOUT_MODE-1
                jr      z,tfs_dout          ; S10.B: nothing of main's to keep
                ex      de,hl               ; DE = the row
                ld      hl,FCH_STATE0       ; the 50-byte engine-state span
                ld      bc,FCH_STATESZ
                ldir
tfs_rec:
                pop     hl                  ; the block
                ld      de,FCH_HDRSZ
                add     hl,de
                ex      de,hl               ; DE = the record, after the FCB header
                ld      hl,FSECTOR_BUF      ; D-FIELDFIX: the record travels too
                ld      bc,FCH_RECMAX
                ldir
                jr      tfs_end
tfs_dout:
                ; S10.B: a DOUT_MODE channel's state is all disk.rom's (the FCB in
                ; the row, the record in the block). Copying main's globals over
                ; the row, or FSECTOR_BUF over the record, would destroy both.
                pop     hl                  ; the block
tfs_end:
                jp      fp_stash_ok

; fch_engrow (D-FCBSHAPE S2): -> HL = DSK_ENGTAB + ch*FCH_STATESZ for the channel
; in FCH_ACTIVE, CF clear -- or CF set when that channel is not a DISK file (mode
; 0 or >= LPT_MODE): a device or cassette channel keeps no engine state, and on a
; diskless machine the table is not reserved at all. Clobbers A,B,C,D,E.
fch_engrow:
                ld      a,(FCH_ACTIVE)
                ld      c,a
                ld      b,0
                ld      hl,FCH_MODES
                add     hl,bc
                ld      a,(hl)
                dec     a                   ; disk modes 1..LPT_MODE-1 -> 0..LPT_MODE-2
                cp      LPT_MODE-1
                ccf
                ret     c                   ; closed, device or cassette
                ld      hl,DSK_ENGTAB
                ld      de,FCH_STATESZ
                ld      b,c
feng_lp:
                add     hl,de               ; row ch (row 0 unused); no carry below $E000
                djnz    feng_lp
                ret


; t_fat_rand_open/get/put (docs/spec-eviction-g4-space.md §3, carve #1): call
; the sub-local bodies (sub/randio.asm, included after this file + dirverb.asm
; so `call read_sector`/`fat_mount`/... inside them resolve to the fatprim
; primitive bodies already resident in this page -- the same mechanism
; t_read_sector etc. above use). Uniform Cy-only convention; fp_stash_ok/err
; still persist HL/A for consistency with the other primitives, though no
; caller currently reads them back for any of the three (field.asm/files.asm
; only test Cy).
t_fat_rand_open:
                call    fat_rand_open
                jp      c,fp_stash_err
                jp      fp_stash_ok
t_fat_rand_get:
                call    fat_rand_get
                jp      c,fp_stash_err
                jp      fp_stash_ok
t_fat_rand_put:
                call    fat_rand_put
                jp      c,fp_stash_err
                jp      fp_stash_ok

; The shared primitive bodies (dskio_calslt/read_sector/write_sector through
; fat_dir_update, then fat_delete). Included here WHOLESALE -- this file's
; own copies of dskio_calslt/read_sector/write_sector (inside fat-prim-
; body.inc) ARE the tenant's sub-local CALSLT path (see header).
                include "basic/fat-prim-body.inc"
                include "basic/fatfits-body.inc"     ; fat_fits (D-SAVEFULLSTAMP)
                include "basic/fat-delete-body.inc"
