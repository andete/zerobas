; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; pu-render.inc — PRINT USING format SCANNERS (shared render body).
;
; pu_to_field + pu_emit_tail: emit the format's LITERAL characters (everything
; outside a #/!/&/\..\ field) and, for pu_to_field, identify the next field's
; type/width. Both are pure leaves over the PU_* RAM sysvars and `pchar` — no
; eval, no pu_deref_body, no div10 — so they are a clean page-0 sub-ROM tenant
; (docs/spec-evict-printusing.md).
;
; Included from ONE home, the sub/detok.asm pattern (a second, retired home was
; the lean 16 KB cart's inline copy in basic/printusing.asm):
;   * sub-ROM page 0 (sub/printusing.asm): `pchar` is re-bound to a
;     DETOKBUF append, and the resident stubs drain DETOKBUF through the real
;     print_string (honouring PRDEST — so PRINT# USING file form is untouched).
; The includer defines BACKSLASH (printusing.asm keeps it for pu_has_field; the
; sub tenant defines its own).
;
; Clean-room: our own code, extracted verbatim from basic/printusing.asm.

; pu_to_field — emit literal format chars from PU_POS until a field; on reaching the
; format end, wrap to 0 ONCE (format reuse). Out: CF clear + PU_TYPE/PU_W set +
; PU_POS advanced past the field; CF set if no field exists (after one wrap).
; Clobbers A, B, C, DE, HL.
pu_to_field:
                ld      a,(PU_FLAGS)
                and     $01                 ; clear "wrapped" (bit1), the asterisk
                                            ; fill (bit2), the sign specifier
                                            ; (bits 3-5) and the decimal flag
                                            ; (bit6) -- all per-FIELD state. Bit0
                                            ; (trailing separator) is per-STATEMENT
                                            ; and must survive.
                ld      (PU_FLAGS),a
ptf_scan:
                ld      a,(PU_POS)
                ld      b,a
                ld      a,(PU_FMTLEN)
                cp      b
                jr      z,ptf_wrap          ; at end of format
                ld      e,b
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '#'
                jp      z,ptf_num
                cp      '!'
                jp      z,ptf_bang
                cp      '&'
                jp      z,ptf_amp
                cp      BACKSLASH
                jp      z,ptf_back
                cp      '*'
                jp      z,ptf_star
                cp      '+'
                jp      z,ptf_plus
                call    pchar               ; literal -> emit
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                jr      ptf_scan
ptf_wrap:
                ld      a,(PU_FLAGS)
                bit     1,a
                jr      nz,ptf_nofield      ; already wrapped -> no field at all
                set     1,a
                ld      (PU_FLAGS),a
                xor     a
                ld      (PU_POS),a
                jr      ptf_scan
ptf_nofield:
                scf
                ret
ptf_num:
                ; width = run of '#' from PU_POS (bounded by the format end).
                ld      a,(PU_POS)
                ld      c,a                 ; C = scan index
                ld      b,0                 ; B = width
ptf_num_lp:
                ld      a,(PU_FMTLEN)
                cp      c
                jr      z,ptf_num_done
                ld      e,c
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '#'
                jr      z,ptf_num_wide
                ; --- D-PUCOMMA: a `,` INSIDE the run joins the field -----------
                ; Measured (`m.trail`): `USING"##,";5` is `  5`, THREE wide -- the
                ; comma is consumed by the field and occupies a column even when
                ; no comma is printed. A LEADING one is a literal (`m.lead`:
                ; `USING",##";5` is `, 5`), and that needs no test here: the caller
                ; only enters ptf_num on a `#`, so the run has always started.
                cp      ','
                jr      nz,ptf_num_done
                ld      a,(PU_FLAGS)
                set     7,a
                ld      (PU_FLAGS),a
ptf_num_wide:
                inc     b                   ; `#` and `,` both take a column
                inc     c
                jr      ptf_num_lp
ptf_num_done:
                ; --- D-PUDOT: a `.` and its own `#` run, right after this one ----
                ; `##.##` is FIVE wide: the point takes a position and so does each
                ; decimal place. The count goes in PU_DEC for the renderer.
                ld      a,(PU_FMTLEN)
                cp      c
                jr      z,ptf_num_sign      ; format ended: no decimal part
                ld      e,c
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '.'
                jr      nz,ptf_num_sign
                inc     c                   ; consume the point
                xor     a
                ld      (PU_DEC),a
                ; ⚠️ COUNT STRAIGHT INTO PU_DEC, do NOT borrow B. B holds the
                ; integer-digit width and C the scan cursor, so the obvious
                ; `push bc` / `ld b,0` / `pop bc` preserves the width and REWINDS
                ; THE CURSOR -- the scanner then re-reads the decimal `#`s instead
                ; of the character after them. That is invisible on all eleven
                ; `d.*` rows (a field with no argument left is just a trailing
                ; literal) and visible on exactly ONE: `##.##-`, where the
                ; trailing sign is the character the cursor never reached.
ptf_dec_lp:
                ld      a,(PU_FMTLEN)
                cp      c
                jr      z,ptf_dec_done
                ld      e,c
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '#'
                jr      nz,ptf_dec_done
                ld      a,(PU_DEC)
                inc     a
                ld      (PU_DEC),a
                inc     c
                jr      ptf_dec_lp
ptf_dec_done:
                ld      a,(PU_FLAGS)
                set     6,a                 ; a decimal part is present
                ld      (PU_FLAGS),a
ptf_num_sign:
                ; --- D-PUSIGN: a TRAILING `+` or `-` right after the run --------
                ld      a,(PU_FMTLEN)
                cp      c
                jr      z,ptf_num_fill      ; format ended: no trailing sign
                ld      e,c
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '+'
                jr      z,ptf_num_tplus
                cp      '-'
                jr      nz,ptf_num_fill
                ld      a,(PU_FLAGS)
                set     3,a                 ; a sign specifier is present
                set     4,a                 ; ...and it is TRAILING
                ld      (PU_FLAGS),a
                inc     c                   ; consume it
                jr      ptf_num_fill
ptf_num_tplus:
                ld      a,(PU_FLAGS)
                set     3,a
                set     4,a
                set     5,a                 ; ...and the character is `+`
                ld      (PU_FLAGS),a
                inc     c
ptf_num_fill:
                ; D-PUSTAR: the two asterisks COUNT toward the field width --
                ; measured, `PRINT USING"**##";5` is `***5`, four characters wide,
                ; and `**##` with 1234 is `1234` with no fill at all.
                ld      a,(PU_FLAGS)
                bit     2,a
                jr      z,ptf_num_sw
                inc     b
                inc     b
ptf_num_sw:
                ; D-PUSIGN: the sign character occupies a position too --
                ; `+##` with 5 is ` +5`, three wide.
                bit     3,a
                jr      z,ptf_num_dw
                inc     b
ptf_num_dw:
                ; D-PUDOT: the point plus every decimal place
                bit     6,a
                jr      z,ptf_num_w
                inc     b                   ; the `.` itself
                push    af
                ld      a,(PU_DEC)
                add     a,b
                ld      b,a
                pop     af
ptf_num_w:
                ld      a,b
                ld      (PU_W),a
                ld      a,c
                ld      (PU_POS),a
                xor     a
                ld      (PU_TYPE),a         ; numeric (also CF clear)
                ret
; --- ptf_star: `**` before a `#` run selects ASTERISK FILL (D-PUSTAR) --------
; docs/spec-basic-pufloat.md. Both characters are consumed and both count toward
; the width; the emitter (basic/printusing.asm pu_do_number) reads PU_FLAGS bit 2
; and pads with `*` instead of a space.
; ⚠️ A LONE `*` STAYS A LITERAL, and so does a `*` at the very end of the format.
; Only the PAIR is a specifier, so `PRINT USING"*#";5` keeps its asterisk.
ptf_star:
                ld      a,(PU_POS)
                inc     a
                ld      c,a                 ; C = index of the SECOND character
                ld      a,(PU_FMTLEN)
                cp      c
                jr      z,ptf_star_lit      ; `*` was the last char -> literal
                ld      e,c
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '*'
                jr      nz,ptf_star_lit     ; not a PAIR -> literal
                ld      a,(PU_FLAGS)
                set     2,a
                ld      (PU_FLAGS),a
                ld      a,c
                inc     a
                ld      (PU_POS),a          ; past BOTH asterisks
                jp      ptf_scan
ptf_star_lit:
                ld      a,'*'
                call    pchar
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                jp      ptf_scan

; --- ptf_plus: a LEADING `+` before a `#` run (D-PUSIGN) --------------------
; One character, consumed, and it counts toward the width. ⚠️ A `+` NOT followed
; by `#` stays a literal, so `PRINT USING"+A#";5` keeps its plus.
ptf_plus:
                ld      a,(PU_POS)
                inc     a
                ld      c,a
                ld      a,(PU_FMTLEN)
                cp      c
                jr      z,ptf_plus_lit      ; `+` was the last char -> literal
                ld      e,c
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '#'
                jr      nz,ptf_plus_lit
                ld      a,(PU_FLAGS)
                set     3,a                 ; sign present, LEADING (bit4 clear)
                set     5,a                 ; and the character is `+`
                ld      (PU_FLAGS),a
                ld      a,c
                ld      (PU_POS),a          ; past the `+`
                jp      ptf_scan
ptf_plus_lit:
                ld      a,'+'
                call    pchar
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                jp      ptf_scan

ptf_bang:
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                ld      a,1
                ld      (PU_W),a
                ld      a,2                 ; type 2 = '!'
                ld      (PU_TYPE),a
                or      a                   ; CF clear
                ret
ptf_amp:
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                ld      a,1                 ; type 1 = '&'
                ld      (PU_TYPE),a
                or      a
                ret
ptf_back:
                ; find the closing '\' from PU_POS+1; width = closepos-PU_POS+1.
                ld      a,(PU_POS)
                ld      c,a
                inc     c                   ; scan from the char after the opening '\'
ptf_back_lp:
                ld      a,(PU_FMTLEN)
                cp      c
                jr      z,ptf_back_unterm   ; no closing '\' before the end
                ld      e,c
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      BACKSLASH
                jr      z,ptf_back_close
                inc     c
                jr      ptf_back_lp
ptf_back_close:
                ld      a,c
                ld      hl,PU_POS
                sub     (hl)
                inc     a                   ; width = (close - open) + 1  (>= 2)
                ld      (PU_W),a
                inc     c                   ; PU_POS past the closing '\'
                ld      a,c
                ld      (PU_POS),a
                ld      a,3                 ; type 3 = '\..\'
                ld      (PU_TYPE),a
                or      a
                ret
ptf_back_unterm:
                ; lone '\' with no close -> treat it as a literal and keep scanning.
                ld      a,BACKSLASH
                call    pchar
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                jp      ptf_scan

; pu_emit_tail — emit literal format chars from PU_POS up to (not including) the next
; field or the format end. No wrap. Clobbers A, B, DE, HL.
pu_emit_tail:
                ld      a,(PU_POS)
                ld      b,a
                ld      a,(PU_FMTLEN)
                cp      b
                ret     z                   ; end of format
                ld      e,b
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '#'
                ret     z
                cp      '!'
                ret     z
                cp      '&'
                ret     z
                cp      BACKSLASH
                ret     z
                call    pchar
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                jr      pu_emit_tail
