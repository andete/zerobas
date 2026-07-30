; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sv-diskwr.inc -- the sequential DISK write helpers (disk_write_begin/putword/putbyte/write_end).
; ===========================================================================

; Shared disk-write helper (the WRITE analogue of the read side's fat_io_open /
; fat_io_getbyte). Built on the loader-side FAT12 engine over the STANDARD $4010
; DSKIO entry (basic/fat.asm) — disk-ROM-independent, NOT the private bdos_entry.
; disk_write_begin creates a fresh file; disk_putbyte appends one byte (the engine
; buffers it into a 512-byte sector and flushes whole sectors as they fill);
; disk_write_end flushes the partial final sector and stamps the directory size.
; The engine tracks exact byte counts, so the on-disk file size is its true length
; (no 128-byte record zero-padding) — SAVE/BSAVE produce byte-exact images.

; disk_write_begin — require a recorded disk-ROM slot, then Create (truncate-or-
; make) the file named in DISK_FCB_NAME and arm the sequential-write iterator.
; On any failure jumps to sv_load_error (does not return).
;
; DOCUMENTED DIVERGENCE (no write rollback): fat_io_create stamps the directory
; entry up front. If a later disk_putbyte/disk_write_end fails mid-stream (disk
; full / write error), the error path jumps to sv_load_error WITHOUT fat_io_close, so
; the entry is left with an un-stamped size/first-cluster (a zero-length or partial
; file). Acceptable for a game loader — a failed SAVE simply needs re-issuing — and
; no caller depends on atomic write; surfaced here so it is not mistaken for a bug.
disk_write_begin:
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,sv_load_error
                call    fat_io_create       ; mount + dir-create + reset write state
                jp      c,sv_load_error        ; disk full / dir full / write protect / I-O
                ret

; disk_putword — write the 16-bit little-endian word stored at RAM address HL out
; through disk_putbyte (low byte then high byte). disk_putbyte clobbers HL (and
; everything else), so the source address is kept in a RAM slot (DSV_PTR, which is
; otherwise only used by do_save's own loop and is free during the BSAVE header)
; and reloaded for the high byte rather than trusted in a register.
;   in:  HL = address of a 2-byte LE word in page-3 RAM.
;   out: both bytes appended to the write stream. Clobbers all (via disk_putbyte).
;
; ⚠️ SUB-SIDE ONLY, and this gate is the second `IF SUB_BUILD` in the tree
; (sub/sub.asm: "it gates body .inc files that genuinely differ by side").
; This file is shared by both ROMs, but disk_putword's ONLY caller is
; basic/sv-bsvdisk.inc's BSAVE header emitter, and that body is included by
; sub/save.asm alone — the whole BSAVE/SAVE write engine is a sub-ROM page-1
; tenant (SUBROM_IDX_SAVE). So the main ROM assembled 16 bytes it could never
; reach. Gated, not deleted, by the ROM REGION STRUCTURE REVIEW's R1 carve
; (docs/spec-rom-region-rebalance-r1.md A3): 16 B off main PAGE 1, sub.rom
; byte-identical.
;
; 🔴 IT WAS THE BUILD THAT CAUGHT THIS, NOT THE REVIEW. R1's transitive dead-code
; sweep walked only main.asm's include closure, which does not contain
; sv-bsvdisk.inc, so the caller was INVISIBLE and the routine read as plain dead
; code. Deleting it outright failed the assembly with a clean undefined-symbol
; ERROR. Lesson for the next sweep over a SHARED body: "dead" is per-BUILD, and a
; file included by both ROMs has two answers (docs/rom-region-structure-review.md
; §0.1, §4).
    IF SUB_BUILD
disk_putword:
                ld      (DSV_PTR),hl        ; remember the word's address
                ld      a,(hl)              ; low byte
                call    disk_putbyte
                ld      hl,(DSV_PTR)        ; reload (disk_putbyte clobbered HL)
                inc     hl
                ld      a,(hl)              ; high byte
                call    disk_putbyte
                ret
    ENDIF

; disk_putbyte — append the byte in A to the open-for-write file via the FAT12
; engine (which buffers into a 512-byte sector and flushes whole sectors as they
; fill). On a write error jumps to sv_load_error.
;   in:  A = byte to write.
;   out: byte appended. Clobbers all (CALSLT clobbers everything across a sector
;        flush's DSKIO; the engine keeps its state in RAM).
disk_putbyte:
                call    fat_io_putbyte
                jp      c,sv_load_error        ; disk full / write error
                ret

; disk_write_end — flush the buffered partial final sector and stamp the directory
; entry with the true byte count + first cluster (fat_io_close). On a write error
; jumps to sv_load_error. Returns to the caller's caller (the REPL) on success.
disk_write_end:
                call    fat_io_close
                jp      c,sv_load_error
                ret                         ; back to the prompt
