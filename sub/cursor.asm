; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; cursor_tenant -- the line editor's BLOCK CURSOR (D-CURSORBLOCK, 2026-09-26).
;
; Joost, watching zerobas beside the VG-8020: *"zerobas doesn't show the square
; rect prompt indication"*. Measured (scratchpad/cursorblock_probe.py), VRAM and
; RAM only: while the VG-8020 waits for a key in its line editor -- at the
; prompt, mid-line, in INPUT, in SCREEN 1 -- the name-table cell at CSRY/CSRX
; holds character 255, and character 255's pattern is the glyph that was UNDER
; it with all 8 bytes inverted (`B` = F0 48 48 70 48 48 F0 00 gives
; 0F B7 B7 8F B7 B7 0F FF; a space gives FF x8). zerobas showed nothing: its
; wait is C-BIOS's CHGET, which draws no cursor. CSRSW reads 0 on both machines
; at the prompt, so the reference's editor draws the cursor itself and leaves
; the published cell alone -- so does this.
;
; E = 1: show the cursor at CSRY/CSRX; E = 0: remove it. In insert mode
; (INSFLG set, D-INSMODE) the cursor is the bottom three rows only. Both are idempotent
; (CSR_ON), so a path that removes twice, or never showed it, writes nothing.
; SCREEN 0 and 1 only: the line reader switches a graphics mode to text first
; (txt_mode), so any other mode here draws nothing rather than guess a layout.
; PAGE 1 because it calls the BIOS VRAM entries, which live in page 0.
;
; 🔴 THE CELL IS NAMBAS-BASED, NOT TXTNAM/T32NAM (D-CURGEO, measured 2026-11-04,
; probes/basic/basic_probe_curgeo.py, `make curgeo-acceptance`). POKE TXTNAM to
; $1000 (SCREEN 0) or T32NAM to $1400 (SCREEN 1) without a SCREEN statement and
; BOTH references -- VG-8020 and CF-3300 -- go on drawing the cursor (and PRINT)
; in the table NAMBAS names, the one on screen; the POKEd table stays clean.
; This tenant used to compute the cell from TXTNAM/T32NAM, so after that POKE it
; showed NO cursor and wrote a stray $FF into a table nobody displays. It now
; takes the cell from rl_vaddr (basic/edscreen.asm, the same arithmetic every
; line-editor read uses) -- a fidelity fix that also gave sub page 1 33 B.
; The PATTERN base is still TXTCGP/T32CGP; the probe does not measure that half.
;
; Clean room (PROVENANCE.md): the behaviour was measured on the reference's VRAM
; and work-area RAM only -- no reference ROM byte was read or disassembled. The
; table-base cells (NAMBAS/TXTCGP/T32CGP) are the published MSX work area; the
; border rule is C-BIOS's own (a BSD peer this project patches).
cursor_tenant:
                ld      a,e
                or      a
                ld      a,(CSR_ON)          ; (no flags: ct_off tests it itself)
                jr      z,ct_off
                or      a
                ret     nz                  ; already shown
                ld      a,(SCRMOD)
                cp      2
                ret     nc                  ; not a text mode: no cursor
                ; the pattern base for the mode; the CELL is NAMBAS-based (header)
                ld      de,(TXTCGP)
                or      a
                jr      z,ct_geom
                ld      de,(T32CGP)
ct_geom:
                push    de                  ; [cgp]
                call    ek_getcsr           ; B = CSRY, C = CSRX (sub2/edctrl.asm)
                call    rl_vaddr            ; HL = NAMBAS + (row-1)*pitch + border +
                                            ; (col-1) -- the cell the line editor
                                            ; reads (basic/edscreen.asm; clobbers
                                            ; A, B, DE)
                ld      (CSR_ADDR),hl
                call    RDVRM               ; A = the character under the cursor
                ld      (CSR_CHAR),a
                ; source = cgp + char*8, destination = cgp + 255*8
                pop     de                  ; DE = cgp   [ ]
                ld      l,a
                ld      h,0
                add     hl,hl
                add     hl,hl
                add     hl,hl
                add     hl,de               ; HL = the glyph under the cursor
                push    hl
                ld      hl,255*8
                add     hl,de
                ex      de,hl               ; DE = character 255's pattern
                pop     hl
                ; D-INSMODE: in insert mode only pattern rows 5..7 are inverted --
                ; rows 0..4 keep the glyph (the VG-8020, INSFLG 255: `rows=====iii`).
                ; C = the rows still to copy AS-IS: 5 in insert mode ($FF and 5),
                ; else 0.
                ld      a,(INSFLG)
                and     5
                ld      c,a
                ld      b,8
ct_copy:
                call    RDVRM
                inc     c
                dec     c                   ; Z iff no as-is rows are left (A kept)
                jr      z,ct_inv
                dec     c
                jr      ct_put
ct_inv:
                cpl                         ; inverted, as measured
ct_put:
                ex      de,hl
                call    WRTVRM
                ex      de,hl
                inc     hl
                inc     de
                djnz    ct_copy
                ld      hl,(CSR_ADDR)
                ld      a,255
                call    WRTVRM              ; the cell shows character 255
                ld      a,1
                ld      (CSR_ON),a
                ret
ct_off:                                     ; A = CSR_ON, loaded at the top
                or      a
                ret     z                   ; nothing shown
                xor     a
                ld      (CSR_ON),a
                ld      hl,(CSR_ADDR)
                ld      a,(CSR_CHAR)
                jp      WRTVRM              ; the character comes back
