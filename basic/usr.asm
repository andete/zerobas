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
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; zf_lp and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
; ⚠️ ENTERED BY FALLTHROUGH, so this cannot become an `equ` -- a `jp`
; has to stay in its place. tools/dupspan_indep.py calls it SAFE-JP.
cut_lp:
                jp      zf_lp

; --- ex_def: DEF USR[n] = <addr> -------------------------------------------
; HL -> the DEF token. `DEF USR` (USR is its own token, $DD) stores a machine-
; code vector, and after D-DEFTYPETOK that is the ONLY thing DEF_TOKEN means:
; all four DEF<type> verbs crunch to their own tokens ($AB..$AE) and dispatch
; to ex_deftype below, so none of them arrives here as ASCII text any more.
; Anything after DEF that is not USR (incl. DEF FN) hits stmt_error. On
; success continues the line.
ex_def:
                inc     hl                  ; past the DEF token
                call    skip_spaces
                cp      USR_TOKEN           ; DEF USR -> machine-code vector
                jp      nz,stmt_error       ; DEF<type> has its own token now; DEF FN
                                            ; and anything else are syntax errors
                inc     hl                  ; past USR
                call    usr_index           ; A = vector index 0..9 (HL advanced)
                push    af                  ; save index across '=' + eval
                call    skip_spaces
                cp      EQ_TOKEN            ; '=' crunches to $EF
                jp     nz,ex_def_err
                inc     hl
                call    eval                ; DE = entry address, HL = cursor
                pop     af                  ; A = index
                push    hl                  ; guard cursor across the store
                call    usr_setslot         ; USRTAB[index] = DE
                pop     hl
                jp      exec_stmt           ; continue the line
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; ee_synerr_pop and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
ex_def_err      equ     ee_synerr_pop

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
usi_dflt:                                   ; ⚠️ SHARED: ev_usr_index's own default
                xor     a                   ; default USR0
                ret                          ; arm jr's here too (D-DEFTYPETOK trim)

; --- usr_setslot: USRTAB[A] = DE -------------------------------------------
; Clobbers A, HL. (Caller guards the token cursor.)
;
; ⚠️ THE INDEX ADD IS 8-BIT, AND THAT IS PROVED RATHER THAN HOPED (D-DEFTYPETOK
; funding trim). The obvious form -- `ld l,a` / `ld h,0` / `ld bc,USRTAB` /
; `add hl,bc` -- is a 16-bit add costing 8 B; it is only needed if the offset
; can carry out of the low byte, and here it cannot: the index is 0..9
; (usr_index / ev_usr_index clamp it to the $11..$1A digit tokens), so the
; offset is 0..18, and USRTAB's own low byte is $9A -- $9A + 18 = $AC, still
; inside the page. So the low byte alone can be added and H left as USRTAB's
; own. 6 B instead of 8, at BOTH slot sites (usr_call has the identical
; sequence), which is 4 of the 6 bytes that paid for DEFSNG/DEFDBL/DEFSTR's
; dispatch rows. The assert below is what keeps it proved: move USRTAB to an
; address whose low byte is above $ED and the BUILD says so, instead of this
; silently indexing into the wrong sysvar.
    IF (low USRTAB) + 18 > 255
                db      USRTAB_TOO_CLOSE_TO_A_PAGE_END__8BIT_SLOT_INDEX_WOULD_CARRY
    ENDIF
usr_setslot:
                add     a,a                 ; index * 2 (0..18)
                ld      hl,USRTAB
                add     a,l                 ; low byte only -- cannot carry (assert)
                ld      l,a                 ; HL = slot address
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
                cp      '('
                jr      nz,ev_usr_err
                inc     ix
                call    ev_logic            ; DE = argument (full expression)
                call    ev_sp
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
; ⚠️ THE DEFAULT ARM IS usr_index's, NOT A COPY (D-DEFTYPETOK funding trim).
; `evui_dflt` was a byte-identical `xor a` / `ret` sitting 83 B below usi_dflt
; -- inside jr range, so both arms simply target the one tail and the duplicate
; is gone (2 B of the 6 that paid for the DEF<type> dispatch rows). Safe
; because the tail touches NO index register: this routine walks IX and
; usr_index walks HL, but the shared code only sets A and returns, so neither
; cursor is in play. If usi_dflt ever grows past a `xor a`/`ret`, it must stay
; index-register-free or these two must split again.
ev_usr_index:
                call    ev_sp
                cp      INT_DIGIT_BASE      ; $11
                jr      c,usi_dflt
                cp      $1A+1
                jr      nc,usi_dflt
                sub     INT_DIGIT_BASE
                inc     ix
                ret

; --- usr_call: call USRTAB[A] with HL=arg, capture HL as the result --------
; in:  A = index, DE = argument. out: DE = result. IX (the cursor) preserved.
; Refuses to jump if the vector is 0 (un-DEF'd) — a $0000 jump resets the MSX.
usr_call:
                push    ix                  ; the cursor must survive the routine
                add     a,a                 ; index * 2 (0..18)
                ld      hl,USRTAB           ; 8-bit index add -- see usr_setslot's
                add     a,l                 ; assert for why no carry is possible
                ld      l,a                 ; HL = slot
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

; --- ex_deftype: DEFINT|DEFSNG|DEFDBL|DEFSTR <ranges> ----------------------
; (repack build only; docs/spec-basic-float-core.md §11.1) HL -> the statement's
; OWN token, one of DEFSTR/DEFINT/DEFSNG/DEFDBL ($AB..$AE) -- interp.asm's
; dispatch table hands the token itself, and all FOUR of its rows point here
; (D-DEFINTTOK brought DEFINT, D-DEFTYPETOK the other three). Each of the four
; crunches to a single byte matching the reference, so there is no mnemonic
; TEXT left in the buffer to parse: stepping over the token lands directly on
; the range-list text (e.g. " A-Z"). Which of the four it was is not lost --
; the tenant reads the token back (see below) to pick the type code. Then: a
; comma-list of `letter` or `letter-letter` range items, writing that code into
; DEFTBL for every first-letter in each range. On success continues the line; an
; empty or reversed range -> stmt_error. The DEFtbl is consulted at every later
; variable reference (var_name_key / var_str_type), so redeclaring a letter
; orphans values held under its old type (spec §11.1). Clobbers A,B,C,D,E,H,L.
;
; ⚠️ HOW THE TENANT LEARNS WHICH VERB THIS WAS, AND WHY IT COSTS NOTHING.
; deftype_tenant (sub/deftype.asm) reads the byte ONE BELOW the cursor it is
; handed, `(DEFT_PTR-1)`. That byte is always this statement's token, because
; the only thing this routine does before handing HL over is step over it --
; which is how the type survives the CALSLT that clobbers every register,
; without a flag byte, an ABI cell, or a cold-boot reset. A DEFT_PRESET cell
; was drafted first and MEASURED TOO EXPENSIVE for main page 1 (a `ld a,n`/
; `ld (nn),a` pair here plus a reset in `init`, ~9 B against the handful of
; bytes this window has). The peek needs none of that, and it is also what lets
; all four dispatch rows share ONE handler instead of needing four.
;
; ⚠️ THREE DISPATCH ROWS ARE THE ENTIRE MAIN-ROM COST OF DEFSNG/DEFDBL/DEFSTR.
; Everything else those three needed -- three kwtable rows and the token ->
; type-code lookup -- is SUB-ROM, which has room; this window does not.
ex_deftype:
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
