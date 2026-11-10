; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; B1TEXT -- D-BIOSLADDER rung B1 (TODO.md): the text console a ROM program drives
; through the main BIOS. A 16 KB "AB" cartridge; INIT runs it.
;   1. the console cells as the cartridge finds them at INIT (CSRX, CSRY, LINLEN,
;      LINL40, CRTCNT, CNSDFG) and IFF2 (CAP+30: 4 = interrupts enabled); RG1SAV at INIT (CAP+31), LINL32 at INIT (CAP+33)
;      and after INITXT (CAP+32);
;   2. LINL40 := 40, INITXT, CLS; CHPUT of a line with CR LF, BS, TAB and the cursor
;      control codes; CSRX / CSRY after it;
;   3. POSIT (12, 5) and a character; ESC Y (row 8, column 3) and a character; the
;      cursor after each;
;   4. ESC K and ESC J on a filled line, home + right, and up / down at the edges;
;   5. ERAFNK and DSPFNK: CNSDFG after each;
;   6. KILBUF, then CHGET x 3 of typed keys (the harness types them once KEYREADY
;      is 1);
;   7. 30 numbered lines: the screen scrolls; the cursor after it.
; Captured: the cells and codes above in the CAP block, and the 40 x 24 name table
; (VRAM $0000-$03BF) after step 7.
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @keys aB7
; @vram 0000:3C0
; @timeout 40

CHGET   equ     $009F
CHPUT   equ     $00A2
CLS     equ     $00C3
POSIT   equ     $00C6
ERAFNK  equ     $00CC
DSPFNK  equ     $00CF
INITXT  equ     $006C
KILBUF  equ     $0156
LINL40  equ     $F3AE
LINL32  equ     $F3AF
LINLEN  equ     $F3B0
CRTCNT  equ     $F3B1
CSRY    equ     $F3DC
CSRX    equ     $F3DD
CNSDFG  equ     $F3DE
RG1SAV  equ     $F3E0

DONE    equ     $E000
CAP     equ     $E001
KEYRDY  equ     $E100

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      a, i                ; P/V = IFF2: interrupts on at INIT?
                push    af
                ld      hl, CAP             ; the block starts 0 on both machines
                ld      de, CAP+1           ; (power-on RAM: VG-8020 $00, ours $FF)
                ld      bc, $FE
                ld      (hl), 0
                ldir
                pop     hl
                ld      a, l
                and     4
                ld      (CAP+30), a
                ld      a, (RG1SAV)         ; VDP register 1 as the BIOS keeps it
                ld      (CAP+31), a
                ld      a, (LINL32)         ; the SCREEN 1 width at INIT
                ld      (CAP+33), a
                ld      a, (CSRX)
                ld      (CAP+0), a
                ld      a, (CSRY)
                ld      (CAP+1), a
                ld      a, (LINLEN)
                ld      (CAP+2), a
                ld      a, (LINL40)
                ld      (CAP+3), a
                ld      a, (CRTCNT)
                ld      (CAP+4), a
                ld      a, (CNSDFG)
                ld      (CAP+5), a
                ; --- 2: a known screen, then control codes ---------------------------
                ld      a, 40
                ld      (LINL40), a
                call    INITXT
                ld      a, (RG1SAV)
                ld      (CAP+32), a
                xor     a
                call    CLS
                ld      hl, msg1
                call    puts
                ld      de, CAP+6
                call    curs
                ; --- 3: POSIT and ESC Y -----------------------------------------------
                ld      hl, $0C05           ; H = column 12, L = row 5
                call    POSIT
                ld      a, '#'
                call    CHPUT
                ld      de, CAP+8
                call    curs
                ld      hl, msg2            ; ESC Y (row 8 + 32) (column 3 + 32) '@'
                call    puts
                ld      de, CAP+10
                call    curs
                ; --- 4: erase codes, home, edges -------------------------------------
                ld      hl, msg3
                call    puts
                ld      de, CAP+12
                call    curs
                ld      hl, msg4
                call    puts
                ld      de, CAP+14
                call    curs
                ; --- 5: the function-key line ----------------------------------------
                call    ERAFNK
                ld      a, (CNSDFG)
                ld      (CAP+16), a
                ld      a, (CRTCNT)
                ld      (CAP+17), a
                call    DSPFNK
                ld      a, (CNSDFG)
                ld      (CAP+18), a
                ld      a, (CRTCNT)
                ld      (CAP+19), a
                call    ERAFNK
                ; --- 6: typed keys -----------------------------------------------------
                call    KILBUF
                ld      a, 1
                ld      (KEYRDY), a
                call    CHGET
                ld      (CAP+20), a
                call    CHGET
                ld      (CAP+21), a
                call    CHGET
                ld      (CAP+22), a
                ld      de, CAP+23
                call    curs
                ; --- 7: scroll ---------------------------------------------------------
                ld      b, 30
                ld      c, '0'
scroll:
                push    bc
                ld      a, 13
                call    CHPUT
                ld      a, 10
                call    CHPUT
                ld      a, 'L'
                call    CHPUT
                pop     bc
                push    bc
                ld      a, c
                call    CHPUT
                pop     bc
                inc     c
                ld      a, c
                cp      '9' + 1
                jr      nz, scr_next
                ld      c, '0'
scr_next:
                djnz    scroll
                ld      de, CAP+25
                call    curs
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; puts -- CHPUT each byte of the 0-terminated string at HL
puts:
                ld      a, (hl)
                or      a
                ret     z
                push    hl
                call    CHPUT
                pop     hl
                inc     hl
                jr      puts

; curs -- (DE) := CSRX, (DE+1) := CSRY
curs:
                ld      a, (CSRX)
                ld      (de), a
                inc     de
                ld      a, (CSRY)
                ld      (de), a
                ret

msg1:           db      "B1 TEXT", 13, 10, "AB", 8, "C", 9, "D", 28, 28, "E", 29, "F"
                db      30, "G", 31, 31, "H", 13, 10, 0
msg2:           db      27, "Y", 8 + 32, 3 + 32, "@", 0
msg3:           db      13, 10, "ERASE ME TO THE END", 13, 28, 28, 28, 27, "K", "x"
                db      13, 10, "AND BELOW", 30, 27, "J", "y", 0
msg4:           db      11, 28, "h", 30, "u", 13, 29, "l", 0
