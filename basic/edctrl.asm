; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; basic/edctrl.asm -- the screen editor's CTRL editing keys (D-EDCTRL part 2)
; CTRL-B / CTRL-E / CTRL-F / CTRL-N / CTRL-U, handled in MAIN before a key goes
; to the sub-ROM readline tenant (basic/repl.asm rl_get). Each behaviour below
; is the VG-8020's, MEASURED (scratchpad/edctrl_probe.py), not the manual's:
;   CTRL-E  blank from the cursor to the end of the LOGICAL line; each row of
;           that tail now ends a line (LINTTB); the cursor stays.
;   CTRL-U  the same from the line's start: column 1 of its first row, or the
;           column input began on if that row is the input row (INPUT keeps its
;           `? `) -- the FSTPOS rule rl_enter reads the line back with.
;   CTRL-B  to the start of the previous word; CTRL-F to the start of the next.
;           A word is a run of letters and digits (`A,B.CD EF` steps E -> C -> B).
;           Both scan the WHOLE SCREEN, not the logical line: CTRL-B from a
;           line's first column lands on the `Ok` above it, and CTRL-F with no
;           word ahead stops on the last cell of the text window.
;   CTRL-N  to just past the last non-blank character of the logical line --
;           column 1 of the next row when that character ends a full row.
;   All five end insert mode (INSFLG := 0).
; The cell arithmetic is basic/edscreen.asm's (rl_vpeek/rl_vpoke/rl_lastrow),
; the same code the readline tenant calls. Coordinates are 1-based (row B,
; column C), as CSRY/CSRX are.
; CLEAN-ROOM: original code over documented work-area cells (CSRX, CSRY, LINLEN,
; CRTCNT, LINTTB, INSFLG) and the RDVRM/WRTVRM BIOS entries. No reference-ROM
; disassembly; the behaviours are black-box readings of the screen and RAM.

; --- ek_ctrl: A = the key. Z = handled (main skips the tenant), NZ = not ours --
ek_ctrl:
                cp      2
                jr      z,ek_b
                cp      5
                jr      z,ek_e
                cp      6
                jr      z,ek_f
                cp      14
                jp      z,ek_n              ; jp: past jr's reach
                cp      21
                ret     nz                  ; not an editing key: the tenant's
                ; --- CTRL-U: to the line's start, then CTRL-E's erase ---
                call    ek_firstrow         ; B = the logical line's first row
                ld      a,(RL_ROW0)
                cp      b
                ld      c,1
                jr      nz,eku_at
                ld      a,(RL_COL0)         ; the input row: input's own column
                ld      c,a
eku_at:
                call    ek_setcsr
                jr      ek_erase
ek_e:
                call    ek_getcsr
ek_erase:                                   ; blank (B,C) .. the line's end
                push    bc
                call    rl_lastrow          ; B = the line's last row (from CSRY)
                ld      d,b                 ; D = that row
                pop     bc
                push    bc                  ; the first row we touch, for LINTTB
eke_lp:
                ld      a,' '
                call    rl_vpoke
                ld      a,b
                cp      d
                jr      nz,eke_step
                ld      a,(LINLEN)
                cp      c
                jr      z,eke_marks         ; (D, LINLEN) blanked: done
eke_step:
                call    ek_next
                jr      nc,eke_lp
eke_marks:
                pop     bc                  ; B = the first row touched
eke_mlp:
                ld      hl,LINTTB-1
                ld      a,b
                call    ek_hladd            ; HL = LINTTB[row-1]
                ld      (hl),1              ; this row ends a line now
                ld      a,b                 ; the row just marked
                inc     b
                cp      d                   ; AFTER the inc: `inc` sets Z itself, so
                jr      nz,eke_mlp          ; cp-then-inc ran B round to 0, writing 1
                                            ; over LINTTB..$FCB0 -- SCRMOD, INSFLG
                                            ; and all (caught by the edctrl probe)
                jr      ek_done
ek_f:
                call    ek_getcsr
ekf_word:                                   ; skip the word the cursor is in
                call    ek_isword
                jr      nc,ekf_gap
                call    ek_next
                jr      nc,ekf_word
                jr      ek_set              ; the screen ended
ekf_gap:                                    ; skip what separates it
                call    ek_isword
                jr      c,ek_set            ; the next word starts here
                call    ek_next
                jr      nc,ekf_gap
                jr      ek_set              ; the screen ended: its last cell
ek_b:
                call    ek_getcsr
                call    ek_prev
                jr      c,ek_set            ; (1,1): nowhere to go
ekb_gap:
                call    ek_isword
                jr      c,ekb_word
                call    ek_prev
                jr      nc,ekb_gap
                jr      ek_set
ekb_word:
                call    ek_prev
                jr      c,ek_set            ; the word starts at (1,1)
                call    ek_isword
                jr      c,ekb_word
                call    ek_next             ; one past the word's first cell: back
                jr      ek_set
ek_n:
                call    rl_lastrow          ; B = the line's last row (clobbers DE)
                push    bc
                call    ek_firstrow         ; B = its first row
                ld      e,b                 ; E = the line's first row
                pop     bc                  ; B = its last row again
                ld      a,(LINLEN)
                ld      c,a
ekn_lp:
                call    rl_vpeek
                cp      ' '
                jr      nz,ekn_hit
                call    ek_prev
                jr      c,ek_set
                ld      a,b
                cp      e
                jr      nc,ekn_lp           ; still inside the line
                ld      b,e                 ; an empty line: its first row, column 1
                ld      c,1
                jr      ek_set
ekn_hit:
                call    ek_next             ; just past it (column 1 of the next row
                                            ; when it ended a full row)
ek_set:
                call    ek_setcsr
ek_done:
                xor     a
                ld      (INSFLG),a          ; every editing key ends insert mode
                ret                         ; Z: handled

; --- ek_isword: CF iff the cell at (B,C) is a letter or a digit ---------------
ek_isword:
                call    rl_vpeek
                cp      '0'
                ccf
                ret     nc                  ; below '0'
                cp      '9'+1
                ret     c                   ; a digit
                and     $DF                 ; fold the case
                cp      'A'
                ccf
                ret     nc
                cp      'Z'+1
                ret                         ; CF iff A..Z

; --- ek_next / ek_prev: one cell on, across rows; CF = the window's end -------
; (B,C) unchanged when CF is set.
ek_next:
                ld      a,(LINLEN)
                cp      c
                jr      z,ekx_row
                inc     c
                or      a
                ret
ekx_row:
                ld      a,(CRTCNT)
                cp      b
                scf
                ret     z                   ; the last cell of the window
                inc     b
                ld      c,1
                or      a
                ret
ek_prev:
                ld      a,c
                dec     a
                jr      z,ekp_row
                ld      c,a
                or      a
                ret
ekp_row:
                ld      a,b
                dec     a
                scf
                ret     z                   ; (1,1)
                ld      b,a
                ld      a,(LINLEN)
                ld      c,a
                or      a
                ret

; --- ek_firstrow: B = the first row of the logical line that holds the cursor --
ek_firstrow:
                ld      a,(CSRY)
                ld      b,a
ekfr_lp:
                ld      a,b
                dec     a
                ret     z                   ; row 1 starts every line
                ld      hl,LINTTB-2
                ld      a,b
                call    ek_hladd            ; HL = LINTTB[row-2], the row above
                ld      a,(hl)
                or      a
                ret     nz                  ; the row above ended its line
                dec     b
                jr      ekfr_lp

ek_hladd:                                   ; HL += A
                add     a,l
                ld      l,a
                ret     nc
                inc     h
                ret
ek_getcsr:
                ld      a,(CSRY)
                ld      b,a
                ld      a,(CSRX)
                ld      c,a
                ret
ek_setcsr:
                ld      a,b
                ld      (CSRY),a
                ld      a,c
                ld      (CSRX),a
                ret
