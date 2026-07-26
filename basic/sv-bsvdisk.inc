; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sv-bsvdisk.inc -- BSAVE's DISK write engine (bsv_open .. bsv_fin).
; ===========================================================================
; One of the five SAVE-family WRITE ENGINES evicted from main page 1 into the
; sub-ROM PAGE-1 tenant sub/save.asm (SUBROM_IDX_SAVE) to fund `TIME` and
; interrupt-traps T5 together -- docs/decision-fund-time-and-t5.md, D-FUND-1.
; BLOAD's mirror, and the same mechanism: beside fatprim_tenant the FAT12 write
; primitives are in-page calls instead of cross-slot round trips.
;
; The text is VERBATIM. basic/save.asm includes it at its ORIGINAL POSITION for
; ROM_BASE >= $4000, so the lean 16 KB cart stays byte-frozen; the repack build
; leaves a tenant-call stub under the SAME entry label instead, which is why the
; `jr`/fall-through reaching it from the resident PARSE needs no edit.
;
; `sv_load_error` is the one rebound name: resident it is a zero-byte EQU onto
; `load_error` (so the lean bytes are unchanged), in the tenant it is the
; sub-local reporter that sets SV_STAT and lets the resident stub report ONCE.
; Its `ret`-not-abort shape is preserved exactly -- see [[load-error-is-not-abort]].
;
; CLEAN-ROOM: our own code, moved. Cassette/disk format provenance unchanged
; (basic/PROVENANCE.md).
; ===========================================================================

bsv_open:
                ; --- create the file and set the DTA -----------------------
                call    disk_write_begin    ; require DISKSLOT_OK; Set-DTA; Create
                ; --- 7-byte header: $FE start(LE) end(LE) exec(LE) ----------
                ; disk_putbyte clobbers ALL registers (its CALSLT may flush a
                ; record), so each 16-bit field is emitted via disk_putword, which
                ; reloads the word from its RAM home for the high byte rather than
                ; trusting a register across the call.
                ld      a,BSAVE_DISK_ID     ; $FE
                call    disk_putbyte
                ld      hl,CURPTR           ; start (LE)
                call    disk_putword
                ld      hl,DSV_END          ; end (LE)
                call    disk_putword
                ld      hl,EXECPTR          ; exec (LE)
                call    disk_putword
                ; --- data bytes [start..end] inclusive, RAM or VRAM --------
                ; With ",S" (VRAM_FLAG) the start/end are VRAM addresses and each
                ; byte is fetched via RDVRM ($004A) instead of a RAM read; the
                ; loop shape is otherwise identical.
bsv_data:
                ld      hl,(CURPTR)
                ld      a,(VRAM_FLAG)
                or      a
                jr      z,bsv_data_ram
                call    RDVRM               ; HL=CURPTR (VRAM addr) -> A
                jr      bsv_data_put
bsv_data_ram:
                ld      a,(hl)              ; HL=CURPTR (RAM addr) -> A
bsv_data_put:
                call    disk_putbyte
                ld      hl,(CURPTR)
                ld      de,(DSV_END)
                ld      a,h
                cp      d
                jr      nz,bsv_next         ; high bytes differ -> more to do
                ld      a,l
                cp      e
                jr      z,bsv_fin           ; cur == end -> last byte written
bsv_next:
                ld      hl,(CURPTR)
                inc     hl
                ld      (CURPTR),hl
                jr      bsv_data
bsv_fin:
                jp      disk_write_end      ; flush + Close + back to the prompt
