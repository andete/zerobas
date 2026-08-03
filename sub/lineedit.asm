; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — lineedit.asm  (numbered-line editor TXTTAB-memmove tenant)
; ===========================================================================
; store_line's insert/delete body (prog_find_del/delete_at/open_gap/the
; token-body copy) + the relink loop, evicted from the repack main ROM's
; basic/program.asm into sub-ROM PAGE 1 (docs/spec-eviction-g4-space.md §4,
; carve #2 of the G4-space eviction slice). dispatch_line/store_line's own
; parse head stays MAIN-RESIDENT and already marshals its two inputs into RAM
; before this carve even existed (SL_NUM = target line number, SL_TOK = the
; crunched token-body pointer, basic/sysvars.inc) -- nothing new to marshal.
; The tenant reports back only an OOM status byte (LE_STATUS); the resident
; store_line head does the existing `ld a,7 / jp raise_error` (raise_error is
; main PAGE-1 resident, unreachable from here) -- the exact head/body split
; docs/spec-eviction-g4-space.md §4 calls for.
;
; ONE index, SELECTOR-DISPATCHED (LE_OP, aliased onto the SAME DISKOP_OP/
; DISKOP_STATUS cells fatprim/dirverb/audio already share -- one subrom_call
; reaches exactly one tenant, so the separate value namespaces never
; collide): LE_OP_STORE (0) processes SL_NUM/SL_TOK exactly like the
; original store_line (empty body -> delete; else bounds-check + insert),
; LE_OP_RELINK (1) just runs the relink loop -- reached by the RESIDENT
; `relink:` shim (basic/program.asm) for cload.asm's own 2 plain `call
; relink` sites, which still need a working resident label since the loop
; itself no longer lives there.
;
; LE_OP_DELRANGE (2) is the `DELETE <range>` STATEMENT, added whole by
; D-DELETE (docs/spec-basic-delete.md): argument parse, both validations and
; the delete walk, all here, because the walk drives delete_at/relink_body
; below and the argument marshals as a single pointer. It is the one op that
; reports an ERR CODE rather than a boolean in LE_STATUS -- basic/sysvars.inc
; records the widened contract. Its own header (below le_oom) carries the
; measured rules.
;
; WHY vars_reset IS NOT A STRADDLE. relink's own tail (repack) calls
; vars_reset (arrays slice-1/4b's scalar-region re-anchor + arrays-slice-4c's
; string-heap reset, basic/arrays.asm) to invalidate live scalars/arrays on
; every program edit. vars_reset is assembled in the main-ROM PAGE-0 LOW
; REGION (< $4000, e.g. $3D92 -- confirmed via build/basic-reloc.sym), NOT
; page 1: while a page-1 tenant runs, only main PAGE 1 is switched out (the
; BIOS + our own low region stay mapped, sub/sub.asm's own header, "PAGE 1 --
; the BIOS is visible but main BASIC is switched out"), so an ordinary
; in-slot `call vars_reset` from HERE reaches it directly, no subrom_call/
; CALSLT bounce needed. It is added to the resident-ABI import list
; (sub/basic-resident-abi.inc, tools/gen_resident_abi.py REQUIRED) purely so
; a future page-0-low shift can never leave this tenant calling a stale
; address (the same staleness guard fp_sqrt's 9 symbols already get) --
; NOT because it needs subrom_call marshalling. tools/check_tenant_
; closure.py's --page1 walk (a page-1 tenant's callee must be sub-local page
; 1 or < $4000) confirms this is closure-clean.
;
; skip_to_eol + le_tok_skip (+ le_tsk1/le_tsk2/le_tsk4/le_tsk8/le_tsk_str/le_tsk_rem/le_tsk_data) are
; DUPLICATED sub-locally, verbatim from basic/interp.asm: skip_to_eol itself
; calls le_tok_skip (a token-aware skip, needed so a stored line's own operand
; bytes -- e.g. a float literal's $00 mantissa byte -- are never mistaken for
; the line/statement terminator), and le_tok_skip is a pure leaf (reads only the
; tokenised program-text bytes at HL, calls nothing else) -- safe to
; duplicate, no straddle. (Bigger than the spec's own "~10 B" estimate, which
; only accounted for skip_to_eol itself and missed its le_tok_skip dependency;
; flagged here rather than silently eating the difference out of the G4
; budget.)
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/program.asm
; (basic/lineedit-body.inc / basic/interp.asm -- see those files' headers for
; the full line-link-format / token-stream provenance: MSX2 Technical
; Handbook Table 2.20 / Figure 2.12 for the control-flow token set, the
; line-link layout + text base allowed-source/oracle-confirmed). The
; dispatch/marshalling glue is own-design, the fatprim/dirverb precedent +
; MSX2 Technical Handbook CALSLT ABIs. No reference-ROM disassembly. See
; sub/PROVENANCE.md.
; ===========================================================================

; --- lineedit_tenant: the SUBROM_IDX_LINEEDIT entry -------------------------
; ⚠️ A FOURTH OP MADE THE OLD TWO-WAY `dec a / jp nz` WRONG, NOT MERELY
; INCOMPLETE. It read "anything that is not 1 is a delrange", so LE_OP_LSTRANGE
; would have run le_delrange and DELETED the lines a LIST was asked to print.
; The selector is an explicit ladder now.
lineedit_tenant:
                ld      a,(LE_OP)
                or      a
                jp      z,le_store              ; LE_OP_STORE = 0
                dec     a
                jp      z,relink_body           ; LE_OP_RELINK = 1 (cload.asm's own
                                                ; call sites); tail: vars_reset; ret
                dec     a
                jp      z,le_delrange           ; LE_OP_DELRANGE = 2 (D-DELETE)
                jp      le_lstrange             ; LE_OP_LSTRANGE = 3 (D-LSTRNG)

; --- le_store: store_line's own body (empty body -> delete; else bounds-
; check + insert), byte-for-byte the same logic as the pre-eviction
; store_line, minus the OOM raise (LE_STATUS reports it back instead).
; Inputs: SL_NUM (line number), SL_TOK (crunched token-body pointer, both
; RAM, set by the resident head before subrom_call).
le_store:
                ; D-DOTGAPS writer (a), R-DOT3a/R-DOT3a' (docs/spec-basic-dotgaps.md
                ; §2, measured in docs/dotgaps-msx1-characterization.md §4):
                ; storing a line records the line number TYPED. All THREE store
                ; forms funnel through here and all three write it -- an insert
                ; (cln-ins -> 25), a replacement (cln-edit -> 20), and 🔴 the
                ; BARE-LINE-NUMBER DELETE (cln-sdel), which leaves `.` naming a
                ; line that no longer exists so `LIST .` prints nothing.
                ; 🔴 AND THE `DELETE` VERB DOES NOT WRITE IT (cln-del reads
                ; `20 REM B` after `DELETE 40`). Two ways to remove a line, the
                ; same visible effect on the program, DIFFERENT effects on `.` --
                ; which is why le_delrange below has no write of its own and why
                ; this one may not move anywhere more "general".
                ; 🔴 HERE, NOT AT `le_ok`, AND THE DIFFERENCE IS MEASURED. D-DOTLINE
                ; put it on the SUCCESS path reasoning that "a refused line was not
                ; touched", and marked the placement UNMEASURED. Both references
                ; write it on an OOM-REFUSED store (`crf-oom` reads the typed 20
                ; with nothing stored and `crf-oomlst` proving the program never
                ; changed) and do NOT write it when the LINE NUMBER is refused
                ; (`crf-ovr`/`crf-huge` stay at 10, `Syntax error`). The 65529
                ; ceiling is checked in the resident head (basic/program.asm
                ; dl_store) before store_line marshals here, so this instruction
                ; is inside the one gap in the tree that satisfies both readings.
                ; ⚠️ NO EMULATOR ROW ON THIS SIDE CAN SEE IT: a line store is
                ; bounded by the CONSTANT TXTMAX below, not by HIMEM, so no CLEAR
                ; and no typed line reaches the OOM path at all (characterization
                ; §6 D4). tests/test_program.py's store_line OOM row is the
                ; instrument -- a green acceptance run is NOT coverage of this
                ; rule.
                ld      hl,(SL_NUM)
                ld      (DOT),hl
                ld      hl,(SL_TOK)
                ld      a,(hl)
                or      a
                jr      z,le_delete             ; empty body -> delete only
                ; line size = 4 (link+lineno) + body length (incl 00), found
                ; by a token-aware walk so embedded 00 operand bytes don't
                ; truncate it.
                call    skip_to_eol             ; HL (= SL_TOK) -> past the body's 00
                ld      de,(SL_TOK)
                or      a
                sbc     hl,de                   ; HL = body length incl. terminator
                ld      bc,4
                add     hl,bc                   ; HL = full line size
                ld      (SL_SIZE),hl
                ld      b,h
                ld      c,l                     ; BC = size (for the bounds check)
                ; bounds: PRGEND + size must stay below TXTMAX
                ld      hl,(PRGEND)
                add     hl,bc
                ld      de,TXTMAX
                or      a
                sbc     hl,de                   ; (PRGEND+size) - TXTMAX
                jr      nc,le_oom               ; >= TXTMAX -> out of memory
                call    prog_find_del           ; SL_SLOT = insertion point (post-delete)
                call    open_gap                ; make room of SL_SIZE at SL_SLOT
                ld      hl,(SL_SLOT)
                ld      (hl),0                  ; link placeholder (relink fills it)
                inc     hl
                ld      (hl),0
                inc     hl
                ld      a,(SL_NUM)              ; line number, LE
                ld      (hl),a
                inc     hl
                ld      a,(SL_NUM+1)
                ld      (hl),a
                inc     hl
                ld      de,(SL_TOK)             ; source = tokenised body
                ex      de,hl                   ; HL = source, DE = dest (after lineno)
                ld      bc,(SL_SIZE)            ; body length = full size - 4 header bytes
                dec     bc
                dec     bc
                dec     bc
                dec     bc
                ldir                            ; copy body incl. its 00 terminator
                jr      le_ok
le_delete:
                call    prog_find_del           ; deletes a matching line if present
le_ok:
                ; (the `DOT` write moved to le_store's head -- D-DOTGAPS, above)
                xor     a
                ld      (LE_STATUS),a           ; 0 = ok
                jp      relink_body             ; tail: vars_reset; ret
le_oom:
                ld      a,1
                ld      (LE_STATUS),a           ; 1 = out of memory
                ret

; --- le_delrange: DELETE [<lo>][-[<hi>]] (LE_OP_DELRANGE, D-DELETE) --------
; docs/spec-basic-delete.md §2, measured in
; docs/delete-msx1-characterization.md. The WHOLE verb is here -- parse,
; both validations and the walk -- because the walk drives the memmove engine
; below and the parse marshals as one pointer; basic/program.asm's ex_delete
; is a ~34 B marshalling head, against the ~88 B of main page 1 a resident
; parse would have cost (spec §3.1).
;   IN : SL_DELPTR = the statement cursor, ON the DELETE token (an alias of
;        SL_TOK -- §3.2 records the proof that store_line's cells are never in
;        flight with this op).
;   OUT: LE_STATUS = 0 (deleted; program relinked and vars_reset run) or the
;        ERR CODE ITSELF -- 2 (R-D6) or 5 (R-D2/R-D4).
;
; 🔴 THE TWO ENDS OF THE RANGE ARE NOT SYMMETRIC, AND THAT IS THE MEASURED
; FINDING. The HIGH end must name a stored line exactly (R-D2); the LOW end
; need not name anything at all (R-D3). `DELETE 15-30` deletes two lines
; cleanly and `DELETE 20-35` deletes nothing and raises -- the same shape with
; the missing number moved across the '-'.
le_delrange:
                ld      hl,(SL_DELPTR)
                inc     hl                      ; past the DELETE token
                call    ldr_num                 ; DE = lo (0 if absent -- R-D5)
                ld      (SL_DELLO),de
                ld      (SL_DELHI),de           ; R-D1: `DELETE n` IS `DELETE n-n`
                                                ; (dlt-one and dlt-same read the
                                                ; same ` 13  0 `)
                call    ldr_skipsp
                cp      MINUS_TOKEN             ; the '-' is the ORDINARY minus
                jr      nz,ldr_endarg           ; token and does not disarm
                inc     hl                      ; line-number mode, so the number
                call    ldr_num                 ; behind it is another $0E
                ld      (SL_DELHI),de           ; (characterization §1)
ldr_endarg:
                ; R-D6: anything but end-of-statement here is ERR 2, raised
                ; BEFORE a byte is deleted -- `DELETE 10,30` reads ` 15  2 `, all
                ; four lines still standing, even though the tokeniser happily
                ; arms across the comma. A ':' IS accepted, and R-D8 then
                ; abandons the rest of the line (dlt-tail: ERR 0, B unset).
                call    ldr_skipsp
                or      a
                jr      z,ldr_check
                cp      COLON
                ld      a,2                     ; (no flags -- the `cp` still holds)
                jr      nz,ldr_fail
ldr_check:
                ; R-D4: lo > hi -> ERR 5. NOT the same rule as R-D2 below, and
                ; dlt-rev is the row that separates them: `DELETE 30-20`'s high
                ; end 20 EXISTS, so R-D2 passes, and a machine that simply
                ; deleted the empty range would read ` 15  0 `. It reads ` 15  5 `.
                ld      hl,(SL_DELHI)
                ld      de,(SL_DELLO)
                or      a
                sbc     hl,de
                jr      c,ldr_fc
                ; R-D2: a line numbered EXACTLY hi must exist, and the check runs
                ; BEFORE the walk -- `DELETE 20-35` leaves lines 20 AND 30
                ; standing (dlt-himiss), which an implementation that deleted as
                ; it walked could not do. Past the last line is no exemption:
                ; `DELETE 10-65529`, the natural "everything from 10 on" idiom, is
                ; ERR 5 as well (dlt-hitop).
                ld      bc,(SL_DELHI)
                call    ldr_find
                jr      c,ldr_walk
ldr_fc:
                ld      a,5                     ; ERR 5: illegal function call
ldr_fail:
                ld      (LE_STATUS),a
                ret                             ; R-D7: a FAILED delete is a
                                                ; COMPLETE no-op -- no relink, no
                                                ; vars_reset, and the resident head
                                                ; leaves CONTVALID alone. Measured
                                                ; without a RUN in the way:
                                                ; dlt-varsbad keeps A=1 and
                                                ; dlt-contbad's CONT still resumes.
ldr_walk:
                ; Delete every stored line whose number is in [lo, hi].
                ;
                ; ⚠️ THE WALK STEPS WITH PRGEND + skip_to_eol AND NOT WITH THE LINK
                ; CHAIN. The first delete_at makes every link from that slot on
                ; stale -- relink does not run until ldr_done -- so a link walk
                ; would follow a dangling pointer on the second iteration.
                ; ldr_find above may use the chain precisely because it runs
                ; before any of this.
                ld      hl,TXTBASE
ldr_lp:
                ld      a,(PRGEND)              ; HL == PRGEND -> the end marker
                cp      l
                jr      nz,ldr_line
                ld      a,(PRGEND+1)
                cp      h
                jr      z,ldr_done
ldr_line:
                inc     hl
                inc     hl
                ld      e,(hl)                  ; DE = this line's number
                inc     hl
                ld      d,(hl)
                dec     hl
                dec     hl
                dec     hl                      ; HL back to the link field
                ld      bc,(SL_DELHI)
                ld      a,c                     ; hi - number: CF set -> past the
                sub     e                       ; top of the range. Lines are
                ld      a,b                     ; stored ASCENDING, so nothing
                sbc     a,d                     ; further on can be in it either.
                jr      c,ldr_done
                ld      bc,(SL_DELLO)
                ld      a,e                     ; number - lo: CF set -> not yet at
                sub     c                       ; the range. R-D3: the low end need
                ld      a,d                     ; not name a line; the walk starts
                sbc     a,b                     ; at the first stored line >= lo
                jr      c,ldr_skip              ; (dlt-lomid: `DELETE 25-30` takes
                                                ; only line 30, not 20).
                ld      (SL_SLOT),hl            ; in range: unlink it. delete_at
                call    delete_at               ; shifts the tail DOWN over this
                ld      hl,(SL_SLOT)            ; slot, so HL now addresses the
                jr      ldr_lp                  ; NEXT line and must NOT advance.
ldr_skip:
                inc     hl
                inc     hl
                inc     hl
                inc     hl                      ; past link(2) + lineno(2)
                call    skip_to_eol             ; -> next line (token-aware, so a
                jr      ldr_lp                  ; float literal's $00 byte is not
                                                ; mistaken for the terminator)
ldr_done:
                xor     a
                ld      (LE_STATUS),a           ; 0 = ok
                jp      relink_body             ; R-D7: relink, tail -> vars_reset.
                                                ; DELETE is a program EDIT and
                                                ; joins the tail every other edit
                                                ; already reaches (dlt-vars ` 0  0 `
                                                ; against dlt-varsctl's ` 1  0 `).

; --- le_lstrange: LIST [<lo>][-[<hi>]] -- PARSE ONLY (LE_OP_LSTRANGE) -------
; docs/spec-basic-listrange.md §2, measured in
; docs/listrange-msx1-characterization.md. Unlike le_delrange this is the parse
; and NOTHING ELSE: the walk stays resident because it prints through main
; page-1 pchar and CALSLTs the page-0 detokeniser, neither of which a page-1
; tenant can reach (spec §3.1 -- that is what makes DELETE's whole-verb split
; impossible for LIST, rather than merely expensive).
;   IN : LST_PTR = the statement cursor, ON the LIST token.
;   OUT: LST_LO / LST_HI = the range; LE_STATUS = 0, or 2 for R-LS6.
;
; 🔴 LIST'S RANGE RULES ARE NOT DELETE'S, AND FIVE OF THE TWENTY MEASURED SHAPES
; WOULD BE WRONG IF THEY HAD BEEN COPIED FROM le_delrange ABOVE. There is NO
; high-end existence check (`LIST 20-35` lists two lines where `DELETE 20-35` is
; ERR 5), NO reversal check (`LIST 30-20` lists nothing, ERR 0, where DELETE
; raises), and -- the sharpest one -- an ABSENT HIGH END IS 65535, NOT 0, so
; `LIST 20-` lists to the END of the program where `DELETE 20-` is ERR 5.
le_lstrange:
                ld      hl,(LST_PTR)
                inc     hl                      ; past the LIST token
                ld      de,0
                ld      (LST_LO),de             ; R-LS5: with neither end given,
                dec     de                      ; bare LIST is 0-65535 -- which is
                ld      (LST_HI),de             ; what forbids "hi defaults to lo"
                                                ; (that would make bare LIST 0-0 and
                                                ; list nothing; lst-all lists all)
                call    ldr_num                 ; CF set -> a $0E number was there
                jr      nc,llr_dash
                ld      (LST_LO),de
                ld      (LST_HI),de             ; R-LS1: `LIST n` IS `LIST n-n`
                                                ; (lst-one and lst-same both read B)
llr_dash:
                call    ldr_skipsp
                cp      MINUS_TOKEN             ; the '-' is the ORDINARY minus token
                jr      nz,llr_end              ; and does not disarm line-number
                inc     hl                      ; mode, so the number behind it is
                ld      de,$FFFF                ; another $0E (characterization §1)
                ld      (LST_HI),de             ; R-LS5: an absent HIGH end is the END
                call    ldr_num                 ; of the program (lst-openhi: `LIST
                jr      nc,llr_end              ; 20-` reads B|C|D, NOT nothing)
                ld      (LST_HI),de
llr_end:
                ; R-LS6: anything but end-of-statement here is ERR 2, raised
                ; BEFORE a line is printed -- `LIST 10,30` prints `Syntax error`
                ; and no listing, even though the tokeniser arms a $0E reference
                ; across the comma (lna-listcomma). A ':' IS accepted, and R-LS7
                ; then abandons the rest of the line (lse-tail: ERR 0, B unset).
                ; This is also the rule that answers `LIST .`, whose '.' is not
                ; crunched -- see spec §6 for why that is pinned and not fixed.
                call    ldr_skipsp
                or      a
                jr      z,llr_ok
                cp      COLON
                ld      a,2                     ; (no flags -- the `cp` still holds)
                jr      nz,llr_fail
llr_ok:
                xor     a
llr_fail:
                ld      (LE_STATUS),a
                ret                             ; NOTE: no relink, no vars_reset --
                                                ; R-LS8, LIST is not a program edit
                                                ; (lse-vars keeps A=1, lse-cont's
                                                ; CONT still resumes)

; --- ldr_skipsp: advance HL past blanks; A = (HL) --------------------------
; A sub-local clone of main page-1 `skip_spaces` ($4240), which is UNREACHABLE
; from here: while a page-1 tenant runs, main page 1 is switched out (this
; file's own header). Same reason skip_to_eol + le_tok_skip are duplicated
; below -- and like them it is a pure leaf over RAM, so no straddle.
ldr_skipsp:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      ldr_skipsp

; --- ldr_num: read an OPTIONAL `$0E,lo,hi` line-number reference -----------
; out: DE = its value, or 0 when there is none -- R-D5, "an absent number is
; 0", which is the whole of what makes `DELETE -30` (= 0-30, deletes from the
; start), `DELETE 20-` (= 20-0, ERR 5) and bare `DELETE` (= 0-0, ERR 5) fall
; out of R-D2/R-D4 with no rules of their own. HL advances only if there was
; one. Blanks first: `DELETE 20` stores the typed blank (characterization §1).
;
; ⚠️ CF REPORTS *PRESENCE*, AND ONLY D-LSTRNG READS IT. DELETE cannot tell "no
; number" from "the number 0" and does not need to -- R-D5 makes them the same
; thing, so it reads DE and ignores CF. LIST's R-LS5 is the opposite: an absent
; high end is 65535 and an absent low end is 0, so the two ends have DIFFERENT
; defaults and the caller must know which case it is in. Adding CF is therefore
; not a tidy-up, it is the whole difference between the two verbs' parses.
; DELETE's behaviour is unchanged (it never tested CF, and A is re-fetched by the
; ldr_skipsp that follows every call) -- knife K3 scores the dlt- rows to prove
; that rather than assert it.
;
; --- D-DOTLINE: the `.` arm (docs/spec-basic-dotline.md, R-DOT1/R-DOT2) -----
; 🎯 ONE RESOLVER, AND IT IS ALREADY SHARED. This is the single place both
; le_delrange and le_lstrange read a line number from, so `.` lands in BOTH
; implemented verbs at ONE site -- and AUTO/RENUM get it free the day they are
; dispatched. That is the whole reason `.` was worth doing as its own slice
; rather than inside DELETE (spec-basic-delete.md §6 declined exactly that).
;
; ⚠️ A `.` DOES NOT DISARM LINE-NUMBER MODE, AND NOTHING HAD LOCKED THAT BEFORE
; THIS SLICE. `LIST .-30` stores `<93> . <F2><0E><1E><00>` on both references
; (lna-listdotd): the '.' is the literal $2E and the 30 behind the '-' is still
; an armed $0E. That is NOT the obvious answer -- '.' is a NAME character
; everywhere else in the tokeniser (the whole `dot` battery exists because `B.5`
; is one identifier) and a name character DISARMS. Had it disarmed, the number
; behind the '-' would arrive as ASCII digits and the ldr_num call after the '-'
; would parse garbage.
;
; ⚠️ CF SET, exactly as for a $0E: `.` IS a number for R-LS5's purposes, so
; `LIST .-` gets the open-high-end default and not the no-number one.
ldr_num:
                call    ldr_skipsp
                ld      de,0                    ; R-D5 (does not disturb the flags
                cp      LINENO_TOKEN            ;  ldr_skipsp left in A)
                jr      z,ldrn_yes
                cp      '.'                     ; R-DOT1: the current-line form
                jr      z,ldrn_dot
                or      a                       ; CF CLEAR = no number here
                ret
ldrn_dot:
                inc     hl                      ; past the '.' (one byte, not four)
                ld      de,(DOT)
                scf                             ; CF SET = a number was read
                ret
ldrn_yes:
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                inc     hl
                scf                             ; CF SET = a number was read
                ret

; --- ldr_find: does a line numbered BC exist? CF set = yes -----------------
; Verbatim from basic/program.asm's `find_line_bc`, duplicated for the
; ldr_skipsp reason (it is main page-1 resident). Walks the LINK CHAIN, which
; is legal here and only here: R-D2 runs before anything is deleted, so every
; link is still valid. Clobbers A, DE, HL; BC is the input and survives.
ldr_find:
                ld      hl,TXTBASE
ldrf_lp:
                ld      e,(hl)                  ; DE = link
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                ret     z                       ; $0000 -> not found (`or e` left
                                                ; CF clear)
                push    hl                      ; compare line number at HL+2,+3
                inc     hl
                inc     hl
                ld      a,(hl)
                cp      c
                jr      nz,ldrf_next
                inc     hl
                ld      a,(hl)
                cp      b
                jr      nz,ldrf_next
                pop     hl
                scf
                ret
ldrf_next:
                pop     hl                      ; HL = current slot; DE = its link
                ex      de,hl
                jr      ldrf_lp

; --- prog_find_del: locate the slot for SL_NUM, deleting an exact match ----
; Walks the (currently valid) link chain. Sets SL_SLOT to the first line
; whose number >= SL_NUM (or the end marker). If a line of exactly SL_NUM
; exists, it is removed first so the caller can insert in its place.
; Clobbers A, BC, DE, HL. Verbatim from basic/program.asm.
prog_find_del:
                ld      hl,TXTBASE
pfd_lp:
                ld      e,(hl)                  ; DE = link
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                jr      z,pfd_here              ; end marker -> insert here, no match
                push    hl                      ; stored number at slot+2..+3
                inc     hl
                inc     hl
                ld      c,(hl)
                inc     hl
                ld      b,(hl)                  ; BC = stored line number
                pop     hl
                ld      de,(SL_NUM)
                ld      a,c                     ; compare stored(BC) - target(DE)
                sub     e
                ld      a,b
                sbc     a,d
                jr      c,pfd_next              ; stored < target -> keep walking
                ; stored >= target: this is the slot
                ld      a,c                     ; exact match?
                cp      e
                jr      nz,pfd_here
                ld      a,b
                cp      d
                jr      nz,pfd_here
                ld      (SL_SLOT),hl            ; same number -> delete then reuse slot
                call    delete_at
                ld      hl,(SL_SLOT)
                ret
pfd_here:
                ld      (SL_SLOT),hl
                ret
pfd_next:
                ld      e,(hl)                  ; reload link (the compare clobbered DE
                inc     hl                      ;  with SL_NUM), then advance to it
                ld      d,(hl)
                ex      de,hl                   ; HL = link -> next line
                jr      pfd_lp

; --- delete_at: remove the line whose slot is in SL_SLOT --------------------
; Shifts the rest of the program (including the end marker) down over it and
; shrinks PRGEND. Clobbers A, BC, DE, HL. Verbatim from basic/program.asm.
delete_at:
                ld      hl,(SL_SLOT)
                inc     hl                      ; skip link(2)+lineno(2) -> body
                inc     hl
                inc     hl
                inc     hl
                call    skip_to_eol             ; HL = next-line address (token-aware)
                ex      de,hl                   ; DE = next-line address
                ; count = (PRGEND+2) - next   (bytes to move, incl. end marker)
                push    de                      ; next (move source)
                ld      hl,(PRGEND)
                inc     hl
                inc     hl
                or      a
                sbc     hl,de
                ld      b,h
                ld      c,l                     ; BC = count
                ; PRGEND -= (next - slot)
                ld      hl,(SL_SLOT)
                ex      de,hl                   ; DE = slot, HL = next
                or      a
                sbc     hl,de                   ; HL = removed size (next - slot)
                ex      de,hl                   ; DE = size, HL = slot
                ld      hl,(PRGEND)
                or      a
                sbc     hl,de
                ld      (PRGEND),hl
                pop     hl                      ; HL = next (source)
                ld      de,(SL_SLOT)            ; DE = slot (dest)
                ld      a,b
                or      c
                ret     z                       ; nothing trailing to move
                ldir
                ret

; --- open_gap: insert SL_SIZE bytes at SL_SLOT, shifting the tail up --------
; Moves [SL_SLOT .. PRGEND+1] (program tail incl. end marker) up by SL_SIZE
; and grows PRGEND. Caller has already bounds-checked. Clobbers A, BC, DE,
; HL. Verbatim from basic/program.asm.
open_gap:
                ld      hl,(PRGEND)             ; count = (PRGEND+2) - slot
                inc     hl
                inc     hl
                ld      de,(SL_SLOT)
                or      a
                sbc     hl,de
                ld      b,h
                ld      c,l                     ; BC = count
                ld      hl,(PRGEND)
                inc     hl                      ; HL = last tail byte (PRGEND+1) = source end
                ld      de,(SL_SIZE)
                push    hl
                add     hl,de                   ; dest end = source end + size
                ex      de,hl                   ; DE = dest end
                pop     hl                      ; HL = source end
                ld      a,b
                or      c
                jr      z,og_end
                lddr                            ; shift the tail upward
og_end:
                ld      hl,(PRGEND)             ; PRGEND += SL_SIZE
                ld      de,(SL_SIZE)
                add     hl,de
                ld      (PRGEND),hl
                ret

; --- relink_body: recompute every line's link pointer, stopping at the end
; marker, then vars_reset. A line's link = the address of the following
; line's link field. Clobbers A, DE, HL, B, C. Verbatim from basic/
; program.asm's `relink` (repack arm), renamed here to avoid confusion with
; the resident marshalling shim of the same name (basic/program.asm) -- this
; IS the loop that shim's LE_OP_RELINK reaches, and le_store's own tail
; above reaches it directly (sub-local, no double subrom_call).
relink_body:
                ld      hl,TXTBASE
rlb_lp:
                ld      a,(PRGEND+1)            ; reached the end marker (HL == PRGEND)?
                cp      h                       ; (a fresh line's link is a placeholder
                jr      nz,rlb_more             ;  0000, so we cannot stop on link==0)
                ld      a,(PRGEND)
                cp      l
                jr      nz,rlb_more             ; HL != PRGEND -> more lines to link
                jp      vars_reset              ; tail call (own header: page-0 low-region
                                                ; resident, directly reachable here)
rlb_more:
                push    hl                      ; remember this link field
                inc     hl                      ; skip link (2) + lineno (2)
                inc     hl
                inc     hl
                inc     hl
                call    skip_to_eol             ; HL = next line (token-aware end-find)
                ex      de,hl                   ; DE = next-line address
                pop     hl                      ; HL = link field to fill
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ex      de,hl                   ; HL = next-line address
                jr      rlb_lp

; --- le_tok_skip: advance HL past one token, including its operand bytes ------
; Sub-local duplicate of basic/interp.asm le_tok_skip (own header: skip_to_eol's
; own dependency, a pure leaf, safe to duplicate). Verbatim (the org is
; $2812 here too, so the repack-only SNG/DBL float-literal cases are
; included, matching this sub-ROM's repack-only existence).
le_tok_skip:
                ld      a,(hl)
                inc     hl
                cp      HEX_TOKEN               ; $0C ,word
                jr      z,le_tsk2
                cp      INT2_TOKEN              ; $1C ,word
                jr      z,le_tsk2
                cp      LINENO_TOKEN            ; $0E ,word
                jr      z,le_tsk2
                cp      LINEADDR_TOKEN          ; $0D ,word
                jr      z,le_tsk2
                cp      OCT_TOKEN               ; $0B ,word
                jr      z,le_tsk2
                cp      INT1_TOKEN              ; $0F ,byte
                jr      z,le_tsk1
                cp      PEEK_PREFIX             ; $FF ,function-token byte
                jr      z,le_tsk1
                cp      SNG_TOKEN               ; $1D ,4 float value bytes. A mantissa
                jr      z,le_tsk4                  ; byte can be $00 (e.g. .5 -> 1D 40 50 00
                cp      DBL_TOKEN               ; 00), so without this stride skip_to_eol
                jr      z,le_tsk8                  ; mistakes it for the line/stmt terminator
                                                ; -- a stored `10 A=1.5` would never RUN.
                cp      '"'                     ; string literal
                jr      z,le_tsk_str
                cp      REM_TOKEN               ; REM -> rest of line
                jr      z,le_tsk_rem
                cp      DATA_TOKEN              ; DATA -> verbatim body to ':' / EOL
                jr      z,le_tsk_data
                ret                             ; 0-operand token / plain byte
le_tsk1:
                inc     hl
                ret
le_tsk2:
                inc     hl
                inc     hl
                ret
le_tsk8:                                           ; DBL_TOKEN: 8 value bytes (4 here + 4 in le_tsk4)
                inc     hl
                inc     hl
                inc     hl
                inc     hl
le_tsk4:                                           ; SNG_TOKEN: 4 value bytes
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ret
le_tsk_str:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                cp      '"'
                jr      nz,le_tsk_str
                ret
le_tsk_rem:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                jr      le_tsk_rem
le_tsk_data:                                       ; DATA body: verbatim ASCII to ':' or EOL,
                ld      a,(hl)                  ; left un-consumed (the ':' / 00 is stepped
                or      a                       ; by the caller's outer loop). Skipping the
                ret     z                       ; body as a unit means a stray control byte
                cp      COLON                   ; in it can never be misread as an operand-
                ret     z                       ; bearing token -- same end position as the
                inc     hl                      ; old byte-by-byte walk on valid DATA.
                jr      le_tsk_data

; --- skip_to_eol: HL at a token body -> HL just past the line's 00 ---------
; terminator. Token-aware (steps whole tokens via le_tok_skip above), so an
; operand byte equal to 00 is not mistaken for the terminator. Sub-local
; duplicate of basic/interp.asm skip_to_eol (verbatim).
skip_to_eol:
                ld      a,(hl)
                or      a
                jr      z,ste_done
                call    le_tok_skip
                jr      skip_to_eol
ste_done:
                inc     hl                      ; advance past the 00 terminator
                ret
