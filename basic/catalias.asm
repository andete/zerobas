; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; catalias.asm -- D-CATALIAS (2026-11-13): `V$=V$+<computed>` reaches the VG-8020's
; string-space capacity. Main page 1, in front of the $6CF3 pin (basic/main.asm).
;
; The reference's peak for `V$=V$+X` is old V$ + the new result (2N+2: 100 at CLEAR 200,
; 94 with a 12-byte Q$, 80 with 40 -- scratchpad/strspace_run5.out, catalias_vg2.out);
; ours was ~3N+5, because str_concat_tail SNAPSHOTTED a variable left operand (a copy of
; V$'s body) before evaluating the right one. Design: scratchpad/catalias_design.md,
; route (c) -- an INDIRECT BODILESS SLOT, never a second root on V$'s body (the GC moves
; each body once and needs root pointers DISTINCT: a second root is double-move
; corruption, sub/strheap.asm's "phantom root").
;
; The slot is a 3-byte temp [len][word]: the word is the scalar's DESCRIPTOR ADDRESS
; (>= $8000, in [VARTAB, ARYTAB)), or an array element's OFFSET from ARYTAB (< $8000,
; bit 15 clear -- op 21's convention). Neither is a heap pointer, so the GC never roots
; it (sg_inrange: OLD_FRETOP <= ptr < CEIL); the real root is the variable itself, which
; the GC fixes up as usual. It is resolved at OP TIME (sct_resolve), after operand 2 --
; whose evaluation may move V$'s body (a GC) or the arrays (a new scalar inserts at
; ARYTAB; a scalar's own descriptor never moves, basic/vars.asm). The op is then op 22
; (sh_append's realloc arm, never the extend-in-place one: that would alias V$), reading
; the variable through blk+4 and writing the new body into the slot through blk+6
; (sub/strheap.asm she_out), which thereby becomes an owned temp: the expression's value.
;
; Under CLEARPOOL only (op 22 is a CLEARPOOL row; without it op 2 would extend V$'s own
; body in place). Clean-room: own design, no reference code read.

; ---------------------------------------------------------------------------------------
; (moved here from basic/interp.asm, D-TAPEBIOS 2026-11-13: raise_error's span before the
; $475A pin had no room for the Ctrl-STOP release wait set_errflg now does; both are
; reached by `call` only.)
; --- set_errflg: A = an ERR code -> call H.ERRO, then ERR := the code -------
; 🏗️ D-HERRO (2026-10-27). The VG-8020 calls the published error hook H.ERRO
; ($FFB1) once on EVERY error -- trapped or not, from ERROR or BASIC itself --
; BEFORE ERR is stored, with E = the code, and takes the code back from E
; (a hook doing `ld e,5` turns ERROR 7 into Illegal function call):
; scratchpad/herro_probe.py / herro2_probe.py. zerobas never called it. Every
; site that recorded an error with `ld (ERRFLG),a` calls this instead, the same
; 3 bytes. ⚠️ The editor rejects that print a FIXED message (line too large,
; line-buffer overflow, CONT at the prompt) keep it even if a hook rewrites E.
; Out: A = the (possibly rewritten) code. Clobbers DE.
set_errflg:
                ld      e,a
                call    H_ERRO              ; RET unless something hooked it
                ld      a,e
                ; 📼 D-TAPEBIOS (2026-11-13): a Device I/O error waits for Ctrl-STOP to be
                ; RELEASED. The tape BIOS returns at the press with the key down, as the
                ; VG-8020's does (probes/tape/bios_probe_tapdiff.py); zerobas's run loop
                ; polls the key's LEVEL, so an ON ERROR handler entered with it down
                ; would break at its first statement, where the VG-8020 runs it
                ; (D-CASWBRK, scratchpad/caswbrk_hold_tap.out). HERE, not in raise_error:
                ; the deferred raises (a sub-ROM tenant's 19 at the statement boundary)
                ; record through this routine without passing raise_error's entry.
                ; F is kept: this routine never touched it before.
                push    af
                cp      19
                call    z,brk_release
                pop     af
                ld      (ERRFLG),a
                ret
; brk_release -- D-TAPEBIOS: return once Ctrl-STOP is up, the whole hold consumed: BREAKX
; marks the press seen (D-BRKLATCH), and a key auto-repeat that latched INTFLG while the
; key was held (C-BIOS repeats from ~36 frames; the BIOS used to wait with interrupts
; off, so none ran) is dropped -- the VG-8020 runs a handler entered under a 0.9 s hold
; to its end (caswbrk `phold`). Changes AF.
brk_release:
                call    BREAKX
                jr      c,brk_release
                xor     a
                ld      (INTFLG),a
                ret
; ---------------------------------------------------------------------------------------
; fperr_to_err -- the dense FPERR -> ERR byte map, moved here from island 3 ($09E0, basic/
; islands.asm) by D-SCALXYF (2026-11-13): C-BIOS's graphics span grew into it. Verbatim;
; still read only by fp_runtime_error's absolute `ld hl,fperr_to_err` (basic/interp.asm).
fperr_to_err:
                db      6                   ; FPERR 1: overflow (err_overflow, program.asm's
                                            ; own string, dl_overflow -- REUSED byte-for-byte)
                db      11                  ; FPERR 2: division by zero (err_fp_divzero)
                db      5                   ; FPERR 3: illegal function call -- math pack
                                            ; slice 1b SQR(x<0)/LOG, and the deferred
                                            ; ASC domain check (ev_f_ifc). A REAL ENTRY
                                            ; since D-MSGEXACT: it was a `db 0` placeholder
                                            ; while FPERR=3 was intercepted upstream to get
                                            ; a LOWERCASE message. Same ERR 5, same string
                                            ; as FPERR=8 now -- knife K3 cuts this slot.
                db      2                   ; FPERR 4: syntax error (D-F2-3 empty
                                            ; parenthesised/argument expression; reuses
                                            ; stmt_error's own ERR-2 table entry)
                db      9                   ; FPERR 5: subscript out of range -- arrays
                                            ; slice-1 (§4.1 #3/#8): index out of range, or
                                            ; wrong dimension count
                db      7                   ; FPERR 6: out of memory (DIM/auto-dim OOM via
                                            ; ary_errmap). A REAL ENTRY since D-MSGEXACT --
                                            ; was a `db 0` placeholder while FPERR=6 was
                                            ; intercepted upstream to get the CAPITALISED
                                            ; message; that is now the only spelling.
                db      10                  ; FPERR 7: redimensioned array -- arrays
                                            ; slice-1 (§4.1 #4): a second DIM of a live array
                db      5                   ; FPERR 8: illegal function call -- arrays
                                            ; slice-1 (§4.1 #9): negative subscript; arrays'
                                            ; OWN reference-verbatim capitalised
                                            ; "Illegal function call" (basic/arrays.asm
                                            ; err_illegal_fn_arr; §9.5 pins the array error
                                            ; surface oracle-exact, unlike the lowercase
                                            ; shared FPERR=3 SQR/LOG keep) -- ERR-5's table
                                            ; entry still points at THAT string, not FPERR=3's
                db      16                  ; FPERR 9: string formula too complex -- arrays
                                            ; slice-4a (docs/spec-basic-arrays-slice4a-
                                            ; string-heap.md §6/§11): temp-descriptor stack
                                            ; overflow (basic/str-engine.asm err_too_complex,
                                            ; low region)
                db      13                  ; FPERR 10: type mismatch -- a string function
                                            ; given a NON-string arg (LEN(5)/ASC(5)/VAL(5));
                                            ; ev_f_tmm (expr.asm) defers this via FPERR=10.
                                            ; Same ERR-13 table entry type_mismatch_error uses.
    IF CLEARPOOL
                db      14                  ; FPERR 11 (= FPERR_STROOM, sysvars.inc):
                                            ; OUT OF STRING SPACE -- the string heap could
                                            ; not allocate, which with the D-CLP partition
                                            ; ON means the pool `CLEAR n` sized ran out.
                                            ; ⚠️ Deliberately NOT FPERR=6/ERR 7: an ARRAY
                                            ; that will not fit is out of MEMORY, and the
                                            ; probe's oos-vs-oom row pins the two apart.
                                            ; Unlike 3 and 6 this needs no special case in
                                            ; fp_runtime_error -- ERR 14 has exactly one
                                            ; message (err_out_of_str, str-engine.asm) and
                                            ; flows through the generic err_msgtab lookup.
    ENDIF
                db      24                  ; FPERR_MISSOP (sysvars.inc, D-MISSOP): MISSING
                                            ; OPERAND -- a factor was REQUIRED and the
                                            ; statement ended instead (end of line, ':', or
                                            ; a byte that cannot start one). Deferred by
                                            ; ev_f_err, expr.asm. ⚠️ THIS `db` MUST FOLLOW
                                            ; the CLEARPOOL block, not sit inside it: the
                                            ; table is DENSE and FPERR_MISSOP's value moves
                                            ; with the switch (12 with CLEARPOOL, 11
                                            ; without), which is why the equ lives beside
                                            ; FPERR_STROOM rather than being a literal.
                db      15                  ; FPERR_STRLONG (= FPERR_MISSOP+1, sysvars.inc,
                                            ; D-STRLONG): STRING TOO LONG -- a `+` fold whose
                                            ; combined length exceeds STRMAX. sh_append used
                                            ; to clamp it to 255 and return that; both
                                            ; references raise here instead. Same DENSE-table
                                            ; caveat as the entry above: this `db` must stay
                                            ; LAST, because FPERR_MISSOP moves with CLEARPOOL
                                            ; and this code is defined relative to it.

; --- sct_op: str_concat_tail's APPEND call. In: A = [op] (2, 22, or 23: the chain's
; first `+` after a variable left operand), DE = R. BC := R -- the result's slot, blk+6
; (sub/strheap.asm she_out) -- then op 23 resolves the variable (sct_resolve), and
; sh_go_g runs with HL = the operand. Out: as sh_go_g (A = ERR, Z iff 0).
sct_op:
                ld      b,d
                ld      c,e
    IF CLEARPOOL
                cp      23
                call    z,sct_resolve
    ENDIF
                ld      hl,(STRPTR)
                jp      sh_go_g

; --- se2_fin: sct_err2's tail. DE = R, C = [op]. An UNRESOLVED variable slot (op 23:
; no op ran) becomes "" -- never [len][a variable's address] as a value a consumer
; could slice; then STRPTR := R, CF set (success-shaped, no re-drive).
se2_fin:
    IF CLEARPOOL
                ld      a,c
                cp      23
                call    z,sct_zero
    ENDIF
                ld      (STRPTR),de
                scf
                ret

    IF CLEARPOOL
; --- sas_var: str_alias_or_snap's variable arm, reached by `jp` (no frame of its own).
; STRPTR -> operand 1's descriptor, not program text. A scalar ([VARTAB, ARYTAB)) or an
; array element ([ARYTAB, STREND)) -> push the slot, STRPTR / HL := it, and set
; str_concat_tail's [op] cell to 23: sct_go pushed [op][cursor] and called
; str_alias_or_snap, so with this routine's own push the cell is at SP+6. Anything else
; (a temp, a work cell) -> the snapshot, as before. Clobbers A, BC, DE.
sas_var:
                ld      de,(STRPTR)
                ld      hl,(STREND)
                scf
                sbc     hl,de               ; CF iff STRPTR >= STREND
                jp      c,str_snapshot_arg  ; above the arrays: a temp or a work cell
                ex      de,hl               ; HL = STRPTR
                ld      de,(VARTAB)
                or      a
                sbc     hl,de               ; CF iff STRPTR < VARTAB
                jp      c,str_snapshot_arg  ; below the variables
                add     hl,de               ; HL = STRPTR
                ld      de,(ARYTAB)
                or      a
                sbc     hl,de               ; HL = STRPTR - ARYTAB, CF iff a scalar
                jr      nc,sas_have         ; an element: the word is its offset (< $8000)
                add     hl,de               ; a scalar: the word is its descriptor's address
sas_have:
                ex      de,hl               ; DE = the word
                ld      hl,(TEMPPT)
                push    de                  ; [word]
                ld      de,TEMPBASE-3
                ex      de,hl               ; HL = TEMPBASE-3, DE = the slot
                or      a
                sbc     hl,de               ; CF iff the slot would pass TEMPBASE
                pop     bc                  ; BC = the word
                jp      c,str_snapshot_arg  ; full: the snapshot raises it
                ld      hl,(STRPTR)
                ld      a,(hl)              ; the variable's length (the slot's [len])
                ex      de,hl               ; HL = the slot
                ld      (hl),a
                inc     hl
                ld      (hl),c
                inc     hl
                ld      (hl),b
                inc     hl
                ld      (TEMPPT),hl
                dec     hl
                dec     hl
                dec     hl                  ; HL = the slot
                ld      (STRPTR),hl
                push    hl
                ld      hl,6
                add     hl,sp               ; [slot][ret][cursor][op]
                ld      (hl),23             ; str_concat_tail resolves it at op time
                pop     hl
                ret

; --- sct_resolve: the first `+` of a chain whose left operand is a variable ([op] 23).
; In: DE = the slot. Out: DE = the variable's descriptor NOW, A = SH_OP_APPEND2, the
; slot zeroed ("" until the op writes the result into it -- so an op that fails, or an
; error arm, leaves an ordinary empty temp, never a [len][var address] a consumer could
; read as a body). BC kept (the result slot, blk+6).
sct_resolve:
                ex      de,hl               ; HL = the slot
                xor     a
                ld      (hl),a
                inc     hl
                ld      e,(hl)
                ld      (hl),a
                inc     hl
                ld      d,(hl)
                ld      (hl),a
                bit     7,d
                jr      nz,scr_have         ; >= $8000: a scalar's descriptor address
                ld      hl,(ARYTAB)
                add     hl,de
                ex      de,hl               ; an element: ARYTAB + its offset
scr_have:
                ld      a,SH_OP_APPEND2
                ret

; --- sct_zero: an UNRESOLVED slot met an error arm (a malformed operand 2, before any
; op ran): make it the empty string. In: DE = the slot. Clobbers A, HL.
sct_zero:
                ld      h,d
                ld      l,e
                xor     a
                ld      (hl),a
                inc     hl
                ld      (hl),a
                inc     hl
                ld      (hl),a
                ret
    ENDIF
