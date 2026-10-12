; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; basicrom.asm -- D-BASICROM: a BASIC-PROGRAM CARTRIDGE runs at boot.
; The MSX cartridge header is published: `AB` at the ROM's start, then the INIT,
; STATEMENT, DEVICE and TEXT words; a non-zero TEXT is a tokenised BASIC program
; in the cartridge, which BASIC runs at boot. MEASURED on the VG-8020 with our own
; synthetic cartridge (scratchpad/basicrom_synth.out) and with Vampier's report,
; 3D Golf Simulation (scratchpad/basicrom_golf.out, run, never decoded):
;   * the cartridge stays mapped in PAGE 2 for good;
;   * TXTTAB = TEXT + 1 (the program's first line; TEXT holds its 0 byte);
;   * the variables start at $C000 (VARTAB), the first byte past the ROM;
;   * it runs in SCREEN 1 at WIDTH 29 -- no SCREEN 0 header first -- and at END
;     the prompt follows, the program still LIST-able from the ROM.
; zerobas booted to its own prompt and never looked at TEXT.
; Clean-room: the header layout is the published cartridge format; the rest is
; black-box measurement. No reference ROM byte read. See basic/PROVENANCE.md.

; --- try_text_slot: is the slot just scanned a page-2 TEXT cartridge? --------
; Called first thing by try_init_slot (basic/islands.asm), so EVERY scanned slot
; is asked, expanded or not (the cartridge slots 1 and 2 are not). in: A = the
; slot id. Records the FIRST slot whose $8000 holds `AB` with a non-zero TEXT
; (BROM_SLOT / BROM_TEXT; init_ext_roms clears BROM_TEXT+1 before the scan --
; a TEXT is always $8000.., so a high byte of 0 means "none"). Preserves A.
try_text_slot:
                push    af
                ld      (SCAN_SLOT),a
                ld      a,(BROM_TEXT+1)
                or      a
                jr      nz,tts_done         ; the first one wins
                ld      hl,$8000
                call    rdslt_scan
                cp      'A'
                jr      nz,tts_done
                inc     hl
                call    rdslt_scan          ; (RDSLT preserves HL: rdslt_scan's note)
                cp      'B'
                jr      nz,tts_done
                ld      l,8                 ; $8008: TEXT
                call    rdslt_scan
                ld      e,a
                inc     hl
                call    rdslt_scan
                ld      d,a
                or      a                   ; high byte 0: no TEXT (or a bogus one)
                jr      z,tts_done
                ld      (BROM_TEXT),de
                ld      a,(SCAN_SLOT)
                ld      (BROM_SLOT),a
tts_done:
                pop     af
                ret

; --- brom_screen: the boot screen when a TEXT cartridge is present -----------
; out: Z = none (the caller shows its SCREEN 0 header as usual); NZ = one is
; present and the screen is already SCREEN 1 at width 29, as on the VG-8020.
brom_screen:
                ld      a,(BROM_TEXT+1)
                or      a
                ret     z
                ld      a,29
                ld      (LINL32),a
                call    INIT32              ; SCREEN 1, LINLEN := LINL32
                or      1                   ; NZ
                ret

; --- brom_run: map the cartridge into page 2 and RUN its program -------------
; Returns at once without one; otherwise RUNs it (run_prog's own return is the
; END, after which the boot goes on to the prompt as after AUTOEXEC.BAS).
brom_run:
                ld      a,(BROM_TEXT+1)
                or      a
                ret     z
                ld      a,(BROM_SLOT)
                ld      h,$80
                call    ENASLT              ; page 2 := the cartridge, for good
                ei
                ld      hl,(BROM_TEXT)
                inc     hl
                ld      (TXTTAB),hl         ; the program starts at TEXT + 1
                ld      hl,$C000-2
                ld      (PRGEND),hl         ; VARTAB = PRGEND + 2 = $C000 (measured)
                jp      run_prog
