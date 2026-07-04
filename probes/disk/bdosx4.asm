; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX4.COM -- Tier-C case 2: the DISK-FULL corner of Sequential Write ($15).
; The happy-path WRSEQ (incl. second-cluster allocation) is already proven
; byte-identical to stock by BDOSX3 records 1-9; this exerciser drives the
; ADVERSARIAL corner BDOSX3 never reaches: WRSEQ when the volume has run out
; of free clusters.
;
; It runs on a purpose-built 100%-FULL fixture (build_bdosx4_disk.py leaves ZERO
; free clusters). Lifecycle: FMAKE a fresh scratch file, then WRSEQ the same
; 128-byte pattern 12 times. The write that first needs to allocate a data
; cluster finds none free and returns the disk-full code; every later WRSEQ
; stays full too -- so the run captures the disk-full return with no successful
; physical data flush beforehand to desync the differential. We do NOT posit
; what the disk-full return is; we capture whatever stock does and require ours
; to equal it. A closing FCLOSE (record 13) captures how each side finalises a
; file that never got a cluster.
;
; Every call's outward registers land in a fixed RAM buffer (`regs`), then the
; program self-loops at `done` -- the anchor for disk_probe_diff.py's
; `capture --at <done> --mem <regs> ...` differential. Same skeleton as
; bdosx3.asm (fillfcb-style setup, IX-indexed `snap`, 8-byte records).
;
; CLEAN-ROOM: 100% own code. BDOS function contracts are the published
; map.grauw.nl MSX-DOS function reference (DOS-1 subset) + CP/M 2.2 FCB layout,
; already cited in disk/PROVENANCE.md. No stock/kernel bytes decoded.
;
; Build: pasmo --bin bdosx4.asm bdosx4.com bdosx4.sym

                org     $0100

BDOS            equ     $0005

start:
                call    build_wrpat

                ; --- record 0: $16 FMAKE (fresh FCB "BDOSXF  TMP") ---
                ld      hl, name_bdosxf_tmp
                call    fillfcb_named
                ld      c, $16
                ld      de, fcb
                call    BDOS
                ld      ix, regs+0*8
                ld      (ix+0), $16
                call    snap

                ; --- set DTA -> wrpat (once for the whole WRSEQ run) ---
                ld      de, wrpat
                ld      c, $1A
                call    BDOS

                ; --- records 1..12: $15 WRSEQ; the disk fills partway through ---
                ; IX walks regs+1*8, regs+2*8, ...; after 12 iterations it points
                ; at regs+13*8, exactly the FCLOSE slot below.
                ld      ix, regs+1*8
wr_loop:
                ld      c, $15
                ld      de, fcb
                push    ix                      ; the kernel returns FCB calls with IX clobbered
                call    BDOS                    ; (to $F195); preserve our record-walk across it,
                pop     ix                      ; else `ld (ix+0)` stamps system RAM (killed stock)
                ld      (ix+0), $15
                call    snap                    ; snap sees the true BDOS return regs
                ld      de, 8
                add     ix, de                  ; next 8-byte record slot
                ld      hl, wr_count
                dec     (hl)
                jr      nz, wr_loop

                ; --- record 13: $10 FCLOSE (IX already at regs+13*8) ---
                ld      c, $10
                ld      de, fcb
                push    ix                      ; same IX-preservation guard as the WRSEQ loop
                call    BDOS
                pop     ix
                ld      (ix+0), $10
                call    snap

done:
                jr      done                    ; self-loop; capture --at <done>

; ---------------------------------------------------------------------------
; build_wrpat -- fill `wrpat` with byte[i] = (i*3 + 1) & $FF, i=0..127. Same
; deterministic pattern as bdosx3.asm. Clobbers AF/B/HL.
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
; fillfcb_named -- zero the 37-byte FCB, set drive=0 (implicit via the zero
; fill), copy the 11-byte 8.3 name at HL into +1. Clobbers AF/BC/DE/HL.
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
; data
; ---------------------------------------------------------------------------
wr_count:        db     12                      ; WRSEQ attempts (loaded once per run)
name_bdosxf_tmp: db     "BDOSXF  TMP"           ; scratch file created + written to the wall

; Addresses are NOT hand-pinned (build_bdosx4_disk.py reads them from the .sym).
fcb:            ds      37                      ; 37-byte FCB
regs:           ds      16*8                    ; 16 records x 8 B (14 used)
wrpat:          ds      128                     ; deterministic write pattern
