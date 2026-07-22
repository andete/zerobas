; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; readdata-body.inc -- the READ/DATA value engine: read_one_value + data_seek +
; data_parse_int. ONE body, TWO homes (the casmatch/lineedit pattern):
;
;   * lean cart (ROM_BASE >= $4000): included INLINE by basic/program.asm, so the
;     lean image is byte-identical to before the carve;
;   * repack build: included by the PAGE-0 sub-ROM tenant sub/readdata.asm
;     (SUBROM_IDX_READVAL), with a thin resident stub left behind in program.asm.
;
; The carve is page-0 CLEAN: it walks tokenised program RAM and parses ASCII --
; no eval, no float pack, no BIOS (docs/spec-eviction-g7-space.md). Its three
; shared callees (skip_spaces, upcase, tok_skip) stay resident and are duplicated
; sub-locally, the way DEFtype's skip_spaces was.
;
; Clean-room: this is our own code, relocated verbatim. No disassembly.

; --- read_one_value: fetch the next DATA item -------------------------------
; out: CF set + DE = value (DATA cursor advanced to the following item); CF clear
; if no DATA remains. Clobbers A, BC, HL.
read_one_value:
                ld      a,(DATASTATE)
                cp      2
                jr      z,rov_none          ; exhausted
                or      a
                jr      nz,rov_at           ; already positioned
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
                call    data_parse_int      ; DE = value, HL past the ASCII number
                push    de                  ; guard the value
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; another item in this DATA statement?
                jr      z,rov_comma
                call    data_seek           ; else seek the next DATA statement
                jr      nc,rov_exhaust
                jr      rov_ok              ; DATAPTR updated, DATASTATE set below
rov_comma:
                inc     hl                  ; step past the comma
                ld      (DATAPTR),hl
rov_ok:
                ld      a,1
                ld      (DATASTATE),a
                pop     de                  ; DE = value
                scf
                ret
rov_exhaust:
                ld      a,2                 ; this was the last item
                ld      (DATASTATE),a
                pop     de                  ; DE = value (this read still succeeds)
                scf
                ret
rov_none:
                or      a                   ; CF clear -> out of data
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
                ld      a,(hl)
                cp      '-'
                jr      z,dp_neg
                cp      '&'
                jr      z,dp_hex
                jp      dp_decimal
dp_neg:
                inc     hl
                call    skip_spaces
                ld      a,(hl)
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
