; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sv-bsvcas.inc -- BSAVE's TAPE write engine (bsv_cas_open .. bsv_cas_fin).
; ===========================================================================
; One of the five SAVE-family WRITE ENGINES evicted from main page 1 into the
; sub-ROM PAGE-1 tenant sub/save.asm (SUBROM_IDX_SAVE) to fund `TIME` and
; interrupt-traps T5 together -- docs/decision-fund-time-and-t5.md, D-FUND-1.
; BLOAD's mirror, and the same mechanism: beside fatprim_tenant the FAT12 write
; primitives are in-page calls instead of cross-slot round trips.
;
; The text is VERBATIM. It sits at its ORIGINAL POSITION — chosen so the (now
; retired) lean 16 KB cart stayed byte-frozen when this was carved — and the
; build leaves a tenant-call stub under the SAME entry label instead, which is
; why the `jr`/fall-through reaching it from the resident PARSE needs no edit.
;
; `sv_load_error` is the one rebound name: resident it is a zero-byte EQU onto
; `load_error` (which is what kept the then-lean bytes unchanged), in the tenant it is the
; sub-local reporter that sets SV_STAT and lets the resident stub report ONCE.
; Its `ret`-not-abort shape is preserved exactly -- see [[load-error-is-not-abort]].
;
; CLEAN-ROOM: our own code, moved. Cassette/disk format provenance unchanged
; (basic/PROVENANCE.md).
; ===========================================================================

bsv_cas_open:
                ; --- tape header block: TAPOON(long) + 10x$D0 + 6-char name + TAPOOF ---
                ld      a,$FF               ; non-zero -> long header
                call    TAPOON
                jp      c,sv_load_error
                ; emit 10x BINARY_ID ($D0)
                ld      a,10
                ld      (TSV_CNT),a
bsv_cas_id:
                ld      a,BINARY_ID         ; $D0
                call    TAPOUT
                jp      c,sv_load_error
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,bsv_cas_id
                ; emit 6-char name from TSV_NAME
                call    tape_name_emit
                jp      c,sv_load_error
                call    TAPOOF              ; end of header block
                ; --- tape data block: TAPOON(short) + start/end/exec + data + TAPOOF ---
                xor     a                   ; zero -> short header
                call    TAPOON
                jp      c,sv_load_error
                ; start (LE): low byte then high byte, each from CURPTR
                ld      hl,CURPTR
                call    tape_putword        ; emits (HL) then (HL+1)
                jp      c,sv_load_error
                ; end (LE)
                ld      hl,TSV_END
                call    tape_putword
                jp      c,sv_load_error
                ; exec (LE)
                ld      hl,EXECPTR
                call    tape_putword
                jp      c,sv_load_error
                ; data bytes RAM[start..end] inclusive; CURPTR = start
bsv_cas_data:
                ld      hl,(CURPTR)
                ld      a,(hl)
                call    TAPOUT
                jp      c,sv_load_error
                ld      hl,(CURPTR)
                ld      de,(TSV_END)
                ld      a,h
                cp      d
                jr      nz,bsv_cas_next
                ld      a,l
                cp      e
                jr      z,bsv_cas_fin       ; cur == end -> done
bsv_cas_next:
                ld      hl,(CURPTR)
                inc     hl
                ld      (CURPTR),hl
                jr      bsv_cas_data
bsv_cas_fin:
                call    TAPOOF              ; end of data block; motor off
                ret                         ; back to the REPL
