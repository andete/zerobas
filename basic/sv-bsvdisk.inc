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
; The text is VERBATIM. basic/save.asm leaves a tenant-call stub under the SAME
; entry label as the body it replaced, which is why the
; `jr`/fall-through reaching it from the resident PARSE needs no edit.
;
; `sv_load_error` is the one rebound name: resident it is a zero-byte EQU onto
; `load_error`; in the tenant it is the
; sub-local reporter that sets SV_STAT and lets the resident stub report ONCE.
; ~~Its `ret`-not-abort shape is preserved exactly~~ -- 🔴 NOT ANY MORE: since
; D-DISKFULLRETRY (2026-10-02) it ABORTS to save_tenant from any depth, because
; the resume retried a failed flush on every remaining byte
; ([[load-error-is-not-abort]], sub/save.asm's ERROR PATH note).
;
; CLEAN-ROOM: our own code, moved. Cassette/disk format provenance unchanged
; (basic/PROVENANCE.md).
; ===========================================================================

bsv_open:
                ; --- create the file and set the DTA -----------------------
                call    disk_write_begin    ; require DISKSLOT_OK; Set-DTA; Create
                ; --- D-DISKFULLSTAMP: does the whole image FIT? ------------
                ; MEASURED on the CF-3300 (scratchpad/bsvfull_stamp.out): when it
                ; does not, the header is written, the data block is refused
                ; WHOLE (no partial data, no second cluster even with two free),
                ; and the file is CLOSED -- a Ctrl-Z after the header, size 8,
                ; one cluster, then 66. Streaming on until the disk filled left
                ; ours a LOST cluster (an allocated chain no entry points at).
                ; So count first (fat_fits, shared with tokenised SAVE).
                ld      hl,(DSV_END)
                ld      de,(CURPTR)
                or      a
                sbc     hl,de               ; HL = length - 1
                ld      de,7
                add     hl,de               ; HL = header + length - 1, CF = bit 16
                call    fat_fits            ; A = 0 fits, $FF does not
                push    af                  ; the verdict, across the header writes
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
                pop     af
                or      a
                jr      nz,bsv_full         ; D-DISKFULLSTAMP: the block cannot fit
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
; bsv_full -- the CF-3300's refusal: close the file as it stands (its CLOSE adds
; the Ctrl-Z; the successful path does not -- a 263 B BSAVE is 263 B there), then
; 66. A close that cannot even place the header (no free cluster at all) fails
; with the allocator's own 66 pending.
bsv_full:
                ld      a,$1A
                call    disk_putbyte
                call    fat_io_close        ; header + Ctrl-Z, stamped
                jp      c,sv_load_error     ; its code is already pending
                ld      a,66                ; Disk full
                ld      (DISKOP_ERR),a
                jp      sv_load_error
