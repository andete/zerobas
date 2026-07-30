; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — printusing.asm  (PRINT USING format-scanner tenant)
; ===========================================================================
; The PRINT USING format literal-scanners (pu_to_field + pu_emit_tail), evicted
; from the repack main ROM's basic/printusing.asm into sub-ROM PAGE 0
; (docs/spec-evict-printusing.md), to free page-1 window space for the
; error-handling S2a slice.
;
; WHY SUB-SIDE. Both routines are PURE leaves over the PU_* RAM sysvars + pchar:
; they scan the copied format string (PU_FMT) and emit its literal characters,
; identifying the next #/!/&/\..\ field (pu_to_field) or stopping at it
; (pu_emit_tail). No eval, no pu_deref_body, no div10 — so they are a valid
; page-0 tenant run under DI, and the fragile value-render/deref paths
; (pu_do_number / pu_do_string / pu_fmt_int) stay RESIDENT and unchanged.
;
; The shared body lives in basic/pu-render.inc (the shared
; inline copy). Here it binds `pchar` to sub/detok.asm's sub-local DETOKBUF
; append (both are co-resident page-0 tenants — SUB_PARTS — so pchar is defined
; once, there, and shared). The two entry wrappers reset the DETOKBUF cursor,
; run the scanner, and 0-terminate the buffer; the resident stubs
; (basic/printusing.asm) drain DETOKBUF through the real
; print_string, honouring PRDEST — so the ONE scanner feeds both PRINT USING ->
; screen and PRINT# USING -> file (the 003ff70 file-form fix stays main-side).
;
; RAM: DETOKBUF ($BE00, 512 B) + DB_CUR ($F108) are shared sysvars.inc equates,
; byte-identical main/sub. PU_FMTMAX is 32, so a scanner's literal run is <= 32 B
; -- the 512 B buffer never overflows and needs no bound check.
;
; CLEAN-ROOM: original code (the scanners are copied verbatim from our own
; basic/printusing.asm via basic/pu-render.inc). No disassembly.
; ===========================================================================

BACKSLASH       equ     $5C                 ; '\' field char (pu-render.inc)

; --- pu_tofield_tenant: the SUBROM_IDX_PU_TOFIELD entry --------------------
; Reset the DETOKBUF cursor, run pu_to_field (emits leading literals via the
; sub-local pchar, sets PU_TYPE/PU_W/PU_POS, CF set if no field), 0-terminate the
; buffer, and return the no-field flag in A (0 = a field was found; 1 = none) —
; A is the CALSLT-safe result channel; the resident stub turns it back into CF.
pu_tofield_tenant:
                ld      de,DETOKBUF
                ld      (DB_CUR),de         ; reset the DETOKBUF write cursor
                call    pu_to_field         ; emit leading literals -> DETOKBUF; CF=no-field
                ld      hl,(DB_CUR)
                ld      (hl),0              ; 0-terminate (ld: no flag effect, CF survives)
                ld      a,0
                ret     nc                  ; field found -> A=0
                inc     a                   ; no field -> A=1
                ret

; --- pu_tail_tenant: the SUBROM_IDX_PU_TAIL entry -------------------------
; Reset the cursor, run pu_emit_tail (emits trailing literals up to the next
; field / format end), 0-terminate. No result flag.
pu_tail_tenant:
                ld      de,DETOKBUF
                ld      (DB_CUR),de
                call    pu_emit_tail
                ld      hl,(DB_CUR)
                ld      (hl),0
                ret

; The shared scanner body (pu_to_field/ptf_* + pu_emit_tail). Binds pchar to
; sub/detok.asm's sub-local DETOKBUF append (defined once, co-resident).
                include "basic/pu-render.inc"
