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
; (ROM offset +$10); in the port they CALSLT the in-slot disk ROM's DSKIO at
; $4010 across slots (the slot id is the INIT-scan's DISKSLOT capture).
; ⚠️ NEITHER PRIMITIVE IS IN THIS FILE ANY MORE — the eviction moved the whole
; primitive/sector layer to the page-1 tenant, so the CALSLT bodies now live in
; basic/fat-prim-body.inc (read_sector/write_sector) and sub/format.asm (its own
; private write path); D-SEEDHOLE2 removed the last two callerless shims that
; still carried those names here. The port's provenance below is unchanged --
; only the address of the code it describes is. Everything above the
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
; AFTER the resident cursor in this file — see that file's header).
; (BYTE-IDENTICAL to the pre-eviction build), the repack build emits resident
; SHIMS under the SAME names instead (this file's `IF the repack build`
; branches below), keeping every existing call site (`call fat_mount`,
; `call fat_find`, ...) unchanged. ⚠️ "Every existing call site" was the design
; intent and is NOT what the tree grew into: later evictions moved whole CALLERS
; across too, and five shims outlived their last main call site -- see the carve
; note above the shims. See basic/PROVENANCE.md §FAT12 primitive
; eviction.

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

; --- the UNIFORM shims (nine contiguous + fat_delete) --------------------
; Every one of these was, until 2026-07-27, an independent 34-byte copy of the
; SAME body: load a selector, bounce to the tenant, marshal Cy+HL+A back. Only
; the DISKOP_SEL_* immediate differed. Thirteen copies (the twelve there were
; then, plus fat_delete further down) cost 442 B of main page 1 to say one
; thing thirteen times, on a build with 8 B free.
;
; Collapsed to `ld a,<selector>` + a jump into ONE shared body (fatprim_bounce),
; which is what a shim layer should have looked like from the start. The
; register/flag contract is UNCHANGED and this is a pure dedup — see
; fatprim_bounce for the one substantive difference (a branchless tail that is
; flag-equivalent, not merely similar). Cost per shim: 4 B, was 34 B.
;
; ORDER MATTERS ONLY FOR REACH: the contiguous stubs sit directly above
; fatprim_bounce so every `jr` lands within range. fat_delete sits after the
; resident fat_io_* cursor (~324 B away) and therefore uses `jp`. Deleting a
; stub only SHORTENS that distance, so reach survives a carve a fortiori.
;
; ⚠️ THE COUNT IS NOT STABLE, AND EVERY MOVE HAS BEEN IN BOTH DIRECTIONS: D-FCH
; added fch_restage/fch_flush_active (14 contiguous), and D-SEEDHOLE2
; (2026-08-22) removed five that no main caller had reached for weeks —
; read_sector, write_sector, fat_read_fat_sector, fat_alloc_cluster,
; fat_write_fat_entry, 20 B of page 1. A shim here is worth its 4 B only while
; a MAIN caller exists; the sub-ROM tenant reaches the primitive directly, not
; through this layer.
;
; 🔴 HOW THEY BECAME ORPHANS, because the shape will recur on the next eviction:
; an eviction moves a CALLER into the sub-ROM but leaves its main-side shim
; standing, and the evicted body's own `call <name>` then reads — to a seed
; scrape keyed on NAMES — as a live external reference to the main label of that
; name, when it in fact resolves sub-locally. `d3885b3` (fat_rand_* -> sub-ROM)
; orphaned four of the five and `0cbf495` (the FILES walk -> sub-ROM) the fifth;
; both were invisible to `make deadcode` until the seed set was rebuilt on
; sub/basic-resident-abi.inc. docs/spec-deadcode-gate.md §11.


; fat_mount — see basic/fat-prim-body.inc for the full contract.
fat_mount:
                ld      a,DISKOP_SEL_FAT_MOUNT
                jr      fatprim_bounce

; fat_find — see basic/fat-prim-body.inc for the full contract.
fat_find:
                ld      a,DISKOP_SEL_FAT_FIND
                jr      fatprim_bounce

; fat_open — see basic/fat-prim-body.inc for the full contract.
fat_open:
                ld      a,DISKOP_SEL_FAT_OPEN
                jr      fatprim_bounce

; fat_read_file_sector — see basic/fat-prim-body.inc for the full contract.
fat_read_file_sector:
                ld      a,DISKOP_SEL_FAT_READ_FILE_SECTOR
                jr      fatprim_bounce

; fat_flush_data_sector — see basic/fat-prim-body.inc for the full contract.
fat_flush_data_sector:
                ld      a,DISKOP_SEL_FAT_FLUSH_DATA_SECTOR
                jr      fatprim_bounce

; fch_restage — see fat_restage_channel in basic/fat-prim-body.inc (D-FCH
; S-FCH-1). No inputs to marshal; reads FCH_ACTIVE/FCH_MODES + the engine state
; from RAM. ⚠️ Goes through subrom_call, so it CLOBBERS IX — every caller in
; basic/files.asm guards it (the EOF/LOF function callers need IX to survive).
fch_restage:
                ld      a,DISKOP_SEL_FCH_RESTAGE
                jr      fatprim_bounce

; fch_flush_active — see fat_detach_channel in basic/fat-prim-body.inc. Same IX
; caveat as fch_restage.
fch_flush_active:
                ld      a,DISKOP_SEL_FCH_DETACH
                jr      fatprim_bounce

; fat_dir_create — see basic/fat-prim-body.inc for the full contract.
fat_dir_create:
                ld      a,DISKOP_SEL_FAT_DIR_CREATE
                jr      fatprim_bounce

; fat_dir_update — see basic/fat-prim-body.inc for the full contract. Two call
; sites tail-call this via `jp` (field.asm frp_overlay, fat_io_close below) --
; transparent to a shim entered by `call` OR `jp`, since it still ends in `ret`
; either way.
fat_dir_update:
                ld      a,DISKOP_SEL_FAT_DIR_UPDATE
                ; fall through

; fatprim_bounce — the ONE body the thirteen uniform shims share.
;   in:  A = DISKOP_SEL_* selector; the primitive's own register inputs are
;        already marshalled in the DISKOP block by the caller's contract.
;   out: exactly the pre-collapse contract — Cy=1 + HL/A reloaded on a tenant
;        error OR a missing sub-ROM, Cy=0 + HL/A reloaded on success.
;
; The tail is branchless where the originals branched, and that is the only
; instruction-level change. It is flag-equivalent, not approximately so:
;   * `or a` clears Cy and sets Z iff DISKOP_STATUS == 0 (success);
;   * `ld hl,(nn)` and `ld a,(nn)` DO NOT AFFECT FLAGS, so Z/Cy survive both
;     reloads — which is what lets the reload be shared by both dispositions
;     instead of duplicated into an error tail;
;   * `ret z` therefore returns success with Cy already clear (exactly what the
;     old `jr nz,<err>` fallthrough did), and the error path falls into `scf`.
; Reloading HL/A on BOTH paths is not new behaviour: every old shim's error tail
; did the same two loads before its `scf`.
fatprim_bounce:
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                call    subrom_call
                ret     c                   ; sub-ROM absent -> Cy=1
                ld      a,(DISKOP_STATUS)
                or      a                   ; Z iff success; ALSO clears Cy
                ld      hl,(DISKOP_HL)      ; flag-transparent
                ld      a,(DISKOP_A)        ; flag-transparent
                ret     z                   ; success: Cy clear from `or a`
                scf
                ret

; 🎯 THE `name_cmp` SHIM IS GONE, AND ITS DEATH IS A CARVE THIS SLICE DID NOT
; PLAN FOR (D-LFILES, docs/spec-basic-lfiles.md §6). It marshalled a Z result
; through DISKOP_STATUS for exactly ONE main-side caller — do_files's filespec
; filter — and D-LFILES moved that walk into the dirverb tenant, where `name_cmp`
; resolves to the sub-local primitive BODY instead. Main's every other user of
; the pattern match reaches it inside fat_find, which is itself a tenant call.
;
; The dead-code gate is what would have said so: leaving the shim here fails
; `make basic-reloc` with an unreachable span, which is the difference between a
; carve and a leak. DISKOP_SEL_NAME_CMP and the tenant's own dispatch arm
; (sub/fatprim.asm) are KEPT — the selector namespace is a published numbering and
; renumbering it to reclaim six sub-ROM bytes would be a drift risk against a wall
; that is not the binding one.






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
                jp     c,fcfs_absent
                ld      de,(FAT_WRTMP2)
                ret
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to vptr_none,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
fcfs_absent     equ     vptr_none




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
; truncating it. A MISSING file is REFUSED (Cy=1 -> do_open's oo_fail ->
; load_error), matching the CF-3300: it raises `File not found`, opens NO channel
; (the following LOF(1) reports ERR 59) and writes NO directory entry — measured
; two-sidedly, screen AND the machine's own disk image (D-APPMISS,
; docs/spec-basic-append-missing-refuse.md; lof-cf3300-characterization §4).
; ⚠️ This used to `jp c,fat_io_create` and the comment here called that settled
; CF-3300 parity, citing disk_probe_append.py — which creates its file with
; OUTPUT first and only ever appends to an EXISTING one. That probe's parity
; claim is real for the Ctrl-Z rule below and never reached the missing case.
; If the existing file ends in a Ctrl-Z ($1A) soft-EOF, the write cursor is placed
; ON that marker so it is overwritten and re-stamped at the next CLOSE — matching
; the real National CF-3300 (disk_probe_append.py: "first\r\n\x1a" + APPEND
; "second" -> "first\r\nsecond\r\n\x1a", the original Ctrl-Z gone).
;   out: Cy = 0 ready (write stream primed at EOF); Cy = 1 = missing / mount /
;        I-O error.
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
                ret     c                   ; not found -> REFUSE (-> oo_fail -> load error)
                ; reuse the existing dir entry (FWR_DIRSEC/OFF set by fat_find) + chain.
                ld      hl,(FAT_FIRSTCLUS)
                ld      (FWR_FIRST),hl
                ld      hl,(FAT_FILESIZE)   ; size (low 16 bits)
                ld      a,h
                or      l
                jr      z,fia_empty         ; empty file -> write from offset 0
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

; fat_delete — resident shim (docs/spec-evict-diskfile-cluster.md §11). See
; basic/fat-delete-body.inc for the full contract; same uniform Cy+HL+A
; marshalling convention as the other primitive shims above.
; `jp`, not `jr`: this is the thirteenth uniform shim but it sits AFTER the
; resident fat_io_* cursor, ~324 B below fatprim_bounce — out of `jr` reach.
fat_delete:
                ld      a,DISKOP_SEL_FAT_DELETE
                jp      fatprim_bounce
