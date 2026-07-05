; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX7.COM -- Tier-C case 5: the RENAME-COLLISION corner of Rename ($17
; FREN). See disk/docs/tier2-tierC-spec.md "Candidate cases" #5. The
; happy-path FREN (renaming to a FRESH name) is already proven byte-identical
; to stock elsewhere (BDOSX3 record 14); this exerciser drives the
; ADVERSARIAL corner: renaming a file to a name that ALREADY EXISTS.
;
; Fixture: two 1-byte files "RENSRC  .TMP" and "RENDST  .TMP", both present.
; Lifecycle: FREN RENSRC.TMP -> RENDST.TMP (collision; RENDST already exists)
; -> FOPEN "RENSRC  TMP" (did the source survive the failed rename?) -> FOPEN
; "RENDST  TMP" (is the original destination intact?). Every call's outward
; registers land in a fixed RAM buffer (`regs`), then the program self-loops
; at `done` -- the anchor for disk_probe_diff.py's `capture --at <done> --mem
; ...` differential. Same skeleton as bdosx4.asm/bdosx3.asm (fillfcb-style
; setup, IX-indexed `snap`, 8-byte records).
;
; FREN FCB layout -- old name at FCB+1 (11 bytes, "old" 8.3 name), new name at
; FCB+17 (11 bytes, "new" 8.3 name): the EXACT layout bdosx3.asm's `fillfren`
; uses for its own (non-colliding) $17 call, confirmed by reading bdosx3.asm
; directly (fillfren: old name -> fcb+1, new name -> fcb+17). Copied verbatim
; here for the collision case -- same published CP/M FREN convention, already
; cited in disk/PROVENANCE.md.
;
; CLEAN-ROOM: 100% own code; BDOS function contracts = published
; map.grauw.nl MSX-DOS function reference (DOS-1 subset) + CP/M 2.2 FCB
; layout (rename old-name/+1, new-name/+17 convention), cited in
; disk/PROVENANCE.md; no stock/kernel bytes decoded.
;
; Build: pasmo --bin bdosx7.asm bdosx7.com bdosx7.sym

                org     $0100

BDOS            equ     $0005

start:
                ; --- record 0: $17 FREN "RENSRC  TMP" -> "RENDST  TMP" (collision) ---
                call    fillfren
                ld      c, $17
                ld      de, fcb
                push    ix                      ; the kernel returns FCB calls with IX clobbered
                call    BDOS                    ; (to $F195); preserve our record-walk across it,
                pop     ix                      ; else `ld (ix+0)` stamps system RAM (killed stock)
                ld      ix, regs+0*8
                ld      (ix+0), $17
                call    snap

                ; --- record 1: $0F FOPEN "RENSRC  TMP" (did the source survive?) ---
                ld      hl, name_rensrc_tmp
                call    fillfcb_named
                ld      c, $0F
                ld      de, fcb
                push    ix
                call    BDOS
                pop     ix
                ld      ix, regs+1*8
                ld      (ix+0), $0F
                call    snap

                ; --- record 2: $0F FOPEN "RENDST  TMP" (is the original dest intact?) ---
                ld      hl, name_rendst_tmp
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
; fillfren -- zero the FCB, old name ("RENSRC  TMP") at +1, new name
; ("RENDST  TMP", already on disk -- the collision) at +17 (published CP/M
; FREN convention, same layout as bdosx3.asm's fillfren). Clobbers
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
                ld      hl, name_rensrc_tmp
                ld      de, fcb+1
                ld      bc, 11
                ldir
                ld      hl, name_rendst_tmp
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
; data
; ---------------------------------------------------------------------------
name_rensrc_tmp: db     "RENSRC  TMP"           ; rename source; present pre-boot
name_rendst_tmp: db     "RENDST  TMP"           ; rename target; ALSO present (the collision)

; Addresses are NOT hand-pinned (build_bdosx7_disk.py reads them from the .sym).
fcb:            ds      37                      ; 37-byte FCB
regs:           ds      8*8                     ; 8 records x 8 B (3 used)
