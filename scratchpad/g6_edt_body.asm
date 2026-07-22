ex_def_type:
                ld      a,(hl)
                inc     hl
                cp      'I'
                jr      z,edt_i             ; INT
                cp      'S'
                jr      z,edt_s             ; SNG or STR
                cp      'D'
                jr      z,edt_d             ; DBL
edt_bad:
                jp      stmt_error
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
                call    skip_spaces
                ld      a,(hl)
                call    is_letter           ; each item must start with a letter
                jr      nc,edt_bad
                call    upcase
                ld      b,a                 ; B = range-start letter
                inc     hl
                ld      d,b                 ; D = range-end (default = start, single letter)
                call    skip_spaces
                ld      a,(hl)
                cp      MINUS_TOKEN         ; "X-Y" range? ('-' crunched to $F2)
                jr      nz,edt_fill
                inc     hl                  ; past '-'
                call    skip_spaces
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
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; more items?
                jr      z,edt_comma
                jp      exec_stmt           ; end of the list -> run the next statement
edt_comma:
                inc     hl                  ; past ','
                jr      edt_item
