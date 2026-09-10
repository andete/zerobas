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
KEYSLOTS        equ     10
KEYSTRIDE       equ     16
KEYMAX          equ     15                  ; measured truncation (D-KEYSCOUT2)

keystr_tenant:
                ; Every op leaves DETOKBUF printable for the resident drain:
                ; LIST fills it, the others leave it EMPTY (a lone NUL), so
                ; ex_key can drain unconditionally and spend no page-1 bytes on
                ; a branch.
                ld      hl,DETOKBUF
                ld      (DB_CUR),hl
                ld      (hl),0
                ld      a,(KEYARG)
                or      a
                jr      z,ks_defaults
                cp      255
                jr      z,ks_list
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
