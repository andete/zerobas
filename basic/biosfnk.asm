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
                push    hl                  ; D-BREAKXBUF (2026-11-19): the key buffer emptied,
                ld      hl,(PUTPNT)         ;   GETPNT := PUTPNT, and OLDKEY row 7 := $EF, as the
                ld      (GETPNT),hl         ;   VG-8020 (docs/bios/BREAKX.md R-BX-BUF); HL kept
                pop     hl
                ld      a,$EF               ; STOP (row 7 bit 4) already down
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
                call    bf_scroll           ; D-DSPFNKSCROLL (basic/main.asm, the low region's end)
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
                ei                          ; D-ISCNTCEI (2026-11-19): interrupts on after, and
                ld      a,(INTFLG)          ;   with nothing pending A = 0, F $54 (an AND's), as
                and     a                   ;   the VG-8020 (docs/bios/ISCNTC.md R-IS-AF / R-IS-EI)
                ret     z                   ; nothing pending: A = 0
                jp      isc_slow

; PNTINI ($0129) / SCANL ($012F) / SCANR ($012C) -- D-BIOSRUNG (2026-11-12): C-BIOS's
; were bare `ret`s. The body is the sub-ROM's paint tenant (sub/paintbios.asm, which
; carries the VG-8020's measured behaviour); here only the op in C (PNTINI's A goes in
; B). Each `db $21` is an `ld hl,nn` that swallows the next entry's `ld c,n` -- HL is
; an input to none of the three. IX kept, as bios_beep.
bios_pntini:
                ld      b,a
                ld      c,2
                db      $21                 ; skips bios_scanl's `ld c,1`
bios_scanl:
                ld      c,1
                db      $21                 ; skips bios_scanr's `ld c,0`
bios_scanr:
                ld      c,0
                push    ix
                call    sr_inl1
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_PAINT)
                pop     ix
                ret

; GRPPRT ($008D) -- D-BIOSRUNG (2026-11-12). C-BIOS's draws in SCREEN 2 only; on the
; VG-8020 the BIOS entry draws in every mode with the pixel pitch from SCRMOD's bit 0
; (SCREEN 3 -- and SCREEN 1 -- a 4x4 block per font pixel, the advance and CR 32;
; scratchpad/grpprt3_run*.out), which is exactly BASIC's own PRINT #-to-GRP: tenant
; (sub2/grpprt.asm, measured on the VG-8020 by D-OPENGRP). So the entry is that tenant,
; byte in E. Registers kept, as the VG-8020 keeps them.
bios_grpprt:
                push    hl
                push    de
                push    bc
                push    af
                push    ix
                ld      e,a
                ld      a,i                 ; D-GRPPRTEI (2026-11-19): P/V := the entry IFF2
                push    af
                call    sr_inl1
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_GRPPRT)
                pop     af
                pop     ix
                jp      pe,bgp_out          ; on at entry: on after, as the tenant leaves it
                pop     af                  ; A = the code
                push    af
                cp      $20
                jr      nc,bgp_out          ; printable: on after (docs/bios/GRPPRT.md R-GP-EI)
                di                          ; a control code: off again, as it was
bgp_out:
                pop     af
                pop     bc
                pop     de
                pop     hl
                ret

; STRTMS ($0099) -- D-BIOSRUNG / STRTMS (2026-11-12). C-BIOS's was a print_debug stub.
; Measured on the VG-8020 (scratchpad/strtms_run*.out, plycnt_run.out): PLYCNT counts
; PLAY statements queued and not yet started; STRTMS with MUSICF != 0 or PLYCNT = 0 does
; nothing, else st_go: PLYCNT - 1 and MUSICF := 7 -- all three voices fetch on. The same
; code is PLAY's start (st_go, from the parser tenant, sub/playparse.asm) and the
; servicer's sync, where every voice has reached its end marker (basic/playsvc.asm).
; st_go sits in island 1 (basic/islands.asm): this pad and the low region had no room
; for both halves (switch-build-check: the switch-off builds overran the low region).
; A / HL / F changed.
bios_strtms:
                ld      a,(MUSICF)
                or      a
                ret     nz                  ; playing: nothing
                ld      a,(PLYCNT)
                or      a
                ret     z                   ; no statement waiting
                jp      st_go

; PUTQ ($00F9) -- A = the queue (0..2), E = the byte. C-BIOS's writes at PUT and then
; steps it; the VG-8020's steps FIRST (three bytes land at VOICAQ+1..3, PUT 3), as its
; rings are read (scratchpad/strtms_run4.out). A full queue: Z, nothing written, B / C
; the old / new PUT, HL the entry + 3. Stored: HL = the descriptor, BC = the new PUT,
; A = the buffer's low byte, Z / C clear, DE kept -- as the VG-8020.
bios_putq:
                ld      c,a
                add     a,a
                add     a,c
                add     a,a
                add     a,low QUETAB
                ld      l,a
                ld      h,high QUETAB       ; HL = the descriptor (no carry: QUETAB is
                ld      a,(hl)              ;   $F959, queue 2 at $F965)
                ld      b,a                 ; B = the old PUT
                inc     a                   ; PUT + 1 ...
                inc     hl
                inc     hl
                inc     hl
                and     (hl)                ; ... AND the size
                ld      c,a                 ; C = the new PUT
                dec     hl
                dec     hl
                cp      (hl)                ; = GET: full -- D-PUTQREGS (2026-11-19): B the old
                inc     hl                  ;   PUT, C the new, HL the entry + 3, as the VG-8020
                inc     hl                  ;   (docs/bios/PUTQ.md R-PQ-REGS)
                ret     z
                dec     hl
                dec     hl
                dec     hl
                ld      (hl),a              ; PUT := it
                ld      b,0
                push    hl
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a                 ; HL = the buffer (A = its low byte)
                add     hl,bc
                ld      (hl),e
                pop     hl
                ret                         ; Z clear from the `cp`, C clear from `add hl,bc`

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
; INLIN / QINLIN hand read_line to the shared tail; PINLIN's entry (bios_pinlin, basic/main.asm
; at the low region's end: this file's pad in front of the $3283 pin is full) hands
; read_line_col1 (D-PINLINSTART, docs/bios/PINLIN.md R-L-PIN).
bios_inlin:
                ld      hl,read_line
bil_go:
                in      a,(PSLTREG)
                push    af                  ; the caller's slot layout
                and     %11110011           ; page 1 -> primary slot 0: main ROM
                out     (PSLTREG),a
                call    cl_jphl             ; read_line(_col1): LINEBUF (= BUF) <- the line; CF = STOP
                pop     hl                  ; H = the caller's layout (flags kept)
                ld      a,h
                out     (PSLTREG),a
                ld      hl,LINEBUF - 1      ; the published HL
                ld      a,$0D               ; A as the VG-8020 leaves it
                ret     nc
                ; D-INLINSTOPF (2026-11-14): on CTRL-STOP the VG-8020 returns A = 0 and
                ; F = $45 (Z, P/V, Cy) from all three entries -- `xor a / scf`'s flags
                ; exactly, read as a result (scratchpad/IN_run2.out); zerobas left A = $0D,
                ; F = $21. Cy was already right.
                xor     a
                scf
                ret

; nsx_px -- D-SETCLAST part 2 + D-NSETCXFULL (2026-11-19): NSETCX ($0123) decides each pattern
; byte WHOLE on the VG-8020 (docs/bios/NSETCX.md R-NX-VRAM): the run's pixels in a byte are one
; mask M, and SETC's rule applies with M for CMASK -- ATRBYT the background: M's bits cleared; the
; foreground: set; pattern OR M = $FF: cleared, ATRBYT ORed into (colour AND $F0); else set,
; ATRBYT the foreground. All 8 pixels (M = $FF): pattern $00 and colour byte := ATRBYT, at CLOC
; XOR $2000 (cases 12, 13). zerobas's SETC takes a multi-bit CMASK as it is (setc_col,
; basic/main.asm). Entered from our repacked NSETCX's per-pixel `call setc` at $07FB
; (basic/islands.asm `cbios_nsx_px`) with HL = the pixels left, this one included, and CLOC /
; CMASK on this pixel; it does the run's pixels in this byte and leaves HL / CMASK on their last,
; so nsetcx's own `call rightc / dec hl` steps past them. SCREEN 3 (nibbles): SETC per pixel, as
; before. BC / DE are free here (nsetcx keeps neither). Page 0: a caller's page 1 may be RAM.
BIOS_SETC       equ     $0120
nsx_px:
                ld      a,(SCRMOD)
                cp      2
                jp      nz,BIOS_SETC
                ld      a,(CMASK)
                ld      c,a                 ; C: the pixel, B: the mask so far
                ld      b,a
nsx_lp:
                bit     0,c
                jr      nz,nsx_go           ; the byte's last pixel
                ld      a,h
                or      a
                jr      nz,nsx_more
                ld      a,l
                dec     a
                jr      z,nsx_go            ; the run's last pixel
nsx_more:
                srl     c
                ld      a,b
                or      c
                ld      b,a
                dec     hl
                jr      nsx_lp
nsx_go:
                ld      a,b
                inc     a
                jr      z,nsx_full          ; all 8 pixels
                dec     a
                ld      (CMASK),a
                call    BIOS_SETC           ; BC / DE / HL kept
nsx_end:
                ld      a,c
                ld      (CMASK),a           ; on the run's last pixel in this byte
                ret
nsx_full:
                push    hl
                ld      hl,(CLOC)
                xor     a
                call    WRTVRM              ; the pattern byte: $00
                ld      a,h
                xor     $20
                ld      h,a
                ld      a,(ATRBYT)
                call    WRTVRM              ; the colour byte: ATRBYT, whole
                pop     hl
                jr      nsx_end

; bios_isflio -- ISFLIO ($014A). D-ISFLIO (2026-11-19): the VG-8020 returns A = PTRFIL ($F864)'s
; two bytes ORed -- non-zero exactly when a file is the I/O target -- with that OR's flags, BC / DE /
; HL kept (docs/bios/ISFLIO.md R-IF-A / R-IF-F / R-IF-KEEP). C-BIOS's looked at the low byte only,
; so a file whose FCB sits at $xx00 read as "no file". Page 0: a caller's page 1 may be RAM.
bios_isflio:
                push    hl
                ld      hl,(PRDEST)         ; PTRFIL, both bytes (zerobas writes only the low one)
                ld      a,h
                or      l
                pop     hl
                ret

; bios_clrspr -- CLRSPR ($0069). D-CLRSPRR1 / D-CLRSPRMODE / D-CLRSPRORDER / D-CLRREGS
; (2026-11-19), as the VG-8020 (docs/bios/CLRSPR.md): VDP R#1 := RG1SAV; the sprite pattern
; table (2 KB from PATBAS) := 0 FIRST, then the 32 attribute entries from ATRBAS -- Y $D1 in
; every SCRMOD (SCREEN 0 too), X not written, pattern k (4 x k with 16 x 16 sprites), colour
; FORCLR as it is. On return A = E = FORCLR, D kept, BC = $0020 / $0080, HL = ATRBAS + $80,
; F as the loop's last GSPSIZ / `inc c` leaves it, interrupts on. C-BIOS's returned at once in
; SCREEN 0, wrote Y $D9 above SCREEN 3, cleared the patterns last and left R#1 alone. Page 0.
bios_clrspr:
                ld      a,(RG1SAV)
                ld      b,a
                ld      c,1
                call    WRTVDP              ; R#1 := RG1SAV
                ld      hl,(PATBAS)
                ld      bc,2048
                xor     a
                call    FILVRM              ; the patterns first
                ld      hl,(ATRBAS)
                call    SETWRT
                ld      a,(FORCLR)
                ld      e,a
                ld      bc,$2000            ; B = 32 entries, C = the pattern number
                di
bcs_lp:
                ld      a,$D1
                out     ($98),a             ; Y
                nop                         ; >= 29 T between VRAM accesses (MSX1)
                nop
                nop
                nop
                in      a,($98)             ; X: kept
                ld      a,c
                nop
                nop
                nop
                out     ($98),a             ; the pattern number
                inc     c
                call    GSPSIZ              ; C set: 16 x 16, 4 numbers a sprite
                jr      nc,bcs_8
                inc     c
                inc     c
                inc     c
bcs_8:
                ld      a,e
                out     ($98),a             ; the colour: FORCLR
                inc     hl                  ; HL steps with the entry (flags kept)
                inc     hl
                inc     hl
                inc     hl
                djnz    bcs_lp
                ld      a,e
                ei
                ret
