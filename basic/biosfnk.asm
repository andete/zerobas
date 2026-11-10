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
                ld      a,CON_ROWS          ; 24 either way: the console's bound is
                ld      (CRTCNT),a          ; CRTCNT + CNSDFG (crt_rows), as the VG-8020
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

; PINLIN ($00AE) / INLIN ($00B1) / QINLIN ($00B4): C-BIOS's INLIN is a skeleton --
; its Return handler is a bare `ret` back into the key loop, so a program calling
; any of the three HUNG (scratchpad/biossweep_b6.out: "AB" echoed, never returned).
; The VG-8020 returns the line in BUF, 0-terminated, HL = BUF - 1, A = $0D; QINLIN
; prints "? " first. BASIC's own line editor (read_line, basic/repl.asm -- the
; prompt's and INPUT's: screen editing, Enter reads the logical line) does the
; work; it is MAIN PAGE 1, so page 1 is mapped to primary slot 0 for the call and
; the caller's layout put back after (htimi_guard's way). CF = Ctrl-STOP as
; read_line reports it. PINLIN's AUTO handling is BASIC's own (repl), not here.
bios_qinlin:
                ld      a,'?'
                call    CHPUT
                ld      a,' '
                call    CHPUT
bios_inlin:                                 ; also PINLIN
                in      a,(PSLTREG)
                push    af                  ; the caller's slot layout
                and     %11110011           ; page 1 -> primary slot 0: main ROM
                out     (PSLTREG),a
                call    read_line           ; LINEBUF (= BUF) <- the line; CF = STOP
                pop     hl                  ; H = the caller's layout (flags kept)
                ld      a,h
                out     (PSLTREG),a
                ld      hl,LINEBUF - 1      ; the published HL
                ld      a,$0D               ; A as the VG-8020 leaves it
                ret
