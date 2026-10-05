; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; basic/edscreen.asm -- the screen editor's cell helpers, in MAIN's LOW region
; (D-EDCTRL, 2026-10-05). Moved verbatim from sub/readline.asm, where the
; readline tenant (sub page 1) still calls them through the resident ABI
; (tools/gen_resident_abi.py REQUIRED_SUB): page 0 stays mapped while a page-1
; tenant runs, so a low-region routine is callable from both sides. Main's own
; editing keys use them too -- one copy of the screen arithmetic, not two.
; CLEAN-ROOM: original code; NAMBAS/LINLEN/SCRMOD/CRTCNT/CSRY/LINTTB are
; documented MSX work-area cells and RDVRM/WRTVRM BIOS entries (MSX2 Technical
; Handbook). No reference-ROM disassembly.

; --- rl_vpeek: A = the screen character at row B, column C (both 1-based) ----
; The name table is NAMBAS + (row-1)*stride + margin + (col-1); the stride is
; the mode's (40 in SCREEN 0, 32 in SCREEN 1), not LINLEN, and the margin centres
; the LINLEN-wide window in it (see rl_vcol). Preserves BC, DE.
rl_vpeek:
                push    bc
                push    de
                call    rl_vaddr
                call    RDVRM               ; A = VRAM byte at HL (BIOS)
                pop     de
                pop     bc
                ret

; --- rl_vpoke: the screen character at row B, column C := A. Preserves BC, DE. -
rl_vpoke:
                push    bc
                push    de
                push    af
                call    rl_vaddr
                pop     af
                call    WRTVRM
                pop     de
                pop     bc
                ret

; --- rl_vaddr: HL = the name-table address of row B, column C. Clobbers A,B,DE.
rl_vaddr:
                ld      a,(SCRMOD)
                or      a
                ld      e,40
                jr      z,rl_stride
                ld      e,32
rl_stride:
                ld      d,0
                ld      hl,(NAMBAS)
                dec     b
                jr      z,rl_vcol
rl_vrow:
                add     hl,de
                djnz    rl_vrow
rl_vcol:
                ; The text window is CENTRED in the name table: column 1 sits at
                ; index (stride + 1 - LINLEN) / 2 -- measured: 1 at WIDTH 39 on
                ; C-BIOS (the prompt row reads `| ZB` with CSRX = 3), and the
                ; VG-8020's captures show two blanks at its default 37. 0 at 40.
                ld      a,e                 ; the stride
                inc     a
                ld      e,a
                ld      a,(LINLEN)
                ld      d,a
                ld      a,e
                sub     d                   ; stride + 1 - LINLEN
                srl     a                   ; the left margin
                add     a,c
                dec     a                   ; + (col - 1)
                ld      e,a
                ld      d,0
                add     hl,de
                ret

; --- rl_lastrow: B = the last row of the logical line that holds the cursor ----
; Walks down while LINTTB says the row continues (0), never past the bottom row.
; Clobbers A, DE, HL.
rl_lastrow:
                ld      a,(CSRY)
                ld      b,a
rl_lr_lp:
                ld      a,(CRTCNT)
                cp      b
                ret     z                   ; the bottom row ends every line
                ld      hl,LINTTB-1
                ld      e,b
                ld      d,0
                add     hl,de               ; LINTTB[row-1]
                ld      a,(hl)
                or      a
                ret     nz                  ; this row ends the line
                inc     b
                jr      rl_lr_lp
