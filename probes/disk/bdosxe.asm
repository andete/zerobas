; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSXE.COM -- D-DISKCONTRACT gap 2 (2026-11-17): a disk ERROR as an MSX-DOS program sees
; it through the BDOS. Every other exerciser runs on a writable disk; DSKIO's own error
; codes are compared by phydioerr-acceptance, but not what the BDOS does with them.
;
; The program installs its OWN disk-error handler through DISKVE ($F323: the published
; "pointer to the address of the disk error handler" -- so $F323 holds the address of a
; cell, `hcell`, which holds the handler's address), then on a WRITE-PROTECTED disk
; (build_bdosxe_disk.py leaves the image read-only; openMSX mounts it protected):
;   record 0: $16 FMAKE "WPTEST  TMP"  -- the directory write fails
;   record 1: $30 WRABS sector 20, 1 sector, drive 0
;   record 2: $2F RDABS sector 1440 -- past the 720 KB disk's last cylinder: a READ error
; Each call's answer comes from `answers` (index = the call's number; the builder can
; patch it, default all 0 = Ignore), so the same program measures Ignore and Retry.
; The handler records the registers it is entered with (A, B, C, D, E, H, L -- 8 B a
; call, up to 6 calls) and answers C = 0 (Ignore), so the BDOS returns to us; each
; BDOS return is snapped as the other exercisers do. We do not posit what either side
; passes: the capture is diffed against the stock CF-3300 byte for byte.
;
; CLEAN-ROOM: 100% own code; DISKVE and the BDOS functions are the published MSX-DOS 1
; interface (the map already cited in disk/PROVENANCE.md). Nothing of the reference read.
;
; Build: pasmo --bin bdosxe.asm bdosxe.com bdosxe.sym

                org     $0100

BDOS            equ     $0005
DISKVE          equ     $F323

start:
                call    build_wrpat
                ld      hl, hcell
                ld      (DISKVE), hl            ; our handler, through the published cell

                ; --- record 0: $16 FMAKE on the protected disk ---
                ld      hl, name_wptest
                call    fillfcb_named
                ld      c, $16
                ld      de, fcb
                ld      ix, regs+0*8
                push    ix
                call    BDOS
                pop     ix
                ld      (ix+0), $16
                call    snap

                ; --- record 1: $30 WRABS sector 20 from wrpat ---
                ld      de, wrpat
                ld      c, $1A                  ; SETDTA: the buffer WRABS writes from
                call    BDOS
                ld      de, 20                  ; the sector
                ld      hl, $0100               ; H = 1 sector, L = drive 0 (A:)
                ld      c, $30
                ld      ix, regs+1*8
                push    ix
                call    BDOS
                pop     ix
                ld      (ix+0), $30
                call    snap

                ; --- record 2: $2F RDABS sector 1440 (a read error) into wrpat ---
                ld      de, 1440
                ld      hl, $0100               ; H = 1 sector, L = drive 0
                ld      c, $2F
                ld      ix, regs+2*8
                push    ix
                call    BDOS
                pop     ix
                ld      (ix+0), $2F
                call    snap

done:
                jr      done                    ; self-loop; capture --at <done>

; ---------------------------------------------------------------------------
; handler -- the disk-error handler DISKVE names. Records A B C D E H L into the
; next 8-byte slot of `hrec` (slot +7 = the call's index), counts the call, and
; answers C = 0 (Ignore). After 6 calls it answers C = 2 (Abort) instead, so a
; side that retried for ever could not hang the run: the anchor would then be
; missed, which the harness reports, rather than looping silently.
; ---------------------------------------------------------------------------
handler:
                ld      (hsave), hl
                ld      hl, (hptr)
                ld      (hl), a
                inc     hl
                ld      (hl), b
                inc     hl
                ld      (hl), c
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (hl), e
                inc     hl
                push    de
                ld      de, (hsave)
                ld      (hl), d
                inc     hl
                ld      (hl), e
                inc     hl
                pop     de
                ld      a, (hcount)
                ld      (hl), a                 ; slot +7: this call's index
                inc     hl
                ld      (hptr), hl
                inc     a
                ld      (hcount), a
                cp      6
                jr      nc, h_abort             ; the hang guard
                ld      hl, answers-1
                push    de
                ld      e, a
                ld      d, 0
                add     hl, de                  ; answers[call index] (B, D, E kept)
                pop     de
                ld      c, (hl)
                ld      hl, (hsave)
                ret
h_abort:        ld      hl, (hsave)
                ld      c, 2                    ; Abort (the hang guard)
                ret

; ---------------------------------------------------------------------------
; build_wrpat -- byte[i] = (i*3 + 1) & $FF, i = 0..511 (a sector's worth).
; ---------------------------------------------------------------------------
build_wrpat:
                ld      hl, wrpat
                ld      bc, 512
                ld      a, 1
bw_loop:
                ld      (hl), a
                inc     hl
                add     a, 3
                dec     bc
                ld      e, a
                ld      a, b
                or      c
                ld      a, e
                jr      nz, bw_loop
                ret

; fillfcb_named -- zero the 37-byte FCB, copy the 8.3 name at HL to +1.
fillfcb_named:
                push    hl
                ld      hl, fcb
                ld      b, 37
                xor     a
ffn_zero:
                ld      (hl), a
                inc     hl
                djnz    ffn_zero
                pop     hl
                ld      de, fcb+1
                ld      bc, 11
                ldir
                ret

; snap -- A B C D E H L into (ix+1)..(ix+7); (ix+0) is the function number.
snap:
                ld      (ix+1), a
                ld      (ix+2), b
                ld      (ix+3), c
                ld      (ix+4), d
                ld      (ix+5), e
                ld      (ix+6), h
                ld      (ix+7), l
                ret

; ---------------------------------------------------------------------------
; data -- regs, hrec and hcount are CONTIGUOUS: one capture block (3*8 + 6*8 + 1 B)
; ---------------------------------------------------------------------------
name_wptest:    db      "WPTEST  TMP"
hcell:          dw      handler
hptr:           dw      hrec
hsave:          dw      0
answers:        db      0, 0, 0, 0, 0, 0        ; per call: 0 Ignore, 1 Retry (builder-patched)
fcb:            ds      37
regs:           ds      3*8
hrec:           ds      6*8
hcount:         db      0
wrpat:          ds      512
