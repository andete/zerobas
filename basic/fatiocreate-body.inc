; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fatiocreate-body.inc -- fat_io_create (the sequential FAT12 WRITE open).
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
; emitted bytes are unchanged.
;
; CLEAN-ROOM: our own code, moved. FAT12 provenance unchanged
; (basic/PROVENANCE.md §disk DSKIO host engine).
; ===========================================================================

; fat_io_create — create (truncate-or-make) the file named in DISK_FCB_NAME for
; sequential WRITE from offset 0.
;   out: Cy = 0 created (stream ready); Cy = 1 = mount / dir-full / I/O error.
; Mounts, makes/reuses a root-dir slot (fat_dir_create), and resets the write
; iterator: no cluster yet, empty buffer, zero bytes. The first cluster is
; allocated lazily on the first flush.
fat_io_create:
                call    fat_mount
                ret     c
                ld      hl, DISK_FCB_NAME
                call    fat_dir_create
                ret     c
                xor     a
                ld      (FWR_SECIDX), a
                ld      hl, 0
                ld      (FWR_CLUS), hl
                ld      (FWR_FIRST), hl
                ld      (FWR_BUFLEN), hl
                ld      (FWR_BYTES), hl
                ld      (FWR_BYTES + 2), hl
                ; D-LOF (docs/spec-basic-lof-size-field.md §4a): the LOF field
                ; too. FAT_FILESIZE is written ONLY by fat_find, i.e. only when a
                ; file is FOUND, so before this a created channel reported
                ; whatever the previous tenant of the FCH_STATE0 span left --
                ; MEASURED at 26 and at 2048 (docs/lof-cf3300-characterization.md
                ; §2). The famous -1 was just the cold-boot content of the cell;
                ; nothing ever stored $FFFF. A created file is 0 bytes until
                ; CLOSE stamps the directory, and the reference agrees (0, and
                ; still 0 after a PRINT #). All four bytes: it is a size field,
                ; and a half-initialised one is the same defect one reader away.
                ld      (FAT_FILESIZE), hl
                ld      (FAT_FILESIZE + 2), hl
                or      a                   ; Cy = 0 success
                ret
