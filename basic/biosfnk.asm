; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; biosfnk.asm -- the BIOS's INIFNK ($003E), ERAFNK ($00CC), DSPFNK ($00CF) and BEEP
; ($00C0), D-BIOSCONTRACT
; (2026-11-09). C-BIOS's were print_debug stubs: a program's own KEY OFF / KEY ON
; through the BIOS did nothing. Measured on the Philips VG-8020, called directly
; (scratchpad/biossweep_fnk.out): ERAFNK sets CNSDFG ($F3DE) to 0 and blanks the
; function-key row; DSPFNK sets it to $FF and paints the row; in a graphics mode
; only the cells change (VRAM untouched). HL / BC kept here (the VG-8020 keeps HL).
; This is the work BASIC's KEY OFF / KEY ON did after the stub returned (sub2/
; scrstmt.asm, which now only calls the BIOS): CRTCNT = 24 + A, so 24 / 23.
; ⚠️ The VG-8020 leaves CRTCNT 24 after DSPFNK too -- it protects the key row
; through CNSDFG, and its BASIC holds 24 under KEY ON (biossweep_crt.out); zerobas's
; console bounds its scroll by CRTCNT, so DSPFNK writes 23 until that is changed
; (TODO D-BIOSCONTRACT). Page 0 (the $3297 pad): a caller's page 1 may be RAM.
; Clean-room: own code; the published entry names and work-area cells.

; INIFNK ($003E): C-BIOS's was a stub; the VG-8020 rewrites the ten defaults into
; FNKSTR (scratchpad/biossweep_b5.out). The keystr tenant's op 0 -- what the cold
; boot runs (basic/interp.asm) -- through bios_fnk's call.
bios_inifnk:
                push    hl
                push    bc
                push    ix
                xor     a                   ; op 0: the defaults
                jr      bios_fnk_key

bios_erafnk:
                xor     a                   ; the line hidden
                jr      bios_fnk
bios_dspfnk:
                ld      a,$FF               ; the line shown
bios_fnk:
                push    hl
                push    bc
                push    ix
                ld      c,a                 ; C = 0 / $FF (= -1)
                add     a,CON_ROWS          ; 24 / 23
                ld      (CRTCNT),a
                ld      a,c
                ld      (CNSDFG),a
                ld      a,(SCRMOD)
                cp      2
                jr      nc,bios_fnk_out     ; graphics: the cells only
                ld      a,KEYOP_FNKBLANK
                sub     c                   ; BLANK / PAINT (= BLANK + 1)
bios_fnk_key:                               ; A = the keystr op
                ld      (KEYARG),a
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_KEYSTR
                call    subrom_call         ; CF = no sub-ROM: nothing painted
bios_fnk_out:
                pop     ix
                pop     bc
                pop     hl
                ret

; BEEP ($00C0): C-BIOS's was a print_debug stub -- no tone. The sub-ROM's BEEP tenant
; (sub/beep.asm, the body BASIC's BEEP runs) through subrom_call; the VG-8020's tone
; is pinned by beep-acceptance's `bios` case (a USR to $00C0). HL / IX kept (CALSLT
; spends the rest; the VG-8020 changes DE / BC too).
bios_beep:
                push    hl
                push    ix
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_BEEP
                call    subrom_call
                pop     ix
                pop     hl
                ret
