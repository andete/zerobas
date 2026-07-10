; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; str-engine.asm — the string expression engine (repack build only).
; ===========================================================================
; This file is assembled ONLY in the repack build (ROM_BASE < $4000), into the
; reclaimed page-0 low region ($2812-$3FFF). It is NOT part of the lean 16 KB
; basic.rom — the byte-full lean image keeps the minimal string-VALUE layer
; (basic/strvar.asm) and this file's callers fold back to str_eval_one there.
; See docs/spec-basic-string-engine.md and basic/PROVENANCE.md.
;
; S3 delivers the CONCAT spine: the temp-result ring (own-design, spec §3a D-A,
; N=3) and `+` concatenation of string operands. The core string FUNCTIONS
; (LEN/ASC/VAL/CHR$/STR$/LEFT$/RIGHT$/MID$) land in S4 — their keyword tokens are
; already crunched (kwtable.inc) but have no handler yet.
;
; Clean-room: original code. Concatenation SEMANTICS (left-to-right, truncate the
; combined length) are from the public MSX-BASIC language reference; the fixed temp
; ring, the STRMAX clamp, and the descriptor layout are zerobas's own design — the
; reference ROM's string heap + garbage collector are deliberately NOT reproduced.
; No disassembly.
; ===========================================================================

; --- str_alloc_temp: hand out the next result-ring slot ---------------------
; The string-producing ops (concat here; the S4 functions later) write their result
; into a [len][bytes] slot of the STRTMP ring and point STRPTR at it. Slots are used
; round-robin over STRNTMP entries: a fresh call advances STRTMP_IDX and returns that
; slot's address. N=3 covers the real expression depth (a binary op has <=2 live
; operands + 1 result); a deeper nest reuses the oldest slot — a documented own-design
; truncation of expression depth (spec §3a/§7), mirroring the STRMAX length clamp.
; out: HL = address of the slot's [len][bytes] descriptor.
; Clobbers A, DE.
str_alloc_temp:
                ld      a,(STRTMP_IDX)
                inc     a
                cp      STRNTMP
                jr      c,sat_store         ; < N -> keep
                xor     a                   ; wrap to slot 0 (also self-heals garbage RAM)
sat_store:
                ld      (STRTMP_IDX),a      ; A = new slot index (0..N-1)
                ; HL = STRTMP + A*STRTMPSZ
                ld      hl,STRTMP
                or      a
                ret     z                   ; slot 0 -> base
                ld      de,STRTMPSZ
sat_add:
                add     hl,de
                dec     a
                jr      nz,sat_add
                ret

; --- str_copy_desc: copy a [len][bytes] descriptor, clamped to STRMAX -------
; in:  HL = source descriptor, DE = destination descriptor (>= STRTMPSZ bytes).
; out: dst len = min(srclen, STRMAX); that many bytes copied. Clobbers A, B, HL, DE.
str_copy_desc:
                ld      a,(hl)              ; source length
                cp      STRMAX + 1
                jr      c,scd_len           ; <= STRMAX
                ld      a,STRMAX            ; clamp
scd_len:
                ld      (de),a              ; store dst length
                or      a
                ret     z                   ; empty -> done
                ld      b,a
                inc     hl                  ; -> src bytes
                inc     de                  ; -> dst bytes
scd_cp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                djnz    scd_cp
                ret

; --- str_append_desc: append a descriptor onto an accumulator, clamped ------
; Appends the source string onto the destination accumulator, clamping the COMBINED
; length to STRMAX (extra source bytes are dropped — the documented own-design
; truncation, consistent with STRMAX everywhere).
; in:  HL = source [len][bytes], DE = destination accumulator [len][bytes].
; out: dst length = min(dstlen + srclen, STRMAX), appended bytes copied.
; Clobbers A, BC, HL, DE.
str_append_desc:
                ld      a,(de)              ; current dst length
                ld      c,a                 ; C = dst length
                ld      a,STRMAX
                sub     c                   ; A = room left (dstlen <= STRMAX, so >= 0)
                ret     z                   ; full -> append nothing (len already STRMAX)
                ld      b,(hl)              ; B = source length (bytes available)
                cp      b
                jr      nc,sad_cnt          ; room >= srclen -> copy srclen
                ld      b,a                 ; else copy only 'room' bytes
sad_cnt:
                ld      a,b
                or      a
                ret     z                   ; nothing to append -> dst length unchanged
                ; update the dst length FIRST (C + B), before the copy loop consumes B.
                ld      a,c
                add     a,b                 ; new length = old dstlen + appended count
                ld      (de),a              ; DE still = dst base
                inc     hl                  ; HL -> source bytes[0]
                ; DE -> dst append point = dstbase + 1 + dstlen(C)
                inc     de                  ; past the length byte
                ld      a,c
                add     a,e
                ld      e,a
                ld      a,0
                adc     a,d
                ld      d,a
sad_cp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                djnz    sad_cp
                ret

; --- str_concat_tail: fold trailing `+ operand` terms into a temp -----------
; Entered by str_eval (basic/strvar.asm) AFTER the first operand: HL = cursor just
; past operand 1, STRPTR -> operand 1's [len][bytes] descriptor, VALTYP = 1. If the
; next non-space token is the '+' operator (PLUS_TOKEN), allocate ONE result temp,
; copy operand 1 into it, then repeatedly evaluate "+ <operand>" and append into that
; temp (clamped to STRMAX), leaving STRPTR -> the result. Otherwise leave STRPTR at
; operand 1 (single operand — byte-for-byte the old str_eval behaviour).
;
; The accumulator R is allocated once and its address held in STRCAT_R, so a whole
; `A$+B$+C$+...` chain uses a SINGLE ring slot (only R plus one transient operand are
; ever live). A nested string-function operand (S4) may allocate its own ring slot;
; the N=3 ring caps the simultaneously-live temps (spec §3a/§7).
; out: STRPTR -> result, VALTYP = 1, HL past the whole expression, CF set. CF clear if
;      a trailing operand is malformed (caller errors), matching str_eval_one.
; Clobbers A, BC, DE, HL.
str_concat_tail:
                push    hl                  ; save cursor (operand-1 end)
                call    skip_spaces         ; HL -> next non-space
                ld      a,(hl)
                cp      PLUS_TOKEN          ; '+' ($F1) ?
                jr      z,sct_go
                pop     hl                  ; no concat -> restore exact cursor
                scf
                ret
sct_go:
                pop     bc                  ; discard the stale saved cursor
                ; HL -> the '+' token. Allocate R, remember it, copy operand 1 into it.
                push    hl                  ; save cursor (@ '+')
                call    str_alloc_temp      ; HL = R
                ld      (STRCAT_R),hl       ; remember the accumulator address
                ex      de,hl               ; DE = R (destination)
                ld      hl,(STRPTR)         ; HL = operand 1 (source)
                call    str_copy_desc       ; R := operand 1 (clamped)
                pop     hl                  ; HL = cursor (@ '+')
sct_loop:
                inc     hl                  ; past the '+'
                call    skip_spaces         ; HL -> the next operand
                call    str_eval_one        ; STRPTR -> operand, HL advanced, CF set/clear
                jr      nc,sct_err          ; malformed operand
                push    hl                  ; save advanced cursor
                ld      de,(STRCAT_R)       ; DE = R (destination)
                ld      hl,(STRPTR)         ; HL = operand (source)
                call    str_append_desc     ; R := R + operand (clamped)
                pop     hl                  ; restore cursor
                ; another '+' ?
                push    hl
                call    skip_spaces
                ld      a,(hl)
                cp      PLUS_TOKEN
                jr      z,sct_next
                pop     hl                  ; no more terms -> HL past the last operand
                push    hl                  ; keep the cursor
                ld      hl,(STRCAT_R)
                ld      (STRPTR),hl         ; result = R
                pop     hl                  ; HL = cursor
                scf
                ret
sct_next:
                pop     hl                  ; HL -> the '+' token
                jr      sct_loop
sct_err:
                or      a                   ; CF clear -> malformed operand
                ret
