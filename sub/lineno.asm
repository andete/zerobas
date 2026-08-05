; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; lineno.asm -- the ASCII line-number scanner as a PAGE-1 sub-ROM tenant
; (SUBROM_IDX_PARSELN). docs/spec-rom-region-evict-lineno.md (D-EVLNO), which
; opens rank 4 of docs/rom-region-structure-review.md §7 -- the first per-file
; eviction of that tier, and the first one costed by BUILDING it.
;
; WHY THIS ONE. A scout sweep of every page-1 label's own transitive closure
; (control AND data, tools/carve_scout.py after D-EVLNO's fix to it) found the
; tier is thin: almost every statement-shaped entry reaches `eval` -> the float
; pack, and every printing path reaches `pchar` -> CHPUT. Of the clusters that
; ARE closure-clean, this is the only one that is BOTH single-entry and free of
; interrupt context:
;   * play_service (217 B, 1 entry) runs from H.TIMI -- a CALSLT inside the VBLANK
;     handler, and circular besides (a page-0 tenant runs with $0038 paged out).
;     sub/beep.asm's header already rejected psv_fetch/psv_env for this reason.
;   * fat.asm+field.asm (193 B) needs 9 stubs AND reaches fatprim_bounce, i.e. a
;     PAGE-1 tenant -- which a page-0 tenant cannot call.
;   * trap_return_check (78 B) is on the RETURN-from-trap path, and T4/T5 measure
;     handler cost in JIFFIES.
;
; PAGE 1, AND FOR A REASON NEITHER title_tenant's NOR errmsg_tenant's. Those two
; are page-1 because their one outward edge is CHPUT (page-0 BIOS, invisible to a
; page-0 tenant). THIS body calls nothing at all -- no BIOS, no main low region,
; no main page 1, no CALSLT of its own -- so it is legal on EITHER island and
; needs neither one's privilege. The tie is broken by capacity: the page-0 entry
; table is FULL, 13 rows $0010..$0036 with ONE spare byte before the fixed $0038
; vector (sub/sub.asm), so the review's "prefer page 0" costing rule has no room
; to apply. Measured, not assumed: $0037 reads $FF and $0038 reads C3 0A F1.
;
; COLD, and the tree already argued it. dl_store calls this once per typed or
; loaded numbered line and then calls `tokenise` -- itself a sub-ROM tenant --
; five instructions later; basic/interp.asm's tokenise stub already records that
; a whole-line DI span on the line-entry path "is cosmetic (post-Enter; drifts
; JIFFY/TIME only, no functional effect)". This adds a second round trip to a path
; that already pays one.
;
; ⚠️ THE BODY BELOW IS THE RESIDENT ROUTINE MOVED VERBATIM -- every instruction,
; every internal label (pl_lp/pl_sat/pl_blank/pl_bl_lp/pl_bl_end) and every
; comment, so that a diff against `git show a191119:basic/program.asm` is a pure
; move and the D-LNBLANK contract can be audited without re-reading it. The ONE
; edit is the entry label: `parse_lineno` stays the name of the RESIDENT STUB, and
; the body is entered here as `pln_scan`, so no label exists in both builds.
;
; Clean-room: own code, moved unchanged. The D-LNBLANK blank/zero-separator rules
; it implements were pinned black-box against the VG-8020 and the CF-3300
; (docs/lnblank-msx1-characterization.md); no ROM bytes lifted.

; parseln_tenant -- the marshalling shell. IN: HL -> the first digit (passed
; through subrom_call/CALSLT). OUT: PLN_NUM = the line number, PLN_PTR = HL at the
; body. Nothing rides in registers: CALSLT owns them on the way out, which is why
; fatprim_bounce reloads DISKOP_HL/DISKOP_A rather than trusting the return.
; Cannot fail -- dl_store's ceiling check judges the value, not this routine.
parseln_tenant:
                call    pln_scan
                ld      (PLN_NUM),bc
                ld      (PLN_PTR),hl
                ret

; --- pln_scan (was parse_lineno): ASCII decimal at (HL) -> BC, HL advanced -----
; past the number. Accumulates BC = BC*10 + digit (16-bit; dl_store rejects
; anything past 65529 before the value is used, so the wrap this used to document
; is unreachable). Clobbers A, HL.
;
; D-LNBLANK (docs/spec-basic-lnblank.md): A BLANK INSIDE THE NUMBER IS
; TRANSPARENT. `2 0 REMX` stores line 20, `2 0 0 REMX` stores line 200 -- measured
; byte-exact on BOTH the VG-8020 and the CF-3300, which agree on all 54 rows
; (docs/lnblank-msx1-characterization.md §1). zerobas stopped at the blank and
; stored line 2, with the leftover digits crunched into the BODY: same source
; text, different line number AND different body.
;
; ⚠️ A BLANK IS ONLY TRANSPARENT WHEN A DIGIT FOLLOWS IT. Consuming blanks
; greedily gives the right line number and the WRONG BODY: the reference keeps
; every blank of the run except one, so `20  REMX` stores ` REM X` and not
; `REM X`. The scan therefore looks ahead across the run and only commits to it
; when it ends in a digit.
;
; ⚠️ AND THE SEPARATOR IT EATS DEPENDS ON THE VALUE, NOT THE TEXT. Exactly one
; blank separates the number from the body -- unless the line number is ZERO, when
; none is eaten (`0 REMX` -> ` REM X`, `00 REMX` -> ` REM X`, but `01 REMX` ->
; `REM X`). `00`/`01` differ only in VALUE, both have two digits and both start
; with `0`, so the discriminator is the value; `0 0 REMX` reaches zero THROUGH a
; blank and still eats none, which is the row that rules out "the digit run".
; That rule lives here rather than in dl_store because it is the same decision:
; the run of blanks that did NOT end in a digit is where the body begins.
; (Folding it in also pays for itself -- dl_store's `call skip_spaces` is gone.)
pln_scan:
                ld      bc,0
pl_lp:
                ld      a,(hl)
                cp      '0'
                jr      c,pl_blank
                cp      '9'+1
                jr      nc,pl_blank
                sub     '0'
                push    hl                  ; BC = BC*10 + A
                ld      h,b
                ld      l,c
                add     hl,hl               ; 2*acc
                jr      c,pl_sat
                add     hl,hl               ; 4*acc
                jr      c,pl_sat
                add     hl,bc               ; 5*acc
                jr      c,pl_sat
                add     hl,hl               ; 10*acc
                jr      c,pl_sat
                ld      c,a
                ld      b,0
                add     hl,bc               ; + digit
                jr      c,pl_sat
                ld      b,h
                ld      c,l
                pop     hl
                inc     hl
                jr      pl_lp
pl_sat:
                ; 🔴 THE CEILING CHECK IN dl_store CANNOT SEE AN ACCUMULATOR THAT
                ; ALREADY WRAPPED. `99999` is 99999-65536 = 34463 in 16 bits, which
                ; is comfortably UNDER the ceiling -- so a bound tested on the
                ; finished value passed it, and `99999 REM` still stored line 34463
                ; with the range check in place. Measured, not reasoned: the gate
                ; row stayed red after the first cut of the fix.
                ;
                ; So the overflow is caught WHERE IT HAPPENS. Any carry out of the
                ; BC*10+digit chain means the number has passed 65535, and 65535 is
                ; already past the ceiling -- saturating to $FFFF hands dl_store a
                ; value its own bound rejects, and the two checks together cover
                ; both halves (wrapped values here, 65530..65535 there).
                ;
                ; No need to consume the remaining digits: the caller refuses the
                ; line outright and never reads HL again. The `pop` only balances
                ; the push above.
                pop     hl
                ld      bc,$FFFF
                ret
pl_blank:
                ; Not a digit. Only a blank can continue the number; anything else
                ; ends it here, with HL on it (`20REMX`, `2 X=1`).
                cp      ' '
                ret     nz
                push    hl                  ; where the run of blanks starts
pl_bl_lp:
                inc     hl
                ld      a,(hl)
                cp      ' '
                jr      z,pl_bl_lp          ; ANY run is transparent, not just one
                cp      '0'
                jr      c,pl_bl_end
                cp      '9'+1
                jr      nc,pl_bl_end
                pop     af                  ; a digit follows -> the run belonged to
                jr      pl_lp               ; the number; keep the advanced HL
pl_bl_end:
                pop     hl                  ; back to the first blank of the run
                ld      a,b                 ; the number/body separator: exactly one
                or      c                   ; blank, and NONE when the value is zero
                ret     z
                inc     hl
                ret
