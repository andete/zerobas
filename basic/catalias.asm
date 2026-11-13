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
