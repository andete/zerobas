; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; CLAIMFILL -- D-CLAIM473's measuring cartridge: claimonce.asm's claim (HIMEM := $F380 - N, once) PLUS a pattern, so
; a RAM diff shows who writes where after this INIT. It fills $A5 over its OWN claim [$F380 - N, $F380) and over
; [$D000, $EF80) -- far below the INIT stack (~$F08C on the CF-3300 and zerobas) and above BASIC's start-up use.
; Any byte there that is no longer $A5 later was written by the disk ROM or the BIOS after this cartridge's INIT
; (scratchpad/claim473_probe.py reads those ranges as RAM addresses -- never a PC, never a ROM byte).
; N is the word at claim_n ($4010), patched per run.
; CLEAN-ROOM: 100% own code; only the published HIMEM cell.
HIMEM           equ     $FC4A
PAT             equ     $A5
                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0
claim_n:        dw      16                  ; $4010: N, patched by the probe
init:
                ld      hl, (HIMEM)
                ld      de, $F380
                or      a
                sbc     hl, de
                ret     nz                  ; claimed already (the page-2 mirror's run)
                ld      hl, $F380
                ld      de, (claim_n)
                sbc     hl, de              ; HL = $F380 - N (Cy clear: Z above)
                ld      (HIMEM), hl
                ; fill [HL, $F380) -- the claim
                ld      a, d
                or      e
                jr      z, low_fill         ; N = 0: no claim to fill
                ld      b, d
                ld      c, e                ; BC = N
                ld      (hl), PAT
                dec     bc
                ld      a, b
                or      c
                jr      z, low_fill
                ld      d, h
                ld      e, l
                inc     de
                ldir
low_fill:
                ld      hl, $D000
                ld      de, $D001
                ld      bc, $EF80 - $D000 - 1
                ld      (hl), PAT
                ldir
                ret
