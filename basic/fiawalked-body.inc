; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fiawalked-body.inc -- fat_io_append's "chain already walked" tail: work out
; where an append RESUMES (last cluster, partial-vs-full last sector, the Ctrl-Z
; overwrite rule) and prime the write iterator. ONE body, TWO homes, the pattern
; the FAT12 eviction established:
;
;   * included by the PAGE-1 fatprim tenant (sub/fiawalk.asm, table
;     row DISKOP_SEL_FIA_WALKED), with a resident shim under the same name.
;
; Carve 2 of the three that fund graphics G7 (docs/spec-eviction-g7-space.md). It
; qualifies because it is pure RAM arithmetic over the FAT_*/FWR_* cells and
; FSECTOR_BUF -- it calls nothing at all, and every path returns Cy = 0, so the
; shim needs no status marshalling.
;
; Clean-room: our own code, relocated verbatim. No disassembly.

fia_walked:
                ld      hl,(FAT_CURCLUS)
                ld      (FWR_CLUS),hl       ; resume in the file's last cluster
                ; rem = size & 0x1FF (bytes in the last sector; 0 = it is full).
                ld      hl,(FAT_FILESIZE)
                ld      a,h
                and     1
                ld      h,a                 ; HL = rem (0..511)
                ld      (FAT_WRTMP2),hl
                ld      a,h
                or      l
                jr      z,fia_full          ; rem == 0 -> last sector is full
                ; partial last sector: rewrite it. SECIDX = CLUSSEC-1; the partial
                ; sector content is already in FSECTOR_BUF. Check its last byte.
                ld      a,(FAT_CLUSSEC)
                dec     a
                ld      (FWR_SECIDX),a
                ld      hl,FAT_DBUF
                ld      de,(FAT_WRTMP2)
                dec     de                  ; offset rem-1 = last data byte
                add     hl,de
                ld      a,(hl)
                cp      $1A
                jr      z,fia_part_ctrlz
                ld      hl,(FAT_WRTMP2)     ; no Ctrl-Z: BUFLEN = rem, bytes = size
                ld      (FWR_BUFLEN),hl
                jp      fia_bytes_size
fia_part_ctrlz:
                ld      hl,(FAT_WRTMP2)     ; Ctrl-Z: overwrite it. BUFLEN = rem-1,
                dec     hl                  ; bytes = size-1
                ld      (FWR_BUFLEN),hl
                jp      fia_bytes_m1
fia_full:
                ; last sector full: check its final byte ([511]) for the Ctrl-Z.
                ld      a,(FAT_DBUF+511)
                cp      $1A
                jr      z,fia_full_ctrlz
                ; no Ctrl-Z: resume on a FRESH next sector (SECIDX = CLUSSEC; if that
                ; equals SECPERCLUS the next flush allocates a new cluster). bytes=size.
                ld      a,(FAT_CLUSSEC)
                ld      (FWR_SECIDX),a
                ld      hl,0
                ld      (FWR_BUFLEN),hl
                jp      fia_bytes_size
fia_full_ctrlz:
                ; overwrite the Ctrl-Z at offset 511 by rewriting the full last
                ; sector: SECIDX = CLUSSEC-1, BUFLEN = 511, bytes = size-1.
                ld      a,(FAT_CLUSSEC)
                dec     a
                ld      (FWR_SECIDX),a
                ld      hl,511
                ld      (FWR_BUFLEN),hl
                jp      fia_bytes_m1
fia_bytes_size:
                ld      hl,FAT_FILESIZE     ; FWR_BYTES = size (4-byte LE)
                ld      de,FWR_BYTES
                ld      bc,4
                ldir
                or      a                   ; Cy = 0 success
                ret
fia_bytes_m1:
                ld      hl,FAT_FILESIZE     ; FWR_BYTES = size, then -1
                ld      de,FWR_BYTES
                ld      bc,4
                ldir
                ld      hl,FWR_BYTES
                ld      a,(hl)
                sub     1
                ld      (hl),a
                inc     hl
                ld      a,(hl)
                sbc     a,0
                ld      (hl),a
                inc     hl
                ld      a,(hl)
                sbc     a,0
                ld      (hl),a
                inc     hl
                ld      a,(hl)
                sbc     a,0
                ld      (hl),a
                or      a                   ; Cy = 0 success
                ret
