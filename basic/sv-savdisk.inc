; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sv-savdisk.inc -- SAVE's tokenised DISK write engine (sav_disk_write .. sav_fin).
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
; ~~Its `ret`-not-abort shape is preserved exactly~~ -- 🔴 NOT ANY MORE: in
; disk.rom (the only home of this engine now) sv_load_error ABORTS to
; hk_dpsave (D-DISKFULL, `hkds_run`), see [[load-error-is-not-abort]].
;
; CLEAN-ROOM: our own code, moved. Cassette/disk format provenance unchanged
; (basic/PROVENANCE.md).
; ===========================================================================

                ; --- (no flag) tokenised save: create + $FF marker + image --
sav_disk_write:
                call    disk_write_begin
                ; D-SAVEFULLSTAMP: MEASURED on the CF-3300 (scratchpad/
                ; savefull_probe.py), a program that cannot fit is refused WHOLE:
                ; SF.BAS = the $FF marker only, size 1, one cluster -- and NO
                ; Ctrl-Z, where BSAVE's refusal has one. Ours streamed until the
                ; disk filled and left a LOST cluster. The arithmetic and the
                ; refusal live in disk/kernel.asm's free region (sav_fits,
                ; sav_full): this engine's region is pinned with no room.
                call    sav_fits            ; A = 0 fits, $FF does not
                push    af
                ; --- $FF tokenised-BASIC disk marker -----------------------
                ld      a,BASIC_DISK_ID     ; $FF
                call    disk_putbyte
                pop     af
                or      a
                jp      nz,sav_full         ; D-SAVEFULLSTAMP: it cannot fit
                ; --- program image: TXTBASE .. PRGEND+1 inclusive ----------
                ; PRGEND points at the $0000 end-of-program marker (program.asm),
                ; so the last image byte is PRGEND+1. Walk inclusive.
                ld      hl,TXTBASE
                ld      (DSV_PTR),hl
                ld      hl,(PRGEND)
                inc     hl                  ; last image byte = PRGEND+1
                ld      (DSV_END),hl
sav_data:
                ld      hl,(DSV_PTR)
                ld      a,(hl)
                call    disk_putbyte
                ld      hl,(DSV_PTR)
                ld      de,(DSV_END)
                ld      a,h
                cp      d
                jr      nz,sav_next
                ld      a,l
                cp      e
                jr      z,sav_fin
sav_next:
                ld      hl,(DSV_PTR)
                inc     hl
                ld      (DSV_PTR),hl
                jr      sav_data
sav_fin:
                jp      disk_write_end
