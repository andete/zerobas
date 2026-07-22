; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; readdata.asm -- the READ/DATA value engine as a PAGE-0 sub-ROM tenant
; (SUBROM_IDX_READVAL). docs/spec-eviction-g7-space.md.
;
; WHY THIS ONE. G7 (sprites) needs ~390 B of page-1 tail that does not exist, and
; the scout (scratchpad/g6_carve_scout.py) found no single clean carve that size,
; so G7 is funded by a COMBINATION. This is the largest of them. The rule the
; scout applies (G6 spec §8): a PAGE-0 tenant may call page-1 residents but NOT
; the BIOS or the page-0 low region (the float pack), judged transitively --
; almost nothing qualifies because almost everything reaches `eval`. The
; READ/DATA value engine does: it walks tokenised program RAM (DATAPTR/DATALINE/
; RESTORE_LINE/DATASTATE, all page-3 RAM) and parses ASCII digits, with no eval,
; no float work and no BIOS. It is warm rather than hot -- one CALSLT per READ
; item, and a READ loop's cost is dominated by the variable store around it.
;
; The body is basic/readdata-body.inc, shared VERBATIM with the lean cart (which
; still has it inline, so the lean image stays byte-identical). Only the (CF, DE)
; return contract changes shape: CF cannot ride back through subrom_call, so the
; tenant lands it in RDV_ST/RDV_VAL and the resident stub rebuilds it.
;
; Three shared callees stay resident and are duplicated sub-locally below:
; skip_spaces, upcase (the page-0 tokeniser's own `upcase` is reused instead) and
; tok_skip (the resident's copy is page 1; sub/lineedit.asm's is page 1 too).
;
; Clean-room: this is our own code, relocated. No disassembly.

readdata_tenant:
                call    read_one_value      ; CF set + DE = value, else out of data
                ld      (RDV_VAL),de
                ld      a,0
                jr      nc,rdt_status
                inc     a                   ; 1 = a value was read
rdt_status:
                ld      (RDV_ST),a
                ret

                include "basic/readdata-body.inc"

; --- sub-local skip_spaces (the resident's is page 1) ----------------------
skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      skip_spaces

; --- sub-local tok_skip (page 0's copy of the shared body) -----------------
                include "basic/tokskip-body.inc"
