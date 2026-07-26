; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fat.asm — loader-side FAT12 read+write engine driving the STANDARD $4010 DSKIO
; sector interface of whatever disk ROM occupies the slot.
; ===========================================================================
; This is the Phase-1.5 HOST side: zerobas-BASIC's disk loader verbs reach files
; through the disk ROM's standard DSKIO ($4010) physical-sector entry and own the
; FAT12 / directory logic themselves, instead of calling zerobas-disk's PRIVATE
; bdos_entry (SYSTEM vector $F37D). Driving the standard sector interface makes the
; loader disk-ROM-INDEPENDENT: any standard MSX1 disk ROM (our own, or a foreign
; one such as the National CF-3300) services the same loader unchanged.
;
; PORTED from disk/disk.asm (this project's OWN clean-room FAT12 code — porting our
; own code carries its provenance forward, not a forbidden disassembly). The only
; substantive change vs. the disk-ROM-side original is the physical-sector
; primitive: there `read_sector`/`write_sector` tail-called the LOCAL `dskio`
; (ROM offset +$10); here they CALSLT the in-slot disk ROM's DSKIO at $4010 across
; slots (the slot id is the INIT-scan's DISKSLOT capture). Everything above the
; sector primitive — BPB parse, cluster-chain walk, 8.3 directory search, FAT12
; nibble pack/unpack, free-cluster allocation, multi-FAT sync, directory
; create/update — is byte-for-byte the same algorithm as disk.asm.
;
; CLEAN-ROOM: every constant/address/algorithm traces to an allowed source, cited
; inline (same provenance as disk/disk.asm, carried over):
;   * DSKIO register convention + $4010 offset — MSX2 Technical Handbook, disk-ROM
;     interface (§5); cross-checked by black-box openMSX observation of the real
;     National CF-3300 (disk/docs/expansion-protocol.md §3). CY = direction
;     (clear = read, set = write).
;   * CALSLT ($001C) inter-slot call + slot-id byte format — MSX2 TH / MSX Assembly
;     Page BIOS call list; CALSLT passes the caller's AF (hence the direction CY)
;     through to the target and returns the target's AF (hence the error CY) — this
;     is exactly how C-BIOS's clprim restores AF around `jp (ix)` (allowed C-BIOS
;     source, observed not transcribed). State is kept in RAM across the call
;     because CALSLT clobbers AF/BC/DE/HL/IX/IY.
;   * BPB / FAT / directory layout — Microsoft FAT filesystem specification; ECMA-107
;     geometry. Assumes 512-byte sectors (validated at mount).
;   * On-disk BSAVE ($FE) / tokenised-BASIC ($FF) markers — MSX-BASIC file formats
;     (public MSX-BASIC file-format reference), already in sysvars.inc.
; No reference BIOS / disk-ROM / MSX-BASIC / MSX-DOS disassembly was read.
; See basic/PROVENANCE.md §disk DSKIO host engine.
;
; REPACK EVICTION, PHASE 1 (docs/spec-evict-diskfile-cluster.md §11, funding
; D-F2-2 A2+VPEEK): the FAT12 PRIMITIVE/SECTOR layer below (dskio_calslt
; through fat_dir_update, PLUS fat_delete further down) moves to a sub-ROM
; PAGE-1 tenant (sub/fatprim.asm fatprim_tenant, SUBROM_IDX_FATPRIM) — a
; single selector-dispatched entry covering all 15 marshalled primitives
; (DISKOP_OP picks the routine; a subrom_call only reaches one tenant entry).
; The BYTE-GRANULAR fat_io_* cursor (fat_io_open..fat_io_close) below stays
; resident in BOTH builds: it is reached via the ARL_GETBYTE polymorphic RAM
; vector, valid only while the owning code is mapped in, so it cannot move
; yet (spec §11's empirical rationale). The shared bodies live in
; basic/fat-prim-body.inc (dskio_calslt..fat_dir_update) and
; basic/fat-delete-body.inc (fat_delete, kept separate only because it sits
; AFTER the resident cursor in this file — see that file's header); the lean
; 16 KB cart includes them inline at their original positions
; (BYTE-IDENTICAL to the pre-eviction build), the repack build emits resident
; SHIMS under the SAME names instead (this file's `IF ROM_BASE < $4000`
; branches below), keeping every existing call site (`call read_sector`,
; `call fat_find`, ...) unchanged. See basic/PROVENANCE.md §FAT12 primitive
; eviction.

    IF ROM_BASE >= $4000
                include "basic/fat-prim-body.inc"      ; lean: inline, byte-identical
; write_sector: fat-prim-body.inc names its copy `fatprim_write_sector` (the
; sub-ROM tenant assembly needs that name distinct from sub/format.asm's OWN
; private write_sector -- see fat-prim-body.inc's header). This alias makes
; every existing external call site here (field.asm/files.asm's literal
; `call write_sector`) resolve exactly as before -- EQU emits zero bytes, so
; this cannot affect lean byte-identity.
write_sector    equ     fatprim_write_sector
    ELSE
; --- repack: resident shims replacing the FAT12 primitive/sector layer -----
; docs/spec-evict-diskfile-cluster.md §11. Every routine below keeps its
; ORIGINAL name and calling convention (register-input contract unchanged);
; only the BODY is now a dispatch to the sub-ROM PAGE-1 tenant fatprim_tenant
; (sub/fatprim.asm, SUBROM_IDX_FATPRIM), selected by a DISKOP_OP byte (RAM),
; since one subrom_call only reaches ONE tenant entry, not 15. Cy cannot ride
; back through subrom_call/CALSLT (its own `or a` always clears it,
; sub/format.asm's rule) -- so every primitive's disposition + HL/A outputs
; are marshalled through the DISKOP result block (basic/sysvars.inc),
; reloaded here uniformly (safe: DSKIO/CALSLT already clobbers HL at every
; existing call site, so no caller relies on HL surviving a primitive call
; unmarshalled). The three primitives whose REAL ABI needs something other
; than the uniform Cy+HL+A convention get bespoke treatment:
; fat_alloc_cluster (HL is a genuine, caller-read output -- covered by the
; uniform reload), name_cmp (Z, not Cy -- its own shim below), and
; fat_count_free (DE, not Cy -- rides back over FAT_WRTMP2 instead of a new
; RAM cell, see that cell's sysvars.inc comment).

; read_sector — see basic/fat-prim-body.inc for the full contract.
read_sector:
                ld      a,DISKOP_SEL_READ_SECTOR
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c                   ; sub-ROM absent -> Cy=1 (same
                                            ; disposition class as a real I/O
                                            ; error, do_format-style contract)
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,rdsec_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
rdsec_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; write_sector — see basic/fat-prim-body.inc for the full contract.
write_sector:
                ld      a,DISKOP_SEL_WRITE_SECTOR
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,wrsec_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
wrsec_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; fat_mount — see basic/fat-prim-body.inc for the full contract.
fat_mount:
                ld      a,DISKOP_SEL_FAT_MOUNT
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,ftmnt_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
ftmnt_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; fat_find — see basic/fat-prim-body.inc for the full contract.
fat_find:
                ld      a,DISKOP_SEL_FAT_FIND
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,ftfnd_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
ftfnd_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; name_cmp — Z-based (not Cy), so it gets its own tail: see basic/
; fat-prim-body.inc for the full contract ("Z set if equal"). DISKOP_STATUS
; is reused as the Z surrogate (0 = match/Z, nonzero = no-match/NZ) — same
; polarity as the Cy convention, just tested with `or a` for Z instead of
; branching on Cy.
name_cmp:
                ld      a,DISKOP_SEL_NAME_CMP
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                jr      c,ncm_absent        ; absent -> defensive "no match" (NZ)
                ld      a,(DISKOP_STATUS)
                or      a                   ; Z set iff STATUS==0 (tenant's match)
                ret
ncm_absent:
                or      1                   ; force NZ regardless of A's value
                ret

; fat_open — see basic/fat-prim-body.inc for the full contract.
fat_open:
                ld      a,DISKOP_SEL_FAT_OPEN
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,ftopn_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
ftopn_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; fat_read_fat_sector — see basic/fat-prim-body.inc for the full contract.
fat_read_fat_sector:
                ld      a,DISKOP_SEL_FAT_READ_FAT_SECTOR
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,frfat_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
frfat_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; fat_read_file_sector — see basic/fat-prim-body.inc for the full contract.
fat_read_file_sector:
                ld      a,DISKOP_SEL_FAT_READ_FILE_SECTOR
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,frfil_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
frfil_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; fat_alloc_cluster — see basic/fat-prim-body.inc for the full contract. HL is
; a REAL caller-read output (field.asm:576/599) -- covered by the uniform
; DISKOP_HL reload below, no bespoke handling needed.
fat_alloc_cluster:
                ld      a,DISKOP_SEL_FAT_ALLOC_CLUSTER
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,falcl_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
falcl_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; fat_write_fat_entry — see basic/fat-prim-body.inc for the full contract.
fat_write_fat_entry:
                ld      a,DISKOP_SEL_FAT_WRITE_FAT_ENTRY
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,fwfe_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
fwfe_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; fat_count_free — DE-based (not Cy/HL), so it gets its own tail: see basic/
; fat-prim-body.inc for the full contract ("DE = free cluster count"). No
; new RAM cell: the tenant wrapper (sub/fatprim.asm t_fat_count_free) mirrors
; DE into FAT_WRTMP2 (fat_count_free's OWN scratch, already RAM-visible both
; sides) before returning, on EVERY exit path (see basic/sysvars.inc's
; DISKOP block comment for why that is safe). The original never guaranteed
; a Cy contract here either (its only caller, expr.asm ev_ff_dskf, reads DE
; only) so this shim does not fabricate one.
fat_count_free:
                ld      a,DISKOP_SEL_FAT_COUNT_FREE
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                jr      c,fcfs_absent
                ld      de,(FAT_WRTMP2)
                ret
fcfs_absent:
                ld      de,0
                ret

; fat_flush_data_sector — see basic/fat-prim-body.inc for the full contract.
fat_flush_data_sector:
                ld      a,DISKOP_SEL_FAT_FLUSH_DATA_SECTOR
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,ffds_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
ffds_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; fat_dir_create — see basic/fat-prim-body.inc for the full contract.
fat_dir_create:
                ld      a,DISKOP_SEL_FAT_DIR_CREATE
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,fdcr_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
fdcr_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret

; fat_dir_update — see basic/fat-prim-body.inc for the full contract. Two
; call sites tail-call this via `jp` (field.asm frp_overlay, fat_io_close
; below) -- transparent to a shim entered by `call` OR `jp`, since it simply
; ends in `ret` either way.
fat_dir_update:
                ld      a,DISKOP_SEL_FAT_DIR_UPDATE
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,fdup_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
fdup_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret
    ENDIF

; ===========================================================================
; Byte-stream I/O layer — the loader-facing API the disk verbs call. This is the
; HOST analogue of disk.asm's bdos layer, but byte-granular instead of the FCB's
; 128-byte record framing: the verbs (BLOAD / LOAD / RUN / SAVE / BSAVE) stream
; bytes, and this layer maps them onto whole 512-byte FAT sectors. No FCB and no
; 128-byte zero-padding — exact byte counts are tracked, so a file's on-disk size
; is its true length (SAVE/BSAVE produce byte-exact images that round-trip).
; ===========================================================================

                include "basic/fatio-body.inc"


                include "basic/fatiocreate-body.inc"   ; fat_io_create (shared with sub/save.asm)

; fat_io_append — open the file named in DISK_FCB_NAME for sequential WRITE,
; positioned at end-of-file (text APPEND). New bytes extend the file instead of
; truncating it. A missing file is created (append == create). If the existing
; file ends in a Ctrl-Z ($1A) soft-EOF, the write cursor is placed ON that marker
; so it is overwritten and re-stamped at the next CLOSE — matching the real
; National CF-3300 (disk_probe_append.py: "first\r\n\x1a" + APPEND "second" ->
; "first\r\nsecond\r\n\x1a", the original Ctrl-Z gone).
;   out: Cy = 0 ready (write stream primed at EOF); Cy = 1 = mount / I-O error.
; Method: find the file (fat_find records FAT_FIRSTCLUS/FILESIZE + FWR_DIRSEC/OFF),
; walk the cluster chain reading every data sector (the last stays in FSECTOR_BUF),
; then prime the write iterator to RESUME at the res. Reuses the read-side
; fat_open/fat_read_file_sector to walk; no new chain logic. Size handled as 16-bit
; (loader text files; a >64 KB append is out of scope — documented limit).
fat_io_append:
                call    fat_mount
                ret     c
                ld      hl,DISK_FCB_NAME
                call    fat_find
                jp      c,fat_io_create     ; not found -> append == create from scratch
                ; reuse the existing dir entry (FWR_DIRSEC/OFF set by fat_find) + chain.
                ld      hl,(FAT_FIRSTCLUS)
                ld      (FWR_FIRST),hl
                ld      hl,(FAT_FILESIZE)   ; size (low 16 bits)
                ld      a,h
                or      l
                jp      z,fia_empty         ; empty file -> write from offset 0
                ; nsec = ceil(size / 512) = (size + 511) >> 9 (high byte >> 1).
                ld      de,511
                add     hl,de
                ld      a,h
                srl     a
                ld      (FAT_WRTMP),a       ; loop counter = sectors to walk
                xor     a
                ld      (FAT_WRTMP+1),a
                ; walk the chain; fat_read_file_sector leaves the LAST sector in
                ; FSECTOR_BUF and FAT_CURCLUS/FAT_CLUSSEC on it (CLUSSEC = sec+1).
                call    fat_open
fia_walk:
                ld      hl,(FAT_WRTMP)
                ld      a,h
                or      l
                jr      z,fia_walked
                call    fat_read_file_sector
                ld      hl,(FAT_WRTMP)
                dec     hl
                ld      (FAT_WRTMP),hl
                jr      fia_walk
    IF ROM_BASE >= $4000
                include "basic/fiawalked-body.inc"     ; lean: inline, byte-identical
    ELSE
; fia_walked -- resident shim (docs/spec-eviction-g7-space.md, carve 2). The body
; is a page-1 fatprim-tenant row; every path in it returns Cy = 0, so the shim
; only has to make the call and clear carry.
fia_walked:
                ld      a,DISKOP_SEL_FIA_WALKED
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call         ; CF=1 iff the sub-ROM is absent
                ret     c
                or      a                   ; success: Cy = 0, like the body
                ret
    ENDIF
fia_empty:
                ; existing but EMPTY file: write from offset 0, reusing the dir entry
                ; (FWR_DIRSEC/OFF from fat_find; FWR_FIRST = FAT_FIRSTCLUS = 0). Same
                ; primed state as fat_io_create but without making a new dir slot.
                xor     a
                ld      (FWR_SECIDX),a
                ld      hl,0
                ld      (FWR_CLUS),hl
                ld      (FWR_BUFLEN),hl
                ld      (FWR_BYTES),hl
                ld      (FWR_BYTES+2),hl
                or      a                   ; Cy = 0 success
                ret


                include "basic/fatiow-body.inc"        ; fat_io_putbyte/fwr_bytes_inc/fat_io_close

    IF ROM_BASE >= $4000
                include "basic/fat-delete-body.inc"    ; lean: inline, byte-identical
    ELSE
; fat_delete — resident shim (docs/spec-evict-diskfile-cluster.md §11). See
; basic/fat-delete-body.inc for the full contract; same uniform Cy+HL+A
; marshalling convention as the other primitive shims above.
fat_delete:
                ld      a,DISKOP_SEL_FAT_DELETE
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c
                ld      a,(DISKOP_STATUS)
                or      a
                jr      nz,fdel_err
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                ret
fdel_err:
                ld      hl,(DISKOP_HL)
                ld      a,(DISKOP_A)
                scf
                ret
    ENDIF
