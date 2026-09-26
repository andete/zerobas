; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; keystr.asm -- KEY n,"str" / KEY LIST / the function-key defaults, as a PAGE-0
; sub-ROM tenant (SUBROM_IDX_KEYSTR, D-KEYSTR 2026-09-10).
;
; Clean-room: own design. The ten default strings are a MEASUREMENT, not a
; transcription: scratchpad/keydef_probe.py PEEKs all 160 bytes of the
; function-key area ($F87F, stride 16, NUL-terminated -- itself measured by
; D-KEYSTR's scout) on the Philips VG-8020 and the National CF-3300 after a cold
; boot. The two agree on every byte except F6 (`color 15,4,4` vs `color
; 15,4,7`); the VG-8020 value ships on BOTH targets by Joost's standing style
; ruling (2026-09-04). Nothing here is derived from a disassembly or byte-copy
; of any reference ROM. Basis: basic/PROVENANCE.md.
;
; THREE OPERATIONS, selected by KEYARG (a page-3 cell, set by the caller):
;   0        cold boot: copy the 160-byte image to $F87F (basic/interp.asm init)
;   1..10    KEY n,"str": copy STRSCR's [len][bytes] (at most 15) into slot n,
;            NUL-terminated, the rest of the slot cleared. The caller has
;            already staged the string (fname_expr) and checked 1..10.
;   255      KEY LIST: render the ten slots into DETOKBUF, each up to its NUL,
;            each on its own line, control bytes as blanks (measured); the
;            resident side drains the buffer with print_string.
; PAGE-0 CLEAN: RAM in, RAM out; its only call is the sub-local pchar (the
; DETOKBUF appender), so nothing crosses to main at all. The resident side
; drains DETOKBUF with print_string after every op.
; Clobbers everything (tenant convention).
FNKSTR          equ     $F87F               ; measured base (D-KEYSTR scout)
; --- the function-key LINE (D-FNKLINE) --------------------------------------
; 🔬 THE LAYOUT IS MEASURED, read back as TEXT rather than counted
; (scratchpad/fnkline_probe.py), because a count cannot give column positions:
;   "  color  auto   goto   list   run       "   KEY ON, the defaults
;   "  ZQZQZQ auto   goto   list   run       "   after KEY 1,"ZQZQZQ"
; FIVE fields at columns 2, 9, 16, 23, 30 -- stride 7, each SIX wide. The
; ASSIGNED row is what pins the width: `ZQZQZQ` fills 2..7 exactly and `auto`
; still starts at 9, so the field is 6 and column 8 is the gap.
; ⚠️ ROW 23 IS `NAMBAS + 920` -- the SCREEN 0 name table is 40 bytes a row
; REGARDLESS of `LINLEN` (37 on the reference, 39 here), which is why stride-40
; arithmetic finds the labels on both. A fixed ABSOLUTE offset is the mistake
; D-KWOSK made in this exact place.
; ⚠️ A byte below 32 renders as a SPACE: the slot is NUL-filled past the string
; and F5's default carries a trailing CR, and the reference shows neither as a
; glyph (no measured cell read below 32).
FNK_ROW         equ     920                 ; row 23 within the name table
; 🖥️ D-KEYSCR1 (2026-09-26): SCREEN 1's row is 32 cells, MEASURED on the
; VG-8020 (VPEEK of row 23 at $1800+23*32): `··color·auto··goto··list··run···`.
FNK_ROW32       equ     736                 ; row 23 of a 32-column name table
; 🔑 D-KEYWIDTH (2026-09-26): THE GEOMETRY FOLLOWS `LINLEN`, NOT THE MODE. The
; stride-7/width-6 above (SCREEN 0) and pitch-6/width-5 (SCREEN 1) were two
; POINTS of one rule, both taken at the boot width. Swept on the VG-8020 at 24
; widths in both modes (scratchpad/keywidth_probe.py): the row starts at the
; text area's own left border, (row - LINLEN + 1) / 2 -- 0 at WIDTH 40, 2 at 37,
; 10 at 20 -- and a field's PITCH is (LINLEN + 1) / 5 with pitch-1 characters
; shown: 8 at 40 and 39, 7 at 38..36, 6 at 30/29, 5 at 25/24, 4 at 20 (`col aut
; got lis run`), 3 at 15, 2 at 10; at WIDTH 5 and 1 the row is BLANK. zerobas
; kept one layout per mode, so `WIDTH 20` still showed `color auto goto ...`.
FNK_FIELDS      equ     5                   ; F1..F5 are displayed; F6..F10 are not
KEYSLOTS        equ     10
KEYSTRIDE       equ     16
KEYMAX          equ     15                  ; measured truncation (D-KEYSCOUT2)

; ks_paint / ks_blank: draw or erase the function-key line.
; 🔴 VRAM FROM A PAGE-0 TENANT IS ALLOWED AND PRECEDENTED -- `gfx_vram_wr`
; (sub/graphics.asm, itself a page-0 tenant) is a page-local `call`, takes
; HL = address and C = byte, clobbers A only and preserves HL/BC/DE. A page-0
; tenant may NOT call the BIOS, so `WRTVRM`/`LDIRVM` are out; that is the whole
; reason the primitive matters here.
ks_paint:
                call    ks_blank            ; start from a clean row, so a macro
                                            ; that shortened leaves no tail
                call    ks_geom             ; HL -> row 23, column 0; C = row length
                ld      a,(LINLEN)
                ld      b,a                 ; B = LINLEN
                ld      a,c
                sub     b
                inc     a
                srl     a                   ; the left border, (row - LINLEN + 1) / 2
                ld      e,a
                ld      d,0
                add     hl,de               ; HL -> the first field
                ld      a,b
                inc     a                   ; LINLEN + 1 ...
                ld      c,-1
ksp_div:
                inc     c
                sub     5
                jr      nc,ksp_div          ; ... / 5 = the pitch, in C
                dec     c                   ; pitch - 1 = the characters shown
                ret     z                   ; pitch 1: nothing (WIDTH 5)
                ret     m                   ; pitch 0: nothing (WIDTH 1..3)
                ld      a,c                 ; A = field width
                ld      de,FNKSTR           ; DE -> slot 1
                ld      b,FNK_FIELDS
ksp_field:
                push    bc                  ; C is the data byte below
                push    de                  ; [n][slot]
                push    af                  ; [n][slot][width]
                ld      b,a
ksp_char:
                ld      a,(de)
                cp      ' '
                jr      nc,ksp_put
                ld      a,' '               ; NUL or a control byte -> blank
ksp_put:
                ld      c,a
                call    gfx_vram_wr
                inc     hl
                inc     de
                djnz    ksp_char
                inc     hl                  ; the one-column gap
                pop     af                  ; A = width      [n][slot]
                pop     de                  ; DE = this slot [n]
                push    hl                  ; DE = the next slot: a fixed stride,
                ld      hl,KEYSTRIDE        ; so the field width never enters it
                add     hl,de
                ex      de,hl
                pop     hl
                pop     bc
                djnz    ksp_field
                ret

; ks_geom -- the key row for the current text mode.
;   out: HL = row 23's first name-table cell, C = the row's length (what
;        ks_blank clears, and what the border is measured against). Clobbers
;        A, DE.
ks_geom:
                ld      hl,(NAMBAS)
                ld      a,(SCRMOD)
                dec     a
                ld      de,FNK_ROW
                ld      c,40
                jr      nz,ksg_have
                ld      de,FNK_ROW32
                ld      c,32
ksg_have:
                add     hl,de
                ret

ks_blank:
                call    ks_geom             ; HL -> row 23, column 0; C = length
                ld      b,c
ksb_lp:
                ld      c,' '
                call    gfx_vram_wr
                inc     hl
                djnz    ksb_lp
                ret

keystr_tenant:
                ; Every op leaves DETOKBUF printable for the resident drain:
                ; LIST fills it, the others leave it EMPTY (a lone NUL), so
                ; ex_key can drain unconditionally and spend no page-1 bytes on
                ; a branch.
                call    db_begin            ; D-DETOKBUF: the window; DB_SKIP is the
                                            ; resident loop's (KEY LIST re-runs)
                ld      (de),a              ; A = 0: an empty window until an op writes
                ld      a,(KEYARG)
                or      a
                jr      z,ks_defaults
                cp      255
                jr      z,ks_list
                cp      KEYOP_FNKPAINT
                jr      z,ks_paint
                cp      KEYOP_FNKBLANK
                jr      z,ks_blank
                ; --- KEY n,"str": slot address = FNKSTR + 16*(n-1) --------------
                dec     a
                ld      l,a
                ld      h,0
                add     hl,hl
                add     hl,hl
                add     hl,hl
                add     hl,hl               ; HL = 16*(n-1)
                ld      de,FNKSTR
                add     hl,de               ; HL = the slot
                push    hl
                ld      b,KEYSTRIDE         ; clear the whole slot first, so a
                xor     a                   ; shorter string leaves no tail behind
ks_clr:         ld      (hl),a
                inc     hl
                djnz    ks_clr
                pop     de                  ; DE = the slot
                ld      hl,STRSCR
                ld      a,(hl)              ; A = staged length
                inc     hl                  ; HL -> the bytes
                or      a
                ret     z                   ; empty string: the slot is already clear
                cp      KEYMAX+1
                jr      c,ks_len
                ld      a,KEYMAX            ; truncate to 15 (measured)
ks_len:         ld      c,a
                ld      b,0
                ldir
                ret
ks_defaults:    ; --- cold boot: the measured image, all 160 bytes -------------
                ld      hl,keystr_image
                ld      de,FNKSTR
                ld      bc,KEYSLOTS*KEYSTRIDE
                ldir
                ret
ks_list:        ; --- KEY LIST: ten lines into DETOKBUF; the resident stub drains --
                ; The D-PUEMIT shape: `pchar` here is sub/detok.asm's sub-local
                ; re-bind that APPENDS to DETOKBUF -- the resident pchar is main
                ; page 1 and outside the resident ABI (whose ceiling is the low
                ; region), and the BIOS is switched out under a page-0 tenant, so
                ; a buffer is the only sink there is. The first cut called the
                ; local pchar believing it was the resident one, and wrote ten
                ; lines through a stale DB_CUR.
                ; \U0001f3af CONTROL BYTES PRINT AS BLANKS, measured: the references
                ; show F10's leading $0C as a space and F5/F8/F9's CR and $1E as
                ; nothing visible after the line -- exactly what "print < $20 as
                ; a space" renders, and the opposite of what CHPUT would do with
                ; a $0C (clear the screen) or a CR.
                ld      hl,FNKSTR
                ld      b,KEYSLOTS
ks_line:        push    bc
                push    hl
ks_ch:          ld      a,(hl)
                or      a
                jr      z,ks_eol
                cp      $20
                jr      nc,ks_out
                ld      a,' '
ks_out:         call    pchar               ; append to DETOKBUF (preserves regs)
                inc     hl
                jr      ks_ch
ks_eol:         ld      a,13
                call    pchar
                ld      a,10
                call    pchar
                pop     hl
                ld      de,KEYSTRIDE
                add     hl,de
                pop     bc
                djnz    ks_line
                ld      hl,(DB_CUR)
                ld      (hl),0              ; terminate for the resident drain
                ret

; --- the measured image: scratchpad/keydef_probe.py, VG-8020, 2026-09-10 -----
keystr_image:
                db      $63,$6F,$6C,$6F,$72,$20,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00    ; F1
                db      $61,$75,$74,$6F,$20,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00    ; F2
                db      $67,$6F,$74,$6F,$20,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00    ; F3
                db      $6C,$69,$73,$74,$20,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00    ; F4
                db      $72,$75,$6E,$0D,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00    ; F5
                db      $63,$6F,$6C,$6F,$72,$20,$31,$35,$2C,$34,$2C,$34,$0D,$00,$00,$00    ; F6
                db      $63,$6C,$6F,$61,$64,$22,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00    ; F7
                db      $63,$6F,$6E,$74,$0D,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00    ; F8
                db      $6C,$69,$73,$74,$2E,$0D,$1E,$1E,$00,$00,$00,$00,$00,$00,$00,$00    ; F9
                db      $0C,$72,$75,$6E,$0D,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00    ; F10
