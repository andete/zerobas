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
; Included from TWO homes, exactly the sub/detok.asm pattern:
;   * lean 16 KB cart (basic/printusing.asm, ROM_BASE >= $4000): inline, `pchar`
;     = the real print.asm sink → BYTE-IDENTICAL to the pre-eviction build.
;   * sub-ROM page 0 (sub/printusing.asm, repack): `pchar` is re-bound to a
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
                and     $FD                 ; clear "wrapped" (bit1)
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
                jr      nz,ptf_num_done
                inc     b
                inc     c
                jr      ptf_num_lp
ptf_num_done:
                ld      a,b
                ld      (PU_W),a
                ld      a,c
                ld      (PU_POS),a
                xor     a
                ld      (PU_TYPE),a         ; numeric (also CF clear)
                ret
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
