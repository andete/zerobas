; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; =============================================================================
; mathwrap.asm -- the math tenants' scratch, CALLEE-SAVED (D-WSZERO S14e)
; =============================================================================
; The nine math tenants (SQR ATN EXP LOG ^ SIN COS TAN RND) keep 39 B of scratch
; -- SQRT_X / SQRT_Y / SQRT_K / SQRT_ITER / SQRT_POW10 and every alias of them
; (MATH_*, HORNER_G, RND_LE, RND_STATE) -- in MW_HOST, the head of the DEF FN
; shadow slots (basic/sysvars.inc). Those slots are live while an FN call runs
; (its formals) and while PRINT USING renders (PU_NUM / PU_DIG, D-WSZERO S12), and
; a math function can be evaluated inside either. So every entry from the sub
; page-1 table goes through math_wrap: the host's 39 B are copied onto the Z80
; stack, the body runs, and they are copied back -- whatever was live there is
; exactly as it was. The scratch used to sit in zerobas's own workspace window
; ($F16E-$F194), RAM a diskless VG-8020 leaves to programs.
;
; WHY THE RESTORE ALWAYS RUNS: a page-1 tenant cannot raise (main page 1 is
; switched out); every math error is DEFERRED through FPERR (penderr_set), so each
; body returns -- none of sub/fp_*.asm raises or jumps to an error tail.
; WHY THE SHADOW SET IS SAFE: the caller's DE / HL (^'s n and j, D-WSZERO S14e)
; ride in it across the save copy, and C-BIOS's KEYINT pushes the shadow set
; (exx / ex af,af' / push x4) before anything else, so an IRQ cannot touch it.
; ⚠️ NOT INTERRUPT-LIVE, AND THAT IS A KNOWN COST (D-GCDI2): a long `^` holds DI
; for up to 165 ms and RND's loop leaves 41 ms gaps (frames, keys, TIME lost --
; the program ladder's L1_loan / L1_dice). An `ei` here was tried on 2026-10-28
; and REVERTED: with page 1 = this ROM, htimi_guard skips PLAY on every frame
; that lands inside the tenant, and a tight SIN loop then STARVED PLAY completely
; (play-trace-acceptance di_safety, notes-advanced=[]), where under DI the frame
; is served late on the way out. The fix belongs in htimi_guard, not here.
; COST (TIER 5, unmeasured here): two 39-byte LDIRs, ~1.7k T per call.
; Clean-room: own design.
; -----------------------------------------------------------------------------
mw_sqrt:        ld      ix,fp_sqrt          ; IX is free: CALSLT entered with IX =
                jr      math_wrap           ; this table entry, and every resident
mw_atan:        ld      ix,fp_atan          ; caller saves its own IX across
                jr      math_wrap           ; subrom_call
mw_exp:         ld      ix,fp_exp
                jr      math_wrap
mw_log:         ld      ix,fp_log
                jr      math_wrap
mw_pow:         ld      ix,fp_pow
                jr      math_wrap
mw_sin:         ld      ix,fp_sin
                jr      math_wrap
mw_cos:         ld      ix,fp_cos
                jr      math_wrap
mw_tan:         ld      ix,fp_tan
                jr      math_wrap
mw_rnd:         ld      ix,fp_rnd
math_wrap:
                exx                         ; the caller's DE / HL (^'s n, j) wait
                ld      hl,-MW_N
                add     hl,sp
                ld      sp,hl               ; MW_N bytes reserved on the stack
                ex      de,hl               ; DE = the save area
                ld      hl,MW_HOST
                ld      bc,MW_N
                ldir                        ; host -> stack
                exx                         ; DE / HL as the caller passed them
                call    mw_jpix             ; the body: results in FAC / FACTYP / FPERR
                push    af
                ld      hl,2
                add     hl,sp               ; HL = the save area (past AF)
                ld      de,MW_HOST
                ld      bc,MW_N
                ldir                        ; stack -> host: put back what was live
                pop     af
                ld      hl,MW_N
                add     hl,sp
                ld      sp,hl               ; the reservation released
                ret
mw_jpix:        jp      (ix)
