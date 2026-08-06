; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; GENERATED FILE -- do not hand-edit. Produced by tools/gen_math_coeffs.py
; (own decimal minimax + constants; cross-checked vs Cody & Waite METHOD,
; NEVER the MSX ROM). docs/spec-basic-mathpack-slice2.md §11.3.
;
; Clean-room: own design. Every constant is produced here, by our own
; decimal minimax fit; none is derived from a disassembly or byte-copy of
; any reference ROM's coefficient tables.
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

; ---- math pack slice 2b: EXP + LOG (docs/spec-basic-mathpack-slice2.md §12) ----
EXP_COEF_DEG    equ 9
EXP_COEF:       db 10                ; term count (c[9]..c[0]) -- E(r)=(exp(r)-1)/r, |r|<=ln10/16+pad
                ; c[9]
                db 000h            ; sign  (+)
                dw 65530          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 7, 5, 6, 8, 1, 3, 0, 4, 6, 7, 1, 4, 0, 0   ; dig[0..13], guard=0
                ; c[8]
                db 000h            ; sign  (+)
                dw 65531          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 7, 5, 7, 0, 2, 9, 3, 1, 1, 5, 6, 2, 4, 0   ; dig[0..13], guard=0
                ; c[7]
                db 000h            ; sign  (+)
                dw 65532          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 4, 8, 0, 1, 5, 8, 5, 3, 4, 2, 2, 8, 4, 0   ; dig[0..13], guard=0
                ; c[6]
                db 000h            ; sign  (+)
                dw 65533          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 9, 8, 4, 1, 2, 6, 7, 4, 9, 0, 0, 1, 1, 0   ; dig[0..13], guard=0
                ; c[5]
                db 000h            ; sign  (+)
                dw 65534          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 3, 8, 8, 8, 8, 8, 8, 8, 8, 9, 0, 3, 4, 0   ; dig[0..13], guard=0
                ; c[4]
                db 000h            ; sign  (+)
                dw 65534          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 8, 3, 3, 3, 3, 3, 3, 3, 3, 3, 5, 0, 7, 3, 0   ; dig[0..13], guard=0
                ; c[3]
                db 000h            ; sign  (+)
                dw 65535          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 4, 1, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 0   ; dig[0..13], guard=0
                ; c[2]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 0   ; dig[0..13], guard=0
                ; c[1]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0   ; dig[0..13], guard=0
                ; c[0]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0   ; dig[0..13], guard=0
LOG_COEF_DEG    equ 5
LOG_COEF:       db 6                ; term count (c[5]..c[0]) -- 2*atanh(sqrt g)/sqrt g
                ; c[5]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 8, 4, 2, 1, 9, 7, 4, 3, 4, 2, 0, 0, 3, 0   ; dig[0..13], guard=0
                ; c[4]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 2, 2, 2, 0, 8, 2, 4, 3, 7, 6, 5, 8, 8, 0   ; dig[0..13], guard=0
                ; c[3]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 8, 5, 7, 1, 4, 3, 2, 3, 1, 6, 0, 6, 9, 0   ; dig[0..13], guard=0
                ; c[2]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 3, 9, 9, 9, 9, 9, 9, 9, 9, 9, 5, 4, 6, 8, 0   ; dig[0..13], guard=0
                ; c[1]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 9, 0   ; dig[0..13], guard=0
                ; c[0]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0   ; dig[0..13], guard=0
EXP_RC:  ; 8/ln10 (n8 := nearest-int(x*RC))
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 3, 4, 7, 4, 3, 5, 5, 8, 5, 5, 2, 2, 6, 0, 0   ; dig[0..13], guard=0
EXP_C1:  ; ln10/8 hi split, 10 sig (n8*C1 EXACT)
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 8, 7, 8, 2, 3, 1, 3, 6, 6, 0, 0, 0, 0, 0   ; dig[0..13], guard=0
EXP_C2:  ; ln10/8 lo split (C - C1)
                db 000h            ; sign  (+)
                dw 65526          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 4, 2, 5, 5, 7, 1, 0, 5, 0, 2, 2, 4, 9, 0   ; dig[0..13], guard=0
LN10_C1:  ; ln10 hi split, 12 sig (e'*C1 EXACT)
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 3, 0, 2, 5, 8, 5, 0, 9, 2, 9, 9, 0, 0, 0   ; dig[0..13], guard=0
LN10_C2:  ; ln10 lo split (ln10 - C1)
                db 000h            ; sign  (+)
                dw 65525          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 4, 0, 4, 5, 6, 8, 4, 0, 1, 7, 9, 9, 1, 5, 0   ; dig[0..13], guard=0
POW8_TBL:       ; [m] = round14(10^(m/8)), m=0..7 ([0] exactly 1.0; EXP's T-hat AND LOG's K-hat)
                ; [0]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0   ; dig[0..13], guard=0
                ; [1]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 3, 3, 3, 5, 2, 1, 4, 3, 2, 1, 6, 3, 3, 0   ; dig[0..13], guard=0
                ; [2]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 7, 7, 8, 2, 7, 9, 4, 1, 0, 0, 3, 8, 9, 0   ; dig[0..13], guard=0
                ; [3]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 3, 7, 1, 3, 7, 3, 7, 0, 5, 6, 6, 1, 7, 0   ; dig[0..13], guard=0
                ; [4]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 3, 1, 6, 2, 2, 7, 7, 6, 6, 0, 1, 6, 8, 4, 0   ; dig[0..13], guard=0
                ; [5]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 4, 2, 1, 6, 9, 6, 5, 0, 3, 4, 2, 8, 5, 8, 0   ; dig[0..13], guard=0
                ; [6]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 5, 6, 2, 3, 4, 1, 3, 2, 5, 1, 9, 0, 3, 5, 0   ; dig[0..13], guard=0
                ; [7]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 7, 4, 9, 8, 9, 4, 2, 0, 9, 3, 3, 2, 4, 6, 0   ; dig[0..13], guard=0
EXP_TCOR:       ; [m] = round14(ln(POW8[m]) - m*ln10/8), m=1..7 (T-hat representation-error absorber)
                ; [1]
                db 080h            ; sign  (-)
                dw 65523          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 8, 0, 1, 6, 7, 1, 5, 2, 5, 6, 4, 9, 2, 0   ; dig[0..13], guard=0
                ; [2]
                db 080h            ; sign  (-)
                dw 65523          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 2, 8, 2, 2, 0, 7, 1, 3, 1, 9, 3, 1, 9, 0   ; dig[0..13], guard=0
                ; [3]
                db 000h            ; sign  (+)
                dw 65523          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 8, 8, 6, 6, 0, 0, 5, 0, 2, 5, 0, 3, 2, 0   ; dig[0..13], guard=0
                ; [4]
                db 000h            ; sign  (+)
                dw 65522          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 6, 5, 3, 5, 7, 9, 5, 8, 1, 7, 9, 2, 8, 0, 0   ; dig[0..13], guard=0
                ; [5]
                db 080h            ; sign  (-)
                dw 65522          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 5, 3, 3, 2, 1, 9, 7, 4, 3, 3, 6, 4, 6, 3, 0   ; dig[0..13], guard=0
                ; [6]
                db 000h            ; sign  (+)
                dw 65522          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 6, 3, 5, 3, 1, 4, 7, 2, 3, 9, 3, 3, 8, 0   ; dig[0..13], guard=0
                ; [7]
                db 000h            ; sign  (+)
                dw 65522          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 5, 5, 6, 4, 3, 8, 1, 9, 6, 7, 2, 0, 9, 5, 0   ; dig[0..13], guard=0
LNK_TBL:        ; [j] = round14(ln(POW8[j])), j=1..7 (ln of the ROUNDED K-hat -- absorption)
                ; [1]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 8, 7, 8, 2, 3, 1, 3, 6, 6, 2, 4, 2, 4, 0   ; dig[0..13], guard=0
                ; [2]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 5, 7, 5, 6, 4, 6, 2, 7, 3, 2, 4, 8, 5, 0, 0   ; dig[0..13], guard=0
                ; [3]
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 8, 6, 3, 4, 6, 9, 4, 0, 9, 8, 7, 2, 7, 9, 0   ; dig[0..13], guard=0
                ; [4]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 1, 5, 1, 2, 9, 2, 5, 4, 6, 4, 9, 7, 0, 0   ; dig[0..13], guard=0
                ; [5]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 4, 3, 9, 1, 1, 5, 6, 8, 3, 1, 2, 1, 3, 0   ; dig[0..13], guard=0
                ; [6]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 7, 2, 6, 9, 3, 8, 8, 1, 9, 7, 4, 5, 5, 0   ; dig[0..13], guard=0
                ; [7]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 0, 1, 4, 7, 6, 1, 9, 5, 6, 3, 6, 9, 8, 0   ; dig[0..13], guard=0
NEGLNK_TBL:     ; [j] = round14(ln(POW8[j]) - ln10), j=0..7 (the e'=-1 decade's merged additive -- kills the cancellation)
                ; [0]
                db 080h            ; sign  (-)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 3, 0, 2, 5, 8, 5, 0, 9, 2, 9, 9, 4, 0, 0   ; dig[0..13], guard=0
                ; [1]
                db 080h            ; sign  (-)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 0, 1, 4, 7, 6, 1, 9, 5, 6, 3, 6, 9, 8, 0   ; dig[0..13], guard=0
                ; [2]
                db 080h            ; sign  (-)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 7, 2, 6, 9, 3, 8, 8, 1, 9, 7, 4, 5, 5, 0   ; dig[0..13], guard=0
                ; [3]
                db 080h            ; sign  (-)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 4, 3, 9, 1, 1, 5, 6, 8, 3, 1, 2, 1, 3, 0   ; dig[0..13], guard=0
                ; [4]
                db 080h            ; sign  (-)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 1, 5, 1, 2, 9, 2, 5, 4, 6, 4, 9, 7, 0, 0   ; dig[0..13], guard=0
                ; [5]
                db 080h            ; sign  (-)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 8, 6, 3, 4, 6, 9, 4, 0, 9, 8, 7, 2, 7, 7, 0   ; dig[0..13], guard=0
                ; [6]
                db 080h            ; sign  (-)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 5, 7, 5, 6, 4, 6, 2, 7, 3, 2, 4, 8, 5, 1, 0   ; dig[0..13], guard=0
                ; [7]
                db 080h            ; sign  (-)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 8, 7, 8, 2, 3, 1, 3, 6, 6, 2, 4, 2, 5, 0   ; dig[0..13], guard=0
LOG_BP:         ; [j] = round14(10^((2j-1)/16)), j=1..8 (j-scan breakpoints)
                ; [1]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 1, 5, 4, 7, 8, 1, 9, 8, 4, 6, 8, 9, 5, 0   ; dig[0..13], guard=0
                ; [2]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 5, 3, 9, 9, 2, 6, 5, 2, 6, 0, 5, 9, 5, 0   ; dig[0..13], guard=0
                ; [3]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 0, 5, 3, 5, 2, 5, 0, 2, 6, 4, 5, 7, 1, 0   ; dig[0..13], guard=0
                ; [4]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 7, 3, 8, 4, 1, 9, 6, 3, 4, 2, 6, 4, 4, 0   ; dig[0..13], guard=0
                ; [5]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 3, 6, 5, 1, 7, 4, 1, 2, 7, 2, 5, 4, 8, 4, 0   ; dig[0..13], guard=0
                ; [6]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 4, 8, 6, 9, 6, 7, 5, 2, 5, 1, 6, 5, 8, 6, 0   ; dig[0..13], guard=0
                ; [7]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 6, 4, 9, 3, 8, 1, 6, 3, 1, 5, 7, 6, 2, 1, 0   ; dig[0..13], guard=0
                ; [8]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 8, 6, 5, 9, 6, 4, 3, 2, 3, 3, 6, 0, 0, 7, 0   ; dig[0..13], guard=0

; ---- math pack slice 2d: SIN + COS (docs/spec-basic-mathpack-slice2.md §14) ----
SIN_COEF_DEG    equ 6
SIN_COEF:       db 7                ; term count (c[6]..c[0]) -- S(u)=sin(sqrt u)/sqrt u, sin(r)=r*S(r^2)
                ; c[6]
                db 000h            ; sign  (+)
                dw 65527          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 5, 8, 9, 4, 7, 3, 5, 0, 1, 6, 6, 8, 6, 0   ; dig[0..13], guard=0
                ; c[5]
                db 080h            ; sign  (-)
                dw 65529          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 5, 0, 5, 0, 7, 1, 6, 9, 4, 6, 3, 6, 3, 0   ; dig[0..13], guard=0
                ; c[4]
                db 000h            ; sign  (+)
                dw 65531          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 7, 5, 5, 7, 3, 1, 3, 3, 7, 6, 2, 2, 5, 0   ; dig[0..13], guard=0
                ; c[3]
                db 080h            ; sign  (-)
                dw 65533          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 9, 8, 4, 1, 2, 6, 9, 8, 2, 8, 6, 5, 0, 0   ; dig[0..13], guard=0
                ; c[2]
                db 000h            ; sign  (+)
                dw 65534          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 8, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 0, 4, 0   ; dig[0..13], guard=0
                ; c[1]
                db 080h            ; sign  (-)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 0   ; dig[0..13], guard=0
                ; c[0]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0   ; dig[0..13], guard=0
COS_COEF_DEG    equ 6
COS_COEF:       db 7                ; term count (c[6]..c[0]) -- C(u)=cos(sqrt u), cos(r)=C(r^2)
                ; c[6]
                db 000h            ; sign  (+)
                dw 65528          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 0, 6, 3, 0, 4, 5, 1, 9, 3, 0, 0, 7, 1, 0   ; dig[0..13], guard=0
                ; c[5]
                db 080h            ; sign  (-)
                dw 65530          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 7, 5, 5, 5, 2, 3, 3, 8, 4, 3, 2, 9, 1, 0   ; dig[0..13], guard=0
                ; c[4]
                db 000h            ; sign  (+)
                dw 65532          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 2, 4, 8, 0, 1, 5, 7, 8, 5, 3, 8, 3, 0, 1, 0   ; dig[0..13], guard=0
                ; c[3]
                db 080h            ; sign  (-)
                dw 65534          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 3, 8, 8, 8, 8, 8, 8, 8, 6, 9, 9, 7, 8, 0   ; dig[0..13], guard=0
                ; c[2]
                db 000h            ; sign  (+)
                dw 65535          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 4, 1, 6, 6, 6, 6, 6, 6, 6, 6, 6, 4, 7, 2, 0   ; dig[0..13], guard=0
                ; c[1]
                db 080h            ; sign  (-)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 4, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 0   ; dig[0..13], guard=0
                ; c[0]
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0   ; dig[0..13], guard=0
TWO_OVER_PI:  ; 2/pi (n := nearest-int(x*2/pi))
                db 000h            ; sign  (+)
                dw 0              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 6, 3, 6, 6, 1, 9, 7, 7, 2, 3, 6, 7, 5, 8, 0   ; dig[0..13], guard=0
SIN_C1:  ; pi/2 hi split, 5 sig 1.5708 (n*C1 EXACT, |n|<=1e9)
                db 000h            ; sign  (+)
                dw 1              ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 1, 5, 7, 0, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0   ; dig[0..13], guard=0
SIN_C2:  ; pi/2 lo split (pi/2 - C1)
                db 080h            ; sign  (-)
                dw 65531          ; dexp  (value = d0.d1.. x 10^(dexp-1))
                db 3, 6, 7, 3, 2, 0, 5, 1, 0, 3, 3, 8, 0, 8, 0   ; dig[0..13], guard=0
