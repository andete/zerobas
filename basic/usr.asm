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

; --- ex_def: DEF USR[n] = <addr> / DEFSNG|DBL|STR <ranges> ------------------
; HL -> the DEF token. `DEF USR` (USR is its own token, $DD) stores a machine-
; code vector. In the repack build the `DEFSNG/DEFDBL/DEFSTR` forms are also
; handled (ex_def_type below): those mnemonics are NOT keyword tokens (only
; "DEF" is), so after the DEF token they arrive as plain upcased ASCII text
; ("SNG"/"DBL"/"STR") -- exactly why no new sub-ROM kwtable entry is needed for
; them. DEFINT does NOT reach here any more (D-DEFINTTOK): it has its own
; token, DEFINT_TOKEN, and its own dispatch entry (ex_defint, below) --
; ex_def only ever sees DEF_TOKEN. Anything else this routine sees (incl. DEF
; FN) hits stmt_error. On success continues the line.
ex_def:
                inc     hl                  ; past the DEF token
                call    skip_spaces
                cp      USR_TOKEN           ; DEF USR -> machine-code vector
                jp      nz,ex_def_type      ; else DEFINT/SNG/DBL/STR (or stmt_error)
                inc     hl                  ; past USR
                call    usr_index           ; A = vector index 0..9 (HL advanced)
                push    af                  ; save index across '=' + eval
                call    skip_spaces
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
                call    ev_logic            ; DE = argument (full expression)
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jr      nz,ev_usr_err
                inc     ix
                call    flt_int_result      ; USR returns an int even if its arg was a
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

; --- ex_defint: DEFINT <ranges> (D-DEFINTTOK) -------------------------------
; HL -> the DEFINT_TOKEN token itself (interp.asm's dispatch table hands the
; statement's own token, not the char after it -- unlike ex_def_type below,
; which is entered mid-mnemonic-parse from ex_def). DEFINT crunches to its own
; single byte now ($AC, oracle-pinned against the Philips VG-8020 -- see
; kwtable.inc's "DEFINT" row), so there is no "INT" mnemonic text left in the
; buffer to skip; advancing past the token lands directly on the range-list
; text (e.g. " A-Z"), and that is the ONLY thing this entry point needs to do
; before falling straight into ex_def_type's body below -- see there for how
; the tenant tells the two callers apart.
;
; BYTE-BUDGET NOTE: main page 1 sits within single-digit bytes of the $8000
; ceiling (docs/rom-region-structure-review.md), so this is deliberately a
; ONE-INSTRUCTION entry point, not a small ABI setup dance. An earlier draft
; had this set a dedicated `DEFT_PRESET` memory-ABI byte (extending
; DEFT_PTR/DEFT_STATUS, basic/sysvars.inc) before falling in; it worked, but
; cost a `ld a,n`/`ld (nn),a` pair here PLUS a cold-boot reset in `init`
; (basic/interp.asm) to keep power-on RAM garbage from being misread as a
; preset -- about 9 B this window measurably did not have. See ex_def_type's
; comment for the free mechanism that replaced it.
ex_defint:
                inc     hl                  ; past the DEFINT token -> range-list text
                ; falls into ex_def_type: HL is exactly the cursor it expects

; --- ex_def_type: DEFSNG|DEFDBL|DEFSTR <ranges> (DEFINT: see ex_defint above) -
; (repack build only; docs/spec-basic-float-core.md §11.1) Reached two ways:
; falling through from ex_defint just above (HL -> the range-list text, one
; past DEFINT_TOKEN), or jumped to from ex_def with HL -> the first char after
; the DEF token (skip_spaces already done): the mnemonic SNG/DBL/STR as
; upcased ASCII (these are not keyword tokens; DEFINT USED to arrive the same
; way, as "INT", but has its own token and its own entry point now --
; D-DEFINTTOK). Parse the mnemonic -> a type code in C (4 single / 8 double /
; DEFTBL_STR string), then a comma-list of `letter` or `letter-letter` range
; items, writing that code into DEFTBL for every first-letter in each range. On
; success continues the line; a malformed mnemonic / empty or reversed range ->
; stmt_error. The DEFtbl is consulted at every later variable reference
; (var_name_key / var_str_type), so redeclaring a letter orphans values held
; under its old type (spec §11.1). Clobbers A,B,C,D,E,H,L.
;
; TELLING THE TWO CALLERS APART COSTS NOTHING NEW (D-DEFINTTOK): deftype_tenant
; (sub/deftype.asm) peeks at the byte ONE BELOW the cursor it is handed,
; `(DEFT_PTR-1)`. Down the ex_defint path that byte is DEFINT_TOKEN itself (the
; one instruction there did nothing but `inc hl` past it). Down THIS path it
; never can be: ex_def's own `inc hl` + `skip_spaces` leave that byte as either
; DEF_TOKEN ($97) or an ASCII space ($20), and DEFINT_TOKEN is $AC -- disjoint
; from both, and from every ASCII mnemonic letter this path's own dispatch
; already requires ('I'/'S'/'D'). No flag byte, no cold-boot reset, no new
; sub-ROM ABI cell; the peek is free in the sub-ROM (which has room) and the
; main-ROM side spends nothing beyond ex_defint's one `inc hl`.
ex_def_type:
                ; The body is a page-0 sub-ROM tenant (docs/spec-eviction-g6-space.md):
                ; DEFtype is a pure parse + DEFTBL fill with no BIOS and no float
                ; work, so its whole closure stays off page 0 -- the one thing a
                ; page-0 tenant may not touch. It is also a COLD path (a declaration
                ; run once at the top of a program), so the CALSLT round trip costs
                ; nothing that matters. HL (the token cursor) goes in and comes back
                ; through DEFT_PTR, since CALSLT clobbers the registers.
                ld      (DEFT_PTR),hl
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_DEFTYPE
                call    subrom_call
                jp      c,subrom_absent_error
                ld      a,(DEFT_STATUS)
                or      a
                jp      nz,stmt_error       ; malformed mnemonic / empty or reversed range
                ld      hl,(DEFT_PTR)       ; the tenant advanced the cursor
                jp      exec_stmt
