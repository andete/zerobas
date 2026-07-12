; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; usr.asm — DEF USR[n]=addr (statement) and USR[n](arg) (expression function).
;
;   DEFUSR[n] = <addr>      ; store a machine-code entry address (USR0..USR9)
;   x = USR[n](<arg>)       ; call that routine; the non-,R way a loader stub
;                           ; jumps into freshly BLOAD'ed code
;
; This is the other common loader-stub shape: `DEFUSR=&Hxxxx : … : A=USR(0)`
; instead of `BLOAD"…",R`. The vectors live in the documented USRTAB sysvar
; ($F39A, 10×2 bytes; see sysvars.inc), so DEF USR is observable and matches the
; real home of the value.
;
; Tokens (MSX2 Technical Handbook Table 2.20): DEF = $97, USR = $DD. In the
; crunched stream `DEFUSR` is two tokens ($97 $DD), exactly as a real ROM crunches
; it; an optional USR number 0..9 follows as a digit token ($11+n).
;
; CALLING CONVENTION (own design — see note): zerobas is integer-only and has no
; floating-point DAC, so it does not use MSX-BASIC's DAC/VALTYP argument protocol.
; Instead USR[n](arg) evaluates the 16-bit integer argument into HL and CALLs the
; routine; the value the routine leaves in HL becomes the function result. A
; never-returning routine (the typical "the game takes over" case) simply never
; RETs, which is fine. This is sufficient for loader stubs, where the argument and
; return value are usually `0`/ignored. The reference convention is now
; oracle-measured (basic_probe_usr.py, black-box differential vs Philips VG-8020):
; the reference passes an integer arg in DAC+2..3 (16-bit LE at offset 2 of the
; 8-byte DAC $F7F6), sets VALTYP ($F663)=$02, and enters with HL->DAC base.
; zerobas instead passes the arg directly in HL and leaves DAC/VALTYP untouched —
; a deliberate own-design divergence (observed outputs only; no disassembly).
;
; Clean-room: original code; DEF USR / USR *semantics* from the public MSX-BASIC
; language reference; tokens from Table 2.20; USRTAB from C-BIOS sysvars. No
; disassembly.

; --- clear_usrtab: zero the 10 USR vectors at boot --------------------------
; Makes an un-DEF'd USR reliably read 0 (so usr_call can refuse to jump to a
; stray address — jumping to $0000 would reset the machine). Called from init.
clear_usrtab:
                ld      hl,USRTAB
                ld      b,20                ; 10 vectors * 2 bytes
                xor     a
cut_lp:
                ld      (hl),a
                inc     hl
                djnz    cut_lp
                ret

; --- ex_def: DEF USR[n] = <addr> / DEFINT|SNG|DBL|STR <ranges> --------------
; HL -> the DEF token. `DEF USR` (USR is its own token, $DD) stores a machine-
; code vector. In the repack build the `DEFINT/DEFSNG/DEFDBL/DEFSTR` forms are
; also handled (ex_def_type below): those mnemonics are NOT keyword tokens (only
; "DEF" is), so after the DEF token they arrive as plain upcased ASCII text
; ("INT"/"SNG"/"DBL"/"STR") -- exactly why no new sub-ROM kwtable entry is
; needed. Anything else (incl. DEF FN, and every DEF form in the lean build)
; hits stmt_error. On success continues the line.
ex_def:
                inc     hl                  ; past the DEF token
                call    skip_spaces
                ld      a,(hl)
                cp      USR_TOKEN           ; DEF USR -> machine-code vector
    IF ROM_BASE < $4000
                jp      nz,ex_def_type      ; else DEFINT/SNG/DBL/STR (or stmt_error)
    ELSE
                jp      nz,stmt_error       ; lean: only DEF USR
    ENDIF
                inc     hl                  ; past USR
                call    usr_index           ; A = vector index 0..9 (HL advanced)
                push    af                  ; save index across '=' + eval
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' crunches to $EF
                jr      nz,ex_def_err
                inc     hl
                call    eval                ; DE = entry address, HL = cursor
                pop     af                  ; A = index
                push    hl                  ; guard cursor across the store
                call    usr_setslot         ; USRTAB[index] = DE
                pop     hl
                jp      exec_stmt           ; continue the line
ex_def_err:
                pop     af                  ; discard saved index
                jp      stmt_error

; --- usr_index: read an optional USR number 0..9 from (HL) ------------------
; out: A = index (0 if none present); HL advanced past a digit token if taken.
; The number crunches to a digit token ($11..$1A). (Only 0..9 are valid USR
; numbers, so the one-byte $0F form never arises here.)
usr_index:
                call    skip_spaces
                ld      a,(hl)
                cp      INT_DIGIT_BASE      ; $11
                jr      c,usi_dflt
                cp      $1A+1               ; $11..$1A -> digits 0..9
                jr      nc,usi_dflt
                sub     INT_DIGIT_BASE      ; A = 0..9
                inc     hl
                ret
usi_dflt:
                xor     a                   ; default USR0
                ret

; --- usr_setslot: USRTAB[A] = DE -------------------------------------------
; Clobbers A, BC, HL. (Caller guards the token cursor.)
usr_setslot:
                add     a,a                 ; index * 2
                ld      l,a
                ld      h,0
                ld      bc,USRTAB
                add     hl,bc               ; HL = slot address
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

; --- ev_usr: USR[n](arg) factor (called from expr.asm ev_f, IX = cursor) ----
; in:  IX -> the USR token. out: DE = result, IX advanced past ')'.
ev_usr:
                inc     ix                  ; past USR token
                call    ev_usr_index        ; A = index 0..9 (IX advanced)
                push    af                  ; save index
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jr      nz,ev_usr_err
                inc     ix
                call    ev_xor              ; DE = argument (full expression)
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jr      nz,ev_usr_err
                inc     ix
    IF ROM_BASE < $4000
                call    flt_int_result      ; USR returns an int even if its arg was a
    ENDIF                                   ;  float (basic/float.asm; clobbers A only)
                pop     af                  ; A = index
                jp      usr_call            ; perform the call (preserves IX) -> DE
ev_usr_err:
                pop     af                  ; discard saved index
                ld      a,$DD               ; expression-error marker (cf. ev_f_err)
                ld      (ERRMARK),a
                ld      de,0
                ret

; --- ev_usr_index: optional USR number 0..9 from the IX stream -------------
ev_usr_index:
                call    ev_sp
                ld      a,(ix+0)
                cp      INT_DIGIT_BASE      ; $11
                jr      c,evui_dflt
                cp      $1A+1
                jr      nc,evui_dflt
                sub     INT_DIGIT_BASE
                inc     ix
                ret
evui_dflt:
                xor     a                   ; default USR0
                ret

; --- usr_call: call USRTAB[A] with HL=arg, capture HL as the result --------
; in:  A = index, DE = argument. out: DE = result. IX (the cursor) preserved.
; Refuses to jump if the vector is 0 (un-DEF'd) — a $0000 jump resets the MSX.
usr_call:
                push    ix                  ; the cursor must survive the routine
                add     a,a                 ; index * 2
                ld      l,a
                ld      h,0
                ld      bc,USRTAB
                add     hl,bc               ; HL = slot
                ld      c,(hl)
                inc     hl
                ld      b,(hl)              ; BC = routine address
                ld      a,b
                or      c
                jr      z,usr_undef         ; vector not set -> error, no jump
                ex      de,hl               ; HL = argument
                ld      de,usr_ret          ; continuation after the routine RETs
                push    de
                push    bc                  ; routine entry
                ret                         ; -> routine (HL=arg); its RET -> usr_ret
usr_ret:
                ex      de,hl               ; DE = result (whatever the routine left in HL)
                pop     ix                  ; restore the cursor
                ret
usr_undef:
                pop     ix                  ; restore the cursor
                ld      a,$DD               ; expression-error marker
                ld      (ERRMARK),a
                ld      de,0
                ret

    IF ROM_BASE < $4000
; --- ex_def_type: DEFINT|DEFSNG|DEFDBL|DEFSTR <ranges> ----------------------
; (repack build only; docs/spec-basic-float-core.md §11.1) HL -> the first char
; after the DEF token (skip_spaces already done): the mnemonic INT/SNG/DBL/STR
; as upcased ASCII (these are not keyword tokens). Parse the mnemonic -> a type
; code in C (2 int / 4 single / 8 double / DEFTBL_STR string), then a comma-list
; of `letter` or `letter-letter` range items, writing that code into DEFTBL for
; every first-letter in each range. On success continues the line; a malformed
; mnemonic / empty or reversed range -> stmt_error. The DEFtbl is consulted at
; every later variable reference (var_name_key / var_str_type), so redeclaring a
; letter orphans values held under its old type (spec §11.1). Clobbers A,B,C,D,
; E,H,L.
ex_def_type:
                ld      a,(hl)
                inc     hl
                cp      'I'
                jr      z,edt_i             ; INT
                cp      'S'
                jr      z,edt_s             ; SNG or STR
                cp      'D'
                jr      z,edt_d             ; DBL
edt_bad:
                jp      stmt_error
edt_i:                                      ; "I" -> expect "NT"
                ld      a,(hl)
                cp      'N'
                jr      nz,edt_bad
                inc     hl
                ld      a,(hl)
                cp      'T'
                jr      nz,edt_bad
                inc     hl
                ld      c,2                 ; int
                jr      edt_list
edt_s:                                      ; "S" -> "NG" (single) or "TR" (string)
                ld      a,(hl)
                inc     hl
                cp      'N'
                jr      z,edt_sn
                cp      'T'
                jr      nz,edt_bad
                ld      a,(hl)              ; "ST" -> expect 'R'
                cp      'R'
                jr      nz,edt_bad
                inc     hl
                ld      c,DEFTBL_STR        ; string
                jr      edt_list
edt_sn:                                     ; "SN" -> expect 'G'
                ld      a,(hl)
                cp      'G'
                jr      nz,edt_bad
                inc     hl
                ld      c,4                 ; single
                jr      edt_list
edt_d:                                      ; "D" -> expect "BL"
                ld      a,(hl)
                cp      'B'
                jr      nz,edt_bad
                inc     hl
                ld      a,(hl)
                cp      'L'
                jr      nz,edt_bad
                inc     hl
                ld      c,8                 ; double
                ; fall through to edt_list
; --- range-list parser: C = type code (preserved by skip_spaces/is_letter/upcase)
edt_list:
edt_item:
                call    skip_spaces
                ld      a,(hl)
                call    is_letter           ; each item must start with a letter
                jr      nc,edt_bad
                call    upcase
                ld      b,a                 ; B = range-start letter
                inc     hl
                ld      d,b                 ; D = range-end (default = start, single letter)
                call    skip_spaces
                ld      a,(hl)
                cp      MINUS_TOKEN         ; "X-Y" range? ('-' crunched to $F2)
                jr      nz,edt_fill
                inc     hl                  ; past '-'
                call    skip_spaces
                ld      a,(hl)
                call    is_letter
                jr      nc,edt_bad
                call    upcase
                ld      d,a                 ; D = range-end letter
                inc     hl
edt_fill:
                ld      a,b                 ; start must not exceed end
                cp      d
                jr      z,edt_fill_go
                jr      nc,edt_bad          ; start > end -> reversed range, reject
edt_fill_go:
                push    hl                  ; guard the token cursor across the fill
                ld      a,d
                sub     b                   ; A = end - start (>= 0); compute the count
                inc     a                   ; NOW, before ld de,DEFTBL clobbers D (end)
                push    af                  ; count = span + 1, stashed across the addr calc
                ld      a,b
                sub     'A'
                ld      l,a
                ld      h,0
                ld      de,DEFTBL
                add     hl,de               ; HL -> DEFTBL[start]
                pop     af
                ld      b,a                 ; B = count
edt_fill_lp:
                ld      (hl),c              ; DEFTBL[letter] = type code
                inc     hl
                djnz    edt_fill_lp
                pop     hl                  ; restore the token cursor
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; more items?
                jr      z,edt_comma
                jp      exec_stmt           ; end of the list -> run the next statement
edt_comma:
                inc     hl                  ; past ','
                jr      edt_item
    ENDIF
