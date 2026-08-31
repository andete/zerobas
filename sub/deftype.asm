; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; deftype.asm -- DEFINT / DEFSNG / DEFDBL / DEFSTR as a PAGE-0 sub-ROM tenant
; (SUBROM_IDX_DEFTYPE). docs/spec-eviction-g6-space.md.
;
; WHY THIS ONE. G6 (DRAW) needed ~86 B of page-1 tail that did not exist, and the
; runway scouted for it turned out to straddle. This carve was found by the
; tenancy analysis in scratchpad/g6_carve_scout.py, which classifies every
; resident routine by the rule the G6 spec (§8) writes down: a PAGE-0 tenant may
; call page-1 residents but NOT the BIOS or the page-0 low region (the float
; pack), so a candidate is clean only if its TRANSITIVE closure stays off page 0.
; Almost nothing qualifies -- most statements reach `eval`, and eval bottoms out
; in the float pack -- but DEFtype does: it was a pure mnemonic parse plus a
; DEFTBL fill (a token peek plus that fill today, see the D-DEFINTTOK note
; below), with no eval, no BIOS, and no float work either way. It is also cold (a
; declaration, run once), so a CALSLT round trip per execution costs nothing.
;
; The body below is the resident routine MOVED VERBATIM, with three edits: the
; token cursor arrives and leaves through DEFT_PTR (CALSLT clobbers registers),
; `jp stmt_error` becomes a status the resident stub raises, and `jp exec_stmt`
; becomes a normal return. Nothing about the LANGUAGE changed -- DEFtype is
; repack-only, so the lean cart never had it by
; construction (no -body.inc dance needed, unlike the casmatch carve).
;
; skip_spaces is duplicated sub-locally (5 instructions); `upcase` and
; `is_letter` already exist in this page of the sub-ROM and are reused.
;
; D-DEFINTTOK (2026-08-18) and D-DEFTYPETOK (2026-08-19) between them replaced
; the FIRST of those three edits entirely. All four DEF<type> verbs now crunch
; to their own single-byte tokens ($AB..$AE, matching the reference), so this
; tenant no longer parses a mnemonic out of the line at all: it reads the token
; back from below the handed-over cursor and indexes a 4-byte type-code table.
; The mnemonic dispatch that used to stand at the top is DELETED, not bypassed
; -- with DEFSNG/DEFDBL/DEFSTR carrying their own kwtable rows there is no
; caller left that could reach it, and `make deadcode` fails a build that keeps
; unreachable code. No memory-ABI cell was added for any of this: main page 1
; had no spare bytes for the store + cold-boot reset a flag byte would cost --
; see ex_deftype's own comment in basic/usr.asm for the full story and the
; measurement.
;
; Clean-room: this is our own code, relocated. No disassembly.

deftype_tenant:
                ld      hl,(DEFT_PTR)       ; the resident's token cursor
                xor     a
                ld      (DEFT_STATUS),a     ; 0 = ok until something rejects
                ; D-DEFINTTOK / D-DEFTYPETOK: recover WHICH of the four verbs
                ; this was, without a memory-ABI flag byte (main page 1 had no
                ; room to spend setting one -- basic/usr.asm's ex_deftype
                ; comment carries the measurement). ex_deftype does nothing but
                ; `inc hl` past the statement token before handing the cursor
                ; over, so the byte just BELOW it IS that token: $AB DEFSTR,
                ; $AC DEFINT, $AD DEFSNG, $AE DEFDBL. They are contiguous by
                ; construction (basic/sysvars.inc says so and says not to
                ; reorder them), so `sub DEFSTR_TOKEN` turns the token into a
                ; 0..3 index straight into edt_codes below -- no compare chain,
                ; and the whole thing is sub-ROM, where there is room.
                ;
                ; ⚠️ NO RANGE CHECK, AND NONE IS REACHABLE. This tenant has
                ; exactly ONE caller now (ex_deftype), and interp.asm's dispatch
                ; table reaches that from exactly four token rows -- so the byte
                ; below the cursor cannot be anything but those four. The
                ; mnemonic-TEXT dispatch that used to stand here (and the
                ; ex_def path that fed it) is gone with D-DEFTYPETOK: DEFSNG/
                ; DEFDBL/DEFSTR have their own kwtable rows now, so no DEF<type>
                ; verb arrives as ASCII any more and DEF_TOKEN means DEF USR
                ; alone. Deleted rather than left unreachable -- the dead-code
                ; gate (`make deadcode`) would have failed the build otherwise.
                ld      a,(hl)              ; the statement token itself
                inc     hl                  ; step over it -> range-list text
                sub     DEFSTR_TOKEN        ; $AB..$AE -> 0..3
                push    hl
                ld      hl,edt_codes
                add     a,l                 ; index (the table cannot straddle a
                ld      l,a                 ;  page: 4 bytes, see the align note)
                ld      c,(hl)              ; C = DEFTBL type code for this verb
                pop     hl
                jr      edt_list
; Type codes in TOKEN ORDER ($AB DEFSTR, $AC DEFINT, $AD DEFSNG, $AE DEFDBL) --
; the same values the deleted mnemonic parser loaded (2 int / 4 single / 8
; double / DEFTBL_STR string, basic/sysvars.inc). ⚠️ The index add above is
; 8-bit (`add a,l`), so these four bytes must not cross a 256-byte boundary;
; the build-time assert below is what makes a future edit that moves them say
; so instead of reading garbage.
; ⚠️ AND THE ASSERT FIRED, ON AN EDIT IN A DIFFERENT FILE (D-DEFFN, 2026-08-22 --
; docs/deffn-impl-2026-08-22.md §4.5, branch `deffn-draft`). Adding a 40-byte
; routine to sub/arrays.asm -- included AHEAD of this file -- shifted these four
; bytes onto a page boundary and the BUILD said so, which is exactly what the
; guard was for. 🎯 What the guard could NOT do was say what to do about it, and
; "never let an unrelated sub-ROM edit relocate this table" is not a rule anyone
; can keep: every future sub page-0 tenant re-rolls the dice. So the alignment is
; now ENFORCED rather than asserted -- at most 3 bytes of page-0 padding, against
; 3 KB free, buy the 8-bit `add a,l` index unconditionally. The assert stays
; below as a PROOF that can no longer fire; if it ever does, this pad is what
; broke. On today's tree the pad emits NOTHING, which is why sub.rom is
; byte-identical across this change.
    IF (low $) > 252
                ds      256 - (low $), $00
    ENDIF
edt_codes:
                db      DEFTBL_STR          ; $AB DEFSTR
                db      2                   ; $AC DEFINT
                db      4                   ; $AD DEFSNG
                db      8                   ; $AE DEFDBL
    IF (high edt_codes) != (high (edt_codes+3))
                db      EDT_CODES_STRADDLES_A_PAGE__ADD_A_L_INDEX_IS_8_BIT
    ENDIF
edt_bad:
                jp      edt_fail
; --- range-list parser: C = type code (preserved by skip_spaces/is_letter/upcase)
edt_list:
edt_item:
                call    edt_skip_spaces
                call    is_letter           ; each item must start with a letter
                jr      nc,edt_bad
                call    upcase
                ld      b,a                 ; B = range-start letter
                inc     hl
                ld      d,b                 ; D = range-end (default = start, single letter)
                call    edt_skip_spaces
                cp      MINUS_TOKEN         ; "X-Y" range? ('-' crunched to $F2)
                jr      nz,edt_fill
                inc     hl                  ; past '-'
                call    edt_skip_spaces
                call    is_letter
                jr      nc,edt_bad
                call    upcase
                ld      d,a                 ; D = range-end letter
                inc     hl
edt_fill:
                ld      a,b                 ; start must not exceed end
                cp      d
                jr      z,edt_fill_go
                jr      nc,edt_bad          ; start > end -> reversed range, reject
edt_fill_go:
                push    hl                  ; guard the token cursor across the fill
                ld      a,d
                sub     b                   ; A = end - start (>= 0); compute the count
                inc     a                   ; NOW, before ld de,DEFTBL clobbers D (end)
                push    af                  ; count = span + 1, stashed across the addr calc
                ld      a,b
                sub     'A'
                ld      l,a
                ld      h,0
                ld      de,DEFTBL
                add     hl,de               ; HL -> DEFTBL[start]
                pop     af
                ld      b,a                 ; B = count
edt_fill_lp:
                ld      (hl),c              ; DEFTBL[letter] = type code
                inc     hl
                djnz    edt_fill_lp
                pop     hl                  ; restore the token cursor
                call    edt_skip_spaces
                cp      ','                 ; more items?
                jr      z,edt_comma
                ; 🔴 D-DEFCORNER (2026-08-31): this used to hand the cursor back
                ; on ANY non-comma byte -- so `DEFINT AC=7` filled A and then
                ; EXECUTED `C=7` as a statement (measured 7 here, ERR 2 on both
                ; references). The agreeing row `DEFINT AB` hid it: zb's
                ; re-dispatch of the bare `B` is ERR 2 too, the same code at the
                ; same line as the references' item reject -- two mechanisms
                ; agreeing by accident until the d.tail row made the tail
                ; harmless and observable. An item may end only at ',', ':' or
                ; EOL; anything else rejects the STATEMENT, not the next one.
                or      a                   ; end of line -> done
                jp      z,edt_ok
                cp      COLON               ; ':' -> the next statement runs
                jp      z,edt_ok
                jp      edt_fail            ; junk glued to the item -> ERR 2
edt_comma:
                inc     hl                  ; past ','
                jr      edt_item

; --- tenant tails: a status, not an interpreter jump ------------------------
edt_ok:
                ld      (DEFT_PTR),hl       ; hand the advanced cursor back
                ret
edt_fail:
                ld      a,1
                ld      (DEFT_STATUS),a     ; -> the stub raises stmt_error
                ret

; --- sub-local skip_spaces (the resident one is page-1; 5 instructions) -----
edt_skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      edt_skip_spaces
