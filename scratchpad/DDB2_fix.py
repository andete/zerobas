#!/usr/bin/env python3
"""D-DOSDRVB part 2 (2026-11-17): under MSX-DOS a disk access on the other drive prompts
"Insert diskette for drive X:" / "and strike a key when ready" and waits for a key, as the
CF-3300 does (scratchpad/XB2_stock.out). fat_geom_read -- the one point every disk access
crosses -- calls dsel_bdos instead of drv_select: the default drive (0) is the CURRENT one
($F247 + 1, which SELDSK sets since part 1); with the BIOS in page 0 (BASIC) it is drv_select
as before; under MSX-DOS (RAM in page 0) the prompt goes through the BDOS console (fmt_pr /
conout_emit_e) and the key through innoe_body -- drv_select's CHPUT and its calbak into main's
page 1 are not there. Refuses on a bad anchor."""
import sys


def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)}: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))


edit("disk/kernel.asm", '''                ld      a, (DK_FCB_DRV)     ; D-DSKIB: the drive this operation named
                call    drv_select          ; -> the swap prompt when it is the other one''',
     '''                ld      a, (DK_FCB_DRV)     ; D-DSKIB: the drive this operation named
                call    dsel_bdos           ; -> the swap prompt when it is the other one
                                            ; (D-DOSDRVB: under MSX-DOS too)''')
K = "disk/kernel.asm"
edit(K, '''; 🔴 D-ALIASWCELL (2026-09-23)''', '''; dsel_bdos -- 🎯 D-DOSDRVB part 2 (2026-11-17): fat_geom_read's drive select. A = the drive the
; operation named (DK_FCB_DRV: 0 the default, 1 A:, 2 B:). The default is the CURRENT drive,
; $F247 + 1 -- 0 under BASIC unless a $F37D SELDSK moved it, so BASIC's paths are unchanged.
; With the BIOS in page 0 (BASIC) it is drv_select, the D-DSKIB prompt. Under MSX-DOS (RAM in
; page 0; a machine with its RAM in primary slot 0 would read as BASIC here) the CF-3300 prints,
; after a CR LF even at a line's start, "Insert diskette for drive B:" / "and strike a key when
; ready", CR LF, and waits for a key (scratchpad/XB2_stock.out) -- through the BDOS console
; here, since CHPUT and drv_select's calbak into main's page 1 are not there. Drives past B:
; under MSX-DOS are left alone (only SELDSK's 0 / 1 reach here today).
dsel_bdos:
                or      a
                jr      nz, dsb_named
                ld      a, (CURDRV_CELL)
                inc     a                   ; the default: the current drive
dsb_named:
                push    af
                in      a, ($A8)
                and     3                   ; page 0's primary slot: 0 = the BIOS
                jr      nz, dsb_dos
                pop     af
                jp      drv_select          ; BASIC: D-DSKIB's prompt
dsb_dos:
                pop     af
                cp      3
                ret     nc
                dec     a                   ; 0 A:, 1 B:
                ld      hl, DSK_CURDRV
                cp      (hl)
                ret     z                   ; the drive already holds it: silent
                ld      (hl), a
                push    af
                ld      hl, dsl_text_nl
                call    fmt_pr              ; CR LF first, even at a line's start
                ld      hl, dsl_text_1
                call    fmt_pr
                pop     af
                add     a, 'A'
                ld      e, a
                call    conout_emit_e       ; the drive letter
                ld      hl, dsl_text_2
                call    fmt_pr              ; ":" CR LF "and strike a key when ready" CR LF
                jp      innoe_body          ; the key, no echo

; 🔴 D-ALIASWCELL (2026-09-23)''')
print("ok")
