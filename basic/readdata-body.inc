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
; out: A = status -- 0 = out of data, 1 = an item was read: STRSCR = [len][bytes]
;      in BOTH modes since D-READFLT (ex_read parses a numeric one), DE = its
;      first byte in the program text, the DATA cursor advanced to the following
;      item. (Status 2, "not a number", is now ex_read's to decide.)
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
                ; ✅ D-READFLT (2026-10-09): a NUMERIC item is captured as TEXT
                ; too, and ex_read parses it with VAL's parser (inp_num, the one
                ; INPUT uses) -- this used to be data_parse_int, an int16 scanner, so
                ; `DATA 1.5` / `2E3` / `-.25` were Syntax error and `DATA 40000`
                ; read back as -25536 where the VG-8020 reads every one
                ; (scratchpad/readflt_run.out). The unquoted loop only: a '"' is
                ; content here, so `DATA "5"` reaches the parser with its quote and
                ; is refused there, as on the reference.
                call    skip_spaces         ; LEADING spaces are not part of the item
                ld      de,STRSCR+1
                ld      b,0
                jr      rovs_unq
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
; ✅ D-READREF (2026-10-07): the item is also returned BY ADDRESS. Its bytes are
; one contiguous run of the DATA text (DATA is not crunched), so the start pushed
; below -- after the leading spaces, after an opening quote -- is what the shared
; tail pops into DE (RDV_VAL), and ex_read points the variable there instead of
; copying it into the string space, as both references do.
rov_str:
                call    skip_spaces         ; LEADING spaces are not part of the item
                ld      de,STRSCR+1         ; DE -> the byte buffer
                ld      b,0                 ; B = length so far
                cp      '"'
                jr      nz,rovs_unq
                inc     hl                  ; past the opening quote
                push    hl                  ; the item's first byte (D-READREF)
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
rovs_unq:
                push    hl                  ; the item's first byte (D-READREF)
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
                ld      (STRSCR),a          ; STRSCR = [len][bytes]; the start pushed
                                            ; above is the value the tail pops
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

