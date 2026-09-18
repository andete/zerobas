; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fat-prim-body.inc — the FAT12 primitive/sector layer (shared body).
;
; docs/spec-evict-diskfile-cluster.md §11 (Phase 1). This is the CALSLT-pure,
; coarse (per-sector/cluster/directory) FAT12 engine BELOW the byte-stream
; cursor: physical sector I/O (dskio_calslt/read_sector/write_sector), mount,
; directory search (fat_find/name_cmp), cluster-chain walk (fat_open/
; fat_advance/fat_next_cluster/fat_read_file_sector), free-cluster allocation
; and FAT12 write-back (fat_alloc_cluster/fat_write_fat_entry/
; fat_write_buf_allfats/fat_total_clusters/fat_count_free/
; fat_flush_data_sector), and directory create/update (fat_dir_create/
; fat_dir_update). The BYTE-GRANULAR fat_io_* cursor (fat_io_open..
; fat_io_close) is NOT part of this file — it stays main-ROM-resident in both
; builds (spec §11's "why the cursor must not move now": the ARL_GETBYTE
; polymorphic RAM vector points at it, and that vector is only valid while the
; owning code is mapped in). `fat_delete` is ALSO primitive-layer (spec §11's
; table), but it sits AFTER the cursor in the original file, so it lives in
; the separate basic/fat-delete-body.inc (kept out of THIS file to preserve the
; original byte order — primitives, then cursor, then fat_delete; see that file's
; own header).
;
; Home (the format-body.inc / pu-render.inc pattern,
; docs/spec-evict-call-format.md, docs/spec-evict-printusing.md):
;   * (retired) lean 16 KB cart, inline at this
;     file's original position (right after the file header, before the
;     fat_io_* cursor) — byte-identical to the pre-eviction build (this file
;     is a pure relocation of that exact code, nothing added/removed/
;     reordered).
;   * sub-ROM PAGE-1 tenant (sub/fatprim.asm, repack): fatprim_tenant reads
;     a DISKOP_OP selector byte (RAM) and jumps to the requested primitive
;     below, with HL/DE intact (the primitive's own real inputs). Every
;     primitive's Cy/Z/register outputs are marshalled back through the
;     DISKOP result block (RAM) by a small tenant-side wrapper in
;     sub/fatprim.asm, because Cy cannot ride back through subrom_call/
;     CALSLT (spec §4/§11, the `sub/format.asm` "Cy cannot ride back" rule).
;     `write_sector`/`dskio_calslt` below ARE the tenant's sub-local CALSLT
;     copy (this file is included there wholesale, so no separate
;     duplication is needed the way `sub/format.asm` needed one for
;     write_sector alone — here the primitive/sector layer BEING MOVED
;     already starts at dskio_calslt).
;
; Clean-room: our own code, extracted verbatim from basic/fat.asm (see that
; file's header for the full FAT12/DSKIO provenance / oracle citations).

; ===========================================================================
; Physical-sector primitives — the ONLY routines that differ from disk.asm.
; They CALSLT the disk ROM's standard DSKIO entry ($4010) across slots, with the
; MSX2-TH register convention (A=drive, B=#sectors, C=media, DE=first logical
; sector, HL=buffer, CY=direction). DISKSLOT (the INIT-scan capture) is the slot;
; the target address is the FIXED $4010 offset (NOT the SYSTEM-vector bdos_entry).
; ===========================================================================

; dskio_calslt — issue one DSKIO call across slots to the in-slot disk ROM.
;   in:  A=drive, B=#sectors, C=media descriptor, DE=first logical sector,
;        HL=transfer buffer, CY=direction (clear=read / set=write).
;   out: CY=0 ok; CY=1 error (A=DSKIO error code, B=sectors not transferred).
; CALSLT clobbers IX/IY and (per its contract) the register file, but it preserves
; the direction CY into DSKIO and returns DSKIO's result CY (see file header).
; The slot word is built in RAM (CALSLT reads the slot from IYh): we reuse the
; INIT-scan CALSLT word SCAN_IY ($E0D9), dead once the REPL runs, exactly as
; bdos_call did. DSKIO_ENTRY = $4010 is the disk-ROM interface table's DSKIO offset
; (MSX2 TH §5; header is 16 bytes so the table starts at +$10).
dskio_calslt:
                push    af                  ; preserve the direction CY across IY setup
                ld      a,(DISKSLOT)
                ld      (SCAN_IY+1),a       ; IYh = disk ROM slot id
                ld      iy,(SCAN_IY)
                ld      ix,DSKIO_ENTRY      ; standard DSKIO entry ($4010)
                pop     af                  ; restore A=drive and the direction CY
                call    CALSLT              ; cross-slot DSKIO; returns DSKIO's CY/A/B
                ; D-DISKERR (docs/spec-basic-diskerr.md): DSKIO's error byte (published:
                ; 0 write protected, 2 not ready, 4 CRC, 6 seek, 8 record not found,
                ; 10 write fault, 12 other) becomes the MSX ERR code the verb raises --
                ; 70 `Disk offline`, 68 `Disk write protected`, else 69 `Disk I/O
                ; error` -- and a successful transfer clears it, so a later non-DSKIO
                ; failure in the same verb keeps its own face.
                jr      c,dc_fail
                xor     a
                ld      (DISKOP_ERR),a      ; CY clear: no code pending
                ret
dc_fail:
                push    af
                ld      c,70                ; not ready (2) -> Disk offline
                cp      2
                jr      z,dc_map
                ld      c,68                ; write protected (0) -> Disk write protected
                or      a
                jr      z,dc_map
                ld      c,69                ; anything else -> Disk I/O error
dc_map:
                ld      a,c
                ld      (DISKOP_ERR),a
                pop     af
                scf
                ret

; read_sector — read one logical sector into a buffer via cross-slot DSKIO.
;   in:  DE = logical sector number, HL = buffer
;   out: Cy = 0 ok, Cy = 1 error (A = DSKIO error code)
; Ported from disk.asm read_sector; the body is identical except the tail call now
; goes through dskio_calslt (cross-slot $4010) instead of the local dskio.
; 🏗️ D-FATENG Option 2: THE ONLY PLACE THE TWO HOMES DIFFER. Assembled into
; disk.rom the primitive reaches its OWN DSKIO by a plain local call; assembled
; into sub.rom (or main) it must CALSLT across to whatever disk ROM holds the
; slot. Everything else in this file is identical on both sides, which is what
; makes one source possible at all. Same shape as sv-diskwr.inc's `IF SUB_BUILD`.
; ⚠️ ONE LABEL, CONDITIONAL ONLY ON THE DIFFERING INSTRUCTION. The first cut
; put a whole `read_sector:` in each arm, and `check_dead_code` does not read
; `IF/ELSE` -- it kept one arm's span, lost `dskio_calslt`'s only reacher, and
; reported it plus dc_fail/dc_map as 47 B of dead code in [sub]. With the label
; outside, the span carries BOTH `jp` edges and the graph stays honest on both
; sides.
read_sector:
                xor     a               ; drive 0 (ignored); also Cy = 0 = read
                ld      b, 1            ; one sector
                ld      c, $F9          ; media byte ($F9 = 720K; ignored, single drive)
    IF DISK_BUILD
                jp      dskio           ; LOCAL: no slot to cross, and the inter-slot
                                        ; call disappears with it
    ELSE
                jp      dskio_calslt    ; tail-call: returns to our caller with DSKIO's CY
                                        ; (A=0 cleared CY here -> read direction)
    ENDIF

; write_sector — write one logical sector from a buffer via cross-slot DSKIO.
;   in:  DE = logical sector number, HL = buffer (512 bytes)
;   out: Cy = 0 ok, Cy = 1 error (A = DSKIO error code)
; Ported from disk.asm write_sector; identical body, cross-slot tail call.
; NAMED fatprim_write_sector (not write_sector): sub/format.asm ALREADY
; defines its own private write_sector (FORMAT's sub-local CALSLT write
; path, with its own FMT_RESULT stash) in the SAME sub.rom assembly as
; this tenant (sub/fatprim.asm) -- pasmo has one flat global namespace, so
; the two cannot share the name. (The retired lean cart aliased `write_sector equ
; fatprim_write_sector` right after this include, in basic/fat.asm, so every
; external call site — field.asm/files.asm's `call write_sector` —
; is unaffected; the repack build's resident shim (basic/fat.asm) is
; independently named `write_sector` already (a different code path, no
; collision there). Zero-byte rename either way (EQU never emits bytes).
fatprim_write_sector:
                ld      b, 1            ; one sector
                ld      c, $F9          ; media byte (ignored, single drive)
                ld      a, 0            ; drive 0 (ignored)
                scf                     ; Cy = 1 = WRITE direction (MSX2 TH DSKIO)
    IF DISK_BUILD
                jp      dskio           ; LOCAL, as read_sector above
    ELSE
                jp      dskio_calslt    ; tail-call: returns to our caller with DSKIO's CY
    ENDIF

; ===========================================================================
; FAT12 READ layer (ported verbatim from disk.asm §FAT12 layer).
; Sources: Microsoft FAT filesystem specification (BPB, FAT, directory) +
; ECMA-107 (geometry). All algorithms unchanged from disk.asm.
; ===========================================================================

; fat_mount — read the boot sector and derive FAT12 geometry into scratch.
;   out: Cy = 0 ok (geometry valid), Cy = 1 error (FDC error / not 512 B per sec)
fat_mount:
                ld      de, 0           ; boot sector = logical sector 0
                ld      hl, FSECTOR_BUF
                call    read_sector
                ret     c
                ; require 512 bytes per sector ($0200 LE) — matches FSECTOR_BUF
                ld      a, (FSECTOR_BUF + BPB_BYTSPERSEC)
                or      a
                jr      nz, fat_mount_bad   ; low byte must be 0
                ld      a, (FSECTOR_BUF + BPB_BYTSPERSEC + 1)
                cp      2
                jr      nz, fat_mount_bad   ; high byte must be 2 ($0200 = 512)
                ld      a, (FSECTOR_BUF + BPB_SECPERCLUS)
                ld      (FAT_SECPERCLUS), a
                ld      hl, (FSECTOR_BUF + BPB_RSVDSECCNT)
                ld      (FAT_FATSTART), hl  ; first FAT sector = reserved sectors
                ; first root sector = reserved + numFATs * secPerFAT
                ld      a, (FSECTOR_BUF + BPB_NUMFATS)
                ld      (FAT_NUMFATS), a    ; cache for the write path's FAT sync
                ld      b, a
                ld      de, (FSECTOR_BUF + BPB_FATSZ16)
                ld      (FAT_SECPERFAT), de ; cache for per-copy sector stride
                ld      hl, 0
fm_fatacc:
                add     hl, de
                djnz    fm_fatacc           ; HL = numFATs * secPerFAT
                ld      de, (FAT_FATSTART)
                add     hl, de
                ld      (FAT_FIRSTROOT), hl
                ; root sectors = (rootEnts*32 + 511) / 512  (512 B per sector)
                ld      hl, (FSECTOR_BUF + BPB_ROOTENTCNT)
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = rootEnts * 32
                ld      de, 511
                add     hl, de
                ld      a, h
                srl     a                   ; HL >> 9  (== H >> 1, result < 256)
                ld      l, a
                ld      h, 0
                ld      (FAT_ROOTSECS), hl
                ; first data sector = firstRoot + rootSecs
                ld      de, (FAT_FIRSTROOT)
                add     hl, de
                ld      (FAT_FIRSTDATA), hl
                or      a                   ; Cy = 0 success
                ret
fat_mount_bad:
                scf
                ret

; fat_find — search the root directory for an 8.3 file name.
;   in:  HL = pointer to an 11-byte name field (8 name + 3 ext, space-padded)
;   out: Cy = 0 found  -> FAT_FIRSTCLUS, FAT_FILESIZE set; Cy = 1 not found / error
; Compare is case-insensitive; FAT directories store upper-case 8.3 names.
fat_find:
                ld      (FAT_NAMEPTR), hl
                ld      hl, (FAT_FIRSTROOT)
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_ROOTSECS)
                ld      (FAT_DIRREM), hl
ff_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jr      z, ff_notfound      ; scanned every root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, FSECTOR_BUF
                call    read_sector
                ret     c                   ; propagate FDC error
                ld      hl, FSECTOR_BUF
                ld      b, 16               ; 512 / 32 entries per sector
ff_entloop:
                push    bc
                push    hl
                ld      a, (hl)
                or      a
                jr      z, ff_endmark       ; $00 = end of directory
                cp      $E5
                jr      z, ff_skip          ; deleted entry
                push    hl
                ld      de, 11
                add     hl, de
                ld      a, (hl)             ; attribute byte (+11)
                pop     hl
                and     $18                 ; volume-label | directory -> skip
                jr      nz, ff_skip
                ld      de, (FAT_NAMEPTR)
                call    name_cmp
                jr      z, ff_found
ff_skip:
                pop     hl
                ld      de, 32
                add     hl, de              ; next 32-byte directory entry
                pop     bc
                djnz    ff_entloop
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jr      ff_secloop
ff_endmark:
                pop     hl
                pop     bc
ff_notfound:
                scf
                ret
ff_found:
                pop     hl                  ; HL = directory entry
                pop     bc
                ; record the entry's location (sector + byte offset) for fat_delete.
                ; FWR_DIRSEC/FWR_DIROFF are write-side scratch the read path ignores
                ; and the write path re-sets, so reusing them here is safe.
                ld      de, (FAT_DIRSEC)
                ld      (FWR_DIRSEC), de
                push    hl
                ld      de, FSECTOR_BUF
                or      a
                sbc     hl, de              ; HL = entry offset within the sector
                ld      (FWR_DIROFF), hl
                pop     hl
                push    hl
                ld      de, 26
                add     hl, de
                ld      a, (hl)             ; first cluster low (+26)
                inc     hl
                ld      h, (hl)             ; first cluster high (+27)
                ld      l, a
                ld      (FAT_FIRSTCLUS), hl
                pop     hl
                push    hl
                ld      de, 28
                add     hl, de
                ld      de, FAT_FILESIZE
                ld      bc, 4
                ldir                        ; file size (+28..31, LE)
                pop     hl
                or      a                   ; Cy = 0 found
                ret

; name_cmp — compare two 11-byte 8.3 name fields, case-insensitive.
;   in:  HL = directory entry name, DE = search name
;   out: Z set if equal; trashes A, BC, DE, HL
name_cmp:
                ld      b, 11
nc_loop:
                ld      a, (de)
                cp      '?'                 ; '?' in the pattern (DE) matches ANY entry
                jr      z, nc_wild          ; char (FILES/KILL wildcard; MSX FCB '?')
                call    toupper
                ld      c, a
                ld      a, (hl)
                call    toupper
                cp      c
                ret     nz
nc_wild:
                inc     hl                  ; 16-bit inc: leaves flags intact
                inc     de
                djnz    nc_loop             ; djnz leaves flags intact
                ret                         ; Z set (final cp c on a match, or the
                                            ; cp '?' when the last char is a wildcard)

; toupper — fold a..z to A..Z; all other bytes unchanged.
;   in: A, out: A
toupper:
                cp      $61                 ; 'a'
                ret     c
                cp      $7B                 ; 'z' + 1
                ret     nc
                sub     $20
                ret

; fat_open — start sequential reading of the file found by fat_find.
fat_open:
                ld      hl, (FAT_FIRSTCLUS)
                ld      (FAT_CURCLUS), hl
                xor     a
                ld      (FAT_CLUSSEC), a
                ret

; fat_advance — step the iterator to the next cluster in the chain.
fat_advance:
                ld      hl, (FAT_CURCLUS)
                call    fat_next_cluster
                ld      (FAT_CURCLUS), hl
                xor     a
                ld      (FAT_CLUSSEC), a
                ret

; fat_next_cluster — follow the FAT12 chain one link.
;   in:  HL = current cluster
;   out: HL = next cluster (12-bit; >= $0FF8 means end-of-chain)
; FAT12 packs 1.5 bytes per entry, so an entry can straddle a 512-byte sector
; boundary; the high byte is then read from the following FAT sector.
; (Microsoft FAT spec §3.2.)
fat_next_cluster:
                ld      a, l
                and     1
                ld      (FAT_PARITY), a     ; cluster parity selects the nibbles
                ; fatofs = cluster + cluster/2  (= cluster * 3/2)
                ld      e, l
                ld      d, h
                srl     d
                rr      e                   ; DE = cluster >> 1
                add     hl, de              ; HL = fatofs
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a    ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                   ; fatofs >> 9 = FAT sector offset
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, FSECTOR_BUF
                call    read_sector
                ; byte0 = buf[byteidx]
                ld      hl, (FAT_BYTEIDX)
                ld      de, FSECTOR_BUF
                add     hl, de
                ld      a, (hl)
                ld      (FAT_B0), a
                ; byte1 = buf[byteidx+1], possibly in the next FAT sector
                ld      hl, (FAT_BYTEIDX)
                ld      de, 511
                or      a
                sbc     hl, de
                jr      z, fnc_straddle
                ld      hl, (FAT_BYTEIDX)
                ld      de, FSECTOR_BUF + 1
                add     hl, de
                ld      a, (hl)
                jr      fnc_combine
fnc_straddle:
                ld      hl, (FAT_FATSEC)
                inc     hl
                ex      de, hl
                ld      hl, FSECTOR_BUF
                call    read_sector
                ld      a, (FSECTOR_BUF)
fnc_combine:
                ld      (FAT_B1), a
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fnc_odd
                ; even cluster: next = B0 | ((B1 & $0F) << 8)
                ld      a, (FAT_B1)
                and     $0F
                ld      h, a
                ld      a, (FAT_B0)
                ld      l, a
                ret
fnc_odd:
                ; odd cluster: next = (B1 << 4) | (B0 >> 4)
                ld      a, (FAT_B1)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = B1 << 4
                ld      a, (FAT_B0)
                rrca
                rrca
                rrca
                rrca
                and     $0F                 ; A = B0 >> 4
                ld      e, a
                ld      d, 0
                add     hl, de
                ret

; fat_read_file_sector — read the open file's next data sector into FSECTOR_BUF.
;   out: Cy = 0 ok (FSECTOR_BUF holds 512 bytes), Cy = 1 end-of-file / error
; The caller bounds the true end of file with FAT_FILESIZE; this returns Cy = 1
; once the cluster chain reaches an end-of-chain marker.
fat_read_file_sector:
                ld      a, (FAT_CLUSSEC)
                ld      hl, FAT_SECPERCLUS
                cp      (hl)
                jr      c, frs_incluster
                call    fat_advance         ; current cluster exhausted -> next
frs_incluster:
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                jr      c, frs_eof          ; cluster < 2 (free / empty file)
                ld      hl, (FAT_CURCLUS)
                ld      de, $0FF8
                or      a
                sbc     hl, de
                jr      nc, frs_eof         ; cluster >= $0FF8 = end-of-chain
                ; sector = firstData + (cluster-2)*secPerClus + clussec
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                ex      de, hl              ; DE = cluster - 2
                ld      hl, 0
                ld      a, (FAT_SECPERCLUS)
                ld      b, a
frs_mul:
                add     hl, de
                djnz    frs_mul             ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (FAT_CLUSSEC)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl
                ld      hl, FSECTOR_BUF
                call    read_sector
                ret     c
                ld      a, (FAT_CLUSSEC)
                inc     a
                ld      (FAT_CLUSSEC), a
                or      a                   ; Cy = 0 success
                ret
frs_eof:
                scf
                ret

; ⚠️ SUB-ROM ONLY, and it stays that way: this primitive is sized for the sub-ROM,
; its only real home. (It used to be gated out of the retired lean 16 KB cart,
; which was byte-full and would have overrun its $8000 ceiling outright.)
; fat_restage_channel — re-read into FSECTOR_BUF whatever the LIVE channel had
; staged there before it was switched away (D-FCH S-FCH-1,
; docs/spec-basic-filechan-alloc.md §3.1).
;   in:  the engine globals already hold the channel's state (fch_load_ctx has
;        just LDIR'd it in); FCH_ACTIVE names the channel.
;   out: Cy = 0 ok — INCLUDING "nothing was staged", which is the common case;
;        Cy = 1 read error.
;
; This is what replaces the per-channel 512-byte save copy. The reference charges
; 267 B per channel — less than one sector — so it cannot be keeping a private
; sector per channel either; it treats the shared buffer as a CACHE
; (docs/chancost-cf3300-characterization.md §5.1).
;
; ⚠️ Reads the mode from FCH_MODES[FCH_ACTIVE], NOT from the FCH_MODE mirror:
; fch_sync_mirror runs AFTER fch_load_ctx, so at re-stage time FCH_MODE still
; holds the mode of the channel we switched AWAY from.
fat_restage_channel:
                ld      a, (FCH_ACTIVE)
                or      a
                ret     z                   ; no channel live -> nothing staged
                ld      e, a
                ld      d, 0
                ld      hl, FCH_MODES
                add     hl, de
                ld      a, (hl)             ; A = the live channel's own mode
                dec     a
                jr      z, frst_read        ; 1 = INPUT
                dec     a
                jr      z, frst_write       ; 2 = OUTPUT
                or      a                   ; device channels own no sector; Cy=0
                ret
; fat_detach_channel — write the LIVE channel's dirty partial sector out, IN
; PLACE, so the shared FSECTOR_BUF can be handed to another channel. The inverse
; of fat_restage_channel; together they are the whole write-back cache.
;   out: Cy = 1 on a write error (disk full), Cy = 0 otherwise (including the
;        common "nothing dirty" case).
;
; ⚠️ Sited HERE, not resident, purely for space: as resident code this cost 43 B
; of main page 1 against 6 B free (measured). Everything it touches
; (fat_flush_data_sector, FWR_*) is already sub-local.
; ⚠️ Reads FCH_MODES[FCH_ACTIVE], not the FCH_MODE mirror — same reason as
; fat_restage_channel.
; ⚠️ fat_flush_data_sector STEPS PAST the sector it writes. Mid-stream we are NOT
; finishing this sector, so step back onto it: the re-stage then reads exactly
; what we wrote and appending resumes at FWR_BUFLEN over the zero padding the
; flush laid down. Stepping back is also right when the flush ALLOCATED a cluster
; — it sets FWR_SECIDX=0, writes, then increments to 1, so the decrement lands on
; sector 0 of the NEW FWR_CLUS.
fat_detach_channel:
                ld      a, (FCH_ACTIVE)
                or      a
                ret     z                   ; nothing live
                ld      e, a
                ld      d, 0
                ld      hl, FCH_MODES
                add     hl, de
                ld      a, (hl)
                cp      2                   ; only an OUTPUT channel can be dirty
                jr      z, fdet_maybe
                or      a                   ; Cy = 0 — `cp` LEAVES IT SET for A<2
                ret
fdet_maybe:
                ld      hl, (FWR_BUFLEN)
                ld      a, h
                or      l
                ret     z                   ; nothing buffered -> already clean
                call    fat_flush_data_sector
                ret     c                   ; disk full / write error
                ld      a, (FWR_SECIDX)
                dec     a
                ld      (FWR_SECIDX), a
                or      a                   ; Cy = 0 success
                ret

frst_read:
                ; the read iterator leaves FAT_CLUSSEC one PAST the staged sector
                ; (fat_read_file_sector increments after the read), so step back
                ; onto it and let the normal reader re-read + re-increment.
                ld      a, (FAT_CLUSSEC)
                or      a
                ret     z                   ; nothing read yet -> buffer is empty
                dec     a
                ld      (FAT_CLUSSEC), a
                jp      fat_read_file_sector
frst_write:
                ; fch_flush_active wrote this partial sector out IN PLACE and
                ; stepped FWR_SECIDX back onto it, so (FWR_CLUS, FWR_SECIDX)
                ; names it. FWR_BUFLEN survives in the saved state, so appending
                ; resumes at the right offset over the zero padding the flush laid.
                ld      hl, (FWR_BUFLEN)
                ld      a, h
                or      l
                ret     z                   ; nothing buffered -> nothing to restore
                ; absolute sector = firstData + (cluster-2)*secPerClus + WRSECIDX
                ld      hl, (FWR_CLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                ex      de, hl              ; DE = cluster - 2
                ld      hl, 0
                ld      a, (FAT_SECPERCLUS)
                ld      b, a
frst_mul:
                add     hl, de
                djnz    frst_mul            ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (FWR_SECIDX)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl
                ld      hl, FSECTOR_BUF
                jp      read_sector

; ===========================================================================
; FAT12 WRITE-BACK substrate (ported verbatim from disk.asm §FAT12 write-back).
; All structures (free-cluster scan, 12-bit entry pack, multi-FAT sync, directory
; create/update) realise the Microsoft FAT specification; the physical sector
; write goes through write_sector (cross-slot DSKIO with CY=1). Buffer discipline
; unchanged: the file DATA being accumulated lives in FSECTOR_BUF
; (fat_flush_data_sector writes it out); the FAT/dir METADATA helpers use the
; independent FWBUF, so a cluster scan or dir stamp never disturbs the in-flight
; data sector.
; ===========================================================================

; fat_read_fat_sector — read FAT-copy-0 sector that holds cluster N's entry.
;   in:  HL = cluster number
;   out: FWBUF holds that FAT sector; (FAT_FATSEC) = its absolute sector;
;        (FAT_BYTEIDX) = byte index of the entry's low byte within the sector;
;        (FAT_PARITY) = cluster & 1; Cy reflects the read.
fat_read_fat_sector:
                ld      a, l
                and     1
                ld      (FAT_PARITY), a
                ld      e, l
                ld      d, h
                srl     d
                rr      e                   ; DE = cluster >> 1
                add     hl, de              ; HL = fatofs = cluster * 3/2
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a    ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                   ; fatofs >> 9 = FAT sector offset
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, FWBUF
                jp      read_sector

; fat_alloc_cluster — find a free ($000) cluster, mark it EOC, sync all FATs.
;   out: Cy = 0 ok, HL = the allocated cluster number; Cy = 1 = disk full / error
; (Microsoft FAT spec §3.2: $000 = free, $FF8-$FFF = end-of-chain.)
fat_alloc_cluster:
                call    fat_total_clusters  ; DE = total clusters (reads boot sector)
                ld      (FAT_WRTMP), de
                ; FAT_FATSEC tracks which FAT sector is in FWBUF; -1 = none loaded.
                ld      hl, $FFFF
                ld      (FAT_WRTMP2), hl    ; cached-sector = none
                ld      hl, 2               ; first data cluster
fac_loop:
                ld      de, (FAT_WRTMP)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jr      nc, fac_full        ; cluster >= total -> disk full
                ; which FAT sector + byte index holds cluster HL's entry?
                push    hl
                ld      a, l
                and     1
                ld      (FAT_PARITY), a
                ld      e, l
                ld      d, h
                srl     d
                rr      e                   ; DE = cluster >> 1
                add     hl, de              ; HL = fatofs = cluster * 3/2
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a    ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                   ; FAT sector offset = fatofs >> 9
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de              ; HL = absolute FAT sector
                ; is this sector already in FWBUF? (cached-sector compare)
                ld      de, (FAT_WRTMP2)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jr      z, fac_have_sec     ; already loaded -> no re-read
                ld      (FAT_WRTMP2), hl    ; remember the new cached sector
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, FWBUF
                call    read_sector
                jr      c, fac_rderr
fac_have_sec:
                ; read the 12-bit entry from FWBUF (handles straddle into next sec).
                pop     hl                  ; HL = cluster
                push    hl
                call    fac_entry_from_wbuf ; DE = entry value
                ld      a, d
                or      e
                pop     hl
                jr      z, fac_found        ; $000 -> free
                inc     hl
                jr      fac_loop
fac_rderr:
                pop     hl
                ret                         ; Cy set from read_sector
fac_found:
                ; claim it: write EOC into every FAT copy, return the cluster.
                push    hl
                ld      de, EOC
                call    fat_write_fat_entry ; HL = cluster, DE = value
                pop     hl
                ret     c                   ; write error propagates (Cy set)
                or      a                   ; Cy = 0 success, HL = cluster
                ret
fac_full:
                scf                         ; disk full
                ret

; fac_entry_from_wbuf — unpack cluster (FAT_BYTEIDX/FAT_PARITY already set) from
; the FAT sector currently in FWBUF; if the entry straddles the 512-byte boundary
; (byteidx == 511) read the FOLLOWING FAT sector for the high byte.
;   out: DE = 12-bit entry value; preserves nothing but DE
fac_entry_from_wbuf:
                ld      hl, (FAT_BYTEIDX)
                ld      de, FWBUF
                add     hl, de
                ld      a, (hl)
                ld      (FAT_B0), a
                ld      hl, (FAT_BYTEIDX)
                ld      de, 511
                or      a
                sbc     hl, de
                jr      z, fac_straddle
                ld      hl, (FAT_BYTEIDX)
                ld      de, FWBUF + 1
                add     hl, de
                ld      a, (hl)
                jr      fac_comb
fac_straddle:
                ; read the next FAT sector into FWBUF and cache it.
                ld      hl, (FAT_FATSEC)
                inc     hl
                ld      (FAT_FATSEC), hl
                ld      (FAT_WRTMP2), hl
                ex      de, hl
                ld      hl, FWBUF
                call    read_sector
                ld      a, (FWBUF)
fac_comb:
                ld      (FAT_B1), a
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fac_e_odd
                ld      a, (FAT_B1)
                and     $0F
                ld      d, a
                ld      a, (FAT_B0)
                ld      e, a
                ret
fac_e_odd:
                ld      a, (FAT_B1)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                ld      a, (FAT_B0)
                rrca
                rrca
                rrca
                rrca
                and     $0F
                ld      e, a
                ld      d, 0
                add     hl, de
                ex      de, hl
                ret

; fat_write_fat_entry — set a cluster's 12-bit value in EVERY FAT copy on disk.
;   in:  HL = cluster, DE = 12-bit value to store
;   out: Cy = 0 ok, Cy = 1 error
; (Microsoft FAT spec §3.2 packing; multi-FAT sync per BPB_NUMFATS.)
fat_write_fat_entry:
                ld      (FAT_WRTMP), de     ; save the value
                push    hl                  ; save cluster
                call    fat_read_fat_sector ; FWBUF = FAT sector 0; BYTEIDX/PARITY set
                ; --- pack the low byte / shared nibble into FWBUF[byteidx]
                ld      hl, (FAT_BYTEIDX)
                ld      de, FWBUF
                add     hl, de
                push    hl                  ; HL = &buf[byteidx]
                ld      de, (FAT_WRTMP)     ; DE = value
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fwe_odd0
                ; even: buf[byteidx] = value & $FF
                ld      a, e
                ld      (hl), a
                jr      fwe_byte1
fwe_odd0:
                ; odd: buf[byteidx] = (buf[byteidx] & $0F) | ((value & $0F) << 4)
                ld      a, (hl)
                and     $0F
                ld      b, a
                ld      a, e
                and     $0F
                rlca
                rlca
                rlca
                rlca
                or      b
                ld      (hl), a
fwe_byte1:
                pop     hl                  ; HL = &buf[byteidx]
                ; the second byte may live in the next FAT sector.
                ld      bc, (FAT_BYTEIDX)
                ld      a, c
                cp      $FF
                jr      nz, fwe_b1_same     ; byteidx != 511 -> same sector
                ld      a, b
                or      a
                jr      nz, fwe_b1_same     ; (byteidx high != 0; impossible for 512)
                ; straddle: byte1 is buf[0] of the NEXT FAT sector. First persist
                ; this sector to all FATs, then load + patch the next sector.
                call    fat_write_buf_allfats
                jr      c, fwe_err
                ld      hl, (FAT_FATSEC)
                inc     hl
                ld      (FAT_FATSEC), hl    ; advance to the straddle sector
                ex      de, hl
                ld      hl, FWBUF
                call    read_sector
                jr      c, fwe_err
                ld      hl, FWBUF           ; patch byte 0 of the next sector
                ld      de, (FAT_WRTMP)
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fwe_str_odd
                ; even straddle: buf[0] = (buf[0] & $F0) | ((value >> 8) & $0F)
                ld      a, (hl)
                and     $F0
                ld      b, a
                ld      a, d
                and     $0F
                or      b
                ld      (hl), a
                jr      fwe_finish
fwe_str_odd:
                ; odd straddle: buf[0] = value[11:4] = (value >> 4) & $FF
                ld      hl, FWBUF
                ld      a, e
                rrca
                rrca
                rrca
                rrca
                and     $0F                 ; high nibble of E -> low nibble of result
                ld      b, a
                ld      a, d
                rlca
                rlca
                rlca
                rlca
                and     $F0                 ; D<<4 -> high nibble of result
                or      b
                ld      (hl), a
                jr      fwe_finish
fwe_b1_same:
                ; second byte is buf[byteidx+1] in the same sector.
                inc     hl                  ; HL = &buf[byteidx+1]
                ld      de, (FAT_WRTMP)
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fwe_same_odd
                ; even: buf[byteidx+1] = (buf[byteidx+1] & $F0) | ((value>>8)&$0F)
                ld      a, (hl)
                and     $F0
                ld      b, a
                ld      a, d
                and     $0F
                or      b
                ld      (hl), a
                jr      fwe_finish
fwe_same_odd:
                ; odd: buf[byteidx+1] = (value >> 4) & $FF
                ld      a, e
                rrca
                rrca
                rrca
                rrca
                and     $0F
                ld      b, a
                ld      a, d
                rlca
                rlca
                rlca
                rlca
                and     $F0
                or      b
                ld      (hl), a
fwe_finish:
                pop     hl                  ; discard saved cluster
                ; persist the (current) FAT sector to all FAT copies.
                jp      fat_write_buf_allfats
fwe_err:
                pop     hl                  ; discard saved cluster (keep stack sane)
                scf                         ; report the I/O error
                ret

; fat_write_buf_allfats — write FWBUF back to (FAT_FATSEC) in every FAT copy.
;   in:  FWBUF holds the sector; FAT_FATSEC = its sector in FAT copy 0
;   out: Cy = 0 ok, Cy = 1 error
; (Microsoft FAT spec §3.1: NumFATs identical copies; §3.2: same packing.)
fat_write_buf_allfats:
                ld      a, (FAT_NUMFATS)
                ld      b, a                ; B = copies to write
                ld      hl, (FAT_FATSEC)    ; copy-0 target sector
fwba_loop:
                push    bc
                push    hl
                ex      de, hl              ; DE = target sector
                ld      hl, FWBUF
                call    fatprim_write_sector
                pop     hl
                pop     bc
                ret     c                   ; write error
                ; advance to the same sector in the next FAT copy.
                ld      de, (FAT_SECPERFAT)
                add     hl, de
                djnz    fwba_loop
                or      a                   ; Cy = 0 success
                ret

; fat_total_clusters — total cluster count of the volume (2 + data clusters).
;   out: DE = total clusters; preserves HL
; (Microsoft FAT spec §3.3.) Re-reads the boot sector into FWBUF (NOT FSECTOR_BUF,
; which may hold in-flight write data).
fat_total_clusters:
                push    hl
                ld      de, 0
                ld      hl, FWBUF
                call    read_sector
                jr      c, ftc_done         ; on error report 2 (no free clusters)
                ld      hl, (FWBUF + 19)    ; total sectors 16-bit (BPB +19)
                ld      de, (FAT_FIRSTDATA)
                or      a
                sbc     hl, de              ; HL = data sectors
                ; DE accumulates dataSectors / secPerClus.
                ld      de, 0
                ld      a, (FAT_SECPERCLUS)
                ld      c, a
ftc_div:
                ld      a, l
                or      h
                jr      z, ftc_divdone
                ld      a, l
                sub     c
                ld      l, a
                jr      nc, ftc_nob
                dec     h
ftc_nob:
                inc     de
                jr      ftc_div
ftc_divdone:
                inc     de
                inc     de                  ; + 2 (first data cluster is 2)
ftc_done:
                pop     hl
                ret

; fat_count_free — count free clusters (FAT entries == 0) over the data range
; [2, total). Mounts first. Used by DSKF.
;   out: DE = free cluster count (0 on mount error).
; Reads each FAT sector ONCE (caching it in FSECTOR_BUF, keyed by FWR_FIRST) and
; decodes the 12-bit entry for each cluster inline, counting the zeros. A naive
; one-read-per-cluster scan is correct but ~700 cross-slot DSKIO reads — far too
; slow on a real FDC; caching collapses it to a handful. Loop state lives in RAM
; (the register file is clobbered by read_sector's CALSLT): FAT_WRTMP = total,
; FAT_WRTMP2 = running count, FWR_CLUS = current cluster, FWR_FIRST = cached FAT
; sector (all write-side scratch, dead during this read-only query); FAT_B0/FAT_B1
; hold the entry's two bytes. Sources: Microsoft FAT spec (a 0 entry is free; the
; 12-bit even/odd nibble packing).
fat_count_free:
                call    fat_mount
                jp      c, fcf_zero
                call    fat_total_clusters  ; DE = total clusters (2 + data)
                ld      (FAT_WRTMP), de
                ld      hl, 0
                ld      (FAT_WRTMP2), hl    ; free count = 0
                ld      hl, $FFFF
                ld      (FWR_FIRST), hl     ; cached FAT sector = none
                ld      hl, 2
                ld      (FWR_CLUS), hl
fcf_loop:
                ld      hl, (FWR_CLUS)
                ld      de, (FAT_WRTMP)
                or      a
                sbc     hl, de              ; cluster - total
                jp      nc, fcf_done        ; cluster >= total -> done
                ; offset = cluster + cluster>>1 (= cluster * 3/2)
                ld      hl, (FWR_CLUS)
                ld      d, h
                ld      e, l
                srl     d
                rr      e                   ; DE = cluster>>1
                add     hl, de              ; HL = byte offset within the FAT
                ; FAT sector = FAT_FATSTART + (offset>>9)
                ld      a, h
                srl     a                   ; A = offset>>9
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de              ; HL = absolute FAT sector
                ld      de, (FWR_FIRST)
                or      a
                push    hl
                sbc     hl, de
                pop     hl
                jr      z, fcf_have         ; already cached
                ld      (FWR_FIRST), hl
                ex      de, hl
                ld      hl, FSECTOR_BUF
                call    read_sector         ; cache this FAT sector
fcf_have:
                ; byteidx = offset & 511
                ld      hl, (FWR_CLUS)
                ld      d, h
                ld      e, l
                srl     d
                rr      e
                add     hl, de              ; HL = offset
                ld      a, h
                and     1
                ld      h, a                ; HL = byteidx (0..511)
                ; byte0 = FSECTOR_BUF[byteidx]
                push    hl
                ld      de, FSECTOR_BUF
                add     hl, de
                ld      a, (hl)
                ld      (FAT_B0), a
                pop     hl                  ; HL = byteidx
                ; byte1 = byteidx==511 ? next FAT sector[0] : FSECTOR_BUF[byteidx+1]
                ld      a, h
                cp      1
                jr      nz, fcf_b1_same
                ld      a, l
                cp      $FF
                jr      nz, fcf_b1_same     ; byteidx != 511 -> same sector
                ; straddle: byte1 lives in the next FAT sector (read into FWBUF).
                ld      hl, (FWR_FIRST)
                inc     hl
                ex      de, hl
                ld      hl, FWBUF
                call    read_sector
                ld      a, (FWBUF)
                jr      fcf_haveb1
fcf_b1_same:
                inc     hl                  ; byteidx+1
                ld      de, FSECTOR_BUF
                add     hl, de
                ld      a, (hl)
fcf_haveb1:
                ld      (FAT_B1), a
                ; the 12-bit entry is zero iff the relevant nibbles are all zero.
                ld      a, (FWR_CLUS)
                and     1
                jr      nz, fcf_odd
                ; even: zero iff byte0==0 and (byte1 & $0F)==0
                ld      a, (FAT_B0)
                or      a
                jr      nz, fcf_used
                ld      a, (FAT_B1)
                and     $0F
                jr      nz, fcf_used
                jr      fcf_free
fcf_odd:
                ; odd: zero iff (byte0 & $F0)==0 and byte1==0
                ld      a, (FAT_B0)
                and     $F0
                jr      nz, fcf_used
                ld      a, (FAT_B1)
                or      a
                jr      nz, fcf_used
fcf_free:
                ld      hl, (FAT_WRTMP2)
                inc     hl
                ld      (FAT_WRTMP2), hl    ; free++
fcf_used:
                ld      hl, (FWR_CLUS)
                inc     hl
                ld      (FWR_CLUS), hl
                jp      fcf_loop
fcf_done:
                ld      de, (FAT_WRTMP2)
                ret
fcf_zero:
                ld      de, 0
                ret

; fat_flush_data_sector — write FSECTOR_BUF (the current 512-byte data buffer) to
; the file's current data sector, allocating/extending the cluster chain first.
;   out: Cy = 0 ok, Cy = 1 = disk full / write error
; (Microsoft FAT spec §3.3 data-sector math.)
fat_flush_data_sector:
                ; zero-pad the unused tail of the buffer (bytes WRBUFLEN..511) so a
                ; partial final sector writes 512 well-defined bytes.
                ld      hl, 512
                ld      de, (FWR_BUFLEN)
                or      a
                sbc     hl, de              ; HL = 512 - WRBUFLEN (pad count, 0..512)
                jr      z, ffds_nopad       ; buffer already full -> no pad
                jr      c, ffds_nopad       ; (defensive: WRBUFLEN > 512 never happens)
                ld      b, h
                ld      c, l                ; BC = pad count
                ld      hl, FSECTOR_BUF
                add     hl, de              ; HL = FSECTOR_BUF + WRBUFLEN = first pad byte
ffds_padloop:
                ld      a, b
                or      c
                jr      z, ffds_nopad
                xor     a
                ld      (hl), a
                inc     hl
                dec     bc
                jr      ffds_padloop
ffds_nopad:
                ; ensure we have a data cluster to write into.
                ld      hl, (FWR_CLUS)
                ld      a, h
                or      l
                jr      z, ffds_alloc       ; no cluster yet -> allocate the first
                ld      a, (FWR_SECIDX)
                ld      hl, FAT_SECPERCLUS
                cp      (hl)
                jr      c, ffds_haveclus    ; room in the current cluster
ffds_alloc:
                ; allocate a new cluster (first one, or chain extension).
                call    fat_alloc_cluster
                ret     c                   ; disk full
                ; HL = new cluster. Link it: if a previous cluster exists, point it
                ; at HL; else record HL as the file's first cluster.
                ld      de, (FWR_CLUS)
                ld      a, d
                or      e
                jr      z, ffds_first       ; no previous cluster -> this is first
                push    hl                  ; save new cluster
                ex      de, hl              ; HL = previous cluster
                pop     de                  ; DE = new cluster (value to link)
                push    de
                call    fat_write_fat_entry ; previous -> new (12-bit link)
                pop     hl                  ; HL = new cluster
                ret     c
                jr      ffds_setclus
ffds_first:
                ld      (FWR_FIRST), hl     ; remember the file's first cluster
ffds_setclus:
                ld      (FWR_CLUS), hl
                xor     a
                ld      (FWR_SECIDX), a     ; start at sector 0 of the new cluster
ffds_haveclus:
                ; absolute sector = firstData + (cluster-2)*secPerClus + WRSECIDX
                ld      hl, (FWR_CLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                ex      de, hl              ; DE = cluster - 2
                ld      hl, 0
                ld      a, (FAT_SECPERCLUS)
                ld      b, a
ffds_mul:
                add     hl, de
                djnz    ffds_mul            ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (FWR_SECIDX)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl              ; DE = sector
                ld      hl, FSECTOR_BUF
                call    fatprim_write_sector
                ret     c
                ld      a, (FWR_SECIDX)
                inc     a
                ld      (FWR_SECIDX), a
                or      a                   ; Cy = 0 success
                ret

; fat_dir_create — find/make a root-directory slot for an 8.3 name and write a
; fresh entry; record the slot's sector + offset in FWR_DIRSEC/FWR_DIROFF.
;   in:  HL = 11-byte 8.3 name field
;   out: Cy = 0 ok, Cy = 1 = directory full / I/O error
; (Microsoft FAT spec §3.4. Date/time = 0 is the documented divergence — no clock.)
fat_dir_create:
                ld      (FAT_NAMEPTR), hl
                ld      hl, (FAT_FIRSTROOT)
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_ROOTSECS)
                ld      (FAT_DIRREM), hl
fdcr_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jr      z, fdcr_full        ; no slot in any root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, FWBUF
                call    read_sector
                ret     c
                ld      hl, FWBUF
                ld      b, 16               ; 16 entries per 512-byte sector
fdcr_entloop:
                push    bc
                push    hl
                ld      a, (hl)
                or      a
                jr      z, fdcr_useslot     ; $00 end-marker -> free slot here
                cp      $E5
                jr      z, fdcr_useslot     ; $E5 deleted -> reusable slot
                ; same-name existing entry? (truncate-in-place)
                ld      de, (FAT_NAMEPTR)
                call    name_cmp
                jr      z, fdcr_useslot
                pop     hl
                ld      de, 32
                add     hl, de
                pop     bc
                djnz    fdcr_entloop
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jr      fdcr_secloop
fdcr_useslot:
                pop     hl                  ; HL = dir entry slot in FWBUF
                pop     bc
                ; record the slot's sector + byte offset for fat_dir_update.
                ld      de, (FAT_DIRSEC)
                ld      (FWR_DIRSEC), de
                push    hl
                ld      de, FWBUF
                or      a
                sbc     hl, de              ; HL = offset within the sector
                ld      (FWR_DIROFF), hl
                pop     hl
                ; write the 11-byte name (case already 8.3 upper from the caller).
                push    hl
                ex      de, hl              ; DE = dest slot
                ld      hl, (FAT_NAMEPTR)
                ld      bc, 11
                ldir                        ; name -> entry +0..10
                ; +11 = attribute $00 (normal file; ORACLE: matches MSX-DOS Create).
                xor     a
                ld      (de), a             ; +11 = $00
                inc     de
                ; zero +12..+31 (S1/S2, rec-count, alloc-map, date/time, first
                ; cluster, size). Date/time = 0 is the documented divergence.
                ld      b, 20               ; +12..+31 is 20 bytes
fdcr_zero:
                xor     a
                ld      (de), a
                inc     de
                djnz    fdcr_zero
                pop     hl                  ; discard slot pointer
                ; write the dir sector back.
                ld      de, (FWR_DIRSEC)
                ld      hl, FWBUF
                call    fatprim_write_sector
                ret     c
                or      a                   ; Cy = 0 success
                ret
fdcr_full:
                scf
                ret

; fat_dir_update — rewrite the open-for-write file's directory entry at Close with
; its true byte count (DIRENT_FILESIZE) and first cluster (DIRENT_FIRSTCLUS).
;   out: Cy = 0 ok, Cy = 1 = I/O error
; (Microsoft FAT spec §3.4.)
fat_dir_update:
                ld      de, (FWR_DIRSEC)
                ld      hl, FWBUF
                call    read_sector
                ret     c
                ; HL = &entry = FWBUF + DIROFF
                ld      hl, (FWR_DIROFF)
                ld      de, FWBUF
                add     hl, de
                ; +26 first cluster (LE) = FWR_FIRST
                push    hl
                ld      de, DIRENT_FIRSTCLUS
                add     hl, de
                ld      de, (FWR_FIRST)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                pop     hl
                ; +28 file size (4-byte LE) = FWR_BYTES
                ld      de, DIRENT_FILESIZE
                add     hl, de
                ex      de, hl              ; DE = &entry+28
                ld      hl, FWR_BYTES
                ld      bc, 4
                ldir
                ; write the dir sector back.
                ld      de, (FWR_DIRSEC)
                ld      hl, FWBUF
                call    fatprim_write_sector
                ret     c
                or      a                   ; Cy = 0 success
                ret
