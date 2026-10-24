; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; aliases-early.inc -- label ALIASES that must be defined before any use.
; ===========================================================================
; Clean-room: own code. Fifteen `equ` lines moved verbatim from the files each
; comment names; nothing here is derived from a disassembly or byte-copy of any
; reference ROM. Basis: basic/PROVENANCE.md.
; ===========================================================================
; 🔴 D-PASMO053 (2026-10-11). pasmo 0.5.3 -- the version Debian / Ubuntu ship --
; assembles in two passes, and an alias `X equ lbl` is evaluated in pass 1 before
; `lbl` exists: it is 0 then. In pass 2 every use of X ABOVE its equ line still
; reads that 0. 0.5.5 resolves it; 0.5.3 built a main ROM with 13 jump and
; pointer operands of $0000, silently. So these aliases live HERE, included
; right after sysvars.inc, above every use. (Plain forward references to LABELS
; are fine on both versions; only an alias of a label defined later bites.)
; A new alias used above its own definition needs the same treatment; the CI
; build with the distribution's pasmo 0.5.3, checked against the committed
; images, is what catches one that does not get it.
; Each comment says where the alias used to live, beside its notes. The first
; cut moved 15 and missed six more on gb_illegal's address (one operand stayed
; $0000) -- found by the same image diff.
; ===========================================================================
err_illegal_fn  equ     err_illegal_fn_arr
                                ; (was basic/interp.asm)
err_subrom_absent equ   err_illegal_fn      ; share interp.asm's identical "illegal
                                ; (was basic/subromcall.asm)
flt_int_result  equ     evsgn_settype
                                ; (was basic/float.asm)
inpc_synpop     equ     ex_let_err
                                ; (was basic/input.asm)
raf_zero_ok     equ     cpow_x0_pos
                                ; (was basic/float-arith.asm)
vlf_unset_int   equ     vptr_none
                                ; (was basic/vars.asm)
; (rn_in -- `equ in_msg`, D-ISLDATA2 -- left with RENUM's report loop for
; sub2/pgmedit.asm, D-P0CB 2026-10-24: it imports in_msg itself, as p0_rn_in)
; (eoi_err5 -- ON INTERVAL=0's ERR 5 -- gone with the trap statements to
; sub2/trapstmt.asm, D-P0CB slice B 2026-10-21: tt_illegal raises gb_illegal there)
fchk_ifc        equ     gb_illegal  ; ERR 5 (err_msgtab[5])
                                ; (was basic/files.asm)
ex_donothing    equ     gb_illegal
                                ; (was basic/interp.asm)
ev_f_attr       equ     gb_illegal
                                ; (was basic/interp.asm)
elg_syntax      equ     pl_syntax   ; ERR 2 (bad LINE form)
                                ; (was basic/graphics.asm)
ep_syntax       equ     pl_syntax   ; ERR 2 (a 4th PAINT argument)
                                ; (was basic/graphics.asm)
gfx_syntax      equ     pl_syntax   ; ERR 2 (malformed SPRITE statement)
                                ; (was basic/graphics.asm)
exp_pos_syn     equ     pl_syntax           ; ERR 2 syntax error
                                ; (was basic/print.asm)
gfx_err5        equ     gb_illegal  ; ERR 5 (PSET/PRESET in SCREEN 0/1)
                                ; (was basic/graphics.asm)
gfx_absent      equ     gfx_err5
                                ; (was basic/graphics.asm)
pl_absent       equ     gb_illegal  ; defensive: merged ROM always ships the tenant
                                ; (was basic/play.asm)
pu_ifc          equ     gb_illegal
                                ; (was basic/printusing.asm)
snd_illegal     equ     gb_illegal  ; ERR 5 (register out of 0..13)
                                ; (was basic/sound.asm)
; (strig_illegal -- STRIG(n) / KEY(n)'s ERR 5 -- gone the same way, D-P0CB slice B)
