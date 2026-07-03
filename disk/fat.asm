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
                ds      $46BA - $, $00      ; pure $00 pad (M26, tier2-m26-spec.md
                                            ; §2.4: trace --resync confirmed $46BA is
                                            ; the kernel's real fixed $2F RDABS dispatch
                                            ; address, landing in dead pad -- NOT 61
                                            ; bytes into bdos_create's body as first
                                            ; guessed; no relocation needed)
k_46BA:         jp      rdabs_body          ; $46BA: BDOS $2F RDABS canonical entry (M26)
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
                jp      bdos_seqwrite_body  ; M26 WRABS (tier2-m26-spec.md): relocated --
                                            ; the old span here collided mid-instruction
                                            ; with the real $30 WRABS dispatch address,
                                            ; $4720 (trace --resync confirmed: it's the
                                            ; displacement byte of the `jr c, bsw_full`
                                            ; that used to live at this offset). Real
                                            ; body now bdos_seqwrite_body (disk/kernel.asm
                                            ; free tail); only symbolic callers
                                            ; (driver.asm/kernel.asm `jp bdos_seqwrite`)
                                            ; keep working unchanged.
                ds      $4720 - $, $00      ; pad up to the pinned canonical entry
k_4720:         jp      wrabs_body          ; $4720: BDOS $30 WRABS canonical entry (M26)

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
                jp      fat_mount_tail      ; Tier-2 3b: divert; veneer fills the gap (M24 slice B)
; --- MSX-DOS-1 kernel WRSEQ-worker entry: $477D (M24 slice B;
; tier2-m24-fclose-multicluster-spec.md) --------------------------------------
; The RAM kernel's BDOS $15 WRSEQ handling CALLs this page-1 entry once per
; 128-byte record (pinned black-box, ret=$D88A dispatcher class, DE=IY=$DA40
; kernel FCB pointer). Pre-M24 this fell on the high byte of fat_mount's own
; `ld hl,0` (the numFATs*secPerFAT multiply preamble), NOP'd through, then
; spun the multiply loop 256x on garbage B and clobbered our FAT geometry
; cells from stale SECTOR_BUF bytes -- silently discarding every WRSEQ
; record's data while reporting success. fat_mount's own multiply+remainder
; (fm_fatacc onward, unchanged) is relocated below to make room -- position-
; free, reached only by label from fat_mount's own `jp fat_mount_tail`
; fall-through above.
                ds      $477D - $, $00      ; pad up to the pinned $477D WRSEQ-worker entry
k_477D:
                jp      wrseq_body          ; $477D: BDOS $15 WRSEQ canonical entry (M24 slice B)
fat_mount_bad:
                scf
                ret

; fat_find — search the root directory for an 8.3 file name.
;   in:  HL = pointer to an 11-byte name field (8 name + 3 ext, space-padded)
;   out: Cy = 0 found  -> FAT_FIRSTCLUS, FAT_FILESIZE set; Cy = 1 not found / error
; Compare is case-insensitive; FAT directories store upper-case 8.3 names.
fat_find:
                jp      fat_find_body       ; Tier-2 3b: divert; veneer fills the gap
                ds      $4788 - $, $00      ; pad remainder (M26, tier2-m26-spec.md §2.3:
                                            ; trace --resync confirmed $4788 is the
                                            ; kernel's real fixed $21 RDRND dispatch
                                            ; address, dead pad -- the original
                                            ; "$21/$22 share one dispatch" callwatch
                                            ; read was a dedup artifact; no relocation
                                            ; needed, RDABS-shape)
k_4788:         jp      rdrnd_body          ; $4788: BDOS $21 RDRND canonical entry (M26)
                ds      $4793 - $, $00      ; pad remainder (M26, tier2-m26-spec.md §2.3:
                                            ; $4793 is $22 WRRND's own separate dispatch,
                                            ; same pad corridor, RDABS-shape)
k_4793:         jp      wrrnd_body          ; $4793: BDOS $22 WRRND canonical entry (M26)
                ds      $47B2 - $, $00      ; pad remainder (net-zero: k_47B2 unaffected)
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

; --- Relocated from disk/driver.asm (M21a, tier2-m21-spec.md §5.3) ---------
; $4462 — a byte inside fdc_di_save's body — collided with the kernel's FOPEN
; dir-fill entry point (RC-1). This block is UNCHANGED from its original
; driver.asm form; every caller (dskio's transfer sites, fdc_di_save's own
; internal chain, the canonical $4013/$4016 dskchg/getdpb entries in
; init.asm) resolves by symbol, so relocation needs no repoint anywhere else.

; fdc_di_save / fdc_io_done — bracket a sector op with a DI..(EI) guard.
; The WD2793 data transfer is a tight DRQ poll: a foreign interrupt (the 50 Hz
; VDP IRQ, live once MSX-DOS / COMMAND.COM run with EI) preempting the loop drops
; an FDC byte -> LOST DATA, an endless restore-retry livelock (a3 §8.34). MSX-DOS
; boot ran with interrupts masked, so this only bit in the DOS context. fdc_di_save
; records the caller's IFF2 then masks; fdc_io_done restores it on every exit,
; leaving the result (A = error code, Cy, HL) untouched. (`ld a,i` puts IFF2 in
; P/V; the entry clobbers A, but fdc_read_phys/fdc_write_phys take no A input.)
fdc_di_save:
                ld      a, i            ; P/V = IFF2 (interrupts enabled?)
                di
                jp      pe, fdc_di_on   ; PE -> IFF2 was set
                xor     a               ; were masked: remember 0
                ld      (FDC_IFF), a
                ret
fdc_di_on:
                ld      a, 1            ; were enabled: remember 1
                ld      (FDC_IFF), a
                ret

fdc_io_done:
                push    af              ; preserve result (A error code + Cy)
                ld      a, (FDC_IFF)
                or      a
                jr      z, fdc_iod_x    ; caller had interrupts masked: leave masked
                ei                      ; restore the caller's enabled interrupts
fdc_iod_x:
                pop     af
                ret

; div9 — divide HL by 9 (logical sector -> track*2+head, sector-1).
;   in:  HL = logical sector (0..1439)
;   out: B = quotient (HL / 9), L = remainder (0..8), H = 0; A trashed
div9:
                ld      b, 0
fdc_div_loop:
                ld      a, h
                or      a
                jr      nz, fdc_div_sub ; HL >= 256 -> definitely >= 9
                ld      a, l
                cp      9
                jr      c, fdc_div_done ; HL < 9 -> remainder in L
fdc_div_sub:
                ld      a, l
                sub     9
                ld      l, a
                jr      nc, fdc_div_nob
                dec     h
fdc_div_nob:
                inc     b
                jr      fdc_div_loop
fdc_div_done:
                ret

; dskchg — disk-change status inquiry.
; Fail with carry set until FDC driver lands.
dskchg:
                scf
                ret

; getdpb — build the Drive Parameter Block from the BPB ($4016 disk-ROM entry).
;
; Builds a real DPB from the on-disk BPB. This is the PROVIDER-direction surface
; (disk/docs/expansion-protocol.md §4a): a real MSX-BASIC / MSX-DOS host calls
; $4016 to obtain the mounted volume's geometry as a DPB, so the provider must
; answer it (a black-box trace of BLOAD/SAVE on the CF-3300 showed Disk BASIC
; DOES call GETDPB). zerobas's own loader path never calls $4016 — it derives
; geometry straight from the BPB (fat_mount) — but a foreign host driving us does.
;
; Calling convention (MSX disk-ROM interface; Nextor 2.1 Driver Development Guide
; §4.5.3, which restates the standard GETDPB contract):
;   in:  A  = drive (unit) number (0 = A:)  — ignored, single-drive machine
;        B  = C = media descriptor byte
;        HL = DPB base address MINUS ONE (the byte at base+0 is the drive number,
;             which GETDPB does NOT fill; GETDPB fills base+1 = media onward)
;   out: Cy = 0 ok (DPB filled), Cy = 1 = error (could not read the boot sector)
;
; DPB field layout + encodings: MSX2 Technical Handbook §3, Figure 3.11 (DPB
; structure), and the Nextor 2.1 Driver Development Guide §4.5.3 field formulas.
; Each field below cites its source + derivation. The whole layout was confirmed
; FIELD-FOR-FIELD against a black-box GETDPB trace of the National CF-3300
; reference on this same 720 KB image (carry=0, DPB bytes read out of RAM — the
; reference ROM's code was never read). See disk/PROVENANCE.md §DPB.
;
; fat_mount already parses the BPB into scratch (FAT_FATSTART / FAT_FIRSTROOT /
; FAT_FIRSTDATA / FAT_SECPERCLUS / FAT_NUMFATS / FAT_SECPERFAT) and leaves the
; boot sector in SECTOR_BUF, so GETDPB reuses those (our own code) and reads the
; remaining raw BPB fields (media, sector size, root-entry count) from SECTOR_BUF.
getdpb:
                ; HL = DPB base - 1 (Nextor §4.5.3). GETDPB fills from base+1 (media)
                ; onward; base+0 (drive number) is the caller's, not ours. So the
                ; first byte WE write (media) lands at HL+1. (CONFIRMED by the
                ; CF-3300 black-box trace: with HL = $C0FF the reference wrote the
                ; media byte at $C100 = HL+1; see disk/PROVENANCE.md §DPB.)
                inc     hl                  ; HL -> DPB +1 (media ID), = caller HL + 1
                push    hl                  ; keep DPB+1 pointer across fat_mount
                call    fat_mount           ; parse BPB; leaves boot sector in SECTOR_BUF
                pop     hl
                ret     c                   ; boot-sector read failed -> Cy = 1

                ; +1 media ID = BPB media descriptor (boot sector +21). TH Fig 3.11
                ; "media ID"; ECMA-107 / MS FAT spec media byte. (= $F9 on 720 KB.)
                ld      a, (SECTOR_BUF + 21)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +2

                ; +2..3 sector size (LE) = BPB bytes-per-sector. TH Fig 3.11; we
                ; validated $0200 (512) at mount, so copy the BPB word verbatim.
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC)
                ld      (hl), a
                inc     hl
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC + 1)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +4

                ; +4 directory mask = (sector size / 32) - 1  (Nextor §4.5.3:
                ; "directory mask = (sector size/32) - 1"). 512/32 - 1 = 15 = $0F.
                ; +5 directory shift = number of one-bits in the directory mask
                ;    (Nextor §4.5.3) = log2(entries per sector) = 4 for 512-byte
                ;    sectors. Sector size is validated = 512 at mount, so these are
                ;    the fixed 512-byte values $0F / $04 (CF-3300 oracle: 0f 04).
                ld      (hl), $0F           ; +4 directory mask
                inc     hl
                ld      (hl), 4             ; +5 directory shift
                inc     hl                  ; HL -> DPB +6

                ; +6 cluster mask = (sectors per cluster) - 1   (Nextor §4.5.3).
                ; +7 cluster shift = (one-bits in cluster mask) + 1 (Nextor §4.5.3);
                ;    for a power-of-two secPerClus this equals log2(secPerClus)+1.
                ;    720 KB: secPerClus = 2 -> mask = 1, shift = 2 (CF-3300: 01 02).
                ld      a, (FAT_SECPERCLUS) ; our own BPB-derived value (fat_mount)
                dec     a
                ld      (hl), a             ; +6 cluster mask = secPerClus - 1
                ld      c, a                ; C = cluster mask (count its one-bits)
                inc     hl                  ; HL -> DPB +7
                ld      b, 1                ; shift starts at 1 (Nextor: +1)
                ld      a, c
                or      a
                jr      z, gdpb_popdone
gdpb_pc_loop:
                srl     c
                jr      nc, gdpb_pc_next
                inc     b                   ; one more set bit -> +1 to the shift
gdpb_pc_next:
                ld      a, c
                or      a
                jr      nz, gdpb_pc_loop
gdpb_popdone:
                ld      (hl), b             ; +7 cluster shift
                inc     hl                  ; HL -> DPB +8

                ; +8..9 top sector of FAT (LE) = first FAT sector = reserved sectors.
                ; TH Fig 3.11 "top sector of FAT"; our FAT_FATSTART (fat_mount).
                ld      de, (FAT_FATSTART)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl                  ; HL -> DPB +10

                ; +10 number of FATs. TH Fig 3.11; our FAT_NUMFATS (BPB +16).
                ld      a, (FAT_NUMFATS)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +11

                ; +11 number of directory entries (max 254). TH Fig 3.11; BPB +17
                ; root-entry count low byte (112 on 720 KB -> $70; high byte is 0).
                ld      a, (SECTOR_BUF + BPB_ROOTENTCNT)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +12

                ; +12..13 top sector of data area (LE) = first data sector.
                ; TH Fig 3.11 "top sector of data area"; our FAT_FIRSTDATA.
                ld      de, (FAT_FIRSTDATA)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl                  ; HL -> DPB +14

                ; +14..15 amount of cluster + 1 (LE). TH Fig 3.11 "amount of cluster
                ; + 1"; = data-cluster count + 1. fat_total_clusters returns
                ; dataClusters + 2 (its highest-cluster-plus-one chain bound), so
                ; the DPB field is that value - 1. (CF-3300 oracle: $02CA = 714 =
                ; dataClusters(713) + 1 on this 720 KB image; fat_total_clusters
                ; returns 715, minus 1 = 714.) Microsoft FAT spec §3.3 cluster count.
                push    hl
                call    fat_total_clusters  ; DE = dataClusters + 2 (reads boot sec into WBUF)
                dec     de                  ; DE = dataClusters + 1 (the DPB encoding)
                pop     hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl                  ; HL -> DPB +16

                ; +16 number of sectors per FAT. TH Fig 3.11; our FAT_SECPERFAT
                ; (BPB +22). 720 KB = 3. Single byte (FAT fits < 256 sectors).
                ld      a, (FAT_SECPERFAT)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +17

                ; +17..18 top sector of directory area (LE) = first root-dir sector.
                ; TH Fig 3.11 "top sector of directory area"; our FAT_FIRSTROOT.
                ld      de, (FAT_FIRSTROOT)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ; +19..20 (FAT address in memory) is filled by the OS, not GETDPB
                ; (TH Fig 3.11) — left untouched, matching the CF-3300 oracle which
                ; left those two bytes unwritten.
                or      a                   ; Cy = 0 success
                ret

; fopen_fill_body — M21a: the real page-1 FOPEN dir-fill (tier2-m21-spec.md
; §5.2/§0.1). Reached as a page-1 TAIL-CALL from the kernel's FOPEN handler via
; the $4462 veneer (disk/driver.asm) — the return address already on the stack
; is the kernel's own BDOS-exit trampoline (§0.1 Fact 4), so this body's exit
; A/F ARE the BDOS FOPEN result, not an internal call's return value. The
; kernel has already filled FCB +0..+13 (search name/ext/extent/S1) via its own
; SFIRST/SNEXT-sourced LDIR before calling here (§5.2's division-of-labor
; finding) — this body owns ONLY +14(high)..+31.
;   in:  DE = FCB pointer (kernel work buffer, e.g. $DA40 runtime / $DC5B boot)
;   out: found:     A = $00, HL = $0000 (§6/§0.1 pinned contract at $C4A1)
;        not found: A = $FF                (§0.1 Fact 5, matches stock's $D88A)
;        $F306 cleared either way (Tier-2 dispatcher-flag rule, M20)
fopen_fill_body:
                push    de
                pop     ix                  ; IX = FCB pointer throughout
                xor     a
                ld      (ix+14), a          ; +14 unconditional pre-search clear (§0.1 facts 2/3)
                push    ix
                pop     de
                call    fat_mount
                jp      c, ffb_miss
                push    ix
                pop     de
                inc     de                  ; DE -> FCB+1 (11-byte 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found; HL preserved = &matched dirent
                jp      c, ffb_miss
                ; date/time (§0.1 addendum, confirmed against the FAT12 dir-entry
                ; layout on our own test disk): FCB+20/21 := dirent+24/25 (date),
                ; FCB+22/23 := dirent+22/23 (time) — a word-swap vs. the dirent's
                ; own time-then-date order, not a straight 4-byte copy.
                ld      de, 22
                add     hl, de              ; HL -> dirent+22 (time word)
                ld      a, (hl)
                ld      (ix+22), a
                inc     hl
                ld      a, (hl)
                ld      (ix+23), a
                inc     hl                  ; HL -> dirent+24 (date word)
                ld      a, (hl)
                ld      (ix+20), a
                inc     hl
                ld      a, (hl)
                ld      (ix+21), a
                ; +15 record count = ceil(size/128), capped at 128 ($80)
                ld      hl, (FAT_FILESIZE)
                ld      a, l
                and     $7F
                ld      b, a
                ld      a, 7
ffb_shift:
                srl     h
                rr      l
                dec     a
                jr      nz, ffb_shift
                ld      a, b
                or      a
                jr      z, ffb_noround
                inc     l
ffb_noround:
                ld      a, l
                cp      $81
                jr      c, ffb_rcok
                ld      a, $80
ffb_rcok:
                ld      (ix+15), a
                ; +16..19 size mirror (4-byte LE)
                push    ix
                pop     hl
                ld      bc, 16
                add     hl, bc
                ex      de, hl
                ld      hl, FAT_FILESIZE
                ld      bc, 4
                ldir
                ; +24 devid: oracle-observed constant (§3 RC-1). +25 dirloc is
                ; left at the kernel's pre-zero — a per-file directory-slot index
                ; we don't compute; confirmed cosmetic-only (the prior M21a run
                ; loaded and executed BDOSX.COM correctly with this field
                ; mismatched — see tier2-review-queue.md).
                ld      (ix+24), $40
                ; +26/27 top cluster, +28/29 last cluster (fresh open: both = first)
                ld      hl, (FAT_FIRSTCLUS)
                ld      (ix+26), l
                ld      (ix+27), h
                ld      (ix+28), l
                ld      (ix+29), h
                ; +30/31 relloc = 0
                ld      (ix+30), 0
                ld      (ix+31), 0
                ; Prime the READ-side iterator (M25, tier2-m24-fclose-
                ; multicluster-spec.md "UPDATE 2"): this body previously only
                ; populated FCB display fields, never the internal read state
                ; $14 RDSEQ depends on -- FAT_CURCLUS/FAT_CLUSSEC (fat_open),
                ; BDOS_RECIDX, BDOS_BYTESLEFT. Those were only ever seeded by
                ; our OWN bdos_open/bdos_rdblk, neither of which runs for a
                ; real kernel-driven $0F FOPEN -- so a subsequent $477D-routed
                ; RDSEQ (see wrseq_body below) found BDOS_BYTESLEFT still $0
                ; and returned a false EOF. Exact mirror of bdos_open's own
                ; read-state seeding (disk/driver.asm); reuses the
                ; FAT_FIRSTCLUS/FAT_FILESIZE this body already read above --
                ; no extra mount/find work.
                call    fat_open
                ld      a, RECPERSEC
                ld      (BDOS_RECIDX), a
                ld      hl, FAT_FILESIZE
                ld      de, BDOS_BYTESLEFT
                ld      bc, 4
                ldir
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      hl, 0
                ret
ffb_miss:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, $FF
                ret

; fren_body — MSX-DOS-1 kernel FREN ($17) canonical entry $4392's real body
; (M26, tier2-m26-spec.md). CLEAN-ROOM: reuses fat_mount/fat_find exactly as
; fopen_fill_body does above (M21a) -- searches the root directory for the
; FCB's OLD 8.3 name (+1..11, CP/M rename convention), then overwrites the
; matched directory entry's name field in place with the NEW 8.3 name
; (+17..27, the "second half" of the rename FCB) and persists it via
; write_sector. fat_find leaves the matched entry inside SECTOR_BUF with
; FAT_DIRSEC holding that entry's own sector number -- exactly the state
; needed to write it back in place; no separate directory-entry-address
; bookkeeping is needed beyond what fat_find already provides.
fren_body:
                push    de
                pop     ix                  ; IX = FCB pointer
                push    ix
                pop     de
                call    fat_mount
                jp      c, fren_miss
                push    ix
                pop     de
                inc     de                  ; DE -> FCB+1 (old 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found; HL = &matched dirent (in SECTOR_BUF)
                jp      c, fren_miss
                ex      de, hl              ; DE = &matched dirent (write destination)
                push    ix
                pop     hl
                ld      bc, 17
                add     hl, bc              ; HL = FCB+17 (new 8.3 name, source)
                ld      bc, 11
                ldir                        ; overwrite the dirent's name in place
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    write_sector
                jp      c, fren_ioerr
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ret
fren_miss:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, $FF
                ret
fren_ioerr:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, 2                ; generic FDC I/O error (fdc_read_data convention)
                ret

; rdabs_body — MSX-DOS-1 kernel RDABS ($2F) canonical entry $46BA's real body
; (M26, tier2-m26-spec.md §2.4). CLEAN-ROOM, from the published contract
; (map.grauw.nl BDOS function reference, disk/docs/tier2-bdos-remaining-spec.md
; §2 table): in DE = start logical sector, H = sector count, L = drive
; (ignored -- single-drive ROM, same convention as read_sector/write_sector
; above). Target buffer = the runtime DTA (DOS_DTAPTR, $F23D -- M19/M21
; precedent, NOT our own internal BDOS_DTA cell). Calls dskio directly
; (disk/driver.asm) rather than read_sector, since RDABS must honour an
; arbitrary sector count, not just one.
; Exit contract empirically pinned via `capture` (BDOSX3 record 22, H=1):
; stock's own A=$00 B=$00 C=$01 D=$00 E=$00 H=$00 L=$00 on success -- C
; carries the original sector count (not officially documented; matched here
; since BDOSX3's zero-diff bar covers full register state, same discipline
; as M22a's VERIFY/CPMVER register-parity work). dskio clobbers B/C
; internally for its own CHS bookkeeping, so the original count is saved
; across the call on the stack, not left in a register.
rdabs_body:
                ld      b, h                ; B := sector count (dskio's own count param)
                push    bc                  ; preserve original count across the dskio call
                ld      hl, (DOS_DTAPTR)    ; target = runtime DTA
                xor     a                   ; drive ignored (single-drive); Cy=0 = read
                call    dskio
                pop     bc                  ; B := original count again (dskio clobbers B/C)
                jp      c, rdabs_ioerr
                ld      a, b                ; A := original count
                ld      c, a                ; C := count (pinned exit value)
                xor     a
                ld      b, a                ; B := $00 (pinned exit value)
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      h, a
                ld      l, a                ; H=L=$00 (pinned exit value)
                ret
rdabs_ioerr:
                ld      b, a                ; preserve dskio's error code
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      a, b                ; restore error code
                scf
                ret

; wrabs_body — MSX-DOS-1 kernel WRABS ($30) canonical entry $4720's real body
; (M26, tier2-m26-spec.md §2.5/§7). CLEAN-ROOM, mirror of rdabs_body above:
; in DE = start logical sector, H = sector count, L = drive (ignored --
; single-drive ROM). Source buffer = the runtime DTA (DOS_DTAPTR, $F23D).
; Calls dskio directly with Cy=1 (write direction) rather than a fixed-count
; wrapper, for the same arbitrary-count reason as RDABS. Entry/exit register
; contract pinned by black-box `capture` (BDOSX3 record 23, H=1): identical
; shape to RDABS's own pinned contract -- A=$00 B=$00 C=$01 D=$00 E=$00
; H=$00 L=$00 on success, C carrying the original sector count.
wrabs_body:
                ld      b, h                ; B := sector count (dskio's own count param)
                push    bc                  ; preserve original count across the dskio call
                ld      hl, (DOS_DTAPTR)    ; source = runtime DTA
                xor     a                   ; drive 0 (ignored, single-drive)
                scf                         ; Cy=1 = write direction (MSX2 TH DSKIO)
                call    dskio
                pop     bc                  ; B := original count again (dskio clobbers B/C)
                jp      c, wrabs_ioerr
                ld      a, b                ; A := original count
                ld      c, a                ; C := count (pinned exit value)
                xor     a
                ld      b, a                ; B := $00 (pinned exit value)
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      h, a
                ld      l, a                ; H=L=$00 (pinned exit value)
                ret
wrabs_ioerr:
                ld      b, a                ; preserve dskio's error code
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      a, b                ; restore error code
                scf
                ret
