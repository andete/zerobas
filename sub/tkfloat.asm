; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — tkfloat.asm  (float literal crunch; WAVE 1 tenant, now a co-located
; callee of the WAVE 2 whole-tokeniser eviction, docs/spec-basic-subrom.md)
; ===========================================================================
; The float LITERAL CRUNCH (tk_float, FAC-less: ASCII literal -> tokenised BCD
; value bytes), evicted from the repack main ROM's basic/float.asm into sub-ROM
; PAGE 0 as a pure leaf. Wave 1 reached it through its OWN page-0 entry with a
; per-literal CALSLT + an A-disposition return protocol; WAVE 2 evicted the whole
; tokeniser here too, so tk_float is now reached by an ordinary in-slot
; `jp tk_float` from tk_loop, and its exits are plain `jp tk_loop` / `jp tk_end`
; back into the co-located loop again (the disposition protocol + the float.asm
; dispatch stub were reverted, spec §5) — one CALSLT per LINE, not per literal.
;
; WHY THE CRUNCH IS SUB-SIDE (user call 2026-07-11): a page-0 sub-ROM tenant runs
; with the BIOS + low region switched out, so it must be pure computation. The
; PRINT formatter is pure-compute too but RUNTIME-HOT (every float PRINT), so it
; stays resident. The crunch runs only at TOKENISE time (line edit / program
; load) — cold — so it is the right thing to page out (as is the whole loop).
;
; PURE-LEAF DISCIPLINE (§3b). The crunch may touch ONLY page-2/3 RAM + co-located
; sub-ROM code: its two page-1 leaf callees `upcase` (basic/interp.asm) and
; `cmp16_bits` (basic/expr.asm) are duplicated below as byte-identical own-design
; clones; tk_loop / tk_end live in the co-located sub/tokenise.inc.
; The tkf_ref* bound tables live INSIDE this body (used by tkf_cmp32767); the
; resident float-arith needs them too, so basic/float.asm keeps its OWN copy —
; no cross-ROM reference either way.
;
; RAM cells (TKPOS/TKDIG/TKPC/TKLEAD/TKOVF/TKSRCSAVE/TKFLAGS/...) are the SAME
; addresses as the repack main ROM (shared sysvars.inc, included by sub.asm),
; so no marshalling translation.
;
; CLEAN-ROOM: the crunch algorithm is own-design (copied verbatim from our own
; basic/float.asm); classification/format rules are oracle-pinned + MSX2 TH; the
; token bytes are oracle-pinned. No disassembly.
; ===========================================================================

SGL_DIGITS      equ     6       ; single mantissa digit count (MSX2 TH number format)
DBL_DIGITS      equ     14      ; double mantissa digit count (MSX2 TH number format)

tk_float:
                push    de                  ; save the TOKBUF destination cursor
                xor     a
                ld      (TKPOS),a
                ld      (TKHAVESIG),a
                ld      (TKDCOUNT),a
                ld      (TKSTORED),a
                ld      (TKFLAGS),a
                ld      (TKINTLEN),a
                ld      (TKNZPOS),a
                ld      (TKEXP),a
                ld      (TKEXP+1),a
                ld      ix,TKDIG            ; TKDIG write cursor (own scratch)
                call    tkf_scan_digits     ; integer-part digits
                ld      a,(TKPOS)
                ld      (TKINTLEN),a        ; P = integer-part digit count
                push    hl                  ; D-DECBLANK S3: the dot is reachable
                call    tkf_fetch           ; ACROSS a blank run, from either side
                cp      '.'                 ; (`1 .5` and `1. 5` are both 1.5)
                jr      z,tkf_dot
                pop     hl                  ; not ours: the run stays in the source
                jr      tkf_nodot
tkf_dot:
                pop     af                  ; accept: the run belonged to the number
                inc     hl
                ld      a,(TKFLAGS)
                or      1                   ; bit0 = has_dot
                ld      (TKFLAGS),a
                call    tkf_scan_digits     ; fractional-part digits (pos continues)
tkf_nodot:
                call    tkf_try_exponent    ; consumes E/D exponent if well-formed
                ld      a,(TKFLAGS)
                bit     1,a                 ; has_exp?
                jr      nz,tkf_classify     ; exponent present -> no suffix check (oracle)
                call    tkf_try_suffix      ; consumes !/#/% if present
tkf_classify:
                ld      (TKSRCSAVE),hl      ; scanning is done -- park the source cursor;
                                             ; tkf_int_value/tkf_calc_and_round/
                                             ; tkf_emit_mantissa below all use HL as
                                             ; scratch (see sysvars.inc TKSRCSAVE)
                ld      a,(TKFLAGS)
                bit     5,a                 ; percent?
                jp      nz,tkf_check_percent
                bit     4,a                 ; hash?
                jp      nz,tkf_double
                bit     2,a                 ; expD?
                jp      nz,tkf_double
                bit     3,a                 ; bang?
                jp      nz,tkf_single
                bit     0,a                 ; dot?
                jp      nz,tkf_bydcount
                bit     1,a                 ; exponent (E, non-D)?
                jp      nz,tkf_bydcount
                ; plain literal, no forcing suffix/dot/exponent: maybe int
                ld      a,(TKDCOUNT)
                cp      5
                jp      c,tkf_go_int        ; D<=4 -> always int
                jp      nz,tkf_bydcount     ; D>5 -> not int-eligible
                call    tkf_cmp32767        ; D==5: CF set iff TKDIG[0..4] <= 32767
                jp      c,tkf_go_int
                jp      tkf_bydcount
tkf_check_percent:
                ld      a,(TKDCOUNT)
                cp      5
                jp      c,tkf_go_int
                jp      nz,tkf_overflow
                call    tkf_cmp32767
                jp      c,tkf_go_int
                jp      tkf_overflow
tkf_bydcount:
                ld      a,(TKDCOUNT)
                cp      7
                jp      nc,tkf_double
                ; falls through: D<=6 -> single
tkf_single:
                ld      a,SGL_DIGITS
                ld      (TKPC),a
                call    tkf_calc_and_round  ; -> TKLEAD + TKDIG[0..PC-1]; may not return
                                             ; (jp tkf_overflow on dec_exp>63); clobbers HL
                pop     de
                ld      a,SNG_TOKEN
                ld      (de),a
                inc     de
                ld      a,(TKLEAD)
                ld      (de),a
                inc     de
                call    tkf_emit_mantissa   ; also clobbers HL (own TKDIG walk)
                ld      hl,(TKSRCSAVE)      ; restore the source cursor for tk_loop
                jp      tk_loop             ; continue tokenising (HL/DE advanced)
tkf_double:
                ld      a,DBL_DIGITS
                ld      (TKPC),a
                call    tkf_calc_and_round
                pop     de
                ld      a,DBL_TOKEN
                ld      (de),a
                inc     de
                ld      a,(TKLEAD)
                ld      (de),a
                inc     de
                call    tkf_emit_mantissa
                ld      hl,(TKSRCSAVE)
                jp      tk_loop             ; continue tokenising (HL/DE advanced)
tkf_go_int:
                call    tkf_int_value       ; DE = value (0..32767); clobbers HL
                ld      b,d
                ld      c,e                 ; BC = value
                pop     de                  ; DE = TOKBUF destination cursor
                ld      hl,(TKSRCSAVE)      ; restore the source cursor for tk_loop
                jp      tkf_emit_int_bc
tkf_overflow:
                pop     de                  ; nothing of this literal was emitted yet,
                                             ; so DE is exactly the line-truncation point
                ld      a,1
                ld      (TKOVF),a
                jp      tk_end              ; end the line here (TKOVF flags the reject;
                                             ; DE is the truncation point for the 0 term)

; --- tkf_scan_digits: consume a run of ASCII digits at (HL) -----------------
; Shared by the integer-part and fractional-part scans (pos is continuous
; across the '.'), so intlen (P) and the first-nonzero position (f) come out
; right regardless of which side of the dot they fall on (own-design, derived
; from the oracle captures: dec_exp = P - f + explicit_exp exactly reproduces
; every §9.2 example, `.000001`'s dec_exp=-5 included). Leading zeros are
; skipped (not stored, not counted in D); once the first nonzero digit is
; seen, every digit from there on (incl. trailing zeros) is stored into TKDIG
; (capped at 24 bytes; TKDCOUNT keeps counting past the cap for correct
; single/double classification even on a very long literal). IX = TKDIG write
; cursor (free during tokenise; no conflict with the evaluator's IX use).
; Clobbers A, B.
tkf_scan_digits:
                push    hl                  ; D-DECBLANK S2 (docs/spec-basic-decblank.md
                call    tkf_fetch           ; §4): the digit run is blank-transparent --
                cp      '0'                 ; `1 0` is the single literal 10 on BOTH
                jr      c,tksd_stop         ; references, byte-identical to `1 0`'s
                cp      '9'+1               ; unblanked form.
                jr      nc,tksd_stop
                ; ⚠️ THE DISCARD COMES AFTER THE DIGIT IS EXTRACTED, AND THAT
                ; ORDER IS THE WHOLE INSTRUCTION. `pop af` is how the pushed HL
                ; is thrown away, but it LOADS A from the stack -- putting it
                ; before the `sub '0'` fed the source pointer's high byte to the
                ; accumulator, so `A=1` crunched to the integer 187 and `A=1E2`
                ; overflowed the literal and refused the line. The gate caught it
                ; on the first run; static reading of the diff did not.
                sub     '0'
                ld      b,a                 ; B = digit value 0..9
                pop     af                  ; a digit follows: the run was the
                                            ; number's, so keep the advanced HL
                ld      a,(TKHAVESIG)
                or      a
                jr      nz,tksd_have
                ld      a,b
                or      a
                jr      nz,tksd_first
                jr      tksd_advance        ; leading zero: not stored, not counted
tksd_first:
                ld      a,1
                ld      (TKHAVESIG),a
                ld      a,(TKPOS)
                ld      (TKNZPOS),a         ; f = position of the first nonzero digit
tksd_have:
                ld      a,(TKDCOUNT)
                cp      200
                jr      nc,tksd_dsat
                inc     a
                ld      (TKDCOUNT),a        ; D += 1 (saturating)
tksd_dsat:
                ld      a,(TKSTORED)
                cp      24
                jr      nc,tksd_advance     ; TKDIG full -> still counted in D, not stored
                ld      (ix+0),b
                inc     ix
                inc     a
                ld      (TKSTORED),a
tksd_advance:
                ld      a,(TKPOS)
                inc     a
                ld      (TKPOS),a
                inc     hl                  ; HL is at the DIGIT (tkf_fetch left it
                jr      tkf_scan_digits     ; there), so this is still one past it
tksd_stop:
                ; ⚠️ THE RUN IS NOT OURS AND EVERY BLANK OF IT STAYS. Measured:
                ; `20 A=1 +2` stores `<12> <F1><13>` and `20 A=1  +2` keeps BOTH
                ; blanks, on the VG-8020 and the CF-3300 alike. That is where the
                ; decimal literal differs from the LEADING LINE NUMBER, which eats
                ; exactly one separator blank (parse_lineno / pl_bl_end) -- so
                ; "copy the line-number scanner" would have been wrong here, and
                ; only a row with a NON-digit past the blanks could say so
                ; (docs/decblank-msx1-characterization.md §1.1).
                pop     hl
                ret

; --- tkf_fetch: the next character, SKIPPING ANY RUN OF BLANKS --------------
; in:  HL = source cursor.
; out: A  = the first non-blank character at or after (HL); HL = ITS address.
; Clobbers A, HL only (IX = the TKDIG cursor and DE = the exponent accumulator
; are both live across calls to this).
;
; D-DECBLANK R-D3: the cursor this scan finally reports is ONE PAST THE LAST
; CHARACTER IT ACTUALLY CONSUMED. Lookahead may cross any number of blanks; only
; consumption commits them. So every caller PUSHes HL first and then either
;   pop af   -- accept: the blank run belonged to the number, and HL stays here
;   pop hl   -- reject: the run is not ours, and the source is untouched
; ⚠️ That split is the whole rule. A `pop af` on the reject path makes a scan
; that finds nothing still swallow the blanks (knife K4), and a `pop hl` on the
; accept path rewinds every iteration (K2) -- two different wrong answers that
; a probe row without a trailing blank cannot tell apart from the right one.
tkf_fetch:
                ld      a,(hl)
                cp      ' '
                ret     nz
tkf_f_lp:
                inc     hl
                ld      a,(hl)
                cp      ' '
                jr      z,tkf_f_lp
                ret

; --- tkf_try_exponent: consume an optional E/D exponent (§9.2 rule 6) ------
; HL -> the char right after the mantissa digits. If E/e/D/d is followed by
; an OPTIONAL sign and then ZERO OR MORE digits, all of it is consumed: TKFLAGS
; bit1 (has_exp) [+bit2 (expD), forces double] is set, the signed magnitude is
; accumulated into TKEXP (16-bit, saturated at +-9999 -- far outside the
; legal +-63 dec_exp range, so the saturation never affects a correctly
; classified literal), and HL advances past it. Only the ABSENCE of a marker
; leaves HL unchanged.
;
; ⚠️ D-EXPBAD's headline below said THERE IS NO FAILURE CASE. There is exactly
; one, and it is at the top of the routine, not here: an `E` in front of `L`/`Q`
; is not a marker at all (D-EXPKW, tke_mark_e). Once the marker IS taken, the
; paragraph below holds unchanged -- the digits really are optional.
;
; 🔴 D-EXPBAD (docs/spec-basic-expbad.md, landed 2026-07-31): THE DIGITS ARE
; OPTIONAL AND THERE IS NO ROLLBACK. This used to put a digitless marker BACK --
; own-design, never oracle-pinned, and wrong. Measured on both references
; (docs/expbad-msx1-characterization.md):
;   1E     -> <1D>A<10><00><00>            a SINGLE 1.0, marker EATEN
;   1E+    -> the same; the sign goes too
;   1D     -> <1F>A<10>x6                  a DOUBLE -- THE PRECISION SURVIVES
;   1E#    -> <1D>A<10><00><00> then '#'   the suffix scan is SKIPPED, as it is
;                                          for a well-formed exponent (below)
;   12345EX-> a SINGLE, not the two-byte INT the digit count alone would give
; ⚠️ The last two are the rows that say has_exp must be SET rather than merely
; "the marker consumed", and `1D` is the only row in the language that says the
; PRECISION is remembered -- every row the defect was filed with was an `E`.
; It does NOT reach branch_lineno's line-number scan (`GOTO 1EX` keeps `EX` on
; both references) or a DATA body.
;
; Oracle-pinned quirk (S2 extra capture, 2026-07-11, same probe machinery as
; basic_probe_floatlit.py's --machine mode): once an exponent IS consumed, a
; trailing !/#/% is NOT treated as a suffix -- it is left as a raw verbatim
; byte. Captures (VG-8020, `bload"cas:",r:a=<lit>`, KBUF tail):
;   1e10# -> 1D 4B 10 00 00 23 00...   ($23 = '#', uneaten)
;   1e5#  -> 1D 46 10 00 00 23 00...
;   1e1#  -> 1D 42 10 00 00 23 00...
;   1d5!  -> 1F 46 10 00 00 00 00 00 00 21 00...   ($21 = '!', uneaten)
; i.e. the classification is exactly as if no suffix were present (E doesn't
; force a precision; D forces double); tk_loop's caller in tk_float enforces
; this by skipping tkf_try_suffix whenever TKFLAGS bit1 is set. Clobbers
; A, B, C, DE.
;
; D-DECBLANK S4: the marker, its sign and its digits are ALL reachable across a
; blank run -- `1 E2`, `1 E 2`, `1E -2`, `1E- 2` and `1E 2 3` (= 1E23) are all
; measured on both references. The `push` at the top is what makes a run that
; leads to NO MARKER stay in the source; D-EXPBAD then removed the only other
; rollback this routine had.
tkf_try_exponent:
                push    hl                  ; restore target if there is NO marker
                call    tkf_fetch
                call    upcase
                cp      'E'
                jr      z,tke_mark_e
                cp      'D'
                jr      z,tke_mark_d
                pop     hl                  ; no marker: the run is not ours
                ret
tke_mark_d:
                ld      a,1
                ld      (TKEXPD),a
                jr      tke_go
tke_mark_e:
                ; 🔴 D-EXPKW (docs/spec-basic-expkw.md): AN `E` IN FRONT OF `L` OR
                ; `Q` IS NOT A MARKER. `ELSE` and `EQV` are the only reserved words
                ; in the language that begin with `E`, and both references hardcode
                ; the two LETTERS rather than matching the words -- measured over
                ; the whole second-letter alphabet, twice
                ; (docs/expkw-msx1-characterization.md §2):
                ;   1 EL / 1 EQ  -> `A<EF><12> EL`   KEPT, and neither is a keyword
                ;   1 ERL/1 DIM  -> marker EATEN,    and both ARE keywords
                ;   1 D<c>       -> EATEN, 26/26.    `D` has no protected letter
                ; so `match_kw` here would be both wrong and dearer (it EMITS to
                ; (DE), so it would need a scratch destination cursor).
                ; ⚠️ This is the rollback D-EXPBAD deleted, re-aimed. "The digits
                ; are optional and there is no failure case" was generalised from
                ; five rows that all put a NON-word behind the marker; the cost was
                ; `PRINT 0 EQV 0` reading as `0E`+`QV`+`0` and `IF..THEN..ELSE`
                ; storing no $A1 at all, i.e. two whole acceptance suites.
                ; The lookahead is blank-transparent and sits at the character
                ; immediately after the marker AND NOWHERE ELSE: behind a consumed
                ; sign the ordinary rules resume (`1 E+L` is a single 1.0 then `L`,
                ; expb-elsign). Tested BEFORE TKEXPD is stored, so a rejected
                ; marker writes nothing; returning with has_exp CLEAR is what
                ; leaves `1EL%` its suffix scan (expb-elpct).
                push    hl                  ; HL is ON the marker
                inc     hl
                call    tkf_fetch
                call    upcase
                cp      'L'
                jr      z,tke_notmark
                cp      'Q'
                jr      z,tke_notmark
                pop     hl                  ; not L/Q: the E arm runs as before
                xor     a
                ld      (TKEXPD),a
                jr      tke_go
tke_notmark:
                pop     hl                  ; discard the lookahead cursor
                pop     hl                  ; the routine's own pre-blank target --
                ret                         ; blanks, marker and letter all stay in
                                            ; the source (`1 E L` is verbatim)
tke_go:
                inc     hl                  ; past E/D -- the LAST CONSUMED character
                xor     a                   ; so far, which is what the cursor tracks
                ld      (TKEXPSIGN),a       ; 0 = positive
                ; D-EXPBAD: the sign lookahead gets the same push/accept/reject
                ; shape as every other fetch (docs/spec-basic-expbad.md §4.1).
                ; ⚠️ COMMITTING WHERE THIS CODE USED TO STAND EATS A BLANK.
                ; `tkf_fetch` advances past a blank run, so a bare fetch followed
                ; by an unconditional commit stores `1E X` as `…<00><00>X` -- the
                ; blank gone -- while every filed row stays green. Measured: both
                ; references keep it (`dec-emarkblk`), and drop it in `1E -X`
                ; where the blank sits before a sign that IS consumed
                ; (`dec-emarkbl2`). Those two rows are the whole reason for the
                ; push.
                push    hl
                call    tkf_fetch
                cp      '+'
                jr      z,tke_sign
                cp      '-'
                jr      nz,tke_nosign
                ld      a,1
                ld      (TKEXPSIGN),a       ; 1 = negative
tke_sign:
                pop     af                  ; accept: any blank run before the sign
                                            ; belonged to it. (`pop af` LOADS A --
                                            ; safe here only because tke_commit
                                            ; reloads it from TKFLAGS.)
                inc     hl                  ; past the sign
                jr      tke_commit
tke_nosign:
                pop     hl                  ; no sign: the blank run is not ours, and
                                            ; the exponent's digits (if any) are
                                            ; fetched by tke_dloop, which push/pops
                                            ; correctly on its own
tke_commit:
                ; 🔴 THERE IS NO FAILURE CASE. The exponent grammar is
                ; `[EeDd] [+-]? digit*` -- THE DIGITS ARE OPTIONAL -- measured on
                ; both references (docs/expbad-msx1-characterization.md §1):
                ; `1E` is a single 1.0 with the marker EATEN, `1E+` eats the sign
                ; too, and `1D` is a DOUBLE, so the marker's PRECISION survives a
                ; failure that consumes no digits. The rollback this used to do
                ; (`tke_fail`) was own-design and never oracle-pinned; asking the
                ; question retired it along with the two range tests that fed it.
                pop     de                  ; discard the marker's rollback slot
                ld      a,(TKFLAGS)
                or      2                   ; bit1 = has_exp
                ld      (TKFLAGS),a
                ld      a,(TKEXPD)
                or      a
                jr      z,tke_accum
                ld      a,(TKFLAGS)
                or      4                   ; bit2 = expD (forces double)
                ld      (TKFLAGS),a
tke_accum:
                ld      de,0                ; DE = exponent magnitude accumulator
tke_dloop:
                push    hl                  ; D-DECBLANK: the EXPONENT's own digit
                call    tkf_fetch           ; run is blank-transparent too --
                cp      '0'                 ; `1E 2 3` is 1E23 on both references,
                jr      c,tke_dstop         ; which the mantissa rows cannot say
                cp      '9'+1
                jr      nc,tke_dstop
                sub     '0'                 ; (extract BEFORE the discard: `pop af`
                ld      c,a                 ;  loads A -- see tkf_scan_digits)
                pop     af                  ; accept: commit the blank run
                push    hl                  ; save source cursor
                ld      h,d
                ld      l,e
                add     hl,hl
                add     hl,hl
                add     hl,de
                add     hl,hl
                ld      e,c
                ld      d,0
                add     hl,de               ; HL = DE_old*10 + digit
                ld      de,9999
                or      a
                sbc     hl,de
                jr      nc,tke_clamp
                add     hl,de
                ex      de,hl
                jr      tke_dnext
tke_clamp:
                ld      de,9999
tke_dnext:
                pop     hl                  ; restore source cursor
                inc     hl                  ; (HL is on the digit tkf_fetch found)
                jr      tke_dloop
tke_dstop:
                ; The digit run is over (and any blank run that merely trails it
                ; is not the exponent's). This is also the only exit, so there is
                ; no separate `tke_ddone` label any more -- pasmo warns about an
                ; unreferenced one, and a label kept for narration is exactly the
                ; kind of thing the dead-code gate exists to stop accumulating.
                pop     hl
                ld      a,(TKEXPSIGN)
                or      a
                jr      z,tke_esdone
                call    neg_de              ; DE = -DE; HL is the SOURCE CURSOR here
                                             ; (unlike flt_out's use of neg_de) -- must
                                             ; NOT be touched, so this (not an HL-based
                                             ; negate) is deliberate
tke_esdone:
                ld      (TKEXP),de
                ret

; --- tkf_try_suffix: consume an optional !/#/% type suffix -----------------
; Only called when tkf_try_exponent found none (see its header). Sets TKFLAGS
; bit3 (!) / bit4 (#) / bit5 (%) and advances HL past the char.
;
; D-DECBLANK S5: the suffix is reachable across a blank run, and it is not a
; spacing detail -- `20 A=1 #` stores a DOUBLE on both references where zerobas
; stored an integer and a stray '#', i.e. the divergence was in the token's TYPE.
; The three arms converge on one accept tail, which costs fewer bytes than the
; three `inc hl` / `ret` tails it replaces.
tkf_try_suffix:
                push    hl
                call    tkf_fetch
                cp      '!'
                jr      z,tks_bang
                cp      '#'
                jr      z,tks_hash
                cp      '%'
                jr      z,tks_pct
                pop     hl                  ; no suffix: every blank stays put
                ret
tks_bang:
                ld      a,(TKFLAGS)
                or      8
                jr      tks_done
tks_hash:
                ld      a,(TKFLAGS)
                or      16
                jr      tks_done
tks_pct:
                ld      a,(TKFLAGS)
                or      32
tks_done:
                ld      (TKFLAGS),a
                pop     af                  ; accept: the run belonged to the number
                inc     hl
                ret

; --- tkf_cmp32767: are the 5 stored digits TKDIG[0..4] <= 32767? -----------
; out: CF set iff <=32767. Clobbers A, B, C, D, E, HL.
tkf_cmp32767:
                ld      de,tkf_ref32767
                ; falls through into the general 5-digit comparator
; --- tkf_cmp5: are the 5 stored digits TKDIG[0..4] <= the bound at (DE)? ---
; DE -> a 5-entry unpacked-digit bound table. out: CF set iff <= bound.
; Clobbers A, B, C, D, E, HL.
tkf_cmp5:
                ld      hl,TKDIG
                ld      b,5
tkf_cmp_lp:
                ld      a,(de)
                ld      c,a
                ld      a,(hl)
                cp      c
                jr      c,tkf_cmp_small     ; stored < ref -> <=32767 -> CF set
                jr      nz,tkf_cmp_big      ; stored > ref -> >32767 -> CF clear
                inc     hl
                inc     de
                djnz    tkf_cmp_lp
                scf                         ; all equal -> ==32767 -> <=
                ret
tkf_cmp_small:
                scf
                ret
tkf_cmp_big:
                or      a
                ret
tkf_ref32767:
                db      3,2,7,6,7
; flt_to_int16's sign-dependent bounds (D-F1-2 address domain, see its header)
tkf_ref65535:
                db      6,5,5,3,5           ; positive ceiling: unsigned 16-bit
tkf_ref32768:
                db      3,2,7,6,8           ; negative magnitude ceiling (-32768)

; --- tkf_int_value: TKDIG[0..D-1] (D=TKDCOUNT, <=5 here) -> DE = value -----
; Same *10+digit accumulation idiom as tk_number (interp.asm); safe from
; 16-bit overflow because every caller has already confirmed D<=5 and, for
; D==5, value<=65535 at most (tkf_cmp5 against a caller-chosen bound: 32767
; in tk_float's int classification, 65535/32768 in flt_to_int16).
; Clobbers A, B, C, HL.
tkf_int_value:
                ld      de,0
                ld      a,(TKDCOUNT)
                or      a
                ret     z
                ld      b,a
                ld      hl,TKDIG
tiv_lp:
                ld      a,(hl)
                ld      c,a
                push    hl
                ld      h,d
                ld      l,e
                add     hl,hl
                add     hl,hl
                add     hl,de
                add     hl,hl
                ld      e,c
                ld      d,0
                add     hl,de
                ex      de,hl
                pop     hl
                inc     hl
                djnz    tiv_lp
                ret

; --- tkf_emit_int_bc: BC = value (0..32767) -> int token(s) at (DE) --------
; Same encoding as tk_number's tail (interp.asm): $11+n / $0F,<byte> /
; $1C,<word LE>. Tail-calls tk_loop.
tkf_emit_int_bc:
                ld      a,b
                or      a
                jr      nz,tei_w
                ld      a,c
                cp      10
                jr      nc,tei_b
                add     a,INT_DIGIT_BASE
                ld      (de),a
                inc     de
                jp      tk_loop             ; continue tokenising (HL/DE advanced)
tei_b:
                ld      a,INT1_TOKEN
                ld      (de),a
                inc     de
                ld      a,c
                ld      (de),a
                inc     de
                jp      tk_loop             ; continue tokenising (HL/DE advanced)
tei_w:
                ld      a,INT2_TOKEN
                ld      (de),a
                inc     de
                ld      a,c
                ld      (de),a
                inc     de
                ld      a,b
                ld      (de),a
                inc     de
                jp      tk_loop             ; continue tokenising (HL/DE advanced)

; --- tkf_calc_and_round: dec_exp + rounded mantissa -> TKLEAD/TKDIG --------
; in: TKPC = target precision (6/14), TKHAVESIG/TKINTLEN/TKNZPOS/TKEXP/
; TKDCOUNT/TKDIG (raw significant digits) from the scan.
; out: TKLEAD = final lead byte (0..127); TKDIG[0..TKPC-1] = the rounded/
; padded mantissa digit VALUES (0-9 each, not yet packed). On dec_exp>63
; (post-rounding) jumps to tkf_overflow and does not return.
; dec_exp = TKINTLEN - TKNZPOS + TKEXP (signed); dec_exp<=-64 -> TKLEAD=0
; with the mantissa still computed/retained (§9.2 rule 6, the "1e-65" case:
; reads as value 0, no error). Clobbers A, B, C, HL, DE.
tkf_calc_and_round:
                ld      a,(TKHAVESIG)
                or      a
                jr      nz,tcr_go
                ; value 0: lead=0, mantissa all zero (14 covers both PC cases)
                xor     a
                ld      (TKLEAD),a
                ld      hl,TKDIG
                ld      b,14
tcr_zero_lp:
                ld      (hl),a
                inc     hl
                djnz    tcr_zero_lp
                ret
tcr_go:
                ld      a,(TKINTLEN)
                ld      l,a
                ld      h,0
                ld      a,(TKNZPOS)
                ld      e,a
                ld      d,0
                or      a
                sbc     hl,de               ; HL = P - f
                ld      de,(TKEXP)
                add     hl,de               ; HL = dec_exp (pre-round)
                ld      (TKDEXP),hl
                call    tkf_round_mantissa  ; may bump TKDEXP by +1 (double carry-out)
                ld      hl,(TKDEXP)
                push    hl
                ld      de,63
                call    cmp16_bits          ; A=1/2/4 (lt/eq/gt); HL clobbered inside
                pop     hl
                cp      4
                jp      z,tkf_overflow      ; dec_exp > 63
                push    hl
                ld      de,$FFC0            ; -64
                call    cmp16_bits
                pop     hl
                cp      1
                jr      nz,tcr_leadok
                xor     a
                ld      (TKLEAD),a          ; dec_exp <= -64 -> forced lead 0
                ret
tcr_leadok:
                ld      de,64
                add     hl,de
                ld      a,l
                ld      (TKLEAD),a
                ret

; --- tkf_round_mantissa: round/pad TKDIG to TKPC digits, half-up -----------
; D<=PC: pad TKDIG[D..PC-1] with zeros, no rounding. D>PC: keep TKDIG[0..PC-1],
; round on TKDIG[PC] (>=5 rounds up, carrying through the kept digits). A full
; carry-out (every kept digit was 9) does NOT renormalise for single (TKDEXP
; unchanged -- the oracle-pinned `9999995!` -> 1000000 quirk) but DOES for
; double (TKDEXP += 1); either way the carried mantissa is "1" + (PC-1) zeros.
; Clobbers A, B, C, HL, DE.
tkf_round_mantissa:
                ld      a,(TKPC)
                ld      b,a
                ld      a,(TKDCOUNT)
                cp      b
                jp      c,trm_pad
                jp      z,trm_pad
                ; D > PC: round using TKDIG[PC]
                ld      hl,TKDIG
                ld      c,b
                ld      b,0
                add     hl,bc
                ld      a,(hl)
                cp      5
                ret     c                   ; rounding digit < 5 -> truncate as-is
                call    trm_increment       ; CF set iff it carried out of all PC digits
                ret     nc
                call    trm_set_carried_mantissa
                ld      a,(TKPC)
                cp      14
                ret     nz                  ; single: quirk -- dec_exp unchanged
                ld      hl,(TKDEXP)
                inc     hl
                ld      (TKDEXP),hl
                ret
trm_pad:
                ld      a,(TKDCOUNT)
                ld      l,a
                ld      h,0
                ld      de,TKDIG
                add     hl,de               ; HL -> first pad slot
                ld      a,(TKPC)
                ld      b,a
                ld      a,(TKDCOUNT)
                ld      c,a
                ld      a,b
                sub     c                   ; A = PC - D
                ret     z
                ld      b,a
trm_pad_lp:
                ld      (hl),0
                inc     hl
                djnz    trm_pad_lp
                ret

; --- trm_increment: TKDIG[0..PC-1] += 1 (big-decimal) ----------------------
; out: CF set iff the increment carried out of the leftmost (index-0) digit.
; Clobbers A, B, HL.
trm_increment:
                ld      a,(TKPC)
                ld      b,a
                ld      hl,TKDIG
                dec     a
                ld      e,a
                ld      d,0
                add     hl,de               ; HL -> TKDIG[PC-1] (rightmost kept digit)
trm_inc_lp:
                ld      a,(hl)
                inc     a
                cp      10
                jr      c,trm_inc_done
                ld      (hl),0
                dec     hl
                djnz    trm_inc_lp
                scf                         ; carried past index 0
                ret
trm_inc_done:
                ld      (hl),a
                or      a
                ret

; --- trm_set_carried_mantissa: TKDIG = "1" + (PC-1) zeros ------------------
trm_set_carried_mantissa:
                ld      a,(TKPC)
                ld      b,a
                ld      hl,TKDIG
                ld      (hl),1
                inc     hl
                dec     b
trm_scm_lp:
                ld      a,b
                or      a
                ret     z
                ld      (hl),0
                inc     hl
                dec     b
                jr      trm_scm_lp

; --- tkf_emit_mantissa: TKDIG[0..PC-1] -> PC/2 packed-BCD bytes at (DE) ----
; 2 digits/byte, left-justified (MSX2 TH §9.1). Clobbers A, B, HL.
tkf_emit_mantissa:
                ld      a,(TKPC)
                ld      b,a
                srl     b                   ; B = PC/2 byte count
                ld      hl,TKDIG
tem_lp:
                ld      a,(hl)
                add     a,a
                add     a,a
                add     a,a
                add     a,a                 ; A = digit<<4 (digit<=9, no wraparound)
                inc     hl
                or      (hl)                ; | next digit (0..9)
                inc     hl
                ld      (de),a
                inc     de
                djnz    tem_lp
                ret

; --- sub-local neg_de (byte-identical clone of basic/float.asm neg_de) ------
; DE = -DE (two's complement); used by the exponent-sign path (tke_esdone). The
; resident copy stays with float-arith/flt_out in the low region (invisible
; here). Clobbers A.
neg_de:
                xor     a
                sub     e
                ld      e,a
                ld      a,0
                sbc     a,d
                ld      d,a
                ret

; --- sub-local upcase (byte-identical clone of basic/interp.asm upcase) ----
; A -> uppercase if 'a'..'z'. Resident copy is in page 1 (invisible here).
upcase:
                cp      'a'
                ret     c
                cp      'z'+1
                ret     nc
                sub     $20
                ret

; --- sub-local cmp16_bits (byte-identical clone of basic/expr.asm cmp16_bits) -
; Signed 16-bit compare HL?DE -> A: 2 equal / 1 less / 4 greater.
cmp16_bits:
                ld      a,h
                cp      d
                jr      nz,c16_ne
                ld      a,l
                cp      e
                jr      nz,c16_ne
                ld      a,2
                ret
c16_ne:
                or      a
                sbc     hl,de
                jp      pe,c16_vset
                jp      m,c16_lt
                jr      c16_gt
c16_vset:
                jp      p,c16_lt
                jr      c16_gt
c16_lt:
                ld      a,1
                ret
c16_gt:
                ld      a,4
                ret
