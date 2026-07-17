; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; str-engine.asm — the string expression engine (repack build only).
; ===========================================================================
; This file is assembled ONLY in the repack build (ROM_BASE < $4000), into the
; reclaimed page-0 low region ($2812-$3FFF). It is NOT part of the lean 16 KB
; basic.rom — the byte-full lean image keeps the minimal string-VALUE layer
; (basic/strvar.asm) and this file's callers fold back to str_eval_one there.
; See docs/spec-basic-arrays-slice4a-string-heap.md and basic/PROVENANCE.md.
;
; REVISED arrays slice-4a (docs/spec-basic-arrays-slice4a-string-heap.md):
; every string descriptor everywhere is now a uniform 3-byte [len:1][ptr:2]
; triple; `ptr` -> a body in the string HEAP (a compacting allocator in the
; sub-ROM tenant, sub/strheap.asm) OR somewhere stable outside it (a token-
; stream literal, STRSCR, STR_EMPTY, FLD_DESC). The old fixed N=3 STRTMP ring
; + STRCAT_R global accumulator are GONE, replaced by a temp-descriptor STACK
; (§6) whose entries own real heap bodies; the concat spine (§7) evaluates
; every operand into an owned temp BEFORE allocating the final result once,
; which structurally eliminates the STRCAT_R re-entrancy bug (retiring
; spec-basic-string-concat-nesting-fix.md).
;
; Clean-room: original code. Concatenation SEMANTICS (left-to-right,
; truncate the combined length) are from the public MSX-BASIC language
; reference; the temp-descriptor stack, the heap descriptor layout, and the
; GC are zerobas's own design (sub/strheap.asm's own header has the full
; provenance/deviation notes). No disassembly.
; ===========================================================================

; ===========================================================================
; String-heap glue (main-ROM side, spec §9/§10): the thin wrapper around the
; SUBROM_IDX_STRHEAP tenant (heap_alloc/GC live there, sub/strheap.asm) plus
; the temp-descriptor stack (§6) built on top of it. Every string-producing
; routine below (concat, the S4 functions) is built on str_temp_alloc /
; str_snapshot_to_temp.
; ===========================================================================

; --- call_strheap: dispatch to the string-heap tenant (SUBROM_IDX_STRHEAP) -
; Shared tail every SH_* glue wrapper below funnels through (13 call sites)
; instead of repeating "ld ix,.. / call subrom_call / jp c,subrom_absent_
; error" inline — this low region has no room to spare for the duplication.
; Clobbers A, IX.
call_strheap:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_STRHEAP
                call    subrom_call
                ret     nc
                jp      subrom_absent_error

; --- str_heap_alloc: A=len(0..255) -> CF set+HL=body ptr / CF clear=OOM ----
; Main-ROM glue for the string-heap tenant's ALLOC op (mirrors
; basic/arrays.asm's ary_engine_call). Clobbers A, DE, IX.
str_heap_alloc:
                ld      (SH_LEN),a
                xor     a
                ld      (SH_OP),a           ; op = 0 (ALLOC)
                call    call_strheap
                ld      a,(SH_ERR)
                or      a
                jr      nz,sha_oom
                ld      hl,(SH_PTR)
                scf
                ret
sha_oom:
                or      a                   ; CF clear
                ret

; --- str_heap_oom_error: raise "Out of memory" (FPERR=6 — the SAME code ----
; arrays' own OOM uses; the shared fre_msgtab entry, no new message).
str_heap_oom_error:
                ld      a,6
                ld      (FPERR),a
                jp      fp_runtime_error

; err_too_complex: fre_msgtab entry 9's string (interp.asm). MSX-authentic
; wording (the reference raises exactly this when its own temp-descriptor
; stack fills, §6/§11) — homed here (low region), not interp.asm's page 1
; (no slack there), same placement discipline as err_subscript et al
; (basic/arrays.asm).
err_too_complex:
                db      "String formula too complex",13,10,0

; ===========================================================================
; Shared low-region helpers (arrays slice-4a). Homed HERE (the reclaimed low
; region) rather than in their page-1 callers because page 1 is byte-full;
; page 1 reaches them by ordinary in-slot call (page 1 <-> low region are the
; main ROM's co-mapped slot-0 pages). NOT reachable from a page-0 sub-ROM
; tenant — but every caller is main-ROM page-1/low code, never a tenant.
; ===========================================================================

; --- heap_reset: reset the string heap + temp-descriptor stack to EMPTY -----
; FRETOP := C = min(HIMEM,TXTMAX); TEMPTOP := TEMPBASE. Called by clear_vars
; (vars.asm) at init/NEW/RUN/CLEAR — the single "variables wiped" hook (§2/§6).
; Clobbers A,B,C,H,L.
heap_reset:
                ld      hl,(HIMEM)
                ld      a,h
                or      l
                jr      z,hr_txtmax
                push    hl
                ld      bc,TXTMAX
                or      a
                sbc     hl,bc
                pop     hl
                jr      c,hr_have           ; HIMEM<TXTMAX -> ceiling=HIMEM
hr_txtmax:
                ld      hl,TXTMAX
hr_have:
                ld      (FRETOP),hl
                ld      hl,TEMPBASE
                ld      (TEMPTOP),hl
                ret

; --- pu_deref_body: HL = a [len:1][ptr:2] descriptor address (its len byte
; already consumed by the caller if needed) -> HL = its CURRENT body address
; (dereferences the ptr tail). The single shared "[len][ptr] -> bytes" reader
; for every page-1 string consumer (print_strval, PRINT USING string fields,
; LSET/RSET, CVI). Clobbers A.
pu_deref_body:
                inc     hl
                ld      a,(hl)              ; ptr-lo
                inc     hl
                ld      h,(hl)              ; ptr-hi
                ld      l,a                 ; HL = body
                ret

; --- mk_rvdesc: A = len, HL = body address -> RVDESC := [len][ptr(=body)];
; returns HL = RVDESC. The shared "wrap a fixed RAM buffer as a [len][ptr]
; rvalue descriptor" builder (STRSCR/FLD_DESC producers). Safe as ONE shared
; RVDESC cell only because each producer's value is consumed immediately
; (copied into a heap temp / a var's heap body) before the next string sub-
; expression reuses it. Clobbers A? no — preserves A. Clobbers nothing but the
; RVDESC cell + HL.
mk_rvdesc:
                ld      (RVDESC),a          ; RVDESC.len
                ld      (RVDESC+1),hl       ; RVDESC.ptr = body
                ld      hl,RVDESC
                ret

; --- strscr_desc: wrap the CURRENT STRSCR byte buffer as a [len][ptr] rvalue
; descriptor in RVDESC (RVDESC.len=(STRSCR), RVDESC.ptr=STRSCR+1). Used by
; every producer that fills STRSCR directly (MKI$/INPUT$/read_into_strscr
; callers). out: HL = RVDESC. Clobbers A.
strscr_desc:
                ld      a,(STRSCR)
                ld      hl,STRSCR+1
                jr      mk_rvdesc

; --- str_eval_lit (repack): a '"'-quoted literal -> a [len][ptr] rvalue -----
; descriptor over the literal's bytes IN PLACE in the tokenised line (§3:
; zero-copy — a literal is never mutated, so RVDESC.ptr points straight at
; the token stream; its ptr sits outside [FRETOP,C) so it is never a GC
; root). Entered with HL on the opening quote; advances HL past the closing
; quote. Homed in the low region (page 1 full); str_eval_one (strvar.asm)
; reaches it by jp. Joins str_eval_ok (page 1) on success. Clobbers A,B,DE,HL.
str_eval_lit:
                inc     hl                  ; past the opening quote; HL = literal[0]
                push    hl                  ; save the literal start
                ld      b,0                 ; B = length so far (clamped to STRMAX=255)
sel_lp:
                ld      a,(hl)
                or      a
                jr      z,sel_close         ; unterminated -> stop (treat EOL as end)
                cp      '"'
                jr      z,sel_close_q
                ld      a,b
                cp      STRMAX
                jr      nc,sel_skip         ; full: stop counting (scan on to the quote)
                inc     b
sel_skip:
                inc     hl
                jr      sel_lp
sel_close_q:
                inc     hl                  ; past the closing quote
sel_close:
                ; HL = cursor past the operand
                ld      a,b                 ; A = length
                pop     de                  ; DE = literal start (RVDESC.ptr target)
                push    hl                  ; guard the advanced cursor
                ex      de,hl               ; HL = literal start (mk_rvdesc's body)
                call    mk_rvdesc           ; RVDESC := [len][ptr]; HL = RVDESC
                ld      (STRPTR),hl
                pop     hl                  ; HL = cursor past the operand
                jp      str_eval_ok

; --- print_strval (repack): emit the [len][ptr] descriptor at STRPTR via -----
; pchar (screen or file per PRDEST). Homed in the low region (page 1 full);
; print.asm / printusing reach it by in-slot call. The lean build keeps its
; own inline [len][bytes] copy in strvar.asm. Clobbers A, B, HL.
print_strval:
                ld      hl,(STRPTR)
                ld      b,(hl)              ; B = length
                ld      a,b
                or      a
                ret     z                   ; empty string -> nothing to print
                call    pu_deref_body       ; HL = body
psv_lp:
                ld      a,(hl)
                call    pchar               ; screen or file (PRDEST); preserves all
                inc     hl
                djnz    psv_lp
                ret


; --- str_temp_alloc: A=length(0..255) -> push a temp-descriptor-stack ------
; entry owning a FRESH heap body of that length (§6/§7). Thin main-ROM glue
; for the string-heap tenant's TEMP_ALLOC op (mirrors str_heap_alloc) — the
; actual push+alloc mechanics moved to the sub-ROM (sub/strheap.asm
; she_temp_alloc/sh_temp_push_alloc) once this low region ran out of room
; for them; see the tenant's own header for the shape-C rationale (§9). out:
; HL = the new temp-stack descriptor address; DE = the heap body address to
; fill (0 if length 0). On ANY failure (temp-stack overflow -> FPERR=9
; "String formula too complex"; heap OOM -> FPERR=6 "Out of memory") sets
; FPERR and returns a NEUTRALISED len-0/ptr-0 entry instead of aborting here
; — matches the established deferred-error discipline (D-F2-1/ev_f_empty):
; every str_eval() caller already checks FPERR at the statement boundary, so
; the caller can keep going structurally and the abort still happens before
; any bad value is ever consumed. Clobbers A, DE, IX.
str_temp_alloc:
                ld      (SH_LEN),a
                ld      a,3
                ld      (SH_OP),a           ; op = 3 (TEMP_ALLOC)
                call    call_strheap
                ld      a,(SH_ERR)
                or      a
                jr      z,sta_ok
                cp      2
                jr      z,sta_overflow
                ld      a,6
                ld      (FPERR),a           ; "Out of memory" — the tenant still
                                            ; hands back a valid (neutralised)
                                            ; slot on this path
                ld      hl,(SH_PTR)
                ld      de,0
                ret
sta_ok:
                ld      hl,(SH_PTR)
                ld      de,(SH_PTR2)
                ret
sta_overflow:
                ld      a,9
                ld      (FPERR),a           ; "String formula too complex"
                ld      hl,STR_EMPTY        ; no slot was reserved -- STR_EMPTY is
                                            ; always a safe, never-a-GC-root fallback
                ld      de,0
                ret

; --- str_snapshot_to_temp: STRPTR -> some source descriptor (anywhere) -----
; push a NEW temp-stack entry OWNING a fresh heap-copied body, and repoint
; STRPTR at it. The general "snapshot an rvalue so it survives a later alloc/
; GC and so a shared mutable scratch (STRSCR) can't be clobbered by
; evaluating the next sub-expression" primitive — replaces the old
; str_dup_temp (ring-slot copy); SAME calling convention (out: HL = temp,
; STRPTR = temp), so every caller below is unchanged beyond the rename. Thin
; main-ROM glue for the tenant's SNAPSHOT op (same shape-C move as
; str_temp_alloc above; the copy itself happens tenant-side, she_snapshot).
; Clobbers A, DE, IX.
str_snapshot_to_temp:
                ld      hl,(STRPTR)
                ld      (SH_SRC),hl         ; source descriptor address (stable)
                ld      a,4
                ld      (SH_OP),a           ; op = 4 (SNAPSHOT)
                call    call_strheap
                ld      a,(SH_ERR)
                or      a
                jr      z,sst_ok
                cp      2
                jr      z,sst_overflow
                ld      a,6
                ld      (FPERR),a           ; "Out of memory"
                ld      hl,(SH_PTR)
                ld      (STRPTR),hl
                ret
sst_ok:
                ld      hl,(SH_PTR)
                ld      (STRPTR),hl
                ret
sst_overflow:
                ld      a,9
                ld      (FPERR),a           ; "String formula too complex"
                ld      hl,STR_EMPTY
                ld      (STRPTR),hl
                ret

; ===========================================================================
; Concat spine (§7): a running-ACCUMULATOR fold. Operand 1 becomes an owned
; temp R; each subsequent operand is appended onto R IN PLACE (sub-ROM op=2,
; sh_append). This is robust to an operand whose OWN evaluation pushes
; intermediate temps (a function operand, e.g. STR$(7), or the nested-concat
; case "A"+MID$("XY"+"Z",1,2)+"B") -- each operand is fully evaluated and
; appended before the next, so there is no "contiguous last-N temps"
; assumption to break. There is no shared mutable global accumulator (R is a
; per-expression temp), so the old STRCAT_R re-entrancy bug cannot recur
; (retires spec-basic-string-concat-nesting-fix.md).
; ===========================================================================

; --- str_concat_tail: fold trailing `+ operand` terms into R ---------------
; Entered by str_eval (basic/strvar.asm) AFTER operand 1: HL = cursor just
; past operand 1, STRPTR -> operand 1's descriptor, VALTYP = 1. If the next
; non-space token is '+', make operand 1 an owned temp R, then for each
; `+ operand`: evaluate it and append it onto R in place (op=2). The result
; is R. Otherwise leave STRPTR at operand 1 unchanged (single operand -- the
; zero-copy fast path). out: STRPTR -> result, VALTYP = 1, HL past the whole
; expression, CF set. CF clear if a trailing operand is malformed. Clobbers
; A, BC, DE, HL, IX (the sub-op stubs CALSLT).
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
                pop     bc                  ; HL already @ '+' (skip_spaces result)
                push    hl                  ; save cursor (@ '+')
                call    str_snapshot_to_temp ; operand 1 -> owned temp R; HL=R, STRPTR=R
                                            ; (unconditional: R must be a fresh temp we
                                            ; can modify in place -- never a var slot;
                                            ; a function-result op1 just costs one extra
                                            ; harmless temp)
                ex      (sp),hl             ; [R]; HL = cursor (@ '+')
sct_loop:
                inc     hl                  ; past the '+'
                call    skip_spaces         ; HL -> the next operand
                call    str_eval_one        ; STRPTR -> operand, HL = ADVANCED cursor, CF
                jr      nc,sct_err2         ; malformed operand -> clean [R]
                push    hl                  ; [R][advanced cursor] (save the ADVANCED
                                            ; cursor -- past the operand, not its start)
                ; append R += operand(STRPTR), in place
                ld      hl,(STRPTR)
                ld      (SH_SRC),hl         ; SH_SRC = the operand (any stable descriptor)
                pop     de                  ; DE = advanced cursor   [R]
                pop     hl                  ; HL = R                 [ ]
                ld      (SH_DEST),hl        ; SH_DEST = R (stable temp slot, modified in place)
                push    hl                  ; [R]
                push    de                  ; [R][cursor]
                ld      a,2
                ld      (SH_OP),a           ; op = 2 (APPEND)
                call    call_strheap
                ld      a,(SH_ERR)
                or      a
                jr      nz,sct_append_err   ; heap OOM / overflow -> [R][cursor]
                pop     hl                  ; HL = cursor            [R]
                call    skip_spaces
                ld      a,(hl)
                cp      PLUS_TOKEN
                jr      z,sct_loop          ; another '+': HL @ '+', [R] on stack
                ; no more terms -> result = R
                pop     de                  ; DE = R                 [ ]
                ex      de,hl               ; HL = R, DE = cursor
                ld      (STRPTR),hl         ; STRPTR = R (the result)
                ex      de,hl               ; HL = cursor
                scf
                ret
sct_err2:
                ; BUG C (Fable, 2026-07-17): a '+' COMMITTED this expression to
                ; string concatenation, but the trailing operand is non-string
                ; (`A$+5`, `A$+`). Returning bare NC let the caller silently
                ; re-drive the WHOLE thing as a number (PRINT A$+5 -> " 0"). Raise
                ; the DEFERRED Type mismatch instead: set ERRMARK+TMISMATCH so the
                ; driver's check_expr_errors aborts at the statement boundary (the
                ; same D-2 deferral the string comparator uses). Still return NC --
                ; the caller restores its own cursor, and on the numeric re-drive
                ; the TMISMATCH we set makes check_expr_errors abort with "type
                ; mismatch" rather than printing a bogus value.
                pop     hl                  ; discard R              [ ]
                call    type_mismatch_set   ; ERRMARK+TMISMATCH (DE=0); clobbers A
                or      a                   ; A=1 -> CF clear (malformed operand)
                ret
sct_append_err:
                ; SH_ERR = 1 (heap OOM) or 2 (temp overflow). Result = R (the
                ; partial accumulator, still valid); set FPERR so the statement-
                ; boundary check aborts before the value is consumed.
                pop     hl                  ; HL = cursor            [R]
                pop     de                  ; DE = R                 [ ]
                ld      (STRPTR),de         ; STRPTR = R (partial)
                ld      a,(SH_ERR)
                cp      2
                ld      a,6                 ; SH_ERR=1 -> "Out of memory"
                jr      nz,sct_ae_set
                ld      a,9                 ; SH_ERR=2 -> "String formula too complex"
sct_ae_set:
                ld      (FPERR),a
                scf                         ; CF set (a string operand WAS recognised;
                                            ; only its VALUE errored, deferred via FPERR)
                ret

; ===========================================================================
; S4 — the core string VERBS (repack build only): LEN/ASC/VAL (string->number)
; and CHR$/STR$/LEFT$/RIGHT$/MID$ (->string). Their keyword tokens are already
; crunched + LIST-detokenised (kwtable.inc, S3); these are the handlers.
;
; Clean-room: original code. The verb SEMANTICS (1-based MID$, LEFT$/RIGHT$ head/
; tail clamps, ASC "" = error, VAL's leading-parse, STR$'s leading blank for
; non-negatives) are from the public MSX-BASIC language reference. Divergences
; (integer-only VAL per spec D-E; CHR$ takes the low byte of n; results transit
; the heap-backed temp-descriptor stack, §6/§7) are zerobas's own design. No
; disassembly.
; ===========================================================================

; --- helpers ---------------------------------------------------------------

; str_min_bc: A = min(A, BC), treating A as a 0..255 length and BC as a 0..65535
; requested count. Used to clamp a LEFT$/RIGHT$/MID$ count to the bytes available.
; Preserves BC, DE, HL. Clobbers A + flags. Unchanged from pre-4a (a pure
; length compare, no descriptor-format dependency).
str_min_bc:
                inc     b
                dec     b                   ; test B (high byte of the count)
                ret     nz                  ; count >= 256 -> min is the length (A<=STRMAX)
                cp      c                   ; length - count(low)
                ret     c                   ; length < count -> length is the min (A)
                ld      a,c                 ; else the count is the min
                ret

; str_temp_slice: in the temp descriptor at BC, keep E bytes starting at
; offset D (0-based) of its CURRENT body, moving them to the front of that
; SAME body (already uniquely owned — no realloc needed, slicing only
; shrinks/moves within memory we already own) and setting the descriptor's
; length to E. Used by LEFT$ (start 0 -> pure truncation), RIGHT$ and MID$.
; Pre-validated so that start+count <= length and count <= STRMAX. in:
; BC = temp descriptor address, D = start, E = count. Clobbers A, BC, DE, HL.
; Thin main-ROM glue for the string-heap tenant's SLICE op (mirrors
; str_heap_alloc) — the byte-move mechanics moved to the sub-ROM
; (sub/strheap.asm she_slice) once this low region ran out of room for
; them; SAME calling convention (BC=temp descriptor, D=start, E=count), so
; every caller (str_fn_left/right/mid) is unchanged. Clobbers A, BC, DE, IX.
str_temp_slice:
                ld      (SH_SRC),bc
                ld      a,d
                ld      (SH_START),a
                ld      a,e
                ld      (SH_COUNT),a
                ld      a,5
                ld      (SH_OP),a           ; op = 5 (SLICE)
                call    call_strheap
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
                ; a $FF string-only token (LEFT$/RIGHT$/MID$ = $81/$82/$83, etc.)
                ; used where a NUMERIC factor is required. BUG C (Fable
                ; 2026-07-17): the old bare `jp ev_f_err` set only ERRMARK (which
                ; check_expr_errors does NOT inspect) and did NOT advance IX, so
                ; once ev_rel's fixed probe re-drives `LEFT$("AB")` numerically the
                ; PRINT item loop spun forever emitting " 0". Defer a real "syntax
                ; error" via ev_f_empty (sets FPERR=4, first-error-wins) so the
                ; driver's check_expr_errors aborts the statement.
                jp      ev_f_empty          ; deferred FPERR=4 "syntax error"

; ev_str_arg: parse "( <string-expr> )" from the IX token stream, leaving STRPTR ->
; the argument's descriptor and IX past ')'. Mirrors ev_ff_cvi's IX<->HL
; bridge. On a syntax/type error it does not return — it `jp ev_f_err` like every
; other factor error. Entered with IX on the function selector byte. UNCHANGED
; from pre-4a (format-agnostic — it only ever hands off to str_eval).
ev_str_arg:
                inc     ix                  ; skip the selector
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_empty
                inc     ix
                call    ev_sp
                ld      a,(ix+0)
                ; empty string-argument (LEN()/ASC()/VAL(), or a trailing ','):
                ; the same missing-operand syntax error as ev_f's ')'/',' gate
                ; (D-F2-3). Route to ev_f_empty so FPERR=4 is set on THIS eval --
                ; then the PRINT/LET driver's check_expr_errors aborts before the
                ; caller's stale-STRPTR read can print a garbage length/byte
                ; (spec-basic-empty-expr-syntax-error.md).
                cp      ')'
                jp      z,ev_f_empty
                cp      ','
                jp      z,ev_f_empty
                push    ix
                pop     hl                  ; HL = cursor
                call    str_eval            ; STRPTR -> desc; HL advanced; CF=ok
                ; BUG C class (Fable 2026-07-17): a NON-string arg -- LEN(5), or a
                ; NESTED malformed string fn LEN(LEFT$("AB")) whose str_eval CALSLT'd
                ; then exited NC -- used to `jp ev_f_err` (ERRMARK only, un-advanced
                ; IX): the caller then read a STALE STRPTR as the answer and dropped
                ; the statement tail. Defer FPERR=4 via ev_f_empty so the driver's
                ; check_expr_errors aborts (garbage IX/STRPTR then can't matter).
                jp      nc,ev_f_empty
                push    hl
                pop     ix                  ; IX = cursor past the string operand
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_empty
                inc     ix
                jp      flt_int_result      ; LEN/ASC/VAL return ints even when a float
                                            ; is nested in the string arg (float.asm F1;
                                            ; clobbers A only, then ret to the caller)
ev_ff_len:
                call    ev_str_arg          ; STRPTR -> desc
                ld      hl,(STRPTR)
                ld      e,(hl)              ; DE = descriptor length byte (still
                ld      d,0                 ; offset 0 in the new format — unchanged)
                ret
ev_ff_asc:
                call    ev_str_arg
                ld      hl,(STRPTR)
                ld      a,(hl)              ; length
                or      a
                jp      z,ev_f_err          ; ASC("") -> Illegal function call
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = ptr (the body address)
                ld      a,(de)              ; first byte of the body
                ld      e,a
                ld      d,0
                ret
ev_ff_val:
                call    ev_str_arg          ; STRPTR -> the string-arg descriptor;
                                            ; IX advanced past ')'
                ; VAL's leading-signed-decimal parse (integer-only, spec D-E)
                ; moved to the sub-ROM tenant (sub/strheap.asm sh_val_parse,
                ; op=13) — pure-RAM parse of (STRPTR)'s body, page-1/low both
                ; byte-full. Thin glue mirrors str_heap_alloc.
                ld      a,13
                ld      (SH_OP),a           ; op = 13 (VAL_PARSE)
                push    ix                  ; the CALSLT in call_strheap clobbers IX
                call    call_strheap        ; -- guard the token cursor ev_f needs back
                pop     ix
                ld      de,(SH_PTR)         ; DE = the parsed integer value
                ret

; --- CHR$/STR$/LEFT$/RIGHT$/MID$: string-VALUED $FF functions ---------------
; Reached from str_eval_maybe_mki (basic/strvar.asm) via `jp str_func_ff` on a
; non-MKI$ $FF token (repack build only). Entered with HL on the selector byte and
; a string context wanting a value. On success each pushes its result as a new
; temp-descriptor-stack entry, points STRPTR at it, and joins str_eval_ok
; (VALTYP=1, CF set, HL past the call). A malformed call or a non-string $FF
; token falls to str_eval_no (CF clear) so the caller treats it as "not a
; string operand" (an error, or — in the numeric/PRINT path — a retry as a
; numeric factor). Dispatch shell UNCHANGED from pre-4a.
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
                cp      HEXD_TOKEN          ; $9B -> HEX$
                jp      z,str_fn_hex
                cp      OCTD_TOKEN          ; $9A -> OCT$
                jp      z,str_fn_oct
                cp      SPACED_TOKEN        ; $99 -> SPACE$
                jp      z,str_fn_space
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
                ld      a,1
                ld      (SH_LEN),a          ; length = 1 (FILL op, same as
                ld      a,e                 ; SPACE$/STRING$ — shape-C follow-up)
                ld      (SH_FILLBYTE),a     ; fill byte = the char (low byte of n)
                ld      a,8
                ld      (SH_OP),a           ; op = 8 (FILL)
                call    call_strheap
                call    shx_finish          ; shared SH_ERR/SH_PTR -> STRPTR tail
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
                push    hl                  ; guard cursor                       [CURSOR]
                ld      c,0                 ; C = leading-space count
                bit     7,d                 ; sign of n
                jr      nz,sfs_conv         ; negative -> no leading space
                inc     c                   ; non-negative -> one leading space
sfs_conv:
                call    pu_fmt_int          ; NUMBUF="[-]digits",0; B=digit count; C preserved
                ld      a,c
                add     a,b                 ; total length = leading space + digits
                push    bc                  ; guard B(digits),C(leadspace)         [CURSOR][BC]
                call    str_temp_alloc      ; A=total -> HL=temp desc, DE=body (or 0)
                pop     bc                  ; B=digits, C=leadspace                [CURSOR]
                push    hl                  ; guard temp desc addr                  [CURSOR][TDESC]
                ld      a,d
                or      e
                jr      z,sfs_finish        ; failure -> DE=0, nothing to fill
                ld      a,c
                or      a
                jr      z,sfs_digits
                ld      a,' '
                ld      (de),a
                inc     de
sfs_digits:
                ld      hl,NUMBUF
sfs_cp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                djnz    sfs_cp              ; B = digit count (>=1)
sfs_finish:
                pop     hl                  ; HL = temp desc addr                    [CURSOR]
                ld      (STRPTR),hl
                pop     hl                  ; restore cursor                            [ ]
                jp      str_eval_ok

; LEFT$(a$,n): the first min(n,len) bytes. Snapshot the source into an owned
; temp, then truncate in place.
; str_arg_empty: an empty string-function first argument (LEFT$()/RIGHT$()/MID$(),
; or a leading ','). Raise the deferred "syntax error" (D-F2-3) like ev_f's ')'/','
; gate, then take the ordinary str_eval_no "not a string operand" exit -- the PRINT/
; LET driver's FPERR check (ems_print / check_expr_errors) then aborts the statement.
str_arg_empty:
                ld      a,4
                ld      (FPERR),a
                jp      str_eval_no
str_fn_left:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                ld      a,(hl)              ; empty first arg -> deferred syntax error
                cp      ')'
                jp      z,str_arg_empty
                cp      ','
                jp      z,str_arg_empty
                call    str_eval            ; STRPTR -> source; HL advanced; CF=ok
                jp      nc,str_eval_no
                push    hl                  ; save cursor@','
                call    str_snapshot_to_temp ; STRPTR -> owned temp copy; HL=temp
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

; RIGHT$(a$,n): the last min(n,len) bytes. Snapshot, then slice from (len-count).
str_fn_right:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                ld      a,(hl)              ; empty first arg -> deferred syntax error
                cp      ')'
                jp      z,str_arg_empty
                cp      ','
                jp      z,str_arg_empty
                call    str_eval
                jp      nc,str_eval_no
                push    hl
                call    str_snapshot_to_temp
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
; p<1 is clamped to the start; p>len yields "". Snapshot, then slice.
str_fn_mid:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                ld      a,(hl)              ; empty first arg -> deferred syntax error
                cp      ')'
                jp      z,str_arg_empty
                cp      ','
                jp      z,str_arg_empty
                call    str_eval            ; STRPTR -> source
                jp      nc,str_eval_no
                push    hl
                call    str_snapshot_to_temp ; STRPTR -> owned temp copy; HL=temp
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

; ===========================================================================
; MID$ STATEMENT (repack build only): MID$(A$,n[,m])=B$ -- overwrite a substring
; of A$ in place, per docs/spec-basic-mid-statement.md. The FUNCTION MID$(a$,p,n)
; (read) is str_fn_mid above; this is the ASSIGNMENT statement, dispatched from
; exec_stmt (basic/interp.asm) when a statement begins with the MID$ function token
; $FF $83 (the only $FF function that starts a statement).
;
; Contract (§2, oracle-locked black-box on the VG-8020): LEN(A$) NEVER changes; the
; replaced count k = min(m|Lb, Lb, La-n+1); bytes outside [n, n+k) are untouched.
; n<1 / n>La / m<0 are range errors -> stmt_error ("syntax error"; zerobas has no
; "Illegal function call", D-3). Target is a plain $-suffixed string var (FIELDed /
; array lvalues deferred). Reuses var_str_type/var_name_key (LHS), str_get_key (the
; in-place STRTAB descriptor), eval (n/m), str_eval (RHS). Clean-room: original code;
; SEMANTICS from the public MSX-BASIC ref. No disassembly.
;
; The dest descriptor address is stashed in MIDS_DEST (aliases NUMBUF, dead here) so
; the token cursor stays in HL through the whole arg parse. Entered with HL ON the
; $FF (PEEK_PREFIX). Clobbers A, BC, DE, HL.
;
; Arrays slice-4a REVISION: A$/B$ are now [len:1][ptr:2] descriptors, not inline
; [len][bytes]. The write target is A$'s CURRENT body (dereferenced from MIDS_DEST,
; +n-1 for the 1-based position) — MID$ overwrites bytes IN PLACE inside A$'s own
; already-owned heap body (its length never changes, so no realloc is ever needed).
ex_mid_stmt:
                inc     hl                  ; -> the function selector
                ld      a,(hl)
                cp      MIDD_TOKEN          ; must be MID$ ($83); any other $FF here is
                jp      nz,stmt_error       ; not a statement
                inc     hl                  ; HL past $FF $83
                ld      a,(hl)
                cp      '('
                jp      nz,stmt_error
                inc     hl                  ; HL -> target var name
                call    var_str_type        ; A=1 iff `$`-suffixed (HL unmoved)
                or      a
                jp      z,stmt_error         ; not a string var -> error
                call    var_name_key        ; BC = key, HL past name + `$`
                push    hl                  ; [cursor] guard across str_get_key
                call    str_get_key         ; HL -> dest descriptor (STRTAB, or STR_EMPTY)
                ld      (MIDS_DEST),hl      ; stash dest addr; cursor kept on the stack
                pop     hl                  ; HL = cursor
                ld      a,(hl)
                cp      ','
                jp      nz,stmt_error
                inc     hl
                call    eval                ; DE = n (1-based); HL advanced
                push    de                  ; [n]
                ld      a,(hl)
                cp      ','
                jr      z,ems_have_m
                ld      de,$00FF            ; m omitted -> a cap larger than any avail (<=255)
                jr      ems_close
ems_have_m:
                inc     hl
                call    eval                ; DE = m
ems_close:
                bit     7,d                 ; m<0 (bit15 set) -> range error
                jp      nz,ems_err_pop1     ; stack still [n]
                push    de                  ; [n][m]
                ld      a,(hl)
                cp      ')'
                jp      nz,ems_err_pop2
                inc     hl
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' crunches to $EF
                jp      nz,ems_err_pop2
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> RHS B$; HL = post-B$ cursor
                jp      nc,ems_err_pop2     ; not a string operand
                ; --- compute + copy. HL = the continue cursor (keep it). ---
                ; n<1/n>255 and the La>=n check, the avail/cap derivation, the
                ; final k=min(cap,Lb), and the actual byte-overwrite ALL moved
                ; to the sub-ROM tenant (sub/strheap.asm sh_mid_store, op=9,
                ; SH_ERR=3 signals the range error) — shape-C follow-up, this
                ; low region ran out of room for the arithmetic too.
                pop     de                  ; DE = m           stack: [n]
                pop     bc                  ; BC = n           stack: []
                push    hl                  ; [cursor] guard across the call
                ld      (SH_NUM),de         ; m
                ld      (SH_START),bc       ; n (full 16-bit; sub-side range-
                                            ; checks 1..255 itself)
                ld      hl,(STRPTR)
                ld      (SH_SRC),hl         ; B$ descriptor address
                ld      hl,(MIDS_DEST)
                ld      (SH_DEST),hl        ; A$ descriptor address
                ld      a,9
                ld      (SH_OP),a           ; op = 9 (MID_STORE)
                call    call_strheap
                ld      a,(SH_ERR)
                cp      3
                jr      z,ems_range         ; range error (n<1/n>255/n>La)
                pop     hl                  ; HL = continue cursor
                jp      exec_stmt
ems_range:
                pop     hl                  ; discard the guarded cursor -> stack balanced
                jp      stmt_error
ems_err_pop2:
                pop     de                  ; discard m
ems_err_pop1:
                pop     de                  ; discard n
                jp      stmt_error

; ===========================================================================
; string-functions S2 (repack build only): HEX$/OCT$/SPACE$ (Group A, $FF-
; prefixed) + STRING$ ($E3, Group B) + INSTR ($E5, Group C) — the five verbs of
; docs/spec-basic-string-functions.md. Group A mirrors CHR$/STR$ above (reached
; via str_func_ff); Group B/C are single-byte reserved-word tokens dispatched
; from str_eval (basic/strvar.asm) and ev_f (basic/expr.asm) respectively.
;
; Clean-room: original code. Verb SEMANTICS (unsigned-16 HEX$/OCT$ text, STRING$
; numeric-code-vs-string-first-byte dual form, INSTR 1-based search) are from the
; public MSX-BASIC language reference, oracle-locked black-box on the Philips
; VG-8020 (S2 gate). The STRMAX clamp / negative-length error (D-3) are zerobas's
; own design, consistent with the rest of the engine. No disassembly.
; ===========================================================================

; str_fn_hex: HEX$(n) -> uppercase hex text of n viewed as an UNSIGNED 16-bit
; value, no leading zeros, always >=1 digit (D-2: HEX$(0)="0", HEX$(-1)="FFFF").
; The nibble/leading-zero-suppression build (was inline here) moved to the
; sub-ROM tenant (sub/strheap.asm sh_hex_build, op=6) — shape-C follow-up,
; this low region ran out of room for it; only the argument PARSE (needs
; `eval`) stays main-side. Thin glue mirrors str_heap_alloc.
str_fn_hex:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = n (unsigned-16 view, D-2); HL advanced
    IF ROM_BASE < $4000
                push    hl                  ; guard cursor across the checked conversion
                call    fac_to_int_addr     ; spec §10.3: HEX$'s int argument is the
                pop     hl                  ; ADDRESS domain, checked (FPERR on overflow) --
    ENDIF                                   ; overrides eval's silent DE when n was a float
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl                  ; HL past ')'
                push    hl                  ; guard cursor
                ld      (SH_NUM),de
                ld      a,6
                ld      (SH_OP),a           ; op = 6 (HEX_BUILD)
                call    call_strheap
                call    shx_finish
                pop     hl                  ; restore cursor
                jp      str_eval_ok

; str_fn_oct: OCT$(n) -> octal text of n (unsigned 16-bit view), no leading
; zeros, always >=1 digit. Same shape-C move (sub/strheap.asm sh_oct_build,
; op=7); only the argument PARSE stays main-side.
str_fn_oct:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = n (unsigned-16 view)
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl                  ; HL past ')'
                push    hl                  ; guard cursor
                ld      (SH_NUM),de
                ld      a,7
                ld      (SH_OP),a           ; op = 7 (OCT_BUILD)
                call    call_strheap
                call    shx_finish
                pop     hl                  ; restore cursor
                jp      str_eval_ok

; shx_finish: shared HEX_BUILD/OCT_BUILD result tail. Reads SH_ERR/SH_PTR
; (set by either op), maps SH_ERR=2 (temp-descriptor stack full) to FPERR=9
; and STR_EMPTY, else publishes SH_PTR as the new STRPTR (SH_ERR=1, heap OOM,
; is honoured too — FPERR=6 — though a <=6-byte alloc essentially never hits
; it). Clobbers A, HL.
shx_finish:
                ld      a,(SH_ERR)
                or      a
                jr      z,shxf_ok
                cp      2
                jr      z,shxf_overflow
                ld      a,6
                ld      (FPERR),a           ; "Out of memory"
                ld      hl,(SH_PTR)
                ld      (STRPTR),hl
                ret
shxf_ok:
                ld      hl,(SH_PTR)
                ld      (STRPTR),hl
                ret
shxf_overflow:
                ld      a,9
                ld      (FPERR),a           ; "String formula too complex"
                ld      hl,STR_EMPTY
                ld      (STRPTR),hl
                ret

; str_fn_space: SPACE$(n) -> n space ($20) bytes, clamped to STRMAX (D-3); a
; negative n is a function error (own-design, mirrors ASC ""). The clamp reuses
; str_min_bc (A=STRMAX ceiling, BC=n), exactly like LEFT$/RIGHT$/MID$'s count clamp.
; Length is known upfront -> allocate once, fill directly.
str_fn_space:
                inc     hl                  ; past the selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = n; HL advanced
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl                  ; HL past ')'
                bit     7,d
                jp      nz,str_eval_no      ; negative n -> function error (D-3)
                push    hl                  ; guard cursor
                ld      b,d
                ld      c,e                 ; BC = n (str_min_bc's "count")
                ld      a,STRMAX            ; A = ceiling
                call    str_min_bc          ; A = min(STRMAX, n) = clamped fill count
                ld      (SH_LEN),a
                ld      a,' '
                ld      (SH_FILLBYTE),a
                ld      a,8
                ld      (SH_OP),a           ; op = 8 (FILL) -- shape-C follow-up:
                                            ; the fill loop moved to the sub-ROM
                                            ; tenant (sub/strheap.asm sh_fill),
                                            ; this low region ran out of room
                call    call_strheap
                call    shx_finish          ; shared SH_ERR/SH_PTR -> STRPTR tail
                pop     hl                  ; restore cursor
                jp      str_eval_ok

; str_fn_inkey: INKEY$ -> a 0- or 1-character string. Samples the keyboard ONCE,
; strictly non-blocking (D-2): CHSNS ($009C) reports Z = buffer empty / NZ = a key
; waits; on a key, CHGET ($009F) consumes it (non-blocking here because CHSNS just
; saw it). No arguments/parens to parse -- HL just steps past the INKEY_TOKEN.
; Control keys pass through as their raw code (D-5, own-design). Entered from
; str_eval_one (basic/strvar.asm) with HL ON the INKEY_TOKEN ($EC).
str_fn_inkey:
                inc     hl                  ; past the INKEY_TOKEN; no args to parse
                push    hl                  ; guard cursor                            [CURSOR]
                call    CHSNS               ; Z = keyboard buffer empty
                jr      z,sfi_empty
                call    CHGET               ; A = the waiting key
                push    af                  ; guard key byte                            [CURSOR][KEY]
                ld      a,1
                call    str_temp_alloc      ; -> HL=temp desc, DE=body(1B, or 0 on fail)
                ld      (STRPTR),hl
                ld      a,d
                or      e
                jr      z,sfi_nowrite       ; failure -> DE=0
                pop     af                  ; A = key byte                              [CURSOR]
                ld      (de),a
                jr      sfi_done
sfi_nowrite:
                pop     af                  ; discard the guarded key byte (balance)     [CURSOR]
sfi_done:
                pop     hl                  ; restore cursor                                [ ]
                jp      str_eval_ok
sfi_empty:
                xor     a
                call    str_temp_alloc      ; A=0 -> HL=temp desc(len0,ptr0), DE=0
                ld      (STRPTR),hl
                pop     hl                  ; restore cursor                                [ ]
                jp      str_eval_ok

; str_fn_string: STRING$(n,c) / STRING$(n,x$) -> n copies of a single fill
; byte, clamped to STRMAX (D-3). The fill byte is resolved by PROBING the 2nd
; argument's type (D-4, the established str_eval-CF pattern): a string x$
; contributes its first byte (empty x$ is a function error -- own-design,
; mirrors ASC ""); otherwise it is re-parsed numerically via `eval` and the low
; byte is the character code. Entered from str_eval_one (basic/strvar.asm) with
; HL ON the STRING_TOKEN byte itself ($E3) -- a single-byte reserved-word
; token (Group B), unlike the $FF-prefixed Group A verbs above. Length known
; upfront -> allocate once, fill directly.
str_fn_string:
                inc     hl                  ; past the STRING_TOKEN byte ($E3)
                ld      a,(hl)
                cp      '('
                jp      nz,str_arg_empty    ; BUG C class (Fable 2026-07-17): STRING$ is a
                                            ; SINGLE-byte token ($E3) -> its malformed re-
                                            ; drive never reaches ev_ff_strnum's deferred
                                            ; error, so a bare str_eval_no INFINITE-LOOPED
                                            ; (screen fills with " 0"). Defer FPERR=4 here.
                inc     hl
                call    eval                ; DE = n; HL advanced (IX preserved)
                bit     7,d
                jp      nz,str_arg_empty    ; negative n -> deferred syntax error (not a hang)
                ld      b,d
                ld      c,e                 ; BC = n
                ld      a,STRMAX
                call    str_min_bc          ; A = clamped fill count
                push    af                  ; guard the count                  [count]
                ld      a,(hl)
                cp      ','
                jr      nz,sfg_reject1      ; unbalance-safe: pop [count] first
                inc     hl
                ; --- resolve the fill byte: probe for a string 2nd arg (D-4) ---
                call    str_eval            ; CF set -> string 2nd arg; STRPTR->desc
                jr      c,sfg_str2
                ; numeric 2nd arg: re-parse via eval, take the low byte as the code
                call    eval                ; DE = char code; HL advanced past it
                ld      a,e                 ; A = fill byte
                jr      sfg_close
sfg_str2:
                push    hl                  ; guard the str_eval-advanced cursor across
                                            ; the descriptor dereference (which uses HL)
                ld      hl,(STRPTR)
                ld      a,(hl)              ; length of the string operand
                or      a
                jr      z,sfg_str2_empty    ; empty x$ -> error (mirrors ASC "")
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = ptr (body address)
                ld      a,(de)              ; A = fill byte (first byte of x$)
                pop     hl                  ; HL = cursor (restored)
                jr      sfg_close
sfg_str2_empty:
                pop     hl                  ; balance (cursor discarded -- error exit)
                jr      sfg_reject1
sfg_close:
                push    af                  ; guard fill byte                  [count][fill]
                ld      a,(hl)
                cp      ')'
                jr      nz,sfg_reject2      ; unbalance-safe: pop [count][fill] first
                inc     hl                  ; HL = cursor, past ')'
                push    hl
                pop     ix                  ; IX = cursor (parked)
                pop     af                  ; A = fill byte                    [count]
                ld      (SH_FILLBYTE),a
                pop     af                  ; A = clamped count                [ ]
                ld      (SH_LEN),a
                ld      a,8
                ld      (SH_OP),a           ; op = 8 (FILL) -- shape-C follow-up
                                            ; (same move as SPACE$ above)
                push    ix                  ; guard the parked cursor across the call
                call    call_strheap
                call    shx_finish          ; shared SH_ERR/SH_PTR -> STRPTR tail
                pop     hl                  ; HL = cursor (restore)
                jp      str_eval_ok
sfg_reject1:
                pop     af                  ; discard [count]
                jp      str_arg_empty       ; BUG C class: defer FPERR=4 (missing ',' / empty
                                            ; x$) -- STRING$ single-byte token would else hang
sfg_reject2:
                pop     af                  ; discard [fill]
                pop     af                  ; discard [count]
                jp      str_arg_empty       ; BUG C class: defer FPERR=4 (missing ')')

; ev_f_instr: INSTR([p,]a$,b$) -> 1-based position of b$ within a$, searching
; from position p (default 1); 0 if not found. Entered from ev_f (basic/expr.asm)
; with IX on the INSTR_TOKEN byte ($E5, single-byte reserved word -- Group C).
; Bridges IX<->HL exactly like ev_str_arg/ev_ff_cvi.
;
; The optional leading numeric p is distinguished from the two-argument form by
; PROBING the first argument's type via str_eval (D-5): CF set -> it IS a$ (the
; two-arg form; p defaults to 1); CF clear -> it's the numeric p (reparse via
; `eval`, then read ',' then str_eval for a$).
;
; Both a$ and b$ are snapshotted into their OWN owned temp (str_snapshot_to_temp)
; immediately after being parsed, so evaluating the second string can't clobber
; the first via STRSCR or the token stream -- the same snapshot-then-operate
; discipline the substring verbs and ev_rel_str's LHS snapshot use. p<1 is a
; function error (ev_f_err); the search itself (empty b$ / p past LEN(a$)) is
; instr_search's contract below.
;
; IX/IY are repurposed as the two temp-descriptor pointers (aT/bT) for
; instr_search once parsing is complete -- the real token cursor is safe in HL
; by then, and is bridged back into IX only right before the return, so ev_f's
; "IX = cursor advanced past the call" convention still holds.
ev_f_instr:
                inc     ix                  ; skip the INSTR selector
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_empty       ; BUG C class: INSTR without '(' -> deferred
                                            ; syntax error (was silent ev_f_err)
                inc     ix
                call    ev_sp
                push    ix
                pop     hl                  ; HL = cursor (bridge for the D-5 probe)
                call    str_eval            ; CF set -> a$ (2-arg form); STRPTR->desc
                jr      c,efi_have_a
                ; --- not a string: the leading numeric p (3-arg form) ---
                call    eval                ; DE = p; HL advanced past it (HL-based entry)
                push    de                  ; guard p                             [p]
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,efi_reject_p
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> a$; HL advanced; CF=ok
                jr      nc,efi_reject_p
                jr      efi_dup_a
efi_reject_p:
                pop     de                  ; discard [p]
                jp      ev_f_empty          ; BUG C class: 3-arg form missing ',' / a$
                                            ; not a string -> deferred syntax error
efi_have_a:
                ld      de,1                ; default p = 1 (two-arg form)
                push    de                  ; guard p                             [p]
efi_dup_a:
                push    hl                  ; guard cursor (past a$)              [p][cursor]
                call    str_snapshot_to_temp ; HL = aT (a$ snapshot); STRPTR=aT
                ex      (sp),hl             ; HL=cursor(restored); top:=aT        [p][aT]
                ld      a,(hl)
                cp      ','
                jp      nz,efi_reject_pa    ; malformed -> discard [p][aT]
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> b$; HL advanced; CF=ok
                jp      nc,efi_reject_pa
                push    hl                  ; guard cursor (past b$)              [p][aT][cursor]
                call    str_snapshot_to_temp ; HL = bT (b$ snapshot); STRPTR=bT
                ex      (sp),hl             ; HL=cursor(restored); top:=bT        [p][aT][bT]
                ld      a,(hl)
                cp      ')'
                jp      nz,efi_reject_pab
                inc     hl                  ; HL = cursor, past ')'
                ; --- everything parsed: search ---
                pop     iy                  ; IY = bT                             [p][aT]
                pop     ix                  ; IX = aT                             [p]
                pop     bc                  ; BC = p                              [ ]
                ; HL still = the real final cursor (untouched by the pops above)
                bit     7,b
                jr      z,efi_p_nonneg
                push    hl
                pop     ix                  ; restore IX = real cursor before erroring
                jp      ev_f_err            ; p negative -> error (D-5/§2 p<1)
efi_p_nonneg:
                ld      a,b
                or      c
                jr      nz,efi_p_ok
                push    hl
                pop     ix                  ; restore IX = real cursor before erroring
                jp      ev_f_err            ; p == 0 -> error (p<1)
efi_p_ok:
                ; Thin main-ROM glue for the string-heap tenant's
                ; INSTR_SEARCH op (mirrors str_heap_alloc) — the search body
                ; (now dereferencing aT/bT's [len:1][ptr:2] to find their
                ; CURRENT bodies, was inline-bodied) moved to the sub-ROM
                ; (sub/strheap.asm sh_instr_search) once this low region ran
                ; out of room for it.
                push    hl                  ; guard the real cursor               [cursor]
                push    ix
                pop     hl
                ld      (SH_SRC),hl         ; a$ temp descriptor address
                push    iy
                pop     hl
                ld      (SH_DEST),hl        ; b$ temp descriptor address
                ld      (SH_P),bc           ; p
                ld      a,11
                ld      (SH_OP),a           ; op = 11 (INSTR_SEARCH)
                call    call_strheap
                ld      de,(SH_PTR)         ; DE = result (1-based match / 0)
                pop     ix                  ; IX = cursor (bridge back to ev_f's convention)
                jp      flt_int_result      ; INSTR returns an int even when a float rode
                                            ; in via p or a nested STR$ arg (float.asm F1;
                                            ; clobbers A only, then ret to the caller)
efi_reject_pa:
                pop     hl                  ; discard [aT]                        [p]
                pop     hl                  ; discard [p]                         [ ]
                jp      ev_f_empty          ; BUG C class: malformed a$/b$ or missing ','
                                            ; (INSTR("AB")) -> deferred syntax error, not the
                                            ; silent ev_f_err (stale STRPTR + dropped tail)
efi_reject_pab:
                pop     hl                  ; discard [bT]                        [p][aT]
                pop     hl                  ; discard [aT]                        [p]
                pop     hl                  ; discard [p]                         [ ]
                jp      ev_f_empty          ; BUG C class: missing ')' -> deferred syntax error

; --- exp_maybe_strfn: PRINT hook for the string-VALUED $FF functions --------
; Reached from exp_loop (basic/print.asm) when a PRINT item begins with a $FF
; function token (repack build only). Try the string path first — CHR$/STR$/LEFT$/
; RIGHT$/MID$/MKI$ succeed and print; a numeric $FF function (PEEK/…) fails cleanly
; (str_func_ff restores HL to the $FF), so we fall back to exp_num.
;
; S2 (spec-basic-print-unparen-compare.md §3): after a successful string-function
; parse, remember the operand START (push hl BEFORE str_eval) and peek the token
; that follows the value for a relational operator. If one follows, this item is
; really the LHS of an unparenthesized comparison (`PRINT LEFT$(A$,1)="H"`); restore
; the operand start and re-drive it through eval/ev_rel instead of printing it.
; UNCHANGED from pre-4a — format-agnostic (only ever calls str_eval/print_strval).
exp_maybe_strfn:
                push    hl                  ; operand START (peek may reparse via eval)
                call    str_eval            ; STRPTR -> value; HL advanced; CF=ok
                jr      nc,ems_fallback     ; not a string function -> numeric factor
                call    skip_spaces
                ld      a,(hl)
                call    relop_peek          ; ZF=1 iff (HL) is a relop token
                jr      nz,ems_print        ; no relop -> plain PRINT (below)
                pop     hl                  ; relop follows -> restore the operand START
                jp      exp_num             ; re-drive via eval -> ev_rel (-1/0, or D-2 abort)
ems_print:
                pop     de                  ; drop the saved operand-start (balances the
                                             ;  push above; str_eval already clobbers DE)
    IF ROM_BASE < $4000
                ld      a,(FPERR)           ; D-F2-1: e.g. print hex$(65536.) — the
                or      a                   ; overflow happens inside str_eval's HEX$
                jp      nz,fp_runtime_error ; argument conversion (fac_to_int_addr)
    ENDIF
                push    hl                  ; print_strval clobbers HL (token cursor)
                call    print_strval
                pop     hl
                jp      exp_loop
ems_fallback:
                pop     hl                  ; balance the operand-start push (str_func_ff
                                             ;  restores HL to the $FF on failure, so this
                                             ;  is the same cursor exp_num sees un-gated)
                jp      exp_num

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

; --- relop_peek: is A a relational-operator token? --------------------------
; UNCHANGED from pre-4a — a straight range test over the established relop
; token equates (basic/sysvars.inc); no descriptor-format dependency.
; in: A = the current token byte (caller peeks via `ld a,(hl)`; not consumed).
; out: ZF=1 iff A is one of the three contiguous relop tokens GT_TOKEN ($EE) /
;      EQ_TOKEN ($EF) / LT_TOKEN ($F0). ZF=0 otherwise. Does not touch
;      HL/DE/BC/IX -- only A and flags.
relop_peek:
                sub     GT_TOKEN            ; A -= $EE (0/1/2 for the three relops)
                cp      3                   ; CF=1 iff A(orig)-$EE < 3, i.e. in range
                jr      c,rp_yes
                or      1                   ; not in range -> force A nonzero -> ZF=0
                ret
rp_yes:
                cp      a                   ; in range -> force ZF=1
                ret

; --- str_cmp_bits: UNSIGNED byte-by-byte compare of two descriptors --------
; in: HL = lhs descriptor, DE = rhs descriptor.
; out: A = 1 (lhs<rhs) / 2 (equal) / 4 (lhs>rhs) -- the same encoding cmp16_bits
;      (expr.asm) produces for the numeric path, so the caller's `and c` (requested
;      vs actual) is unchanged. Compares corresponding bytes by raw unsigned value;
;      at the first differing byte the smaller byte's string is less (spec §2.1);
;      if all shared bytes match, the SHORTER string is less (§2.2); same length +
;      all bytes equal -> equal (§2.3). Case-sensitive: no folding (§2.4).
; Preserves BC (the caller keeps its requested-bits register in C across the call).
; Clobbers DE, HL, IX, flags.
;
; Thin main-ROM glue for the string-heap tenant's CMP op (mirrors
; str_heap_alloc) — the byte-compare mechanics (now dereferencing each
; descriptor's [len:1][ptr:2] to find the CURRENT body, was inline
; [len][bytes]) moved to the sub-ROM (sub/strheap.asm sh_cmp_bits) once this
; low region ran out of room for it.
str_cmp_bits:
                push    bc                  ; guard the caller's C (requested bits)
                ld      (SH_SRC),hl
                ld      (SH_DEST),de
                ld      a,10
                ld      (SH_OP),a           ; op = 10 (CMP)
                call    call_strheap
                ld      a,(SH_LEN)          ; A = 1/2/4 relation bits (the
                                            ; tenant reuses SH_LEN as CMP's
                                            ; 1-byte result field)
                pop     bc                  ; restore the caller's bits (C)
                ret

; --- type_mismatch_set: D-2's comparator-level signal ------------------------
; UNCHANGED from pre-4a. A string on one side of a relational and a non-string
; on the other (or a bare string LHS with no relop at all) -- sets ERRMARK
; (the generic expression-error landmark, ev_f_err's convention) plus the
; distinct TMISMATCH marker, and yields 0 (false). This does NOT abort the
; line itself: ev_rel has no mid-expression unwind, so the real abort happens
; at the STATEMENT boundary, once eval() returns, via the repack-gated
; post-eval check in ex_if / the numeric-assignment / PRINT-item drivers
; jumping to type_mismatch_error (interp.asm).
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
; Snapshots the LHS into an OWNED temp (str_snapshot_to_temp — was str_dup_temp
; pre-4a, same calling convention) so evaluating the RHS can't clobber it via
; STRSCR or a later alloc/GC (e.g. two literal operands would otherwise BOTH
; land on the shared RVDESC/STRSCR scratch and the second overwrites the
; first before the compare — the same discipline the substring verbs use).
; Reads the relop token(s) with the EXISTING relop_bit + compound-form merge
; (<=/>=/<> fall out unchanged), evaluates the RHS via str_eval, then compares
; with str_cmp_bits and joins the numeric path's convention (`and c` -> -1/0).
;
; A bare string LHS with no following relop, or a non-string RHS (`A$ < 5`), is
; D-2's type mismatch -> type_mismatch_set (yields 0, ERRMARK+TMISMATCH set).
; out: DE = -1/0; ret. Clobbers A, BC, DE, HL (like the numeric ev_rel body).
; Slice-4a: str_snapshot_to_temp / str_eval / str_cmp_bits are now sub-ROM
; op stubs that CALSLT -> they CLOBBER IX (and every register). The old
; str_dup_temp / cmp16-style callees were LOCAL and preserved IX, so this
; routine used to keep the token cursor in IX across them. Now the cursor is
; carried on the STACK and reloaded into IX only for the relop reads / the
; final ev_rel "IX = advanced cursor" return contract.
ev_rel_str:
                ; HL = cursor past the LHS operand, STRPTR = LHS descriptor.
                push    hl                  ; [cursor] (snapshot's CALSLT clobbers HL/IX)
                call    str_snapshot_to_temp ; STRPTR -> LHS snapshot temp; HL = LHS temp
                ex      (sp),hl             ; [LHStemp]; HL = cursor
                push    hl
                pop     ix                  ; IX = cursor (for the relop reads)
                call    ev_sp
                ld      a,(ix+0)
                call    relop_bit
                jp      nc,ers_mismatch     ; bare string LHS, no relop -> D-2 ([LHStemp])
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
                push    ix                  ; [LHStemp][cursor]
                push    bc                  ; [LHStemp][cursor][bits]
                push    ix
                pop     hl                  ; HL = cursor
                call    str_eval            ; STRPTR -> RHS desc; HL advanced; clobbers IX
                pop     bc                  ; C = bits            [LHStemp][cursor]
                jr      nc,ers_rhs_mismatch ; RHS not a string -> D-2 (`A$ < 5`)
                ; HL = new cursor (past RHS). STRPTR = RHS descriptor.
                ex      (sp),hl             ; [LHStemp][newcursor]; HL = old cursor (dead)
                ld      hl,(STRPTR)         ; HL = RHS descriptor addr
                ex      de,hl               ; DE = RHS descriptor addr
                pop     ix                  ; IX = newcursor       [LHStemp]
                pop     hl                  ; HL = LHS temp addr   [ ]
                push    ix                  ; [newcursor] (str_cmp_bits CALSLT clobbers IX)
                call    str_cmp_bits        ; A = actual bit (1/2/4); preserves BC (C=reqbits)
                pop     ix                  ; IX = newcursor (ev_rel's "advanced cursor")
                and     c                   ; intersect requested with actual
                jr      z,ers_false
                ld      de,$FFFF            ; true = -1
                jp      flt_int_result      ; the -1/0 result is an int even when a float
                                            ; rode in via a nested STR$ operand (float.asm
                                            ; F1; clobbers A only, preserves IX)
ers_false:
                ld      de,0                ; false = 0
                jp      flt_int_result      ; (same)
ers_rhs_mismatch:
                pop     ix                  ; BUG C lesser: RESTORE the cursor (the RHS
                                            ; str_eval CALSLT trashed IX) instead of
                                            ; discarding it -> type_mismatch_set returns
                                            ; with a coherent cursor, not garbage. [LHStemp]
ers_mismatch:
                pop     hl                  ; discard [LHStemp] (bare-LHS entry: IX already
                                            ; = cursor from the relop reads above)
                jp      type_mismatch_set
