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
; in the float pack -- but DEFtype does: it is a pure mnemonic parse plus a
; DEFTBL fill, with no eval, no BIOS, and no float work. It is also cold (a
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
; Clean-room: this is our own code, relocated. No disassembly.

deftype_tenant:
                ld      hl,(DEFT_PTR)       ; the resident's token cursor
                xor     a
                ld      (DEFT_STATUS),a     ; 0 = ok until something rejects
                ld      a,(hl)
                inc     hl
                cp      'I'
                jr      z,edt_i             ; INT
                cp      'S'
                jr      z,edt_s             ; SNG or STR
                cp      'D'
                jr      z,edt_d             ; DBL
edt_bad:
                jp      edt_fail
edt_i:                                      ; "I" -> expect "NT"
                ld      a,(hl)
                cp      'N'
                jr      nz,edt_bad
                inc     hl
                ld      a,(hl)
                cp      'T'
                jr      nz,edt_bad
                inc     hl
                ld      c,2                 ; int
                jr      edt_list
edt_s:                                      ; "S" -> "NG" (single) or "TR" (string)
                ld      a,(hl)
                inc     hl
                cp      'N'
                jr      z,edt_sn
                cp      'T'
                jr      nz,edt_bad
                ld      a,(hl)              ; "ST" -> expect 'R'
                cp      'R'
                jr      nz,edt_bad
                inc     hl
                ld      c,DEFTBL_STR        ; string
                jr      edt_list
edt_sn:                                     ; "SN" -> expect 'G'
                ld      a,(hl)
                cp      'G'
                jr      nz,edt_bad
                inc     hl
                ld      c,4                 ; single
                jr      edt_list
edt_d:                                      ; "D" -> expect "BL"
                ld      a,(hl)
                cp      'B'
                jr      nz,edt_bad
                inc     hl
                ld      a,(hl)
                cp      'L'
                jr      nz,edt_bad
                inc     hl
                ld      c,8                 ; double
                ; fall through to edt_list
; --- range-list parser: C = type code (preserved by skip_spaces/is_letter/upcase)
edt_list:
edt_item:
                call    edt_skip_spaces
                ld      a,(hl)
                call    is_letter           ; each item must start with a letter
                jr      nc,edt_bad
                call    upcase
                ld      b,a                 ; B = range-start letter
                inc     hl
                ld      d,b                 ; D = range-end (default = start, single letter)
                call    edt_skip_spaces
                ld      a,(hl)
                cp      MINUS_TOKEN         ; "X-Y" range? ('-' crunched to $F2)
                jr      nz,edt_fill
                inc     hl                  ; past '-'
                call    edt_skip_spaces
                ld      a,(hl)
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
                ld      a,(hl)
                cp      ','                 ; more items?
                jr      z,edt_comma
                jp      edt_ok              ; end of the list -> hand the cursor back
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
