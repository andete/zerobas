; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fatio-body.inc — the sequential FAT12 READ layer (fat_io_open + fat_io_getbyte).
; ===========================================================================
; Shared, byte-identically, between the RESIDENT main ROM (basic/fat.asm, where
; fat_mount/fat_find/fat_open/fat_read_file_sector are marshalling STUBS over the
; fatprim sub-ROM tenant) and the sub-ROM PAGE-1 BLOAD tenant (sub/bload.asm,
; docs/spec-traps-t3-key.md §7.6), where those same four names bind to the REAL
; implementations sitting right there in sub/fatprim.asm.
;
; That is the whole trick, and it is why the carve is affordable: this layer is
; pure RAM bookkeeping over four calls, so the identical source text becomes a
; cross-slot round trip on one side and four plain in-page calls on the other.
; The resident copy must stay — do_load, ex_merge and the file verbs all use it.
;
; CLEAN-ROOM: extracted verbatim from our own basic/fat.asm. FAT12 provenance is
; unchanged (basic/PROVENANCE.md §disk DSKIO host engine).
; ===========================================================================

; fat_io_open — open the file named in DISK_FCB_NAME for sequential READ.
;   out: Cy = 0 opened (stream ready); Cy = 1 not found / mount / I/O error.
; Mounts the volume, finds the 8.3 name, primes the read iterator, seeds the
; bytes-remaining counter from the true file size, and marks the sector buffer
; empty so the first fat_io_getbyte refills it.
fat_io_open:
                call    fat_mount
                ret     c
; fat_io_find — the same open MINUS the mount, for a caller that has already
; mounted and wants the find's carry BY ITSELF. A ZERO-BYTE label: it splits no
; code, it only names the boundary `fat_io_open` already had. Cy out of here
; means precisely "the volume mounted and the 8.3 name is NOT in the directory"
; — the tail below cannot set it (it ends `or a`). D-BLNF: that is how the BLOAD
; tenant tells NOT FOUND from a mount/I-O fault without a DISKOP_OP it never
; writes (sub/bload.asm, basic/bload-body.inc); df_or_loaderr reads the same
; distinction off DISKOP_OP on the resident side, where fat_find is a
; marshalling stub (basic/files.asm).
fat_io_find:
                ld      hl, DISK_FCB_NAME
                call    fat_find
                ret     c
                call    fat_open
                ; seed FREAD_LEFT = FAT_FILESIZE (4-byte LE).
                ld      hl, FAT_FILESIZE
                ld      de, FREAD_LEFT
                ld      bc, 4
                ldir
                ; mark the in-RAM sector buffer exhausted (OFF==512 -> first
                ; getbyte triggers fat_read_file_sector).
                ld      hl, 512
                ld      (FREAD_OFF), hl
                or      a                   ; Cy = 0 success
                ret

; fat_io_getbyte — return the next file byte in A; Cy set on EOF (no more data).
; State: FREAD_OFF = next byte index within FSECTOR_BUF (0..512); FREAD_LEFT =
; bytes of the file still undelivered (bounds the true EOF). Refills FSECTOR_BUF
; from the cluster chain when the in-RAM sector is exhausted. CALSLT (inside
; fat_read_file_sector's DSKIO) clobbers every register, so all loop state lives
; in RAM and is reloaded here each call.
fat_io_getbyte:
                ; EOF once every file byte has been delivered (FREAD_LEFT == 0).
                ld      hl, (FREAD_LEFT)
                ld      de, (FREAD_LEFT + 2)
                ld      a, h
                or      l
                or      d
                or      e
                jr      z, fig_eof
                ; refill the sector buffer if exhausted (OFF >= 512).
                ld      hl, (FREAD_OFF)
                ld      de, 512
                or      a
                sbc     hl, de
                jr      c, fig_have         ; OFF < 512 -> bytes left in FSECTOR_BUF
                call    fat_read_file_sector
                jr      c, fig_eof          ; chain ended early -> EOF (size bounded)
                ld      hl, 0
                ld      (FREAD_OFF), hl     ; back to byte 0 of the fresh sector
fig_have:
                ; A = FSECTOR_BUF[OFF]; advance OFF and decrement LEFT.
                ld      hl, (FREAD_OFF)
                ld      de, FSECTOR_BUF
                add     hl, de
                ld      a, (hl)
                ld      b, a                ; B = the byte (survives the bookkeeping)
                ld      hl, (FREAD_OFF)
                inc     hl
                ld      (FREAD_OFF), hl
                ; FREAD_LEFT -= 1 (4-byte LE decrement).
                ld      hl, FREAD_LEFT
                ld      a, (hl)
                sub     1
                ld      (hl), a
                inc     hl
                ld      a, (hl)
                sbc     a, 0
                ld      (hl), a
                inc     hl
                ld      a, (hl)
                sbc     a, 0
                ld      (hl), a
                inc     hl
                ld      a, (hl)
                sbc     a, 0
                ld      (hl), a
                ld      a, b                ; A = the byte
                or      a                   ; Cy = 0 (A may be anything; OR clears Cy)
                ret
fig_eof:
                scf
                ret
