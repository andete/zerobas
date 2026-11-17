; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSXL.COM -- D-CONCOL (2026-11-17): the BDOS console's LOGICAL COLUMN ($F237, the cell TAB
; expansion counts from) after every kind of output, the data for disk/docs/spec-bdos-concol.md.
; BDOSXC compares the screen; this measures the counter itself, case by case.
;
; Each case starts at column 0: a CONOUT CR first (CR is the one code both machines agree resets
; it). Then its bytes go out through CONOUT ($02), DIRIO-out ($06) or as one STROUT ($09) string,
; and two bytes are recorded: ($F237) and the screen cursor's CSRX. Case table: the function
; (0 = the end), the byte count, the bytes; a STROUT case's bytes end with its own '$'.
; The first two cells hold LINLEN and the column at entry.
;
; CLEAN-ROOM: 100% own code; the published BDOS interface and work-area cells. Nothing of the
; reference read.
;
; Build: pasmo --bin bdosxl.asm bdosxl.com bdosxl.sym

                org     $0100

BDOS            equ     $0005
LINLEN          equ     $F3B0
CSRX            equ     $F3DD
COLUMN          equ     $F237

start:
                jr      begin                   ; $0102 = $6C: a distinctive arm signature
                db      $6C
begin:
                ld      a, (LINLEN)
                ld      (head+0), a
                ld      a, (COLUMN)
                ld      (head+1), a
                ld      ix, results
                ld      hl, cases
next:
                ld      a, (hl)                 ; the function, 0 = the end
                or      a
                jp      z, finish
                ld      c, a
                and     $7F
                ld      (func), a
                inc     hl
                ld      b, (hl)                 ; the byte count
                inc     hl
                bit     7, c                    ; round 2: bit 7 = a CONTINUATION -- no CR,
                jr      nz, nocr                ; the count carries over from the case before
                push    hl
                push    bc
                ld      e, 13                   ; every case starts at column 0
                ld      c, $02
                call    BDOS
                pop     bc
                pop     hl
nocr:
                ld      a, (func)
                cp      $09
                jr      nz, bytes
                push    hl                      ; STROUT: the whole string at once
                push    bc
                ex      de, hl
                ld      c, $09
                call    BDOS
                pop     bc
                pop     hl
                ld      e, b
                ld      d, 0
                add     hl, de                  ; past the string
                jr      record
bytes:
                ld      e, (hl)
                inc     hl
                push    hl
                push    bc
                ld      a, (func)
                ld      c, a
                call    BDOS                    ; CONOUT / DIRIO-out of E
                pop     bc
                pop     hl
                djnz    bytes
record:
                ld      a, (COLUMN)
                ld      (ix+0), a
                ld      a, (CSRX)
                ld      (ix+1), a
                inc     ix
                inc     ix
                jr      next
finish:
                ld      e, 13
                ld      c, $02
                call    BDOS
                ld      e, 10
                ld      c, $02
                call    BDOS
                ld      a, $A5
                ld      (mark), a
                jp      done

func:           db      0

; --- the cases ---------------------------------------------------------------
; macro-free: `db func, n, bytes...`
cases:
                ; A. "XYZ" then one control code (CONOUT), 0..31 and 127; 1 (the graphic-
                ;    character prefix) is followed by 'Q', 27 (ESC) is its own group below
                db      2, 4, "XYZ", 0
                db      2, 5, "XYZ", 1, "Q"
                db      2, 4, "XYZ", 2
                db      2, 4, "XYZ", 3
                db      2, 4, "XYZ", 4
                db      2, 4, "XYZ", 5
                db      2, 4, "XYZ", 6
                db      2, 4, "XYZ", 7
                db      2, 4, "XYZ", 8
                db      2, 4, "XYZ", 9
                db      2, 4, "XYZ", 10
                db      2, 4, "XYZ", 11
                db      2, 4, "XYZ", 12
                db      2, 4, "XYZ", 13
                db      2, 4, "XYZ", 14
                db      2, 4, "XYZ", 15
                db      2, 4, "XYZ", 16
                db      2, 4, "XYZ", 17
                db      2, 4, "XYZ", 18
                db      2, 4, "XYZ", 19
                db      2, 4, "XYZ", 20
                db      2, 4, "XYZ", 21
                db      2, 4, "XYZ", 22
                db      2, 4, "XYZ", 23
                db      2, 4, "XYZ", 24
                db      2, 4, "XYZ", 25
                db      2, 4, "XYZ", 26
                db      2, 4, "XYZ", 28
                db      2, 4, "XYZ", 29
                db      2, 4, "XYZ", 30
                db      2, 4, "XYZ", 31
                db      2, 4, "XYZ", 127
                ; B. the graphic prefix alone after "XYZ", then one more printable
                db      2, 4, "XYZ", 1
                db      2, 1, "Q"               ; (continues the pending prefix? a fresh CR came first)
                ; C. ESC sequences after "XYZ", byte by byte
                db      2, 4, "XYZ", 27
                db      2, 1, "K"               ; (completes the ESC above, after the CR)
                db      2, 5, "XYZ", 27, "K"    ; erase to the line's end
                db      2, 5, "XYZ", 27, "C"    ; cursor right
                db      2, 5, "XYZ", 27, "D"    ; cursor left
                db      2, 5, "XYZ", 27, "x"
                db      2, 6, "XYZ", 27, "x", "5"
                db      2, 5, "XYZ", 27, "Y"
                db      2, 6, "XYZ", 27, "Y", 32+3
                db      2, 7, "XYZ", 27, "Y", 32+3, 32+10
                db      2, 8, "XYZ", 27, "Y", 32+3, 32+10, "Q"
                ; D. TAB from columns 0..9, 15, 16
                db      2, 1, 9
                db      2, 2, "1", 9
                db      2, 3, "12", 9
                db      2, 4, "123", 9
                db      2, 5, "1234", 9
                db      2, 6, "12345", 9
                db      2, 7, "123456", 9
                db      2, 8, "1234567", 9
                db      2, 9, "12345678", 9
                db      2, 10, "123456789", 9
                db      2, 16, "123456789012345", 9
                db      2, 17, "1234567890123456", 9
                db      2, 3, 9, 9, 9           ; three TABs
                ; E. BS at column 0, and twice from 1
                db      2, 1, 8
                db      2, 3, "Q", 8, 8
                db      2, 4, "QR", 8, 9        ; BS then TAB
                ; F. past the line: 36, 37, 38, 41, 45 printables (LINLEN in the head)
                db      2, 36, "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                db      2, 37, "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!"
                db      2, 38, "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?"
                db      2, 41, "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?+-*"
                db      2, 45, "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?+-*/=<>"
                db      2, 43, "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?+-*/", 9
                ; G. characters $80..$FF
                db      2, 4, "XYZ", $80
                db      2, 4, "XYZ", $A0
                db      2, 4, "XYZ", $FF
                ; H. DIRIO-out ($06): printable, BS, TAB, FF, BEL, LF, CR
                db      6, 3, "XYZ"
                db      6, 4, "XYZ", 8
                db      6, 4, "XYZ", 9
                db      6, 4, "XYZ", 12
                db      6, 4, "XYZ", 7
                db      6, 4, "XYZ", 10
                db      6, 4, "XYZ", 13
                ; I. STROUT ($09): the same codes inside one string
                db      9, 4, "XYZ$"
                db      9, 5, "XYZ", 8, "$"
                db      9, 5, "XYZ", 9, "$"
                db      9, 5, "XYZ", 12, "$"
                db      9, 5, "XYZ", 7, "$"
                db      9, 5, "XYZ", 10, "$"
                db      9, 7, "XYZ", 27, "Y", 32+3, "$"
                ; ===== ROUND 2 (2026-11-17): the goldfish reviewers' separating cases. Rows 84 on;
                ; $8x = a continuation (no CR first); each count n is len(bytes), generated =====
                db      $02, 2, $41, $42   ; R2a base: count 2
                db      $86, 3, $58, $59, $5A   ; R2a DIRIO from count 2: untouched 2 / zeroed 0
                db      $02, 7, $58, $59, $5A, $1B, $59, $23, $2A   ; R2b desync: count 6, CSRX 11
                db      $82, 1, $09   ; R2b TAB: from the count -> 8; from the cursor -> next stop past 10
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2b desync: count 36, CSRX 8
                db      $82, 1, $09   ; R2b TAB at count 36
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then BEL
                db      $82, 1, $07   ; R2c BEL after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then NUL
                db      $82, 1, $00   ; R2c NUL after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then LF
                db      $82, 1, $0A   ; R2c LF after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then right
                db      $82, 1, $1C   ; R2c right after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then up
                db      $82, 1, $1E   ; R2c up after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then down
                db      $82, 1, $1F   ; R2c down after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then ESC K
                db      $82, 2, $1B, $4B   ; R2c ESC K after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then prefix+Q
                db      $82, 2, $01, $51   ; R2c prefix+Q after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then home
                db      $82, 1, $0B   ; R2c home after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then FF
                db      $82, 1, $0C   ; R2c FF after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then BS
                db      $82, 1, $08   ; R2c BS after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then left
                db      $82, 1, $1D   ; R2c left after the desync
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2c desync 36 / CSRX 8, then DEL
                db      $82, 1, $7F   ; R2c DEL after the desync
                db      $02, 7, $58, $59, $5A, $1B, $59, $23, $2A   ; R2c desync by ESC Y: count 6, CSRX 11
                db      $82, 1, $07   ; R2c BEL: unchanged 6 / re-synced 10
                db      $02, 1, $1D   ; R2d cursor-left at count 0
                db      $02, 1, $7F   ; R2d DEL at count 0
                db      $02, 5, $58, $59, $5A, $1B, $08   ; R2e ESC BS
                db      $02, 5, $58, $59, $5A, $1B, $09   ; R2e ESC TAB
                db      $02, 5, $58, $59, $5A, $1B, $0D   ; R2e ESC CR
                db      $02, 7, $58, $59, $5A, $1B, $59, $09, $34   ; R2e ESC Y with a TAB as the row
                db      $02, 7, $58, $59, $5A, $1B, $59, $23, $09   ; R2e ESC Y with a TAB as the column
                db      $02, 5, $58, $59, $5A, $01, $09   ; R2e prefix 1 then TAB
                db      $02, 5, $58, $59, $5A, $01, $08   ; R2e prefix 1 then BS
                db      $02, 5, $58, $59, $5A, $01, $0D   ; R2e prefix 1 then CR
                db      $09, 5, $58, $59, $5A, $0B, $24   ; R2f STROUT home
                db      $09, 5, $58, $59, $5A, $0D, $24   ; R2f STROUT CR
                db      $09, 5, $58, $59, $5A, $1D, $24   ; R2f STROUT left
                db      $09, 5, $58, $59, $5A, $7F, $24   ; R2f STROUT DEL
                db      $09, 5, $58, $59, $5A, $80, $24   ; R2f STROUT $80
                db      $09, 5, $58, $59, $5A, $1C, $24   ; R2f STROUT right
                db      $09, 2, $08, $24   ; R2f STROUT BS at count 0
                db      $09, 6, $58, $59, $5A, $09, $09, $24   ; R2f STROUT two TABs
                db      $02, 4, $58, $59, $5A, $20   ; R2g space
                db      $02, 4, $58, $59, $5A, $7E   ; R2g ~
                db      $02, 4, $58, $59, $5A, $81   ; R2g $81
                db      $02, 4, $58, $59, $5A, $FE   ; R2g $FE
                db      $02, 2, $08, $51   ; R2h 255 then a printable: wrap 0 / clamp 255
                db      $02, 2, $08, $09   ; R2h TAB at 255
                db      $02, 7, $08, $08, $08, $08, $08, $08, $09   ; R2h TAB at 250
                db      $02, 7, $58, $59, $5A, $0C, $41, $09, $42   ; R2i XYZ FF A TAB B
                db      $02, 26, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $09   ; R2j 25 printables then TAB
                db      $02, 3, $58, $59, $5A   ; R2k base: count 3
                db      $8B, 1, $00   ; R2k CONST ($0B) once
                db      $86, 1, $FF   ; R2k DIRIO input (E=$FF) once
                db      $82, 1, $09   ; R2k then TAB: from 3 -> 8
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2l desync 36
                db      $86, 1, $07   ; R2l DIRIO BEL at count 36
                db      $02, 36, $41, $42, $43, $44, $45, $46, $47, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52, $53, $54, $55, $56, $57, $58, $59, $5A, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39   ; R2l desync 36
                db      $86, 1, $09   ; R2l DIRIO TAB at count 36
                db      0

                ds      $0A00 - $, $00
done:
                jr      done                    ; the capture anchor, pinned at $0A00
                ds      $0A10 - $, $00
mark:           db      $EE                     ; $A5: the run finished
head:           ds      2, $EE                  ; LINLEN, the column at entry
results:        ds      2 * 200, $EE            ; ($F237), CSRX per case
