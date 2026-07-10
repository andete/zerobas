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

; ===========================================================================
; S4 — the core string VERBS (repack build only): LEN/ASC/VAL (string->number)
; and CHR$/STR$/LEFT$/RIGHT$/MID$ (->string). Their keyword tokens are already
; crunched + LIST-detokenised (kwtable.inc, S3); these are the handlers.
;
; Clean-room: original code. The verb SEMANTICS (1-based MID$, LEFT$/RIGHT$ head/
; tail clamps, ASC "" = error, VAL's leading-parse, STR$'s leading blank for
; non-negatives) are from the public MSX-BASIC language reference. Divergences
; (integer-only VAL per spec D-E; CHR$ takes the low byte of n; the STRMAX length
; clamp; results that transit the fixed N=3 temp ring, so a concat chain with >=3
; string-function operands reuses the oldest slot — the documented own-design
; depth limit, spec §3a/§7) are zerobas's own design. No disassembly.
; ===========================================================================

; --- helpers ---------------------------------------------------------------

; str_dup_temp: copy the descriptor at (STRPTR) into a fresh result-ring temp and
; repoint STRPTR at it. The string verbs that take a source string (LEFT$/RIGHT$/
; MID$) dup first, then slice the copy in place — so only the ONE temp address must
; survive the numeric-argument eval that follows (which may itself move STRPTR via a
; nested LEN/VAL). in: STRPTR -> source. out: HL = temp, STRPTR = temp. Clobbers A,BC,DE.
str_dup_temp:
                call    str_alloc_temp      ; HL = temp (clobbers A,DE)
                push    hl                  ; save temp
                ex      de,hl               ; DE = temp (destination)
                ld      hl,(STRPTR)         ; HL = source
                call    str_copy_desc       ; temp := source (clamped to STRMAX)
                pop     hl                  ; HL = temp
                ld      (STRPTR),hl
                ret

; str_min_bc: A = min(A, BC), treating A as a 0..255 length and BC as a 0..65535
; requested count. Used to clamp a LEFT$/RIGHT$/MID$ count to the bytes available.
; Preserves BC, DE, HL. Clobbers A + flags.
str_min_bc:
                inc     b
                dec     b                   ; test B (high byte of the count)
                ret     nz                  ; count >= 256 -> min is the length (A<=STRMAX)
                cp      c                   ; length - count(low)
                ret     c                   ; length < count -> length is the min (A)
                ld      a,c                 ; else the count is the min
                ret

; str_temp_slice: in the temp descriptor at BC, keep the count bytes starting at
; offset `start`, moving them to the front and setting the descriptor length. Used
; by LEFT$ (start 0 -> pure truncation), RIGHT$ and MID$. Pre-validated so that
; start+count <= length and count <= STRMAX. in: BC = temp, D = start (0-based),
; E = count. Clobbers A, BC, DE, HL. Leaves the temp in place (STRPTR unchanged).
str_temp_slice:
                ld      a,e
                ld      (bc),a              ; temp length := count
                or      a
                ret     z                   ; count 0 -> empty descriptor, done
                ld      a,d
                or      a
                ret     z                   ; start 0 -> slice already at the front
                push    de                  ; save start:count
                ld      h,b
                ld      l,c
                inc     hl                  ; HL = temp+1 = destination (front)
                push    hl                  ; save destination
                ld      c,d
                ld      b,0                 ; BC = start
                add     hl,bc               ; HL = temp+1+start = source
                pop     de                  ; DE = destination
                pop     bc                  ; B = start, C = count
                ld      b,0                 ; BC = count
                ldir                        ; move count bytes forward (dst < src, safe)
                ret

; --- LEN/ASC/VAL: string-argument functions in the NUMERIC evaluator -------
; Reached from ev_f_ff (basic/expr.asm) via `jp ev_ff_strnum` on an unrecognised
; $FF selector (repack build only; the lean build's ev_f_ff still `jp ev_f_err`s).
; Entered with IX on the function selector byte. Each returns its numeric result in
; DE (the factor convention), IX advanced past the call.
ev_ff_strnum:
                cp      LEN_TOKEN           ; $92 -> LEN(a$)
                jr      z,ev_ff_len
                cp      ASC_TOKEN           ; $95 -> ASC(a$)
                jr      z,ev_ff_asc
                cp      VAL_TOKEN           ; $94 -> VAL(a$)
                jr      z,ev_ff_val
                jp      ev_f_err            ; a $FF string-token used in a numeric slot

; ev_str_arg: parse "( <string-expr> )" from the IX token stream, leaving STRPTR ->
; the argument's [len][bytes] descriptor and IX past ')'. Mirrors ev_ff_cvi's IX<->HL
; bridge. On a syntax/type error it does not return — it `jp ev_f_err` like every
; other factor error. Entered with IX on the function selector byte.
ev_str_arg:
                inc     ix                  ; skip the selector
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_err
                inc     ix
                call    ev_sp
                push    ix
                pop     hl                  ; HL = cursor
                call    str_eval            ; STRPTR -> desc; HL advanced; CF=ok
                jp      nc,ev_f_err
                push    hl
                pop     ix                  ; IX = cursor past the string operand
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
                ret
ev_ff_len:
                call    ev_str_arg          ; STRPTR -> desc
                ld      hl,(STRPTR)
                ld      e,(hl)              ; DE = descriptor length byte
                ld      d,0
                ret
ev_ff_asc:
                call    ev_str_arg
                ld      hl,(STRPTR)
                ld      a,(hl)              ; length
                or      a
                jp      z,ev_f_err          ; ASC("") -> Illegal function call
                inc     hl
                ld      e,(hl)              ; DE = first byte
                ld      d,0
                ret
ev_ff_val:
                call    ev_str_arg
                ; fall through: parse a leading signed decimal from the descriptor.
; str_val_parse: STRPTR -> [len][bytes]; parse an optional-sign leading decimal
; integer -> DE (0 if no digits; integer-only, spec D-E). Clobbers A,BC,HL.
str_val_parse:
                ld      hl,(STRPTR)
                ld      b,(hl)              ; B = remaining byte count
                inc     hl                  ; HL -> bytes
                ld      de,0                ; accumulator
                ld      c,0                 ; C bit0 = negative flag
svp_sp:
                ld      a,b
                or      a
                jr      z,svp_done          ; consumed all -> value so far
                ld      a,(hl)
                cp      ' '
                jr      nz,svp_sign
                inc     hl
                dec     b
                jr      svp_sp              ; skip leading spaces
svp_sign:
                cp      '-'
                jr      nz,svp_plus
                ld      c,1                 ; negative
                inc     hl
                dec     b
                jr      svp_digits
svp_plus:
                cp      '+'
                jr      nz,svp_digits
                inc     hl
                dec     b
svp_digits:
                ld      a,b
                or      a
                jr      z,svp_fin
                ld      a,(hl)
                cp      '0'
                jr      c,svp_fin
                cp      '9'+1
                jr      nc,svp_fin
                sub     '0'                 ; A = digit 0..9
                push    hl                  ; guard the string cursor across the *10
                push    af                  ; save the digit
                ld      h,d
                ld      l,e                 ; HL = acc
                add     hl,hl               ; *2
                add     hl,hl               ; *4
                add     hl,hl               ; *8
                ex      de,hl               ; DE = acc*8 ; HL = acc
                add     hl,hl               ; HL = acc*2
                add     hl,de               ; HL = acc*10
                pop     af                  ; A = digit
                ld      d,0
                ld      e,a
                add     hl,de               ; HL = acc*10 + digit
                ex      de,hl               ; DE = new acc
                pop     hl                  ; restore string cursor
                inc     hl
                dec     b
                jr      svp_digits
svp_fin:
                bit     0,c
                jr      z,svp_done          ; non-negative -> DE is the value
                ld      hl,0
                or      a
                sbc     hl,de               ; HL = -DE
                ex      de,hl               ; DE = negated value
svp_done:
                ret

; --- CHR$/STR$/LEFT$/RIGHT$/MID$: string-VALUED $FF functions ---------------
; Reached from str_eval_maybe_mki (basic/strvar.asm) via `jp str_func_ff` on a
; non-MKI$ $FF token (repack build only). Entered with HL on the selector byte and
; a string context wanting a value. On success each writes its result into a result-
; ring temp, points STRPTR at it, and joins str_eval_ok (VALTYP=1, CF set, HL past
; the call). A malformed call or a non-string $FF token falls to str_eval_no (CF
; clear) so the caller treats it as "not a string operand" (an error, or — in the
; numeric/PRINT path — a retry as a numeric factor).
str_func_ff:
                ld      a,(hl)
                cp      CHRD_TOKEN          ; $96 -> CHR$
                jp      z,str_fn_chr
                cp      STRD_TOKEN          ; $93 -> STR$
                jp      z,str_fn_str
                cp      LEFTD_TOKEN         ; $81 -> LEFT$
                jp      z,str_fn_left
                cp      RIGHTD_TOKEN        ; $82 -> RIGHT$
                jp      z,str_fn_right
                cp      MIDD_TOKEN          ; $83 -> MID$
                jp      z,str_fn_mid
                dec     hl                  ; restore HL to the $FF prefix
                jp      str_eval_no         ; unknown $FF function -> not a string operand

; CHR$(n): a 1-byte string of the low 8 bits of n (own-design leniency — MSX errors
; on n>255; zerobas is integer-only-lenient and takes E, like its other verbs).
str_fn_chr:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = n; HL advanced (IX preserved)
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl                  ; HL past ')'
                push    hl                  ; guard cursor across the temp write
                ld      a,e                 ; A = the char (low byte of n)
                push    af
                call    str_alloc_temp      ; HL = temp (clobbers A,DE)
                pop     af                  ; A = char
                ld      (hl),1              ; length = 1
                inc     hl
                ld      (hl),a              ; the byte
                dec     hl                  ; HL = temp base
                ld      (STRPTR),hl
                pop     hl                  ; restore cursor
                jp      str_eval_ok

; STR$(n): the decimal text of n. Leading blank for non-negative n (MSX format);
; the '-' for a negative is emitted by pu_fmt_int. Reuses print.asm's div10 via
; pu_fmt_int (NUMBUF = "[-]digits",0, B = digit count) — no perturbation of the
; existing PRINT/USING paths (they keep their own entry points).
str_fn_str:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = n
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl                  ; HL past ')'
                push    hl                  ; guard cursor
                ld      c,0                 ; C = leading-space count
                bit     7,d                 ; sign of n
                jr      nz,sfs_conv         ; negative -> no leading space
                inc     c                   ; non-negative -> one leading space
sfs_conv:
                call    pu_fmt_int          ; NUMBUF="[-]digits",0; B=digit count; C preserved
                call    str_alloc_temp      ; HL = temp base (clobbers A,DE; B,C survive)
                push    hl                  ; save temp base
                ld      a,c
                add     a,b                 ; total length = leading space + digits
                ld      (hl),a
                inc     hl                  ; -> temp bytes
                ld      a,c
                or      a
                jr      z,sfs_digits
                ld      (hl),' '            ; leading blank
                inc     hl
sfs_digits:
                ld      de,NUMBUF
sfs_cp:
                ld      a,(de)
                ld      (hl),a
                inc     de
                inc     hl
                djnz    sfs_cp              ; B = digit count (>=1)
                pop     hl                  ; HL = temp base
                ld      (STRPTR),hl
                pop     hl                  ; restore cursor
                jp      str_eval_ok

; LEFT$(a$,n): the first min(n,len) bytes. Dup the source into a temp, then truncate.
str_fn_left:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    str_eval            ; STRPTR -> source; HL advanced; CF=ok
                jp      nc,str_eval_no
                push    hl                  ; save cursor@','
                call    str_dup_temp        ; STRPTR -> temp copy of source; HL=temp
                pop     hl
                ld      a,(hl)
                cp      ','
                jp      nz,str_eval_no
                inc     hl
                ld      bc,(STRPTR)         ; BC = temp addr
                push    bc                  ; save it across the numeric eval
                call    eval                ; DE = n
                pop     bc                  ; BC = temp addr
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl                  ; HL = cursor past ')'
                push    hl                  ; save cursor
                ld      l,c
                ld      h,b                 ; HL = temp addr (kept through the clamp)
                ld      (STRPTR),hl         ; STRPTR = temp (eval may have moved it)
                ld      a,(bc)              ; A = templen
                ld      b,d
                ld      c,e                 ; BC = n (the requested count)
                call    str_min_bc          ; A = min(templen, n) ; preserves HL=temp
                ld      e,a                 ; E = count
                ld      d,0                 ; D = start = 0 (LEFT$ -> pure truncation)
                ld      b,h
                ld      c,l                 ; BC = temp addr
                call    str_temp_slice
                pop     hl                  ; restore cursor
                jp      str_eval_ok

; RIGHT$(a$,n): the last min(n,len) bytes. Dup, then slice from (len-count).
str_fn_right:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    str_eval
                jp      nc,str_eval_no
                push    hl
                call    str_dup_temp
                pop     hl
                ld      a,(hl)
                cp      ','
                jp      nz,str_eval_no
                inc     hl
                ld      bc,(STRPTR)
                push    bc
                call    eval                ; DE = n
                pop     bc
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl
                push    hl
                ld      l,c
                ld      h,b                 ; HL = temp addr (kept through the clamp)
                ld      (STRPTR),hl         ; STRPTR = temp
                ld      a,(bc)              ; templen
                ld      b,d
                ld      c,e                 ; BC = n (the requested count)
                call    str_min_bc          ; A = count = min(templen, n) ; HL=temp preserved
                ld      e,a                 ; E = count
                ld      a,(hl)              ; templen (HL still = temp base)
                sub     e                   ; A = start = templen - count
                ld      d,a                 ; D = start
                ld      b,h
                ld      c,l                 ; BC = temp addr
                call    str_temp_slice
                pop     hl
                jp      str_eval_ok

; MID$(a$,p[,n]): count bytes from 1-based position p (or to end if n omitted).
; p<1 is clamped to the start; p>len yields "". Dup, then slice.
str_fn_mid:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    str_eval            ; STRPTR -> source
                jp      nc,str_eval_no
                push    hl
                call    str_dup_temp        ; STRPTR -> temp copy; HL=temp
                pop     hl
                ld      a,(hl)
                cp      ','
                jp      nz,str_eval_no
                inc     hl
                ld      bc,(STRPTR)
                push    bc                  ; [temp]
                call    eval                ; DE = p (1-based)
                push    de                  ; [temp][p]
                ld      a,(hl)
                cp      ','
                jr      z,sfm_haveN
                ld      de,$FFFF            ; n omitted -> "to end" (clamps to avail)
                jr      sfm_close
sfm_haveN:
                inc     hl
                call    eval                ; DE = n (count)
sfm_close:
                ld      a,(hl)
                cp      ')'
                jr      nz,sfm_reject2      ; unbalance-safe: pop [temp][p] first
                inc     hl                  ; HL = cursor past ')'
                ld      b,d
                ld      c,e                 ; BC = requested count (n or $FFFF)
                pop     de                  ; DE = p           stack: [temp]
                ld      a,d
                or      e
                jr      z,sfm_start         ; p==0 -> start 0 (DE already 0)
                dec     de                  ; DE = p-1 (desired 0-based start)
sfm_start:
                ex      (sp),hl             ; HL = temp addr; stack top := cursor
                ld      a,(hl)              ; A = templen
                push    hl                  ; [cursor][temp]
                ld      h,a                 ; H = templen (scratch)
                ld      a,d
                or      a
                jr      nz,sfm_clampmax     ; start high byte set -> beyond end
                ld      a,e
                cp      h                   ; start(low) - templen
                jr      c,sfm_starthave     ; start < templen
sfm_clampmax:
                ld      a,h                 ; start = templen (avail becomes 0 -> "")
sfm_starthave:
                ld      d,a                 ; D = clamped start (0..templen)
                ld      a,h                 ; templen
                sub     d                   ; A = avail = templen - start
                call    str_min_bc          ; A = count = min(avail, requested)
                ld      e,a                 ; E = count
                pop     bc                  ; BC = temp addr    stack: [cursor]
                ld      l,c
                ld      h,b
                ld      (STRPTR),hl         ; STRPTR = temp (before the slice clobbers BC)
                call    str_temp_slice      ; in-place slice [start..start+count)
                pop     hl                  ; restore cursor
                jp      str_eval_ok
sfm_reject2:
                pop     bc                  ; discard p
                pop     bc                  ; discard temp
                jp      str_eval_no

; --- exp_maybe_strfn: PRINT hook for the string-VALUED $FF functions --------
; Reached from exp_loop (basic/print.asm) when a PRINT item begins with a $FF
; function token (repack build only). Try the string path first — CHR$/STR$/LEFT$/
; RIGHT$/MID$/MKI$ succeed and print; a numeric $FF function (PEEK/…) fails cleanly
; (str_func_ff restores HL to the $FF), so we fall back to exp_num.
exp_maybe_strfn:
                call    str_eval            ; STRPTR -> value; HL advanced; CF=ok
                jp      nc,exp_num          ; not a string function -> numeric factor
                push    hl                  ; print_strval clobbers HL (token cursor)
                call    print_strval
                pop     hl
                jp      exp_loop

; ===========================================================================
; string-compare S2 (repack build only): the six relational operators on two
; string operands (spec-basic-string-compare.md). Reused spine: ev_rel (expr.asm)
; already factors a comparison into "requested bits" (relop_bit + the compound-
; form merge) AND'd against an "actual bit" (1=less/2=equal/4=greater) from the
; two operands -- today cmp16_bits. This substitutes ONE thing: an UNSIGNED-BYTE
; string comparator (str_cmp_bits) producing that same 1/2/4 encoding, plus a
; type-mismatch signal (D-2) when a string meets a non-string.
;
; Clean-room: original code. Comparison SEMANTICS (unsigned byte-by-byte,
; shorter-is-less, case-sensitive, §2 D-3) are the standard MSX-BASIC string-
; ordering contract (public language reference), oracle-locked black-box on the
; Philips VG-8020 (probes/basic/basic_probe_str_cmp.py) -- not assumed. The
; relation-bit encoding is zerobas's own (matches cmp16_bits, expr.asm). No
; disassembly.
; ===========================================================================

; --- str_cmp_bits: UNSIGNED byte-by-byte compare of two [len][bytes] descriptors
; in: HL = lhs descriptor, DE = rhs descriptor.
; out: A = 1 (lhs<rhs) / 2 (equal) / 4 (lhs>rhs) -- the same encoding cmp16_bits
;      (expr.asm) produces for the numeric path, so the caller's `and c` (requested
;      vs actual) is unchanged. Compares corresponding bytes by raw unsigned value;
;      at the first differing byte the smaller byte's string is less (spec §2.1);
;      if all shared bytes match, the SHORTER string is less (§2.2); same length +
;      all bytes equal -> equal (§2.3). Case-sensitive: no folding (§2.4).
; Preserves BC (the caller keeps its requested-bits register in C across the call).
; Clobbers A, DE, HL, flags.
str_cmp_bits:
                push    bc                  ; guard the caller's C (requested bits)
                ld      a,(hl)              ; A = lhslen
                ld      b,a                 ; B = lhslen (temp, for the tie-break)
                ld      a,(de)              ; A = rhslen
                ; Tie-break bit (used only if every compared byte matches): the
                ; SHORTER string is less (§2.2); equal lengths -> equal (§2.3).
                cp      b                   ; A(rhslen) - B(lhslen)
                jr      z,scb_tb_eq
                jr      c,scb_tb_gt         ; rhslen < lhslen -> lhs is the longer -> lhs>rhs
                ld      a,1                 ; rhslen > lhslen -> lhs is the shorter -> lhs<rhs
                jr      scb_tb_push
scb_tb_eq:
                ld      a,2
                jr      scb_tb_push
scb_tb_gt:
                ld      a,4
scb_tb_push:
                push    af                  ; stash the tie-break bit across the byte scan
                ; minlen = min(lhslen, rhslen) via the existing str_min_bc helper
                ; (preserves BC/DE/HL); re-read both lengths fresh (A was clobbered above).
                ld      a,(de)              ; A = rhslen
                ld      c,a
                ld      b,0                 ; BC = rhslen (str_min_bc's "count")
                ld      a,(hl)              ; A = lhslen (str_min_bc's "length")
                call    str_min_bc          ; A = min(lhslen, rhslen)
                ld      b,a                 ; B = minlen (loop counter)
                inc     hl                  ; HL -> lhs bytes
                inc     de                  ; DE -> rhs bytes
                ld      a,b
                or      a
                jr      z,scb_tie           ; minlen 0 -> nothing to compare
scb_loop:
                ld      a,(de)              ; A = rhsbyte
                cp      (hl)                ; vs lhsbyte (raw unsigned compare)
                jr      z,scb_eqbyte
                jr      c,scb_gt            ; rhsbyte < lhsbyte -> lhs > rhs
                jr      scb_lt              ; rhsbyte > lhsbyte -> lhs < rhs
scb_eqbyte:
                inc     hl
                inc     de
                djnz    scb_loop
scb_tie:
                pop     af                  ; A = the stashed tie-break bit
                pop     bc                  ; restore the caller's bits (C)
                ret
scb_gt:
                pop     af                  ; discard the stashed tie-break bit
                ld      a,4
                pop     bc
                ret
scb_lt:
                pop     af
                ld      a,1
                pop     bc
                ret

; --- type_mismatch_set: D-2's comparator-level signal ------------------------
; A string on one side of a relational and a non-string on the other (or a bare
; string LHS with no relop at all) -- sets ERRMARK (the generic expression-error
; landmark, ev_f_err's convention) plus the distinct TMISMATCH marker, and yields
; 0 (false). This does NOT abort the line itself: ev_rel has no mid-expression
; unwind (every existing evaluator error works this way -- see ev_f_err), so the
; real abort happens at the STATEMENT boundary, once eval() returns, via the
; repack-gated post-eval check in ex_if / the numeric-assignment / PRINT-item
; drivers (interp.asm / print.asm) jumping to type_mismatch_error (interp.asm).
; out: DE = 0; ret. Clobbers A.
type_mismatch_set:
                ld      a,$DD               ; expression-error marker (ev_f_err convention)
                ld      (ERRMARK),a
                ld      a,1
                ld      (TMISMATCH),a
                ld      de,0
                ret

; --- ev_rel_str: the string-compare path of ev_rel --------------------------
; Reached from expr.asm's ev_rel (a near-zero-byte gated hook there) when the LHS
; of a relational probes as a string operand (str_eval succeeded). Entered with
; HL = cursor past the LHS operand, STRPTR -> the LHS descriptor.
;
; Snapshots the LHS into a ring temp (str_dup_temp -- D-4's "reuse a temp-ring
; slot" -- the same dup-then-operate discipline the substring verbs use) so
; evaluating the RHS can't clobber it via STRSCR or a reused ring slot (e.g. two
; literal operands would otherwise BOTH land in STRSCR and the second overwrites
; the first before the compare). Reads the relop token(s) with the EXISTING
; relop_bit + compound-form merge (<=/>=/<> fall out unchanged), evaluates the RHS
; via str_eval, then compares with str_cmp_bits and joins the numeric path's
; convention (`and c` -> -1/0).
;
; A bare string LHS with no following relop, or a non-string RHS (`A$ < 5`), is
; D-2's type mismatch -> type_mismatch_set (yields 0, ERRMARK+TMISMATCH set).
; out: DE = -1/0; ret. Clobbers A, BC, DE, HL (like the numeric ev_rel body).
ev_rel_str:
                push    hl
                pop     ix                  ; IX = cursor (bridge back)
                call    str_dup_temp        ; HL = LHS snapshot in a ring temp (D-4)
                push    hl                  ; guard the LHS temp addr across the RHS parse
                call    ev_sp
                ld      a,(ix+0)
                call    relop_bit
                jp      nc,ers_mismatch     ; bare string LHS, no relop -> D-2
                ld      c,b                 ; C = requested relation bits
                inc     ix
                call    ev_sp
                ld      a,(ix+0)
                call    relop_bit           ; a second relop? (<=, >=, <>)
                jr      nc,ers_rhs
                ld      a,c
                or      b
                ld      c,a                 ; merge the two relation bits
                inc     ix
ers_rhs:
                push    bc                  ; guard the bits across the RHS eval
                push    ix
                pop     hl
                call    str_eval            ; STRPTR -> RHS desc, HL advanced, CF=ok
                pop     bc                  ; C = bits (POP doesn't touch flags)
                jp      nc,ers_mismatch     ; RHS not a string -> D-2 (`A$ < 5`)
                push    hl                  ; save the cursor (past the RHS)
                ld      hl,(STRPTR)         ; HL = RHS descriptor addr
                ex      (sp),hl             ; stack top := RHS desc addr; HL = cursor
                push    hl
                pop     ix                  ; IX = cursor (bridge back)
                pop     de                  ; DE = RHS descriptor addr
                pop     hl                  ; HL = LHS descriptor addr (the snapshot)
                call    str_cmp_bits        ; A = actual relation bit (1/2/4); preserves C
                and     c                   ; intersect requested with actual
                jr      z,ers_false
                ld      de,$FFFF            ; true = -1
                ret
ers_false:
                ld      de,0                ; false = 0
                ret
ers_mismatch:
                pop     hl                  ; discard the guarded LHS temp addr
                jp      type_mismatch_set
