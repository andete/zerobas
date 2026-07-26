; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fatiow-body.inc -- fat_io_putbyte + fwr_bytes_inc + fat_io_close.
; ===========================================================================
; Extracted VERBATIM from basic/fat.asm so the sub-ROM SAVE tenant
; (sub/save.asm, SUBROM_IDX_SAVE) gets a byte-identical SUB-LOCAL copy instead
; of a second hand-maintained one. This is the WRITE mirror of fatio-body.inc,
; which does the same for the read cursor and sub/bload.asm.
;
; The resident copy STAYS -- do_save's ASCII path, the file verbs and pch_disk
; all use it. A duplicate in the sub-ROM costs no main page-1 bytes. On the
; resident side fat_mount / fat_dir_create / fat_flush_data_sector /
; fat_dir_update are marshalling STUBS over the fatprim tenant; inside the
; tenant the same source text binds to the REAL implementations sitting beside
; it in sub/fatprim.asm -- four plain in-page calls. That is the whole trick.
;
; fat.asm includes this at its ORIGINAL POSITION in both builds, so the file's
; emitted bytes are unchanged and the lean 16 KB cart stays byte-frozen.
;
; CLEAN-ROOM: our own code, moved. FAT12 provenance unchanged
; (basic/PROVENANCE.md §disk DSKIO host engine).
; ===========================================================================

; fat_io_putbyte — append the byte in A to the open-for-write file.
;   in:  A = byte to write.
;   out: Cy = 0 ok; Cy = 1 = disk full / write error.
; Buffers the byte into FSECTOR_BUF at offset FWR_BUFLEN; when the buffer fills
; (512 bytes) it is flushed to the file's current data sector (allocating/extending
; the cluster chain as needed) and the buffer resets. FWR_BYTES accumulates the
; true byte count for fat_io_close to stamp into the directory entry. The flush's
; DSKIO clobbers all registers, so state is kept in RAM.
fat_io_putbyte:
                ld      c, a                ; C = byte to store (survives the math)
                ld      hl, (FWR_BUFLEN)
                ld      de, FSECTOR_BUF
                add     hl, de              ; HL = FSECTOR_BUF + FWR_BUFLEN
                ld      (hl), c             ; store the byte
                ; advance buffered length and total byte count by 1.
                ld      hl, (FWR_BUFLEN)
                inc     hl
                ld      (FWR_BUFLEN), hl
                call    fwr_bytes_inc       ; FWR_BYTES += 1 (4-byte LE)
                ; if the 512-byte buffer is now full, flush it.
                ld      hl, (FWR_BUFLEN)
                ld      de, 512
                or      a
                sbc     hl, de
                jr      c, fip_ok           ; buffer not full yet
                call    fat_flush_data_sector
                ret     c                   ; disk full / write error
                ld      hl, 0
                ld      (FWR_BUFLEN), hl    ; buffer drained
fip_ok:
                or      a                   ; Cy = 0 success
                ret

; fwr_bytes_inc — FWR_BYTES += 1, 4-byte little-endian increment.
fwr_bytes_inc:
                ld      hl, FWR_BYTES
                ld      a, (hl)
                add     a, 1
                ld      (hl), a
                inc     hl
                ld      a, (hl)
                adc     a, 0
                ld      (hl), a
                inc     hl
                ld      a, (hl)
                adc     a, 0
                ld      (hl), a
                inc     hl
                ld      a, (hl)
                adc     a, 0
                ld      (hl), a
                ret

; fat_io_close — finish a sequential-write file durably.
;   out: Cy = 0 ok; Cy = 1 = I/O error.
; Flushes a buffered partial final sector (FWR_BUFLEN > 0), then rewrites the
; directory entry with the true byte count and first cluster.
fat_io_close:
                ld      hl, (FWR_BUFLEN)
                ld      a, h
                or      l
                jr      z, fic_dir          ; nothing buffered
                call    fat_flush_data_sector
                ret     c
fic_dir:
                jp      fat_dir_update      ; tail: write true size + first cluster
