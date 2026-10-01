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
PHASE   equ     $C000                   ; page-3 TPA byte: 1 writing, 2 RDBLK reading,
                                        ; 3 RDRND reading, 4 done (5 seek reading, 6 done
                                        ; when BIG.BIN is on the disk)
ERRS    equ     $C001                   ; the seek phase's count of WRONG blocks
FCBDUMP equ     $C010                   ; BIG.BIN's FCB (37 B) after FOPEN, after block 0
                                        ; and after block 5, at +0/+30h/+60h: which fields
                                        ; each machine keeps (D-RDBLKSEEK's design input)
                                        ; (a timing hook: a poller reads it, nothing else)
        org     $0100
start:
        ld      a, 1
        ld      (PHASE), a
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
        ; --- READ SIDE (D-WRBLKRS follow-up): reopen both, RS = 1, and read them
        ; ALTERNATELY with RDBLK $27, 256 a call, appending every block to OUT.BIN
        ; with WRBLK. A read side that positions as if records were 128 B shows
        ; up as OUT.BIN's blocks out of order or wrong. Expected: 11h..18h.
        ld      a, 2
        ld      (PHASE), a
        ld      de, fcba
        ld      c, $0F                  ; FOPEN
        call    BDOS
        ld      de, fcbb
        ld      c, $0F
        call    BDOS
        ld      de, fcbo
        ld      c, $16                  ; FMAKE OUT.BIN
        call    BDOS
        ld      hl, 1
        ld      (fcba + 14), hl
        ld      (fcbb + 14), hl
        ld      (fcbo + 14), hl
        ld      hl, 0
        ld      (fcba + 33), hl
        ld      (fcba + 35), hl
        ld      (fcbb + 33), hl
        ld      (fcbb + 35), hl
        ld      (fcbo + 33), hl
        ld      (fcbo + 35), hl
        ld      b, 4
rround:
        push    bc
        ld      de, fcba
        call    rd_copy
        ld      de, fcbb
        call    rd_copy
        pop     bc
        djnz    rround
        ld      de, fcbo
        ld      c, $10
        call    BDOS
        ; --- RDRND SIDE (D-RDRNDMULTI): reopen both, RS = 128, and read them
        ; ALTERNATELY with RDRND $21 at record 2k (= block k's fill), appending
        ; each 128 B record to OUT2.BIN with WRBLK. Expected: 11h..18h, 128 B each.
        ld      a, 3
        ld      (PHASE), a
        ld      de, fcba
        ld      c, $0F                  ; FOPEN
        call    BDOS
        ld      de, fcbb
        ld      c, $0F
        call    BDOS
        ld      de, fcbr
        ld      c, $16                  ; FMAKE OUT2.BIN
        call    BDOS
        ld      hl, 128
        ld      (fcba + 14), hl
        ld      (fcbb + 14), hl
        ld      hl, 1
        ld      (fcbr + 14), hl
        ld      hl, 0
        ld      (fcbr + 33), hl
        ld      (fcbr + 35), hl
        xor     a
        ld      (recn), a
        ld      b, 4
nround:
        push    bc
        ld      de, fcba
        call    rnd_copy
        ld      de, fcbb
        call    rnd_copy
        ld      hl, recn
        inc     (hl)
        inc     (hl)
        pop     bc
        djnz    nround
        ld      de, fcbr
        ld      c, $10
        call    BDOS
        ld      a, 4
        ld      (PHASE), a
        ; --- SEEK SIDE (D-RDBLKSEEK), only when BIG.BIN exists (the probe's
        ; --seek): read it WHOLE in 256 B RDBLKs at RS = 1. Block k is 256 x k,
        ; so a mispositioned read counts in ERRS. The phase's TIME is the row:
        ; a read that reaches RR by fetching every byte before it is quadratic.
        xor     a
        ld      (ERRS), a
        ld      (blkn), a
        ld      de, fcbg
        ld      c, $0F                  ; FOPEN BIG.BIN
        call    BDOS
        or      a
        jr      nz, no_big
        ld      a, 5
        ld      (PHASE), a
        ld      de, FCBDUMP
        call    fcb_dump
        ld      hl, 1
        ld      (fcbg + 14), hl
        ld      hl, 0
        ld      (fcbg + 33), hl
        ld      (fcbg + 35), hl
        ld      b, 128                  ; 32 KB
sk_loop:
        push    bc
        ld      de, fcbg
        ld      hl, 256
        ld      c, $27                  ; RDBLK
        push    ix
        call    BDOS
        pop     ix
        ld      a, (blkn)
        ld      de, FCBDUMP + $30
        or      a
        call    z, fcb_dump
        ld      a, (blkn)
        ld      de, FCBDUMP + $60
        cp      5
        call    z, fcb_dump
        ld      hl, dta
        ld      a, (blkn)
        ld      b, 0
sk_cmp:
        cp      (hl)
        jr      nz, sk_bad
        inc     hl
        djnz    sk_cmp
        jr      sk_next
sk_bad:
        ld      hl, ERRS
        inc     (hl)
sk_next:
        ld      hl, blkn
        inc     (hl)
        pop     bc
        djnz    sk_loop
        ld      a, 6
        ld      (PHASE), a
no_big:
        ld      c, $00                  ; terminate
        call    BDOS
        ret

; rd_copy -- DE = the FCB to read: RDBLK 256 x 1 B into the DTA, then WRBLK
; those 256 B onto OUT.BIN.
rd_copy:
        ld      hl, 256
        ld      c, $27                  ; RDBLK
        push    ix
        call    BDOS
        pop     ix
        ld      de, fcbo
        ld      hl, 256
        ld      c, $26                  ; WRBLK
        push    ix
        call    BDOS
        pop     ix
        ret

; fcb_dump -- copy BIG.BIN's FCB (37 B) to DE.
fcb_dump:
        ld      hl, fcbg
        ld      bc, 37
        ldir
        ret

; rnd_copy -- DE = the FCB: random record := (recn), RDRND one 128 B record into
; the DTA, then WRBLK those 128 B onto OUT2.BIN.
rnd_copy:
        ld      hl, 33
        add     hl, de
        ld      a, (recn)
        ld      (hl), a
        inc     hl
        xor     a
        ld      (hl), a
        inc     hl
        ld      (hl), a
        inc     hl
        ld      (hl), a
        ld      c, $21                  ; RDRND
        push    ix
        call    BDOS
        pop     ix
        ld      de, fcbr
        ld      hl, 128
        ld      c, $26                  ; WRBLK
        push    ix
        call    BDOS
        pop     ix
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
recn:   db      0
blkn:   db      0
fcba:
        db      0
        db      "ALT1    BIN"
        ds      40 - 12, 0
fcbb:
        db      0
        db      "ALT2    BIN"
        ds      40 - 12, 0
fcbo:
        db      0
        db      "OUT     BIN"
        ds      40 - 12, 0
fcbr:
        db      0
        db      "OUT2    BIN"
        ds      40 - 12, 0
fcbg:
        db      0
        db      "BIG     BIN"
        ds      40 - 12, 0
dta:    ds      256
