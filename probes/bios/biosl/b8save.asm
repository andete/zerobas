; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; B8SAVE -- D-BIOSLADDER rung B8 (Joost 2026-11-10: "a rom that e.g. uses the disk for
; save game"). A 16 KB "AB" cartridge. Its INIT only hooks H.STKE (an RST 30h inter-
; slot call into this cartridge) and returns: a disk interface may sit in a later
; slot and be initialised after us, and H.STKE runs once every ROM has been. Then:
;   0. what the ROM finds: H.PHYD's first byte (CAP+0; $C9 = no disk interface) and
;      $F37D's (CAP+1). No disk interface: the rest is skipped (the NODISK row).
;   1. a save through the $F37D BDOS: SETDTA, FMAKE "SAVEGAMEDAT" (CAP+2), RS := 1,
;      RR := 0, WRBLK 64 bytes (A, HL: CAP+3..5), FCLOSE (CAP+6);
;   2. the load: FOPEN (CAP+7), the size (+16..19: CAP+8..11), RDBLK 64 (A, HL:
;      CAP+12..14), the 64 bytes as written (CAP+15: 1);
;   3. a second variant through PHYDIO: write the disk's LAST sector (1439 of a 720 KB
;      disk -- outside every file) and read it back (CF of each: CAP+16, +17; the bytes
;      as written: CAP+18).
;   4. a canary the program writes at $C000 when H.STKE runs, checked at the end
;      (CAP+19: 1 = untouched) -- RAM a cartridge owns once every ROM is initialised.
; Drive A is a fresh copy of the generated empty 720 KB disk (@disk). Our disk machine
; asks the date before BASIC starts when the disk has no AUTOEXEC.BAS (the CF-3300's
; behaviour; the VG-8020 + NMS 1200 does not ask), so a CR is typed at 20 s (@type-at);
; the VG-8020 has finished by then. Not compared: the file's date (no clock).
; CLEAN-ROOM: 100% own code; only published BIOS / BDOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @timeout 60

PHYDIO  equ     $0144
EXPTBL  equ     $FCC1
BDOS    equ     $F37D
H_PHYD  equ     $FFA7
H_STKE  equ     $FEDA

DONE    equ     $A000           ; @cap A000: below HIMEM -- the disk ROM's work area
CAP     equ     $A001           ; (from ~$DE00 up) is live once H.STKE runs
FCB     equ     $A200           ; 37 bytes
BUF     equ     $A300           ; 64 bytes written
BUF2    equ     $A340           ; 64 bytes read back
SEC     equ     $A400           ; 512 bytes: the PHYDIO sector
SEC2    equ     $A600           ; 512 bytes read back
CANARY  equ     $C000           ; 16 bytes: a program's RAM at $C000 after H.STKE

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                ; our slot ID (page 1), for the RST 30h call in H.STKE
                in      a, ($A8)
                rrca
                rrca
                and     3
                ld      c, a
                ld      hl, EXPTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                and     $80
                jr      z, plain
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ld      a, (hl)
                rrca
                rrca
                and     3
                rlca
                rlca
                or      c
                or      $80
                ld      c, a
plain:
                ld      a, $F7              ; RST 30h, slot, address, RET
                ld      (H_STKE), a
                ld      a, c
                ld      (H_STKE+1), a
                ld      hl, stke
                ld      (H_STKE+2), hl
                ld      a, $C9
                ld      (H_STKE+4), a
                ret

stke:
                ld      a, $C9
                ld      (H_STKE), a         ; once
                ld      hl, CANARY          ; 4. a program's own RAM at $C000 from here
                ld      b, 16
canw:
                ld      (hl), b
                inc     hl
                djnz    canw
                ei
                ld      a, (H_PHYD)
                ld      (CAP+0), a
                ld      a, (BDOS)
                ld      (CAP+1), a
                ld      a, (H_PHYD)
                cp      $C9
                jp      z, finish           ; no disk interface
                ; --- 1: save -------------------------------------------------------------
                ld      hl, BUF
                ld      b, 64
                ld      a, 1
fill:
                ld      (hl), a
                inc     hl
                add     a, 3
                djnz    fill
                ld      de, BUF
                ld      c, $1A              ; SETDTA
                call    BDOS
                call    fcb_new
                ld      de, FCB
                ld      c, $16              ; FMAKE
                call    BDOS
                ld      (CAP+2), a
                call    fcb_rs1
                ld      de, FCB
                ld      hl, 64
                ld      c, $26              ; WRBLK
                call    BDOS
                ld      (CAP+3), a
                ld      (CAP+4), hl
                ld      de, FCB
                ld      c, $10              ; FCLOSE
                call    BDOS
                ld      (CAP+6), a
                ; --- 2: load -------------------------------------------------------------
                call    fcb_new
                ld      de, FCB
                ld      c, $0F              ; FOPEN
                call    BDOS
                ld      (CAP+7), a
                ld      hl, (FCB+16)
                ld      (CAP+8), hl
                ld      hl, (FCB+18)
                ld      (CAP+10), hl
                ld      de, BUF2
                ld      c, $1A
                call    BDOS
                call    fcb_rs1
                ld      de, FCB
                ld      hl, 64
                ld      c, $27              ; RDBLK
                call    BDOS
                ld      (CAP+12), a
                ld      (CAP+13), hl
                ld      hl, BUF
                ld      de, BUF2
                ld      b, 64
                call    same
                ld      (CAP+15), a
                ; --- 3: PHYDIO ------------------------------------------------------------
                ld      hl, SEC
                ld      b, 0
                ld      a, $77
pfill:
                ld      (hl), a
                inc     hl
                ld      (hl), b
                inc     hl
                inc     a
                djnz    pfill               ; 512 bytes
                ld      hl, SEC
                ld      de, 1439
                ld      bc, $01F9           ; 1 sector, media $F9
                xor     a                   ; drive A
                scf                         ; write
                call    PHYDIO
                sbc     a, a                ; CF -> $FF / $00
                ld      (CAP+16), a
                ld      hl, SEC2
                ld      de, 1439
                ld      bc, $01F9
                xor     a                   ; drive A, CF = 0: read
                call    PHYDIO
                sbc     a, a
                ld      (CAP+17), a
                ld      hl, SEC
                ld      de, SEC2
                ld      b, 0                ; 256 x 2 bytes
                call    same2
                ld      (CAP+18), a
finish:
                ld      hl, CANARY          ; still ours? (CAP+19: 1)
                ld      b, 16
canr:
                ld      a, (hl)
                cp      b
                jr      nz, cbad
                inc     hl
                djnz    canr
                ld      a, 1
                ld      (CAP+19), a
cbad:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; fcb_new -- a fresh FCB: drive 0, "SAVEGAMEDAT", the rest 0
fcb_new:
                ld      hl, FCB
                ld      de, FCB+1
                ld      bc, 36
                ld      (hl), 0
                ldir
                ld      hl, fname
                ld      de, FCB+1
                ld      bc, 11
                ldir
                ret

; fcb_rs1 -- RS (+14..15) := 1, RR (+33..36) := 0
fcb_rs1:
                ld      hl, 1
                ld      (FCB+14), hl
                ld      hl, 0
                ld      (FCB+33), hl
                ld      (FCB+35), hl
                ret

; same -- A := 1 if the B bytes at HL and DE are equal, else 0
same:
                ld      a, (de)
                cp      (hl)
                jr      nz, differ
                inc     hl
                inc     de
                djnz    same
                ld      a, 1
                ret
differ:
                xor     a
                ret

; same2 -- as same, over 2 x B bytes (B = 0: 512)
same2:
                ld      a, (de)
                cp      (hl)
                jr      nz, differ
                inc     hl
                inc     de
                ld      a, (de)
                cp      (hl)
                jr      nz, differ
                inc     hl
                inc     de
                djnz    same2
                ld      a, 1
                ret

fname:          db      "SAVEGAMEDAT"
