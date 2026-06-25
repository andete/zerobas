; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; FAT12 + BDOS/FCB file layer (read + write-back substrate)
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- BDOS WRITE calls (disk/PROVENANCE.md §BDOS interface, §FAT12 write-back) -

; bdos_create ($16) — create (or truncate-if-exists) the file named in the FCB,
; ready for sequential writing from offset 0.
;   in:  DE = FCB pointer (FCB+1 = 11-byte 8.3 name)
;   out: A = $00 created / $FF error (disk full / write protect / I/O)
; Mounts the volume, then finds or makes a root-directory slot for the name and
; writes a fresh dir entry (name, attribute $00, first cluster = 0, size = 0,
; timestamps = 0 — see the date/time divergence in disk/PROVENANCE.md). No data
; cluster is allocated yet: the first cluster is allocated lazily on the first
; Sequential Write, so a zero-byte file occupies no clusters (matching MSX-DOS).
bdos_create:
                jp      bdos_create_body    ; Tier-2 3b: divert; veneer fills the gap
                ds      $46C8 - $, $00      ; anchor the canonical address
                jp      k_46C8              ; $46C8: COMMAND.COM-load kernel veneer
                ds      $46E6 - $, $00      ; pad to bdos_create_failpop (net-zero)
bdos_create_failpop:
                pop     hl
bdos_create_err:
                xor     a
                ld      (BDOS_WRMODE), a
                ld      a, $FF
                ret

; bdos_seqwrite ($15) — write the next 128-byte record FROM the DTA into the file.
;   out: A = $00 ok / $01 disk full / $FF error (MSX2 TH, BDOS conventions)
; Buffers RECSIZE (128) bytes from BDOS_DTA into SECTOR_BUF at offset BDOS_WRBUFLEN;
; whenever the buffer fills (512 bytes) it is flushed to the file's current data
; sector (allocating/extending the cluster chain as needed) and the buffer resets.
; BDOS_WRBYTES accumulates the true byte count for Close to stamp into the dir
; entry. (CP/M / MSX-DOS sequential write delivers a fixed 128-byte record from
; the DTA — MSX2 TH FCB sequential I/O; record framing as the read side.)
bdos_seqwrite:
                ld      a, (BDOS_WRMODE)
                or      a
                jr      z, bsw_err          ; not open for write
                ; copy RECSIZE bytes DTA -> SECTOR_BUF + BDOS_WRBUFLEN
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, SECTOR_BUF
                add     hl, de              ; HL = dest in SECTOR_BUF
                ex      de, hl              ; DE = dest
                ld      hl, (BDOS_DTA)      ; HL = source record (settable DTA)
                ld      bc, RECSIZE
                ldir                        ; copy 128 bytes into the buffer
                ; advance buffered length and total byte count by RECSIZE.
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, RECSIZE
                add     hl, de
                ld      (BDOS_WRBUFLEN), hl
                call    wrbytes_add_recsize ; BDOS_WRBYTES += RECSIZE (4-byte LE)
                ; if the 512-byte buffer is now full, flush it to the file.
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, 512
                or      a
                sbc     hl, de
                jr      c, bsw_ok           ; buffer not full yet
                call    fat_flush_data_sector
                jr      c, bsw_full         ; disk full / write error
                ld      hl, 0
                ld      (BDOS_WRBUFLEN), hl ; buffer drained
bsw_ok:
                xor     a                   ; A = $00 success
                ret
bsw_full:
                ld      a, $01              ; disk full (MSX-DOS seq-write code)
                ret
bsw_err:
                ld      a, $FF
                ret

; wrbytes_add_recsize — BDOS_WRBYTES += RECSIZE, 4-byte little-endian add.
wrbytes_add_recsize:
                ld      hl, BDOS_WRBYTES
                ld      a, (hl)
                add     a, RECSIZE
                ld      (hl), a
                inc     hl
                ld      b, 3                ; carry through the upper 3 bytes
wba_loop:
                ld      a, (hl)
                adc     a, 0
                ld      (hl), a
                inc     hl
                djnz    wba_loop
                ret

; --- FAT12 layer (disk/PROVENANCE.md §FAT12 layer) -------------------------
; Read-only FAT12 on top of the DSKIO sector reader. Sources: Microsoft FAT
; filesystem specification (BPB, FAT, directory) and ECMA-107 (geometry).
; Assumes 512-byte sectors (validated at mount); the on-disk BPB supplies every
; other geometry value, so the same code serves any FAT12 image the BPB
; describes. These routines are internal helpers; the BDOS/FCB layer (next TODO
; item) wires them to zerobas's BLOAD path. End-to-end validation waits on the
; openMSX machine config + oracle probe 2 (DSKIO boot-sector read).

; read_sector — read one logical sector into a buffer via the DSKIO core.
;   in:  DE = logical sector number, HL = buffer
;   out: Cy = 0 ok, Cy = 1 error (A = DSKIO error code)
read_sector:
                xor     a               ; drive 0 (ignored); also Cy = 0 = read
                ld      b, 1            ; one sector
                ld      c, $F9          ; media byte (ignored, single drive)
                jp      dskio           ; tail-call: dskio returns to our caller

; fat_mount — read the boot sector and derive FAT12 geometry into scratch.
;   out: Cy = 0 ok (geometry valid), Cy = 1 error (FDC error / not 512 B per sec)
fat_mount:
                ld      de, 0           ; boot sector = logical sector 0
                ld      hl, SECTOR_BUF
                call    read_sector
                ret     c
                ; require 512 bytes per sector ($0200 LE) — matches SECTOR_BUF
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC)
                or      a
                jr      nz, fat_mount_bad   ; low byte must be 0
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC + 1)
                cp      2
                jr      nz, fat_mount_bad   ; high byte must be 2 ($0200 = 512)
                ld      a, (SECTOR_BUF + BPB_SECPERCLUS)
                ld      (FAT_SECPERCLUS), a
                ld      hl, (SECTOR_BUF + BPB_RSVDSECCNT)
                ld      (FAT_FATSTART), hl  ; first FAT sector = reserved sectors
                ; first root sector = reserved + numFATs * secPerFAT
                ld      a, (SECTOR_BUF + BPB_NUMFATS)
                ld      (FAT_NUMFATS), a    ; cache for the write path's FAT sync
                ld      b, a
                ld      de, (SECTOR_BUF + BPB_FATSZ16)
                ld      (FAT_SECPERFAT), de ; cache for per-copy sector stride
                ld      hl, 0
fm_fatacc:
                add     hl, de
                djnz    fm_fatacc           ; HL = numFATs * secPerFAT
                ld      de, (FAT_FATSTART)
                add     hl, de
                ld      (FAT_FIRSTROOT), hl
                ; root sectors = (rootEnts*32 + 511) / 512  (512 B per sector)
                ld      hl, (SECTOR_BUF + BPB_ROOTENTCNT)
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
                jp      fat_find_body       ; Tier-2 3b: divert; veneer fills the gap
                ds      $47B2 - $, $00      ; anchor the canonical address
                jp      k_47B2              ; $47B2: COMMAND.COM-load kernel veneer
                ds      $47B9 - $, $00      ; pad remainder (net-zero: ff_secloop stays $47B9)
ff_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jr      z, ff_notfound      ; scanned every root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    read_sector
                ret     c                   ; propagate FDC error
                ld      hl, SECTOR_BUF
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
                call    toupper
                ld      c, a
                ld      a, (hl)
                call    toupper
                cp      c
                ret     nz
                inc     hl                  ; 16-bit inc: leaves flags intact
                inc     de
                djnz    nc_loop             ; djnz leaves flags intact
                ret                         ; Z set from the final cp

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
; boundary (e.g. cluster 682 on a full 720 KB image); the high byte is then read
; from the following FAT sector. A read error here is not separately reported —
; it yields a bogus link that the caller's end-of-chain test treats as EOF.
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
                ld      hl, SECTOR_BUF
                call    read_sector
                ; byte0 = buf[byteidx]
                ld      hl, (FAT_BYTEIDX)
                ld      de, SECTOR_BUF
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
                ld      de, SECTOR_BUF + 1
                add     hl, de
                ld      a, (hl)
                jr      fnc_combine
fnc_straddle:
                ld      hl, (FAT_FATSEC)
                inc     hl
                ex      de, hl
                ld      hl, SECTOR_BUF
                call    read_sector
                ld      a, (SECTOR_BUF)
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

; fat_read_file_sector — read the open file's next data sector into SECTOR_BUF.
;   out: Cy = 0 ok (SECTOR_BUF holds 512 bytes), Cy = 1 end-of-file / error
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
                jp      frs_mul_body        ; Tier-2 3b: divert; veneers fill the gap
                ds      $4919 - $, $00      ; anchor canonical address
                jp      k_4919              ; $4919: COMMAND.COM-load kernel veneer
                ds      $4935 - $, $00      ; anchor canonical address
                jp      k_4935              ; $4935: COMMAND.COM-load kernel veneer
frs_eof:                                    ; kept inline (jr target from frs_incluster)
                scf
                ret
                ds      $4941 - $, $00      ; net-zero: absorbs the relocated write_sector

; ===========================================================================
; FAT12 WRITE-BACK substrate (disk/PROVENANCE.md §FAT12 write-back)
; ===========================================================================
; (write_sector was relocated to the Tier-2 relocated-bodies section: its $4937
; entry collided with the $4935 veneer; it is reached unchanged via its label.)
; The write twins of the read helpers. All structures (free-cluster scan, 12-bit
; entry pack, multi-FAT sync, directory-entry create/update) are realised from
; the Microsoft FAT specification; the physical sector write goes through the
; already-validated dskio write path. Reached by bdos_create / bdos_seqwrite /
; bdos_close. Buffer discipline: the file DATA being accumulated for a Sequential
; Write lives in SECTOR_BUF (fat_flush_data_sector writes it out); the FAT/dir
; METADATA helpers (alloc/link/dir create/update) use the independent WBUF, so a
; cluster scan or dir stamp never disturbs the in-flight data sector.

; fat_read_fat_sector — read FAT-copy-0 sector that holds cluster N's entry.
;   in:  HL = cluster number
;   out: WBUF holds that FAT sector; (FAT_FATSEC) = its absolute sector;
;        (FAT_BYTEIDX) = byte index of the entry's low byte within the sector;
;        (FAT_PARITY) = cluster & 1; Cy reflects the read.
; Uses the write-back buffer WBUF (NOT SECTOR_BUF), so the in-flight data being
; accumulated for a Sequential Write is never disturbed by a FAT scan. Shared
; offset math with fat_next_cluster: fatofs = cluster*3/2; sector = fatStart +
; fatofs/512; byteidx = fatofs & 511. (Microsoft FAT spec §3.2.)
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
                ld      hl, WBUF
                jp      read_sector

; fat_alloc_cluster — find a free ($000) cluster, mark it EOC, sync all FATs.
;   out: Cy = 0 ok, HL = the allocated cluster number; Cy = 1 = disk full / error
; Linear scan from cluster 2 to the last data cluster (total = fat_total_clusters,
; computed ONCE). To keep the scan fast on a populated disk (the first free
; cluster can be hundreds of clusters in), the FAT is read SECTOR-BY-SECTOR into
; WBUF: fat_get_entry is only invoked once a candidate $000 is suspected, so the
; common case reads one FAT sector and tests up to 341 entries from RAM. The first
; $000 entry is claimed: written as EOC ($FFF) into every FAT copy via
; fat_write_fat_entry, so a freshly allocated tail cluster already terminates the
; chain. (Microsoft FAT spec §3.2: $000 = free, $FF8-$FFF = end-of-chain.)
fat_alloc_cluster:
                call    fat_total_clusters  ; DE = total clusters (reads boot sector)
                ld      (FAT_WRTMP), de
                ; FAT_FATSEC tracks which FAT sector is in WBUF; -1 = none loaded.
                ld      hl, $FFFF
                ld      (FAT_WRTMP2), hl    ; cached-sector = none
                ld      hl, 2               ; first data cluster
fac_loop:
                jp      fac_loop_body       ; Tier-2 3b: divert; veneers fill the gap
                ds      $498C - $, $00      ; anchor canonical address
                jp      k_498C              ; $498C: COMMAND.COM-load kernel veneer
                ds      $49B4 - $, $00      ; anchor canonical address
                jp      k_49B4              ; $49B4: COMMAND.COM-load kernel veneer
                ds      $49C3 - $, $00      ; pad to fac_have_sec (net-zero)
fac_have_sec:
                ; read the 12-bit entry from WBUF (handles straddle into next sec).
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
; the FAT sector currently in WBUF; if the entry straddles the 512-byte boundary
; (byteidx == 511) read the FOLLOWING FAT sector for the high byte (and leave it
; cached, since the scan continues into it).
;   out: DE = 12-bit entry value; preserves nothing but DE
fac_entry_from_wbuf:
                ld      hl, (FAT_BYTEIDX)
                ld      de, WBUF
                add     hl, de
                ld      a, (hl)
                ld      (FAT_B0), a
                ld      hl, (FAT_BYTEIDX)
                ld      de, 511
                or      a
                sbc     hl, de
                jr      z, fac_straddle
                ld      hl, (FAT_BYTEIDX)
                ld      de, WBUF + 1
                add     hl, de
                ld      a, (hl)
                jr      fac_comb
fac_straddle:
                ; read the next FAT sector into WBUF and cache it.
                ld      hl, (FAT_FATSEC)
                inc     hl
                ld      (FAT_FATSEC), hl
                ld      (FAT_WRTMP2), hl
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                ld      a, (WBUF)
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
                jp      fac_e_odd_body      ; Tier-2 3b: divert; veneer fills the gap
                ds      $4A39 - $, $00      ; anchor canonical address
                jp      k_4A39              ; $4A39: COMMAND.COM-load kernel veneer
                ds      $4A40 - $, $00      ; pad to fat_write_fat_entry (net-zero)

; fat_write_fat_entry — set a cluster's 12-bit value in EVERY FAT copy on disk.
;   in:  HL = cluster, DE = 12-bit value to store
;   out: Cy = 0 ok, Cy = 1 error
; Reads the FAT-copy-0 sector(s) holding the entry, packs the 12 bits into the
; right nibbles (even cluster: low byte = v[7:0], high nibble of next byte =
; v[11:8]; odd cluster: low nibble of byte = v[3:0], next byte = v[11:4] — the
; exact inverse of fat_next_cluster's unpack), then writes the modified sector
; back to the SAME relative sector in all BPB_NUMFATS copies. If the entry
; straddles a 512-byte boundary the following FAT sector is updated too.
; (Microsoft FAT spec §3.2 packing; multi-FAT sync per BPB_NUMFATS.)
fat_write_fat_entry:
                ld      (FAT_WRTMP), de     ; save the value
                push    hl                  ; save cluster
                call    fat_read_fat_sector ; WBUF = FAT sector 0; BYTEIDX/PARITY set
                ; --- pack the low byte / shared nibble into WBUF[byteidx]
                ld      hl, (FAT_BYTEIDX)
                ld      de, WBUF
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
                ; this sector to all FATs, then load + patch the next sector. The
                ; saved cluster is still on the stack, so pop it before any early
                ; error return (Cy preserved) to keep the stack balanced.
                call    fat_write_buf_allfats
                jr      c, fwe_err
                ld      hl, (FAT_FATSEC)
                inc     hl
                ld      (FAT_FATSEC), hl    ; advance to the straddle sector
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                jr      c, fwe_err
                ld      hl, WBUF            ; patch byte 0 of the next sector
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
                ; compute (value>>4): low nibble from high nibble of E, high nibble
                ; from low nibble of D.
                ld      hl, WBUF
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

; fat_write_buf_allfats — write WBUF back to (FAT_FATSEC) in every FAT copy.
;   in:  WBUF holds the sector; FAT_FATSEC = its sector in FAT copy 0
;   out: Cy = 0 ok, Cy = 1 error
; The same relative offset in each of the BPB_NUMFATS copies differs by exactly
; secPerFAT sectors, so copy k's sector = FAT_FATSEC + k*secPerFAT. The bytes are
; written from WBUF, which must NOT be disturbed between copies — so the per-copy
; target sector is computed without re-reading. (Microsoft FAT spec §3.1: NumFATs
; identical copies; §3.2: same entry packing in each.)
fat_write_buf_allfats:
                ; numFATs and secPerFAT were cached by fat_mount (FAT_NUMFATS /
                ; FAT_SECPERFAT) precisely so this routine needs no boot-sector
                ; re-read — WBUF here holds the FAT sector we must preserve across
                ; all copies.
                ld      a, (FAT_NUMFATS)
                ld      b, a                ; B = copies to write
                ld      hl, (FAT_FATSEC)    ; copy-0 target sector
fwba_loop:
                push    bc
                push    hl
                ex      de, hl              ; DE = target sector
                ld      hl, WBUF
                call    write_sector
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
; dataClusters = (totalSectors - firstData) / secPerClus; we read totalSectors
; from the BPB. Re-reads the boot sector into WBUF (NOT SECTOR_BUF, which may hold
; in-flight write data). (Microsoft FAT spec §3.3.)
fat_total_clusters:
                push    hl
                ld      de, 0
                ld      hl, WBUF
                call    read_sector
                jr      c, ftc_done         ; on error report 2 (no free clusters)
                ld      hl, (WBUF + 19)     ; total sectors 16-bit (BPB +19)
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

; fat_flush_data_sector — write SECTOR_BUF (the current 512-byte data buffer) to
; the file's current data sector, allocating/extending the cluster chain first.
;   out: Cy = 0 ok, Cy = 1 = disk full / write error
; Zero-pads SECTOR_BUF from BDOS_WRBUFLEN..511 (partial final sector), ensures a
; current cluster exists (allocating the first one and recording it in BDOS_WRFIRST,
; or allocating + linking the next when the current cluster is full), then writes
; the absolute data sector = firstData + (cluster-2)*secPerClus + WRSECIDX and
; advances WRSECIDX. (Microsoft FAT spec §3.3 data-sector math.)
fat_flush_data_sector:
                ; zero-pad the unused tail of the buffer (bytes WRBUFLEN..511) so a
                ; partial final sector writes 512 well-defined bytes. pad count =
                ; 512 - WRBUFLEN; dest = SECTOR_BUF + WRBUFLEN.
                ld      hl, 512
                ld      de, (BDOS_WRBUFLEN)
                or      a
                sbc     hl, de              ; HL = 512 - WRBUFLEN (pad count, 0..512)
                jr      z, ffds_nopad       ; buffer already full -> no pad
                jr      c, ffds_nopad       ; (defensive: WRBUFLEN > 512 never happens)
                ld      b, h
                ld      c, l                ; BC = pad count
                ld      hl, SECTOR_BUF
                add     hl, de              ; HL = SECTOR_BUF + WRBUFLEN = first pad byte
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
                jp      ffds_nopad_body     ; Tier-2 3b: divert; veneer fills the gap
                ds      $4B59 - $, $00      ; anchor canonical address
                jp      k_4B59              ; $4B59: COMMAND.COM-load kernel veneer
                ds      $4B62 - $, $00      ; pad to ffds_alloc (net-zero)
ffds_alloc:
                ; allocate a new cluster (first one, or chain extension).
                call    fat_alloc_cluster
                ret     c                   ; disk full
                ; HL = new cluster. Link it: if a previous cluster exists, point it
                ; at HL; else record HL as the file's first cluster.
                ld      de, (BDOS_WRCLUS)
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
                ld      (BDOS_WRFIRST), hl  ; remember the file's first cluster
ffds_setclus:
                ld      (BDOS_WRCLUS), hl
                xor     a
                ld      (BDOS_WRSECIDX), a  ; start at sector 0 of the new cluster
ffds_haveclus:
                ; absolute sector = firstData + (cluster-2)*secPerClus + WRSECIDX
                ld      hl, (BDOS_WRCLUS)
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
                ld      a, (BDOS_WRSECIDX)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl              ; DE = sector
                ld      hl, SECTOR_BUF
                call    write_sector
                ret     c
                ld      a, (BDOS_WRSECIDX)
                inc     a
                ld      (BDOS_WRSECIDX), a
                or      a                   ; Cy = 0 success
                ret

; fat_dir_create — find/make a root-directory slot for an 8.3 name and write a
; fresh entry; record the slot's sector + offset in BDOS_DIRSEC/BDOS_DIROFF.
;   in:  HL = 11-byte 8.3 name field
;   out: Cy = 0 ok, Cy = 1 = directory full / I/O error
; First scans the root directory for an EXISTING entry of the same name (truncate-
; in-place: reuse its slot, which also frees nothing — the old chain is orphaned;
; acceptable for the loader-create subset, see PROVENANCE divergence). Otherwise
; claims the first free slot ($00 end-marker or $E5 deleted). Writes name (+0..10),
; attribute $00 (+11; ORACLE: MSX-DOS Create makes a normal file, archive bit
; clear), zeroes +12..25 incl. the date/time fields (intentional divergence — no
; clock; see disk/PROVENANCE.md), first cluster 0 (+26), size 0 (+28..31), then
; writes the dir sector back. (Microsoft FAT spec §3.4.)
fat_dir_create:
                ld      (FAT_NAMEPTR), hl
                ld      hl, (FAT_FIRSTROOT)
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_ROOTSECS)
                ld      (FAT_DIRREM), hl
fdc_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jr      z, fdc_full         ; no slot in any root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, WBUF
                call    read_sector
                ret     c
                ld      hl, WBUF
                ld      b, 16               ; 16 entries per 512-byte sector
fdc_entloop:
                jp      fdc_entloop_body    ; Tier-2 3b: divert; veneer fills the gap
                ds      $4BE5 - $, $00      ; anchor canonical address
                jp      k_4BE5              ; $4BE5: COMMAND.COM-load kernel veneer
                ds      $4C05 - $, $00      ; pad to fdc_useslot (net-zero)
fdc_useslot:
                jp      fdc_useslot_body    ; Tier-2 3b: divert; veneer fills the gap
                ds      $4C25 - $, $00      ; anchor canonical address
                jp      k_4C25              ; $4C25: COMMAND.COM-load kernel veneer
                ds      $4C29 - $, $00      ; pad to fdc_zero (net-zero)
fdc_zero:
                xor     a
                ld      (de), a
                inc     de
                djnz    fdc_zero
                pop     hl                  ; discard slot pointer
                ; write the dir sector back.
                ld      de, (BDOS_DIRSEC)
                ld      hl, WBUF
                call    write_sector
                ret     c
                or      a                   ; Cy = 0 success
                ret
fdc_full:
                scf
                ret

; fat_dir_update — rewrite the open-for-write file's directory entry at Close
; with its true byte count (DIRENT_FILESIZE) and first cluster (DIRENT_FIRSTCLUS).
;   out: Cy = 0 ok, Cy = 1 = I/O error
; Re-reads the dir entry's sector (BDOS_DIRSEC), patches the entry at BDOS_DIROFF:
; first cluster word (+26) from BDOS_WRFIRST, size dword (+28) from BDOS_WRBYTES,
; then writes the sector back. The name + attribute were set at Create and are
; left intact. (Microsoft FAT spec §3.4.)
fat_dir_update:
                ld      de, (BDOS_DIRSEC)
                ld      hl, WBUF
                call    read_sector
                ret     c
                ; HL = &entry = WBUF + DIROFF
                ld      hl, (BDOS_DIROFF)
                ld      de, WBUF
                add     hl, de
                ; +26 first cluster (LE) = BDOS_WRFIRST
                push    hl
                ld      de, DIRENT_FIRSTCLUS
                add     hl, de
                ld      de, (BDOS_WRFIRST)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                pop     hl
                ; +28 file size (4-byte LE) = BDOS_WRBYTES
                ld      de, DIRENT_FILESIZE
                add     hl, de
                ex      de, hl              ; DE = &entry+28
                ld      hl, BDOS_WRBYTES
                ld      bc, 4
                ldir
                ; write the dir sector back.
                ld      de, (BDOS_DIRSEC)
                ld      hl, WBUF
                call    write_sector
                ret     c
                or      a                   ; Cy = 0 success
                ret

