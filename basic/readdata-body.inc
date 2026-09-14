; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; readdata-body.inc -- the READ/DATA value engine: read_one_value + data_seek +
; data_parse_int. ONE body, TWO homes (the casmatch/lineedit pattern):
;
;   * included by the PAGE-0 sub-ROM tenant sub/readdata.asm
;     (SUBROM_IDX_READVAL), with a thin resident stub left behind in program.asm.
;
; The carve is page-0 CLEAN: it walks tokenised program RAM and parses ASCII --
; no eval, no float pack, no BIOS (docs/spec-eviction-g7-space.md). Its three
; shared callees (skip_spaces, upcase, tok_skip) stay resident and are duplicated
; sub-locally, the way DEFtype's skip_spaces was.
;
; Clean-room: this is our own code, relocated verbatim. No disassembly.

; --- read_one_value: fetch the next DATA item -------------------------------
; in:  (RDV_MODE) 0 = NUMERIC (parse the item as an int16), 1 = STRING (capture
;      the item's raw ASCII span into STRSCR). D-READVAR, docs/spec-basic-readvar.md.
; out: A = status -- 0 = out of data, 1 = an item was read (DE = the value in
;      numeric mode, STRSCR = [len][bytes] in string mode; the DATA cursor is
;      advanced to the following item), 2 = the item is NOT A NUMBER (numeric mode
;      only; the cursor is NOT advanced, the caller raises ERR 2).
; Clobbers A, BC, DE, HL.
;
; ⚠️ THE STATUS REPLACED A CARRY FLAG. It used to be (CF, DE), which is one bit and
; therefore could not carry the third answer -- and the third answer is the one the
; characterization found pointing the OTHER way (`DATA HELLO` / `READ A` is a Syntax
; error on both references; this engine used to parse no digits, yield 0 and store
; it silently). A two-valued return is why that divergence had nowhere to go.
read_one_value:
                ld      a,(DATASTATE)
                cp      2
                jr      z,rov_none          ; exhausted
                ; 🔴 D-READDIR: 3 = unpositioned FROM THE PROGRAM TOP, stored by
                ; vars_reset (RUN, NEW, CLEAR/MAXFILES and every program EDIT). It is a
                ; third state rather than a RESTORE_LINE seed because that seed costs ten
                ; bytes in the LOW region, which had five, while this branch costs twelve
                ; in the sub ROM, which had hundreds. RESTORE keeps its own contract:
                ; state 0 with RESTORE_LINE naming the line it restored to.
                cp      3
                jr      z,rov_top
                or      a
                jr      nz,rov_at           ; already positioned
                jr      rov_unpos
rov_top:
                ld      hl,TXTBASE
                ld      (RESTORE_LINE),hl
rov_unpos:
                ; unpositioned: seek the first DATA item from RESTORE_LINE
                ld      hl,(RESTORE_LINE)
                ld      (DATALINE),hl
                ld      a,(hl)              ; empty program / no line -> no data
                inc     hl
                or      (hl)
                jr      z,rov_none
                ld      hl,(DATALINE)
                inc     hl                  ; HL = body of RESTORE_LINE (link+4)
                inc     hl
                inc     hl
                inc     hl
                call    data_seek           ; -> DATAPTR at first item, or CF clear
                jr      nc,rov_none
rov_at:
                ld      hl,(DATAPTR)
                ld      a,(RDV_MODE)
                or      a
                jr      nz,rov_str          ; string target -> capture the raw span
                call    data_parse_int      ; DE = value, HL past the ASCII number
                push    de                  ; guard the value
                call    skip_spaces
                cp      ','                 ; another item in this DATA statement?
                jr      z,rov_comma
                or      a                   ; end of line ends the item too
                jr      z,rov_seek
                ; 🔴 D-KWBARS: AND SO DOES A ':' -- THE PREMISE WAS RIGHT AND THE
                ; CONCLUSION WAS BACKWARDS. This arm used to say "the tokeniser ends
                ; a DATA body AT a ':' (tk_data_rest), so a stored body never
                ; contains one and this needs no ':' arm". The first half is true and
                ; is exactly WHY the arm is needed: the body ends at the ':', so the
                ; byte the scan stops ON is that ':' -- which is neither ',' nor NUL,
                ; so it fell into the TRAILING JUNK path below and
                ; `DATA 42:READ A:PRINT A` answered `Syntax error in 10` where both
                ; references read 42. D-DATACOLON fixed the tokeniser and the runtime
                ; SKIP and left the CONSUMER; nothing had ever READ an item out of a
                ; DATA statement with a statement after it
                ; [[a-fix-falsifies-the-justification-beside-it]].
                cp      COLON
                jr      z,rov_seek          ; the DATA STATEMENT is over: seek the next
                ; Anything else is TRAILING JUNK, i.e. the item was never a number
                ; (`DATA HELLO` leaves data_parse_int sitting on the 'H'). Both
                ; references answer Syntax error; report it and leave the cursor
                ; alone. ⚠️ An EMPTY item is NOT junk -- `DATA ,X` parses zero
                ; digits and lands ON the comma, so it still reads back as 0.
                pop     de
                ld      a,2
                ret
rov_seek:
                call    data_seek           ; seek the next DATA statement
                jr      nc,rov_exhaust
                jr      rov_ok              ; DATAPTR updated, DATASTATE set below
rov_comma:
                inc     hl                  ; step past the comma
                ld      (DATAPTR),hl
rov_ok:
                ld      a,1
                ld      (DATASTATE),a
                pop     de                  ; DE = value
                ret                         ; A = 1: an item was read
rov_exhaust:
                ld      a,2                 ; this was the last item
                ld      (DATASTATE),a
                pop     de                  ; DE = value (this read still succeeds)
                ld      a,1
                ret
rov_none:
                xor     a                   ; 0 -> out of data
                ret

; --- rov_str: the item's RAW ASCII span -> STRSCR ([len][bytes]) ------------
; in: HL at the item start (DATAPTR). out: HL at the item's terminator, joining
; the numeric path's own comma / data_seek tail. STRSCR is page-3 RAM, so a page-0
; tenant may fill it; wrapping it as a descriptor may not happen here (RDV_MODE).
;
; 🔴 THE LEXING RULE IS MEASURED AND IT IS NOT SYMMETRIC (spec §6.1, both
; references): skip LEADING spaces, then take bytes VERBATIM to the next comma or
; the end of the statement -- `DATA PAD  ,X` reads back as 'PAD  ', two trailing
; spaces intact. Trimming the tail as well is the obvious rule and it is WRONG.
; A leading '"' delimits instead, so a comma inside quotes is content.
rov_str:
                call    skip_spaces         ; LEADING spaces are not part of the item
                ld      de,STRSCR+1         ; DE -> the byte buffer
                ld      b,0                 ; B = length so far
                cp      '"'
                jr      nz,rovs_lp
                inc     hl                  ; past the opening quote
rovs_qlp:
                ld      a,(hl)
                or      a
                jr      z,rovs_done         ; unterminated -> the EOL ends the item
                inc     hl
                cp      '"'
                jr      z,rovs_done         ; the closing quote ends it, and is eaten
                ld      c,a
                call    rovs_put
                jr      rovs_qlp
rovs_lp:
                ld      a,(hl)
                or      a
                jr      z,rovs_done
                cp      ','                 ; the separator is NOT consumed here --
                jr      z,rovs_done         ; the shared tail below steps over it
                cp      COLON               ; D-KWBARS: and an UNQUOTED ':' ends the
                jr      z,rovs_done         ; DATA STATEMENT, so it ends the item too.
                                            ; Without it `DATA AB:READ A$` read the
                                            ; whole rest of the line -- TOKENS and all
                                            ; -- into A$. The QUOTED loop above must
                                            ; NOT have this arm: a ':' inside quotes is
                                            ; content (D-DATACOLON `d.qcolon`).
                inc     hl
                ld      c,a
                call    rovs_put
                jr      rovs_lp
rovs_done:
                ld      a,b
                ld      (STRSCR),a          ; STRSCR = [len][bytes]
                push    de                  ; the tail pops a value; there is none in
                                            ; string mode, so keep its stack shape
                call    skip_spaces
                cp      ','
                jr      z,rov_comma
                jr      rov_seek
rovs_put:
                ld      a,b                 ; C = the byte. STRSCR holds STRMAX bytes;
                cp      STRMAX              ; a DATA item cannot reach that (LINEMAX is
                ret     nc                  ; 255 and crunching only shrinks), so this
                ld      a,c                 ; is a structural bound, not a live clamp
                ld      (de),a
                inc     de
                inc     b
                ret

; --- data_seek: scan forward for the next DATA statement --------------------
; in:  HL = a token position; DATALINE = link-field of the line containing it.
; out: CF set -> DATAPTR = first ASCII item after the next DATA token (DATALINE
;      updated if a line boundary was crossed); CF clear -> end of program.
; Token-aware via tok_skip so a constant's operand byte is never mistaken for a
; DATA token; a DATA statement's own ASCII body is never scanned (we stop AT the
; DATA token and the caller resumes past the statement's ':' / EOL).
data_seek:
ds_lp:
                ld      a,(hl)
                or      a
                jr      z,ds_eol            ; end of line -> follow the link
                cp      DATA_TOKEN
                jr      z,ds_found
                call    tok_skip
                jr      ds_lp
ds_eol:
                ld      hl,(DATALINE)       ; advance to the next line
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ld      a,d
                or      e
                jr      z,ds_none           ; $0000 link -> program end
                ex      de,hl               ; HL = next line link-field
                ld      (DATALINE),hl
                inc     hl                  ; HL = its body (link+4)
                inc     hl
                inc     hl
                inc     hl
                jr      ds_lp
ds_found:
                inc     hl                  ; past the DATA token
ds_sp:
                ld      a,(hl)              ; skip spaces before the first item
                cp      ' '
                jr      nz,ds_set
                inc     hl
                jr      ds_sp
ds_set:
                ld      (DATAPTR),hl
                scf
                ret
ds_none:
                or      a
                ret

; --- data_parse_int: parse an ASCII integer at (HL) -> DE -------------------
; Leading spaces, an optional '-', then decimal digits or a "&H" hex constant.
; HL stops at the first non-numeric byte. Clobbers A, BC, HL.
data_parse_int:
                call    skip_spaces
                cp      '-'
                jr      z,dp_neg
                cp      '&'
                jr      z,dp_hex
                jp      dp_decimal
dp_neg:
                inc     hl
                call    skip_spaces
                cp      '&'
                jr      z,dp_neghex
                call    dp_decimal
                jr      dp_negate
dp_neghex:
                call    dp_hex
dp_negate:
                push    hl                  ; preserve the cursor across the negate
                ld      hl,0
                or      a
                sbc     hl,de
                ex      de,hl               ; DE = -value
                pop     hl
                ret
dp_decimal:
                ld      de,0
dp_dlp:
                ld      a,(hl)
                cp      '0'
                ret     c
                cp      '9'+1
                ret     nc
                sub     '0'
                ld      c,a                 ; C = digit
                push    hl
                ld      h,d
                ld      l,e                 ; HL = acc
                add     hl,hl               ; 2*acc
                add     hl,hl               ; 4*acc
                add     hl,de               ; 5*acc
                add     hl,hl               ; 10*acc
                ld      b,0
                add     hl,bc               ; + digit
                ex      de,hl               ; DE = new acc
                pop     hl
                inc     hl
                jr      dp_dlp
dp_hex:
                inc     hl                  ; past '&'
                ld      a,(hl)
                call    upcase
                cp      'H'
                jr      nz,dp_hbad          ; only &H is supported here
                inc     hl                  ; past 'H'
                ld      de,0
dp_hlp:
                ld      a,(hl)
                call    upcase
                cp      '0'
                jr      c,dp_hdone
                cp      '9'+1
                jr      c,dp_hdig           ; '0'..'9'
                cp      'A'
                jr      c,dp_hdone
                cp      'F'+1
                jr      nc,dp_hdone
                sub     'A'-10              ; 'A'..'F' -> 10..15
                jr      dp_hacc
dp_hdig:
                sub     '0'
dp_hacc:
                ld      c,a                 ; nibble
                push    hl
                ld      h,d
                ld      l,e
                add     hl,hl
                add     hl,hl
                add     hl,hl
                add     hl,hl               ; 16*acc
                ld      b,0
                add     hl,bc               ; + nibble
                ex      de,hl
                pop     hl
                inc     hl
                jr      dp_hlp
dp_hdone:
                ret
dp_hbad:
                ld      de,0
                ret
