; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX3.COM -- Tier-2 BDOS exerciser, M24: block C (mutation + random +
; absolute I/O). See disk/docs/tier2-bdos-remaining-spec.md SS5.3 for the
; full design. Runs a create->write(x9, forcing a second-cluster FAT
; allocation)->close->reopen->read-back->close->rename->delete->negative-
; reopen lifecycle on a scratch file, then a random-record round trip and an
; absolute sector read/write-back on the resident BDOSX.BIN / boot sector,
; recording every call's outward registers into a fixed RAM buffer, then
; self-looping at `done` -- the anchor for disk_probe_diff.py's
; `capture --at <done> --mem ...` differential. Same skeleton as bdosx.asm/
; bdosx2.asm (fillfcb-style setup, IX-indexed `snap`, 8-byte records).
;
; Deliberately isolated in its own program (not folded into bdosx.asm/
; bdosx2.asm): this is the highest-risk block (dir-write + FAT-allocate
; machinery has never run through the runtime kernel before this test) so a
; divergence/hang here must not corrupt the already-proven Phase-1/BDOSX2
; evidence, per the spec's own reasoning (SS5, "why three programs").
;
; CLEAN-ROOM: 100% own code. BDOS function contracts are the published
; map.grauw.nl MSX-DOS function reference (this DOS-1-compatible subset) +
; MSX2 Technical Handbook Chapter 3 + CP/M 2.2 equivalents (FCB layout incl.
; the random field +33..35 and the rename old-name/+1, new-name/+17
; convention -- already cited in disk/PROVENANCE.md SS FCB layout). No
; stock/kernel bytes decoded.
;
; Build: pasmo -s bdosx3.sym --bin bdosx3.asm bdosx3.com

                org     $0100

BDOS            equ     $0005

; ---------------------------------------------------------------------------
; entry: FMAKE -> WRSEQ x9 -> FCLOSE -> FOPEN -> RDSEQ -> FCLOSE -> FREN ->
;        FDEL -> FOPEN(post-delete, negative) -> FOPEN(BDOSX.BIN) ->
;        RDRND -> WRRND -> RDRND -> FCLOSE -> RDABS -> WRABS
;
; Records 1-9 (WRSEQ) all write the SAME 128-byte `wrpat` buffer -- CP/M
; sequential write auto-advances the FCB's current-record field each call, so
; nine identical-content writes still land in nine distinct file records
; (1152 B total, > one 1024-B cluster -- forces the never-before-exercised
; second-cluster FAT allocation). Record 12's RDSEQ readback of record 0
; against the same pattern is the round-trip proof.
; ---------------------------------------------------------------------------
start:
                call    build_wrpat

                ; --- record 0: $16 FMAKE (fresh FCB "BDOSXW  TMP") ---
                ld      hl, name_bdosxw_tmp
                call    fillfcb_named
                ld      c, $16
                ld      de, fcb
                call    BDOS
                ld      ix, regs+0*8
                ld      (ix+0), $16
                call    snap

                ; --- records 1-9: $15 WRSEQ x9 (DTA -> wrpat, set once) ---
                ld      de, wrpat
                ld      c, $1A
                call    BDOS

                ld      c, $15
                ld      de, fcb
                call    BDOS
                ld      ix, regs+1*8
                ld      (ix+0), $15
                call    snap

                ld      c, $15
                ld      de, fcb
                call    BDOS
                ld      ix, regs+2*8
                ld      (ix+0), $15
                call    snap

                ld      c, $15
                ld      de, fcb
                call    BDOS
                ld      ix, regs+3*8
                ld      (ix+0), $15
                call    snap

                ld      c, $15
                ld      de, fcb
                call    BDOS
                ld      ix, regs+4*8
                ld      (ix+0), $15
                call    snap

                ld      c, $15
                ld      de, fcb
                call    BDOS
                ld      ix, regs+5*8
                ld      (ix+0), $15
                call    snap

                ld      c, $15
                ld      de, fcb
                call    BDOS
                ld      ix, regs+6*8
                ld      (ix+0), $15
                call    snap

                ld      c, $15
                ld      de, fcb
                call    BDOS
                ld      ix, regs+7*8
                ld      (ix+0), $15
                call    snap

                ld      c, $15
                ld      de, fcb
                call    BDOS
                ld      ix, regs+8*8
                ld      (ix+0), $15
                call    snap

                ld      c, $15
                ld      de, fcb
                call    BDOS
                ld      ix, regs+9*8
                ld      (ix+0), $15
                call    snap

                ; --- record 10: $10 FCLOSE (dir-entry size/date rewrite) ---
                ld      c, $10
                ld      de, fcb
                call    BDOS
                ld      ix, regs+10*8
                ld      (ix+0), $10
                call    snap

                ; --- record 11: $0F FOPEN (reopen "BDOSXW  TMP") ---
                ld      hl, name_bdosxw_tmp
                call    fillfcb_named
                ld      c, $0F
                ld      de, fcb
                call    BDOS
                ld      ix, regs+11*8
                ld      (ix+0), $0F
                call    snap

                ; --- record 12: $14 RDSEQ (DTA -> rdbuf; round-trip proof) ---
                ld      de, rdbuf
                ld      c, $1A
                call    BDOS
                ld      c, $14
                ld      de, fcb
                call    BDOS
                ld      ix, regs+12*8
                ld      (ix+0), $14
                call    snap

                ; --- record 13: $10 FCLOSE ---
                ld      c, $10
                ld      de, fcb
                call    BDOS
                ld      ix, regs+13*8
                ld      (ix+0), $10
                call    snap

                ; --- record 14: $17 FREN ("BDOSXW  TMP" -> "BDOSXR  TMP") ---
                call    fillfren
                ld      c, $17
                ld      de, fcb
                call    BDOS
                ld      ix, regs+14*8
                ld      (ix+0), $17
                call    snap

                ; --- record 15: $13 FDEL (fresh FCB "BDOSXR  TMP") ---
                ld      hl, name_bdosxr_tmp
                call    fillfcb_named
                ld      c, $13
                ld      de, fcb
                call    BDOS
                ld      ix, regs+15*8
                ld      (ix+0), $13
                call    snap

                ; --- record 16: $0F FOPEN "BDOSXR  TMP" post-delete (expect A=$FF) ---
                ld      hl, name_bdosxr_tmp
                call    fillfcb_named
                ld      c, $0F
                ld      de, fcb
                call    BDOS
                ld      ix, regs+16*8
                ld      (ix+0), $0F
                call    snap

                ; --- record 17: $0F FOPEN "BDOSX   BIN" (Phase-1's resident file) ---
                ld      hl, name_bdosx_bin
                call    fillfcb_named
                ld      c, $0F
                ld      de, fcb
                call    BDOS
                ld      ix, regs+17*8
                ld      (ix+0), $0F
                call    snap

                ; --- record 18: $21 RDRND, r0=2 (direct store) -> DTA rdbuf2 ---
                ld      a, 2
                ld      (fcb+33), a
                ld      de, rdbuf2
                ld      c, $1A
                call    BDOS
                ld      c, $21
                ld      de, fcb
                call    BDOS
                ld      ix, regs+18*8
                ld      (ix+0), $21
                call    snap

                ; --- record 19: $22 WRRND, r0=1 -> DTA wrpat (overwrites record 1) ---
                ld      a, 1
                ld      (fcb+33), a
                ld      de, wrpat
                ld      c, $1A
                call    BDOS
                ld      c, $22
                ld      de, fcb
                call    BDOS
                ld      ix, regs+19*8
                ld      (ix+0), $22
                call    snap

                ; --- record 20: $21 RDRND, r0=1 -> DTA rdbuf2 (round trip of WRRND) ---
                ld      a, 1
                ld      (fcb+33), a
                ld      de, rdbuf2
                ld      c, $1A
                call    BDOS
                ld      c, $21
                ld      de, fcb
                call    BDOS
                ld      ix, regs+20*8
                ld      (ix+0), $21
                call    snap

                ; --- record 21: $10 FCLOSE ---
                ld      c, $10
                ld      de, fcb
                call    BDOS
                ld      ix, regs+21*8
                ld      (ix+0), $10
                call    snap

                ; --- record 22: $2F RDABS (DTA -> absbuf; L=0 drive-A H=1 sector DE=0) ---
                ld      de, absbuf
                ld      c, $1A
                call    BDOS
                ld      de, 0
                ld      l, 0
                ld      h, 1
                ld      c, $2F
                call    BDOS
                ld      ix, regs+22*8
                ld      (ix+0), $2F
                call    snap

                ; --- record 23: $30 WRABS (same regs; writes absbuf back unchanged) ---
                ld      de, 0
                ld      l, 0
                ld      h, 1
                ld      c, $30
                call    BDOS
                ld      ix, regs+23*8
                ld      (ix+0), $30
                call    snap

done:
                jr      done                    ; self-loop; disk_probe_diff.py
                                                ; `capture --at <done> --mem ...`
                                                ; anchor (SS7 of the earlier Phase-1
                                                ; spec; unarmed like BDOSX2 -- `done`
                                                ; sits well past any early boot
                                                ; busy-loop address).

; ---------------------------------------------------------------------------
; build_wrpat -- fill `wrpat` with byte[i] = (i*3 + 1) & $FF, i=0..127 (the
; spec SS5.3 deterministic write pattern). Clobbers AF/B/HL.
; ---------------------------------------------------------------------------
build_wrpat:
                ld      hl, wrpat
                ld      b, 128
                ld      a, 1
bw_loop:
                ld      (hl), a
                inc     hl
                add     a, 3
                djnz    bw_loop
                ret

; ---------------------------------------------------------------------------
; fillfcb_named -- zero the 37-byte FCB, set drive=0, copy the 11-byte 8.3
; name pointed to by HL. Clobbers AF/BC/DE/HL.
; ---------------------------------------------------------------------------
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

; ---------------------------------------------------------------------------
; fillfren -- zero the FCB, old name ("BDOSXW  TMP") at +1, new name
; ("BDOSXR  TMP") at +17 (published CP/M FREN convention). Clobbers
; AF/BC/DE/HL.
; ---------------------------------------------------------------------------
fillfren:
                ld      hl, fcb
                ld      b, 37
                xor     a
fr_zero:
                ld      (hl), a
                inc     hl
                djnz    fr_zero
                ld      hl, name_bdosxw_tmp
                ld      de, fcb+1
                ld      bc, 11
                ldir
                ld      hl, name_bdosxr_tmp
                ld      de, fcb+17
                ld      bc, 11
                ldir
                ret

; ---------------------------------------------------------------------------
; snap -- store A, B, C, D, E, H, L into (ix+1)..(ix+7). (ix+0) is pre-filled
; by the caller with the literal BDOS function number.
; ---------------------------------------------------------------------------
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
; data (8.3 name tables + FCB + result buffers)
; ---------------------------------------------------------------------------
name_bdosxw_tmp: db     "BDOSXW  TMP"           ; scratch file, created/written/closed/reopened
name_bdosxr_tmp: db     "BDOSXR  TMP"           ; scratch file's post-rename name
name_bdosx_bin:  db     "BDOSX   BIN"           ; Phase-1's resident 384-byte data file

; Addresses below are NOT hand-pinned (the code is longer than bdosx.asm/
; bdosx2.asm's provisional $0300/$0340/$0480 budget -- a fixed `ds` to those
; addresses here would go negative and wrap). They fall wherever the
; assembled code ends; build_bdosx3_disk.py reads the real addresses from
; the .sym and reports them (M15 SS7.3 no-hand-guessed-addresses lesson).
fcb:            ds      37                      ; 37-byte FCB
regs:           ds      32*8                    ; 32 records x 8 B
wrpat:          ds      128                     ; deterministic write pattern
rdbuf:          ds      128                     ; WRSEQ round-trip readback
rdbuf2:         ds      128                     ; RDRND readback (x2 uses)
absbuf:         ds      512                     ; RDABS/WRABS sector buffer
