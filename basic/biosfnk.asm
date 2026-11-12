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

; FNKSB ($00C9) -- D-BIOSRUNG (2026-11-12). C-BIOS's was a print_debug stub. Measured on
; the VG-8020 with CNSDFG changed BEHIND BASIC's back (scratchpad/fnksb_probe.py,
; fnksb_run*.out): KEY OFF + CNSDFG := $FF -> the key row PAINTED (a KILBUF call in its
; place leaves it blank: FNKSB did it), with DSPFNK's registers exactly (HL kept, DE
; $FC40, BC 0, A 0 -- biosregs' dsp0 row); KEY ON + CNSDFG := 0 -> nothing, A = 0
; (CNSDFG's value, not the caller's). So: CNSDFG != 0 -> DSPFNK.
bios_fnksb:
                ld      a,(CNSDFG)
                or      a
                ret     z
                jr      bios_dspfnk

; CALBAS ($0159) -- D-BIOSRUNG (2026-11-12). C-BIOS's printed "ERROR:CALLED NON EXISTING
; BASIC." and never returned (scratchpad/calbas_run.out). The published contract: call
; the BASIC interpreter at IX from any slot. The VG-8020, called with IX = $004D
; (WRTVRM, the same entry in both ROMs), A = $5A, HL = $3F10: the cell written, HL / DE /
; BC / A back, IY 0 -- an inter-slot call into the main ROM's slot (EXPTBL's byte,
; slot 0 here). IYH := that byte, then CALSLT.
bios_calbas:
                ld      iy,(EXPTBL - 1)     ; IYH = EXPTBL[0]: the main ROM's slot
                jp      CALSLT

; OUTDLP ($014D) -- D-BIOSRUNG (2026-11-12). C-BIOS's was a print_debug stub: nothing
; reached the printer. Measured on the VG-8020 with openMSX's printer logger
; (scratchpad/outdlp_probe.py, outdlp_run.out): `A TAB B TAB C CR LF` prints
; `A` + 7 spaces + `B` + 7 spaces + `C\r\n`; `ABC TAB D` pads from column 3 to 8 --
; a TAB is spaces to the next multiple of 8 of LPTPOS, and LPTPOS is 0 after the CR.
; LPTPOS is kept as BASIC's LPRINT keeps it (pch_lpt, basic/print.asm: CR -> 0, LF
; leaves it, else +1, saturating at 255). A failing LPTOUT returns its CF (⚠️ the
; published Device I/O error, and a non-MSX printer's character transform, are NOT
; measured yet -- TODO D-BIOSRUNG). A kept, as the contract's "Registers: F".
bios_outdlp:
                cp      9
                jr      z,odl_tab
odl_put:
                push    af
                call    LPTOUT
                jr      c,odl_fail
                pop     af
                push    af
                cp      13
                jr      z,odl_home
                cp      10
                jr      z,odl_done
                ld      a,(LPTPOS)
                inc     a
                jr      z,odl_done          ; 255 saturates, as pch_lpt
                ld      (LPTPOS),a
                jr      odl_done
odl_home:
                xor     a
                ld      (LPTPOS),a
odl_done:
                pop     af
                ret
odl_fail:
                ; D-LPTSTOP: the published face -- the VG-8020 says `Device I/O error`
                ; (outdlp_fail_run5.out), through BASIC as its other errors
                pop     af
                ld      a,19                ; Device I/O error
                jp      raise_error
odl_tab:
                ld      a,' '
                call    odl_put
                ret     c
                ld      a,(LPTPOS)
                and     7
                jr      nz,odl_tab
                ld      a,9
                ret

; BREAKX ($00B7) -- D-BRKLATCH (2026-11-12). C-BIOS's body reads CTRL+STOP; on the
; VG-8020 a press BREAKX has seen does not ALSO reach the interrupt's latch -- after
; LPTOUT's CTRL-STOP abort INTFLG reads 0, and 0 ten frames later, the key still down
; (scratchpad/BL_lptintflg.out); only the auto-repeat latches it later (from 36 frames).
; C-BIOS latches INTFLG only for a key the scan sees as NEWLY down against OLDKEY (or a
; repeat), so marking STOP down in OLDKEY consumes the press the same way. CF / A as
; C-BIOS's body leaves them.
bios_breakx:
                call    CBIOS_BREAKX
                ret     nc
                ld      a,(OLDKEY+7)
                and     $EF                 ; STOP (row 7 bit 4) already down
                ld      (OLDKEY+7),a
                scf
                ret

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
; ISCNTC ($00BA) / CKCNTC ($00BD) -- D-BIOSRUNG (2026-11-12). C-BIOS's were print_debug
; stubs that returned in every state. Measured on the VG-8020, called directly with the
; state set by the caller's own code (scratchpad/iscntc_probe.py, iscntc_run3..8.out),
; both entries alike: BASROM != 0 -> return, A = BASROM, INTFLG untouched; INTFLG 0 ->
; return, A = 0; 3 (CTRL-STOP) -> `Break in <line>`; 4 (STOP) -> wait for the key to be
; up and pressed AGAIN (a held key does not end it), then return A = 4, INTFLG 0 -- or a
; CTRL-STOP there breaks. BC / DE / HL kept. The rare two (a break, a wait) need BASIC
; and live in page 1 beside inp_break (basic/input.asm); this front is page 0.
bios_iscntc:
                ld      a,(BASROM)
                or      a
                ret     nz                  ; a protected ROM BASIC: A = BASROM
                ld      a,(INTFLG)
                or      a
                ret     z                   ; nothing pending: A = 0
                jp      isc_slow

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
