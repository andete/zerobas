; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX5.COM -- Tier-C case 3: the DIR-FULL corner of Create ($16 FMAKE).
; See disk/docs/tier2-tierC-spec.md "Candidate cases" #3. The happy-path FMAKE
; is already proven byte-identical to stock elsewhere (BDOSX3 record 0); this
; exerciser drives the ADVERSARIAL corner: FMAKE when the root directory has
; NO free entry slot left, while the volume still has free DATA CLUSTERS (so
; the failure is unambiguously dir-full, not disk-full -- build_bdosx5_disk.py
; fills the root dir to its BPB entry count with tiny dummy files, then
; asserts free clusters remain > 0).
;
; Lifecycle: FMAKE a fresh name (no dir slot -> stock should fail) -> FMAKE a
; second, distinct fresh name (consistency of the dir-full return) -> FOPEN
; the first name (does a failed create leave anything openable?). Every
; call's outward registers land in a fixed RAM buffer (`regs`), then the
; program self-loops at `done` -- the anchor for disk_probe_diff.py's
; `capture --at <done> --mem ...` differential. Same skeleton as bdosx4.asm/
; bdosx3.asm (fillfcb-style setup, IX-indexed `snap`, 8-byte records).
;
; CLEAN-ROOM: 100% own code; BDOS function contracts = published
; map.grauw.nl MSX-DOS function reference (DOS-1 subset) + CP/M 2.2 FCB
; layout, cited in disk/PROVENANCE.md; no stock/kernel bytes decoded.
;
; Build: pasmo --bin bdosx5.asm bdosx5.com bdosx5.sym

                org     $0100

BDOS            equ     $0005

start:
                ; --- record 0: $16 FMAKE (fresh FCB "DIRFULL TMP"; dir is full) ---
                ld      hl, name_dirfull_tmp
                call    fillfcb_named
                ld      c, $16
                ld      de, fcb
                push    ix                      ; the kernel returns FCB calls with IX clobbered
                call    BDOS                    ; (to $F195); preserve our record-walk across it,
                pop     ix                      ; else `ld (ix+0)` stamps system RAM (killed stock)
                ld      ix, regs+0*8
                ld      (ix+0), $16
                call    snap

                ; --- record 1: $16 FMAKE (second, distinct fresh FCB "DIRFUL2 TMP") ---
                ld      hl, name_dirful2_tmp
                call    fillfcb_named
                ld      c, $16
                ld      de, fcb
                push    ix
                call    BDOS
                pop     ix
                ld      ix, regs+1*8
                ld      (ix+0), $16
                call    snap

                ; --- record 2: $0F FOPEN "DIRFULL TMP" (the name record 0 failed to create) ---
                ld      hl, name_dirfull_tmp
                call    fillfcb_named
                ld      c, $0F
                ld      de, fcb
                push    ix
                call    BDOS
                pop     ix
                ld      ix, regs+2*8
                ld      (ix+0), $0F
                call    snap

done:
                jr      done                    ; self-loop; capture --at <done>

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
name_dirfull_tmp: db    "DIRFULL TMP"           ; fresh name; no dir slot to hold it
name_dirful2_tmp: db    "DIRFUL2 TMP"           ; second, distinct fresh name

; Addresses are NOT hand-pinned (build_bdosx5_disk.py reads them from the .sym).
fcb:            ds      37                      ; 37-byte FCB
regs:           ds      8*8                     ; 8 records x 8 B (3 used)
