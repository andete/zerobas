; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; wrblk_alt.asm -- S10.A's proof (disk/docs/spec-diskcode-eviction.md §6.6bc):
; TWO FCBs written ALTERNATELY with BDOS $26 WRBLK, record size 1, 256 bytes a
; call -- the shape a BASIC disk channel takes under step 10 (a 256 B record
; moved by one block transfer, S10.0). If the kernel's canonical WRBLK holds no
; cross-call state, the two files come out as if written separately.
;
;   FMAKE ALT1.BIN, FMAKE ALT2.BIN; RS := 1 on both
;   4 rounds: WRBLK ALT1 (256 x fill), WRBLK ALT2 (256 x fill+1); fill += 2
;   FCLOSE both; terminate
; Expected: ALT1 = 11h,13h,15h,17h blocks; ALT2 = 12h,14h,16h,18h blocks; 1024 B
; each. Clean-room: published BDOS FCB calls only (MSX2 TH / map.grauw.nl).

BDOS    equ     $0005
        org     $0100
start:
        ld      de, fcba
        ld      c, $16                  ; FMAKE
        call    BDOS
        ld      de, fcbb
        ld      c, $16
        call    BDOS
        ld      hl, 1
        ld      (fcba + 14), hl         ; record size 1: the FCB counts BYTES
        ld      (fcbb + 14), hl
        ld      hl, 0
        ld      (fcba + 33), hl         ; random record 0 (24-bit + the 4th byte)
        ld      (fcba + 35), hl
        ld      (fcbb + 33), hl
        ld      (fcbb + 35), hl
        ld      de, dta
        ld      c, $1A                  ; SETDTA
        call    BDOS
        ld      a, $11
        ld      (fillv), a
        ld      b, 4
round:
        push    bc
        ld      de, fcba
        call    wr_one
        ld      de, fcbb
        call    wr_one
        pop     bc
        djnz    round
        ld      de, fcba
        ld      c, $10                  ; FCLOSE
        call    BDOS
        ld      de, fcbb
        ld      c, $10
        call    BDOS
        ld      c, $00                  ; terminate
        call    BDOS
        ret

; wr_one -- DE = the FCB. Fill the DTA with (fillv), WRBLK 256 records of 1 B
; (RR advances by 256 inside the call), then fillv += 1.
wr_one:
        push    de
        ld      a, (fillv)
        ld      hl, dta
        ld      b, 0                    ; 256
wo_fill:
        ld      (hl), a
        inc     hl
        djnz    wo_fill
        pop     de
        ld      hl, 256
        ld      c, $26                  ; WRBLK
        push    ix                      ; kernel FCB calls return with IX clobbered
        call    BDOS
        pop     ix
        ld      hl, fillv
        inc     (hl)
        ret

fillv:  db      0
fcba:
        db      0
        db      "ALT1    BIN"
        ds      40 - 12, 0
fcbb:
        db      0
        db      "ALT2    BIN"
        ds      40 - 12, 0
dta:    ds      256
