                org     $6000
CALSLT          equ     $001C
EXPTBL          equ     $FCC1
target          equ     $49EE
; --- shared helper (paid once) ---
helper_start:
                ld      iy,(EXPTBL-1)
                jp      CALSLT
helper_end:
; --- per call site, helper form ---
site_start:
                ld      ix,target
                call    helper_start
site_end:
; --- per call site, inline form (no helper) ---
inline_start:
                ld      ix,target
                ld      iy,(EXPTBL-1)
                call    CALSLT
inline_end:
