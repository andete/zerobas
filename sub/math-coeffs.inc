; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; GENERATED FILE -- do not hand-edit. Produced by tools/gen_math_coeffs.py
; (own decimal minimax + constants; cross-checked vs Cody & Waite METHOD,
; NEVER the MSX ROM). docs/spec-basic-mathpack-slice2.md §11.3.
;
; FPNUM 18-byte records: sign(1) + dexp LE word(2) + dig[0..13] + guard(1).

ATAN_DEG        equ 8
ATAN_COEF:      db 9                ; term count (c[8]..c[0])
                ; c[8]
                db 000h            ; sign  (+)
                dw 65535          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 4, 4, 3, 7, 5, 9, 2, 0, 0, 7, 9, 0, 4, 6, 0   ; dig[0..13], guard=0
                ; c[7]
                db 080h            ; sign  (-)
                dw 65535          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 6, 4, 8, 2, 8, 0, 2, 7, 1, 0, 7, 1, 9, 3, 0   ; dig[0..13], guard=0
                ; c[6]
                db 000h            ; sign  (+)
                dw 65535          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 7, 6, 7, 9, 3, 2, 3, 0, 4, 8, 8, 8, 4, 2, 0   ; dig[0..13], guard=0
                ; c[5]
                db 080h            ; sign  (-)
                dw 65535          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 9, 0, 9, 0, 3, 6, 8, 3, 6, 5, 7, 6, 0, 1, 0   ; dig[0..13], guard=0
                ; c[4]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 1, 1, 1, 1, 0, 9, 7, 8, 0, 4, 4, 8, 6, 0   ; dig[0..13], guard=0
                ; c[3]
                db 080h            ; sign  (-)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 4, 2, 8, 5, 7, 1, 4, 1, 0, 1, 1, 1, 3, 0   ; dig[0..13], guard=0
                ; c[2]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 9, 9, 9, 9, 9, 9, 9, 9, 9, 8, 7, 1, 4, 0   ; dig[0..13], guard=0
                ; c[1]
                db 080h            ; sign  (-)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0   ; dig[0..13], guard=0
                ; c[0]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0   ; dig[0..13], guard=0
PI_2:
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 5, 7, 0, 7, 9, 6, 3, 2, 6, 7, 9, 4, 9, 0   ; dig[0..13], guard=0
PI_6:
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 5, 2, 3, 5, 9, 8, 7, 7, 5, 5, 9, 8, 3, 0, 0   ; dig[0..13], guard=0
SQRT3:
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 7, 3, 2, 0, 5, 0, 8, 0, 7, 5, 6, 8, 9, 0   ; dig[0..13], guard=0
BREAK:
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 6, 7, 9, 4, 9, 1, 9, 2, 4, 3, 1, 1, 2, 0   ; dig[0..13], guard=0
