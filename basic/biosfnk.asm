; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

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

; FNKSB ($00C9) -- D-BIOSRUNG (2026-11-12). C-BIOS's was a print_debug stub. Measured on
; the VG-8020 with CNSDFG changed BEHIND BASIC's back (scratchpad/fnksb_probe.py,
; fnksb_run*.out): KEY OFF + CNSDFG := $FF -> the key row PAINTED (a KILBUF call in its
; place leaves it blank: FNKSB did it), with DSPFNK's registers exactly (HL kept, DE
; $FC40, BC 0, A 0 -- biosregs' dsp0 row); KEY ON + CNSDFG := 0 -> nothing, A = 0
; (CNSDFG's value, not the caller's). So: CNSDFG != 0 -> DSPFNK.

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
; leaves it, else +1, saturating at 255). A failing LPTOUT is BASIC's Device I/O error, as the
; VG-8020's (D-LPTSTOP). The graphic characters and a non-MSX printer: below.
; D-OUTDLPGRAPH / D-OUTDLPF (2026-11-19), docs/bios/OUTDLP.md R-OD-PRN / R-OD-POS / R-OD-A /
; R-OD-F: a graphic character's $01 does not move LPTPOS (on any printer); on a printer that is
; not an MSX one (NTMSXP, $F417, not 0) the $01 is held back -- A 1, F $42 -- and the next code,
; if $40-$5F, goes out as one space (A $20), any other as it is. F is LPTOUT's on the byte sent
; (its AND flags), as on entry after a TAB. The held $01 is GRPHED ($FCA6) := 1, where the VG-8020
; and the CF-3300 keep it -- the same flag as the GRP: channel's pending header and CNVCHR's
; (D-PAINTRAMCLASH, scratchpad/OUTDLPHOLD_run1.out); a PRINT # to GRP in between consumes it.
NTMSXP          equ     $F417
bios_outdlp:
                push    hl
                push    af                  ; A / F as on entry (a TAB returns them)
                ld      hl,GRP_HDR
                cp      9
                jr      z,odl_tab
                pop     af
                bit     0,(hl)
                ld      (hl),0              ; (GRPHED is 0 or 1: every writer stores the byte)
                jr      z,odl_nh            ; no $01 held
                cp      $40
                jr      c,odl_nh            ; held $01 + a code outside $40-$5F: as it is
                cp      $60
                jr      nc,odl_nh
                ld      a,' '               ; a graphic code, to a non-MSX printer: a space
                jr      odl_send
odl_nh:
                cp      1
                jr      nz,odl_send
                ld      a,(NTMSXP)
                or      a
                ld      a,1
                jr      z,odl_lpt           ; an MSX printer: $01 goes out, uncounted
                ld      (hl),1              ; else held back for the next byte
                ld      hl,$0142
                push    hl
                pop     af                  ; A 1, F $42
                pop     hl
                ret
odl_send:
                call    odl_put
                pop     hl
                ret
odl_lpt:
                call    LPTOUT
                jr      c,odl_fail
                pop     hl
                ret
; odl_put: A to the printer, LPTPOS moved (CR -> 0, LF kept, else +1, saturating at 255).
; Out: A as sent, F LPTOUT's.
odl_put:
                call    LPTOUT
                jr      c,odl_fail
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
                ld      a,19                ; Device I/O error
                jp      raise_error
odl_tab:                                    ; (stack: the entry AF, HL)
odl_tlp:
                ld      a,' '
                call    odl_put
                ld      a,(LPTPOS)
                and     7
                jr      nz,odl_tlp
                pop     af                  ; A 9, F as on entry
                pop     hl
                ret

; BREAKX ($00B7) -- D-BRKLATCH (2026-11-12). C-BIOS's body reads CTRL+STOP; on the
; VG-8020 a press BREAKX has seen does not ALSO reach the interrupt's latch -- after
; LPTOUT's CTRL-STOP abort INTFLG reads 0, and 0 ten frames later, the key still down
; (scratchpad/BL_lptintflg.out); only the auto-repeat latches it later (from 36 frames).
; C-BIOS latches INTFLG only for a key the scan sees as NEWLY down against OLDKEY (or a
; repeat), so marking STOP down in OLDKEY consumes the press the same way. CF / A as
; C-BIOS's body leaves them.


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
; were bare `ret`s. SCANL / SCANR's body is the sub-ROM's paint tenant (sub/paintbios.asm,
; which carries the VG-8020's measured behaviour); here only the op in C. PNTINI is below. Each `db $21` is an `ld hl,nn` that swallows the next entry's `ld c,n` -- HL is
; an input to none of the three. IX kept, as bios_beep.
; D-PNTINIREGS (2026-11-19): PNTINI is answered HERE, not by the tenant: BDRATR (GFX_B) :=
; ATRBYT in SCREEN 2 -- A := ATRBYT, F an AND's flags -- else := A, A kept, F as CP $10 + CCF
; leave it; BC, DE, HL and the interrupt state kept (docs/bios/PNTINI.md R-PI-BDR / R-PI-AF /
; R-PI-KEEP). The tenant set BC and HL, enabled interrupts, and took ATRBYT in SCREEN 0 / 1 too.

; GRPPRT ($008D): basic/islands.asm bios_grpprt (island 3; D-GRPPRTPOS and kin, 2026-11-19).

; STRTMS ($0099) -- D-BIOSRUNG / STRTMS (2026-11-12). C-BIOS's was a print_debug stub.
; Measured on the VG-8020 (scratchpad/strtms_run*.out, plycnt_run.out): PLYCNT counts
; PLAY statements queued and not yet started; STRTMS with MUSICF != 0 or PLYCNT = 0 does
; nothing, else st_go: PLYCNT - 1 and MUSICF := 7 -- all three voices fetch on. The same
; code is PLAY's start (st_go, from the parser tenant, sub/playparse.asm) and the
; servicer's sync, where every voice has reached its end marker (basic/playsvc.asm).
; st_go sits in island 1 (basic/islands.asm): this pad and the low region had no room
; for both halves (switch-build-check: the switch-off builds overran the low region).
; Registers as the VG-8020's (D-STRTMS, docs/bios/STRTMS.md R-ST-REGS): playing -- A = MUSICF,
; F its OR flags, HL kept; nothing waiting -- A 0, F $44, HL = PLYCNT ($FB40); started -- A 7,
; F the flags DEC leaves on PLYCNT (st_go's), HL 1, and each voice's first word ($FB41, $FB66,
; $FB8B) := 1 (R-ST-PLAY; zerobas's PLAY keeps nothing in a VCB's bytes 0-1).
; st_start: the start itself -- also PLAY's (the parser's st_go, basic/islands.asm, jumps
; here) and the player's next round. PLYCNT - 1 (F as DEC leaves it), MUSICF := 7, A = 7,
; and each voice's first word := 1: the player's counter, so every voice reads its
; first packet on the next frame. HL = 1; B, C, D, E, IX, IY kept.
st_start:
                ld      hl,PLYCNT
                dec     (hl)
                ld      a,7
                ld      (MUSICF),a
                ld      hl,1
                ld      (VCBA),hl
                ld      (VCBB),hl
                ld      (VCBC),hl
                ret

; PUTQ ($00F9) -- A = the queue (0..2), E = the byte. C-BIOS's writes at PUT and then
; steps it; the VG-8020's steps FIRST (three bytes land at VOICAQ+1..3, PUT 3), as its
; rings are read (scratchpad/strtms_run4.out). A full queue: Z, nothing written, B / C
; the old / new PUT, HL the entry + 3. Stored: HL = the descriptor, BC = the new PUT,
; A = the buffer's low byte, Z / C clear, DE kept -- as the VG-8020.

; D-BEEPRESET (2026-11-19): the VG-8020's BEEP ends with GICINI's reset -- R7 $B8, the volumes
; 0, the queues and MUSICF / PLYCNT -- and returns A 0, F $44, BC 0, E 7, D and HL kept
; (docs/bios/BEEP.md R-BP-PSG / R-BP-REGS; the voice buffers' bytes are D-GICINIVCB's).

; PINLIN ($00AE) / INLIN ($00B1) / QINLIN ($00B4): C-BIOS's INLIN is a skeleton --
; its Return handler is a bare `ret` back into the key loop, so a program calling
; any of the three HUNG (scratchpad/biossweep_b6.out: "AB" echoed, never returned).
; The VG-8020 returns the line in BUF, 0-terminated, HL = BUF - 1, A = $0D; QINLIN
; prints "? " first. BASIC's own line editor (read_line, basic/repl.asm -- the
; prompt's and INPUT's: screen editing, Enter reads the logical line) does the
; work; it is MAIN PAGE 1, so page 1 is mapped to primary slot 0 for the call and
; the caller's layout put back after (htimi_guard's way). CF = Ctrl-STOP as
; read_line reports it. PINLIN's AUTO handling is BASIC's own (repl), not here.
; INLIN / QINLIN hand read_line to the shared tail; PINLIN's entry (bios_pinlin, basic/main.asm
; at the low region's end: this file's pad in front of the $3283 pin is full) hands
; read_line_col1 (D-PINLINSTART, docs/bios/PINLIN.md R-L-PIN).
BIOS_SETC       equ     $0120
BIOS_UPC        equ     $0102
BIOS_DOWNC      equ     $0108
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

; bios_mapxyc -- MAPXYC ($0111). D-MAPXYCBASE / D-MAPXYCWRAP / D-MAPXYCMODE / D-MAPXYCF
; (2026-11-19), as the VG-8020 (docs/bios/MAPXYC.md), X in C and Y in E (B and D play no part):
;   SCRMOD 2: CLOC := GRPCGP + (Y AND $F8) x 32 + (X AND $F8) + (Y AND 7), CMASK := $80 >> (X AND 7),
;     A := the offset's low byte, D := X;
;   any other SCRMOD: CLOC := MLTCGP + ((Y >> 3) AND 7) x 256 + ((X >> 1) AND 31) x 8 + (Y AND 7),
;     CMASK := $F0 / $0F for an even / odd X, A := (Y >> 3) AND 7.
; F: S / Z / P/V from A, then `add hl,de` adds the base -- H the carry out of bit 11, C out of bit
; 15, bits 5 / 3 from CLOC's high byte, N clear -- exactly the reference's. HL := CLOC, BC kept, DE
; kept (but D), the interrupt state kept. C-BIOS's left the base out, did not wrap Y in SCREEN 3,
; took the SCREEN 2 way for SCRMOD 0 / 1 and left other flags. Page 0.

; bios_scalxy -- SCALXY ($010E). D-SCALXYMODE / D-SCALXYF (2026-11-19), as the VG-8020
; (docs/bios/SCALXY.md): BC (X) and DE (Y) clipped as signed 16-bit numbers to 0..255 / 0..191,
; then, with SCRMOD other than 2, both divided by 4. The carry set and A $80 when neither was
; clipped, clear and $00 when either was; the other flags: SCREEN 2 Z alone; otherwise Z and P/V
; from the new E, the rest clear. A / F are built in HL and popped, which also restores HL; IX,
; IY and the interrupt state are kept. C-BIOS's divided only in SCREEN 3 and left SCREEN 2's
; flags there. Page 0.

; bios_nsetcx -- NSETCX ($0123). D-NSETCX0 / D-NSETCXL (2026-11-19), as the VG-8020
; (docs/bios/NSETCX.md): outside SCREEN 2 the count is L alone, L = 0 giving 256 (HL $0102 sets 2);
; in SCREEN 2 HL = 0 still takes the byte at CLOC through SETC's steps with no bit -- SETC with
; CMASK 0 (the colour into the background nibble when the pattern byte is $FF, else the foreground,
; unless ATRBYT is one already there), CLOC / CMASK kept, interrupts on after. Every other case
; C-BIOS's own body (CBIOS_NSETCX, from C-BIOS's symbol table: basic/cbios-abi.inc), whose per-pixel
; `call setc` is nsx_px (above). C-BIOS's returned at once for HL = 0 and counted all of HL. Page 0.
