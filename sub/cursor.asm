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
; Clean room (PROVENANCE.md): the behaviour was measured on the reference's VRAM
; and work-area RAM only -- no reference ROM byte was read or disassembled. The
; table-base cells (TXTNAM/TXTCGP/T32NAM/T32CGP) are the published MSX work
; area; the border rule is C-BIOS's own (a BSD peer this project patches).
cursor_tenant:
                ld      a,e
                or      a
                jp      z,ct_off
                ld      a,(CSR_ON)
                or      a
                ret     nz                  ; already shown
                ld      a,(SCRMOD)
                cp      2
                ret     nc                  ; not a text mode: no cursor
                ; name base, pattern base and row pitch for the mode
                ld      hl,(TXTNAM)
                ld      de,(TXTCGP)
                ld      c,40
                or      a
                jr      z,ct_geom
                ld      hl,(T32NAM)
                ld      de,(T32CGP)
                ld      c,32
ct_geom:
                push    de                  ; [cgp]
                ; + (CSRY-1) * pitch
                ld      a,(CSRY)
                dec     a
                ld      b,0
                jr      z,ct_row_done
ct_row:
                add     hl,bc
                dec     a
                jr      nz,ct_row
ct_row_done:
                ; + the left border, (pitch - LINLEN + 1) / 2 (C-BIOS's own rule)
                ld      a,(LINLEN)
                neg
                add     a,c
                inc     a
                srl     a
                ld      c,a
                add     hl,bc
                ; + CSRX - 1
                ld      a,(CSRX)
                dec     a
                ld      c,a
                add     hl,bc               ; HL = the cursor cell
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
                ld      a,(INSFLG)
                ld      c,a                 ; C = $FF in insert mode, else 0
                ld      b,8
ct_copy:
                call    RDVRM
                ; D-INSMODE: in insert mode only pattern rows 5..7 are inverted --
                ; rows 0..4 keep the glyph (the VG-8020, INSFLG 255: `rows=====iii`)
                push    af
                ld      a,b
                cp      4                   ; B = 8..4 are rows 0..4
                jr      c,ct_inv
                ld      a,c
                or      a
                jr      z,ct_inv
                pop     af                  ; insert mode, rows 0..4: as-is
                jr      ct_put
ct_inv:
                pop     af
                cpl                         ; every byte inverted, as measured
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
ct_off:
                ld      a,(CSR_ON)
                or      a
                ret     z                   ; nothing shown
                xor     a
                ld      (CSR_ON),a
                ld      hl,(CSR_ADDR)
                ld      a,(CSR_CHAR)
                jp      WRTVRM              ; the character comes back
